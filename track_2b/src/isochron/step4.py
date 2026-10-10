"""Step 4: translate an English sentence to a length budget (EN → DE, EN → FR).

Systems (docs/eval_protocol.md, step 4), for every sentence, target language and seed:
- (a) plain: one translation without a length instruction (translate_plain_v1).
- (b) one step: translate to the budget in one request, 4 candidates (translate_budget_<unit>_v1); the
  candidate closest to the budget in its unit is chosen. Step 3 has not been run, so (b) and (c) use the
  selection step 2 uses (closest of 4), as fixed before any test run.
- (c) translate, then shorten: (a), kept unchanged if it is at most 1.10 × the budget; otherwise
  shortened with our method, prompt v1 and the repair loop, in the budget's unit (shorten_<unit>_v1 and
  revise_v1 or revise_chars_v1; the loop's NLI compares with (a)).
Budgets, each ±10 %:
- isometric: the English source's characters without spaces (the IWSLT 2022 definition); unit chars.
- isosyllabic: the English source's syllables × target rate ÷ English rate (Pellegrino et al. 2011:
  EN 6.19, DE 5.97, FR 7.18, IT 6.99 syllables per second), rounded half up; unit syllables.

Generation only: scoring (lengths, NLI against the reference and the source, intervals) is
isochron.step4_report. Every request uses the generation settings of step 2 and its own seed: (a) and
(b) the item seed, (c) item seed + 1000 × round. Resumable and concurrent like isochron.loop_run.

    uv run python -m isochron.step4 --langs de fr --split dev --exclude-gonogo --limit 5 --seeds 0 --quantisation Q4_K_M --out results/raw/step4_smoke --resume
    uv run python -m isochron.step4 --langs de --split dev --exclude-gonogo --limit 2 --mock      (dry run, no LLM)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from isochron.candidates import N_CANDIDATES, parse_candidates, select
from isochron.config import ConfigError, LLMConfig
from isochron.gonogo import gonogo_ids
from isochron.judge import first_object
from isochron.language import check as check_language
from isochron.language import describe as describe_language
from isochron.llm import ChatClient
from isochron.loop_run import ROUND_SEED_STEP, done_items, write_json
from isochron.metrics.length import counter_description, default_counter, length
from isochron.prompts import Prompt
from isochron.provenance import git_commit
from isochron.repair import MAX_REVISIONS, run_loop
from isochron.run import GENERATION, LLAMACPP_SAMPLERS, backend_info, check_endpoint, mock_answer
from isochron.schema import SentenceRecord, read_jsonl

RATES = {"en": 6.19, "de": 5.97, "fr": 7.18, "it": 6.99}  # syllables per second, Pellegrino et al. (2011)
BUDGETS = {"isometric": "chars", "isosyllabic": "syllables"}
KEEP_PLAIN = 1.10  # (c) keeps (a) when it is at most this times the budget
PROMPTS = {
    "plain": "translate_plain_v1",
    "budget_chars": "translate_budget_chars_v1",
    "budget_syllables": "translate_budget_syllables_v1",
    "shorten_chars": "shorten_chars_v1",
    "shorten_syllables": "shorten_syllables_v1",
    "revise_chars": "revise_chars_v1",
    "revise_syllables": "revise_v1",
}
SAME_RUN = ("kind", "langs", "split", "seeds", "budgets", "max_revisions", "round_seed", "mock", "model",
            "quantisation", "generation", "prompts", "length_counter", "nli_model", "language_check", "data",
            "items")
PLAIN_TRIES = 3


def budget(kind: str, source: str, lang: str, counter: str) -> int:
    """The target length of the translation, in the budget's unit."""
    if kind == "isometric":
        return length(source, "chars", "en", counter)
    syllables = length(source, "syllables", "en", counter)
    return int(syllables * RATES[lang] / RATES["en"] + 0.5)


def parse_translation(raw: str) -> tuple[str | None, str | None]:
    def check(obj: dict) -> str | None:
        t = obj.get("translation")
        return None if isinstance(t, str) and t.strip() else 'no non-empty "translation" string'

    obj, error = first_object(raw, check)
    return (obj["translation"].strip(), None) if obj else (None, error)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Step 4: translate to a length budget (generation only).")
    ap.add_argument("--langs", nargs="+", choices=("de", "fr", "it"), default=["de", "fr"])
    ap.add_argument("--split", choices=("dev", "test"), default="dev")
    ap.add_argument("--allow-test", action="store_true", help="the test split is for final numbers only")
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--budgets", nargs="+", choices=sorted(BUDGETS), default=sorted(BUDGETS))
    ap.add_argument("--ids", nargs="+", help="FLEURS sentence ids")
    ap.add_argument("--exclude-gonogo", action="store_true", help="skip the ids of the 50 go/no-go sentences")
    ap.add_argument("--limit", type=int, help="first N sentences per language, in file order")
    ap.add_argument("--quantisation", help="quantisation of the served model, recorded in config.json")
    ap.add_argument("--mock", action="store_true", help="dry run without an LLM: the reference stands in for (a)")
    ap.add_argument("--device", default=None, help="NLI device for the loop (default: cuda, then mps, then cpu)")
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
    excluded = set(gonogo_ids()) if args.exclude_gonogo else set()
    data = {lang: Path(f"data/fleurs_{lang}_{args.split}.jsonl") for lang in args.langs}
    records: dict[str, list[SentenceRecord]] = {}
    for lang, path in data.items():
        recs = [r for r in read_jsonl(path, SentenceRecord) if r.id not in excluded]
        if args.ids:
            recs = [r for r in recs if r.id in set(args.ids)]
        records[lang] = recs[: args.limit]
    if not any(records.values()):
        sys.exit("no sentences selected")
    selection = ("ids " + " ".join(args.ids) if args.ids else "all sentences in file order") \
        + (", excluding the go/no-go ids" if args.exclude_gonogo else "") \
        + (f", first {args.limit} per language" if args.limit else "")

    counter = default_counter()
    prompts = {k: Prompt.load(v) for k, v in PROMPTS.items()}
    client, backend, extra, config = None, {"type": "none (mock)"}, {}, None
    if not args.mock:
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

    nli = NLI(device=args.device)
    started = datetime.now(timezone.utc)
    out = args.out or Path("results/raw") / f"{started:%Y%m%dT%H%M%SZ}_step4_{'_'.join(args.langs)}_{args.split}" \
        f"{'_mock' if args.mock else ''}"
    session = {"started": started.isoformat(timespec="seconds"), "git_commit": git_commit(), "workers": args.workers,
               "endpoint": "none (mock)" if args.mock else config.base_url, "backend": backend, "nli": nli.describe()}
    cfg = {
        "date": session["started"], "git_commit": session["git_commit"], "step": 4, "kind": "step4",
        "task": "translate an English FLEURS sentence to a length budget",
        "langs": args.langs, "split": args.split, "seeds": args.seeds,
        "budgets": {b: BUDGETS[b] for b in args.budgets}, "rates": RATES, "keep_plain": KEEP_PLAIN,
        "selection_b": "closest of 4 candidates in the budget's unit",
        "shorten_c": "prompt v1 with the repair loop in the budget's unit; (a) kept if at most 1.10 × the budget",
        "max_revisions": MAX_REVISIONS,
        "round_seed": f"(a), (b): item seed; (c): item seed + {ROUND_SEED_STEP} × round",
        "mock": args.mock, "model": "mock (reference and prefix cuts, no LLM)" if args.mock else config.name,
        "quantisation": "n/a (mock)" if args.mock else args.quantisation,
        "endpoint": session["endpoint"], "backend": backend, "generation": {**GENERATION, **extra},
        "prompts": {k: {"name": p.name, "sha256": p.sha256} for k, p in prompts.items()},
        "length_counter": {"syllables": counter_description(counter), "counter": counter},
        "nli": nli.describe(), "nli_model": f"{MODEL_ID} @ {REVISION}", "language_check": describe_language(),
        "data": {lang: {"file": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for lang, p in data.items()},
        "items": {"selection": selection, "n": {lang: len(r) for lang, r in records.items()},
                  "ids": {lang: [r.id for r in rs] for lang, rs in records.items()}},
        "tts": "none", "workers": args.workers, "sessions": [session],
    }
    if (out / "config.json").exists():
        if not args.resume:
            sys.exit(f"{out} already holds a run; pass --resume to continue it")
        old = json.loads((out / "config.json").read_text(encoding="utf-8"))
        differ = [k for k in SAME_RUN if old.get(k) != cfg.get(k)]
        if differ:
            sys.exit(f"{out} holds a different run; these settings differ: {', '.join(differ)}")
        old.setdefault("sessions", []).append(session)
        cfg = old
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "config.json", cfg)

    items_path = out / "items.jsonl"
    done = {(i, lvl, s) for i, lvl, s in done_items_step4(items_path)}
    todo = [(lang, r, seed) for seed in args.seeds for lang in args.langs for r in records[lang]
            if (r.id, lang, seed) not in done]
    n_all = sum(len(r) for r in records.values()) * len(args.seeds)
    print(f"step 4: {n_all} items, {len(done)} done, {len(todo)} to go, {args.workers} worker(s) → {out}", flush=True)

    nli_lock, write_lock = threading.Lock(), threading.Lock()

    def meaning(sources, outputs):
        with nli_lock:
            return nli.meaning(sources, outputs)

    def call(prompt: str, seed: int, mock_text: str, unit: str, lang: str, goal: int) -> tuple[str, dict[str, Any]]:
        t0 = time.monotonic()
        if args.mock:
            raw = mock_answer(mock_text, unit, lang, goal, seed, counter) if unit else \
                json.dumps({"translation": mock_text}, ensure_ascii=False)
            return raw, {"seed": seed, "latency_s": round(time.monotonic() - t0, 3), "finish_reason": "stop"}
        res = client.chat([{"role": "user", "content": prompt}], seed=seed, **GENERATION, **extra)
        return res.text, {"seed": seed, "latency_s": round(time.monotonic() - t0, 3), "finish_reason": res.finish_reason,
                          "usage": res.usage, "timings": res.raw.get("timings")}

    def one(lang: str, r: SentenceRecord, seed: int) -> dict[str, Any]:
        t_item = time.monotonic()
        item: dict[str, Any] = {"id": r.id, "lang": lang, "seed": seed, "source": r.src_text, "reference": r.ref_text}
        # (a) plain translation; an unparsable answer is asked again with the next seed
        tries = []
        plain = None
        for k in range(PLAIN_TRIES):
            prompt = prompts["plain"].render(lang, None, r.src_text)
            raw, info = call(prompt, seed + ROUND_SEED_STEP * k, r.ref_text, "", lang, 0)
            text, error = parse_translation(raw)
            tries.append({"raw": raw, "parse_error": error, "llm": info})
            if text:
                plain = text
                break
        item["a"] = {"text": plain, "tries": tries,
                     "language": asdict(check_language(plain, lang)) if plain else None}
        item["budgets"] = {}
        for kind in args.budgets:
            unit = BUDGETS[kind]
            goal = budget(kind, r.src_text, lang, counter)
            entry: dict[str, Any] = {"unit": unit, "target": goal}
            # (b) one step, closest of 4
            prompt = prompts[f"budget_{unit}"].render(lang, goal, r.src_text)
            raw, info = call(prompt, seed, r.ref_text, unit, lang, goal)
            cands, error = parse_candidates(raw)
            idx = select(cands, "closest", lambda t: length(t, unit, lang, counter), goal)
            entry["b"] = {"raw": raw, "parse_error": error, "candidates": cands, "llm": info,
                          "chosen": idx, "text": cands[idx] if idx is not None else None}
            # (c) translate, then shorten
            if plain is None:
                entry["c"] = {"kept_plain": False, "text": None, "loop": None}
            elif length(plain, unit, lang, counter) <= KEEP_PLAIN * goal:
                entry["c"] = {"kept_plain": True, "text": plain, "loop": None}
            else:
                def generate(p: str, rnd: int, unit: str = unit, goal: int = goal) -> tuple[str, dict[str, Any]]:
                    return call(p, seed + ROUND_SEED_STEP * rnd, plain, unit, lang, goal)

                log = run_loop(prompts[f"shorten_{unit}"].render(lang, goal, plain), plain, lang, goal, generate,
                               meaning, lambda t, u: length(t, u, lang, counter), prompts[f"revise_{unit}"],
                               check_language, unit=unit)
                entry["c"] = {"kept_plain": False, "text": log["final"]["text"] if log["final"] else None, "loop": log}
            item["budgets"][kind] = entry
        item["time_s"] = round(time.monotonic() - t_item, 3)
        return item

    pool = ThreadPoolExecutor(max_workers=args.workers)
    try:
        with open(items_path, "a", encoding="utf-8") as f:
            futures = [pool.submit(one, *job) for job in todo]
            for i, fut in enumerate(as_completed(futures), len(done) + 1):
                it = fut.result()
                with write_lock:
                    f.write(json.dumps(it, ensure_ascii=False) + "\n")
                    f.flush()
                print(f"  {i}/{n_all} {it['lang']} {it['id']} s{it['seed']}: "
                      + ", ".join(f"{k} T={v['target']} c {'kept (a)' if v['c']['kept_plain'] else 'shortened'}"
                                  for k, v in it["budgets"].items())
                      + f", {it['time_s']:.1f}s", flush=True)
    except BaseException:
        pool.shutdown(wait=False, cancel_futures=True)
        raise
    pool.shutdown()
    if client:
        client.close()
    print(f"wrote {items_path}")


def done_items_step4(path: Path) -> set[tuple[str, str, int]]:
    """(id, lang, seed) of the finished items; a cut-off last line is removed (as in loop_run)."""
    if not path.exists():
        return set()
    good, keys = [], set()
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        try:
            it = json.loads(line)
            keys.add((str(it["id"]), it["lang"], int(it["seed"])))
        except (json.JSONDecodeError, KeyError):
            print(f"dropping an incomplete line from {path}", file=sys.stderr)
            continue
        good.append(line if line.endswith("\n") else line + "\n")
    path.write_text("".join(good), encoding="utf-8")
    return keys


if __name__ == "__main__":
    main()
