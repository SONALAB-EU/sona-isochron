"""Where FLEURS comes from, and its raw train sentences.

Train sentences are for building examples and checks only; tuning uses dev and
reported numbers use test.
"""

from __future__ import annotations

from pathlib import Path

from huggingface_hub import hf_hub_download

REPO_ID = "google/fleurs"
REVISION = "70bb2e84b976b7e960aa89f1c648e09c59f894dd"


def fetch(filename: str) -> Path:
    """A file of the pinned FLEURS revision, from the Hugging Face cache."""
    return Path(hf_hub_download(REPO_ID, filename, repo_type="dataset", revision=REVISION))


def train_sentences(config: str) -> dict[int, str]:
    """FLEURS sentence id -> raw transcription, from the raw release's train.tsv."""
    sentences: dict[int, str] = {}
    with open(fetch(f"data/{config}/train.tsv"), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cols = line.rstrip("\n").split("\t")
                sentences.setdefault(int(cols[0]), cols[2])
    return sentences
