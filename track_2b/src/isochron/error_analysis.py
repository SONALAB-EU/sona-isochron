"""Error analysis of the go/no-go outputs (closest candidate). Analysis only, no re-scoring.

- Histogram of achieved ÷ target syllables over the outputs with a usable answer.
- 30 outputs the NLI flags as dropped, drawn with seed 0 after sorting by
  (id, seed), each classified by what was lost. The classifications come
  from independent annotators (LLM agents, not native speakers), stored in a
  JSON file. A category counts for a case when at least 2 of the 3 annotators
  chose it.

    uv run python -m isochron.error_analysis cases          (writes the 30 cases as JSON)
    uv run python -m isochron.error_analysis report ANNOTATIONS.json
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import numpy as np

from isochron.provenance import git_commit

RUN = Path("results/raw/20261009T141318Z_step2_de_dev_syllables")
CASES = Path("results/gonogo_error_cases.json")
OUT = Path("results/gonogo_error_analysis.md")
CATEGORIES = ("number", "name", "date", "clause", "qualifier", "other", "none")
N_CASES, SEED = 30, 0
BINS = np.round(np.arange(0.40, 1.31, 0.05), 2)


def closest_usable(run: Path) -> list[dict]:
    rows = [json.loads(line) for line in open(run / "scores.jsonl", encoding="utf-8")]
    return [r for r in rows if r["selection"] == "closest" and r["output"]]


def draw_cases(rows: list[dict]) -> list[dict]:
    dropped = sorted((r for r in rows if r["nli"]["dropped"]), key=lambda r: (int(r["id"]), r["seed"]))
    picked = random.Random(SEED).sample(dropped, N_CASES)
    return [
        {"case": i + 1, "id": r["id"], "seed": r["seed"], "input": r["input"], "output": r["output"],
         "target": r["target"]["syllables"], "syllables": r["output_len"]["syllables"],
         "nli_added": r["nli"]["added"]}
        for i, r in enumerate(sorted(picked, key=lambda r: (int(r["id"]), r["seed"])))
    ], len(dropped)


def histogram(rows: list[dict]) -> list[str]:
    ratios = np.array([r["output_len"]["syllables"] / r["target"]["syllables"] for r in rows])
    edges = list(BINS) + [np.inf]
    counts = np.histogram(np.clip(ratios, BINS[0] - 1, None), bins=[-np.inf] + edges)[0]
    labels = [f"< {BINS[0]:.2f}"] + [f"{a:.2f}–{b:.2f}" for a, b in zip(BINS[:-1], BINS[1:])] + [f"≥ {BINS[-1]:.2f}"]
    out = ["| Achieved ÷ target | Outputs | |", "|------------------:|--------:|-|"]
    for label, c in zip(labels, counts):
        lo = float(label.split("–")[0]) if "–" in label else None
        band = " ← fit band" if lo is not None and 0.9 <= lo < 1.1 else ""
        out.append(f"| {label} | {c} | {'█' * int(c)}{band} |")
    q = np.percentile(ratios, [25, 50, 75])
    out += ["", f"n = {len(ratios)}; median {q[1]:.2f} (quartiles {q[0]:.2f}–{q[2]:.2f}); "
            f"below 0.90: {int((ratios < 0.9).sum())}, within 0.90–1.10: "
            f"{int(((ratios >= 0.9) & (ratios <= 1.1)).sum())}, above 1.10: {int((ratios > 1.1).sum())}. "
            "(Fit uses integer arithmetic, so outputs exactly on 0.90 or 1.10 count as fits.)"]
    return out


def report(annotations_path: Path) -> None:
    rows = closest_usable(RUN)
    cases, n_dropped = draw_cases(rows)
    ann = json.loads(annotations_path.read_text(encoding="utf-8"))
    annotators = sorted(ann["annotators"])
    labels = {a: {int(c["case"]): c for c in ann["annotators"][a]} for a in annotators}

    majority, per_case = Counter(), []
    for case in cases:
        k = case["case"]
        chosen = {cat: sum(cat in labels[a][k]["lost"] for a in annotators) for cat in CATEGORIES}
        maj = [cat for cat, v in chosen.items() if v >= 2]
        majority.update(maj)
        notes = " / ".join(labels[a][k]["what"] for a in annotators)
        per_case.append((case, maj, notes))

    agree = []
    for cat in CATEGORIES:
        pairs = [
            sum((cat in labels[a][c["case"]]["lost"]) == (cat in labels[b][c["case"]]["lost"]) for c in cases) / len(cases)
            for a, b in combinations(annotators, 2)
        ]
        agree.append((cat, np.mean(pairs)))

    out = [
        "# Error analysis of the go/no-go outputs (closest candidate)",
        "",
        "Analysis only: the go/no-go result is final and is not re-scored.",
        "",
        f"- Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        f"- Git commit: {git_commit()}",
        f"- Run: `{RUN}` (Apertus 1.5 8B Q4_K_M, prompt v1, seeds 0/1/2, level 80 %); "
        "model, endpoint and generation settings as in `results/gonogo_step2_de.md`; TTS: none",
        f"- n: {len(rows)} outputs with a usable answer; {n_dropped} flagged as dropped by the NLI; "
        f"{N_CASES} of those drawn with `random.Random({SEED})` after sorting by (id, seed)",
        f"- Annotators: {', '.join(annotators)}. {ann['who']}",
        "",
        "## Achieved ÷ target syllables",
        "",
        *histogram(rows),
        "",
        f"## What was lost in {N_CASES} dropped cases",
        "",
        "A case can lose several kinds of information. A category counts when at least 2 of the 3 annotators",
        "chose it; `none` means the annotators found nothing lost (an NLI false alarm).",
        "",
        "| Category | Cases (majority) | Share of the 30 | Pairwise agreement |",
        "|----------|-----------------:|----------------:|-------------------:|",
        *[f"| {cat} | {majority[cat]} | {100 * majority[cat] / N_CASES:.0f} % | {100 * a:.0f} % |" for cat, a in agree],
        "",
        "Definitions given to the annotators: " + ann["definitions"],
        "",
        "## Cases",
        "",
        "| # | Id | Seed | Target | Syll. | Lost (majority) | What was lost (one note per annotator) |",
        "|--:|---:|-----:|-------:|------:|-----------------|----------------------------------------|",
        *[f"| {c['case']} | {c['id']} | {c['seed']} | {c['target']} | {c['syllables']} | {', '.join(m) or '–'} | {n} |"
          for c, m, n in per_case],
    ]
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {OUT.resolve()}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Error analysis of the go/no-go outputs.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("cases")
    rep = sub.add_parser("report")
    rep.add_argument("annotations", type=Path)
    args = ap.parse_args()
    if args.cmd == "cases":
        cases, n_dropped = draw_cases(closest_usable(RUN))
        CASES.write_text(json.dumps(cases, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{n_dropped} dropped outputs; wrote {len(cases)} cases to {CASES.resolve()}")
        print("\n".join(histogram(closest_usable(RUN))))
    else:
        report(args.annotations)


if __name__ == "__main__":
    main()
