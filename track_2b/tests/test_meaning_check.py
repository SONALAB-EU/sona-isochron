"""isochron.meaning_check: the second NLI's pairs match step4_report's cache, and the report reads both models."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from isochron import meaning_check
from isochron.judge import SUITES
from isochron.metrics.length import espeak_available
from isochron.schema import ControlPair, read_jsonl

ROOT = Path(__file__).resolve().parents[1]


def test_kappa() -> None:
    assert meaning_check.kappa([True, True, False, False], [True, True, False, False]) == 1.0
    assert meaning_check.kappa([True, False], [False, True]) == -1.0
    assert meaning_check.kappa([True, True], [True, True]) == 1.0  # no variation: perfect agreement


@pytest.mark.skipif(not espeak_available(), reason="needs espeak-ng")
def test_pairs_scores_and_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from isochron import step4, step4_report

    monkeypatch.chdir(ROOT)
    run = tmp_path / "run"
    step4.main(["--langs", "de", "--split", "dev", "--exclude-gonogo", "--limit", "2", "--seeds", "0", "--mock",
                "--device", "cpu", "--out", str(run)])
    pairs_path = tmp_path / "pairs.jsonl"
    meaning_check.write_pairs([run], pairs_path)
    pairs = [json.loads(line) for line in pairs_path.read_text(encoding="utf-8").splitlines()]

    class Stub:
        def describe(self) -> str:
            return "stub NLI"

        def meaning(self, sources, outputs):
            return [meaning_check.Meaning("entailment", "entailment") for _ in sources]

    # the keys are step4_report's cache keys: its own scoring finds every pair cached
    cache = tmp_path / "cache1.jsonl"
    cache.write_text(json.dumps({"nli": "stub NLI"}) + "\n" + "".join(
        json.dumps({"key": meaning_check.key(p["premise"], p["hypothesis"]),
                    "m": {"kept": True, "added": False, "dropped": False}}) + "\n" for p in pairs), encoding="utf-8")
    before = cache.read_text(encoding="utf-8")
    items = [json.loads(line) for line in (run / "items.jsonl").read_text(encoding="utf-8").splitlines()]
    step4_report.score(step4_report.outputs(items, "espeak"), "espeak", Stub(), cache)
    assert cache.read_text(encoding="utf-8") == before  # nothing was missing
    scores = tmp_path / "scores"
    scores.mkdir()
    (scores / "step4_cache.jsonl").write_text(json.dumps({"nli": "second stub"}) + "\n" + "".join(
        json.dumps({"key": meaning_check.key(p["premise"], p["hypothesis"]),
                    "m": {"kept": i % 2 == 0, "added": i % 2 == 1, "dropped": False}}) + "\n"
        for i, p in enumerate(pairs)), encoding="utf-8")
    controls = [{"suite": s, "id": p.id, "lang": p.lang, "control": p.control, "model": m, "forward": "entailment",
                 "backward": "entailment"} for s in meaning_check.SUITE_NAMES
                for p in read_jsonl(SUITES[s]["file"], ControlPair) for m in ("evaluation", "second")]
    (scores / "controls.jsonl").write_text("".join(json.dumps(c) + "\n" for c in controls), encoding="utf-8")
    (scores / "score_config.json").write_text(json.dumps(
        {"git_commit": "abc", "slurm_job": "1", "gpu": "none", "torch": "x", "transformers": "y"}), encoding="utf-8")
    out = tmp_path / "report.md"
    meaning_check.report([run], scores, cache, out)
    text = out.read_text(encoding="utf-8")
    assert "Second NLI: second stub" in text and "Evaluation NLI (the loop's own model): stub NLI" in text
    assert "| identity | 60 | 100 % (60/60) | 100 % (60/60) | 100 % (60/60) | no: 87 % (52/60) |" in text  # hard_xl
    assert "paired differences (post-hoc, added after test outputs existed; percentage points)" in text
    assert "Does (c) gain more from the evaluation NLI than (a) does?" in text
