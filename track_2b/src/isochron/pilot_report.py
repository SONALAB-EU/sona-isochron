"""Tables for repair-loop runs: one row per variant × repair condition.

Reads each run's items.jsonl (generation log) and judge.jsonl (final meaning
judge, evaluation only) and writes results/phase2_pilot.md (or --out).

- Wrong language: the chosen output is not in the run's language by the
  language check (isochron.language). It counts as a failure, like a missing
  output: no fit, not kept, recall 0, not complete, no ratio. The phase 2
  pilot ran before the loop had this check; its outputs are re-scored here.
- Fit: the chosen output is within ±10 % of T in syllables (T = level % of the
  input syllables). A missing output is a miss.
- Fact recall: the judge's kept ÷ facts, per output, averaged. A missing or
  wrong-language output keeps no fact (recall 0). Outputs the judge could not
  parse are left out and counted under "Judge invalid".
- Added-fact rate: the share of outputs with an answer in the right language
  for which the judge marks at least one fact as added.
- Fit & complete: the output fits AND the judge keeps every fact (recall 1) and
  finds nothing added. This is the success measure the recommendation uses
  (fixed before any judge output was seen): the condition with the highest
  rate is recommended, and near-ties (overlapping 95 % intervals) are broken by
  time per output. Outputs the judge could not parse count as not complete.
- Achieved ÷ target: syllables ÷ T over outputs with an answer; missing outputs
  are counted under "No output".
- Rounds: rounds after round 0 (0 to 2; always 0 without the loop), retries
  after an unusable answer included and also counted on their own.
- Time: seconds per output. Without the loop it is the round-0 request; with
  it, every round including the NLI checks.
- 95 % intervals: bootstrap over sentences (each carries all its levels and
  seeds), 10,000 resamples, seed 0.

    uv run python -m isochron.pilot_report RUN_DIR [RUN_DIR ...] [--notes FILE] [--out FILE --title TEXT]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from isochron.language import check as check_language
from isochron.language import describe as describe_language
from isochron.provenance import git_commit

N_BOOT, BOOT_SEED = 10_000, 0
OUT = Path("results/phase2_pilot.md")
TITLE = "Phase 2 pilot (exploratory): prompt variants with and without the repair loop"


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


def short(commit: str) -> str:
    """Abbreviated hash, keeping any '(with uncommitted changes ...)' note."""
    sha, _, note = commit.partition(" ")
    return f"{sha[:7]} {note}".strip()


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
            wrong = bool(cand) and check_language(cand["text"], cfg["lang"]).wrong
            usable = bool(cand) and not wrong
            rows.append({"variant": cfg["variant"], "cond": cond, "id": it["id"], "level": it["level"],
                         "fit": bool(usable and cand["hit"]), "nli_kept": bool(usable and cand["kept"]),
                         "no_output": not cand, "wrong_language": wrong,
                         "ratio": cand["syllables"] / it["target"] if usable else None,
                         "valid": j.get("valid", False), "recall": 0.0 if wrong else j.get("recall"),
                         "added": None if wrong else j.get("added_any"),
                         "rounds": rounds, "retries": retries, "secs": secs})
    return cfg, rows


def table(rows: list[dict], title: str) -> list[str]:
    out = [f"### {title}", "",
           "| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | "
           "Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |",
           "|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|"
           "------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|"]
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
            return valid(r) and not r["no_output"] and not r["wrong_language"]

        def complete(r):
            return bool(r["fit"] and answered(r) and r["recall"] == 1 and not r["added"])

        ratios = [r["ratio"] for r in rs if r["ratio"] is not None]
        out.append(
            f"| {variant} | {cond} | {len(rs)} | {ci(by(lambda r: r['fit']))} | {ci(by(lambda r: r['recall'], valid))} "
            f"| {ci(by(lambda r: r['added'], answered))} | {ci(by(complete))} "
            f"| {100 * np.mean([r['nli_kept'] for r in rs]):.0f} % "
            f"| {f'{np.mean(ratios):.2f}' if ratios else '–'} | {np.mean([r['rounds'] for r in rs]):.2f} "
            f"| {sum(r['retries'] for r in rs)} | {np.mean([r['secs'] for r in rs]):.1f} "
            f"| {sum(r['no_output'] for r in rs)} | {sum(r['wrong_language'] for r in rs)} | {sum(not valid(r) for r in rs)} |"
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Tables for repair-loop runs (the phase 2 pilot by default).")
    ap.add_argument("runs", type=Path, nargs="+")
    ap.add_argument("--notes", type=Path, help="hand-written summary (markdown) placed before the tables")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--title", default=TITLE)
    args = ap.parse_args()
    cfgs, rows = [], []
    for run in args.runs:
        cfg, rs = rows_for(run)
        cfgs.append((run, cfg))
        rows += rs
    judge_cfgs = [json.loads((run / "judge_config.json").read_text(encoding="utf-8")) for run in args.runs]
    judge_cfg, c0 = judge_cfgs[0], cfgs[0][1]
    loop_lang = {cfg.get("language_check", "none (the run predates it)") for _, cfg in cfgs}
    levels = sorted({r["level"] for r in rows}, reverse=True)
    out = [
        f"# {args.title}",
        "",
        f"- Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        f"- Git commit (report): {git_commit()}; runs: "
        + ", ".join(f"`{run.name}` ({short(cfg['git_commit'])})" for run, cfg in cfgs)
        + "; judge: " + ", ".join(sorted({short(c["git_commit"]) for c in judge_cfgs})),
        f"- Model: {c0['model']}, quantisation {c0['quantisation']}, endpoint {c0['endpoint']}, "
        f"backend {c0['backend'].get('build_info')}",
        f"- Generation: {json.dumps(c0['generation'])}",
        f"- Prompts: " + ", ".join(f"{cfg['variant']} `{cfg['prompt']['name']}` ({cfg['prompt']['sha256'][:12]})" for _, cfg in cfgs)
        + f"; repair `{c0['revise_prompt']['name']}` ({c0['revise_prompt']['sha256'][:12]}), at most {c0['max_revisions']} rounds",
        f"- Loop checks: {c0['length_counter']['syllables']} and NLI {c0['nli']}; language check in the loop: "
        f"{'; '.join(sorted(loop_lang))}; the loop never sees the judge",
        f"- Scoring: an output in the wrong language counts as a failure ({describe_language()})",
        f"- Judge (evaluation only): {judge_cfg['model']} ({judge_cfg['quantisation']}), endpoint {judge_cfg['endpoint']}, "
        f"backend {judge_cfg['backend'].get('build_info')}, temperature 0, seed {judge_cfg['seed']}, prompts "
        + ", ".join(f"{k} ({v[:12]})" for k, v in judge_cfg["prompts"].items()),
        f"- Items: {c0['items']['n']} sentences ({c0['items']['selection']}; {c0['lang']} {c0['split']}), "
        f"levels {c0['levels']}, seeds {c0['seeds']}, "
        f"round seeds: {c0.get('round_seed', 'the item seed in every round')}; TTS: none",
        f"- 95 % intervals: bootstrap over sentences, {N_BOOT} resamples, seed {BOOT_SEED}. "
        + ("Dev split: exploratory, not a decision." if c0["split"] == "dev" else f"Split: {c0['split']}."),
        "",
        *([args.notes.read_text(encoding="utf-8").rstrip(), ""] if args.notes else []),
        "## Tables",
        "",
        "Fit, fact recall, added-fact rate and fit & complete are in %. Time is per output (one sentence at one level",
        "and seed). Fit & complete = fits, and the judge keeps every fact and finds nothing added. An output in the",
        "wrong language counts as a failure.",
        "",
        *table(rows, f"{'Both' if len(levels) == 2 else 'All'} levels ({' and '.join(f'{lv} %' for lv in levels)})"),
        *[line for lv in levels for line in ("", *table([r for r in rows if r["level"] == lv], f"Level {lv} %"))],
    ]
    args.out.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    print(f"\nwrote {args.out.resolve()}")


if __name__ == "__main__":
    main()
