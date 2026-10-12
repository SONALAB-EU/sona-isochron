"""Step 4 tables: translation to a length budget, per target language, budget and system.

Reads one or more step 4 runs (isochron.step4; for example the German and the French job) and writes a
markdown report.

- Fit: the output is within ±10 % of the budget, in the budget's unit (characters without spaces for
  the isometric budget, syllables for the isosyllabic one). A missing or wrong-language output is a miss.
- Kept vs reference (the main NLI check): the NLI finds entailment both ways between the output and the
  human reference translation, in the target language. Added and dropped are its two directions.
- Kept vs source (secondary): the same against the English source (cross-lingual NLI).
- The final judge, if the run has judge.jsonl (isochron.judge step4): it lists the facts of the English
  source and marks each as kept, changed or dropped in the output, and lists added facts.
  - Fact recall: kept facts ÷ facts, averaged over outputs. A missing or wrong-language output keeps no
    fact. Outputs the judge could not parse are left out and counted under "Judge invalid".
  - Added-fact rate: share of outputs in the right language for which the judge finds an added fact.
  - Fit & complete: fits, and the judge keeps every fact and finds nothing added (as in step 2).
- Achieved ÷ budget, and compression = output ÷ plain translation (a), both in the budget's unit, over
  outputs with an answer.
- Lengths: mean characters, words and syllables of the outputs with an answer.
- (c) keeps (a) unchanged when (a) is at most 1.10 × the budget; "(a) kept" is how often.
- A wrong-language output (isochron.language) counts as a failure, like a missing one.
- 95 % intervals: bootstrap over sentences (each carries its seeds), 10,000 resamples, seed 0.

    uv run python -m isochron.step4_report RUN_DIR [RUN_DIR ...] [--validation FILE ...] [--out FILE]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from isochron.language import check as check_language
from isochron.language import describe as describe_language
from isochron.metrics.length import hit, length
from isochron.pilot_report import BOOT_SEED, N_BOOT, ci, short
from isochron.provenance import git_commit
from isochron.step2_report import first_table

SYSTEMS = {"a": "(a) plain translation", "b": "(b) one step to the budget", "c": "(c) translate, then shorten"}


def outputs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per (item, budget, system), before scoring."""
    rows = []
    for it in items:
        plain = it["a"]["text"]
        for kind, entry in it["budgets"].items():
            texts = {"a": plain, "b": entry["b"]["text"], "c": entry["c"]["text"]}
            for system, text in texts.items():
                loop = entry["c"].get("loop") if system == "c" else None
                rows.append({"id": it["id"], "lang": it["lang"], "seed": it["seed"], "budget": kind,
                             "unit": entry["unit"], "target": entry["target"], "system": system, "text": text,
                             "plain": plain, "source": it["source"], "reference": it["reference"],
                             "kept_plain": entry["c"]["kept_plain"] if system == "c" else None,
                             "rounds": loop["revisions"] if loop else 0})
    return rows


def attach_judge(rows: list[dict[str, Any]], judged: dict[tuple, dict[str, Any]]) -> None:
    """Adds the judge's verdict to every row, in place (step 2's rules: wrong language keeps nothing)."""
    for r in rows:
        j = judged[(r["id"], r["lang"], r["seed"])]
        v = j["a"] if r["system"] == "a" else j["budgets"][r["budget"]][r["system"]]
        r["judge_valid"] = bool(v.get("valid")) and v.get("recall") is not None
        r["recall"] = 0.0 if r["wrong_language"] else v.get("recall")
        r["added_fact"] = None if (r["wrong_language"] or not r["text"]) else v.get("added_any")
        r["complete"] = bool(r["fit"] and r["judge_valid"] and r["usable"] and v["recall"] == 1 and not v.get("added_any"))


def score(rows: list[dict[str, Any]], counter: str, nli, cache: Path | None = None) -> None:
    """Adds lengths, fit, the language check and both NLI checks to every row, in place.

    Every distinct text is measured once, and every distinct NLI pair is scored once; with a cache file,
    scores of an earlier pass are reused (the file records the NLI model, so a different one is refused).
    """

    @lru_cache(maxsize=None)
    def size(text: str, unit: str, lang: str) -> int:
        return length(text, unit, lang, counter)

    for r in rows:
        t, lang = r["text"], r["lang"]
        r["wrong_language"] = bool(t) and check_language(t, lang).wrong
        r["usable"] = bool(t) and not r["wrong_language"]
        if t:
            r["len"] = {u: size(t, u, lang) for u in ("chars", "words", "syllables")}
            r["fit"] = r["usable"] and hit(r["len"][r["unit"]], r["target"])
            r["ratio"] = r["len"][r["unit"]] / r["target"]
            r["compression"] = (r["len"][r["unit"]] / size(r["plain"], r["unit"], lang)) if r["plain"] else None
        else:
            r["len"], r["fit"], r["ratio"], r["compression"] = None, False, None, None
    scored = [r for r in rows if r["usable"]]
    pairs = sorted({(r[ref], r["text"]) for r in scored for ref in ("reference", "source")})
    done: dict[str, dict[str, bool]] = {}
    model = nli.describe()
    if cache and cache.exists():
        lines = cache.read_text(encoding="utf-8").splitlines()
        if lines and json.loads(lines[0]).get("nli") != model:
            raise SystemExit(f"{cache} holds scores of another NLI setup: {json.loads(lines[0]).get('nli')}")
        done = {e["key"]: e["m"] for e in map(json.loads, lines[1:])}

    def key(p: tuple[str, str]) -> str:
        return hashlib.sha256(f"{p[0]}\0{p[1]}".encode()).hexdigest()

    todo = [p for p in pairs if key(p) not in done]
    if todo:
        meanings = nli.meaning([p[0] for p in todo], [p[1] for p in todo])
        new = {key(p): {"kept": m.kept, "added": m.added, "dropped": m.dropped} for p, m in zip(todo, meanings)}
        done.update(new)
        if cache:
            fresh = not cache.exists()
            with open(cache, "a", encoding="utf-8") as f:
                if fresh:
                    f.write(json.dumps({"nli": model}) + "\n")
                f.writelines(json.dumps({"key": k, "m": m}) + "\n" for k, m in new.items())
    for r in rows:
        r["ref"] = r["src"] = None
        if r["usable"]:
            r["ref"] = done[key((r["reference"], r["text"]))]
            r["src"] = {"kept": done[key((r["source"], r["text"]))]["kept"]}


def table(rows: list[dict[str, Any]], title: str) -> list[str]:
    out = [f"### {title}", "",
           "| System | Outputs | Fit ±10 % | Kept vs reference | Added vs ref. | Dropped vs ref. | Kept vs source "
           "| Achieved ÷ budget | Compression vs (a) | Chars / words / syllables | (a) kept | Avg. rounds "
           "| Wrong language | No output |",
           "|--------|--------:|-----------|-------------------|--------------:|----------------:|----------------"
           "|------------------:|-------------------:|--------------------------|---------:|------------:"
           "|---------------:|----------:|"]
    for system, name in SYSTEMS.items():
        rs = [r for r in rows if r["system"] == system]
        if not rs:
            continue
        ids = sorted({r["id"] for r in rs})

        def by(f):
            return {i: [f(r) for r in rs if r["id"] == i] for i in ids}

        usable = [r for r in rs if r["usable"]]

        def mean(values, fmt="{:.2f}"):
            values = [v for v in values if v is not None]
            return fmt.format(np.mean(values)) if values else "–"

        lens = " / ".join(mean([r["len"][u] for r in usable], "{:.1f}") for u in ("chars", "words", "syllables"))
        kept_plain = f"{100 * np.mean([r['kept_plain'] for r in rs]):.0f} %" if system == "c" else "–"
        out.append(
            f"| {name} | {len(rs)} | {ci(by(lambda r: r['fit']))} | {ci(by(lambda r: bool(r['ref'] and r['ref']['kept'])))} "
            f"| {100 * np.mean([bool(r['ref'] and r['ref']['added']) for r in usable]) if usable else 0:.0f} % "
            f"| {100 * np.mean([bool(r['ref'] and r['ref']['dropped']) for r in usable]) if usable else 0:.0f} % "
            f"| {ci(by(lambda r: bool(r['src'] and r['src']['kept'])))} "
            f"| {mean([r['ratio'] for r in usable])} | {mean([r['compression'] for r in usable])} | {lens} "
            f"| {kept_plain} | {mean([r['rounds'] for r in rs]) if system == 'c' else '–'} "
            f"| {sum(r['wrong_language'] for r in rs)} | {sum(not r['text'] for r in rs)} |")
    return out


def judge_table(rows: list[dict[str, Any]], title: str) -> list[str]:
    out = [f"### {title}: final judge", "",
           "| System | Outputs | Fit ±10 % | Fit & complete | Fact recall | Added-fact rate | Judge invalid |",
           "|--------|--------:|-----------|----------------|-------------|----------------:|--------------:|"]
    for system, name in SYSTEMS.items():
        rs = [r for r in rows if r["system"] == system]
        if not rs:
            continue
        ids = sorted({r["id"] for r in rs})

        def by(f, sel=lambda r: True):
            return {i: [f(r) for r in rs if r["id"] == i and sel(r)] for i in ids}

        answered = [r for r in rs if r["judge_valid"] and r["usable"]]
        added = f"{100 * np.mean([bool(r['added_fact']) for r in answered]):.1f} %" if answered else "–"
        out.append(f"| {name} | {len(rs)} | {ci(by(lambda r: r['fit']))} | {ci(by(lambda r: r['complete']))} "
                   f"| {ci(by(lambda r: r['recall'], lambda r: r['judge_valid']))} | {added} "
                   f"| {sum(not r['judge_valid'] for r in rs)} |")
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Step 4 tables.")
    ap.add_argument("runs", type=Path, nargs="+")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--title", help="default: Step 4 (RUN): translation to a length budget")
    ap.add_argument("--validation", type=Path, nargs="*", default=[], help="judge validation reports to cite")
    ap.add_argument("--notes", type=Path, help="hand-written summary placed before the tables")
    ap.add_argument("--nli-cache", type=Path, help="JSONL file: NLI scores reused across passes")
    ap.add_argument("--device", default=None, help="NLI device (default: cuda, then mps, then cpu)")
    args = ap.parse_args(argv)
    cfgs = [json.loads((run / "config.json").read_text(encoding="utf-8")) for run in args.runs]
    items = [json.loads(line) for run in args.runs
             for line in (run / "items.jsonl").read_text(encoding="utf-8").splitlines() if line]
    judged, judge_cfgs = {}, []
    for run in args.runs:
        if (run / "judge.jsonl").exists():
            judge_cfgs.append(json.loads((run / "judge_config.json").read_text(encoding="utf-8")))
            for line in (run / "judge.jsonl").read_text(encoding="utf-8").splitlines():
                j = json.loads(line)
                judged[(j["id"], j["lang"], j["seed"])] = j
    if judged and len(judge_cfgs) != len(args.runs):
        raise SystemExit("some runs have judge.jsonl and others do not")
    cfg = cfgs[0]
    from isochron.metrics.meaning import NLI

    nli = NLI(device=args.device)
    rows = outputs(items)
    score(rows, cfg["length_counter"]["counter"], nli, args.nli_cache)
    if judged:
        attach_judge(rows, judged)
    name = "+".join(run.name for run in args.runs)
    out = args.out or Path("results") / f"{name}.md"
    sentences = defaultdict(set)
    for it in items:
        sentences[it["lang"]].add(it["id"])
    j0 = judge_cfgs[0] if judge_cfgs else None
    lines = [
        f"# {args.title or f'Step 4 ({name}): translation to a length budget'}",
        "",
        f"- Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        f"- Git commit (report): {git_commit()}; runs: "
        + ", ".join(f"`{run.name}` ({short(c['git_commit'])})" for run, c in zip(args.runs, cfgs)),
        f"- Model: {cfg['model']}, quantisation {cfg['quantisation']}, backend "
        f"{cfg['backend'].get('build_info', cfg['backend'].get('type'))}; endpoint "
        + ", ".join(f"{'/'.join(c['langs'])} {c['endpoint']}" for c in cfgs),
        f"- Generation: {json.dumps(cfg['generation'])}; seeds {cfg['seeds']} ({cfg['round_seed']})",
        "- Prompts: " + ", ".join(f"`{p['name']}` ({p['sha256'][:12]})" for p in cfg["prompts"].values()),
        f"- Systems: (b) {cfg['selection_b']}; (c) {cfg['shorten_c']}",
        f"- Budgets: {json.dumps(cfg['budgets'])}; syllable rates {json.dumps(cfg['rates'])}; length counter "
        f"{cfg['length_counter']['syllables']}",
        f"- Meaning: NLI {nli.describe()}; language check {describe_language()}",
        *([f"- Judge (evaluation only): {j0['model']} ({j0['quantisation']}), backend "
           f"{j0['backend'].get('build_info')}, temperature 0, seed {j0['seed']}, mode {j0['mode']}, facts listed from "
           f"the English source; endpoint " + ", ".join(j['endpoint'] for j in judge_cfgs)] if j0 else []),
        f"- Items: {cfg['items']['selection']}; sentences "
        + json.dumps({lang: len(ids) for lang, ids in sorted(sentences.items())}) + f"; split {cfg['split']}; TTS: none",
        f"- 95 % intervals: bootstrap over sentences, {N_BOOT} resamples, seed {BOOT_SEED}."
        + (" Dev split: exploratory." if cfg["split"] == "dev" else " Test split: final numbers."),
        "",
        *([args.notes.read_text(encoding="utf-8").rstrip(), ""] if args.notes else []),
        "Fit, kept, added and dropped are in %. (a) is the same translation under both budgets; its fit says how",
        "often plain translation already meets the budget.",
        "",
    ]
    groups = defaultdict(list)
    for r in rows:
        groups[r["lang"], r["budget"]].append(r)
    for (lang, kind), rs in sorted(groups.items()):
        title = f"EN → {lang.upper()}, {kind} budget ({rs[0]['unit']})"
        lines += table(rs, title) + [""]
        if judged:
            lines += judge_table(rs, title) + [""]
    if args.validation:
        lines += ["## Judge validation", ""]
        for path in args.validation:
            text = path.read_text(encoding="utf-8").splitlines()
            mean = next((line for line in text if line.startswith("- Mean accuracy")), "")
            lines += [f"`{path}`{': ' + mean[2:] if mean else ''}", "", *first_table(text), ""]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"wrote {out.resolve()}")


if __name__ == "__main__":
    main()
