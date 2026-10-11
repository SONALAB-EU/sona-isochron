"""results/step2_test.md: step 2 on test, every language in one report, with every run's configuration.

For each run (one per language): the tables of isochron.pilot_report (all levels pooled, then each
level; prompt v1 without and with the repair loop; 95 % bootstrap intervals over sentences), the
effect of the loop as a paired difference, then the judge validation the run relies on, then each
run's config.json and judge_config.json in full.

The loop's effect: with − without, in percentage points, for all levels pooled and for each level.
Both conditions come from the same items, so the bootstrap resamples sentences once per resample and
scores both conditions on that same resample (a paired interval). An interval that excludes 0 means
the difference is not resampling noise over sentences.

    uv run python -m isochron.step2_report RUN_DIR [RUN_DIR ...] --validation FILE [FILE ...] --out results/step2_test.md
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from isochron.language import describe as describe_language
from isochron.pilot_report import BOOT_SEED, N_BOOT, answered, complete, rows_for, short, table, valid
from isochron.provenance import git_commit

METRICS = (  # name, value per output, which outputs count (as in isochron.pilot_report.table)
    ("Fit ±10 %", lambda r: r["fit"], lambda r: True),
    ("Fact recall", lambda r: r["recall"], valid),
    ("Added-fact rate", lambda r: r["added"], answered),
    ("Fit & complete", complete, lambda r: True),
)


def paired_diff(rows: list[dict], value, counts) -> str:
    """Pooled mean with the loop minus pooled mean without, in points, with a paired bootstrap interval."""
    sums = {cond: defaultdict(float) for cond in ("with", "without")}
    ns = {cond: defaultdict(int) for cond in ("with", "without")}
    for r in rows:
        if counts(r):
            sums[r["cond"]][r["id"]] += float(value(r))
            ns[r["cond"]][r["id"]] += 1
    ids = sorted(set(ns["with"]) & set(ns["without"]))  # fixed order, so the bootstrap does not depend on hashing
    if not ids:
        return "–"
    s = {c: np.array([sums[c][i] for i in ids]) for c in sums}
    n = {c: np.array([ns[c][i] for i in ids]) for c in ns}
    idx = np.random.default_rng(BOOT_SEED).integers(0, len(ids), size=(N_BOOT, len(ids)))
    diffs = s["with"][idx].sum(axis=1) / n["with"][idx].sum(axis=1) - s["without"][idx].sum(axis=1) / n["without"][idx].sum(axis=1)
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    point = s["with"].sum() / n["with"].sum() - s["without"].sum() / n["without"].sum()
    return f"{100 * point:+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}]"


def first_table(lines: list[str]) -> list[str]:
    """The first markdown table in lines: its header, separator and rows, up to the first other line."""
    table: list[str] = []
    for line in lines:
        if line.startswith("|"):
            table.append(line)
        elif table:
            break
    return table


def effect_table(rows: list[dict], lang: str, levels: list[int]) -> list[str]:
    out = [f"### {lang}: effect of the repair loop (with − without, percentage points)", "",
           "| Levels | " + " | ".join(name for name, _, _ in METRICS) + " |",
           "|--------|" + "|".join("-" * (len(name) + 2) for name, _, _ in METRICS) + "|"]
    for name, rs in (("all", rows), *((f"{lv} %", [r for r in rows if r["level"] == lv]) for lv in levels)):
        out.append(f"| {name} | " + " | ".join(paired_diff(rs, value, counts) for _, value, counts in METRICS) + " |")
    return out + ["", "Higher is better, except for the added-fact rate. Sentences that lack a judge verdict in "
                      "one condition are left out of that column's difference."]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("runs", type=Path, nargs="+")
    ap.add_argument("--validation", type=Path, nargs="*", default=[], help="judge validation reports to cite")
    ap.add_argument("--notes", type=Path, help="hand-written summary placed before the tables")
    ap.add_argument("--out", type=Path, default=Path("results/step2_test.md"))
    ap.add_argument("--title", default="Step 2 on test: prompt v1 without and with the repair loop")
    args = ap.parse_args(argv)
    runs = []
    for run in args.runs:
        cfg, rows = rows_for(run)
        judge_cfg = json.loads((run / "judge_config.json").read_text(encoding="utf-8"))
        runs.append((run, cfg, rows, judge_cfg))
    c0, j0 = runs[0][1], runs[0][3]
    out = [
        f"# {args.title}",
        "",
        f"- Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        f"- Git commit (report): {git_commit()}; runs: "
        + ", ".join(f"`{run.name}` ({short(cfg['git_commit'])})" for run, cfg, _, _ in runs),
        f"- Model: {c0['model']}, quantisation {c0['quantisation']}, endpoint {c0['endpoint']}, "
        f"backend {c0['backend'].get('build_info')}",
        f"- Generation: {json.dumps(c0['generation'])}; round seeds: {c0['round_seed']}",
        f"- Prompt `{c0['prompt']['name']}` ({c0['prompt']['sha256'][:12]}); repair `{c0['revise_prompt']['name']}` "
        f"({c0['revise_prompt']['sha256'][:12]}), at most {c0['max_revisions']} rounds",
        f"- Loop checks: {c0['length_counter']['syllables']}, NLI {c0['nli']}, language check {describe_language()}",
        f"- Judge (evaluation only): {j0['model']} ({j0['quantisation']}), endpoint {j0['endpoint']}, backend "
        f"{j0['backend'].get('build_info')}, temperature 0, seed {j0['seed']}, mode {j0['mode']}",
        "- Items: " + "; ".join(f"{cfg['lang']} {cfg['split']}: {cfg['items']['n']} sentences × levels {cfg['levels']} "
                                f"× seeds {cfg['seeds']}" for _, cfg, _, _ in runs) + "; TTS: none",
        f"- 95 % intervals: bootstrap over sentences (each carries its levels and seeds), {N_BOOT} resamples, seed {BOOT_SEED}.",
        "",
        *([args.notes.read_text(encoding="utf-8").rstrip(), ""] if args.notes else []),
        "Fit, fact recall, added-fact rate and fit & complete are in %. Fit & complete = the output fits and the judge",
        "keeps every fact and finds nothing added. NLI kept is the loop's own check, reported as a screen. A missing",
        "or wrong-language output counts as a failure. Without the loop = the closest round-0 candidate of the same run.",
        "",
    ]
    for run, cfg, rows, _ in runs:
        levels = sorted({r["level"] for r in rows}, reverse=True)
        lang = cfg["lang"].upper()
        out += [f"## {lang} ({cfg['split']})", "",
                *table(rows, f"{lang}: all levels ({', '.join(f'{lv} %' for lv in levels)})"), "",
                *effect_table(rows, lang, levels), ""]
        for lv in levels:
            out += [*table([r for r in rows if r["level"] == lv], f"{lang}: level {lv} %"), ""]
    if args.validation:
        out += ["## Judge validation", ""]
        for path in args.validation:
            text = path.read_text(encoding="utf-8").splitlines()
            tab = first_table(text)
            mean = next((line for line in text if line.startswith("- Mean accuracy")), "")
            out += [f"`{path}`{': ' + mean[2:] if mean else ''}", "", *tab, ""]
    out += ["## Run configurations", ""]
    for run, cfg, _, judge_cfg in runs:
        out += [f"### `{run.name}`", "", "<details><summary>config.json</summary>", "", "```json",
                json.dumps(cfg, ensure_ascii=False, indent=2), "```", "", "</details>", "",
                "<details><summary>judge_config.json</summary>", "", "```json",
                json.dumps(judge_cfg, ensure_ascii=False, indent=2), "```", "", "</details>", ""]
    args.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {args.out.resolve()}")


if __name__ == "__main__":
    main()
