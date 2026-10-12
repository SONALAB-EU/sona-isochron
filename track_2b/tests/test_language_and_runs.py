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


def test_lengths_csv_has_one_row_per_output(tmp_path: Path) -> None:
    from isochron.lengths_csv import main as lengths_csv

    def cand(text: str, syllables: int, hit: bool) -> dict:
        return {"text": text, "hit": hit, "kept": True, "syllables": syllables}

    cfg = {"variant": "v1", "lang": "de", "split": "test", "model": "m", "quantisation": "BF16", "endpoint": "e",
           "levels": [80], "seeds": [0], "items": {"n": 1}, "git_commit": "0123456789abcdef"}
    item = {"id": "7", "level": 80, "seed": 0, "target": 20, "revisions": 1, "retries": 0,
            "time_round0_s": 1.0, "time_total_s": 2.0, "closest_round0": None,
            "final": cand("Die Polizei schätzte die Zahl auf sechstausend.", 21, True)}
    judged = {"id": "7", "level": 80, "seed": 0, "without": {"valid": True, "recall": 0.0, "added_any": None},
              "with": {"valid": True, "recall": 1.0, "added_any": False}}
    (tmp_path / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    (tmp_path / "items.jsonl").write_text(json.dumps(item) + "\n", encoding="utf-8")
    (tmp_path / "judge.jsonl").write_text(json.dumps(judged) + "\n", encoding="utf-8")
    out = tmp_path / "lengths.csv"
    lengths_csv([str(tmp_path), "--out", str(out)])
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# Step 2 output lengths") and any("quantisation BF16" in line for line in lines)
    rows = [line for line in lines if not line.startswith("#")]
    assert rows == ["lang,id,level,seed,loop,target_syllables,output_syllables,ratio,fit,wrong_language,no_output",
                    "de,7,80,0,without,20,,,0,0,1",
                    "de,7,80,0,with,20,21,1.0500,1,0,0"]


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


def test_rounds_follow_the_loops_best_candidate() -> None:
    from isochron.rounds import item_states, third_round

    def cand(rnd: int, idx: int, text: str, hit: bool, kept: bool) -> dict:
        return {"round": rnd, "index": idx, "text": text, "hit": hit, "kept": kept, "syllables": 10}

    german = ["Die Stadt hat zwei Brücken.", "Die Stadt besitzt zwei Brücken.", "Zwei Brücken hat die Stadt."]
    item = {"closest_round0": cand(0, 1, german[0], True, False),
            "final": cand(2, 0, german[2], True, True),
            "rounds": [{"candidates": [cand(0, 0, german[1], False, True), cand(0, 1, german[0], True, False)],
                        "best_after": {"round": 0, "index": 0}},
                       {"candidates": [cand(1, 0, german[1], True, False)], "best_after": {"round": 1, "index": 0}},
                       {"candidates": [cand(2, 0, german[2], True, True)], "best_after": {"round": 2, "index": 0}}]}
    judged = {"without": {"valid": True, "recall": 1.0, "added_any": False},
              "with": {"valid": True, "recall": 1.0, "added_any": False}}
    s0, s1, s2 = item_states(item, judged, "de")
    assert (s0["fit"], s0["low"], s0["high"], s0["accepted"]) == (False, False, False, False)
    assert (s1["fit"], s1["low"], s1["high"]) == (True, False, True)  # fits, but the judge never saw this text
    assert (s2["fit"], s2["low"], s2["high"], s2["accepted"]) == (True, True, True, True)
    # an item accepted in round 0 keeps that output in rounds 1 and 2
    early = {"closest_round0": item["final"], "final": item["final"],
             "rounds": [{"candidates": [item["final"]], "best_after": {"round": 2, "index": 0}}]}
    assert [s["accepted"] for s in item_states(early, judged, "de")] == [True, True, True]
    # round 2 turned 10 of the 50 open items into fit & complete; 40 are still open: round 3 adds 8 of 100
    counts = {"items": 100, "accepted1": 50, "accepted2": 60, "low1": 20, "high1": 20, "low2": 30, "high2": 30}
    assert third_round(counts) == (8.0, 8.0)
