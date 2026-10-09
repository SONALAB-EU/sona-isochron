"""Smoke-test checks on a scored run, before any larger run is started.

1. Every response parses as JSON with exactly 4 candidates.
2. Every candidate is non-empty and in the run's language (function-word
   vote over de / en / fr / it; ties and texts without function words fail).
3. The NLI scored every (input, selected output) pair, in both directions.

Prints every candidate for reading by eye, then the three verdicts. Exit
status 1 if any check fails. Run from track_2b/:

    uv run python -m isochron.checks results/raw/<run>
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from isochron.candidates import N_CANDIDATES, parse_candidates

FUNCTION_WORDS = {
    "de": set("der die das und ist ein eine einen einem einer nicht mit von zu den im für auf sich des dem auch es an "
              "wird werden wurde wurden sind als bei nach aus oder wie dass sie er hat haben zum zur über vom".split()),
    "en": set("the and is of to in a that it for on with as was are be by this from or an which have has were not "
              "its at".split()),
    "fr": set("le la les et est de des du un une en que qui dans pour pas sur au aux il elle ce sont par avec "
              "ne se son sa ses".split()),
    "it": set("il lo gli e è di del della dei delle che un una per non con sono nel nella alla da si".split()),
}


def guess_language(text: str) -> str:
    words = re.findall(r"[^\W\d_]+", text.lower())
    votes = {lang: sum(w in fw for w in words) for lang, fw in FUNCTION_WORDS.items()}
    best = max(votes.values())
    winners = [lang for lang, v in votes.items() if v == best]
    return winners[0] if best > 0 and len(winners) == 1 else "unknown"


def main(argv: list[str] | None = None) -> int:
    run = Path((argv or sys.argv[1:])[0])
    cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in open(run / "candidates.jsonl", encoding="utf-8") if line.strip()]
    scored = [json.loads(line) for line in open(run / "scores.jsonl", encoding="utf-8") if line.strip()]
    lang = cfg["lang"]

    parse_failures, language_failures = [], []
    for row in rows:
        cands, error = parse_candidates(row["raw"])
        key = f"{row['id']} level {row['level']} seed {row['seed']}"
        print(f"\n[{key}] target {row['target']} {cfg['unit']}")
        if error or len(cands) != N_CANDIDATES:
            parse_failures.append(f"{key}: {error}")
            print(f"  PARSE: {error} | raw: {row['raw'][:300]!r}")
        for i, c in enumerate(cands):
            guess = guess_language(c) if c.strip() else "empty"
            if guess != lang:
                language_failures.append(f"{key} candidate {i}: {guess}: {c!r}")
            print(f"  {i} [{guess}] {c}")

    unscored = [f"{r['id']} level {r['level']} seed {r['seed']} {r['selection']}" for r in scored
                if r["output"] and not (r.get("nli") and r["nli"]["forward"] and r["nli"]["backward"])]
    checks = [
        (f"every response parses as JSON with {N_CANDIDATES} candidates ({len(rows)} responses)", parse_failures),
        (f"every candidate is non-empty and in language '{lang}'", language_failures),
        (f"NLI scored every pair in both directions ({sum(1 for r in scored if r['output'])} pairs)", unscored),
    ]
    print()
    for name, failures in checks:
        print(f"{'PASS' if not failures else 'FAIL'}: {name}")
        for f in failures:
            print(f"    {f}")
    return 1 if any(f for _, f in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
