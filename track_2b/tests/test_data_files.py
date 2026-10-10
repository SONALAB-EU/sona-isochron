"""Every data file loads with the schema that describes it."""

from __future__ import annotations

from pathlib import Path

import pytest

from isochron.schema import ControlPair, OverlongRecord, SentenceRecord, read_jsonl

DATA = Path(__file__).resolve().parents[1] / "data"
SCHEMAS: dict[str, type] = {"fleurs_": SentenceRecord, "overlong_": OverlongRecord, "nli_controls": ControlPair,
                            "judge_controls": ControlPair}
FILES = sorted(DATA.glob("*.jsonl"))


def schema_for(path: Path) -> type:
    for prefix, cls in SCHEMAS.items():
        if path.name.startswith(prefix):
            return cls
    raise AssertionError(f"{path.name}: no schema registered for this file")


def test_expected_files_exist() -> None:
    names = {p.name for p in FILES}
    assert "nli_controls.jsonl" in names
    assert "judge_controls_de.jsonl" in names
    for lang in ("de", "fr", "it"):
        for split in ("dev", "test"):
            assert f"fleurs_{lang}_{split}.jsonl" in names
            assert f"overlong_{lang}_{split}.jsonl" in names


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_data_file_loads(path: Path) -> None:
    cls = schema_for(path)
    records = list(read_jsonl(path, cls))
    assert records, f"{path.name} is empty"
    assert all(r.license == "CC-BY-SA-4.0" for r in records)
    if issubclass(cls, SentenceRecord):
        assert all(isinstance(r.noisy_src, bool) and isinstance(r.noisy_tgt, bool) for r in records)


def test_nli_controls_cover_every_type_per_sentence() -> None:
    pairs = list(read_jsonl(DATA / "nli_controls.jsonl", ControlPair))
    by_sentence: dict[tuple[str, str], set[str]] = {}
    for p in pairs:
        by_sentence.setdefault((p.lang, p.fleurs_id), set()).add(p.control)
    controls = {"identity", "paraphrase", "clause_deleted", "clause_inserted", "negation"}
    assert all(c == controls for c in by_sentence.values())
    assert sorted({lang for lang, _ in by_sentence}) == ["de", "fr"]
    assert all(sum(lang == x for x, _ in by_sentence) == 20 for lang in ("de", "fr"))


def test_judge_controls_are_minimal_edits() -> None:
    pairs = list(read_jsonl(DATA / "judge_controls_de.jsonl", ControlPair))
    counts: dict[str, int] = {}
    for p in pairs:
        counts[p.control] = counts.get(p.control, 0) + 1
    assert counts == {"identity": 60, "same_meaning": 20, "modal_changed": 13, "number_changed": 13,
                      "qualifier_changed": 14, "fact_inserted": 20}
    by_sentence: dict[str, set[str]] = {}
    for p in pairs:
        by_sentence.setdefault(p.fleurs_id, set()).add(p.control)
        if p.control == "identity":
            assert p.output == p.source and p.note is None
        else:
            old, new = p.note.split(" → ")
            assert p.source.count(old) == 1 and p.source.replace(old, new) == p.output != p.source
    edits = {"modal_changed", "number_changed", "qualifier_changed", "fact_inserted"}
    assert all("identity" in c and len(c & edits) == 1 for c in by_sentence.values())
    assert all("fact_inserted" not in c for c in by_sentence.values() if "same_meaning" in c)
    nli_de = {p.fleurs_id for p in read_jsonl(DATA / "nli_controls.jsonl", ControlPair) if p.lang == "de"}
    assert not nli_de & set(by_sentence)
