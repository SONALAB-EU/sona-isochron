"""Syllable counts to check by hand: espeak-ng next to the vowel-group heuristic.

20 German and 20 French words that cover diphthongs, hiatus, glides, silent e
and loanwords, plus 5 FLEURS train sentences per language that contain digits
(drawn with seed 0). Prints the counts and writes results/syllable_spotcheck.md.
Run from track_2b/:

    uv run python -m isochron.metrics.syllable_spotcheck
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from pathlib import Path

from isochron.data.fleurs import REVISION, train_sentences
from isochron.metrics.length import espeak_version, phonemes, syllables, syllables_heuristic
from isochron.provenance import git_commit

WORDS = {
    "de": [
        "Haus", "Fenster", "Mädchen", "Schifffahrt", "Theater", "Eier", "Bauer", "Uhr",
        "Museum", "beobachten", "Familie", "Linien", "Region", "Studium", "Ruine", "Poesie",
        "Kakao", "naiv", "Zoologie", "Melodien",
    ],
    "fr": [
        "aéroport", "pays", "oiseau", "petite", "théâtre", "poème", "Noël", "ouest",
        "maïs", "réaliser", "mademoiselle", "cahier", "hier", "lion", "école", "nuit",
        "depuis", "cuisine", "aujourd'hui", "juillet",
    ],
}
# Reference counts by hand (Claude, standard pronunciation, Duden for German;
# not yet checked by a native speaker). Studium is 2 per Duden [ˈʃtuːdi̯ʊm].
EXPECTED_WORDS = {
    "de": [1, 2, 2, 2, 3, 2, 2, 1, 3, 4, 3, 2, 2, 2, 3, 3, 3, 2, 4, 4],
    "fr": [4, 2, 2, 2, 2, 2, 2, 1, 2, 4, 3, 2, 1, 1, 2, 1, 2, 2, 3, 2],
}
EXPECTED_SENTENCES = {
    "de": {860: 51, 1048: 40, 45: 68, 421: 25, 1320: 50},  # 421: "15." is "fünfzehnten"
    "fr": {1221: 42, 1013: 43, 478: 49, 1189: 44, 713: 30},
}
CONFIGS = {"de": "de_de", "fr": "fr_fr"}
SEED = 0
N_SENTENCES = 5


def main() -> None:
    started = datetime.now(timezone.utc)
    rng = random.Random(SEED)
    out = [
        "# Syllable counter spot check",
        "",
        f"- Date: {started:%Y-%m-%d %H:%M} UTC",
        f"- Git commit: {git_commit()}",
        f"- Counter: {espeak_version()}, syllabic nuclei in its IPA output "
        "(`isochron.metrics.length.syllables`), next to the vowel-group heuristic",
        f"- Sentences: FLEURS train (revision `{REVISION}`) containing digits, "
        f"{N_SENTENCES} per language drawn with seed {SEED}",
        "- Model, endpoint, TTS: none",
        f"- n: {sum(len(w) for w in WORDS.values())} words, {N_SENTENCES * len(WORDS)} sentences",
        "",
        "Reference: hand counts by Claude (standard pronunciation, Duden for German), "
        "not yet checked by a native speaker.",
    ]
    tally = {"espeak-ng": [0, 0], "heuristic": [0, 0]}  # [exact, total]
    errors: list[str] = []

    def record(item: str, ref: int, e: int, h: int) -> None:
        for name, n in (("espeak-ng", e), ("heuristic", h)):
            tally[name][0] += n == ref
            tally[name][1] += 1
        if e != ref:
            errors.append(f"{item}: espeak-ng {e}, reference {ref}")

    sections = []
    for lang, words in WORDS.items():
        print(f"\n=== {lang.upper()} words: reference | espeak | heuristic | word | espeak IPA")
        sections += ["", f"## {lang.upper()} words", "", "| Word | Reference | espeak-ng | Heuristic | espeak-ng IPA |",
                     "|------|----------:|----------:|----------:|---------------|"]
        for w, ref in zip(words, EXPECTED_WORDS[lang]):
            e, h, ipa = syllables(w, lang), syllables_heuristic(w, lang), phonemes(w, lang).strip()
            record(w, ref, e, h)
            print(f"{ref:3d} {e:3d} {h:3d}  {w:14s} {ipa}")
            sections.append(f"| {w} | {ref} | {e} | {h} | `{ipa}` |")

        pool = sorted((sid, s) for sid, s in train_sentences(CONFIGS[lang]).items() if any(c.isdigit() for c in s))
        print(f"\n=== {lang.upper()} train sentences with digits: reference | espeak | heuristic | id | text")
        sections += ["", f"## {lang.upper()} sentences with digits", "",
                     "| FLEURS id | Reference | espeak-ng | Heuristic | Sentence | espeak-ng IPA |",
                     "|----------:|----------:|----------:|----------:|----------|---------------|"]
        for sid, s in rng.sample(pool, N_SENTENCES):
            ref = EXPECTED_SENTENCES[lang][sid]
            e, h, ipa = syllables(s, lang), syllables_heuristic(s, lang), " ".join(phonemes(s, lang).split())
            record(f"{lang} sentence {sid}", ref, e, h)
            print(f"{ref:3d} {e:3d} {h:3d}  [{sid}] {s}")
            sections.append(f"| {sid} | {ref} | {e} | {h} | {s} | `{ipa}` |")

    summary = [f"- {name}: {k}/{n} items exact ({100 * k / n:.0f} %)" for name, (k, n) in tally.items()]
    out += ["", "## Accuracy against the reference", "", *summary, "", "espeak-ng misses:", "",
            *[f"- {x}" for x in errors], *sections]
    print("\n" + "\n".join(summary + ["espeak-ng misses: " + "; ".join(errors)]))

    path = Path("results") / "syllable_spotcheck.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"\nwrote {path.resolve()}")


if __name__ == "__main__":
    main()
