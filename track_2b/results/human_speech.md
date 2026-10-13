# Human speech: syllables, characters and seconds (exploratory, post-hoc)

Post-hoc, added after test outputs existed (protocol v2.27, planned before computing). FLEURS test, read by people; no TTS.

- Date: 2026-10-13 10:24 UTC; git commit 2bea4c0d70b38b0d68126c270ff7bc99ced90f20
- Data: google/fleurs @ 70bb2e8 (CC BY 4.0), `en_us`, `de_de`, `fr_fr` test, the recording `data/fleurs_{de,fr}_test.jsonl` names per sentence; trimmed as `slot_s` (16 kHz, librosa.effects.trim top_db 30, frame 2048, hop 512). Re-measured from the audio: every duration equals the stored one.
- Syllables: eSpeak NG text-to-speech: 1.52.0; characters without spaces. Model, quantisation, endpoint, TTS: none (human recordings). Bootstrap: 10,000 resamples over sentences, seed 0.

## (a) Syllables and seconds, per language

Seconds are trimmed only at the ends, so pauses inside a sentence count: the rates are lower than Pellegrino et al.'s.

| Language | Recordings | r (syllables, seconds) | s per syllable | Syllables per s | Pellegrino | Rate ÷ EN, measured | Rate ÷ EN, budget |
|---|---:|---|---:|---:|---:|---:|---:|
| EN | 233 | 0.85 [0.80, 0.89] | 0.261 | 3.82 | 6.19 | 1.000 | 1.000 |
| DE | 310 | 0.77 [0.71, 0.83] | 0.231 | 4.33 | 5.97 | 1.131 | 0.964 |
| FR | 332 | 0.93 [0.90, 0.94] | 0.194 | 5.16 | 7.18 | 1.349 | 1.160 |

## (b) Does a ruler predict whether the human reading fits the English slot?

### EN → DE: 209 sentences with both recordings clean; the human reading fits the English slot in 43 (20.6 %)

| Ruler | Ruler fits | Agreement with the human fit (%) | Cohen's kappa | Pearson r, ratios | Spearman r, ratios |
|---|---:|---|---|---|---|
| syllables | 36/209 | 66.0 [59.8, 72.2] | −0.11 [−0.21, 0.01] | 0.29 [0.16, 0.43] | 0.38 [0.25, 0.49] |
| characters | 53/209 | 58.9 [52.2, 65.6] | −0.16 [−0.26, −0.05] | 0.30 [0.17, 0.43] | 0.38 [0.26, 0.50] |

Syllables − characters (paired): agreement +7.2 [+2.9, +12.0] points; kappa +0.05 [−0.04, +0.15]; Pearson r −0.01 [−0.09, +0.06].

### EN → FR: 221 sentences with both recordings clean; the human reading fits the English slot in 55 (24.9 %)

| Ruler | Ruler fits | Agreement with the human fit (%) | Cohen's kappa | Pearson r, ratios | Spearman r, ratios |
|---|---:|---|---|---|---|
| syllables | 113/221 | 50.2 [43.9, 57.0] | 0.02 [−0.10, 0.13] | 0.46 [0.36, 0.56] | 0.48 [0.38, 0.57] |
| characters | 54/221 | 61.5 [55.2, 67.9] | −0.04 [−0.16, 0.10] | 0.48 [0.38, 0.57] | 0.47 [0.36, 0.57] |

Syllables − characters (paired): agreement −11.3 [−21.3, −1.8] points; kappa +0.05 [−0.12, +0.21]; Pearson r −0.02 [−0.08, +0.05].
