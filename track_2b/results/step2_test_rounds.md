# Step 2 on test, round by round (from the logged runs)

- Date: 2026-10-12 10:47 UTC
- Git commit (analysis): 99781834a7980c567d01148bc267ede31670f356; runs: `hpc_8b_step2_de_test` (68492f2 (synced copy, recorded by hpc/sync.sh)), `hpc_8b_step2_fr_test` (68492f2 (synced copy, recorded by hpc/sync.sh))
- Model: apertus-v1.5-8b-bf16, quantisation BF16, backend vLLM 0.23.1rc1.dev1029+ga601a9d99; endpoint de http://127.0.0.1:38657/v1, fr http://127.0.0.1:51465/v1
- Judge (evaluation only): qwen3-14b-bf16 (BF16), temperature 0, seed 0
- Items: de test: 347 sentences × levels [90, 80, 70, 60] × seeds [0, 1, 2]; fr test: 332 sentences × levels [90, 80, 70, 60] × seeds [0, 1, 2]; TTS: none
- No new generation or judging: every number comes from items.jsonl and judge.jsonl of the runs.

"After round k": the loop's best candidate after rounds 0 to k, the output if the method stopped there.
Fit & complete gives low and high values where that candidate had no judge verdict (see
`isochron.rounds`). Round 2 equals the reports' "with the loop". The baseline is the reports'
"without the loop" (the closest round-0 candidate). Accepted rate: the share of the items open before
that round that the round accepted, by the loop's own rule.

## DE

| Level | Items | Fit: baseline | Fit after 0 / 1 / 2 (%) | Fit & complete: baseline | Fit & complete after 0 / 1 / 2 (%) | Accepted rate, rounds 0 / 1 / 2 (%) | Open after round 2 | Third round, estimated gain (points) |
|------:|------:|-----:|------------------------|-----:|------------------------------------|-----------------------------------|------------------:|-----------------------------------:|
| 90 % | 1041 | 11.7 | 11.1 / 75.0 / 81.6 | 8.5 | 8.3 / 59.9–60.6 / 65.1 | 10.4 / 70.7 / 26.0 | 202 | +3.3 to +3.8 |
| 80 % | 1041 | 26.7 | 24.7 / 54.2 / 64.8 | 13.0 | 12.9 / 35.7–36.2 / 41.5 | 21.2 / 40.4 / 24.1 | 371 | +4.0 to +4.4 |
| 70 % | 1041 | 44.5 | 40.2 / 49.1 / 57.3 | 16.1 | 15.6 / 23.2–23.8 / 26.3 | 31.0 / 23.1 / 17.0 | 458 | +2.1 to +2.6 |
| 60 % | 1041 | 56.8 | 50.2 / 47.0 / 55.2 | 19.1 | 18.1 / 18.5–19.2 / 20.7 | 35.3 / 11.6 / 16.9 | 495 | +1.3 to +1.8 |
| all | 4164 | 34.9 | 31.6 / 56.3 / 64.7 | 14.2 | 13.7 / 34.3–35.0 / 38.4 | 24.5 / 39.3 / 20.1 | 1526 | +2.8 to +3.3 |

## FR

| Level | Items | Fit: baseline | Fit after 0 / 1 / 2 (%) | Fit & complete: baseline | Fit & complete after 0 / 1 / 2 (%) | Accepted rate, rounds 0 / 1 / 2 (%) | Open after round 2 | Third round, estimated gain (points) |
|------:|------:|-----:|------------------------|-----:|------------------------------------|-----------------------------------|------------------:|-----------------------------------:|
| 90 % | 996 | 9.9 | 9.5 / 73.6 / 81.6 | 6.5 | 6.3 / 61.4–61.8 / 68.3 | 9.0 / 70.0 / 30.9 | 188 | +4.4 to +4.7 |
| 80 % | 996 | 25.9 | 23.9 / 56.3 / 65.9 | 14.6 | 14.2 / 41.5–41.8 / 47.5 | 21.6 / 43.5 / 22.2 | 343 | +4.5 to +4.7 |
| 70 % | 996 | 46.6 | 43.1 / 52.1 / 63.4 | 21.7 | 20.9 / 29.7–30.1 / 36.1 | 35.6 / 23.6 / 23.1 | 377 | +4.6 to +4.9 |
| 60 % | 996 | 55.1 | 49.9 / 50.5 / 59.6 | 19.3 | 19.3 / 21.9–22.2 / 24.7 | 38.4 / 15.8 / 19.7 | 415 | +2.0 to +2.3 |
| all | 3984 | 34.4 | 31.6 / 58.1 / 67.6 | 15.5 | 15.2 / 38.6–39.0 / 44.2 | 26.2 / 41.5 / 23.1 | 1323 | +4.0 to +4.2 |

The third-round column is an estimate, not a measurement. It assumes round 3 turns open items into
fit & complete outputs at round 2's rate. Where the loop's acceptance rate fell from round 1 to 2, a
third round would likely add less.
