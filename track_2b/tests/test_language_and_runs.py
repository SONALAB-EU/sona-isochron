"""The language check, the resumable loop runner, the report's wrong-language rule and the control halves."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from huggingface_hub import try_to_load_from_cache

from isochron.judge import control_half
from isochron.language import check
from isochron.loop_run import done_items
from isochron.metrics.meaning import MODEL_ID, REVISION
from isochron.schema import ControlPair, SentenceRecord, read_jsonl

ROOT = Path(__file__).resolve().parents[1]


def test_language_check() -> None:
    assert not check("Die Vereinten Nationen hoffen, einen Fonds einzurichten.", "de").wrong
    english = check("Broad avenues and glass buildings are typical of the modern city.", "de")
    assert english.wrong and english.label == "en"
    assert check("Le train est parti de Berne à neuf heures.", "de").wrong
    assert not check("Le train est parti de Berne à neuf heures.", "fr").wrong
    # a German fragment led by a foreign name gets an Italian label, but below the threshold
    fragment = check("Giancarlo Fisichella verlor", "de")
    assert fragment.label == "it" and not fragment.wrong


def test_done_items_drops_a_cut_off_line(tmp_path: Path) -> None:
    path = tmp_path / "items.jsonl"
    path.write_text('{"id": "1", "level": 90, "seed": 0}\n{"id": "2", "level": 90, "se', encoding="utf-8")
    assert done_items(path) == {("1", 90, 0)}
    assert path.read_text(encoding="utf-8") == '{"id": "1", "level": 90, "seed": 0}\n'


nli_cached = isinstance(try_to_load_from_cache(MODEL_ID, "model.safetensors", revision=REVISION), str)


@pytest.mark.skipif(not nli_cached, reason="NLI model not in the local Hugging Face cache")
def test_loop_run_resumes_only_the_same_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from isochron.loop_run import run

    monkeypatch.chdir(ROOT)
    data = Path("data/fleurs_de_dev.jsonl")
    records = list(read_jsonl(data, SentenceRecord))[:1]
    out = tmp_path / "run"
    kwargs = dict(variant="v1", lang="de", split="dev", seeds=[0], out=out, kind="test", selection="first 1",
                  data=data, quantisation=None, mock=True, device="cpu")
    run(records, levels=[90], **kwargs)
    first = (out / "items.jsonl").read_text(encoding="utf-8")
    assert len(first.splitlines()) == 1
    with pytest.raises(SystemExit, match="--resume"):
        run(records, levels=[90], **kwargs)
    run(records, levels=[90], resume=True, **kwargs)
    assert (out / "items.jsonl").read_text(encoding="utf-8") == first
    assert len(json.loads((out / "config.json").read_text(encoding="utf-8"))["sessions"]) == 2
    with pytest.raises(SystemExit, match="levels"):
        run(records, levels=[80], resume=True, **kwargs)


def test_report_counts_wrong_language_as_failure(tmp_path: Path) -> None:
    from isochron.pilot_report import rows_for

    def cand(text: str) -> dict:
        return {"text": text, "hit": True, "kept": True, "syllables": 10}

    (tmp_path / "config.json").write_text(json.dumps({"variant": "v1", "lang": "de"}), encoding="utf-8")
    item = {"id": "1", "level": 90, "seed": 0, "target": 10, "revisions": 1, "retries": 0,
            "time_round0_s": 1.0, "time_total_s": 2.0,
            "closest_round0": cand("Die Polizei schätzte die Zahl der Demonstranten auf sechstausend."),
            "final": cand("The police estimated the number of protesters at six thousand.")}
    judged = {"id": "1", "level": 90, "seed": 0, "without": {"valid": True, "recall": 1.0, "added_any": False},
              "with": {"valid": True, "recall": 0.7, "added_any": False}}
    (tmp_path / "items.jsonl").write_text(json.dumps(item) + "\n", encoding="utf-8")
    (tmp_path / "judge.jsonl").write_text(json.dumps(judged) + "\n", encoding="utf-8")
    _, rows = rows_for(tmp_path)
    without, with_ = rows
    assert without["fit"] and not without["wrong_language"] and without["recall"] == 1.0
    assert with_["wrong_language"] and not with_["fit"] and not with_["nli_kept"]
    assert with_["recall"] == 0.0 and with_["added"] is None and with_["ratio"] is None


def test_paired_difference_of_the_loop() -> None:
    from isochron.step2_report import paired_diff

    def rows(with_fit: list[int], without_fit: list[int]) -> list[dict]:
        return [{"id": str(i), "cond": cond, "fit": fit}
                for i, pair in enumerate(zip(with_fit, without_fit)) for cond, fit in zip(("with", "without"), pair)]

    def fit(r: dict) -> int:
        return r["fit"]

    def every(r: dict) -> bool:
        return True

    assert paired_diff(rows([1, 0, 1, 0], [1, 0, 1, 0]), fit, every) == "+0.0 [+0.0, +0.0]"
    assert paired_diff(rows([1, 1, 1, 1], [0, 0, 0, 0]), fit, every) == "+100.0 [+100.0, +100.0]"
    # one sentence of four gains: +25 points, and a resample that misses that sentence gives 0
    assert paired_diff(rows([1, 0, 0, 0], [0, 0, 0, 0]), fit, every).startswith("+25.0 [+0.0, ")
    # a sentence whose rows do not count in one condition is left out of the difference
    assert paired_diff(rows([1, 0], [0, 0]), fit, lambda r: not (r["id"] == "0" and r["cond"] == "without")) == \
        "+0.0 [+0.0, +0.0]"
    assert paired_diff([], fit, every) == "–"


def test_first_table_stops_at_the_end_of_the_first_table() -> None:
    from isochron.step2_report import first_table

    lines = ["# Title", "", "| a | b |", "|---|---|", "| 1 | 2 |", "", "| Id | x |", "|----|---|"]
    assert first_table(lines) == ["| a | b |", "|---|---|", "| 1 | 2 |"]
    assert first_table(["no table"]) == []


def test_control_halves() -> None:
    nli = list(read_jsonl(ROOT / "data/nli_controls.jsonl", ControlPair))
    assert len(control_half(nli, "A")) == len(control_half(nli, "B")) == 100
    hard = list(read_jsonl(ROOT / "data/judge_controls_de.jsonl", ControlPair))
    a, b = control_half(hard, "A", "hard"), control_half(hard, "B", "hard")
    assert not {p.id for p in a} & {p.id for p in b} and len(a) + len(b) == len(hard)
    for half in (a, b):  # every sentence keeps its identity pair in the same half
        assert {p.fleurs_id for p in half if p.control == "identity"} == {p.fleurs_id for p in half}
