<!-- Hand-written summary section of results/step2_test.md, inserted by `python -m isochron.step2_report RUN_DIR... --notes results/step2_test_notes.md`. Date, commits, model, endpoint, TTS, seeds and n are in that report's header. -->

## Summary

These are the final numbers for FLEURS test, German and French: every sentence × levels 90, 80, 70 and
60 % × seeds 0, 1 and 2.
- German: 347 sentences, 4,164 outputs per condition. French: 332 sentences, 3,984 outputs.
- Apertus 1.5 8B ran in BF16 (the official weights) on vLLM, on one H100 per language. The judge,
  Qwen3-14B BF16, was used for evaluation only.
- Both conditions come from the same run: "without the loop" is the closest round-0 candidate.

**The repair loop helps in both languages.** Pooled over the four levels:

| Language | Fit, without → with | Fit & complete, without → with | Paired gain: fit | Paired gain: fit & complete |
|----------|--------------------:|-------------------------------:|-----------------:|----------------------------:|
| German | 34.9 % → 64.7 % | 14.2 % → 38.4 % | +29.8 points [27.2, 32.4] | +24.3 points [22.2, 26.3] |
| French | 34.4 % → 67.6 % | 15.5 % → 44.2 % | +33.2 points [30.6, 35.8] | +28.6 points [26.4, 30.9] |

- **Fact recall** rises from 59.9 % to 78.0 % in German and from 61.6 % to 80.2 % in French (+18.0 and
  +18.5 points).
- **The gain shrinks as the target tightens.** Fit & complete rises by:

  | Level | German | French |
  |------:|--------|--------|
  | 90 % | +56.7 | +61.7 |
  | 80 % | +28.5 | +32.9 |
  | 70 % | +10.2 | +14.5 |
  | 60 % | +1.6 [−0.6, +3.8] | +5.4 [3.2, 7.6] |

- **At 60 %, fit barely moves:** −1.5 points [−5.6, +2.5] in German and +4.5 [0.4, 8.6] in French.
  - When no candidate both fits and keeps the meaning, the loop keeps the meaning. NLI kept rises from
    52 % to 96 % (German) and from 56 % to 98 % (French).
- **Without the loop, Apertus over-shortens:** achieved ÷ target is 0.83 (German) and 0.82 (French), and
  0.71 at level 90 in both. With the loop it is 1.05 and 1.03.

**What goes wrong** (analysis of the same outputs, not a new metric):
- **Misses run long.** Too long outnumbers too short at every level in both languages. At 60 %: 321
  against 145 in German, and 243 against 158 in French.
- **Some outputs are the input unchanged.** At 90 %, an unchanged input is about 1.11 × the target, just
  outside the ±10 % band. Share of items by level:

  | Language | 90 % | 80 % | 70 % | 60 % |
  |----------|-----:|-----:|-----:|-----:|
  | German | 9.4 % | 4.7 % | 3.0 % | 2.0 % |
  | French | 4.2 % | 2.3 % | 0.9 % | 0.3 % |

- **French answers break JSON more often.**
  - Invalid JSON: 2.9 % of French rounds against 0.5 % of German rounds. Most French failures (215 of 253)
    are apostrophes escaped as `\'`, which strict JSON rejects.
  - So round 0 left 89 French items without a usable answer (German: 28). After the loop, 11 French items
    from 3 sentences still have none (German: 0). They count as failures.
  - A more lenient parser could recover these answers, but it would be tuned on dev before any use.

**Clean runs.**
- No output is in the wrong language, in either language or condition.
- None of the 16,296 judge verdicts is invalid.
- **Added facts.** The added-fact rate is about 0 % everywhere. The judge caught 16 of 20 inserted facts on
  the controls, so this means few added facts, not none.

**Cost.** With 16 items in flight on one H100, an output takes about 10 s with the loop (every round and
check) and 0.7 s for round 0. The loop adds 1.21 rounds on average in German and 1.17 in French.

**Caveats.**
- Fact recall and fit & complete are upper bounds. The judge misses half of the lost qualifiers on the
  hard controls (7 of 14), and the NLI misses most of them (3 of 14).
- The judge's hard controls are German only. French judging relies on the NLI suite (French: 95–100 % per
  control type).
- Syllables stand in for spoken time; no speech was synthesised.
- Outputs are not checked for grammar.
