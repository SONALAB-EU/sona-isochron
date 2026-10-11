"""make run: the app (isochron.app), its sample input, and the Docker files' agreement with uv.lock."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest
from huggingface_hub import try_to_load_from_cache

from isochron.app import groups, read_lines
from isochron.data.build_sample_input import sample_lines
from isochron.gonogo import gonogo_ids
from isochron.metrics.length import espeak_available
from isochron.metrics.meaning import MODEL_ID, REVISION

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data/sample_input.jsonl"


def test_sample_input_is_the_builders_output_and_avoids_the_gonogo_sentences(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    lines = [json.loads(line) for line in SAMPLE.read_text(encoding="utf-8").splitlines()]
    assert lines == sample_lines()
    assert len(lines) == 10 and {line["lang"] for line in lines} == {"de"}
    assert not {line["id"] for line in lines} & set(gonogo_ids())
    assert [line["level"] for line in lines] == [90, 80, 70, 60, 90, 80, 70, 60, 90, 80]


def test_read_lines_checks_every_field(tmp_path: Path) -> None:
    path = tmp_path / "in.jsonl"

    def problem(*objs) -> str:
        path.write_text("".join(json.dumps(o) + "\n" for o in objs), encoding="utf-8")
        with pytest.raises(ValueError) as e:
            read_lines(path)
        return str(e.value)

    good = {"id": "1", "lang": "de", "text": "Ein Satz.", "level": 80}
    assert "missing level" in problem({k: v for k, v in good.items() if k != "level"})
    assert "appears twice" in problem(good, good)
    assert "lang must be" in problem({**good, "lang": "en"})
    assert "non-empty" in problem({**good, "text": " "})
    assert "level must be" in problem({**good, "level": 0})
    assert "level must be" in problem({**good, "level": 80.0})
    assert "level must be" in problem({**good, "level": True})
    path.write_text(json.dumps({**good, "extra": "ignored"}) + "\n\n" + json.dumps({**good, "id": 2}) + "\n",
                    encoding="utf-8")
    lines = read_lines(path)
    assert [line.id for line in lines] == ["1", "2"] and lines[0].ref_text == "Ein Satz."


def test_groups_keep_first_appearance_order(tmp_path: Path) -> None:
    lines = read_lines(SAMPLE)
    assert [(lang, level, [m.id for m in members]) for lang, level, members in groups(lines)][:2] == \
        [("de", 90, ["1510", "1515", "1524"]), ("de", 80, ["1512", "1516", "1525"])]


nli_cached = isinstance(try_to_load_from_cache(MODEL_ID, "model.safetensors", revision=REVISION), str)


@pytest.mark.skipif(not nli_cached or not espeak_available(), reason="needs the cached NLI model and espeak-ng")
def test_dry_run_writes_results_and_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from isochron import app

    monkeypatch.chdir(ROOT)
    path = tmp_path / "in.jsonl"
    path.write_text("".join(SAMPLE.read_text(encoding="utf-8").splitlines(keepends=True)[:3]), encoding="utf-8")
    out = tmp_path / "output"
    app.main(["--input", str(path), "--out", str(out), "--mock"])
    results = [json.loads(line) for line in (out / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["id"] for r in results] == ["1510", "1512", "1513"]
    for r in results:
        assert set(r) >= {"input", "input_syllables", "target_syllables", "output", "output_syllables", "fit",
                          "nli_kept", "language", "accepted", "revisions", "round0", "time_s"}
        assert r["target_syllables"] == (r["level"] * r["input_syllables"] + 50) // 100
    text = (out / "summary.md").read_text(encoding="utf-8")
    assert "dry run: no LLM" in text and "n = 3 lines" in text and "TTS: none" in text
    assert len(list((out / "raw").glob("*/de_L*/items.jsonl"))) == 3


def test_docker_image_takes_every_locked_package_but_the_cuda_build_of_torch() -> None:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    torch = next(p for p in lock["package"] if p["name"] == "torch")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    pinned = re.search(r"torch==([0-9.]+)\+cpu", dockerfile)
    assert pinned and pinned.group(1) == torch["version"], "the CPU build of torch must be the locked version"
    assert len(re.findall(r"--hash=sha256:[0-9a-f]{64}", dockerfile)) == 2, "one hash per CPU wheel (amd64, arm64)"
    assert "--require-hashes" in dockerfile and "uv export --frozen" in dockerfile
