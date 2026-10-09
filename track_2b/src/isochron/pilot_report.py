"""Phase 2 pilot table: one row per variant × repair condition.

Reads each pilot run's items.jsonl (generation log) and judge.jsonl (final
meaning judge, evaluation only) and writes results/pilot_phase2.md.

- Fit: the chosen output is within ±10 % of T in syllables (T = level % of the
  input syllables). A missing output is a miss.
- Fact recall: the judge's kept ÷ facts, per output, averaged. A missing output
  keeps no fact (recall 0). Outputs the judge could not parse are left out and
  counted under "Judge invalid".
- Added-fact rate: the share of outputs with an answer for which the judge
  marks at least one fact as added.
- Achieved ÷ target: syllables ÷ T over outputs with an answer; missing outputs
  are counted under "No output".
- Rounds: rounds after round 0 (0 to 2; always 0 without the loop), retries
  after an unusable answer included and also counted on their own.
- Time: seconds per output. Without the loop it is the round-0 request; with
  it, every round including the NLI checks.
- 95 % intervals: bootstrap over sentences (each carries both levels), 10,000
  resamples, seed 0.

    uv run python -m isochron.pilot_report RUN_DIR [RUN_DIR ...]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from isochron.pilot import selection_text
from isochron.provenance import git_commit

N_BOOT, BOOT_SEED = 10_000, 0
OUT = Path("results/pilot_phase2.md")


def ci(values_by_sentence: dict[str, list[float]]) -> str:
    """Mean over all values, with a percentile interval from resampling sentences."""
    groups = [np.asarray(v, dtype=float) for v in values_by_sentence.values() if v]
    if not groups:
        return "–"
    sums, counts = np.array([g.sum() for g in groups]), np.array([len(g) for g in groups])
    idx = np.random.default_rng(BOOT_SEED).integers(0, len(groups), size=(N_BOOT, len(groups)))
    means = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return f"{100 * sums.sum() / counts.sum():.1f} [{100 * lo:.1f}, {100 * hi:.1f}]"


def rows_for(run: Path) -> tuple[dict, list[dict]]:
    cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
    items = {(it["id"], it["level"], it["seed"]): it
             for it in map(json.loads, (run / "items.jsonl").read_text(encoding="utf-8").splitlines()) if it}
    judged = {(j["id"], j["level"], j["seed"]): j
              for j in map(json.loads, (run / "judge.jsonl").read_text(encoding="utf-8").splitlines()) if j}
    if items.keys() != judged.keys():
        raise SystemExit(f"{run}: judge.jsonl does not cover exactly the generated items")
    rows = []
    for key, it in items.items():
        for cond, cand, rounds, retries, secs in (
            ("without", it["closest_round0"], 0, 0, it["time_round0_s"]),
            ("with", it["final"], it["revisions"], it.get("retries", 0), it["time_total_s"]),
        ):
            j = judged[key][cond]
            rows.append({"variant": cfg["variant"], "cond": cond, "id": it["id"], "level": it["level"],
                         "fit": bool(cand and cand["hit"]), "nli_kept": bool(cand and cand["kept"]),
                         "no_output": not cand, "ratio": cand["syllables"] / it["target"] if cand else None,
                         "valid": j.get("valid", False), "recall": j.get("recall"), "added": j.get("added_any"),
                         "rounds": rounds, "retries": retries, "secs": secs})
    return cfg, rows


def table(rows: list[dict], title: str) -> list[str]:
    out = [f"### {title}", "",
           "| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | NLI kept | "
           "Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Judge invalid |",
           "|---------|-------------|--------:|-----------|-------------|-----------------|---------:|"
           "------------------:|------------:|--------:|------------------:|----------:|--------------:|"]
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["variant"], r["cond"]].append(r)
    for (variant, cond), rs in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1] != "without")):
        ids = sorted({r["id"] for r in rs})  # fixed order, so the bootstrap does not depend on hashing

        def by(f, sel=lambda r: True):
            return {sid: [f(r) for r in rs if r["id"] == sid and sel(r)] for sid in ids}

        def valid(r):
            return r["valid"] and r["recall"] is not None

        def answered(r):
            return valid(r) and not r["no_output"]

        ratios = [r["ratio"] for r in rs if r["ratio"] is not None]
        out.append(
            f"| {variant} | {cond} | {len(rs)} | {ci(by(lambda r: r['fit']))} | {ci(by(lambda r: r['recall'], valid))} "
            f"| {ci(by(lambda r: r['added'], answered))} | {100 * np.mean([r['nli_kept'] for r in rs]):.0f} % "
            f"| {f'{np.mean(ratios):.2f}' if ratios else '–'} | {np.mean([r['rounds'] for r in rs]):.2f} "
            f"| {sum(r['retries'] for r in rs)} | {np.mean([r['secs'] for r in rs]):.1f} "
            f"| {sum(r['no_output'] for r in rs)} | {sum(not valid(r) for r in rs)} |"
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase 2 pilot table.")
    ap.add_argument("runs", type=Path, nargs="+")
    args = ap.parse_args()
    cfgs, rows = [], []
    for run in args.runs:
        cfg, rs = rows_for(run)
        cfgs.append((run, cfg))
        rows += rs
    judge_cfg = json.loads((args.runs[0] / "judge_config.json").read_text(encoding="utf-8"))
    c0 = cfgs[0][1]
    out = [
        "# Phase 2 pilot (exploratory): prompt variants with and without the repair loop",
        "",
        f"- Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        f"- Git commit (report): {git_commit()}; runs: "
        + ", ".join(f"`{run.name}` ({cfg['git_commit'][:7]})" for run, cfg in cfgs),
        f"- Model: {c0['model']}, quantisation {c0['quantisation']}, endpoint {c0['endpoint']}, "
        f"backend {c0['backend'].get('build_info')}",
        f"- Generation: {json.dumps(c0['generation'])}",
        f"- Prompts: " + ", ".join(f"{cfg['variant']} `{cfg['prompt']['name']}` ({cfg['prompt']['sha256'][:12]})" for _, cfg in cfgs)
        + f"; repair `{c0['revise_prompt']['name']}` ({c0['revise_prompt']['sha256'][:12]}), at most {c0['max_revisions']} rounds",
        f"- Loop checks: {c0['length_counter']['syllables']} and NLI {c0['nli']}; the loop never sees the judge",
        f"- Judge (evaluation only): {judge_cfg['model']} ({judge_cfg['quantisation']}), endpoint {judge_cfg['endpoint']}, "
        f"backend {judge_cfg['backend'].get('build_info')}, temperature 0, seed {judge_cfg['seed']}, prompts "
        + ", ".join(f"{k} ({v[:12]})" for k, v in judge_cfg["prompts"].items()),
        f"- Items: {c0['items']['n']} sentences ({selection_text()}), levels {c0['levels']}, seeds {c0['seeds']}, "
        f"round seeds: {c0.get('round_seed', 'the item seed in every round')}; TTS: none",
        f"- 95 % intervals: bootstrap over sentences, {N_BOOT} resamples, seed {BOOT_SEED}. Exploratory: not a decision.",
        "",
        "Fit, fact recall and added-fact rate are in %. Time is per output (one sentence at one level).",
        "",
        *table(rows, "Both levels (90 % and 80 %)"),
        "",
        *table([r for r in rows if r["level"] == 90], "Level 90 %"),
        "",
        *table([r for r in rows if r["level"] == 80], "Level 80 %"),
    ]
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    print(f"\nwrote {OUT.resolve()}")


if __name__ == "__main__":
    main()
