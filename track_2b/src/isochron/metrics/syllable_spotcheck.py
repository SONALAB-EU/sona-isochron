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
        "To verify by hand: count the syllables as the text is normally spoken.",
    ]
    for lang, words in WORDS.items():
        print(f"\n=== {lang.upper()} words: espeak | heuristic | word | espeak IPA")
        out += ["", f"## {lang.upper()} words", "", "| Word | espeak-ng | Heuristic | espeak-ng IPA |",
                "|------|----------:|----------:|---------------|"]
        for w in words:
            e, h, ipa = syllables(w, lang), syllables_heuristic(w, lang), phonemes(w, lang).strip()
            print(f"{e:3d} {h:3d}  {w:14s} {ipa}")
            out.append(f"| {w} | {e} | {h} | `{ipa}` |")

        pool = sorted((sid, s) for sid, s in train_sentences(CONFIGS[lang]).items() if any(c.isdigit() for c in s))
        print(f"\n=== {lang.upper()} train sentences with digits: espeak | heuristic | id | text")
        out += ["", f"## {lang.upper()} sentences with digits", "",
                "| FLEURS id | espeak-ng | Heuristic | Sentence | espeak-ng IPA |",
                "|----------:|----------:|----------:|----------|---------------|"]
        for sid, s in rng.sample(pool, N_SENTENCES):
            e, h, ipa = syllables(s, lang), syllables_heuristic(s, lang), " ".join(phonemes(s, lang).split())
            print(f"{e:3d} {h:3d}  [{sid}] {s}")
            out.append(f"| {sid} | {e} | {h} | {s} | `{ipa}` |")

    path = Path("results") / "syllable_spotcheck.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"\nwrote {path.resolve()}")


if __name__ == "__main__":
    main()
