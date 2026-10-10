"""Phase 2 pilot: prompt variants with the repair loop, on German dev sentences.

Generation only (Apertus server running); the final meaning judge runs later,
separately (isochron.judge). One run per variant, through isochron.loop_run,
which documents the variants, the logging and both conditions (without the
loop: the closest round-0 candidate; with the loop: the best over all rounds).

Pilot items: random.Random(0).sample of the German dev sentences outside the
go/no-go 50 (file order), 30 of them.

    uv run python -m isochron.pilot --variant v2a --quantisation Q4_K_M
    uv run python -m isochron.pilot --variant v1 --mock --limit 2      (dry run, no LLM)
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

from isochron.gonogo import gonogo_ids
from isochron.loop_run import REVISE, ROUND_SEED_STEP, VARIANTS, first_prompt, graded_targets, run  # noqa: F401
from isochron.schema import SentenceRecord, read_jsonl

DATA = Path("data/fleurs_de_dev.jsonl")
N_PILOT, PILOT_SEED = 30, 0
LEVELS = (90, 80)


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


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Phase 2 pilot generation.")
    ap.add_argument("--variant", choices=sorted(VARIANTS), required=True)
    ap.add_argument("--levels", type=int, nargs="+", default=list(LEVELS))
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--limit", type=int, help="first N pilot sentences only")
    ap.add_argument("--no-repair", action="store_true")
    ap.add_argument("--quantisation", help="quantisation of the served model, recorded in config.json")
    ap.add_argument("--mock", action="store_true", help="dry run without an LLM")
    ap.add_argument("--device", default=None, help="NLI device for the loop (default: cuda, then mps, then cpu)")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    if not args.mock and not args.quantisation:
        sys.exit("--quantisation is required, so the run records what was served")

    ids = set(pilot_ids())
    records = [r for r in read_jsonl(DATA, SentenceRecord) if r.id in ids][: args.limit]
    started = datetime.now(timezone.utc)
    name = f"{started:%Y%m%dT%H%M%SZ}_pilot_{args.variant}_de_dev" + ("_mock" if args.mock else "")
    run(records, variant=args.variant, lang="de", split="dev", levels=args.levels, seeds=args.seeds,
        out=args.out or Path("results/raw") / name, kind="pilot",
        selection=selection_text() + (f", first {args.limit}" if args.limit else ""), data=DATA,
        quantisation=args.quantisation, mock=args.mock, repair=not args.no_repair, device=args.device)


if __name__ == "__main__":
    main()
