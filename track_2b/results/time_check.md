# Time check: German speech against the English slot (exploratory, post-hoc)

Post-hoc, added after test outputs existed (protocol v2.24). Exploratory: no threshold was fixed in advance.

**Status: the check failed.** In 8 texts the median take says more than its text (Whisper finds at least 3 words after the text's last word), so its duration is not the text's; 4 texts are outside 0.10–0.40 s per syllable; 56 takes are clipped. The seconds below are reported as measured, but they are not valid as the spoken length of the texts, and the comparison of (a) with (c) is not a result.

- Date: 2026-10-13 09:36 UTC; git commit b6813dd17098846cdf7cec150ac0d914ac52df24
- Texts: step 4 test, run `hpc_8b_step4_test` (Apertus 1.5 8B, BF16; vLLM on the cluster, its endpoint in `results/step4_test.md`), German, syllable budget, generation seed 0
- TTS engine: Chatterbox multilingual (chatterbox-tts 0.1.7, MIT; weights ResembleAI/chatterbox @ 5bb1f6e, MIT); voice: the model's built-in default voice (conds.pt); no reference audio, no cloning
- TTS settings: language_id=de, exaggeration=0.5, cfg_weight=0.5, temperature=0.8, repetition_penalty=2.0, min_p=0.05, top_p=1.0, sample_rate=24000, versions=chatterbox-tts 0.1.7, torch 2.6.0+cu124, torchaudio 2.6.0+cu124, transformers 5.2.0, resemble-perth 1.0.1, numpy 1.26.4; NVIDIA H100 80GB HBM3, one job, 607 s wall time; endpoint: none (local inference)
- TTS seeds: [0, 1, 2] (take k uses seed k); 3 takes per text, duration = the median take
- English slot: the FLEURS recording named in `data/fleurs_de_test.jsonl` (google/fleurs, CC BY 4.0), trimmed like the speech: 16 kHz, `librosa.effects.trim(top_db=30, frame 2048, hop 512)`; sources whose English recording is flagged noisy are skipped
- Fit: speech within ±10 % of the English slot. Syllables: eSpeak NG text-to-speech: 1.52.0
- n: 22 of the sheet's 25 sources (3 skipped as noisy: 1710, 1936, 1972); 47 distinct texts × 3 takes

## Fit in seconds

| System | Fits the English slot | Median speech ÷ slot | Range |
|---|---|---:|---|
| (a) plain translation | 6/22 (27 %) | 0.87 | 0.55–1.69 |
| (c) ours | 6/22 (27 %) | 0.79 | 0.47–1.60 |

Paired, per source: (c) fits and (a) does not in 2, the reverse in 2; exact McNemar p = 1.000. In 5 sources (c) kept (a)'s text, so both read the same audio. Not a result: see the status above.

## Does the speech say its text, and only that?

Whisper small (openai-whisper 20250625, MIT; German, temperature 0; `scripts/asr_whisper.py`) transcribed every take (`results/time_check/asr.jsonl`). A take *says more than its text* when at least 3 transcribed words follow the last word it shares with the text (difflib matching blocks). Diagnosis only, decided after the speech was heard.

| Texts | n | Takes that say more | Texts whose median take says more |
|---|---:|---:|---:|
| (a) on the timed sources | 22 | 10/66 | 2/22 |
| (c) on the timed sources | 22 | 17/66 | 5/22 |
| demo texts | 8 | 7/24 | 2/8 |

Sources with a median take that says more, for (a) or (c): 5 of 22 (1737, 1820, 1871, 1908, 1925).

## Do syllables predict seconds?

- German speech, 39 distinct texts: r = 0.67; 0.197 s per syllable overall; least squares: 0.095 s per syllable + 4.04 s.
- English FLEURS speakers, 22 recordings: r = 0.90; 0.260 s per syllable.
- Takes of the same text differ by a median of 15 % of its duration (max − min over 3 takes; largest 106 %).

## Per source

| Source | English slot (s) | (a) s | (c) s | (a) fits | (c) fits |
|---|---:|---:|---:|---|---|
| 1682 | 14.46 | 10.98 | 10.46 | no | no |
| 1699 | 8.64 | 9.25 | 6.14 | yes | no |
| 1712 | 15.10 | 8.35 | 8.35 | no | no |
| 1733 | 16.54 | 12.99 | 10.43 | no | no |
| 1737 | 6.24 | 5.50 | 10.00\* | no | no |
| 1773 | 10.62 | 7.71 | 7.71 | no | no |
| 1790 | 11.55 | 10.59 | 8.32 | yes | no |
| 1794 | 8.10 | 8.83 | 8.83 | yes | yes |
| 1806 | 9.25 | 8.74 | 8.93 | yes | yes |
| 1817 | 4.19 | 3.33 | 4.10 | no | yes |
| 1820 | 7.97 | 13.46 | 7.02\* | no | no |
| 1831 | 9.89 | 7.78 | 7.21 | no | no |
| 1846 | 10.91 | 7.90 | 8.45 | no | no |
| 1861 | 7.30 | 6.02 | 6.02 | no | no |
| 1871 | 6.27 | 5.82\* | 5.82\* | yes | yes |
| 1879 | 5.17 | 4.93 | 4.93 | yes | yes |
| 1908 | 6.40 | 9.04\* | 6.88\* | no | yes |
| 1912 | 10.33 | 6.21 | 4.90 | no | no |
| 1922 | 8.42 | 7.49 | 6.66 | no | no |
| 1925 | 9.97 | 8.51 | 5.88\* | no | no |
| 1962 | 8.58 | 6.69 | 6.69 | no | no |
| 1980 | 7.92 | 7.04 | 6.91 | no | no |

\*: the median take says more than its text.

## Demo lines

Drawn by the rule in `results/time_check/selection.json`: pool: step 4 test sources (German, syllable budget, seed 0) not on the native-speaker sheet, English recording not noisy, both outputs usable; fit: (a) misses, (c) fits, (c) kept vs the reference by both NLI models; miss: (c) not kept plain (the loop ran) and misses; each drawn with random.Random(0).sample from the eligible ids in numeric order. Eligible: 77 fit, 59 miss, of 211 sources.

| Source | Kind | English slot (s) | (a) s | (c) s | Figure |
|---|---|---:|---:|---:|---|
| 1891 | fit | 14.50 | 4.86 | 4.32 | not drawn (the check failed) |
| 1903 | fit | 8.38 | 7.58 | 7.04 | not drawn (the check failed) |
| 1679 | fit | 3.17 | 4.19 | 6.68 | not drawn (the check failed) |
| 2002 | loop missed | 5.50 | 7.01 | 4.93 | not drawn (the check failed) |

## Checks

- Files: 167 (`results/time_check/manifest.csv`, with SHA-256 and licence; the audio stays in `audio/`, git-ignored). None empty or silent (the trim would fail).
- Peak of the speech before 16-bit writing: max 1.072; seconds per syllable per text: 0.147–0.588.
- Problems: 56 of 141 takes peaked above full scale before 16-bit writing (max 1.072), so their peaks are clipped; samples at full scale: at most 0.005 % of a take; 4 texts outside 0.10–0.40 s per syllable (median take): 7ab93ad3d331 0.405, 9d5131600c34 0.588, a1e04404ebd4 0.514, f482aa1d27d1 0.449
