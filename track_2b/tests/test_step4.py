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
def test_paired_differences_compare_systems_on_the_same_sentences() -> None:
    from isochron.step4_report import diff_table

    def row(i: str, system: str, fit: bool, complete: bool, kept: bool) -> dict:
        return {"id": i, "system": system, "fit": fit, "complete": complete, "ref": {"kept": kept}}

    rows = [row("1", "a", False, False, True), row("1", "b", True, False, False), row("1", "c", True, True, True),
            row("2", "a", False, False, True), row("2", "b", False, False, True), row("2", "c", True, True, True)]
    table = diff_table(rows, "EN → DE, isometric budget (chars)", judged=True)
    assert table[2] == "| Difference | Fit ±10 % | Fit & complete | Kept vs reference |"
    c_b, c_a = ([cell.strip() for cell in line.strip("|").split("|")] for line in table[4:6])
    assert c_b[0] == "(c) − (b)" and c_b[1].startswith("+50.0 [") and c_b[2].startswith("+100.0 [")
    assert c_b[3].startswith("+50.0 [")
    assert c_a == ["(c) − (a)", "+100.0 [+100.0, +100.0]", "+100.0 [+100.0, +100.0]", "+0.0 [+0.0, +0.0]"]
    assert "Fit & complete" not in diff_table(rows, "without a judge", judged=False)[2]


def test_tolerant_rereads_only_answers_strict_json_rejected() -> None:
    from isochron.step4_report import tolerant

    raw = r'{"candidates": ["l\'eau est chaude", "c\'est", "oui!", "non!"]}'
    entry = {"unit": "chars", "target": 5, "b": {"text": None, "raw": raw}}
    assert tolerant(entry, "fr", "espeak") == "c'est"  # closest to 5 characters, as (b) chooses
    assert tolerant({**entry, "b": {"text": "déjà lu", "raw": raw}}, "fr", "espeak") == "déjà lu"
    broken = '{"candidates": ["il dit "oui"", "non", "si", "peut-être"]}'  # unescaped quotes: not this rule
    assert tolerant({**entry, "b": {"text": None, "raw": broken}}, "fr", "espeak") is None


def test_parse_table_counts_failures_and_recoveries() -> None:
    from isochron.step4_report import outputs, parse_table

    def cand(text: str) -> dict:
        return {"text": text}

    loop = {"rounds": [{"retry": False, "candidates": [], "raw": "kein JSON"},
                       {"retry": True, "candidates": [cand("court")], "raw": "{}"}],
            "final": cand("court"), "revisions": 1}
    item = {"id": "1", "lang": "fr", "seed": 0, "source": "s", "reference": "r",
            "a": {"text": "un texte assez long", "tries": [{"raw": "x"}, {"raw": "y"}]},
            "budgets": {"isometric": {"unit": "chars", "target": 5,
                                      "b": {"text": None, "raw": r'{"candidates": ["c\'est", "a", "b", "c"]}'},
                                      "c": {"text": "court", "kept_plain": False, "loop": loop}}}}
    table = parse_table([item], outputs([item], "espeak"))
    assert table[4] == "| FR, isometric | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 1 | 0 |"
    text = "\n".join(table)
    assert "FR: 1 of 1 items needed another try, and 0 ended without a translation" in text
    assert "the first prompt again (a retry) 1; the revision of the best candidate again 0" in text
    assert "would have given candidates in 0 of these 1 rounds" in text  # its raw answer is not JSON at all


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


@pytest.mark.skipif(not nli_cached or not espeak_available(), reason="needs the cached NLI model and espeak-ng")
def test_judge_and_report_score_against_the_english_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from isochron import judge, step4, step4_report

    monkeypatch.chdir(ROOT)
    out = tmp_path / "run"
    step4.main(["--langs", "de", "fr", "--split", "dev", "--exclude-gonogo", "--limit", "1", "--seeds", "0", "--mock",
                "--device", "cpu", "--out", str(out)])

    class StubJudge:
        seen_langs: set[str] = set()

        def __init__(self, *args, **kwargs) -> None:
            pass

        def facts(self, source: str, lang: str) -> list[str]:
            StubJudge.seen_langs.add(lang)
            return ["one fact", "another fact"]

        def compare(self, facts: list[str], output: str, lang: str, original: str) -> dict:
            StubJudge.seen_langs.add(lang)
            return {"valid": True, "recall": 1.0, "n_facts": 2, "dropped": 0, "changed": 0, "added": 0, "added_any": False}

        def describe(self) -> dict:
            return {"model": "stub", "endpoint": "none", "backend": {"build_info": "stub"}, "quantisation": "n/a",
                    "seed": 0, "mode": "perfact_v3", "prompts": {}}

    monkeypatch.setattr(judge, "Judge", StubJudge)
    judge.judge_step4([out])
    rows = [json.loads(line) for line in (out / "judge.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {r["lang"] for r in rows} == {"de", "fr"} and StubJudge.seen_langs == {"en"}
    assert all(set(r["budgets"]) == {"isometric", "isosyllabic"} and set(r["budgets"]["isometric"]) == {"b", "c"}
               for r in rows)
    report = tmp_path / "report.md"
    step4_report.main([str(out), "--out", str(report), "--device", "cpu", "--nli-cache", str(tmp_path / "nli.jsonl")])
    text = report.read_text(encoding="utf-8")
    assert "EN → FR, isosyllabic budget (syllables): final judge" in text and "Judge (evaluation only): stub" in text
    assert "EN → DE, isometric budget (chars): paired differences (post-hoc, added after test outputs existed; percentage points)" in text
    # a second pass reuses every NLI score from the cache
    cached = (tmp_path / "nli.jsonl").read_text(encoding="utf-8")
    step4_report.main([str(out), "--out", str(report), "--device", "cpu", "--nli-cache", str(tmp_path / "nli.jsonl")])
    assert (tmp_path / "nli.jsonl").read_text(encoding="utf-8") == cached
