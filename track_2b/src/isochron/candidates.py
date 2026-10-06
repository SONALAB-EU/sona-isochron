"""Read the model's JSON answer and pick one candidate."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence

N_CANDIDATES = 4
SELECTIONS = ("closest", "first")


def parse_candidates(raw: str) -> tuple[list[str], str | None]:
    """Candidates from a JSON answer like {"candidates": [...]}, and a parse error if any.

    Tolerates code fences and text around the JSON object. A wrong number of
    candidates is reported as an error but the candidates are kept.
    """
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return [], "no JSON object"
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        return [], f"invalid JSON: {e.msg}"
    cands = obj.get("candidates") if isinstance(obj, dict) else None
    if not isinstance(cands, list) or not all(isinstance(c, str) for c in cands):
        return [], 'no "candidates" list of strings'
    cands = [c.strip() for c in cands if c.strip()]
    if len(cands) != N_CANDIDATES:
        return cands, f"{len(cands)} candidates instead of {N_CANDIDATES}"
    return cands, None


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
