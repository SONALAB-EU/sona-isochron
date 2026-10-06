"""Length counters: characters, words, syllables, targets and hits."""

from __future__ import annotations

import pytest

from isochron.metrics.length import (
    chars,
    count_nuclei,
    espeak_available,
    hit,
    syllables,
    syllables_heuristic,
    target,
    words,
)

needs_espeak = pytest.mark.skipif(not espeak_available(), reason="espeak-ng not installed")


def test_chars_drop_spaces_keep_punctuation() -> None:
    assert chars("Hallo Welt!") == 10
    assert chars("  Hallo  Welt!  ") == 10


def test_chars_after_nfc() -> None:
    assert chars("über") == chars("über") == 4


def test_words_skip_punctuation_tokens() -> None:
    assert words("Hallo , Welt –") == 2
    assert words("l'apprentissage est « facile »") == 3
    assert words("9:30 Uhr") == 2


@pytest.mark.parametrize(
    ("level", "n", "expected"),
    [(80, 25, 20), (70, 15, 11), (90, 15, 14), (60, 17, 10), (100, 7, 7)],
)
def test_target_rounds_half_up(level: int, n: int, expected: int) -> None:
    assert target(level, n) == expected


def test_hit_is_within_ten_percent_inclusive() -> None:
    assert hit(45, 50) and hit(55, 50) and hit(50, 50)
    assert not hit(44, 50) and not hit(56, 50)


@pytest.mark.parametrize(
    ("ipa", "lang", "expected"),
    [
        ("t_eː_ˈɑː_t_ɜ", "de", 3),  # Theater: hiatus counts twice
        ("_ˈaɪ_ɜ", "de", 2),  # Eier: diphthong is one phoneme
        ("f_a_m_ˈiː_l_ɪ__ə", "de", 3),  # Familie: unstressed i before a vowel is a glide
        ("t_ˌeː_oː_r_ˈiː_ə_n", "de", 4),  # Theorien: stressed i keeps its syllable
        ("n_y_ˈi", "fr", 1),  # nuit: y before i is [ɥ]
        ("n_y_ˈi", "de", 2),  # the French rule does not apply to German
        ("uː_ɐ̯", "de", 1),  # non-syllabic mark
        ("h_aː_b_n̩", "de", 2),  # syllabic consonant
        ("", "de", 0),
    ],
)
def test_count_nuclei(ipa: str, lang: str, expected: int) -> None:
    assert count_nuclei(ipa, lang) == expected


@needs_espeak
@pytest.mark.parametrize(
    ("text", "lang", "expected"),
    [
        ("petite", "fr", 2),  # regression: espeak-ng drops the last letter without a trailing newline
        ("Zeile", "de", 2),
        ("nuit", "fr", 1),
        ("aujourd'hui", "fr", 3),
        ("Familie", "de", 3),
        ("Theater", "de", 3),
        ("17 000", "fr", 3),  # dix-sept mille: numbers count as spoken
        ("1995", "fr", 7),  # mille neuf cent quatre-vingt-quinze
    ],
)
def test_syllables_espeak(text: str, lang: str, expected: int) -> None:
    assert syllables(text, lang) == expected


def test_syllables_heuristic() -> None:
    assert syllables_heuristic("Haus", "de") == 1
    assert syllables_heuristic("Fenster", "de") == 2
    assert syllables_heuristic("petite", "fr") == 2
    assert syllables("petite", "fr", counter="heuristic") == 2


def test_unknown_counter() -> None:
    with pytest.raises(ValueError):
        syllables("Haus", "de", counter="nope")
