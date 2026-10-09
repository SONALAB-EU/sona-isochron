"""Which language is a text in? A character n-gram classifier for en / de / fr / it.

Multinomial naive Bayes over character 1- to 4-grams (lowercased, letters only,
padded with spaces), add-alpha smoothing, trained on the FLEURS train
transcriptions of the four languages. Train only, so dev and test stay
unseen. It is used to check that model outputs are in the requested language;
short, telegraphic sentences without function words are fine.

    uv run python -m isochron.langid        (accuracy on the FLEURS dev sentences)
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from functools import lru_cache

CONFIGS = {"en": "en_us", "de": "de_de", "fr": "fr_fr", "it": "it_it"}
ORDERS = (1, 2, 3, 4)
ALPHA = 0.5


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    return " " + " ".join(re.findall(r"[^\W\d_]+", text)) + " "


def _grams(text: str, n: int) -> list[str]:
    return [text[i : i + n] for i in range(len(text) - n + 1)]


class CharNgramLID:
    def __init__(self, texts: dict[str, list[str]]) -> None:
        self.langs = sorted(texts)
        self.counts = {(lang, n): Counter() for lang in self.langs for n in ORDERS}
        for lang, sentences in texts.items():
            for s in sentences:
                clean = _clean(s)
                for n in ORDERS:
                    self.counts[lang, n].update(_grams(clean, n))
        self.totals = {key: sum(c.values()) for key, c in self.counts.items()}
        self.vocab = {n: len(set().union(*(self.counts[lang, n] for lang in self.langs))) for n in ORDERS}

    def scores(self, text: str) -> dict[str, float]:
        clean = _clean(text)
        out = {}
        for lang in self.langs:
            s = 0.0
            for n in ORDERS:
                counts, total, v = self.counts[lang, n], self.totals[lang, n], self.vocab[n]
                s += sum(math.log((counts[g] + ALPHA) / (total + ALPHA * v)) for g in _grams(clean, n))
            out[lang] = s
        return out

    def predict(self, text: str) -> str:
        if not _clean(text).strip():
            return "unknown"
        scores = self.scores(text)
        return max(scores, key=scores.get)


@lru_cache(maxsize=1)
def fleurs_lid() -> CharNgramLID:
    from isochron.data.fleurs import train_sentences

    return CharNgramLID({lang: list(train_sentences(cfg).values()) for lang, cfg in CONFIGS.items()})


def main() -> None:
    from pathlib import Path

    from isochron.schema import SentenceRecord, read_jsonl

    lid = fleurs_lid()
    checks: dict[str, list[str]] = {"en": []}
    for lang in ("de", "fr", "it"):
        records = list(read_jsonl(Path(f"data/fleurs_{lang}_dev.jsonl"), SentenceRecord))
        checks[lang] = [r.ref_text for r in records]
        if lang == "de":
            checks["en"] = [r.src_text for r in records]
    for lang, texts in checks.items():
        wrong = [(t, lid.predict(t)) for t in texts if lid.predict(t) != lang]
        print(f"{lang}: {len(texts) - len(wrong)}/{len(texts)} dev sentences identified correctly")
        for t, guess in wrong:
            print(f"   as {guess}: {t}")


if __name__ == "__main__":
    main()
