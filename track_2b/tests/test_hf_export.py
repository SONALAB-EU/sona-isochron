"""The Hugging Face dataset (data/hf_dataset/): its card matches its files, and its files reproduce the results."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from huggingface_hub import DatasetCard

from isochron.hf_export import CONFIGS, LOOPBACK, check, scrub

ROOT = Path(__file__).resolve().parents[1]
HF = ROOT / "data/hf_dataset"
DTYPES = {"string": str, "bool": bool, "int64": int, "float64": (int, float)}


def card_meta() -> dict:
    return DatasetCard.load(HF / "README.md").data.to_dict()


def conforms(value, feature) -> bool:
    """A JSON value against a feature as the card's dataset_info declares it (null is always allowed)."""
    if value is None:
        return True
    if isinstance(feature, str):
        return isinstance(value, DTYPES[feature]) and not (feature != "bool" and isinstance(value, bool))
    if isinstance(feature, list):  # a struct, as the YAML writes it inside a list
        return conforms(value, {"struct": feature})
    if "list" in feature:
        return isinstance(value, list) and all(conforms(v, feature["list"]) for v in value)
    if "dtype" in feature:
        return conforms(value, feature["dtype"])
    if "struct" in feature:
        fields = {f["name"]: f for f in feature["struct"]}
        return isinstance(value, dict) and value.keys() <= fields.keys() and all(
            conforms(v, fields[k]) for k, v in value.items())
    raise AssertionError(f"unknown feature {feature}")


def test_scrub_removes_local_paths_and_endpoints() -> None:
    cfg = {"endpoint": "http://127.0.0.1:41631/v1", "items": {"n": 2, "ids": ["1", "2"]},
           "backend": {"type": "vLLM", "model_path": "/somewhere/models/x"},
           "sessions": [{"endpoint": "http://127.0.0.1:1/v1", "backend": {"model_path": "/x"}}]}
    assert scrub(cfg) == {"endpoint": LOOPBACK, "items": {"n": 2}, "backend": {"type": "vLLM"},
                          "sessions": [{"endpoint": LOOPBACK, "backend": {}}]}


pytestmark = pytest.mark.skipif(not HF.exists(), reason="data/hf_dataset/ is not built")


def test_card_header() -> None:
    meta = card_meta()
    assert meta["license"] == "cc-by-sa-4.0"
    assert meta["language"] == ["en", "de", "fr"]
    assert [c["config_name"] for c in meta["configs"]] == [i["config_name"] for i in meta["dataset_info"]]
    assert sorted(c["config_name"] for c in meta["configs"]) == sorted(CONFIGS)
    files = {f["path"] for c in meta["configs"] for f in c["data_files"]}
    assert files == {str(p.relative_to(HF)) for p in HF.rglob("*.jsonl")}


def test_every_row_matches_the_declared_features() -> None:
    meta = card_meta()
    for config in meta["configs"]:
        info = next(i for i in meta["dataset_info"] if i["config_name"] == config["config_name"])
        features = {f["name"]: f for f in info["features"]}
        for data_file in config["data_files"]:
            for n, line in enumerate((HF / data_file["path"]).read_text(encoding="utf-8").splitlines(), 1):
                row = json.loads(line)
                where = f"{data_file['path']}:{n}"
                assert row.keys() == features.keys(), where
                bad = [k for k, v in row.items() if not conforms(v, features[k])]
                assert not bad, f"{where}: {bad}"
                if "split" in row:
                    assert row["split"] == data_file["split"], where


def test_dev_is_exploratory_and_test_is_reported() -> None:
    for config in ("step2_inputs", "step2_responses", "step4_inputs", "step4_responses", "runs"):
        for split, role in (("dev", "exploratory"), ("test", "reported")):
            rows = [json.loads(line) for line in (HF / config / f"{split}.jsonl").read_text(encoding="utf-8").splitlines()]
            assert rows and {r["split_role"] for r in rows} == {role}


def test_no_audio_paths_or_secrets() -> None:
    files = [p for p in HF.rglob("*") if p.is_file()]
    assert {p.suffix for p in files} <= {".jsonl", ".json", ".md"}
    pattern = re.compile(r"/Users/|/home/|/sc/|model_path|127\.0\.0\.1:\d|api[_-]?key|bearer |hf_[A-Za-z0-9]{30}",
                         re.IGNORECASE)
    for p in files:
        hit = pattern.search(p.read_text(encoding="utf-8"))
        assert hit is None, f"{p.relative_to(HF)}: {hit.group(0) if hit else ''}"


def test_size_under_the_data_limit() -> None:
    assert sum(p.stat().st_size for p in (ROOT / "data").rglob("*") if p.is_file()) < 100 * 1024 * 1024


def test_export_reproduces_the_results_files(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    counts, mismatches = check(HF)
    assert not mismatches, "\n".join(mismatches)
    assert counts["step4_test.md"] and counts["step2_test.md"] and counts["step4_test_nli2.md"]
    assert sum(counts.values()) >= 1206
