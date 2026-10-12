"""The native-speaker check (docs/eval_protocol.md, "Native-speaker check"; instructions in
docs/native_check.md).

build: 50 German lines from step 2 on test, for a native speaker who is not told which system produced
each line. They come from 50 different sentences: 25 without the loop (the closest round-0 candidate) and
25 with it, at levels 90, 80, 70 and 60 % in turn, all seeded. A line with no output takes the next seed.
The checker marks whether the shortened line adds or drops information. The key is a separate file, never
shown to the checker. It holds the system, the NLI's labels and the final judge's verdict for each line.

controls: review sheets for the control pairs that Claude wrote. The checker confirms that each variant
does what its type says (the identity pairs are left out). German: the hard controls and the German NLI
pairs. French: the French NLI pairs.

score: agreement of the filled-in sheet with the NLI and with the judge, on "added" and on "dropped"
(share of lines that agree, and Cohen's kappa).

    uv run python -m isochron.native_check build RUN_DIR [--out results/native_check]
    uv run python -m isochron.native_check controls [--out results/native_check]
    uv run python -m isochron.native_check score SHEET.csv [--key KEY.csv] [--out results/native_check_agreement.md]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from isochron.language import check as check_language
from isochron.provenance import git_commit
from isochron.schema import ControlPair, read_jsonl

N_LINES = 50
LEVELS = (90, 80, 70, 60)
SHEET_FIELDS = ("line", "original", "shortened", "adds_information", "drops_information", "grammar_problem", "comment")
KEY_FIELDS = ("line", "run", "id", "level", "seed", "system", "nli_added", "nli_dropped", "judge_recall",
              "judge_dropped_or_changed", "judge_added")
YES_NO = {"yes": True, "ja": True, "y": True, "j": True, "no": False, "nein": False, "n": False}
CONTROL_TYPES = {
    "paraphrase": "same meaning, other words",
    "same_meaning": "same meaning, one small edit",
    "clause_deleted": "one piece of information removed",
    "clause_inserted": "one made-up piece of information added",
    "negation": "the meaning is negated",
    "modal_changed": "one modal changed (can / must / should ...)",
    "number_changed": "one number changed",
    "qualifier_changed": "one qualifier changed or removed (almost, very, local ...)",
    "fact_inserted": "one made-up fact added",
}


def build(run: Path, out: Path) -> None:
    cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
    if cfg["lang"] != "de" or cfg["split"] != "test":
        raise SystemExit(f"{run} is not a German test run")
    items = {(it["id"], it["level"], it["seed"]): it
             for it in map(json.loads, (run / "items.jsonl").read_text(encoding="utf-8").splitlines()) if it}
    judged = {(j["id"], j["level"], j["seed"]): j
              for j in map(json.loads, (run / "judge.jsonl").read_text(encoding="utf-8").splitlines()) if j}
    ids = sorted({key[0] for key in items}, key=int)
    chosen = random.Random(0).sample(ids, N_LINES)
    systems = ["without"] * (N_LINES // 2) + ["with"] * (N_LINES - N_LINES // 2)
    random.Random(1).shuffle(systems)
    lines = []
    for k, (sid, system) in enumerate(zip(chosen, systems)):
        level = LEVELS[k % len(LEVELS)]
        for seed in (0, 1, 2):
            it = items[(sid, level, seed)]
            cand = it["closest_round0"] if system == "without" else it["final"]
            if cand and not check_language(cand["text"], "de").wrong:
                break
        else:
            raise SystemExit(f"sentence {sid} at level {level} has no German output in any seed")
        verdict = judged[(sid, level, seed)][system]
        lines.append({"run": run.name, "id": sid, "level": level, "seed": seed, "system": system,
                      "original": it["input"], "shortened": cand["text"], "nli_added": cand["added"],
                      "nli_dropped": cand["dropped"], "judge_recall": verdict.get("recall"),
                      "judge_dropped_or_changed": (verdict.get("dropped", 0) + verdict.get("changed", 0)) > 0,
                      "judge_added": verdict.get("added_any")})
    random.Random(2).shuffle(lines)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "sheet_de.csv", "w", encoding="utf-8-sig", newline="") as f:  # BOM: spreadsheets read UTF-8
        w = csv.DictWriter(f, fieldnames=SHEET_FIELDS)
        w.writeheader()
        for n, line in enumerate(lines, 1):
            w.writerow({"line": n, "original": line["original"], "shortened": line["shortened"], "adds_information": "",
                        "drops_information": "", "grammar_problem": "", "comment": ""})
    with open(out / "key_de.csv", "w", encoding="utf-8", newline="") as f:
        f.write(f"# The key to sheet_de.csv: never show it to the checker. Written by isochron.native_check on "
                f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC, git commit {git_commit()}; run {run.name} "
                f"({cfg['model']}, {cfg['quantisation']}); NLI labels from the run's own check\n")
        w = csv.DictWriter(f, fieldnames=KEY_FIELDS)
        w.writeheader()
        for n, line in enumerate(lines, 1):
            w.writerow({"line": n, **{k: line[k] for k in KEY_FIELDS if k != "line"}})
    print(f"wrote {out / 'sheet_de.csv'} and {out / 'key_de.csv'} ({len(lines)} lines: "
          f"{sum(x['system'] == 'without' for x in lines)} without the loop, {sum(x['system'] == 'with' for x in lines)} with it)")


def controls(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    sources = {"de": [Path("data/judge_controls_de.jsonl"), Path("data/nli_controls.jsonl")],
               "fr": [Path("data/nli_controls.jsonl")]}
    for lang, files in sources.items():
        pairs = [p for path in files for p in read_jsonl(path, ControlPair) if p.lang == lang and p.control != "identity"]
        with open(out / f"controls_{lang}.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=("pair", "type", "should_be", "original", "variant", "edit",
                                              "correct_as_described", "comment"))
            w.writeheader()
            for p in pairs:
                w.writerow({"pair": p.id, "type": p.control, "should_be": CONTROL_TYPES[p.control], "original": p.source,
                            "variant": p.output, "edit": p.note or "", "correct_as_described": "", "comment": ""})
        print(f"wrote {out / f'controls_{lang}.csv'} ({len(pairs)} pairs)")


def yes_no(value: str) -> bool | None:
    return YES_NO.get(value.strip().lower()) if value and value.strip() else None


def kappa(a: list[bool], b: list[bool]) -> float | None:
    """Cohen's kappa for two yes/no ratings of the same lines."""
    n = len(a)
    if not n:
        return None
    observed = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return None if expected == 1 else (observed - expected) / (1 - expected)


def score(sheet: Path, key: Path, out: Path) -> None:
    with open(sheet, encoding="utf-8-sig") as f:
        marks = {r["line"]: r for r in csv.DictReader(f)}
    with open(key, encoding="utf-8") as f:
        rows = list(csv.DictReader(line for line in f if not line.startswith("#")))
    lines = [(marks[r["line"]], r) for r in rows if r["line"] in marks]
    filled = [(m, r) for m, r in lines
              if yes_no(m["adds_information"]) is not None and yes_no(m["drops_information"]) is not None]
    table = ["| Native speaker vs | On | Lines | Agree | Cohen's kappa |", "|---|---|---:|---:|---:|"]
    for other, field_added, field_dropped in (("NLI", "nli_added", "nli_dropped"),
                                              ("final judge", "judge_added", "judge_dropped_or_changed")):
        for on, mark, field in (("added", "adds_information", field_added), ("dropped", "drops_information", field_dropped)):
            pairs = [(yes_no(m[mark]), r[field] == "True") for m, r in filled if r[field] in ("True", "False")]
            a, b = [p[0] for p in pairs], [p[1] for p in pairs]
            k = kappa(a, b)
            agree = f"{100 * sum(x == y for x, y in pairs) / len(pairs):.0f} %" if pairs else "–"
            table.append(f"| {other} | {on} | {len(pairs)} | {agree} | {'–' if k is None else f'{k:.2f}'} |")
    by_system = {s: [m for m, r in filled if r["system"] == s] for s in ("without", "with")}
    md = ["# Native-speaker check: agreement", "",
          f"- Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC; git commit {git_commit()}",
          f"- Sheet: `{sheet}`; key: `{key}`; {len(filled)} of {len(rows)} lines marked",
          "- TTS: none. The checker did not see which system produced a line.", "", *table, "",
          "Share of lines the native speaker marks as dropping information, by system: "
          + "; ".join(f"{s} the loop {sum(yes_no(m['drops_information']) for m in ms)}/{len(ms)}" for s, ms in by_system.items()),
          ""]
    out.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("run", type=Path)
    b.add_argument("--out", type=Path, default=Path("results/native_check"))
    c = sub.add_parser("controls")
    c.add_argument("--out", type=Path, default=Path("results/native_check"))
    s = sub.add_parser("score")
    s.add_argument("sheet", type=Path)
    s.add_argument("--key", type=Path, default=Path("results/native_check/key_de.csv"))
    s.add_argument("--out", type=Path, default=Path("results/native_check_agreement.md"))
    args = ap.parse_args(argv)
    if args.cmd == "build":
        build(args.run, args.out)
    elif args.cmd == "controls":
        controls(args.out)
    else:
        score(args.sheet, args.key, args.out)


if __name__ == "__main__":
    main()
