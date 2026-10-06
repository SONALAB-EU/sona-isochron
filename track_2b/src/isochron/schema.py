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


R = TypeVar("R", InputRecord, OutputRecord)


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


def write_jsonl(path: str | Path, records: Iterable[InputRecord | OutputRecord]) -> int:
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")
            n += 1
    return n
