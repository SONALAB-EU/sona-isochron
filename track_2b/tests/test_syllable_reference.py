"""Syllable counts must not depend on the machine: every eSpeak NG 1.52.0 build gives these counts.

The reference holds the count for every German and French reference sentence (dev and test). It was
made on macOS with Homebrew's build and matched exactly by a CMake build from source, which is how
hpc/setup.sh installs eSpeak NG on the cluster; setup.sh runs this test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from isochron.metrics.length import espeak_available, espeak_version, syllables
from isochron.schema import SentenceRecord, read_jsonl

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = json.loads((ROOT / "tests/data/syllables_espeak_1.52.0.json").read_text(encoding="utf-8"))


@pytest.mark.skipif(not espeak_available() or espeak_version() != REFERENCE["espeak"],
                    reason="needs espeak-ng 1.52.0")
def test_counts_match_the_reference() -> None:
    counts = {}
    for lang in ("de", "fr"):
        for split in ("dev", "test"):
            for r in read_jsonl(ROOT / f"data/fleurs_{lang}_{split}.jsonl", SentenceRecord):
                counts[f"{lang}/{split}/{r.id}"] = syllables(r.ref_text, lang)
    differ = {k: (counts.get(k), v) for k, v in REFERENCE["counts"].items() if counts.get(k) != v}
    assert not differ, f"{len(differ)} sentences differ (now, reference): {dict(list(differ.items())[:5])}"
    assert counts.keys() == REFERENCE["counts"].keys()
