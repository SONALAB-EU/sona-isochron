# Demo video: lines, captions and the timing slide

Material for the 2-minute demo. Every number comes from committed results files; the audio is not in the
repository (it is git-ignored) and is rebuilt by `isochron.time_check demo-voices` (`STATUS.md`).

## The three demo lines

Seeded picks, not typical results: drawn by the rule in `results/time_check/selection.json` (protocol v2.24),
from test sources whose English recording is not flagged noisy and that are not on the native-speaker sheet.
1891, the fourth pick, is left out: its English reader is slow (0.48 s per syllable, against 0.19–0.21 for
the other three, with pauses around the names), so its slot (14.5 s) says little about the line.

The German voices are synthetic Qwen3-TTS presets (Apache-2.0), matched to the English reader's gender
(protocol v2.33): Serena for these three female readers. They are presets, not clones of the readers.
"Ours" here is step 4's syllable budget (the English syllables × a preset rate), not the voice-calibrated
budget of the slide. Seconds are trimmed, and the speech is the median of 3 clean takes.

| Line | Figure | Audio (git-ignored) | Caption |
|------|--------|---------------------|---------|
| 1679 | `docs/figures/demo_voices/demo_1679.png` | `audio/demo_voices/1679/{english,plain,ours}.wav` | Ours fits the English slot: +5 % (plain translation: +72 %). |
| 1903 | `docs/figures/demo_voices/demo_1903.png` | `audio/demo_voices/1903/{english,plain,ours}.wav` | Ours is just inside the ±10 % band: +10 % (plain translation: +48 %). |
| 2002 | `docs/figures/demo_voices/demo_2002.png` | `audio/demo_voices/2002/{english,plain,ours}.wav` | Ours is still too long: +21 % (plain translation: +59 %). The output records that it does not fit; a flag that sends such lines to a human is future work. |

Measured (`results/time_check/demo_voices/durations.csv`): English slot, plain, ours in seconds:
1679: 3.17, 5.46, 3.33; 1903: 8.38, 12.42, 9.22; 2002: 5.50, 8.74, 6.66.

## The timing slide

`docs/figures/demo_voices/timing_slide.png` (`results/time_check_calibrated.md`; exploratory, post-hoc,
added after test outputs existed):

> 99 German test sources, read by one synthetic voice (Qwen3-TTS, preset Aiden), with the syllable budget
> calibrated to that voice (the English slot ÷ 0.231 s per syllable, measured on dev). Within ±10 % of the
> English speaker's time: ours 47, plain translation 25. Paired: ours fits where plain does not in 22
> sources, the reverse in none (exact McNemar p = 4.8e-07).

Say alongside: with the uncalibrated syllable budget and the same voice, ours fitted 6 of 21 sources and
plain translation 8 (`results/time_check_qwen.md`); budgets must be calibrated to the target voice.
