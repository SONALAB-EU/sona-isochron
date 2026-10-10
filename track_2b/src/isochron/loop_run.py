"""Run a prompt variant with the repair loop on FLEURS sentences: resumable, optionally concurrent.

Generation only (the Apertus server must be running); the final meaning judge
runs later and separately (isochron.judge). Each item logs round 0 and every
revision, so both conditions come from the same run:
- without the loop: the closest round-0 candidate in syllables;
- with the loop:    the best candidate over all rounds (see isochron.repair).

Variants (prompt files in src/isochron/prompts/):
- v1   shorten_syllables_v1  syllable target T = level % of the input syllables (our method, with the loop)
- v2a  shorten_facts_v2a     list the facts first, then candidates at T syllables
- v2b  shorten_words_v2b     source word count + word target (level % of the words)
- v2c  shorten_graded_v2c    4 candidates at level +15/+10/+5/+0 points of the
                             input syllables, capped at 100 %
Fit and closest selection always use T in syllables.

Resuming: with --resume and an existing --out directory, items already in
items.jsonl are skipped. The run must be the same: config.json is compared
field by field (model, quantisation, prompts, generation settings, counters,
NLI, language check, data, items, levels, seeds), and every session is added
to config.json with its date, git commit, endpoint and backend. A line cut
off by a crash is dropped and its item is generated again.

--workers N runs N items at once (for servers with several slots, such as
vLLM). Items are independent and each has fixed seeds, but batching on the
server can change the arithmetic, so outputs need not match a run with
another number of workers; config.json records it.

Run from track_2b/:

    uv run python -m isochron.loop_run --lang de --split test --allow-test --levels 90 80 --seeds 0 --quantisation Q4_K_M --out results/raw/step2_loop_de_test_local --resume
    uv run python -m isochron.loop_run --lang de --split dev --exclude-gonogo --limit 2 --mock      (dry run, no LLM)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from isochron.config import ConfigError, LLMConfig
from isochron.gonogo import gonogo_ids
from isochron.language import check as check_language
from isochron.language import describe as describe_language
from isochron.llm import ChatClient
from isochron.metrics.length import counter_description, default_counter, length, target
from isochron.prompts import Prompt
from isochron.provenance import git_commit
from isochron.repair import MAX_REVISIONS, run_loop
from isochron.run import GENERATION, LLAMACPP_SAMPLERS, backend_info, check_endpoint, mock_answer
from isochron.schema import SentenceRecord, read_jsonl

VARIANTS = {
    "v1": "shorten_syllables_v1",
    "v2a": "shorten_facts_v2a",
    "v2b": "shorten_words_v2b",
    "v2c": "shorten_graded_v2c",
}
REVISE = "revise_v1"
LEVELS = (90, 80, 70, 60)
SEEDS = (0, 1, 2)
GRADES = (15, 10, 5, 0)
ROUND_SEED_STEP = 1000  # round r of an item with seed s is generated with seed s + 1000 * r
# config.json fields that must be equal for a run to be resumed
SAME_RUN = ("kind", "variant", "lang", "split", "levels", "seeds", "repair", "max_revisions", "round_seed", "mock",
            "model", "quantisation", "generation", "prompt", "revise_prompt", "length_counter", "nli_model",
            "language_check", "data", "items")


def graded_targets(level: int, n_syllables: int) -> list[int]:
    return [target(min(level + g, 100), n_syllables) for g in GRADES]


def first_prompt(variant: str, prompt: Prompt, lang: str, level: int, text: str, counter: str) -> tuple[str, dict]:
    n_syl = length(text, "syllables", lang, counter)
    t = target(level, n_syl)
    if variant in ("v1", "v2a"):
        return prompt.render(lang, t, text), {"target": t}
    if variant == "v2b":
        n_words = length(text, "words", lang, counter)
        tw = target(level, n_words)
        return prompt.render(lang, tw, text, source_words=n_words), {"target": t, "target_words_prompted": tw}
    ts = graded_targets(level, n_syl)
    return prompt.render(lang, t, text, t1=ts[0], t2=ts[1], t3=ts[2], t4=ts[3]), {"target": t, "graded_targets": ts}


def item_key(it: dict[str, Any]) -> tuple[str, int, int]:
    return str(it["id"]), int(it["level"]), int(it["seed"])


def done_items(path: Path) -> set[tuple[str, int, int]]:
    """Keys already in items.jsonl. A last line cut off by a crash is removed from the file."""
    if not path.exists():
        return set()
    good, keys = [], set()
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        try:
            keys.add(item_key(json.loads(line)))
        except (json.JSONDecodeError, KeyError):
            print(f"dropping an incomplete line from {path}", file=sys.stderr)
            continue
        good.append(line if line.endswith("\n") else line + "\n")
    path.write_text("".join(good), encoding="utf-8")
    return keys


def write_json(path: Path, obj: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def run(
    records: list[SentenceRecord],
    *,
    variant: str,
    lang: str,
    split: str,
    levels: list[int],
    seeds: list[int],
    out: Path,
    kind: str,
    selection: str,
    data: Path,
    quantisation: str | None,
    mock: bool = False,
    repair: bool = True,
    resume: bool = False,
    workers: int = 1,
    device: str | None = None,
) -> Path:
    """Generate every (sentence, level, seed) item into out/items.jsonl; returns out."""
    counter = default_counter()
    prompt, revise = Prompt.load(VARIANTS[variant]), Prompt.load(REVISE)
    client, backend, extra, config = None, {"type": "none (mock)"}, {}, None
    if not mock:
        try:
            config = LLMConfig.from_env()
        except ConfigError as e:
            sys.exit(f"{e}; use --mock for a dry run")
        check_endpoint(config)
        backend = backend_info(config)
        if backend["type"] == "llama.cpp llama-server":
            extra = {"samplers": LLAMACPP_SAMPLERS}
        client = ChatClient(config, timeout=300)

    from isochron.metrics.meaning import MODEL_ID, NLI, REVISION

    nli = NLI(device=device)
    started = datetime.now(timezone.utc)
    session = {"started": started.isoformat(timespec="seconds"), "git_commit": git_commit(), "workers": workers,
               "endpoint": "none (mock)" if mock else config.base_url, "backend": backend, "nli": nli.describe()}
    cfg = {
        "date": started.isoformat(timespec="seconds"),
        "git_commit": session["git_commit"],
        "phase": 2,
        "kind": kind,
        "variant": variant,
        "lang": lang,
        "split": split,
        "levels": levels,
        "seeds": seeds,
        "repair": repair,
        "max_revisions": MAX_REVISIONS,
        "round_seed": f"item seed + {ROUND_SEED_STEP} × round (round 0 uses the item seed)",
        "mock": mock,
        "model": "mock (word-prefix cuts, no LLM)" if mock else config.name,
        "quantisation": "n/a (mock)" if mock else quantisation,
        "endpoint": session["endpoint"],
        "backend": backend,
        "generation": {**GENERATION, **extra},
        "prompt": {"name": prompt.name, "sha256": prompt.sha256},
        "revise_prompt": {"name": revise.name, "sha256": revise.sha256},
        "length_counter": {"syllables": counter_description(counter), "counter": counter},
        "nli": nli.describe(),
        "nli_model": f"{MODEL_ID} @ {REVISION}",
        "language_check": describe_language(),
        "loop_uses": "language identifier, syllable counter and NLI only; never the final judge",
        "data": {"file": str(data), "sha256": hashlib.sha256(data.read_bytes()).hexdigest()},
        "items": {"selection": selection, "n": len(records), "ids": [r.id for r in records]},
        "tts": "none",
        "workers": workers,
        "sessions": [session],
    }
    items_path = out / "items.jsonl"
    if (out / "config.json").exists():
        if not resume:
            sys.exit(f"{out} already holds a run; pass --resume to continue it")
        old = json.loads((out / "config.json").read_text(encoding="utf-8"))
        differ = [k for k in SAME_RUN if old.get(k) != cfg.get(k)]
        if differ:
            sys.exit(f"{out} holds a different run; these settings differ: {', '.join(differ)}")
        old.setdefault("sessions", []).append(session)
        cfg = old
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "config.json", cfg)

    done = done_items(items_path)
    todo = [(r, level, seed) for seed in seeds for r in records for level in levels if (r.id, level, seed) not in done]
    n_all = len(records) * len(levels) * len(seeds)
    print(f"{variant}: {n_all} items ({len(records)} sentences × {len(levels)} levels × {len(seeds)} seeds), "
          f"{len(done)} done, {len(todo)} to go, {workers} worker(s) → {out}", flush=True)

    def count(text: str, unit: str) -> int:
        return length(text, unit, lang, counter)

    nli_lock, write_lock = threading.Lock(), threading.Lock()

    def meaning(sources, outputs):
        with nli_lock:  # one model, one tokenizer: not shared between threads
            return nli.meaning(sources, outputs)

    def one(r: SentenceRecord, level: int, seed: int) -> dict[str, Any]:
        text, targets = first_prompt(variant, prompt, lang, level, r.ref_text, counter)

        def generate(p: str, rnd: int) -> tuple[str, dict[str, Any]]:
            s = seed + ROUND_SEED_STEP * rnd
            t0 = time.monotonic()
            if mock:
                raw = mock_answer(r.ref_text, "syllables", lang, targets["target"], s, counter)
                return raw, {"seed": s, "latency_s": round(time.monotonic() - t0, 3), "finish_reason": "stop"}
            res = client.chat([{"role": "user", "content": p}], seed=s, **GENERATION, **extra)
            return res.text, {"seed": s, "latency_s": round(time.monotonic() - t0, 3),
                              "finish_reason": res.finish_reason, "usage": res.usage,
                              "timings": res.raw.get("timings")}

        log = run_loop(text, r.ref_text, lang, targets["target"], generate, meaning, count, revise, check_language,
                       repair=repair)
        return {"id": r.id, "level": level, "seed": seed, "input": r.ref_text, **targets, **log}

    pool = ThreadPoolExecutor(max_workers=workers)
    try:
        with open(items_path, "a", encoding="utf-8") as f:
            futures = [pool.submit(one, *job) for job in todo]
            for i, fut in enumerate(as_completed(futures), len(done) + 1):
                it = fut.result()
                with write_lock:
                    f.write(json.dumps(it, ensure_ascii=False) + "\n")
                    f.flush()
                fin = it["final"]
                print(f"  {i}/{n_all} {it['id']} L{it['level']} s{it['seed']}: revisions {it['revisions']}, "
                      f"accepted {it['final_accepted']}, {fin['syllables'] if fin else '-'}/{it['target']} syll, "
                      f"{it['time_total_s']:.1f}s", flush=True)
    except BaseException:
        pool.shutdown(wait=False, cancel_futures=True)  # do not run the queued items; --resume redoes them
        raise
    pool.shutdown()
    if client:
        client.close()
    print(f"wrote {items_path}")
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Generate with a prompt variant and the repair loop (resumable).")
    ap.add_argument("--variant", choices=sorted(VARIANTS), default="v1")
    ap.add_argument("--lang", choices=("de", "fr"), default="de")
    ap.add_argument("--split", choices=("dev", "test"), default="dev")
    ap.add_argument("--allow-test", action="store_true", help="the test split is for final numbers only")
    ap.add_argument("--levels", type=int, nargs="+", default=list(LEVELS))
    ap.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    ap.add_argument("--ids", nargs="+", help="FLEURS sentence ids")
    ap.add_argument("--exclude-gonogo", action="store_true", help="skip the 50 go/no-go sentences (German dev)")
    ap.add_argument("--limit", type=int, help="first N sentences in file order")
    ap.add_argument("--no-repair", action="store_true")
    ap.add_argument("--quantisation", help="quantisation of the served model, recorded in config.json")
    ap.add_argument("--mock", action="store_true", help="dry run without an LLM")
    ap.add_argument("--device", default=None, help="NLI device (default: cuda, then mps, then cpu)")
    ap.add_argument("--workers", type=int, default=1, help="items generated at the same time")
    ap.add_argument("--out", type=Path, help="run directory (default: a new one under results/raw/)")
    ap.add_argument("--resume", action="store_true", help="continue the run in --out")
    args = ap.parse_args(argv)

    if args.split == "test" and not args.allow_test:
        sys.exit("the test split is for final numbers only; pass --allow-test to use it")
    if not args.mock and not args.quantisation:
        sys.exit("--quantisation is required, so the run records what was served")
    if args.resume and not args.out:
        sys.exit("--resume needs --out")
    data = Path(f"data/fleurs_{args.lang}_{args.split}.jsonl")
    records = list(read_jsonl(data, SentenceRecord))
    selection = "all sentences in file order"
    if args.ids:
        records = [r for r in records if r.id in set(args.ids)]
        selection = f"ids {' '.join(args.ids)}"
    if args.exclude_gonogo:
        if (args.lang, args.split) != ("de", "dev"):
            sys.exit("the go/no-go sentences are German dev sentences")
        excluded = set(gonogo_ids())
        records = [r for r in records if r.id not in excluded]
        selection += ", excluding the go/no-go sentences"
    if args.limit:
        records = records[: args.limit]
        selection += f", first {args.limit}"
    if not records:
        sys.exit("no sentences selected")
    started = datetime.now(timezone.utc)
    name = f"{started:%Y%m%dT%H%M%SZ}_loop_{args.variant}_{args.lang}_{args.split}" + ("_mock" if args.mock else "")
    run(records, variant=args.variant, lang=args.lang, split=args.split, levels=args.levels, seeds=args.seeds,
        out=args.out or Path("results/raw") / name, kind="loop run", selection=selection, data=data,
        quantisation=args.quantisation, mock=args.mock, repair=not args.no_repair, resume=args.resume,
        workers=args.workers, device=args.device)


if __name__ == "__main__":
    main()
