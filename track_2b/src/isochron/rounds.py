"""Step 2 round by round: fit and fit & complete after round 0, 1 and 2 of the repair loop.

Computed from the logged runs only (no new generation, no new judging). "After round k" is the loop's
best candidate after rounds 0 to k, the output the method returns if it stops after round k. An item
accepted earlier keeps its output. Round 0 here is therefore the loop's own pick, which prefers a
candidate the NLI keeps, not the closest round-0 candidate the reports call "without the loop". That
baseline is listed beside it.

- Fit: within ±10 % of the target, in the right language (as in isochron.pilot_report).
- Fit & complete: fit, and the final judge keeps every fact and finds nothing added. The judge scored
  two texts per item, the closest round-0 candidate and the final output. A best candidate after round
  0 or 1 that is neither has no verdict. "Low" counts such a candidate as not complete, "high" as
  complete if it fits.
- Accepted: the loop's own stopping rule (fit, kept by the NLI, right language). "Open" items are not
  accepted yet. "Rate" is the share of the items open before round k that round k accepted.
- Third round, an estimate, not a measurement: round 3 would turn open items into fit & complete
  outputs at round 2's rate. That rate is the round-2 gain in fit & complete ÷ the items open after
  round 1.

Writes RESULT.md (the tables, with how they were made) and RESULT.csv (one row per language, level and
round; read by isochron.figures).

    uv run python -m isochron.rounds RUN_DIR [RUN_DIR ...] --out results/step2_test_rounds
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from isochron.language import check as check_language
from isochron.pilot_report import complete as report_complete
from isochron.pilot_report import rows_for, short
from isochron.provenance import git_commit

ROUNDS = (0, 1, 2)
FIELDS = ("lang", "level", "round", "items", "fit", "fit_pct", "fit_complete_low", "fit_complete_high",
          "fit_complete_low_pct", "fit_complete_high_pct", "accepted", "open", "accepted_rate_pct")


def complete(verdict: dict[str, Any] | None) -> bool:
    return bool(verdict and verdict.get("valid") and verdict.get("recall") == 1 and not verdict.get("added_any"))


def item_states(it: dict[str, Any], judged: dict[str, Any], lang: str) -> list[dict[str, bool]]:
    """Fit, fit & complete (low and high) and accepted after each round, for one logged item."""
    cands = {(c["round"], c["index"]): c for r in it["rounds"] for c in r["candidates"]}
    verdicts = {}
    if it["closest_round0"]:
        verdicts[it["closest_round0"]["text"]] = judged["without"]
    if it["final"]:
        verdicts[it["final"]["text"]] = judged["with"]
    last = len(it["rounds"]) - 1
    states = []
    for k in ROUNDS:
        best = it["rounds"][min(k, last)]["best_after"]
        c = cands[(best["round"], best["index"])] if best else None
        ok = bool(c) and not check_language(c["text"], lang).wrong
        fit = bool(ok and c["hit"])
        known = c is not None and c["text"] in verdicts
        low = fit and known and complete(verdicts[c["text"]])
        states.append({"fit": fit, "low": low, "high": low or (fit and not known),
                       "accepted": bool(ok and c["hit"] and c["kept"])})
    return states


def tally(run: Path) -> tuple[dict, dict[Any, dict[str, int]]]:
    cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
    lang = cfg["lang"]
    judged = {(j["id"], j["level"], j["seed"]): j
              for j in map(json.loads, (run / "judge.jsonl").read_text(encoding="utf-8").splitlines()) if j}
    counts: dict[Any, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for line in (run / "items.jsonl").read_text(encoding="utf-8").splitlines():
        it = json.loads(line)
        for k, s in enumerate(item_states(it, judged[(it["id"], it["level"], it["seed"])], lang)):
            for level in (it["level"], "all"):
                c = counts[level]
                c["items"] += k == 0
                for key in ("fit", "low", "high", "accepted"):
                    c[f"{key}{k}"] += s[key]
    # the last round must be the reports' "with the loop", scored the same way
    _, rows = rows_for(run)
    with_rows = [r for r in rows if r["cond"] == "with"]
    assert counts["all"]["fit2"] == sum(r["fit"] for r in with_rows), "round 2 must equal the final outputs"
    assert counts["all"]["low2"] == counts["all"]["high2"] == sum(report_complete(r) for r in with_rows)
    base = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r["cond"] == "without":
            for level in (r["level"], "all"):
                base[level]["fit"] += r["fit"]
                base[level]["complete"] += report_complete(r)
    for level, b in base.items():
        counts[level]["base_fit"], counts[level]["base_complete"] = b["fit"], b["complete"]
    return cfg, counts


def rows_of(lang: str, counts: dict[Any, dict[str, int]]) -> list[dict[str, Any]]:
    out = []
    for level in (90, 80, 70, 60, "all"):
        c = counts[level]
        n = c["items"]
        for k in ROUNDS:
            before = n if k == 0 else n - c[f"accepted{k - 1}"]
            new = c[f"accepted{k}"] - (c[f"accepted{k - 1}"] if k else 0)
            out.append({"lang": lang, "level": level, "round": k, "items": n, "fit": c[f"fit{k}"],
                        "fit_pct": round(100 * c[f"fit{k}"] / n, 1), "fit_complete_low": c[f"low{k}"],
                        "fit_complete_high": c[f"high{k}"], "fit_complete_low_pct": round(100 * c[f"low{k}"] / n, 1),
                        "fit_complete_high_pct": round(100 * c[f"high{k}"] / n, 1), "accepted": c[f"accepted{k}"],
                        "open": n - c[f"accepted{k}"], "accepted_rate_pct": round(100 * new / before, 1) if before else ""})
    return out


def third_round(counts: dict[str, int]) -> tuple[float, float]:
    """Estimated round-3 gain in fit & complete, in points (low and high), at round 2's rate per open item."""
    n, open1, open2 = counts["items"], counts["items"] - counts["accepted1"], counts["items"] - counts["accepted2"]
    gains = (counts["low2"] - counts["high1"], counts["high2"] - counts["low1"])  # smallest and largest round-2 gain
    return tuple(round(100 * g / open1 * open2 / n, 1) if open1 else 0.0 for g in gains)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("runs", type=Path, nargs="+")
    ap.add_argument("--out", type=Path, default=Path("results/step2_test_rounds"), help="path without extension")
    args = ap.parse_args(argv)
    started = datetime.now(timezone.utc)
    runs = [(run, *tally(run)) for run in args.runs]
    rows = [row for _, cfg, counts in runs for row in rows_of(cfg["lang"], counts)]
    c0 = runs[0][1]
    judge = json.loads((runs[0][0] / "judge_config.json").read_text(encoding="utf-8"))
    md = [
        "# Step 2 on test, round by round (from the logged runs)",
        "",
        f"- Date: {started:%Y-%m-%d %H:%M} UTC",
        f"- Git commit (analysis): {git_commit()}; runs: "
        + ", ".join(f"`{run.name}` ({short(cfg['git_commit'])})" for run, cfg, _ in runs),
        f"- Model: {c0['model']}, quantisation {c0['quantisation']}, backend {c0['backend'].get('build_info')}; "
        "endpoint " + ", ".join(f"{cfg['lang']} {cfg['endpoint']}" for _, cfg, _ in runs),
        f"- Judge (evaluation only): {judge['model']} ({judge['quantisation']}), temperature 0, seed {judge['seed']}",
        "- Items: " + "; ".join(f"{cfg['lang']} test: {cfg['items']['n']} sentences × levels {cfg['levels']} × seeds "
                                f"{cfg['seeds']}" for _, cfg, _ in runs) + "; TTS: none",
        "- No new generation or judging: every number comes from items.jsonl and judge.jsonl of the runs.",
        "",
        "\"After round k\": the loop's best candidate after rounds 0 to k, the output if the method stopped there.",
        "Fit & complete gives low and high values where that candidate had no judge verdict (see",
        "`isochron.rounds`). Round 2 equals the reports' \"with the loop\". The baseline is the reports'",
        "\"without the loop\" (the closest round-0 candidate). Accepted rate: the share of the items open before",
        "that round that the round accepted, by the loop's own rule.",
        "",
    ]
    for run, cfg, counts in runs:
        lang = cfg["lang"]
        md += [f"## {lang.upper()}", "",
               "| Level | Items | Fit: baseline | Fit after 0 / 1 / 2 (%) | Fit & complete: baseline | "
               "Fit & complete after 0 / 1 / 2 (%) | Accepted rate, rounds 0 / 1 / 2 (%) | Open after round 2 | "
               "Third round, estimated gain (points) |",
               "|------:|------:|-----:|------------------------|-----:|------------------------------------|"
               "-----------------------------------|------------------:|-----------------------------------:|"]
        for level in (90, 80, 70, 60, "all"):
            c = counts[level]
            n = c["items"]
            r = [row for row in rows if row["lang"] == lang and row["level"] == level]

            def fc(row):
                lo, hi = row["fit_complete_low_pct"], row["fit_complete_high_pct"]
                return f"{lo}" if lo == hi else f"{lo}–{hi}"

            lo3, hi3 = third_round(c)
            md.append(f"| {level if level == 'all' else f'{level} %'} | {n} | {100 * c['base_fit'] / n:.1f} | "
                      + " / ".join(str(row["fit_pct"]) for row in r) + f" | {100 * c['base_complete'] / n:.1f} | "
                      + " / ".join(fc(row) for row in r) + " | "
                      + " / ".join(str(row["accepted_rate_pct"]) for row in r)
                      + f" | {n - c['accepted2']} | {lo3:+.1f} to {hi3:+.1f} |")
        md.append("")
    md += ["The third-round column is an estimate, not a measurement. It assumes round 3 turns open items into",
           "fit & complete outputs at round 2's rate. Where the loop's acceptance rate fell from round 1 to 2, a",
           "third round would likely add less.", ""]
    args.out.with_suffix(".md").write_text("\n".join(md), encoding="utf-8")
    with open(args.out.with_suffix(".csv"), "w", encoding="utf-8", newline="") as f:
        f.write(f"# Step 2 round by round, written by isochron.rounds on {started:%Y-%m-%d %H:%M} UTC, "
                f"git commit {git_commit()}; how it was made: {args.out.with_suffix('.md').name}\n")
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("\n".join(md))
    print(f"wrote {args.out.with_suffix('.md')} and {args.out.with_suffix('.csv')}")


if __name__ == "__main__":
    main()
