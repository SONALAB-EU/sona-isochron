# Voice-calibrated syllable budgets: German speech against the English slot (exploratory, post-hoc)

Post-hoc, added after test outputs existed; planned before generation (protocol v2.30), after the Qwen3-TTS time check showed (c) running short (`results/time_check_qwen.md`).

**Status: every check of the audio passed.** 1 text(s) short of 3 clean takes, left out with their source(s): 1827.

- Date: 2026-10-13 11:22 UTC; git commit 911b7ceaf55aabc30dccbf066ac3f9e3a7a56e0d
- Voice rate: 288.576 s ÷ 1249 syllables = 0.23105 s per syllable, from 30 German dev plain translations (`results/time_check/calibrated/rate.json`); dev only, never test lines.
- Budget: round half up (English slot ÷ rate) syllables, ±10 % (14–90 syllables). Step 4's (c) otherwise unchanged; (a) reused from `hpc_8b_step4_test`, (b) not run.
- Generation: run `hpc_8b_step4_test_calibrated`, apertus-v1.5-8b-bf16, BF16, endpoint http://127.0.0.1:38081/v1 (vLLM on the cluster), seed 0, git commit bda317ce5d52591999e4c20b3564e2432ac90b9f (synced copy, recorded by hpc/sync.sh).
- Sources: 100 test sources (dev: random.Random(0).sample of 30 German dev sources whose (a) at seed 0 is usable; test: random.Random(0).sample of 100 German test sources, English recording not noisy, not on the native-speaker sheet, (a) at seed 0 usable; both from ids in numeric order).
- TTS: Qwen3-TTS: Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice @ 0c0e305 (Apache-2.0), qwen-tts 0.1.1 (Apache-2.0); preset voice Aiden; settings as in v2.28 (temperature 0.9, top_k 50, top_p 1.0, repetition penalty 1.05); round r seeds torch with r; 3 clean takes, at most 10 rounds; Whisper rule chars10 (transcript at most 10 % longer, spaces, punctuation and case removed); float WAV; the median clean take. Jobs: dev 121 s, test 373 s wall time on NVIDIA H100 80GB HBM3. Syllables: eSpeak NG text-to-speech: 1.52.0.
- n: 99 sources with 3 clean takes for both (a) and (c)

## Fit in seconds

| System | Fits the English slot | Too short | Too long | Median speech ÷ slot | Takes rejected |
|---|---|---:|---:|---:|---:|
| (a) plain translation | 25/99 (25 %) | 23 | 51 | 1.10 | 17/315 |
| (c) ours, calibrated budget | 47/99 (47 %) | 28 | 24 | 0.98 | 18/316 |

Paired: (c) fits and (a) does not in 22, the reverse in 0; exact McNemar p = 4.8e-07. (c) kept (a) in 59 sources.

(c) hits its calibrated syllable budget (±10 %) in 61/99; of those, 40 also fit the English slot in seconds.

Seconds per syllable of the speech (median clean take): 0.179–0.321.

Per source: `results/time_check/calibrated/durations.csv`; files, SHA-256 and licences: `results/time_check/calibrated/manifest.csv` (audio in the git-ignored `audio/`).
