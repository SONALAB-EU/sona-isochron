"""isochron.step4_cost: measured sums per line, and the window shared out by both rules."""

from __future__ import annotations

import pytest

from isochron.step4_cost import apportion, lines


def call(latency: float, prompt: int, completion: int) -> dict:
    return {"latency_s": latency, "usage": {"prompt_tokens": prompt, "completion_tokens": completion}}


def test_lines_and_apportioning() -> None:
    rounds = [{"llm": call(1.0, 30, 15), "nli_s": 1.0}, {"llm": call(1.0, 30, 15), "nli_s": 1.0}]
    item = {"id": "1", "lang": "de", "seed": 0, "a": {"tries": [{"llm": call(1.0, 10, 5)}]},
            "budgets": {"isometric": {"b": {"llm": call(2.0, 20, 10)}, "c": {"loop": {"rounds": rounds}}},
                        "isosyllabic": {"b": {"llm": call(2.0, 20, 10)}, "c": {"kept_plain": True, "loop": None}}}}
    records = lines([item])
    by = {(r["system"], r["budget"]): r for r in records}
    assert by["a", "both"]["calls"] == 1 and by["b", "isometric"]["llm_s"] == 2.0
    assert by["c_short", "isometric"] == {**by["c_short", "isometric"], "calls": 2, "llm_s": 2.0, "eval_s": 2.0}
    assert by["c", "isometric"]["calls"] == 3 and by["c", "isometric"]["completion_tokens"] == 35
    assert by["c_short", "isosyllabic"]["calls"] == 0 and by["c", "isosyllabic"]["calls"] == 1  # (a) kept
    apportion(records, {"de": 10.0})
    for rule in ("worker time", "completion tokens"):
        parts = sum(r[f"h100_s ({rule})"] for r in records if r["system"] in ("a", "b", "c_short"))
        assert parts == pytest.approx(10.0)  # the shares add up to the window
    # worker time: weights a 1, b 2 + 2, shortening 4 → 10 s / 9 per unit
    assert by["c", "isometric"]["h100_s (worker time)"] == pytest.approx(10 / 9 * 5)
    # completion tokens: a 5, b 10 + 10, shortening 30 → 10 s / 55 per token
    assert by["b", "isometric"]["h100_s (completion tokens)"] == pytest.approx(10 / 55 * 10)
