# How much longer are German and French than English? (post-hoc, descriptive)

Post-hoc, added after test outputs existed (protocol v2.35).

- Date: 2026-10-13 15:56 UTC; git commit 2758adce7247b065f8e7a8f0a54e25cac9be45cf
- Data: FLEURS test (google/fleurs @ 70bb2e8, CC BY 4.0): the English source, the human reference translation and its reading; Apertus's plain translation (a) at generation seed 0 from the step 4 test runs (Apertus 1.5 8B, BF16, vLLM on the cluster; endpoints in `results/step4_test.md`). TTS: none.
- Lengths: characters without spaces, words, and syllables (eSpeak NG text-to-speech: 1.52.0). Duration: the human readings, trimmed as `slot_s` (16 kHz, librosa trim at 30 dB), where neither recording is flagged noisy.
- Ratio = target ÷ English per sentence. Median with a 95 % bootstrap interval (10,000 resamples over sentences, seed 0); shares with 95 % Wilson intervals.
- Context: W3C, "Text size in translation" (https://www.w3.org/International/articles/article-text-size), citing IBM's guidance that European-language translations of English text over 70 characters run to about 130 % of its length. The last rows of each table keep English sources over 70 characters (with spaces, as that guidance counts them).

## EN → DE: 347 sentences

| Text | n | Median ratio | Longer than the English | Longer by > 10 % |
|---|---:|---|---|---|
| characters: human reference | 347 | 1.18 [1.16, 1.20] | 95 % [92, 96] | 75 % [70, 79] |
| characters: plain translation (a) | 346 | 1.16 [1.15, 1.18] | 91 % [88, 94] | 72 % [67, 77] |
| words: human reference | 347 | 0.97 [0.96, 1.00] | 32 % [28, 37] | 16 % [13, 21] |
| words: plain translation (a) | 346 | 0.95 [0.94, 0.97] | 27 % [23, 32] | 11 % [8, 15] |
| syllables: human reference | 347 | 1.22 [1.18, 1.25] | 91 % [88, 94] | 74 % [70, 79] |
| syllables: plain translation (a) | 346 | 1.19 [1.18, 1.21] | 88 % [84, 91] | 71 % [66, 75] |
| seconds: human readings (recordings not noisy) | 209 | 0.98 [0.94, 1.07] | 47 % [41, 54] | 40 % [33, 46] |
| characters, English > 70 characters: human reference | 329 | 1.18 [1.16, 1.21] | 95 % [92, 97] | 75 % [70, 80] |
| characters, English > 70 characters: plain translation (a) | 328 | 1.17 [1.15, 1.19] | 92 % [89, 95] | 74 % [69, 79] |

## EN → FR: 332 sentences

| Text | n | Median ratio | Longer than the English | Longer by > 10 % |
|---|---:|---|---|---|
| characters: human reference | 332 | 1.18 [1.17, 1.20] | 92 % [89, 95] | 75 % [70, 80] |
| characters: plain translation (a) | 330 | 1.19 [1.18, 1.21] | 93 % [90, 95] | 74 % [69, 78] |
| words: human reference | 332 | 1.14 [1.12, 1.17] | 77 % [72, 81] | 61 % [55, 66] |
| words: plain translation (a) | 330 | 1.12 [1.11, 1.14] | 77 % [72, 81] | 57 % [52, 62] |
| syllables: human reference | 332 | 1.15 [1.12, 1.17] | 81 % [76, 85] | 61 % [55, 66] |
| syllables: plain translation (a) | 330 | 1.12 [1.11, 1.14] | 83 % [78, 86] | 59 % [53, 64] |
| seconds: human readings (recordings not noisy) | 221 | 0.85 [0.83, 0.90] | 27 % [22, 33] | 18 % [14, 24] |
| characters, English > 70 characters: human reference | 314 | 1.18 [1.16, 1.20] | 92 % [89, 95] | 75 % [70, 79] |
| characters, English > 70 characters: plain translation (a) | 312 | 1.19 [1.17, 1.21] | 94 % [90, 96] | 74 % [69, 78] |
