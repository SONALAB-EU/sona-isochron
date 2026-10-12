"""The native-speaker sheet: blind, balanced lines with a separate key, and the agreement scorer."""

from __future__ import annotations

import csv
import json
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
    with open(out / "sheet_de.csv", encoding="utf-8-sig") as f:
        sheet = list(csv.DictReader(f))
    with open(out / "key_de.csv", encoding="utf-8") as f:
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
    native_check.score(filled, out / "key_de.csv", report)
    text = report.read_text(encoding="utf-8")
    assert "| NLI | added | 50 | 100 % | 1.00 |" in text and "| NLI | dropped | 50 | 100 % | 1.00 |" in text


def test_kappa() -> None:
    assert native_check.kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert native_check.kappa([True, True], [True, True]) is None
    assert round(native_check.kappa([True, True, False, False], [True, False, True, False]), 2) == 0.0
