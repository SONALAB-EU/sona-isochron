"""The go/no-go for Wednesday 7 October 2026, as fixed in docs/eval_protocol.md.

Step 2 in German, target 80 % of the input's syllables, on 50 dev sentences
drawn with seed 0 from data/fleurs_de_dev.jsonl, pooled over seeds 0, 1, 2.
GO if at least 60 % of the outputs hit the syllable target and at least 80 %
of those keep meaning (entailment both ways). The scored output is the
candidate closest to the target; the first candidate is reported alongside.
"""

from __future__ import annotations

import random
from pathlib import Path

from isochron.schema import SentenceRecord, read_jsonl

DATA = Path("data/fleurs_de_dev.jsonl")
N = 50
SAMPLE_SEED = 0
LANG, SPLIT, UNIT, LEVEL = "de", "dev", "syllables", 80
SEEDS = (0, 1, 2)
SELECTION = "closest"
PROMPT_SHA256 = "fe4fbfdd800d69b613fd49ba747507aa44a9a868556ceca15421d33edd661a5c"  # shorten_syllables_v1, frozen 2026-10-09
MIN_HIT = 0.60
MIN_KEPT_AMONG_HITS = 0.80


def gonogo_ids(path: Path = DATA) -> list[str]:
    records = list(read_jsonl(path, SentenceRecord))
    return [r.id for r in random.Random(SAMPLE_SEED).sample(records, N)]


def decide(hits: list[bool], kept: list[bool]) -> tuple[bool, float, float]:
    """(go, hit share, kept share among hits) over the pooled outputs."""
    n_hit = sum(hits)
    hit_share = n_hit / len(hits) if hits else 0.0
    kept_share = sum(k for h, k in zip(hits, kept) if h) / n_hit if n_hit else 0.0
    return hit_share >= MIN_HIT and kept_share >= MIN_KEPT_AMONG_HITS, hit_share, kept_share
