"""Does an output keep the meaning of its source? Bidirectional NLI.

Model: MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 (MIT licence),
pinned to REVISION, run locally in float32 on CPU or Apple's mps, in batches.
The predicted label is the argmax over entailment / neutral / contradiction.

For a source s and an output o:
- added content:   s ⇒ o fails (premise s, hypothesis o is not "entailment"),
                   so o says something s does not;
- dropped content: o ⇒ s fails, so s says something o does not;
- kept:            both directions are "entailment".
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

MODEL_ID = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
REVISION = "b5113eb38ab63efdd7f280f8c144ea8b13f978ce"
ENTAILMENT = "entailment"

Predict = Callable[[Sequence[str], Sequence[str]], list[str]]


@dataclass(frozen=True)
class Meaning:
    forward: str
    """Label for premise = source, hypothesis = output."""
    backward: str
    """Label for premise = output, hypothesis = source."""

    @property
    def added(self) -> bool:
        return self.forward != ENTAILMENT

    @property
    def dropped(self) -> bool:
        return self.backward != ENTAILMENT

    @property
    def kept(self) -> bool:
        return not (self.added or self.dropped)


def judge(predict: Predict, sources: Sequence[str], outputs: Sequence[str]) -> list[Meaning]:
    """Both directions for every (source, output) pair, in one predict call."""
    if len(sources) != len(outputs):
        raise ValueError(f"{len(sources)} sources but {len(outputs)} outputs")
    labels = predict([*sources, *outputs], [*outputs, *sources])
    n = len(sources)
    return [Meaning(f, b) for f, b in zip(labels[:n], labels[n:])]


class NLI:
    def __init__(self, device: str | None = None, batch_size: int = 32) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._torch = torch
        self.device = device or ("mps" if torch.backends.mps.is_available() else "cpu")
        self.batch_size = batch_size
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=REVISION)
        # The checkpoint is stored in float16, and transformers 5 loads the stored
        # dtype by default; ask for float32 explicitly.
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, revision=REVISION, dtype=torch.float32)
        self.model = model.to(self.device).eval()
        config = self.model.config
        self.labels = [config.id2label[i].lower() for i in range(config.num_labels)]
        if ENTAILMENT not in self.labels:
            raise ValueError(f"{MODEL_ID} has no entailment label: {self.labels}")

    def predict(self, premises: Sequence[str], hypotheses: Sequence[str]) -> list[str]:
        out: list[str] = []
        for i in range(0, len(premises), self.batch_size):
            batch = self.tokenizer(
                list(premises[i : i + self.batch_size]),
                list(hypotheses[i : i + self.batch_size]),
                truncation=True,
                max_length=512,
                padding=True,
                return_tensors="pt",
            ).to(self.device)
            with self._torch.inference_mode():
                logits = self.model(**batch).logits
            out += [self.labels[k] for k in logits.argmax(dim=-1).tolist()]
        return out

    def meaning(self, sources: Sequence[str], outputs: Sequence[str]) -> list[Meaning]:
        return judge(self.predict, sources, outputs)

    def describe(self) -> str:
        dtype = str(next(self.model.parameters()).dtype).removeprefix("torch.")
        return f"{MODEL_ID} @ {REVISION[:7]}, {self.device}, {dtype}, argmax label"
