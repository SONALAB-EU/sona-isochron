"""Phase 2: prompts, the repair loop, pilot items and the judge's parsing."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from isochron.config import ConfigError, LLMConfig
from isochron.judge import check_added, check_compare, check_facts, first_object, parse_status, verdict
from isochron.metrics.meaning import Meaning
from isochron.pilot import VARIANTS, graded_targets, pilot_ids
from isochron.prompts import PROMPTS, Prompt
from isochron.repair import Candidate, feedback, rank, run_loop

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("path", sorted(PROMPTS.glob("*.txt")), ids=lambda p: p.name)
def test_every_prompt_renders_completely(path: Path) -> None:
    prompt = Prompt.load(path.stem)
    names = set(re.findall(r"\$(\w+)", prompt.text)) - {"language", "target", "text"}
    rendered = prompt.render("de", 40, "Ein Satz.", **{n: f"<{n}>" for n in names})
    assert "$" not in rendered
    assert "German" in rendered


def test_graded_targets() -> None:
    assert graded_targets(80, 100) == [95, 90, 85, 80]
    assert graded_targets(90, 100) == [100, 100, 95, 90]


def test_pilot_ids_avoid_gonogo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    from isochron.gonogo import gonogo_ids
    from isochron.pilot import selection_text

    ids = pilot_ids()
    assert len(ids) == 30 and len(set(ids)) == 30
    assert not set(ids) & set(gonogo_ids())
    assert "30 of the 97" in selection_text()


def _cand(syllables: int, kept: bool, rnd: int = 0, index: int = 0, target: int = 40) -> Candidate:
    return Candidate("x", rnd, index, syllables, 10, "entailment", "entailment" if kept else "neutral",
                     kept, False, not kept, 10 * abs(syllables - target) <= target)


def test_rank_prefers_accepted_then_kept_then_closest() -> None:
    t = 40
    accepted_far = _cand(44, True)        # within ±10 %, kept
    kept_out = _cand(30, True)            # kept, outside
    close_dropped = _cand(40, False)      # exact length, dropped
    assert min([close_dropped, kept_out, accepted_far], key=lambda c: rank(c, t)) is accepted_far
    assert min([close_dropped, kept_out], key=lambda c: rank(c, t)) is kept_out


def test_feedback_lines() -> None:
    lines = feedback(_cand(50, False), 40, words_in=20, syllables_in=40)
    assert lines[0].startswith("- It is 10 syllables too long (50 instead of 40): remove about 5 words")
    assert lines[1] == "- Information from the original is missing; restore it."
    short = feedback(_cand(30, True), 40, words_in=20, syllables_in=40)
    assert short == ["- It is 10 syllables too short (30 instead of 40): add about 5 words, using only information from the original."]
    assert feedback(_cand(41, True), 40, 20, 40) == []


class FakeWorld:
    """Counts words as syllables; the NLI keeps a text iff it contains 'KEEP'."""

    def __init__(self, answers: list[list[str] | str]) -> None:
        self.answers, self.prompts, self.rounds = answers, [], []

    def generate(self, prompt: str, rnd: int):
        self.prompts.append(prompt)
        self.rounds.append(rnd)
        answer = self.answers[len(self.prompts) - 1]
        raw = answer if isinstance(answer, str) else json.dumps({"candidates": answer})
        return raw, {"latency_s": 0.1}

    @staticmethod
    def nli(sources, outputs):
        return [Meaning("entailment", "entailment" if "KEEP" in o else "neutral") for o in outputs]

    @staticmethod
    def count(text: str, unit: str) -> int:
        return len(text.split())


def test_loop_stops_when_round_zero_is_accepted() -> None:
    w = FakeWorld([["a b c d KEEP", "a b", "a", "a b c d e f"]])
    log = run_loop("P0", "s " * 10, "de", 5, w.generate, w.nli, w.count, Prompt.load("revise_v1"))
    assert log["revisions"] == 0 and log["final_accepted"] and log["final"]["index"] == 0
    assert log["closest_round0"]["index"] == 0


def test_loop_revises_with_feedback_and_keeps_the_best() -> None:
    w = FakeWorld([
        ["a b c", "a b c d e f g h", "a", "a b"],              # round 0: nothing kept
        ["a b c d e f g h i j KEEP", "x", "y", "z"],           # round 1: kept but too long
        ["a b c d KEEP", "a b", "a b c", "a"],                # round 2: accepted
    ])
    log = run_loop("P0", "s " * 10, "de", 5, w.generate, w.nli, w.count, Prompt.load("revise_v1"))
    assert log["revisions"] == 2 and log["final_accepted"]
    assert (log["final"]["round"], log["final"]["index"]) == (2, 0)
    assert "Information from the original is missing" in w.prompts[1]
    assert "too long" in w.prompts[2]
    assert (log["closest_round0"]["index"], log["closest_round0"]["syllables"]) == (0, 3)  # 3, 8, 1, 2 vs target 5


def test_unchanged_best_gives_the_same_prompt_but_a_new_round() -> None:
    w = FakeWorld([
        ["a b c d e f g h KEEP", "a", "a b", "a b c"],   # round 0: best is kept but too long
        ["a b c d e", "a b c d", "a b c", "a b c d e f"],  # round 1: hits, but all dropped
        ["a b c d e f g h i KEEP", "x", "y", "z"],        # round 2
    ])
    log = run_loop("P0", "s " * 10, "de", 5, w.generate, w.nli, w.count, Prompt.load("revise_v1"))
    assert w.prompts[1] == w.prompts[2]  # best did not change, so the feedback is the same ...
    assert w.rounds == [0, 1, 2]         # ... but each call knows its round, so the caller can vary the seed
    assert log["retries"] == 0 and not any(r["retry"] for r in log["rounds"])


def test_no_answer_is_retried_and_logged_as_retry() -> None:
    w = FakeWorld(["not json", ["a b c d KEEP", "a", "b", "c"]])
    log = run_loop("P0", "s " * 10, "de", 5, w.generate, w.nli, w.count, Prompt.load("revise_v1"))
    assert w.prompts == ["P0", "P0"] and w.rounds == [0, 1]
    assert log["retries"] == 1 and log["rounds"][1]["retry"] and log["final_accepted"]
    assert log["closest_round0"] is None


def test_loop_without_repair_makes_one_call() -> None:
    w = FakeWorld([["a b c", "a b", "a", "a b c d e f"]])
    log = run_loop("P0", "s " * 10, "de", 5, w.generate, w.nli, w.count, Prompt.load("revise_v1"), repair=False)
    assert len(w.prompts) == 1 and log["revisions"] == 0


def test_judge_parsing_and_verdict() -> None:
    obj, err = first_object('Sure: {"facts": ["A", "B"]} done', check_facts)
    assert obj == {"facts": ["A", "B"]} and err is None
    assert first_object('{"facts": []}', check_facts)[1] is not None
    good = '{"facts": [{"fact": "A", "status": "kept"}, {"fact": "B", "status": "changed"}], "added": ["C"]}'
    obj, err = first_object(good, check_compare(2))
    assert err is None
    assert verdict(obj) == {"recall": 0.5, "n_facts": 2, "dropped": 0, "changed": 1, "added": 1, "added_any": True}
    assert "instead of 3" in first_object(good, check_compare(3))[1]
    placeholder = {"facts": [{"fact": "A", "status": "kept"}], "added": ["...", "…", " "]}
    assert verdict(placeholder)["added_any"] is False


def test_perfact_parsers() -> None:
    assert parse_status("kept") == ({"status": "kept"}, None)
    assert parse_status("Changed.\n") == ({"status": "changed"}, None)
    assert parse_status("The answer: dropped") == ({"status": "dropped"}, None)
    assert parse_status("maybe")[0] is None
    assert first_object('{"added": []}', check_added) == ({"added": []}, None)
    assert first_object('{"added": [1]}', check_added)[1] == 'no "added" list of strings'


def test_config_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ("JUDGE_NAME", "JUDGE_BASE_URL", "JUDGE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(ConfigError, match="JUDGE_NAME"):
        LLMConfig.from_env(env_file=None, prefix="JUDGE")
    monkeypatch.setenv("JUDGE_NAME", "judge")
    monkeypatch.setenv("JUDGE_BASE_URL", "http://example.invalid/v1/")
    monkeypatch.setenv("JUDGE_API_KEY", "k")
    cfg = LLMConfig.from_env(env_file=None, prefix="JUDGE")
    assert (cfg.name, cfg.base_url) == ("judge", "http://example.invalid/v1")


def test_variants_point_to_existing_prompts() -> None:
    for name in VARIANTS.values():
        assert (PROMPTS / f"{name}.txt").exists()
