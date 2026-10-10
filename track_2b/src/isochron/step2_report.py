"""results/step2_test.md: step 2 on test, every language in one report, with every run's configuration.

For each run (one per language): the tables of isochron.pilot_report (all levels pooled, then each
level; prompt v1 without and with the repair loop; 95 % bootstrap intervals over sentences), then the
judge validation the run relies on, then each run's config.json and judge_config.json in full.

    uv run python -m isochron.step2_report RUN_DIR [RUN_DIR ...] --validation FILE [FILE ...] --out results/step2_test.md
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from isochron.language import describe as describe_language
from isochron.pilot_report import BOOT_SEED, N_BOOT, rows_for, short, table
from isochron.provenance import git_commit


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
                *table(rows, f"{lang}: all levels ({', '.join(f'{lv} %' for lv in levels)})"), ""]
        for lv in levels:
            out += [*table([r for r in rows if r["level"] == lv], f"{lang}: level {lv} %"), ""]
    if args.validation:
        out += ["## Judge validation", ""]
        for path in args.validation:
            text = path.read_text(encoding="utf-8").splitlines()
            tab = [line for line in text if line.startswith("|")][:9]
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
