"""The time check: the seeded demo rule, trimming as for the English slots, and the duration and fit maths."""

from __future__ import annotations

import io
import random

import numpy as np
import pytest

from isochron import time_check as tc


def source(i: int, **kw: bool) -> dict:
    row = {"id": str(i), "noisy": False, "a_usable": True, "a_fit": False, "c_usable": True, "c_fit": True,
           "c_kept_plain": False, "c_kept_main": True, "c_kept_second": True}
    return row | kw


def test_demo_rule_is_seeded_and_keeps_the_sheet_and_noisy_recordings_out() -> None:
    rows = [source(i) for i in range(10, 30)]  # eligible "fit" lines
    rows += [source(i, c_fit=False) for i in range(40, 50)]  # the loop ran and missed
    rows += [source(60, c_kept_second=False), source(61, a_fit=True), source(62, c_kept_plain=True, c_fit=False),
             source(63, noisy=True), source(64, c_usable=False, c_fit=False)]
    fit, miss, counts = tc.demo_choice(rows, exclude={"10", "41"})
    assert counts == {"pool": 32, "eligible_fit": 19, "eligible_miss": 9}
    eligible_fit = [str(i) for i in range(11, 30)]  # numeric order, without the sheet's 10
    assert fit == random.Random(0).sample(eligible_fit, 3)
    assert miss == random.Random(0).sample([str(i) for i in range(40, 50) if i != 41], 1)
    assert not {"10", "41", "60", "61", "62", "63", "64"} & set(fit + miss)
    assert tc.demo_choice(list(reversed(rows)), exclude={"10", "41"})[:2] == (fit, miss)  # input order does not matter
    with pytest.raises(SystemExit, match="too few"):
        tc.demo_choice(rows[:2], exclude=set())


def tone(seconds: float, sr: int, lead: float = 0.5, tail: float = 0.7, amp: float = 0.5) -> np.ndarray:
    t = np.arange(int(seconds * sr)) / sr
    voiced = amp * np.sin(2 * np.pi * 220 * t).astype(np.float32)
    return np.concatenate([np.zeros(int(lead * sr), np.float32), voiced, np.zeros(int(tail * sr), np.float32)])


def test_trimming_removes_silence_the_same_way_at_16_and_24_khz() -> None:
    a, b = tc.measure(tone(2.0, 16_000), 16_000), tc.measure(tone(2.0, 24_000), 24_000)
    assert a.raw_s == pytest.approx(3.2) and b.raw_s == pytest.approx(3.2)
    assert 2.0 <= a.trimmed_s <= 2.0 + 2 * 2048 / 16_000  # trim keeps up to a 2048-sample frame each side
    assert b.trimmed_s == pytest.approx(a.trimmed_s, abs=0.035)  # the 24 kHz speech is trimmed at 16 kHz too
    assert a.peak == pytest.approx(0.5, abs=1e-3) and a.clipped == 0.0
    assert tc.measure(np.clip(tone(1.0, 16_000, amp=1.5), -1, 1), 16_000).clipped > 0.2  # half the 1 s tone, in 2.2 s
    with pytest.raises(ValueError, match="silent"):
        tc.measure(np.zeros(16_000, np.float32), 16_000)
    with pytest.raises(ValueError, match="empty"):
        tc.measure(np.zeros(0, np.float32), 16_000)


def test_trimming_matches_the_english_slots_of_build_fleurs() -> None:
    import soundfile as sf

    from isochron.data.build_fleurs import measure as fleurs_measure

    y = tone(1.3, 16_000) + np.float32(0.001) * np.random.default_rng(0).standard_normal(int(2.5 * 16_000)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, y, 16_000, format="WAV", subtype="FLOAT")
    raw, trimmed, floor = fleurs_measure(buf.getvalue())
    ours = tc.measure(y, 16_000)
    assert (ours.raw_s, ours.trimmed_s) == (raw, trimmed) and ours.floor_db == pytest.approx(floor)


def test_fit_median_take_and_paired_statistics() -> None:
    assert tc.fits(11.0, 10.0) and tc.fits(9.0, 10.0) and not tc.fits(11.01, 10.0) and not tc.fits(8.99, 10.0)
    assert tc.median_take([3.1, 2.9, 3.0]) == 2 and tc.median_take([1.0, 2.0, 3.0]) == 1
    assert tc.mcnemar_exact(0, 0) == 1.0
    assert tc.mcnemar_exact(6, 0) == pytest.approx(2 / 64)  # all 6 discordant pairs one way
    assert tc.mcnemar_exact(3, 3) == 1.0
    line = tc.fit_line([10, 20, 30], [2.1, 4.1, 6.1])
    assert line["r"] == pytest.approx(1.0) and line["slope"] == pytest.approx(0.2) and line["intercept"] == pytest.approx(0.1)
    assert line["per_unit"] == pytest.approx(12.3 / 60)
    assert tc.text_id("Haus") == tc.text_id("Haus") != tc.text_id("Haus.")


def test_extra_words_counts_speech_after_the_text() -> None:
    text = "Soziale Löwen leben in Rudeln zusammen und sind Katzen"
    assert tc.extra_words(text, "Soziale Löwen leben in Rudeln zusammen und sind Katzen.") == 0
    assert tc.extra_words(text, "Soziale Löwen leben in Wurden zusammen und sind Katzen.") == 0  # a misheard word
    assert tc.extra_words(text, "Soziale Löwen leben in Rudeln zusammen und sind Katzen. That I've Deconstued Your En.") == 6  # I've counts as two words
    assert tc.extra_words(text, "Tourist D. S.") == 3  # nothing in common: every word is extra


def test_the_qwen_job_uses_the_same_rules_as_the_package() -> None:
    import importlib.util
    from pathlib import Path

    from isochron.native_check import full_stop

    path = Path(__file__).resolve().parents[1] / "hpc" / "tts_qwen_synth.py"
    spec = importlib.util.spec_from_file_location("tts_qwen_synth", path)
    job = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(job)
    for text, heard in (("Ein Land", "Ein Land. Und mehr Worte hier"), ("Luxusstrandresorts.", "Luxus Strand Resorts."),
                        ("Er sagte \"ja.\"", "Er sagte ja.")):
        assert job.full_stop(text) == full_stop(text)
        assert job.extra_words(text, heard) == tc.extra_words(text, heard)
    assert job.extra_words("Luxusstrandresorts.", "Luxus Strand Resorts.") == 3  # a split compound counts as extra
    assert job.MAX_EXTRA == 1 and job.TAKES == 3 and job.ROUNDS == 10 and job.VOICE == "Aiden"


def test_the_chars10_rule_ignores_split_compounds_but_not_extra_speech() -> None:
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("tts_qwen_synth", Path(__file__).resolve().parents[1] / "hpc" / "tts_qwen_synth.py")
    job = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(job)
    text = "Die meisten kleinen Inseln sind souverän, Luxusstrandresorts."
    assert job.longer_chars(text, "Die meisten kleinen Inseln sind souverän. Luxus-Strand-Resorts!") == 1.0
    assert job.longer_chars(text, text + " Und dann noch viel mehr Worte danach.") > job.MAX_LONGER
    assert job.longer_chars("Ja.", "") == 0.0
