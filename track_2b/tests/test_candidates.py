"""Parsing the model's JSON answer and selecting a candidate."""

from __future__ import annotations

from isochron.candidates import parse_candidates, select


def test_parse_clean_and_fenced() -> None:
    raw = '{"candidates": ["a", "b", "c", "d"]}'
    assert parse_candidates(raw) == (["a", "b", "c", "d"], None)
    assert parse_candidates(f"Here you go:\n```json\n{raw}\n```") == (["a", "b", "c", "d"], None)


def test_parse_ignores_braces_around_the_object() -> None:
    obj = '{"candidates": ["a", "b {c}", "d", "e"]}'
    assert parse_candidates(f"{obj}\n(Note: kept {{all}} facts)") == (["a", "b {c}", "d", "e"], None)
    assert parse_candidates(f"{obj} }}") == (["a", "b {c}", "d", "e"], None)
    assert parse_candidates('{"note": 1} ' + obj)[0] == ["a", "b {c}", "d", "e"]
    two = obj + ' {"candidates": ["w", "x", "y", "z"]}'
    assert parse_candidates(two)[0] == ["a", "b {c}", "d", "e"]  # the first valid object wins


def test_parse_errors() -> None:
    assert parse_candidates("no json here")[1] == "no JSON object"
    assert parse_candidates('{"candidates": ["a",]}')[0] == []
    assert parse_candidates('{"versions": ["a"]}')[1] == 'no "candidates" list of strings'
    cands, error = parse_candidates('{"candidates": ["a", " ", "b"]}')
    assert cands == ["a", "b"] and error == "2 candidates instead of 4"


def test_select() -> None:
    cands = ["one two three", "one", "one two", "one two three four"]
    count = lambda c: len(c.split())  # noqa: E731
    assert select(cands, "first", count, 2) == 0
    assert select(cands, "closest", count, 2) == 2
    assert select(cands, "closest", count, 5) == 3
    assert select(["a b", "a b c", "a"], "closest", count, 2) == 0  # exact match
    assert select(["a", "a b c"], "closest", count, 2) == 0  # tie: the earlier candidate
    assert select([], "closest", count, 2) is None
