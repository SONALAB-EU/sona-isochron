# Too long and not too long (post-hoc)

Post-hoc, added after test outputs existed (protocol v2.36). Running long can overlap the next speech segment; running short is tolerable. The pre-registered fit (within ±10 %) stays the main metric.

- Date: 2026-10-13 15:57 UTC; git commit ded97c43a9da49e1be322c08d89c301ca3a8dfc9
- Step 4: `results/step4_test_lengths.csv` (FLEURS test; Apertus 1.5 8B, BF16, vLLM on the cluster, endpoints in `results/step4_test.md`; seeds 0, 1, 2; 347 German and 332 French sentences). TTS: none for step 4.
- Too long: a usable output over 1.10 × the budget; not too long: a usable output at most 1.10 × the budget; a missing or wrong-language output is neither. Shares of all outputs, in %, with 95 % bootstrap intervals over sentences (10,000 resamples, seed 0); paired differences in points.
- Timing tests: Qwen3-TTS (voice Aiden), seconds against the English slot (`results/time_check_qwen.md`, `results/time_check_calibrated.md`).

## Step 4

### EN → DE, characters: 347 sentences × seeds

| System | Too long | Not too long | Neither (missing or wrong language) |
|---|---|---|---:|
| (a) plain | 71.4 [67.1, 75.6] | 28.3 [24.1, 32.6] | 3 of 1041 |
| (b) one step | 1.9 [1.1, 2.9] | 97.5 [96.3, 98.6] | 6 of 1041 |
| (c) ours | 13.8 [11.3, 16.4] | 85.9 [83.2, 88.4] | 3 of 1041 |

| Paired (post-hoc) | Too long | Not too long |
|---|---|---|
| (c) − (a) | −57.5 [−61.7, −53.4] | +57.5 [+53.4, +61.7] |
| (c) − (b) | +11.9 [+9.3, +14.6] | −11.6 [−14.4, −8.8] |

### EN → DE, syllables: 347 sentences × seeds

| System | Too long | Not too long | Neither (missing or wrong language) |
|---|---|---|---:|
| (a) plain | 79.1 [74.9, 83.0] | 20.7 [16.8, 24.8] | 3 of 1041 |
| (b) one step | 14.8 [11.9, 17.9] | 84.9 [81.8, 87.8] | 3 of 1041 |
| (c) ours | 20.4 [17.4, 23.3] | 79.3 [76.2, 82.3] | 4 of 1041 |

| Paired (post-hoc) | Too long | Not too long |
|---|---|---|
| (c) − (a) | −58.7 [−62.8, −54.5] | +58.6 [+54.4, +62.7] |
| (c) − (b) | +5.6 [+1.6, +9.5] | −5.7 [−9.6, −1.6] |

### EN → FR, characters: 332 sentences × seeds

| System | Too long | Not too long | Neither (missing or wrong language) |
|---|---|---|---:|
| (a) plain | 74.2 [69.7, 78.6] | 25.2 [20.9, 29.7] | 6 of 996 |
| (b) one step | 5.1 [3.3, 7.0] | 86.5 [83.6, 89.3] | 83 of 996 |
| (c) ours | 12.2 [9.9, 14.7] | 86.2 [83.6, 88.8] | 15 of 996 |

| Paired (post-hoc) | Too long | Not too long |
|---|---|---|
| (c) − (a) | −61.9 [−66.3, −57.4] | +61.0 [+56.5, +65.4] |
| (c) − (b) | +7.1 [+4.2, +9.9] | −0.3 [−4.0, +3.5] |

### EN → FR, syllables: 332 sentences × seeds

| System | Too long | Not too long | Neither (missing or wrong language) |
|---|---|---|---:|
| (a) plain | 20.5 [16.6, 24.7] | 78.9 [74.7, 82.8] | 6 of 996 |
| (b) one step | 1.4 [0.4, 2.7] | 96.3 [94.6, 97.8] | 23 of 996 |
| (c) ours | 4.1 [2.7, 5.7] | 95.2 [93.4, 96.8] | 7 of 996 |

| Paired (post-hoc) | Too long | Not too long |
|---|---|---|
| (c) − (a) | −16.4 [−19.9, −13.0] | +16.3 [+13.0, +19.8] |
| (c) − (b) | +2.7 [+0.9, +4.6] | −1.1 [−3.4, +1.3] |

## Timing tests

| Timing test | n | (a) too long | (c) too long | (a) not too long | (c) not too long | McNemar p, too long |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-TTS, syllable budget (21 sheet sources) | 21 | 7 | 4 | 14 | 17 | 0.38 |
| Qwen3-TTS, voice-calibrated budget (99 test sources) | 99 | 51 | 24 | 48 | 75 | 1.5e-08 |
