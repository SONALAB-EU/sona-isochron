"""Read the model's JSON answer and pick one candidate."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence

N_CANDIDATES = 4
SELECTIONS = ("closest", "first")


def parse_candidates(raw: str) -> tuple[list[str], str | None]:
    """Candidates from a JSON answer like {"candidates": [...]}, and a parse error if any.

    Tries a JSON decode at every "{" and takes the first object that holds a
    "candidates" list of strings, so code fences and text around the object
    (even with braces in it) are ignored. A wrong number of candidates is
    reported as an error but the candidates are kept.
    """
    decoder = json.JSONDecoder()
    error = "no JSON object"
    for match in re.finditer(r"\{", raw):
        try:
            obj, _ = decoder.raw_decode(raw, match.start())
        except json.JSONDecodeError as e:
            if error == "no JSON object":
                error = f"invalid JSON: {e.msg}"
            continue
        cands = obj.get("candidates") if isinstance(obj, dict) else None
        if not isinstance(cands, list) or not all(isinstance(c, str) for c in cands):
            error = 'no "candidates" list of strings'
            continue
        cands = [c.strip() for c in cands if c.strip()]
        if len(cands) != N_CANDIDATES:
            return cands, f"{len(cands)} candidates instead of {N_CANDIDATES}"
        return cands, None
    return [], error


def select(candidates: Sequence[str], how: str, measure: Callable[[str], int], target: int) -> int | None:
    """Index of the chosen candidate, or None if there are none.

    closest: length (in the target's unit) nearest to the target; on a tie the
             earlier candidate wins.
    first:   the first candidate, i.e. no selection.
    """
    if not candidates:
        return None
    if how == "first":
        return 0
    if how == "closest":
        return min(range(len(candidates)), key=lambda i: (abs(measure(candidates[i]) - target), i))
    raise ValueError(f"unknown selection {how!r}")
