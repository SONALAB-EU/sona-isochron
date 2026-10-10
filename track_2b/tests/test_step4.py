"""Step 4: budgets, the translation parser, and a dry run through the runner and the report."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from huggingface_hub import try_to_load_from_cache

from isochron.metrics.length import espeak_available
from isochron.metrics.meaning import MODEL_ID, REVISION
from isochron.step4 import RATES, budget, parse_translation

ROOT = Path(__file__).resolve().parents[1]


def test_rates_give_the_protocol_factors() -> None:
    assert round(RATES["de"] / RATES["en"], 3) == 0.964
    assert round(RATES["fr"] / RATES["en"], 3) == 1.160
    assert round(RATES["it"] / RATES["en"], 3) == 1.129


def test_isometric_budget_is_the_source_characters_without_spaces() -> None:
    assert budget("isometric", "The cat sat.", "de", "heuristic") == 10
    assert budget("isometric", "The cat sat.", "fr", "heuristic") == 10


def test_isosyllabic_budget_scales_and_rounds_half_up() -> None:
    # heuristic counter: "Banana banana" has 6 syllables in English
    assert budget("isosyllabic", "Banana banana", "de", "heuristic") == 6   # 6 × 0.964 = 5.79
    assert budget("isosyllabic", "Banana banana", "fr", "heuristic") == 7   # 6 × 1.160 = 6.96


def test_parse_translation() -> None:
    assert parse_translation('Sure: {"translation": " Der Zug fährt. "}') == ("Der Zug fährt.", None)
    assert parse_translation('{"translation": ""}')[0] is None
    assert parse_translation("Der Zug fährt.")[0] is None


nli_cached = isinstance(try_to_load_from_cache(MODEL_ID, "model.safetensors", revision=REVISION), str)


@pytest.mark.skipif(not nli_cached or not espeak_available(), reason="needs the cached NLI model and espeak-ng")
def test_dry_run_and_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from isochron import step4, step4_report

    monkeypatch.chdir(ROOT)
    out = tmp_path / "run"
    args = ["--langs", "de", "--split", "dev", "--exclude-gonogo", "--limit", "1", "--seeds", "0", "--mock",
            "--device", "cpu", "--out", str(out)]
    step4.main(args)
    item = json.loads((out / "items.jsonl").read_text(encoding="utf-8"))
    assert item["a"]["text"] == item["reference"]  # the dry run's stand-in for a translation
    assert set(item["budgets"]) == {"isometric", "isosyllabic"}
    assert item["budgets"]["isometric"]["unit"] == "chars" and item["budgets"]["isosyllabic"]["unit"] == "syllables"
    for entry in item["budgets"].values():
        assert entry["b"]["text"] in entry["b"]["candidates"]
        assert entry["c"]["kept_plain"] or entry["c"]["loop"]["unit"] == entry["unit"]
    with pytest.raises(SystemExit, match="--resume"):
        step4.main(args)
    report = tmp_path / "report.md"
    step4_report.main([str(out), "--out", str(report), "--device", "cpu"])
    text = report.read_text(encoding="utf-8")
    assert "EN → DE, isometric budget (chars)" in text and "(c) translate, then shorten" in text
