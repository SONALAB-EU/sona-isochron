"""Every data file loads with the schema that describes it."""

from __future__ import annotations

from pathlib import Path

import pytest

from isochron.schema import OverlongRecord, SentenceRecord, read_jsonl

DATA = Path(__file__).resolve().parents[1] / "data"
SCHEMAS: dict[str, type[SentenceRecord]] = {"fleurs_": SentenceRecord, "overlong_": OverlongRecord}
FILES = sorted(DATA.glob("*.jsonl"))


def schema_for(path: Path) -> type[SentenceRecord]:
    for prefix, cls in SCHEMAS.items():
        if path.name.startswith(prefix):
            return cls
    raise AssertionError(f"{path.name}: no schema registered for this file")


def test_expected_files_exist() -> None:
    names = {p.name for p in FILES}
    for lang in ("de", "fr", "it"):
        for split in ("dev", "test"):
            assert f"fleurs_{lang}_{split}.jsonl" in names
            assert f"overlong_{lang}_{split}.jsonl" in names


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_data_file_loads(path: Path) -> None:
    records = list(read_jsonl(path, schema_for(path)))
    assert records, f"{path.name} is empty"
    assert all(r.license == "CC-BY-SA-4.0" for r in records)
    assert all(isinstance(r.noisy_src, bool) and isinstance(r.noisy_tgt, bool) for r in records)
