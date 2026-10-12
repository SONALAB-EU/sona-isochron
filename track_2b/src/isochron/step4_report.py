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
- Paired differences (post-hoc, added after test outputs existed): (c) − (b) and (c) − (a), in percentage points, for fit, fit &
  complete and kept vs reference. All systems translate the same sentences, so the bootstrap resamples
  sentences once per resample and scores both systems on it (step 2's paired interval,
  isochron.step2_report.paired_diff).
- JSON sensitivity (post-hoc, added after test outputs existed): a row under (b) that re-reads only the
  (b) answers strict JSON rejected, with one tolerant rule (every \\' becomes '), and chooses among the
  recovered candidates as (b) does. No new generation; the judge never saw the recovered outputs, so
  the row is not in the judge tables. The pre-registered (b) row is unchanged.
- Parse failures, per language and budget: (a)'s tries, (b)'s rejected answers and how many the rule
  recovers, and (c)'s loop rounds that gave no candidate (see isochron.repair for how the loop goes on).

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

from isochron.candidates import parse_candidates, select
from isochron.language import check as check_language
from isochron.language import describe as describe_language
from isochron.metrics.length import hit, length
from isochron.pilot_report import BOOT_SEED, N_BOOT, ci, short
from isochron.provenance import git_commit
from isochron.step2_report import first_table, paired_diff

SYSTEMS = {"a": "(a) plain translation", "b": "(b) one step to the budget", "c": "(c) translate, then shorten"}
TOLERANT = "b_tolerant"  # the sensitivity row, in the main tables only, under (b)
TOLERANT_NAME = "(b), `\\'` read as `'`: sensitivity (post-hoc, added after test outputs existed)"
TABLE_ORDER = (("a", SYSTEMS["a"]), ("b", SYSTEMS["b"]), (TOLERANT, TOLERANT_NAME), ("c", SYSTEMS["c"]))
PAIRS = (("c", "b"), ("c", "a"))
DIFFS = (  # name, value per output, judge needed
    ("Fit ±10 %", lambda r: r["fit"], False),
    ("Fit & complete", lambda r: r["complete"], True),
    ("Kept vs reference", lambda r: bool(r["ref"] and r["ref"]["kept"]), False),
)


def tolerant(entry: dict[str, Any], lang: str, counter: str) -> str | None:
    """(b) for the sensitivity row: an answer strict JSON rejected is read again with \\' as ', and the
    candidate closest to the budget is chosen as in (b). Answers that parsed are left as they are."""
    b = entry["b"]
    if b["text"] is not None or not b.get("raw"):
        return b["text"]
    cands, _ = parse_candidates(b["raw"].replace("\\'", "'"))
    idx = select(cands, "closest", lambda t: length(t, entry["unit"], lang, counter), entry["target"])
    return cands[idx] if idx is not None else None


def outputs(items: list[dict[str, Any]], counter: str | None = None) -> list[dict[str, Any]]:
    """One row per (item, budget, system), before scoring; with a counter, also the sensitivity row."""
    rows = []
    for it in items:
        plain = it["a"]["text"]
        for kind, entry in it["budgets"].items():
            texts = {"a": plain, "b": entry["b"]["text"], "c": entry["c"]["text"]}
            if counter:
                texts[TOLERANT] = tolerant(entry, it["lang"], counter)
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
        if r["system"] not in SYSTEMS:  # the sensitivity row: the judge never saw the recovered outputs
            r.update(judge_valid=False, recall=None, added_fact=None, complete=None)
            continue
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
    for system, name in TABLE_ORDER:
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


def diff_table(rows: list[dict[str, Any]], title: str, judged: bool) -> list[str]:
    metrics = [(name, value) for name, value, needs_judge in DIFFS if judged or not needs_judge]
    out = [f"### {title}: paired differences (post-hoc, added after test outputs existed; percentage points)", "",
           "| Difference | " + " | ".join(name for name, _ in metrics) + " |",
           "|------------|" + "|".join("-" * (len(name) + 2) for name, _ in metrics) + "|"]
    for x, y in (*PAIRS, ("c", TOLERANT)):
        if not any(r["system"] == y for r in rows):
            continue
        pair = [{**r, "cond": "with" if r["system"] == x else "without"} for r in rows if r["system"] in (x, y)]
        label = "(c) − (b) with `\\'` read as `'` (sensitivity)" if y == TOLERANT else f"({x}) − ({y})"
        out.append(f"| {label} | " + " | ".join(
            "–" if y == TOLERANT and name == "Fit & complete" else paired_diff(pair, value, lambda r: True)
            for name, value in metrics) + " |")
    return out


def parse_table(items: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[str]:
    """Strict JSON failures per language and budget, and what (a), (b) and (c) did about them."""
    recovered = {(r["id"], r["lang"], r["seed"], r["budget"]) for r in rows if r["system"] == TOLERANT and r["text"]}
    out = ["### Parse failures (strict JSON, as frozen)", "",
           "| Language, budget | (b) rejected | (b) recovered by the rule | (c) loop runs | (c) rounds "
           "| (c) rounds without a candidate | (c) retry rounds | (c) runs with such a round | of those, with an output "
           "| (c) runs without an output |",
           "|------------------|-------------:|--------------------------:|--------------:|-----------:"
           "|-------------------------------:|-----------------:|---------------------------:|-------------------------:"
           "|---------------------------:|"]
    langs = sorted({it["lang"] for it in items})
    for lang in langs:
        its = [it for it in items if it["lang"] == lang]
        for kind in sorted({k for it in its for k in it["budgets"]}):
            entries = [(it, it["budgets"][kind]) for it in its if kind in it["budgets"]]
            rejected = [(it, e) for it, e in entries if e["b"]["text"] is None]
            fixed = sum((it["id"], lang, it["seed"], kind) in recovered for it, _ in rejected)
            loops = [e["c"]["loop"] for _, e in entries if e["c"].get("loop")]
            empty = [[not r["candidates"] for r in lp["rounds"]] for lp in loops]
            hit_runs = [lp for lp, e in zip(loops, empty) if any(e)]
            out.append(f"| {lang.upper()}, {kind} | {len(rejected)} | {fixed} | {len(loops)} "
                       f"| {sum(len(lp['rounds']) for lp in loops)} | {sum(map(sum, empty))} "
                       f"| {sum(r['retry'] for lp in loops for r in lp['rounds'])} | {len(hit_runs)} "
                       f"| {sum(lp['final'] is not None for lp in hit_runs)} "
                       f"| {sum(lp['final'] is None for lp in loops)} |")
    notes = []
    for lang in langs:
        its = [it for it in items if it["lang"] == lang]
        notes.append(f"{lang.upper()}: {sum(len(it['a']['tries']) > 1 for it in its)} of {len(its)} items needed "
                     f"another try, and {sum(not it['a']['text'] for it in its)} ended without a translation")
    loops = [e["c"]["loop"] for it in items for e in it["budgets"].values() if e["c"].get("loop")]
    after = {"the first prompt again (a retry)": 0, "the revision of the best candidate again": 0, "none: it was the last round": 0}
    for lp in loops:
        for i, r in enumerate(lp["rounds"]):
            if not r["candidates"]:
                nxt = lp["rounds"][i + 1] if i + 1 < len(lp["rounds"]) else None
                after["none: it was the last round" if nxt is None else
                      "the first prompt again (a retry)" if nxt["retry"] else "the revision of the best candidate again"] += 1
    failed = [r for lp in loops for r in lp["rounds"] if not r["candidates"]]
    rescuable = sum(bool(parse_candidates((r["raw"] or "").replace("\\'", "'"))[0]) for r in failed)
    wrong_b = sum(" candidates instead of " in (e["b"].get("parse_error") or "") for it in items for e in it["budgets"].values())
    wrong_c = sum(" candidates instead of " in (r.get("parse_error") or "") for lp in loops for r in lp["rounds"])
    slashes = {s: sum(1 for r in rows if r["system"] == s and r["text"] and "\\" in r["text"]
                      and (s != "a" or r["budget"] == min(it_budgets(items)))) for s in SYSTEMS}
    return out + ["",
                  "(a) asks again with the next seed after an unparsable answer, at most 3 times. "
                  + "; ".join(notes) + ". Without (a), (c) has no output either.",
                  "",
                  "After a (c) round without a candidate, the next round sent: "
                  + "; ".join(f"{k} {v}" for k, v in after.items()) + f". The sensitivity rule (`\\'` read as `'`) "
                  f"would have given candidates in {rescuable} of these {len(failed)} rounds; (c) is left as it ran, "
                  "because its later rounds depended on each failure.",
                  "",
                  f"Answers with fewer or more candidates than the 4 asked for (kept, and scored): (b) {wrong_b}, (c)'s "
                  f"rounds {wrong_c}. Outputs that contain a literal backslash (counted as they are): "
                  + ", ".join(f"({s}) {n}" for s, n in slashes.items()) + "."]


def it_budgets(items: list[dict[str, Any]]) -> list[str]:
    return sorted({k for it in items for k in it["budgets"]})


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
    rows = outputs(items, cfg["length_counter"]["counter"])
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
        lines += diff_table(rs, title, bool(judged)) + [""]
    lines += parse_table(items, rows) + [""]
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
