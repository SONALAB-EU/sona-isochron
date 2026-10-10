"""Is an output in the requested language? The repair loop's language check.

Identifier: py3langid 0.4.0 (BSD-3-Clause; a fork of langid.py by Marco Lui,
with its own model of 139 languages). It runs locally and is deterministic.

The rule, chosen on FLEURS train and dev sentences and the dev-split outputs
of the pilot and the go/no-go (see results/language_check.md):
- the identifier is restricted to the pipeline's four languages (de, en, fr,
  it), so a German sentence full of foreign names is not called Scottish
  Gaelic or Luxembourgish;
- an output is in the wrong language when its top label is another of these
  languages with a normalised probability of at least MIN_CONFIDENCE. Short
  German fragments led by a foreign name ("Giancarlo Fisichella verlor") get
  an Italian label with lower probabilities, so they are not flagged.

The check is ours, not Apertus's: the loop treats a wrong-language candidate
as a failure and asks for the requested language.

    uv run python -m isochron.language        (validation, writes results/language_check.md)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from importlib.metadata import version
from pathlib import Path

LANGS = ("de", "en", "fr", "it")
MIN_CONFIDENCE = 0.9
OUT = Path("results/language_check.md")


@dataclass(frozen=True)
class LanguageCheck:
    label: str
    """Most likely language among LANGS."""
    p: float
    """Its probability, normalised over LANGS."""
    wrong: bool
    """label is not the requested language and p >= MIN_CONFIDENCE."""


@lru_cache(maxsize=2)
def _identifier(langs: tuple[str, ...] | None = LANGS):
    from py3langid.langid import MODEL_FILE, LanguageIdentifier

    identifier = LanguageIdentifier.from_model_file(MODEL_FILE, norm_probs=True)
    if langs:
        identifier.set_languages(list(langs))
    return identifier


def identify(text: str, langs: tuple[str, ...] | None = LANGS) -> tuple[str, float]:
    label, p = _identifier(langs).classify(text)
    return label, float(p)


def check(text: str, lang: str) -> LanguageCheck:
    label, p = identify(text)
    return LanguageCheck(label, round(p, 4), label != lang and p >= MIN_CONFIDENCE)


def describe() -> str:
    return (f"py3langid {version('py3langid')}, restricted to {'/'.join(LANGS)}; wrong language = top label is "
            f"another language with probability >= {MIN_CONFIDENCE}")


def main() -> None:
    """Validate the rule and two alternatives; write results/language_check.md."""
    from isochron.data.fleurs import train_sentences
    from isochron.provenance import git_commit
    from isochron.schema import SentenceRecord, read_jsonl

    rules = {
        "139 languages, top label ≠ target": lambda t, lang: identify(t, None)[0] != lang,
        "4 languages, top label ≠ target": lambda t, lang: identify(t)[0] != lang,
        f"4 languages, top label ≠ target, p ≥ {MIN_CONFIDENCE} (used)": lambda t, lang: check(t, lang).wrong,
    }

    def refs(lang: str, split: str, field: str = "ref_text") -> list[str]:
        return [getattr(r, field) for r in read_jsonl(Path(f"data/fleurs_{lang}_{split}.jsonl"), SentenceRecord)]

    def prefixes(texts: list[str], k: int) -> list[str]:
        return [" ".join(t.split()[:k]) for t in texts if len(t.split()) > k]

    de_choice = list(train_sentences("de_de").values()) + refs("de", "dev")
    en_choice = list(train_sentences("en_us").values()) + refs("de", "dev", "src_text")
    de_test, en_test = refs("de", "test"), refs("de", "test", "src_text")
    outputs: dict[str, str] = {}
    runs = sorted(Path("results/raw").glob("*_pilot_*_de_dev")) + sorted(Path("results/raw").glob("*_step2_de_dev_syllables"))
    for run in runs:
        for name in ("items.jsonl", "candidates.jsonl"):
            if not (run / name).exists():
                continue
            for line in (run / name).read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                texts = ([c["text"] for r in row["rounds"] for c in r["candidates"]] if "rounds" in row
                         else row["candidates"])
                for t in texts:
                    outputs.setdefault(t, run.name)

    sets = [
        ("Choice", "German: FLEURS train + dev sentences", de_choice, "de", "none"),
        ("Choice", "German: their first 3 words", prefixes(de_choice, 3), "de", "none"),
        ("Choice", "German: their first 5 words", prefixes(de_choice, 5), "de", "none"),
        ("Choice", "English: FLEURS train + dev sentences", en_choice, "de", "all"),
        ("Choice", "English: their first 3 words", prefixes(en_choice, 3), "de", "all"),
        ("Choice", "English: their first 5 words", prefixes(en_choice, 5), "de", "all"),
        ("Choice", "Apertus outputs, German dev runs (distinct texts)", list(outputs), "de", "the English ones"),
        ("Held out", "German: FLEURS test sentences", de_test, "de", "none"),
        ("Held out", "German: their first 3 words", prefixes(de_test, 3), "de", "none"),
        ("Held out", "English: FLEURS test sentences", en_test, "de", "all"),
        ("Held out", "English: their first 3 words", prefixes(en_test, 3), "de", "all"),
        ("Held out", "French: FLEURS dev + test, checked as German", refs("fr", "dev") + refs("fr", "test"), "de", "all"),
        ("Held out", "Italian: FLEURS dev + test, checked as German", refs("it", "dev") + refs("it", "test"), "de", "all"),
        ("Held out", "French: FLEURS dev + test, checked as French", refs("fr", "dev") + refs("fr", "test"), "fr", "none"),
    ]
    table = ["| Set | Sentences | Should be flagged | " + " | ".join(rules) + " |",
             "|-----|----------:|-------------------|" + "---:|" * len(rules)]
    for kind, name, texts, lang, want in sets:
        cells = [f"{sum(f(t, lang) for t in texts)}" for f in rules.values()]
        table.append(f"| {kind}: {name} | {len(texts)} | {want} | " + " | ".join(cells) + " |")
    flagged = [(t, run) for t, run in outputs.items() if check(t, "de").wrong]
    false_alarms = sorted({t for _, name, texts, lang, want in sets if want == "none"
                           for t in texts if check(t, lang).wrong})
    whole = [(texts, lang) for _, name, texts, lang, want in sets if want == "all" and "words" not in name]
    missed = sum(not check(t, lang).wrong for texts, lang in whole for t in texts)
    n_whole = sum(len(texts) for texts, _ in whole)
    near = sorted(((identify(t), t) for t in outputs if identify(t)[0] != "de" and not check(t, "de").wrong),
                  key=lambda x: -x[0][1])

    lines = [
        "# Language check: validation of the rule",
        "",
        f"- Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
        f"- Git commit: {git_commit()}",
        f"- Identifier: {describe()}",
        "- Model under test: none (this checks the identifier). The outputs are those of Apertus 1.5 8B Q4_K_M in the "
        "pilot runs and the go/no-go run on German dev sentences: " + ", ".join(f"`{r.name}`" for r in runs),
        "- TTS: none. Seeds: none (the identifier is deterministic).",
        f"- n: see the table; {len(outputs)} distinct outputs.",
        "",
        "The rule was chosen on the \"Choice\" rows: FLEURS train and dev sentences, and outputs of dev runs. The",
        "\"Held out\" rows use test sentences and the French and Italian files, and did not inform the choice. (An",
        "earlier, informal look at word prefixes also included test sentences; the chosen rule is the same without",
        "them.) Prefix rows cut each sentence after its first k words, as a stand-in for very short outputs.",
        "",
        *table,
        "",
        f"Reading the table: the used rule flags {sum(check(t, 'de').wrong for t in de_choice + de_test)} of the "
        f"{len(de_choice) + len(de_test)} whole German sentences, and {n_whole - missed} of the {n_whole} whole English, "
        "French and Italian sentences. It misses many 3-word English fragments: that is the price of not flagging German",
        "fragments led by a foreign name. The wrong-language outputs seen so far were whole translations into English.",
        "",
        f"## Outputs the rule flags ({len(flagged)})",
        "",
        *[f"- `{run}`: {t}" for t, run in flagged],
        "",
        f"## False alarms: sentences or fragments in the target language that the rule flags ({len(false_alarms)})",
        "",
        *([f"- {identify(t)[0]} {identify(t)[1]:.3f}: {t}" for t in false_alarms] or ["None."]),
        "",
        f"## Outputs with another top label that the rule does not flag ({len(near)})",
        "",
        *([f"- {label} {p:.3f}: {t}" for (label, p), t in near] or ["None."]),
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {OUT.resolve()}")


if __name__ == "__main__":
    main()
