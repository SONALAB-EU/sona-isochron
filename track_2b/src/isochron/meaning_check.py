"""A second meaning check for step 4: post-hoc, added after test outputs existed.

The repair loop and the step 4 evaluation use the same NLI model (isochron.metrics.meaning, MoritzLaurer/
mDeBERTa-v3-base-xnli-multilingual-nli-2mil7). Inside (c)'s loop it compares each candidate with the plain
translation (a); the evaluation compares each output with the human reference (main) and with the English
source (secondary). So the model that picked (c)'s outputs also scores them. This module re-scores step 4
with a second NLI model that the loop never sees, with a different base model and training data (SECOND),
and runs the planted controls through both models.

Only the inference runs on the GPU:
- pairs (Mac): every pair the step 4 evaluation scores, as isochron.step4_report does: the human reference and
  the English source as premise, each usable output of (a), (b), (b)'s JSON sensitivity row and (c) as
  hypothesis.
- score (GPU job, hpc/meaning_check.sbatch): the second model on those pairs, written in the format of
  step4_report's NLI cache; then both models on the four control suites of isochron.judge.SUITES.
- report (Mac): results/step4_test_nli2.md. Catch rates on the controls for the evaluation NLI, the second NLI
  and the judge (from the committed validation reports); step 4's kept vs reference and vs source under both
  models, with 95 % bootstrap intervals over sentences; how often the two agree; (c) − (a) and (c) − (b)
  under the second model; and whether (c) gains more from the evaluation NLI than (a) does, which is what
  selection by that model would do.

The second model is 2-way (entailment, not entailment). Kept, added and dropped only ask whether a direction is
entailment, so they mean the same for both models.

    uv run python -m isochron.meaning_check pairs RUN_DIR... --out results/raw/meaning_check/pairs.jsonl
    uv run python -m isochron.meaning_check score --pairs PAIRS --out DIR          (on the GPU)
    uv run python -m isochron.meaning_check report RUN_DIR... --scores DIR --cache NLI_CACHE --out FILE
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from isochron.language import check as check_language
from isochron.metrics.meaning import Meaning
from isochron.pilot_report import BOOT_SEED, N_BOOT, ci, short
from isochron.provenance import git_commit
from isochron.step2_report import first_table, paired_diff
from isochron.step4_report import SYSTEMS, TOLERANT, TOLERANT_NAME, outputs

POSTHOC = "post-hoc, added after test outputs existed"
SECOND = {
    "model_id": "MoritzLaurer/bge-m3-zeroshot-v2.0-c",
    "revision": "705510dfe0f35d223a4bf6f5d2695ec5fd162341",
    "licence": "MIT (model card metadata)",
    "base": "BAAI/bge-m3-retromae (XLM-RoBERTa-large architecture; MIT)",
    "data": "English only: MNLI and FEVER-NLI, plus synthetic zero-shot data written by Mixtral-8x7B-Instruct; "
            "no XNLI, ANLI, WANLI or LingNLI and no machine translations",
    "overlap": "MNLI and FEVER-NLI: many of the loop model's German and French training pairs are machine "
               "translations of English pairs in this model's data; the same author; XLM-R and mDeBERTa-v3 were both "
               "pretrained on CC100. It was chosen before any of its scores on step 4's outputs or the controls existed",
}
SUITE_NAMES = ("nli", "hard", "nli_xl", "hard_xl")
VALIDATION = "results/judge_validation_{suite}_v3_qwen3-14b_hpc_8b.md"
ORDER = (("a", SYSTEMS["a"]), ("b", SYSTEMS["b"]), (TOLERANT, TOLERANT_NAME), ("c", SYSTEMS["c"]))


def key(premise: str, hypothesis: str) -> str:
    """The key of isochron.step4_report's NLI cache."""
    return hashlib.sha256(f"{premise}\0{hypothesis}".encode()).hexdigest()


@lru_cache(maxsize=None)
def wrong_language(text: str, lang: str) -> bool:
    return check_language(text, lang).wrong


def step4_rows(runs: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Every step 4 output as isochron.step4_report builds it (sensitivity row included), with "usable"."""
    cfgs, rows = [], []
    for run in runs:
        cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
        items = [json.loads(line) for line in (run / "items.jsonl").read_text(encoding="utf-8").splitlines() if line]
        cfgs.append(cfg)
        rows += outputs(items, cfg["length_counter"]["counter"])
    for r in rows:
        r["usable"] = bool(r["text"]) and not wrong_language(r["text"], r["lang"])
    return cfgs, rows


def write_pairs(runs: list[Path], out: Path) -> None:
    _, rows = step4_rows(runs)
    pairs = sorted({(r[side], r["text"]) for r in rows if r["usable"] for side in ("reference", "source")})
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.writelines(json.dumps({"premise": p, "hypothesis": h}, ensure_ascii=False) + "\n" for p, h in pairs)
    print(f"wrote {out}: {len(pairs)} pairs from {sum(r['usable'] for r in rows)} usable outputs")


def score(pairs_path: Path, out: Path, device: str | None = None) -> None:
    """On the GPU: the second model on the step 4 pairs, then both models on the control suites."""
    import torch
    import transformers

    from isochron.judge import SUITES
    from isochron.metrics.meaning import NLI
    from isochron.schema import ControlPair, read_jsonl

    out.mkdir(parents=True, exist_ok=True)
    pairs = [json.loads(line) for line in pairs_path.read_text(encoding="utf-8").splitlines() if line]
    second = NLI(device=device, model_id=SECOND["model_id"], revision=SECOND["revision"])
    evaluation = NLI(device=device)
    started = time.monotonic()
    meanings = second.meaning([p["premise"] for p in pairs], [p["hypothesis"] for p in pairs])
    step4_s = time.monotonic() - started
    with open(out / "step4_cache.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"nli": second.describe()}) + "\n")
        f.writelines(json.dumps({"key": key(p["premise"], p["hypothesis"]),
                                 "m": {"kept": m.kept, "added": m.added, "dropped": m.dropped}}) + "\n"
                     for p, m in zip(pairs, meanings))
    controls = []
    for suite in SUITE_NAMES:
        cps = list(read_jsonl(SUITES[suite]["file"], ControlPair))
        for name, nli in (("evaluation", evaluation), ("second", second)):
            ms = nli.meaning([p.source for p in cps], [p.output for p in cps])
            controls += [{"suite": suite, "id": p.id, "lang": p.lang, "control": p.control, "model": name,
                          "forward": m.forward, "backward": m.backward} for p, m in zip(cps, ms)]
    with open(out / "controls.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(c, ensure_ascii=False) + "\n" for c in controls)
    config = {
        "label": POSTHOC, "date": f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", "git_commit": git_commit(),
        "slurm_job": os.environ.get("SLURM_JOB_ID"),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "torch": torch.__version__, "transformers": transformers.__version__,
        "second": {**SECOND, "describe": second.describe(), "labels": second.labels},
        "evaluation": {"describe": evaluation.describe(), "labels": evaluation.labels},
        "pairs": len(pairs), "pairs_sha256": hashlib.sha256(pairs_path.read_bytes()).hexdigest(),
        "step4_inference_s": round(step4_s, 1), "controls": len(controls),
    }
    (out / "score_config.json").write_text(json.dumps(config, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(config, indent=1))


def read_cache(path: Path) -> tuple[str, dict[str, dict[str, bool]]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return json.loads(lines[0])["nli"], {e["key"]: e["m"] for e in map(json.loads, lines[1:])}


def kappa(x: list[bool], y: list[bool]) -> float:
    """Cohen's kappa for two binary raters."""
    a, b = np.asarray(x, float), np.asarray(y, float)
    observed = float(np.mean(a == b))
    chance = float(a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean()))
    return (observed - chance) / (1 - chance) if chance < 1 else 1.0


def controls_table(scores: Path) -> list[str]:
    from isochron.judge import SUITES, TITLES

    rows = [json.loads(line) for line in (scores / "controls.jsonl").read_text(encoding="utf-8").splitlines() if line]
    out = []
    for suite in SUITE_NAMES:
        spec = SUITES[suite]
        report = Path(VALIDATION.format(suite=suite))
        judged = {r["Control"]: r for r in table_rows(first_table(report.read_text(encoding="utf-8").splitlines()))}
        out += [f"### {TITLES[suite]}", "",
                f"The judge's column is copied from `{report}`. Rule for both NLI models: {spec['nli_rule']}.", "",
                "| Control | Pairs | Evaluation NLI (the loop's) | Second NLI | Judge (Qwen3-14B) | Same as the "
                "validation report's NLI column |",
                "|---------|------:|-----------------------------|------------|-------------------|"
                "-------------------------------|"]
        for control in spec["nli"]:
            got = {}
            for model in ("evaluation", "second"):
                ok = [spec["nli"][control](Meaning(r["forward"], r["backward"])) for r in rows
                      if r["suite"] == suite and r["model"] == model and r["control"] == control]
                got[model] = f"{100 * sum(ok) / len(ok):.0f} % ({sum(ok)}/{len(ok)})"
            n = sum(1 for r in rows if r["suite"] == suite and r["model"] == "evaluation" and r["control"] == control)
            same = "yes" if judged.get(control, {}).get("NLI, all") == got["evaluation"] else (
                f"no: {judged.get(control, {}).get('NLI, all', '–')}")
            out.append(f"| {control} | {n} | {got['evaluation']} | {got['second']} "
                       f"| {judged.get(control, {}).get('All', '–')} | {same} |")
        out.append("")
    return out


def table_rows(table: list[str]) -> list[dict[str, str]]:
    header = [c.strip() for c in table[0].strip().strip("|").split("|")]
    return [dict(zip(header, (c.strip() for c in line.strip().strip("|").split("|")))) for line in table[2:]]


def meaning_table(rows: list[dict[str, Any]], title: str) -> list[str]:
    out = [f"### {title}", "",
           "| System | Outputs | Kept vs reference: evaluation NLI | Kept vs reference: second NLI | Agreement (κ) "
           "| Kept vs source: evaluation NLI | Kept vs source: second NLI |",
           "|--------|--------:|-----------------------------------|-------------------------------|--------------:"
           "|-------------------------------|----------------------------|"]
    for system, name in ORDER:
        rs = [r for r in rows if r["system"] == system]
        if not rs:
            continue
        ids = sorted({r["id"] for r in rs})

        def by(f):
            return {i: [f(r) for r in rs if r["id"] == i] for i in ids}

        usable = [r for r in rs if r["usable"]]
        x, y = [r["ref1"]["kept"] for r in usable], [r["ref2"]["kept"] for r in usable]
        agree = f"{100 * np.mean(np.equal(x, y)):.0f} % ({kappa(x, y):.2f})" if usable else "–"
        out.append(f"| {name} | {len(rs)} | {ci(by(lambda r: r['usable'] and r['ref1']['kept']))} "
                   f"| {ci(by(lambda r: r['usable'] and r['ref2']['kept']))} | {agree} "
                   f"| {ci(by(lambda r: r['usable'] and r['src1']['kept']))} "
                   f"| {ci(by(lambda r: r['usable'] and r['src2']['kept']))} |")
    return out


def diff_table(rows: list[dict[str, Any]], title: str) -> list[str]:
    def pair(x: str, y: str) -> list[dict[str, Any]]:
        return [{**r, "cond": "with" if r["system"] == x else "without"} for r in rows if r["system"] in (x, y)]

    def kept(model: str):
        return lambda r: bool(r["usable"] and r[f"ref{model}"]["kept"])

    out = [f"### {title}: paired differences ({POSTHOC}; percentage points)", "",
           "| Difference | Kept vs reference: evaluation NLI | Kept vs reference: second NLI |",
           "|------------|-----------------------------------|-------------------------------|"]
    for x, y in (("c", "a"), ("c", "b")):
        out.append(f"| ({x}) − ({y}) | {paired_diff(pair(x, y), kept('1'), lambda r: True)} "
                   f"| {paired_diff(pair(x, y), kept('2'), lambda r: True)} |")
    def gap(r: dict[str, Any]) -> float:
        return float(kept("1")(r)) - float(kept("2")(r))

    out += ["", "Does (c) gain more from the evaluation NLI than (a) does? Evaluation minus second NLI on kept vs "
            f"reference, (c) minus (a), paired: {paired_diff(pair('c', 'a'), gap, lambda r: True)} points. A "
            "positive difference is what selection by the evaluation NLI inside the loop would cause."]
    return out


def report(runs: list[Path], scores: Path, cache: Path, out: Path, notes: Path | None = None) -> None:
    cfgs, rows = step4_rows(runs)
    describe1, first = read_cache(cache)
    describe2, second = read_cache(scores / "step4_cache.jsonl")
    config = json.loads((scores / "score_config.json").read_text(encoding="utf-8"))
    missing = 0
    for r in rows:
        if r["usable"]:
            for n, m in (("1", first), ("2", second)):
                r[f"ref{n}"], r[f"src{n}"] = m.get(key(r["reference"], r["text"])), m.get(key(r["source"], r["text"]))
                missing += r[f"ref{n}"] is None or r[f"src{n}"] is None
    if missing:
        raise SystemExit(f"{missing} pairs have no score: run `pairs` and `score` again")
    sentences = defaultdict(set)
    for r in rows:
        sentences[r["lang"]].add(r["id"])
    cfg = cfgs[0]
    lines = [
        f"# Step 4 on test: a second meaning check ({POSTHOC})",
        "",
        f"- Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        f"- Git commit (report): {git_commit()}; scores: {config['git_commit']} (job {config['slurm_job']}, "
        f"{config['gpu']}, torch {config['torch']}, transformers {config['transformers']}); runs: "
        + ", ".join(f"`{run.name}` ({short(c['git_commit'])})" for run, c in zip(runs, cfgs)),
        f"- Outputs scored: {cfg['model']}, quantisation {cfg['quantisation']}; endpoint "
        + ", ".join(f"{'/'.join(c['langs'])} {c['endpoint']}" for c in cfgs) + f"; seeds {cfg['seeds']}; TTS: none",
        f"- Evaluation NLI (the loop's own model): {describe1}",
        f"- Second NLI: {describe2}. Licence: {SECOND['licence']}. Base: {SECOND['base']}. Training data: "
        f"{SECOND['data']}. Shared with the evaluation NLI: {SECOND['overlap']}.",
        f"- Where each score comes from: the controls, both models on the job's GPU; step 4, the evaluation NLI from "
        f"isochron.step4_report's cache (`{cache.name}`) and the second NLI from the job. Both run locally (no "
        "endpoint).",
        "- Sentences: " + json.dumps({k: len(v) for k, v in sorted(sentences.items())})
        + f"; split {cfg['split']}. 95 % intervals: bootstrap over sentences, {N_BOOT} resamples, seed {BOOT_SEED}.",
        "",
        *([notes.read_text(encoding="utf-8").rstrip(), ""] if notes else []),
        "Kept: the NLI finds entailment in both directions. A missing or wrong-language output counts as not kept.",
        "",
        "## Planted controls",
        "",
        *controls_table(scores),
        "## Step 4 re-scored",
        "",
    ]
    groups = defaultdict(list)
    for r in rows:
        groups[r["lang"], r["budget"]].append(r)
    for (lang, kind), rs in sorted(groups.items()):
        title = f"EN → {lang.upper()}, {kind} budget ({rs[0]['unit']})"
        lines += meaning_table(rs, title) + [""] + diff_table(rs, title) + [""]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"wrote {out.resolve()}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=f"A second meaning check for step 4 ({POSTHOC}).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pairs", help="every pair the step 4 evaluation scores (Mac)")
    p.add_argument("runs", type=Path, nargs="+")
    p.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("score", help="the second model on the pairs, both models on the controls (GPU)")
    s.add_argument("--pairs", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--device", default=None)
    r = sub.add_parser("report", help="results/step4_test_nli2.md (Mac)")
    r.add_argument("runs", type=Path, nargs="+")
    r.add_argument("--scores", type=Path, required=True)
    r.add_argument("--cache", type=Path, required=True, help="the evaluation NLI's cache (isochron.step4_report)")
    r.add_argument("--out", type=Path, default=Path("results/step4_test_nli2.md"))
    r.add_argument("--notes", type=Path, help="hand-written summary placed before the tables")
    args = ap.parse_args(argv)
    if args.cmd == "pairs":
        write_pairs(args.runs, args.out)
    elif args.cmd == "score":
        score(args.pairs, args.out, args.device)
    else:
        report(args.runs, args.scores, args.cache, args.out, args.notes)


if __name__ == "__main__":
    main()
