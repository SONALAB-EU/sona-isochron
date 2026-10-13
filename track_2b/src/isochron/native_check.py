"""The native-speaker check (docs/eval_protocol.md, "Native-speaker check"; instructions in
docs/native_check.md).

build-step4 (the sheet to use): 50 German lines from step 4 on test. 25 English sources are drawn with a
fixed seed; for each, the plain translation (a) and ours (c, translate then shorten, under the syllable
budget), both from generation seed 0. The rows are shuffled, and nothing on the sheet tells the system. The
checker reads the English source and the German output and marks the meaning (kept / minor loss / wrong),
added information (yes/no) and natural German (yes/no). The key is a separate file, never shown to the
checker: the system, and the verdicts of the evaluation NLI (the loop's own model), the second NLI
(isochron.meaning_check, when its scores exist) and the final judge.

build (the backup, from step 2): 50 German lines from step 2 on test, 25 without the loop (the closest
round-0 candidate) and 25 with it, at levels 90, 80, 70 and 60 % in turn, all seeded. A line with no
output takes the next seed. The checker marks whether the shortened line adds or drops information.

controls: review sheets for the control pairs that Claude wrote. The checker confirms that each variant
does what its type says (the identity pairs are left out). German: the hard controls and the German NLI
pairs. French: the French NLI pairs.

xlsx: the step 4 sheet as the file to send to the checker, in a folder of its own that must not hold the
key. The same rows in the same order, with drop-down lists for the three marks, and an instructions tab
with three worked examples (made up by Claude, not among the lines). Nothing in it tells the system.

score: for the step 4 sheet (CSV or XLSX), rates per system with 95 % Wilson intervals, and agreement
(share of lines, Cohen's kappa) with each automatic check; for the step 2 sheet, agreement on "added" and
"dropped". It first checks that every marked line still has its own English and German text, so rows
that were sorted apart from their line numbers cannot be scored against the wrong key.

    uv run python -m isochron.native_check build-step4 RUN_DIR --nli-cache FILE [--nli2-cache FILE]
    uv run python -m isochron.native_check build RUN_DIR [--out results/native_check]
    uv run python -m isochron.native_check controls [--out results/native_check]
    uv run python -m isochron.native_check xlsx [--sheet results/native_check/step4_sheet_de.csv] [--out FILE]
    uv run python -m isochron.native_check score SHEET.csv|SHEET.xlsx [--key KEY.csv] [--out FILE]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import textwrap
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from isochron import xlsx
from isochron.language import check as check_language
from isochron.metrics.length import hit, length
from isochron.provenance import git_commit
from isochron.schema import ControlPair, read_jsonl

N_LINES = 50
LEVELS = (90, 80, 70, 60)
SHEET_FIELDS = ("line", "original", "shortened", "adds_information", "drops_information", "grammar_problem", "comment")
KEY_FIELDS = ("line", "run", "id", "level", "seed", "system", "nli_added", "nli_dropped", "judge_recall",
              "judge_dropped_or_changed", "judge_added")
YES_NO = {"yes": True, "ja": True, "y": True, "j": True, "no": False, "nein": False, "n": False}
N_SOURCES = 25
STEP4_FIELDS = ("line", "english_source", "german_output", "meaning", "added_info", "natural_german", "comment")
STEP4_KEY = ("line", "run", "id", "seed", "system", "budget", "kept_plain", "same_text_as_its_pair", "fits_budget",
             "nli_kept_ref", "nli_added_ref", "nli_dropped_ref", "nli_kept_src",
             "nli2_kept_ref", "nli2_added_ref", "nli2_dropped_ref", "nli2_kept_src",
             "judge_recall", "judge_dropped_or_changed", "judge_added", "judge_complete")
MEANING = {"kept": "kept", "erhalten": "kept", "minor loss": "minor loss", "kleiner verlust": "minor loss",
           "geringer verlust": "minor loss", "wrong": "wrong", "falsch": "wrong"}

# The XLSX for the checker (docs/native_check.md). Its instructions repeat the CSV sheet's, word for word
# where they can; the worked examples are made up and are not among the lines.
XLSX_SHEET = "Lines"
XLSX_COLUMNS = (  # field, header on the sheet, width in characters
    ("line", "Line", 6), ("english_source", "English source", 50), ("german_output", "German translation", 50),
    ("meaning", "Meaning", 13), ("added_info", "Added info", 11), ("natural_german", "Natural German", 17),
    ("comment", "Comment (optional)", 40))
XLSX_DROP_DOWNS = (  # field, options, prompt shown when a cell is selected
    ("meaning", ("kept", "minor loss", "wrong"), "Does the German say what the English says?"),
    ("added_info", ("yes", "no"), "yes if the German says something the English does not."),
    ("natural_german", ("yes", "no"), "yes if it is correct, natural German you would accept in a dubbed film. "
                                      "Ignore punctuation."))
INSTRUCTIONS_TITLE = "Native-speaker check: English → German"
INSTRUCTIONS_INTRO = (
    'The tab "Lines" has {n} rows. Each row has an English sentence and a German translation of it, which may '
    "be shorter than a full translation. Read both, then fill in the row: Meaning, Added info and Natural German "
    "from the drop-down lists (click the cell, then its arrow), and a comment if you like.")
INSTRUCTIONS_COLUMNS = (
    ("Meaning", "kept: the German says everything the English says.\n"
                "minor loss: a detail is missing or weaker, such as a number, a name, a time, a condition, or words "
                "such as almost, very, local, according to the police.\n"
                "wrong: the German says something else, or misses the main point.\n"
                "A missing qualifier or linking word (mostly, some, however, of course) is a minor loss. A detail "
                "replaced by another one is a minor loss if the main point still holds, and wrong if it does not."),
    ("Added info", "yes if the German says something the English does not: a new fact, a detail, or a stronger "
                   "claim. Otherwise no. A dropped qualifier counts under Meaning, not here."),
    ("Natural German", "yes if it is correct, natural German that you would accept in a dubbed film. Otherwise no. "
                       "A formal, written style is fine. Ignore punctuation and quotation marks (a missing full "
                       "stop, ' or \" instead of „ “): judge the words as they would be spoken."),
    ("Comment", "Optional: what was lost, added or unnatural, in a few words."))
WORKED_EXAMPLES = (  # English, German, meaning, added info, natural German, why
    ("The museum, which opened in 1998, now attracts around two million visitors every year.",
     "Das 1998 eröffnete Museum zieht heute jährlich rund zwei Millionen Besucher an.",
     "kept", "no", "yes",
     "Shorter, but nothing is missing: opened in 1998, now, around two million, every year. Nothing is added, "
     "and it reads naturally."),
    ("The new library, which cost 12 million euros, will open in the city centre next month.",
     "Die neue Bibliothek im Stadtzentrum wird nächsten Monat eröffnet.",
     "minor loss", "no", "yes",
     "The cost, 12 million euros, is missing: a detail is lost, but the main point is kept. Nothing is added, "
     "and it reads naturally."),
    ("The mayor said the bridge would stay closed until next spring.",
     "Der Bürgermeister hat die Entscheidung genommen, die Brücke wegen Bauarbeiten im Frühling zu schließen.",
     "wrong", "yes", "no",
     "Meaning: in the English the bridge stays closed until spring; in the German it will be closed in spring. "
     'Added: "wegen Bauarbeiten" (because of construction work) is not in the English, and a decision is a '
     'stronger claim than "said". Natural: "die Entscheidung genommen" copies the English "took the decision"; '
     'German says "getroffen".'))
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
    commit = git_commit()  # before the files are rewritten: rewriting a tracked file would mark the tree dirty
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
    with open(out / "step2_sheet_de.csv", "w", encoding="utf-8-sig", newline="") as f:  # BOM: spreadsheets read UTF-8
        w = csv.DictWriter(f, fieldnames=SHEET_FIELDS)
        w.writeheader()
        for n, line in enumerate(lines, 1):
            w.writerow({"line": n, "original": line["original"], "shortened": line["shortened"], "adds_information": "",
                        "drops_information": "", "grammar_problem": "", "comment": ""})
    with open(out / "step2_key_de.csv", "w", encoding="utf-8", newline="") as f:
        f.write(f"# The key to step2_sheet_de.csv: never show it to the checker. Written by isochron.native_check on "
                f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC, git commit {commit}; run {run.name} "
                f"({cfg['model']}, {cfg['quantisation']}); NLI labels from the run's own check\n")
        w = csv.DictWriter(f, fieldnames=KEY_FIELDS)
        w.writeheader()
        for n, line in enumerate(lines, 1):
            w.writerow({"line": n, **{k: line[k] for k in KEY_FIELDS if k != "line"}})
    print(f"wrote {out / 'step2_sheet_de.csv'} and {out / 'step2_key_de.csv'} ({len(lines)} lines: "
          f"{sum(x['system'] == 'without' for x in lines)} without the loop, {sum(x['system'] == 'with' for x in lines)} with it)")


def full_stop(text: str) -> str:
    """The sheet's punctuation rule, the same for both systems (protocol v2.26): a line that does not end in
    . ! ? or … (before any closing quote or bracket) gets a full stop."""
    stripped = text.rstrip()
    return stripped if stripped.rstrip("\"'”“’»)]").endswith((".", "!", "?", "…")) else stripped + "."


def build_step4(run: Path, out: Path, nli_cache: Path, nli2_cache: Path | None = None,
                budget: str = "isosyllabic", seed: int = 0) -> None:
    from isochron.meaning_check import key, read_cache

    commit = git_commit()  # before the files are rewritten: rewriting a tracked file would mark the tree dirty
    cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
    if cfg["langs"] != ["de"] or cfg["split"] != "test":
        raise SystemExit(f"{run} is not a German step 4 test run")
    items = {it["id"]: it for it in map(json.loads, (run / "items.jsonl").read_text(encoding="utf-8").splitlines())
             if it and it["seed"] == seed}
    judged = {(j["id"], j["seed"]): j for j in map(json.loads, (run / "judge.jsonl").read_text(encoding="utf-8").splitlines()) if j}
    _, nli = read_cache(nli_cache)
    nli2 = read_cache(nli2_cache)[1] if nli2_cache else {}

    def usable(text: str | None) -> bool:
        return bool(text) and not check_language(text, "de").wrong

    eligible = sorted((i for i, it in items.items() if usable(it["a"]["text"]) and usable(it["budgets"][budget]["c"]["text"])),
                      key=int)
    chosen = random.Random(0).sample(eligible, N_SOURCES)
    rows = []
    for sid in chosen:
        it, entry, verdicts = items[sid], items[sid]["budgets"][budget], judged[(sid, seed)]
        for system, text, v in (("a", it["a"]["text"], verdicts["a"]), ("c", entry["c"]["text"], verdicts["budgets"][budget]["c"])):
            ref, src = nli[key(it["reference"], text)], nli[key(it["source"], text)]
            ref2, src2 = nli2.get(key(it["reference"], text)), nli2.get(key(it["source"], text))
            rows.append({"run": run.name, "id": sid, "seed": seed, "system": system, "budget": budget,
                         "kept_plain": entry["c"]["kept_plain"], "same_text_as_its_pair": it["a"]["text"] == entry["c"]["text"],
                         "fits_budget": hit(length(text, entry["unit"], "de", cfg["length_counter"]["counter"]), entry["target"]),
                         "english_source": it["source"], "german_output": text,
                         "nli_kept_ref": ref["kept"], "nli_added_ref": ref["added"], "nli_dropped_ref": ref["dropped"],
                         "nli_kept_src": src["kept"],
                         "nli2_kept_ref": ref2["kept"] if ref2 else "", "nli2_added_ref": ref2["added"] if ref2 else "",
                         "nli2_dropped_ref": ref2["dropped"] if ref2 else "", "nli2_kept_src": src2["kept"] if src2 else "",
                         "judge_recall": v.get("recall"),
                         "judge_dropped_or_changed": (v.get("dropped", 0) + v.get("changed", 0)) > 0,
                         "judge_added": v.get("added_any"),
                         "judge_complete": bool(v.get("valid") and v.get("recall") == 1 and not v.get("added_any"))})
    random.Random(1).shuffle(rows)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "step4_sheet_de.csv", "w", encoding="utf-8-sig", newline="") as f:  # BOM: spreadsheets read UTF-8
        w = csv.DictWriter(f, fieldnames=STEP4_FIELDS)
        w.writeheader()
        for n, row in enumerate(rows, 1):
            w.writerow({"line": n, "english_source": row["english_source"], "german_output": full_stop(row["german_output"]),
                        "meaning": "", "added_info": "", "natural_german": "", "comment": ""})
    with open(out / "step4_key_de.csv", "w", encoding="utf-8", newline="") as f:
        f.write(f"# The key to step4_sheet_de.csv: never show it to the checker. Written by isochron.native_check on "
                f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC, git commit {commit}; run {run.name} "
                f"({cfg['model']}, {cfg['quantisation']}), seed {seed}, (c) under the {budget} budget; NLI: "
                f"{nli_cache.name}" + (f", second NLI: {nli2_cache.name}" if nli2_cache else ", no second NLI yet") + "\n")
        w = csv.DictWriter(f, fieldnames=STEP4_KEY)
        w.writeheader()
        for n, row in enumerate(rows, 1):
            w.writerow({"line": n, **{k: row[k] for k in STEP4_KEY if k != "line"}})
    same = sum(r["same_text_as_its_pair"] for r in rows) // 2
    print(f"wrote {out / 'step4_sheet_de.csv'} and {out / 'step4_key_de.csv'} ({len(rows)} lines from {N_SOURCES} "
          f"sources; in {same} of them (c) kept the plain translation, so both lines read the same)")


def row_height(texts: list[tuple[str, float]]) -> float:
    """Points for a row whose cells wrap: 15 per line of the tallest cell, from its text and column width."""
    lines = max(sum(len(textwrap.wrap(part, max(1, int(0.8 * width)))) or 1 for part in value.split("\n"))
                for value, width in texts)  # 0.8: room for a wider font than Calibri
    return min(409.0, 15.0 * lines + 3)


def step4_xlsx(sheet: Path, out: Path) -> None:
    """The step 4 sheet as an XLSX for the checker: the same rows, drop-down lists, and instructions."""
    with open(sheet, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows or list(rows[0]) != list(STEP4_FIELDS):
        raise SystemExit(f"{sheet} is not a step 4 sheet (columns {', '.join(STEP4_FIELDS)})")
    if [r["line"] for r in rows] != [str(n) for n in range(1, len(rows) + 1)]:
        raise SystemExit(f"{sheet}: the lines are not numbered 1 to {len(rows)} in order")
    keys = sorted(p.name for p in out.parent.glob("*key*")) if out.parent.is_dir() else []
    if keys:
        raise SystemExit(f"{out.parent} holds {', '.join(keys)}: the checker's file goes in a folder without the key")
    by_source = Counter(r["english_source"] for r in rows)
    twice = set(by_source.values()) == {2}
    same = sum(len({r["german_output"] for r in rows if r["english_source"] == s}) == 1 for s in by_source)
    notes = ["Shorter wording is fine as long as nothing is lost. A shorter line is not a minor loss by itself.",
             ("Each English sentence appears twice, each time with its own German translation"
              + ("; sometimes the two are the same" if same else "") + ". Judge each row on its own, and mark both.")
             if twice else "Judge each row on its own. Two rows can read the same; mark both.",
             "If two options seem to fit, choose the closer one and say why in the comment.",
             "Please do not change the English or German text; write corrections in the comment.",
             "If a cell shows no arrow, type exactly kept, minor loss, wrong, yes or no.",
             "Please do not use a dictionary, a translator or a chatbot, and do not look the sentences up online.",
             "It takes about 30–45 minutes. Send the file back as .xlsx, under any name (Numbers: File > Export "
             "To > Excel; Google Sheets: File > Download > Microsoft Excel)."]
    wide = 95
    guide: list[list[xlsx.Cell]] = [[xlsx.Cell(INSTRUCTIONS_TITLE, xlsx.TITLE)], []]
    heights = {1: 22.0}

    def add(label: str, body: str, style: int = xlsx.BODY) -> None:
        guide.append([xlsx.Cell(label, xlsx.LABEL), xlsx.Cell(body, style)])
        heights[len(guide)] = row_height([(body, wide), (label, 18)])

    add("What to do", INSTRUCTIONS_INTRO.format(n=len(rows)))
    for label, body in INSTRUCTIONS_COLUMNS:
        add(label, body)
    add("Please note", "\n".join(f"• {note}" for note in notes))
    guide += [[], [xlsx.Cell("Three worked examples (made up; they are not among the lines)", xlsx.BOLD)]]
    for n, (english, german, meaning, added, natural, why) in enumerate(WORKED_EXAMPLES, 1):
        guide.append([xlsx.Cell(f"Example {n}", xlsx.BOLD)])
        add("English", english)
        add("German", german)
        add("Marks", f"Meaning: {meaning}   ·   Added info: {added}   ·   Natural German: {natural}")
        add("Why", why, xlsx.NOTE)
        guide.append([])
    guide.append([xlsx.Cell("Thank you!", xlsx.BOLD)])
    widths = [w for _, _, w in XLSX_COLUMNS]
    table = [[xlsx.Cell(label, xlsx.HEADER) for _, label, _ in XLSX_COLUMNS]]
    lines = {1: 20.0}
    for r in rows:
        table.append([xlsx.Cell(int(r["line"]), xlsx.NUMBER), xlsx.Cell(r["english_source"], xlsx.TEXT),
                      xlsx.Cell(r["german_output"], xlsx.TEXT),
                      *(xlsx.Cell(None, xlsx.INPUT) for _ in ("meaning", "added_info", "natural_german", "comment"))])
        lines[len(table)] = row_height([(r["english_source"], widths[1]), (r["german_output"], widths[2])])
    fields = [f for f, _, _ in XLSX_COLUMNS]
    drop_downs = [xlsx.DropDown(f"{xlsx.column(fields.index(f))}2:{xlsx.column(fields.index(f))}{len(rows) + 1}",
                                options, dict((f, label) for f, label, _ in XLSX_COLUMNS)[f], prompt)
                  for f, options, prompt in XLSX_DROP_DOWNS]
    xlsx.write(out, [xlsx.Sheet("Instructions", guide, [18, wide], heights, gridlines=False, fit_width=True),
                     xlsx.Sheet(XLSX_SHEET, table, widths, lines, freeze_header=True, drop_downs=drop_downs,
                                landscape=True, fit_width=True, repeat_header=True)])
    print(f"wrote {out} ({len(rows)} lines from {sheet}; send only this file; the key is not in it)")


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


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95 % Wilson score interval for k of n."""
    if not n:
        return float("nan"), float("nan")
    p, d = k / n, 1 + z * z / n
    centre, half = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return centre - half, centre + half


def rate(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.0f} % [{100 * lo:.0f}, {100 * hi:.0f}] ({k}/{n})" if n else "–"


STEP4_CHECKS = (  # name, the key's columns for: meaning kept and nothing added, information lost, information added
    ("Evaluation NLI (the loop's model), vs the reference", "nli_kept_ref", "nli_dropped_ref", "nli_added_ref"),
    ("Evaluation NLI, vs the English source", "nli_kept_src", None, None),
    ("Second NLI, vs the reference", "nli2_kept_ref", "nli2_dropped_ref", "nli2_added_ref"),
    ("Second NLI, vs the English source", "nli2_kept_src", None, None),
    ("Final judge (Qwen3-14B), vs the English source's facts", "judge_complete", "judge_dropped_or_changed", "judge_added"),
)


def read_marks(sheet: Path) -> dict[str, dict[str, str]]:
    """The checker's step 4 rows by line number, from the CSV sheet or the XLSX (its "Lines" tab)."""
    if sheet.suffix.lower() == ".xlsx":
        cells = xlsx.read(sheet, XLSX_SHEET)
        names = {label.lower(): f for f, label, _ in XLSX_COLUMNS} | {f: f for f in STEP4_FIELDS}
        fields = [names.get(h.strip().lower(), "") for h in cells[0]] if cells else []
        records = [{f: v for f, v in zip(fields, row) if f} for row in cells[1:]]
    else:
        with open(sheet, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fields, records = list(reader.fieldnames or []), list(reader)
    if "line" not in fields:
        raise SystemExit(f"{sheet}: no line column")
    marks: dict[str, dict[str, str]] = {}
    for r in records:
        line = (r.get("line") or "").strip()
        try:  # a spreadsheet may save 7 as 7.0 or 7.000000000000001
            number = float(line)
        except ValueError:
            pass
        else:
            if abs(number - round(number)) < 1e-6:
                line = str(round(number))
        if not line:
            if any((v or "").strip() for v in r.values()):
                raise SystemExit(f"{sheet}: a row without a line number has text or marks: "
                                 f"{next(v for v in r.values() if (v or '').strip())[:40]!r}")
            continue
        if line in marks:
            raise SystemExit(f"{sheet}: line {line} appears twice")
        marks[line] = r
    return marks


def check_texts(marks: dict[str, dict[str, str]], sheet: Path, original: Path) -> None:
    """Stop if a marked line's English or German text is not the one the sheet gave it (rows sorted apart from
    their line numbers would otherwise be scored against the wrong key)."""
    with open(original, encoding="utf-8-sig") as f:
        given = {r["line"]: r for r in csv.DictReader(f)}

    def norm(value: str | None) -> str:
        return " ".join(unicodedata.normalize("NFC", value or "").split())

    moved = [line for line, m in marks.items() if line in given and any(
        column in m and norm(m[column]) != norm(given[line][column]) for column in ("english_source", "german_output"))]
    unknown = [line for line in marks if line not in given]
    if marks and not any("english_source" in m or "german_output" in m for m in marks.values()):
        raise SystemExit(f"{sheet}: cannot check the texts, it has no English or German column (renamed headers?); "
                         "check by eye and score with --no-text-check")
    if moved or unknown:
        raise SystemExit(f"{sheet} does not match {original}: "
                         + (f"lines {', '.join(moved[:10])} have another text than the sheet gave them; " if moved else "")
                         + (f"lines {', '.join(unknown[:10])} are not on the sheet; " if unknown else "")
                         + "were rows sorted without their line numbers? If only the text was edited or re-encoded, "
                           "check by eye and score with --no-text-check")


def marked(m: dict[str, str] | None) -> tuple | None:
    """A line's marks, normalised, or None when its meaning is not marked."""
    meaning = MEANING.get(((m or {}).get("meaning") or "").strip().lower())
    return (meaning, yes_no((m or {}).get("added_info", "")), yes_no((m or {}).get("natural_german", ""))) \
        if meaning else None


def with_identical_pairs(marks: dict[str, dict[str, str]], rows: list[dict[str, str]],
                         original: Path) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    """Protocol v2.34: where both systems' German is identical in the sheet as rated, the rated copy's marks
    apply to both lines. Returns the marks and, per line, where they came from."""
    merged = {line: m for line, m in marks.items() if marked(m) is not None}
    origin = {line: "rated" for line in merged}
    with open(original, encoding="utf-8-sig") as f:
        text = {r["line"]: r["german_output"] for r in csv.DictReader(f)}
    by_id: dict[str, list[str]] = {}
    for r in rows:
        by_id.setdefault(r["id"], []).append(r["line"])
    for lines in by_id.values():
        if len(lines) == 2 and text[lines[0]] == text[lines[1]]:
            for x, y in (lines, lines[::-1]):
                if x not in merged and origin.get(y) == "rated":
                    merged[x], origin[x] = merged[y], f"copied from line {y} (identical German)"
    return merged, origin


def score_step4(sheet: Path, key: Path, out: Path, text_check: bool = True, original: Path | None = None) -> None:
    original = original or key.parent / "step4_sheet_de.csv"  # the sheet as the rater saw it
    raw = read_marks(sheet)
    if text_check and original.is_file():
        check_texts(raw, sheet, original)
    elif text_check:
        print(f"note: {original} not found, so the lines' texts were not checked")
    with open(key, encoding="utf-8") as f:
        rows = list(csv.DictReader(line for line in f if not line.startswith("#")))
    bad = [(line, column, m[column]) for line, m in raw.items() for column, ok in (
        ("meaning", lambda v: v.strip().lower() in MEANING), ("added_info", lambda v: yes_no(v) is not None),
        ("natural_german", lambda v: yes_no(v) is not None)) if (m.get(column) or "").strip() and not ok(m[column])]
    if bad:
        raise SystemExit(f"{sheet}: marks that are not on the lists: "
                         + "; ".join(f"line {line} {column} {value!r}" for line, column, value in bad[:10]))
    marks, origin = with_identical_pairs(raw, rows, original) if original.is_file() else (
        {line: m for line, m in raw.items() if marked(m) is not None}, {})
    partial = sorted((line for line, m in marks.items()
                      if 0 < sum(bool((m.get(c) or "").strip()) for c in ("meaning", "added_info", "natural_german")) < 3),
                     key=int)
    if partial:
        print(f"note: lines {', '.join(partial)} are only partly marked; a line counts once Meaning and Added info are")
    lines = []
    for r in rows:
        m = marks.get(r["line"])
        meaning = MEANING.get((m or {}).get("meaning", "").strip().lower())
        added = yes_no((m or {}).get("added_info", ""))
        if meaning and added is not None:
            lines.append({**r, "meaning": meaning, "added": added, "natural": yes_no(m.get("natural_german", ""))})
    names = {"a": "(a) plain translation", "c": "(c) ours: translate, then shorten"}
    table = ["| System | Lines | Meaning kept | Minor loss | Wrong | Adds information | Natural German |",
             "|--------|------:|--------------|------------|-------|------------------|----------------|"]
    for system, name in names.items():
        ls = [x for x in lines if x["system"] == system]
        nat = [x for x in ls if x["natural"] is not None]
        table.append(f"| {name} | {len(ls)} | " + " | ".join(rate(sum(x["meaning"] == v for x in ls), len(ls))
                                                         for v in ("kept", "minor loss", "wrong"))
                     + f" | {rate(sum(x['added'] for x in ls), len(ls))} | {rate(sum(x['natural'] for x in nat), len(nat))} |")
    agree = ["| Native speaker vs | On | Lines | Agree | Cohen's kappa |", "|---|---|---:|---:|---:|"]
    for name, ok, lost, added in STEP4_CHECKS:
        for on, column, human in (("kept, nothing added", ok, lambda x: x["meaning"] == "kept" and not x["added"]),
                                  ("information lost (minor or wrong)", lost, lambda x: x["meaning"] != "kept"),
                                  ("information added", added, lambda x: x["added"])):
            if column is None:
                continue
            pairs = [(human(x), x[column] == "True") for x in lines if x[column] in ("True", "False")]
            if not pairs:
                continue
            k = kappa([p[0] for p in pairs], [p[1] for p in pairs])
            agree.append(f"| {name} | {on} | {len(pairs)} | {100 * sum(a == b for a, b in pairs) / len(pairs):.0f} % "
                         f"| {'–' if k is None else f'{k:.2f}'} |")
    copied = sum(origin.get(r["line"], "").startswith("copied") for r in rows if r["line"] in marks)
    unmarked = sorted((r["line"] for r in rows if r["line"] not in marks), key=int)
    status = (f"Descriptive. {len(unmarked)} of {len(rows)} lines have no rating: where a pair's two German "
              "lines differ, the rater rated one and marked the other a duplicate. So the per-system rates come "
              "from different sentences, not from pairs, and the systems are not compared by a test."
              if unmarked else "All lines are rated.")
    md = ["# Native-speaker check on step 4: rates and agreement", "", status, "",
          f"- Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC; git commit {git_commit()}",
          f"- Sheet: `{sheet}`; key: `{key}`; {len(lines)} of {len(rows)} lines marked (meaning and added "
          f"information), {copied} of them copied from an identical pair (protocol v2.34); texts checked against "
          f"`{original}`",
          "- Rater: one German native speaker.",
          "- The checker saw the English source and one German output per line, not the system. TTS: none.",
          "- 95 % Wilson intervals. Lines left empty are skipped.", "", *table, "", *agree, ""]
    out.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


def score(sheet: Path, key: Path | None, out: Path | None, text_check: bool = True,
          original: Path | None = None) -> None:
    if sheet.suffix.lower() not in (".xlsx", ".csv"):
        raise SystemExit(f"{sheet}: send or convert it as .xlsx or .csv")
    if sheet.suffix.lower() == ".xlsx":
        fields: list[str] = ["english_source"]  # only the step 4 sheet comes as an XLSX
    else:
        with open(sheet, encoding="utf-8-sig") as f:
            fields = list(csv.DictReader(f).fieldnames or [])
    if "english_source" in fields:
        score_step4(sheet, key or Path("results/native_check/step4_key_de.csv"),
                    out or Path("results/native_check_step4_agreement.md"), text_check, original)
    else:
        score_step2(sheet, key or Path("results/native_check/step2_key_de.csv"),
                    out or Path("results/native_check_agreement.md"))


def score_step2(sheet: Path, key: Path, out: Path) -> None:
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
    b4 = sub.add_parser("build-step4", help="the sheet to use: step 4 test outputs, (a) and (c)")
    b4.add_argument("run", type=Path)
    b4.add_argument("--nli-cache", type=Path, required=True, help="the evaluation NLI's cache (isochron.step4_report)")
    b4.add_argument("--nli2-cache", type=Path, help="the second NLI's scores (isochron.meaning_check)")
    b4.add_argument("--budget", default="isosyllabic", choices=("isosyllabic", "isometric"))
    b4.add_argument("--out", type=Path, default=Path("results/native_check"))
    b = sub.add_parser("build", help="the backup: step 2 test outputs")
    b.add_argument("run", type=Path)
    b.add_argument("--out", type=Path, default=Path("results/native_check"))
    c = sub.add_parser("controls")
    c.add_argument("--out", type=Path, default=Path("results/native_check"))
    x = sub.add_parser("xlsx", help="the step 4 sheet as the XLSX to send to the checker")
    x.add_argument("--sheet", type=Path, default=Path("results/native_check/step4_sheet_de.csv"))
    x.add_argument("--out", type=Path, default=Path("results/native_check/rater/german_lines.xlsx"),
                   help="in a folder without the key")
    s = sub.add_parser("score")
    s.add_argument("sheet", type=Path, help="the filled sheet: CSV, or the XLSX for step 4")
    s.add_argument("--as-rated", type=Path, help="step 4: the sheet as the rater saw it (default: step4_sheet_de.csv "
                                                  "next to the key); its texts are checked and its identical pairs share marks")
    s.add_argument("--key", type=Path, help="default: the key that matches the sheet")
    s.add_argument("--out", type=Path, help="default: results/native_check_step4_agreement.md (step 4), "
                                             "results/native_check_agreement.md (step 2)")
    s.add_argument("--no-text-check", action="store_true",
                   help="score step 4 even if a line's text differs from the sheet's (check by eye first)")
    args = ap.parse_args(argv)
    if args.cmd == "build-step4":
        build_step4(args.run, args.out, args.nli_cache, args.nli2_cache, args.budget)
    elif args.cmd == "build":
        build(args.run, args.out)
    elif args.cmd == "controls":
        controls(args.out)
    elif args.cmd == "xlsx":
        step4_xlsx(args.sheet, args.out)
    else:
        score(args.sheet, args.key, args.out, not args.no_text_check, args.as_rated)


if __name__ == "__main__":
    main()
