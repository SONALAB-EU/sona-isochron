"""NLI wrapper: flag logic, call order and, if the model is cached, real predictions."""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from huggingface_hub import try_to_load_from_cache

from isochron.metrics.meaning import MODEL_ID, REVISION, Meaning, judge


def test_flags() -> None:
    assert Meaning("entailment", "entailment").kept
    m = Meaning("neutral", "entailment")
    assert m.added and not m.dropped and not m.kept
    m = Meaning("entailment", "contradiction")
    assert m.dropped and not m.added and not m.kept


def test_judge_asks_both_directions_in_order() -> None:
    calls: list[tuple[list[str], list[str]]] = []

    def fake(premises: Sequence[str], hypotheses: Sequence[str]) -> list[str]:
        calls.append((list(premises), list(hypotheses)))
        return ["entailment", "neutral", "contradiction", "entailment"]

    res = judge(fake, ["s1", "s2"], ["o1", "o2"])
    assert calls == [(["s1", "s2", "o1", "o2"], ["o1", "o2", "s1", "s2"])]
    assert res == [Meaning("entailment", "contradiction"), Meaning("neutral", "entailment")]


def test_judge_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError):
        judge(lambda p, h: [], ["s1"], [])


cached = isinstance(try_to_load_from_cache(MODEL_ID, "model.safetensors", revision=REVISION), str)


@pytest.mark.skipif(not cached, reason="NLI model not in the local Hugging Face cache")
def test_real_model_and_batching() -> None:
    from isochron.metrics.meaning import NLI

    src = "Der Zug fuhr um neun Uhr in Bern ab."
    outputs = [src, "Der Zug fuhr nicht um neun Uhr in Bern ab.", "Der Zug fuhr ab.", "Le train est parti de Berne à neuf heures."]
    nli = NLI(device="cpu", batch_size=3)
    res = nli.meaning([src] * len(outputs), outputs)
    assert res[0].kept
    assert not res[1].kept
    assert res[2].dropped
    # res[3] is a correct French translation, yet the model labels French ⇒ German
    # "contradiction"; cross-lingual NLI is only the secondary check in step 4.
    nli.batch_size = 1
    assert nli.meaning([src] * len(outputs), outputs) == res
