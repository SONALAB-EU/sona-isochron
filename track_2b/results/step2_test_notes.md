<!-- Hand-written summary section of results/step2_test.md, inserted by `python -m isochron.step2_report RUN_DIR... --notes results/step2_test_notes.md`. Date, commits, model, endpoint, TTS, seeds and n are in that report's header. -->

## Summary

These are the final numbers for FLEURS German test: 347 sentences × levels 90, 80, 70 and 60 % × seeds 0, 1
and 2, so 4,164 outputs per condition.
- Apertus 1.5 8B ran in BF16 (the official weights) on vLLM, on one H100. The judge, Qwen3-14B BF16, was
  used for evaluation only.
- Both conditions come from the same run: "without the loop" is the closest round-0 candidate.
- **French: pending.** Job 2636593 has waited for a free H100 since 12:42 UTC. This report will be
  generated again with both languages.

**German, pooled over the four levels:**
- **The repair loop helps.**
  - Fit rises from 34.9 % to 64.7 % (+29.8 points [27.2, 32.4], paired).
  - Fit & complete rises from 14.2 % to 38.4 % (+24.3 points [22.2, 26.3]).
  - Fact recall rises from 59.9 % to 78.0 % (+18.0 points [16.0, 20.1]).
- **The gain shrinks as the target tightens.** Fit & complete rises by:

  | Level | Gain in points |
  |------:|----------------|
  | 90 % | +56.7 [52.7, 60.5] |
  | 80 % | +28.5 [24.9, 32.2] |
  | 70 % | +10.2 [7.7, 12.8] |
  | 60 % | +1.6 [−0.6, +3.8], which cannot be told from zero |

- **At 60 % the loop does not improve fit** (−1.5 points [−5.6, +2.5]).
  - When no candidate both fits and keeps the meaning, the loop keeps the meaning. NLI kept rises from
    52 % to 96 %.
  - So the outputs run long: achieved ÷ target is 1.08.
- **Without the loop, Apertus over-shortens:** achieved ÷ target is 0.83 overall, and 0.71 at level 90.
  With the loop it is 1.05.
- **With the loop, misses run long, and some outputs are the input unchanged.** This is analysis of the
  same outputs, not a new metric.
  - Misses that are too long outnumber those too short at every level. At 60 %, 321 are too long and 145
    too short, of 1,041.
  - The final output is the input unchanged in this share of items:

    | Level | Unchanged input |
    |------:|----------------:|
    | 90 % | 9.4 % |
    | 80 % | 4.7 % |
    | 70 % | 3.0 % |
    | 60 % | 2.0 % |

  - At 90 %, an unchanged input is about 1.11 × the target, just outside the ±10 % band.
- **Clean runs.**
  - No output is in the wrong language, in either condition.
  - Round 0 left 28 items without a usable answer. With the loop there are none, after 33 retries.
  - None of the 8,328 judge verdicts is invalid.
- **Added facts.** The added-fact rate is about 0 % in both conditions. The judge caught 16 of 20
  inserted facts on the controls, so this means few added facts, not none.
- **Cost.** With 16 items in flight on one H100, an output takes 10.5 s with the loop (every round and
  check) and 0.7 s for round 0. The loop adds 1.21 rounds on average.

**Caveats.**
- Fact recall and fit & complete are upper bounds. The judge misses half of the lost qualifiers on the
  hard controls (7 of 14), and the NLI misses most of them (3 of 14).
- Syllables stand in for spoken time; no speech was synthesised.
- Outputs are not checked for grammar.
