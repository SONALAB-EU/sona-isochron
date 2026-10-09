"""Length counters: characters, words and syllables.

chars      Code points after NFC normalisation, with spaces removed;
           punctuation counts. This is the IWSLT 2022 isometric scorer's
           definition (amazon-science/isometric-slt,
           scripts/isometric_slt_stat.py strips the line, deletes " " and
           takes len()).
words      Whitespace-separated tokens that contain at least one letter or
           digit, so punctuation on its own is not a word.
syllables  espeak-ng turns the text into IPA as it would be spoken, so numbers
           and abbreviations count as spoken. We count the syllabic nuclei in
           its output: phonemes that contain a vowel or a syllabic consonant.
           espeak-ng is GPL-3.0 and is only run as an external program, never
           imported.

German years: espeak-ng reads 1959 as a plain number ("eintausendneunhundert…",
10 syllables). Before calling it, German 4-digit numbers 1100–1999 that are not
next to a unit or currency are rewritten as years: 1959 -> "19 hundert 59",
1900 -> "19 hundert". French reads years as full numbers, so it is unchanged.

Two corrections for how espeak-ng writes glides (checked by hand on its output):
- fr: "y" before "i" is the glide [ɥ] (nuit, lui, depuis), not a vowel.
- de: an unstressed i before another vowel in the same word is [i̯]
  (Familie, Italien, Region), not a vowel.

syllables_heuristic() counts vowel-letter groups instead. It is a fallback for
machines without espeak-ng and does not handle numbers. Results record which
counter was used.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import unicodedata
from functools import lru_cache

ESPEAK = "espeak-ng"
VOICES = {"en": "en-us", "de": "de", "fr": "fr", "it": "it"}
UNITS = ("chars", "words", "syllables")
COUNTERS = ("espeak", "heuristic")

IPA_VOWELS = set("aeiouyæøœɐɑɒɔəɘɛɜɞɤɨɪɯɵɶʉʊʌʏᵻɚɝ")
SYLLABIC_MARKS = ("̩", "̍")  # combining vertical line below / above
NON_SYLLABIC = "̯"  # combining inverted breve below
STRESS = "ˈˌ"
LANG_SWITCH = re.compile(r"\([a-z]{2,3}(?:-[a-z0-9]+)?\)")  # e.g. "(en)" around a foreign word

UNITS_AND_CURRENCIES = (
    r"%|‰|°|€|\$|£|¥|Prozent|Grad|Euro|Cent|Dollar|US-Dollar|Pfund|Franken|CHF|USD|EUR|GBP|Yen|"
    r"km²|m²|km|cm|mm|m|kg|g|mg|t|l|ml|ha|kWh|MW|kW|W|Meter|Kilometer|Meilen|Fuß|Kilogramm|Gramm|"
    r"Tonnen|Liter|Hektar"
)
GERMAN_YEAR = re.compile(
    rf"(?<![\d.,$€£¥])(?<![$€£¥] )\b(1[1-9])(\d\d)(?!\d)(?![.,]\d)(?!\s*(?:{UNITS_AND_CURRENCIES})(?![^\W\d_]))"
)

VOWEL_LETTERS = {
    "en": "aeiouy",
    "de": "aeiouyäöü",
    "fr": "aeiouyàâäéèêëîïôöùûüÿœæ",
    "it": "aeiouàèéìíîòóùú",
}


def normalise(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def chars(text: str) -> int:
    return len(normalise(text).strip().replace(" ", ""))


def words(text: str) -> int:
    return sum(any(ch.isalnum() for ch in token) for token in normalise(text).split())


def espeak_available() -> bool:
    return shutil.which(ESPEAK) is not None


@lru_cache(maxsize=1)
def espeak_version() -> str:
    out = subprocess.run([ESPEAK, "--version"], capture_output=True, text=True, check=True).stdout
    return out.split("Data at")[0].strip()


def spoken_years(text: str) -> str:
    """German: 1959 -> "19 hundert 59", unless a unit or currency is attached."""

    def year(m: re.Match[str]) -> str:
        rest = int(m.group(2))
        return f"{m.group(1)} hundert" + (f" {rest}" if rest else "")

    return GERMAN_YEAR.sub(year, text)


@lru_cache(maxsize=1 << 16)
def phonemes(text: str, lang: str) -> str:
    """espeak-ng's IPA for text: phonemes joined by "_", words by whitespace."""
    # The trailing newline matters: with --stdin and no newline, espeak-ng 1.52
    # drops the last character ("petite" is read as "petit").
    result = subprocess.run(
        [ESPEAK, "-q", "--ipa", "--sep=_", "-v", VOICES[lang], "--stdin"],
        input=" ".join((spoken_years(normalise(text)) if lang == "de" else normalise(text)).split()) + "\n",
        capture_output=True,
        text=True,
        check=True,
    )
    return LANG_SWITCH.sub("", result.stdout)


def is_nucleus(phoneme: str) -> bool:
    if any(mark in phoneme for mark in SYLLABIC_MARKS):
        return True
    return any(
        ch in IPA_VOWELS and phoneme[i + 1 : i + 2] != NON_SYLLABIC for i, ch in enumerate(phoneme)
    )


def count_nuclei(ipa: str, lang: str) -> int:
    n = 0
    for word in ipa.split():
        tokens = [t for t in word.split("_") if t.strip("-")]
        for i, tok in enumerate(tokens):
            if not is_nucleus(tok):
                continue
            nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
            stressed = any(ch in STRESS for ch in tok)
            base = tok.strip(STRESS + "ː-")
            if lang == "fr" and base == "y" and not stressed and nxt.lstrip(STRESS).startswith("i"):
                continue
            if lang == "de" and base in ("i", "ɪ") and not stressed and is_nucleus(nxt):
                continue
            n += 1
    return n


def syllables_heuristic(text: str, lang: str) -> int:
    vowels = VOWEL_LETTERS[lang]
    n = 0
    for word in re.findall(r"[^\W\d_]+", normalise(text).lower()):
        k = len(re.findall(f"[{vowels}]+", word))
        if lang == "fr" and k > 1 and re.search(r"[^aeiouyàâäéèêëîïôöùûüÿœæ]es?$", word):
            k -= 1  # silent final e: petite, écoles
        elif lang == "en" and k > 1 and word.endswith("e") and not word.endswith("le"):
            k -= 1  # silent final e: make, time
        n += k
    return n


def syllables(text: str, lang: str, counter: str = "espeak") -> int:
    if counter == "heuristic":
        return syllables_heuristic(text, lang)
    if counter != "espeak":
        raise ValueError(f"unknown syllable counter {counter!r}")
    return count_nuclei(phonemes(text, lang), lang)


def default_counter() -> str:
    """espeak if it is installed, otherwise the heuristic, with a warning."""
    if espeak_available():
        return "espeak"
    print(f"warning: {ESPEAK} not found, counting syllables with the vowel-group heuristic", file=sys.stderr)
    return "heuristic"


def counter_description(counter: str) -> str:
    return espeak_version() if counter == "espeak" else "vowel-group heuristic (isochron.metrics.length)"


def length(text: str, unit: str, lang: str, counter: str = "espeak") -> int:
    if unit == "chars":
        return chars(text)
    if unit == "words":
        return words(text)
    if unit == "syllables":
        return syllables(text, lang, counter)
    raise ValueError(f"unknown unit {unit!r}")


def target(level: int, n: int) -> int:
    """level % of n, rounded half up (integer arithmetic, so 70 % of 15 is 11)."""
    return (level * n + 50) // 100


def hit(n: int, t: int) -> bool:
    """Within ±10 % of the target t."""
    return 10 * abs(n - t) <= t
