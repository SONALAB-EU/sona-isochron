"""NLI sanity suite: does the meaning metric judge hand-made control pairs right?

data/nli_controls.jsonl holds 20 German and 20 French FLEURS train sentences,
each paired with itself and with four variants written by hand. A pair counts
as correct when the NLI flags match its control type:

    identity, paraphrase   kept
    clause_deleted         dropped and not added
    clause_inserted        added and not dropped
    negation               not kept

Prints accuracy per control type, writes results/nli_sanity.md and exits with
status 1 if any type scores below 80 %. Run from track_2b/:

    uv run python -m isochron.metrics.nli_sanity
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from isochron.metrics.meaning import NLI, Meaning
from isochron.provenance import git_commit
from isochron.schema import ControlPair, read_jsonl

EXPECTED: dict[str, Callable[[Meaning], bool]] = {
    "identity": lambda m: m.kept,
    "paraphrase": lambda m: m.kept,
    "clause_deleted": lambda m: m.dropped and not m.added,
    "clause_inserted": lambda m: m.added and not m.dropped,
    "negation": lambda m: not m.kept,
}
EXPECTED_TEXT = {
    "identity": "kept",
    "paraphrase": "kept",
    "clause_deleted": "dropped, not added",
    "clause_inserted": "added, not dropped",
    "negation": "not kept",
}
THRESHOLD = 0.80


def pct(k: int, n: int) -> str:
    return f"{100 * k / n:.0f} % ({k}/{n})"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the NLI sanity suite.")
    ap.add_argument("--data", type=Path, default=Path("data/nli_controls.jsonl"))
    ap.add_argument("--out", type=Path, default=Path("results/nli_sanity.md"))
    ap.add_argument("--device", default=None, help="cpu or mps (default: mps if available)")
    args = ap.parse_args(argv)

    started = datetime.now(timezone.utc)
    pairs = list(read_jsonl(args.data, ControlPair))
    nli = NLI(device=args.device)
    results = nli.meaning([p.source for p in pairs], [p.output for p in pairs])
    correct = [EXPECTED[p.control](m) for p, m in zip(pairs, results)]

    langs = sorted({p.lang for p in pairs})
    table = [
        "| Control | Expected | " + " | ".join(lang.upper() for lang in langs) + " | All |",
        "|---------|----------|" + "---:|" * (len(langs) + 1),
    ]
    failed = []
    print(f"{'control':16s} " + " ".join(f"{lang:>14s}" for lang in langs) + f" {'all':>14s}")
    for control in EXPECTED:
        cells = []
        for lang in (*langs, None):
            ok = [c for p, c in zip(pairs, correct) if p.control == control and lang in (None, p.lang)]
            cells.append(pct(sum(ok), len(ok)))
            if lang is None and sum(ok) < THRESHOLD * len(ok):
                failed.append(control)
        print(f"{control:16s} " + " ".join(f"{c:>14s}" for c in cells))
        table.append(f"| {control} | {EXPECTED_TEXT[control]} | " + " | ".join(cells) + " |")

    wrong = [(p, m) for p, m, c in zip(pairs, results, correct) if not c]
    out = [
        "# NLI sanity suite",
        "",
        f"- Date: {started:%Y-%m-%d %H:%M} UTC",
        f"- Git commit: {git_commit()}",
        f"- NLI model: {nli.describe()}",
        f"- Data: `{args.data}` (SHA-256 `{hashlib.sha256(args.data.read_bytes()).hexdigest()}`), "
        f"{len(pairs)} pairs: {len(pairs) // len(EXPECTED)} FLEURS train sentences × {len(EXPECTED)} control types; "
        "variants written by hand by Claude (AI assistant), not yet reviewed by a native speaker",
        "- LLM, endpoint, TTS: none. Seeds: none (deterministic inference)",
        f"- Pass rule: every control type at least {THRESHOLD:.0%} correct over both languages",
        "",
        f"**Result: {'FAIL: ' + ', '.join(failed) if failed else 'PASS'}**",
        "",
        *table,
        "",
        f"## Pairs judged wrong ({len(wrong)})",
        "",
        "| Id | Source ⇒ output | Output ⇒ source | Output |",
        "|----|-----------------|-----------------|--------|",
        *[f"| {p.id} | {m.forward} | {m.backward} | {p.output} |" for p, m in wrong],
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"\n{'FAIL: ' + ', '.join(failed) if failed else 'PASS'} — wrote {args.out.resolve()}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
