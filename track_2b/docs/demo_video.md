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

## The video

`demo/build_video.py` builds `demo/out/isochron_demo.mp4` and `demo/out/isochron_demo.srt` (both
git-ignored, like the narration in `demo/narration/`); its docstring gives the command. It reads every number
on screen from committed files (the key-results and cost tables of `technical_report.md`,
`results/time_check/demo_voices/durations.csv`, `data/hf_dataset/native_check/test.jsonl`) and the raw loop
record of the line shown as not fitting (`results/raw/hpc_8b_step4_test/items.jsonl`, git-ignored).

Picks, each by a fixed rule:

- "Just inside the band": 1903, ours +9.9 % (2002, at +21 %, is outside the band).
- "The output records it": 1661, the first German test line by ID (seed 0, syllable budget) where ours ran
  the loop and its final candidate still missed the budget: 38 syllables for a budget of 25 after 2
  revisions, `"hit": false`, `"final_accepted": false`.
- The dropped "some": native-check line 32 (FLEURS 1908, ours), marked wrong by the rater; both NLIs kept
  it, the evaluation judge (Qwen3-14B) did flag it (`results/human_check.md`).

### Script (as recorded)

1. In dubbing, a translated line must fit the time the actor speaks. This English line takes three seconds.
   A plain German translation takes five and a half: over seventy percent too long. Today, someone fixes that
   by hand.
2. Isochron uses Apertus 1.5, the open Swiss model, with no fine-tuning. Apertus translates, then shortens to
   a length budget. Our code checks every candidate for length, meaning and language, and sends specific
   feedback. Apertus revises at most twice.
3. After the loop, the same line takes three point three seconds: it fits. This one lands just inside the
   band. And when the loop can't make a line fit, the output records it, so an editor knows which lines need
   work.
4. On the held-out test set, English to German and French, plain translation fits the budget in 20 to 56
   percent of lines; with our loop, 70 to 80. Lines that run too long, the costly error in dubbing, drop from
   up to 79 percent to at most 20. The cost: by an independent check, up to about five points fewer lines
   keep their full meaning.
5. In a separate test, we calibrated the budget to one synthetic voice. Then our lines fit the English timing
   in 47 of 99 cases, against 25 for plain translation.
6. It all runs sovereign: one command starts Apertus and our app in containers with no network, even on a
   laptop. On a GPU it costs about ten H100-minutes per thousand lines.
7. Machine meaning checks miss subtle changes, so a native speaker reviewed our German and found slips they
   missed, like a dropped 'some'. We report them. Isochron, by SONALAB, for Hack Apertus.

Checked against the data: 1679 is 3.17 s English, 5.46 s plain (+72 %), 3.33 s ours (+5 %); fit 19.6–55.6 %
(plain) and 69.9–80.2 % (ours); too long up to 79.1 % (plain) and at most 20.4 % (ours); the second NLI puts
ours 0.5–5.3 points below plain; 47 and 25 of 99; the cost estimate is 0.47–0.65 H100-s per line, 8–11
H100-minutes per 1,000 lines.
