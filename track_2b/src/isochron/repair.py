"""The repair loop (our method): select, check length and meaning, revise with feedback.

The loop sees only the syllable counter and the NLI, never the final judge.

Round 0 asks the variant's prompt for 4 candidates. Each candidate gets its
length (syllables, words) and an NLI verdict against the input, in both
directions. The best candidate so far is ranked by:
1. accepted: within ±10 % of the target and kept by the NLI;
2. kept by the NLI;
3. closest to the target in syllables;
4. earlier round, then earlier position.

If the best one is not accepted, a revision prompt with specific feedback asks
for 4 new candidates: how many syllables too long or short (with the word
equivalent), missing information, added information. There are at most
MAX_REVISIONS rounds after round 0. If no round has yet given a usable
candidate, the next round repeats the round-0 prompt; such a round is logged
as a retry. Every round is logged.

Each round is generated with its own seed (the caller derives it from the
round number). Otherwise an unchanged prompt would be replayed byte for byte.

"Without the loop" is the closest round-0 candidate in syllables (the v1 rule).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from isochron.candidates import parse_candidates, select
from isochron.metrics.length import hit
from isochron.metrics.meaning import Meaning
from isochron.prompts import Prompt

MAX_REVISIONS = 2

Generate = Callable[[str, int], tuple[str, dict[str, Any]]]  # (prompt, round) -> (raw answer, call info)
Judge = Callable[[Sequence[str], Sequence[str]], list[Meaning]]  # the NLI, not the final judge
Count = Callable[[str, str], int]  # (text, unit) -> length


@dataclass
class Candidate:
    text: str
    round: int
    index: int
    syllables: int
    words: int
    forward: str
    backward: str
    kept: bool
    added: bool
    dropped: bool
    hit: bool

    @property
    def accepted(self) -> bool:
        return self.hit and self.kept


def rank(c: Candidate, target: int) -> tuple:
    return (not c.accepted, not c.kept, abs(c.syllables - target), c.round, c.index)


def feedback(c: Candidate, target: int, words_in: int, syllables_in: int) -> list[str]:
    lines = []
    if not c.hit:
        d = c.syllables - target
        w = max(1, round(abs(d) * words_in / syllables_in))
        if d > 0:
            lines.append(f"- It is {d} syllables too long ({c.syllables} instead of {target}): "
                         f"remove about {w} words.")
        else:
            lines.append(f"- It is {-d} syllables too short ({c.syllables} instead of {target}): "
                         f"add about {w} words, using only information from the original.")
    if c.dropped:
        lines.append("- Information from the original is missing; restore it.")
    if c.added:
        lines.append("- It adds information that is not in the original; remove it.")
    return lines


def evaluate(texts: list[str], rnd: int, source: str, target: int, nli: Judge, count: Count) -> list[Candidate]:
    meanings = nli([source] * len(texts), texts) if texts else []
    out = []
    for i, (t, m) in enumerate(zip(texts, meanings)):
        syl = count(t, "syllables")
        out.append(Candidate(t, rnd, i, syl, count(t, "words"), m.forward, m.backward,
                             m.kept, m.added, m.dropped, hit(syl, target)))
    return out


def run_loop(
    first_prompt: str,
    source: str,
    lang: str,
    target: int,
    generate: Generate,
    nli: Judge,
    count: Count,
    revise: Prompt,
    repair: bool = True,
    max_revisions: int = MAX_REVISIONS,
) -> dict[str, Any]:
    """One item through round 0 and, if repair is on, up to max_revisions revisions."""
    words_in, syllables_in = count(source, "words"), count(source, "syllables")
    target_words = max(1, round(target * words_in / syllables_in))
    log: dict[str, Any] = {"rounds": [], "target": target, "target_words": target_words}
    best: Candidate | None = None
    prompt, retry = first_prompt, False
    t_start = time.monotonic()
    for rnd in range(max_revisions + 1 if repair else 1):
        raw, info = generate(prompt, rnd)
        texts, error = parse_candidates(raw)
        t_nli = time.monotonic()
        cands = evaluate(texts, rnd, source, target, nli, count)
        nli_s = time.monotonic() - t_nli
        for c in cands:
            if best is None or rank(c, target) < rank(best, target):
                best = c
        entry = {"round": rnd, "retry": retry, "prompt": prompt, "raw": raw, "parse_error": error,
                 "candidates": [asdict(c) for c in cands], "llm": info, "nli_s": round(nli_s, 3),
                 "best_after": {"round": best.round, "index": best.index} if best else None}
        log["rounds"].append(entry)
        if rnd == 0:
            log["time_round0_s"] = round(info.get("latency_s", 0.0), 3)
            idx = select(texts, "closest", lambda t: count(t, "syllables"), target)
            log["closest_round0"] = asdict(cands[idx]) if idx is not None else None
        if not repair or (best is not None and best.accepted) or rnd == max_revisions:
            break
        if best is None:
            entry["feedback"] = ["(no usable answer: the round-0 prompt is sent again)"]
            prompt, retry = first_prompt, True
        else:
            lines = feedback(best, target, words_in, syllables_in)
            entry["feedback"] = lines
            prompt, retry = revise.render(lang, target, source, current=best.text,
                                          feedback="\n".join(lines), target_words=target_words), False
    log["final"] = asdict(best) if best else None
    log["final_accepted"] = bool(best and best.accepted)
    log["revisions"] = len(log["rounds"]) - 1  # rounds after round 0, retries included
    log["retries"] = sum(r["retry"] for r in log["rounds"])
    log["time_total_s"] = round(time.monotonic() - t_start, 3)
    return log
