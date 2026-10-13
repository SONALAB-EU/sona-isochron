"""The dataset card's field types are regenerated from the files, and an unfilled card is refused."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from isochron.hf_card import kind, main, merge, placeholders, with_features, yaml_field

ROOT = Path(__file__).resolve().parents[1]
HF = ROOT / "data/hf_dataset"


def test_types_merge_across_rows() -> None:
    assert merge(None, "bool") == "bool"
    assert merge("int64", "float64") == "float64"
    assert merge(kind([]), kind(["a"])) == ("list", "string")
    with pytest.raises(ValueError):
        merge("string", "bool")


def test_yaml_forms() -> None:
    assert yaml_field("x", kind(1.5), "c") == {"name": "x", "dtype": "float64"}
    assert yaml_field("seeds", kind([0, 1]), "c") == {"name": "seeds", "list": "int64"}
    facts = merge(kind(None), kind([{"fact": "f", "status": "kept"}]))
    assert yaml_field("judge_facts", facts, "c") == {"name": "judge_facts", "list": [
        {"name": "fact", "dtype": "string"}, {"name": "status", "dtype": "string"}]}
    with pytest.raises(ValueError, match="null in every row"):
        yaml_field("judge_recall", None, "c")


def test_features_written_into_a_card(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "a/dev.jsonl").write_text(json.dumps({"x": None, "y": 1}) + "\n", encoding="utf-8")
    (tmp_path / "a/test.jsonl").write_text(json.dumps({"x": True, "y": 2.5}) + "\n", encoding="utf-8")
    card = ("---\nlicense: cc-by-sa-4.0\nconfigs:\n- config_name: a\n  data_files:\n  - split: dev\n    path: a/dev.jsonl\n"
            "  - split: test\n    path: a/test.jsonl\n---\n# Card\n")
    out = with_features(card, tmp_path)
    assert "dataset_info:\n- config_name: a\n  features:\n  - name: x\n    dtype: bool\n  - name: y\n    dtype: float64\n" in out
    assert out.index("dataset_info:") < out.index("configs:") and out.endswith("---\n# Card\n")


@pytest.mark.skipif(not HF.exists(), reason="data/hf_dataset/ is not built")
def test_committed_card_declares_exactly_the_files_types() -> None:
    text = (HF / "README.md").read_text(encoding="utf-8")
    assert with_features(text, HF) == text, "run: uv run python -m isochron.hf_card features"


def test_placeholders_are_found() -> None:
    text = "- **Git repository:** TODO: the URL\nfine line\n[More Information Needed]\nTODOS is a word\n"
    assert placeholders(text) == ["1: - **Git repository:** TODO: the URL", "3: [More Information Needed]"]


def test_ready_refuses_an_unfilled_card(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("---\nlicense: cc-by-sa-4.0\n---\n- **Contact:** TODO\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="not ready to upload"):
        main(["ready", "--dir", str(tmp_path)])
    (tmp_path / "README.md").write_text("---\nlicense: cc-by-sa-4.0\n---\n- **Contact:** filled\n", encoding="utf-8")
    main(["ready", "--dir", str(tmp_path)])
