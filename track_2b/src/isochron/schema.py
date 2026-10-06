"""Input and output JSONL records.

One JSON object per line. Durations are in seconds.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Iterable, Iterator, TypeVar


@dataclass
class InputRecord:
    id: str
    src_lang: str
    tgt_lang: str
    src_text: str
    slot_s: float
    """Duration of the source speech slot the target line must fit."""
    mt_text: str | None = None
    """Initial (unadapted) translation, if one is supplied."""
    split: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutputRecord:
    id: str
    tgt_text: str
    method: str
    slot_s: float
    tts_s: float | None = None
    """Measured duration of the synthesised target line; None if not measured."""
    attempts: int = 1
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class SentenceRecord:
    """One line of data/fleurs_{lang}_{split}.jsonl (see data/README.md)."""

    id: str
    """FLEURS sentence id."""
    src_lang: str
    tgt_lang: str
    src_text: str
    ref_text: str
    """Human reference translation (FLEURS transcription of the target recording)."""
    slot_s: float
    """Trimmed duration of the EN recording. Not valid until trimming is fixed."""
    ref_tgt_s: float
    """Trimmed duration of the target recording. Not valid until trimming is fixed."""
    noisy_src: bool
    """EN recording's noise floor is above -30 dB, so trimming left noise in place."""
    noisy_tgt: bool
    """Same for the target recording."""
    src_recording_id: str
    tgt_recording_id: str
    license: str
    source: str


@dataclass
class OverlongRecord(SentenceRecord):
    """One line of data/overlong_{lang}_{split}.jsonl: ref_tgt_s > 1.10 × slot_s."""

    overrun: float
    """ref_tgt_s / slot_s."""


@dataclass
class ControlPair:
    """One line of data/nli_controls.jsonl: a hand-made check for the NLI metric."""

    id: str
    lang: str
    fleurs_id: str
    """FLEURS train sentence id of the source."""
    control: str
    """identity, paraphrase, clause_deleted, clause_inserted or negation."""
    source: str
    output: str
    """The source itself (identity) or a variant written by hand."""
    license: str


R = TypeVar("R", InputRecord, OutputRecord, SentenceRecord, OverlongRecord, ControlPair)


def from_dict(cls: type[R], d: dict[str, Any]) -> R:
    known = {f.name for f in fields(cls)}
    unknown = set(d) - known
    if unknown:
        raise ValueError(f"{cls.__name__}: unknown fields {sorted(unknown)}")
    return cls(**d)


def read_jsonl(path: str | Path, cls: type[R]) -> Iterator[R]:
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                yield from_dict(cls, json.loads(line))
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                raise ValueError(f"{path}:{lineno}: {e}") from e


def write_jsonl(
    path: str | Path,
    records: Iterable[InputRecord | OutputRecord | SentenceRecord | OverlongRecord | ControlPair],
) -> int:
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
            n += 1
    return n
