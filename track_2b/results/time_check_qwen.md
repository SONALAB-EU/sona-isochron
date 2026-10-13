# Time check with Qwen3-TTS: German speech against the English slot (exploratory, post-hoc)

Post-hoc, added after test outputs existed; rules fixed before generation (protocol v2.28). Secondary to the human-speech check (`results/human_speech.md`). The earlier Chatterbox run failed its checks and is kept as it was (`results/time_check.md`, protocol v2.25).

**Status: every check of the audio passed.** 1 text(s) short of 3 clean takes after 10 rounds, reported and left out: cc64b45f2726 (0 clean; 1912 c).

- Date: 2026-10-13 10:43 UTC; git commit dbd91f1d195712fb0bdf56379f354221eeeebd81
- Texts: step 4 test, run `hpc_8b_step4_test` (Apertus 1.5 8B, BF16; vLLM on the cluster, its endpoint in `results/step4_test.md`), German, syllable budget, generation seed 0; each read with a full stop at the end (`native_check.full_stop`)
- TTS engine: Qwen3-TTS: Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice @ 0c0e305 (Apache-2.0), qwen-tts 0.1.1 (Apache-2.0); voice: the preset Aiden (chosen before generation), no instruction, no reference audio, no cloning; endpoint: none (local inference)
- TTS settings: language German, temperature=0.9, top_k=50, top_p=1.0, repetition_penalty=1.05, subtalker_temperature=0.9, subtalker_top_k=50, subtalker_top_p=1.0, max_new_tokens=2048, dtype=bfloat16, attn_implementation=sdpa, sample_rate=24000; versions: qwen-tts 0.1.1, torch 2.6.0+cu124, torchaudio 2.6.0+cu124, transformers 4.57.3, accelerate 1.12.0, openai-whisper 20250625, numpy 2.2.6; NVIDIA H100 80GB HBM3, one job, 203 s wall time
- Rounds and seeds: round r seeds torch with r and reads every text still short of 3 clean takes (at most 10 rounds); a take is clean when Whisper small (German, temperature 0) hears at most 1 word after the text's last word. Float WAV. Duration = the median clean take.
- English slot and fit: as in `results/time_check.md` (FLEURS recording, trimmed at 16 kHz with `build_fleurs.TRIM`; within ±10 %). Syllables: eSpeak NG text-to-speech: 1.52.0.
- n: 21 of the sheet's 25 sources (3 skipped as noisy); 47 distinct texts; 157 takes generated

## Rejected takes

| Texts | n | Takes rejected / generated | Texts short of 3 clean takes |
|---|---:|---:|---:|
| (a) on the timed sources | 22 | 4/70 | 0 |
| (c) on the timed sources | 22 | 13/76 | 1 |
| demo texts | 8 | 2/26 | 0 |

Every rejected take, as Whisper heard its end (extra words in brackets):

- 2d8cc638d752 (a), round 0 [3]: …n oder mit Frankreich assoziiert und bekannt als Luxus-Strand-Resorts.
- cc64b45f2726 (c), round 0 [4]: …nd entweder Souverän oder mit Frankreich Assasir Luxus Strand Resorts.
- 97d3032a0c08 (c), round 0 [3]: …n Japan-Bug Bayern präsentiert, begleitet vom Sanger Radyu Kandelwald.
- 2d8cc638d752 (a), round 1 [2]: …nen oder mit Frankreich assoziiert und bekannt als Luxistrand-Resorts.
- cc64b45f2726 (c), round 1 [4]: …der zu verrein oder mit Frankreich assuzilliert. Luxus-Strand-Resorts.
- 135595639080 (a), round 1 [2]: …Erasmith haben ihre Verbleibendenkonzerte auf ihr Tourapkizakt.
- cc64b45f2726 (c), round 2 [3]: …tweder zu vorein oder mit Frankreich assoziiert. Luxus-Strand-Resorts.
- b6518d545b44 (c), round 2 [3]: …oretisch. Das Programm simulierte ZDG-Gitarriors Galaxiebeobachtungen.
- 2d8cc638d752 (a), round 3 [2]: …nen oder mit Frankreich assoziiert und bekannt als Luxustrand-Resorts.
- cc64b45f2726 (c), round 3 [4]: …weder souverän oder mit Frankreich assoziiert. Looks a Strand Resorts.
- b6518d545b44 (c), round 3 [2]: …theoretisch, das Programm simulierte zägetariest Galaxiebeobachtungen.
- 2d8cc638d752 (a), round 4 [2]: …nen oder mit Frankreich assoziiert und bekannt als Luxustrand Resorts.
- cc64b45f2726 (c), round 4 [3]: …ntweder souverän oder mit Frankreich assoziiert. Luxus Strand Resorts.
- b6518d545b44 (c), round 4 [2]: …ar theoretisch. Das Programm simulierte zagitarie Galaxybeobachtungen.
- cc64b45f2726 (c), round 5 [3]: …ntweder souverän oder mit Frankreich assoziiert. Luxus Strandry Sorts.
- cc64b45f2726 (c), round 6 [3]: …ntweder souverän oder mit Frankreich assoziiert. Luxus Strand Resorts.
- cc64b45f2726 (c), round 7 [2]: … entweder souverän oder mit Frankreich assoziiert. Luxistrend Resorts.
- cc64b45f2726 (c), round 8 [5]: …eder zuvor in Oder mit Frankreich assizeiert, looks as strand resorts.
- cc64b45f2726 (c), round 9 [2]: …d entweder souverän oder mit Frankreich assoziiert. Luxustrant Resorts

## Fit in seconds

| System | Fits the English slot | Median speech ÷ slot | Range |
|---|---|---:|---|
| (a) plain translation | 8/21 (38 %) | 0.98 | 0.66–1.48 |
| (c) ours | 6/21 (29 %) | 0.89 | 0.58–1.44 |

Paired, per source: (c) fits and (a) does not in 3, the reverse in 5; exact McNemar p = 0.727. In 5 sources (c) kept (a)'s text. Absolute shares depend on the voice's speaking rate; the comparison of (a) with (c) is what counts.

## Do syllables predict seconds?

- Qwen3-TTS speech, 38 distinct texts: r = 0.98; 0.231 s per syllable overall; least squares: 0.216 s per syllable + 0.59 s.
- Clean takes of the same text differ by a median of 9 % of its duration (largest 27 %).

## Per source

| Source | English slot (s) | (a) s | (c) s | (a) fits | (c) fits |
|---|---:|---:|---:|---|---|
| 1682 | 14.46 | 14.72 | 12.18 | yes | no |
| 1699 | 8.64 | 12.80 | 9.06 | no | yes |
| 1712 | 15.10 | 13.01 | 13.01 | no | no |
| 1733 | 16.54 | 17.92 | 14.02 | yes | no |
| 1737 | 6.24 | 5.14 | 3.81 | no | no |
| 1773 | 10.62 | 9.46 | 9.46 | no | no |
| 1790 | 11.55 | 14.88 | 9.70 | no | no |
| 1794 | 8.10 | 11.14 | 11.65 | no | no |
| 1806 | 9.25 | 12.48 | 11.70 | no | no |
| 1817 | 4.19 | 4.50 | 4.35 | yes | yes |
| 1820 | 7.97 | 7.62 | 5.31 | yes | no |
| 1831 | 9.89 | 10.98 | 10.26 | no | yes |
| 1846 | 10.91 | 10.59 | 10.66 | yes | yes |
| 1861 | 7.30 | 7.14 | 8.26 | yes | no |
| 1871 | 6.27 | 4.13 | 4.13 | no | no |
| 1879 | 5.17 | 4.58 | 4.58 | no | no |
| 1908 | 6.40 | 5.54 | 4.58 | no | no |
| 1922 | 8.42 | 10.18 | 9.97 | no | no |
| 1925 | 9.97 | 9.81 | 5.78 | yes | no |
| 1962 | 8.58 | 8.00 | 8.00 | yes | yes |
| 1980 | 7.92 | 8.98 | 7.78 | no | yes |

## Demo lines

The rule in `results/time_check/selection.json`; speech: the median clean take.

| Source | Kind | English slot (s) | (a) s | (c) s | Figure |
|---|---|---:|---:|---:|---|
| 1891 | fit | 14.50 | 7.01 | 5.54 | `docs/figures/demo/demo_1891.png` |
| 1903 | fit | 8.38 | 10.90 | 9.30 | `docs/figures/demo/demo_1903.png` |
| 1679 | fit | 3.17 | 4.37 | 3.22 | `docs/figures/demo/demo_1679.png` |
| 2002 | loop missed | 5.50 | 7.86 | 6.18 | `docs/figures/demo/demo_2002.png` |

## Checks

- Files: 183 (`results/time_check/manifest_qwen.csv`: every take, clean or not, and the English recordings, with SHA-256 and licence; the audio stays in `audio/`, git-ignored). None empty or silent.
- Float WAV, so nothing is clipped in the files; 0 of 157 takes peak above 1.0 (max 1.000) and would clip only if written as 16-bit.
- Seconds per syllable per text (median clean take): 0.198–0.269.
