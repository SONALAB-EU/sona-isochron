"""Phase 2 pilot: prompt variants with the repair loop, on German dev sentences.

Generation only (Apertus server running); the final meaning judge runs later,
separately (isochron.judge). One run per variant. Each item logs round 0 and
every revision, so both conditions come from the same run:
- without the loop: the closest round-0 candidate in syllables;
- with the loop:    the best candidate over all rounds (see isochron.repair).

Variants (prompt files in src/isochron/prompts/):
- v1   shorten_syllables_v1  syllable target T = level % of the input syllables
- v2a  shorten_facts_v2a     list the facts first, then candidates at T syllables
- v2b  shorten_words_v2b     source word count + word target (level % of the words)
- v2c  shorten_graded_v2c    4 candidates at level +15/+10/+5/+0 points of the
                             input syllables, capped at 100 %
Fit and closest selection always use T in syllables.

Pilot items: random.Random(0).sample of the German dev sentences outside the
go/no-go 50 (file order), 30 of them.

    uv run python -m isochron.pilot --variant v2a --quantisation Q4_K_M
    uv run python -m isochron.pilot --variant v1 --mock --limit 2      (dry run, no LLM)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from isochron.config import ConfigError, LLMConfig
from isochron.gonogo import gonogo_ids
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
DATA = Path("data/fleurs_de_dev.jsonl")
N_PILOT, PILOT_SEED = 30, 0
LEVELS = (90, 80)
GRADES = (15, 10, 5, 0)
ROUND_SEED_STEP = 1000  # round r of an item with seed s is generated with seed s + 1000 * r


def tuning_pool(path: Path = DATA) -> list[SentenceRecord]:
    """The German dev sentences outside the go/no-go 50, in file order."""
    excluded = set(gonogo_ids(path))
    return [r for r in read_jsonl(path, SentenceRecord) if r.id not in excluded]


def pilot_ids(path: Path = DATA) -> list[str]:
    rest = tuning_pool(path)
    picked = {r.id for r in random.Random(PILOT_SEED).sample(rest, N_PILOT)}
    return [r.id for r in rest if r.id in picked]


def selection_text(path: Path = DATA) -> str:
    return (f"random.Random({PILOT_SEED}).sample of {N_PILOT} of the {len(tuning_pool(path))} German dev "
            "sentences outside the go/no-go 50, kept in file order")


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


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Phase 2 pilot generation.")
    ap.add_argument("--variant", choices=sorted(VARIANTS), required=True)
    ap.add_argument("--levels", type=int, nargs="+", default=list(LEVELS))
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--limit", type=int, help="first N pilot sentences only")
    ap.add_argument("--no-repair", action="store_true")
    ap.add_argument("--quantisation", help="quantisation of the served model, recorded in config.json")
    ap.add_argument("--mock", action="store_true", help="dry run without an LLM")
    ap.add_argument("--device", default=None, help="NLI device for the loop (default: mps if available)")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    if not args.mock and not args.quantisation:
        sys.exit("--quantisation is required, so the run records what was served")

    lang = "de"
    ids = set(pilot_ids())
    records = [r for r in read_jsonl(DATA, SentenceRecord) if r.id in ids][: args.limit]
    counter = default_counter()
    prompt, revise = Prompt.load(VARIANTS[args.variant]), Prompt.load(REVISE)

    client, backend, extra = None, {"type": "none (mock)"}, {}
    if not args.mock:
        try:
            config = LLMConfig.from_env()
        except ConfigError as e:
            sys.exit(f"{e}; use --mock for a dry run")
        check_endpoint(config)
        backend = backend_info(config)
        if backend["type"] == "llama.cpp llama-server":
            extra = {"samplers": LLAMACPP_SAMPLERS}
        client = ChatClient(config, timeout=180)

    from isochron.metrics.meaning import NLI

    nli = NLI(device=args.device)
    started = datetime.now(timezone.utc)
    name = f"{started:%Y%m%dT%H%M%SZ}_pilot_{args.variant}_de_dev" + ("_mock" if args.mock else "")
    out = args.out or Path("results/raw") / name
    out.mkdir(parents=True, exist_ok=False)
    cfg = {
        "date": started.isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "phase": 2,
        "kind": "pilot",
        "variant": args.variant,
        "lang": lang,
        "split": "dev",
        "levels": args.levels,
        "seeds": args.seeds,
        "repair": not args.no_repair,
        "max_revisions": MAX_REVISIONS,
        "round_seed": f"item seed + {ROUND_SEED_STEP} × round (round 0 uses the item seed)",
        "mock": args.mock,
        "model": "mock (word-prefix cuts, no LLM)" if args.mock else config.name,
        "quantisation": "n/a (mock)" if args.mock else args.quantisation,
        "endpoint": "none (mock)" if args.mock else config.base_url,
        "backend": backend,
        "generation": {**GENERATION, **extra},
        "prompt": {"name": prompt.name, "sha256": prompt.sha256},
        "revise_prompt": {"name": revise.name, "sha256": revise.sha256},
        "length_counter": {"syllables": counter_description(counter), "counter": counter},
        "nli": nli.describe(),
        "loop_uses": "syllable counter and NLI only; never the final judge",
        "data": {"file": str(DATA), "sha256": hashlib.sha256(DATA.read_bytes()).hexdigest()},
        "items": {"selection": selection_text() + (f", first {args.limit}" if args.limit else ""),
                  "n": len(records), "ids": [r.id for r in records]},
        "tts": "none",
    }
    (out / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def count(text: str, unit: str) -> int:
        return length(text, unit, lang, counter)

    n = len(records) * len(args.levels) * len(args.seeds)
    print(f"{args.variant}: {n} items ({len(records)} sentences × {len(args.levels)} levels × {len(args.seeds)} seeds) → {out}")
    with open(out / "items.jsonl", "w", encoding="utf-8") as f:
        for seed in args.seeds:
            for r in records:
                for level in args.levels:
                    text, targets = first_prompt(args.variant, prompt, lang, level, r.ref_text, counter)

                    def generate(p: str, rnd: int, seed: int = seed) -> tuple[str, dict[str, Any]]:
                        s = seed + ROUND_SEED_STEP * rnd
                        t0 = time.monotonic()
                        if args.mock:
                            raw = mock_answer(r.ref_text, "syllables", lang, targets["target"], s, counter)
                            return raw, {"seed": s, "latency_s": round(time.monotonic() - t0, 3), "finish_reason": "stop"}
                        res = client.chat([{"role": "user", "content": p}], seed=s, **GENERATION, **extra)
                        return res.text, {"seed": s, "latency_s": round(time.monotonic() - t0, 3),
                                          "finish_reason": res.finish_reason, "usage": res.usage,
                                          "timings": res.raw.get("timings")}

                    log = run_loop(text, r.ref_text, lang, targets["target"], generate, nli.meaning, count, revise,
                                   repair=not args.no_repair)
                    f.write(json.dumps({"id": r.id, "level": level, "seed": seed, "input": r.ref_text, **targets, **log},
                                       ensure_ascii=False) + "\n")
                    f.flush()
                    fin = log["final"]
                    print(f"  {r.id} L{level} s{seed}: revisions {log['revisions']}, accepted {log['final_accepted']}, "
                          f"{fin['syllables'] if fin else '-'}/{targets['target']} syll, {log['time_total_s']:.1f}s", flush=True)
    if client:
        client.close()
    print(f"wrote {out / 'items.jsonl'}")


if __name__ == "__main__":
    main()
