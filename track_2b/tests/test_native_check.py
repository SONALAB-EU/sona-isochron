"""The native-speaker sheet: blind, balanced lines with a separate key, and the agreement scorer."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from isochron import native_check


def fake_run(tmp_path: Path) -> Path:
    run = tmp_path / "hpc_8b_step2_de_test"
    run.mkdir()
    (run / "config.json").write_text(json.dumps({"lang": "de", "split": "test", "model": "m", "quantisation": "BF16"}),
                                     encoding="utf-8")
    items, judged = [], []
    for i in range(60):
        for level in native_check.LEVELS:
            cand = {"text": f"Die Stadt {i} hat {level} Häuser.", "added": i % 2 == 0, "dropped": i % 3 == 0}
            items.append({"id": str(i), "level": level, "seed": 0, "input": f"Die große Stadt {i} hat {level} Häuser.",
                          "closest_round0": cand, "final": cand})
            v = {"valid": True, "recall": 1.0, "dropped": 0, "changed": int(i % 3 == 0), "added_any": i % 2 == 0}
            judged.append({"id": str(i), "level": level, "seed": 0, "without": v, "with": v})
    (run / "items.jsonl").write_text("".join(json.dumps(x) + "\n" for x in items), encoding="utf-8")
    (run / "judge.jsonl").write_text("".join(json.dumps(x) + "\n" for x in judged), encoding="utf-8")
    return run


def test_sheet_is_blind_balanced_and_scored(tmp_path: Path) -> None:
    out = tmp_path / "check"
    native_check.build(fake_run(tmp_path), out)
    with open(out / "step2_sheet_de.csv", encoding="utf-8-sig") as f:
        sheet = list(csv.DictReader(f))
    with open(out / "step2_key_de.csv", encoding="utf-8") as f:
        key = list(csv.DictReader(line for line in f if not line.startswith("#")))
    assert len(sheet) == len(key) == 50 and list(sheet[0]) == list(native_check.SHEET_FIELDS)
    assert not {"system", "level", "seed", "id"} & set(sheet[0])  # nothing on the sheet tells the system
    assert sorted(r["system"] for r in key).count("with") == 25 and len({r["id"] for r in key}) == 50
    # the checker marks exactly what the NLI says: full agreement with the NLI
    for row, k in zip(sheet, key):
        row["adds_information"] = "ja" if k["nli_added"] == "True" else "nein"
        row["drops_information"] = "yes" if k["nli_dropped"] == "True" else "no"
    filled = tmp_path / "filled.csv"
    with open(filled, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=native_check.SHEET_FIELDS)
        w.writeheader()
        w.writerows(sheet)
    report = tmp_path / "agreement.md"
    native_check.score(filled, out / "step2_key_de.csv", report)
    text = report.read_text(encoding="utf-8")
    assert "| NLI | added | 50 | 100 % | 1.00 |" in text and "| NLI | dropped | 50 | 100 % | 1.00 |" in text


def test_kappa() -> None:
    assert native_check.kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert native_check.kappa([True, True], [True, True]) is None
    assert round(native_check.kappa([True, True, False, False], [True, False, True, False]), 2) == 0.0


def fake_step4_run(tmp_path: Path) -> tuple[Path, Path]:
    from isochron.meaning_check import key

    run = tmp_path / "hpc_8b_step4_test"
    run.mkdir()
    (run / "config.json").write_text(json.dumps({"langs": ["de"], "split": "test", "model": "m", "quantisation": "BF16",
                                                 "length_counter": {"counter": "espeak"}}), encoding="utf-8")
    items, judged, cache = [], [], [json.dumps({"nli": "stub"})]
    for i in range(30):
        source = f"The old town number {i} has many beautiful houses and a large church."
        reference = f"Die alte Stadt Nummer {i} hat viele schöne Häuser und eine große Kirche."
        plain = f"Die alte Stadt Nummer {i} hat viele schöne Häuser und eine große Kirche."
        short = plain if i % 5 == 0 else f"Die Stadt Nummer {i} hat schöne Häuser und eine Kirche."
        items.append({"id": str(i), "lang": "de", "seed": 0, "source": source, "reference": reference,
                      "a": {"text": plain}, "budgets": {"isosyllabic": {"unit": "syllables", "target": 15,
                                                                       "c": {"text": short, "kept_plain": i % 5 == 0}}}})
        v = {"valid": True, "recall": 1.0 if i % 2 else 0.5, "dropped": i % 2 == 0, "changed": 0, "added_any": False}
        judged.append({"id": str(i), "lang": "de", "seed": 0, "a": v, "budgets": {"isosyllabic": {"c": v}}})
        for text in {plain, short}:
            kept = text == plain or i % 3 != 0
            for premise in (reference, source):
                cache.append(json.dumps({"key": key(premise, text), "m": {"kept": kept, "added": False, "dropped": not kept}}))
    (run / "items.jsonl").write_text("".join(json.dumps(x) + "\n" for x in items), encoding="utf-8")
    (run / "judge.jsonl").write_text("".join(json.dumps(x) + "\n" for x in judged), encoding="utf-8")
    (tmp_path / "nli.jsonl").write_text("\n".join(cache) + "\n", encoding="utf-8")
    return run, tmp_path / "nli.jsonl"


def test_step4_sheet_is_blind_paired_and_scored(tmp_path: Path) -> None:
    run, cache = fake_step4_run(tmp_path)
    out = tmp_path / "check"
    native_check.build_step4(run, out, cache)
    with open(out / "step4_sheet_de.csv", encoding="utf-8-sig") as f:
        sheet = list(csv.DictReader(f))
    with open(out / "step4_key_de.csv", encoding="utf-8") as f:
        key = list(csv.DictReader(line for line in f if not line.startswith("#")))
    assert len(sheet) == len(key) == 50 and list(sheet[0]) == list(native_check.STEP4_FIELDS)
    assert not {"system", "id", "seed", "budget"} & set(sheet[0])  # nothing on the sheet tells the system
    assert sorted(r["system"] for r in key).count("c") == 25 and len({r["id"] for r in key}) == 25
    assert all(sum(r["id"] == i for r in key) == 2 for i in {r["id"] for r in key})  # (a) and (c) of each source
    # the checker marks what the evaluation NLI says: full agreement with it on "kept, nothing added"
    for row, k in zip(sheet, key):
        row["meaning"] = "kept" if k["nli_kept_ref"] == "True" else "kleiner Verlust"
        row["added_info"] = "nein"
        row["natural_german"] = "ja"
    filled = tmp_path / "filled.csv"
    with open(filled, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=native_check.STEP4_FIELDS)
        w.writeheader()
        w.writerows(sheet)
    report = tmp_path / "agreement.md"
    native_check.score(filled, out / "step4_key_de.csv", report)
    text = report.read_text(encoding="utf-8")
    assert "| Evaluation NLI (the loop's model), vs the reference | kept, nothing added | 50 | 100 % | 1.00 |" in text
    assert "| (a) plain translation | 25 | 100 % [87, 100] (25/25) |" in text  # every plain line is kept here


def test_wilson() -> None:
    lo, hi = native_check.wilson(25, 25)
    assert round(100 * lo) == 87 and hi == 1.0
    lo, hi = native_check.wilson(0, 25)
    assert lo == 0.0 and round(100 * hi) == 13


def fill_xlsx(path: Path, out: Path, marks: dict[int, tuple[str, str, str]], swap: tuple[int, int] | None = None) -> None:
    """A copy of the checker's XLSX with marks filled in, as a spreadsheet saves them: Meaning as shared strings
    (one of them in two runs of rich text), the other marks as inline strings. swap exchanges two rows' line
    numbers, as sorting the texts without the line column would."""
    import re
    import zipfile

    with zipfile.ZipFile(path) as z:
        parts = {name: z.read(name).decode("utf-8") for name in z.namelist()}
    sheet, shared = parts["xl/worksheets/sheet2.xml"], parts["xl/sharedStrings.xml"]
    n = len(re.findall("<si>", shared))
    shared = shared.replace("</sst>", "<si><t>kept</t></si><si><r><t>minor </t></r><r><t>loss</t></r></si>"
                                      "<si><t>wrong</t></si></sst>")
    for line, (meaning, added, natural) in marks.items():
        row = line + 1
        index = n + ("kept", "minor loss", "wrong").index(meaning)
        sheet = sheet.replace(f'<c r="D{row}" s="3"/>', f'<c r="D{row}" s="3" t="s"><v>{index}</v></c>')
        for column, value in (("E", added), ("F", natural)):
            sheet = sheet.replace(f'<c r="{column}{row}" s="3"/>',
                                  f'<c r="{column}{row}" s="3" t="inlineStr"><is><t>{value}</t></is></c>')
    if swap:
        a, b = swap
        sheet = sheet.replace(f'<c r="A{a + 1}" s="7"><v>{a}</v></c>', "@A@").replace(
            f'<c r="A{b + 1}" s="7"><v>{b}</v></c>', f'<c r="A{b + 1}" s="7"><v>{a}</v></c>').replace(
            "@A@", f'<c r="A{a + 1}" s="7"><v>{b}</v></c>')
    parts["xl/worksheets/sheet2.xml"], parts["xl/sharedStrings.xml"] = sheet, shared
    with zipfile.ZipFile(out, "w") as z:
        for name, data in parts.items():
            z.writestr(name, data)


def test_step4_xlsx_is_blind_has_drop_downs_and_is_scored(tmp_path: Path) -> None:
    import zipfile

    import pytest

    from isochron import xlsx

    run, cache = fake_step4_run(tmp_path)
    out = tmp_path / "check"
    native_check.build_step4(run, out, cache)
    rater = out / "rater" / "german_lines.xlsx"
    native_check.step4_xlsx(out / "step4_sheet_de.csv", rater)
    first = rater.read_bytes()
    native_check.step4_xlsx(out / "step4_sheet_de.csv", rater)
    assert rater.read_bytes() == first  # the same sheet gives the same bytes
    with open(out / "step4_sheet_de.csv", encoding="utf-8-sig") as f:
        sheet = list(csv.DictReader(f))
    with open(out / "step4_key_de.csv", encoding="utf-8") as f:
        key = list(csv.DictReader(line for line in f if not line.startswith("#")))
    # the rows, in the sheet's order, under the XLSX's headers
    cells = xlsx.read(rater, "Lines")
    assert cells[0] == [label for _, label, _ in native_check.XLSX_COLUMNS]
    assert [r[:3] for r in cells[1:]] == [[r["line"], r["english_source"], r["german_output"]] for r in sheet]
    assert all(r[3:] == ["", "", "", ""] for r in cells[1:])
    # two tabs, instructions first, nothing hidden, no document properties; nothing tells the system
    with zipfile.ZipFile(rater) as z:
        names = z.namelist()
        text = "\n".join(z.read(n).decode("utf-8") for n in names)
        book, lines_xml = z.read("xl/workbook.xml").decode(), z.read("xl/worksheets/sheet2.xml").decode()
    assert not any(n.startswith("docProps/") for n in names) and "hidden" not in text
    assert book.index('name="Instructions"') < book.index('name="Lines"')
    for word in ("system", "plain", "ours", "loop", "budget", "isochron", "Apertus", run.name, "kept_plain",
                 "isosyllabic", "syllable", "NLI", "Qwen", "step 4", "step4"):
        assert not re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE), word
    assert "(a)" not in text and "(c)" not in text
    # drop-down lists on the three mark columns, for every line
    for column, options in (("D", "kept,minor loss,wrong"), ("E", "yes,no"), ("F", "yes,no")):
        assert re.search(f'sqref="{column}2:{column}51"><formula1>"{options}"</formula1>', lines_xml), column
    # the instructions tab: the columns' meanings and three worked examples, one per meaning mark
    guide = [row for row in xlsx.read(rater, "Instructions") if any(row)]
    marks = [row[1] for row in guide if row[0] == "Marks"]
    assert len(marks) == 3 and [m.split("   ·   ")[0] for m in marks] == [
        "Meaning: kept", "Meaning: minor loss", "Meaning: wrong"]
    assert {"Added info: yes", "Added info: no"} <= {m.split("   ·   ")[1] for m in marks}
    assert {"Natural German: yes", "Natural German: no"} <= {m.split("   ·   ")[2] for m in marks}
    examples = {row[1] for row in guide if row[0] in ("English", "German")}
    assert not examples & ({r["english_source"] for r in sheet} | {r["german_output"] for r in sheet})
    # the checker marks what the evaluation NLI says, in the XLSX: the same scores as from the CSV
    filled = tmp_path / "filled.xlsx"
    fill_xlsx(rater, filled, {int(k["line"]): ("kept" if k["nli_kept_ref"] == "True" else "minor loss", "no", "yes")
                              for k in key})
    report = tmp_path / "agreement.md"
    native_check.score(filled, out / "step4_key_de.csv", report)
    text = report.read_text(encoding="utf-8")
    assert "| Evaluation NLI (the loop's model), vs the reference | kept, nothing added | 50 | 100 % | 1.00 |" in text
    assert "| (a) plain translation | 25 | 100 % [87, 100] (25/25) |" in text
    # rows sorted apart from their line numbers are refused, not scored against the wrong key
    a, b = next((int(x["line"]), int(y["line"])) for x in sheet for y in sheet
                if x["english_source"] != y["english_source"])
    swapped = tmp_path / "swapped.xlsx"
    fill_xlsx(rater, swapped, {}, swap=(a, b))
    with pytest.raises(SystemExit, match="another text"):
        native_check.score(swapped, out / "step4_key_de.csv", report)
    # the checker's file never goes in the key's folder
    with pytest.raises(SystemExit, match="without the key"):
        native_check.step4_xlsx(out / "step4_sheet_de.csv", out / "step4_sheet_de.xlsx")


def test_xlsx_writes_and_reads_text_numbers_and_empty_cells(tmp_path: Path) -> None:
    import pytest

    from isochron import xlsx

    path = tmp_path / "t.xlsx"
    hard = 'Größe & <Maß> "29¾" x 24½" – l\'été\nzweite Zeile'
    xlsx.write(path, [xlsx.Sheet("Sheet_1", [[xlsx.Cell("a"), xlsx.Cell(None), xlsx.Cell(7)], [], [xlsx.Cell(hard)]],
                                 [10, 10, 10])])
    assert xlsx.read(path, "Sheet_1") == [["a", "", "7"], ["", "", ""], [hard, "", ""]]
    with pytest.raises(ValueError, match="no sheet"):
        xlsx.read(path, "Lines")
    with pytest.raises(ValueError, match="XML cannot hold"):
        xlsx.write(path, [xlsx.Sheet("S", [[xlsx.Cell("bell\x07")]], [10])])
    assert [xlsx.column(i) for i in (0, 25, 26, 701, 702)] == ["A", "Z", "AA", "ZZ", "AAA"]


def test_step4_scorer_refuses_marks_off_the_lists_and_rows_without_a_line(tmp_path: Path) -> None:
    import pytest

    run, cache = fake_step4_run(tmp_path)
    out = tmp_path / "check"
    native_check.build_step4(run, out, cache)
    with open(out / "step4_sheet_de.csv", encoding="utf-8-sig") as f:
        sheet = list(csv.DictReader(f))
    report = tmp_path / "agreement.md"
    for change, message in (({"meaning": "maybe"}, "not on the lists"), ({"line": "", "meaning": "kept"}, "without a line")):
        rows = [dict(r, meaning="kept", added_info="no", natural_german="yes") for r in sheet]
        rows[3].update(change)
        filled = tmp_path / "filled.csv"
        with open(filled, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=native_check.STEP4_FIELDS)
            w.writeheader()
            w.writerows(rows)
        with pytest.raises(SystemExit, match=message):
            native_check.score(filled, out / "step4_key_de.csv", report)
    with pytest.raises(SystemExit, match="xlsx or .csv"):
        native_check.score(tmp_path / "filled.numbers", out / "step4_key_de.csv", report)
