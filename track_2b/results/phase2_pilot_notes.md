<!-- Hand-written summary section of results/phase2_pilot.md, inserted by `python -m isochron.pilot_report RUN_DIR... --notes results/phase2_pilot_notes.md`. Date, commit, model, endpoint, TTS, seeds and n are in that report's header. -->

## Summary

Exploratory pilot: 30 German dev sentences outside the go/no-go 50, levels 90 % and 80 %, seed 0, Apertus
1.5 8B (Q4_K_M) on a local llama-server. Meaning is scored by the final judge (Qwen3-8B, per-fact prompt),
which the repair loop never sees. Figures are from the "Both levels" table unless a level is named.

- **The repair loop is what helps.** With it, prompt v1 fits 75 % of the time instead of 33 %. Fact recall
  rises from 60 % to 85 %, and fit & complete from 18 % to 50 %. The cost is about 2.5 times the time: 15.6 s
  per output instead of 6.2 s, with 1.08 extra rounds on average.
- **The v2 prompts do not help on their own.** Without the loop, all three fit less often than v1: v2a 18 %,
  v2b 22 % and v2c 8 %, against 33 %. v2a's facts-first answer is often not valid JSON: 16 of its 60 round-0
  answers are unusable.
- **With the loop, the four variants are within noise of each other.** Fit & complete is 42 to 50 %, and all
  four 95 % intervals overlap. v1 leads v2c by one output in 60 (30 against 29).
- **Without the loop, Apertus still over-shortens.** Achieved ÷ target is 0.64 to 0.82. With the loop it is
  1.03 to 1.07.

## Recommendation for the full runs

1. **Main system: prompt v1 with the repair loop.**
   - The rule was fixed in code before any judge output was seen: recommend the condition with the highest
     fit & complete rate, and break near-ties (overlapping 95 % intervals) by time per output.
   - The rule does not name a table. I apply it to the table pooled over both levels, which was already the
     report's first table when the rule was written.
   - There, v1 with the loop has the highest rate: 50.0 % [38.3, 61.7], at 15.6 s per output. Its near-ties
     are the three other variants with the loop, all slower (16.6 to 21.9 s). No condition without the loop
     comes close: the best upper bound is 28.3 %.
   - Level 90 alone gives the same pick: 66.7 % [50.0, 83.3].
   - Level 80 alone does not. v2a and v2c with the loop tie at 36.7 % [20.0, 53.3], and v1 with the loop has
     33.3 %. At n = 30, six other intervals overlap the top one, so the time tie-break would pick v2b
     without the loop (13.3 %, 4.7 s). That pick is degenerate: overlapping intervals are too loose a test
     of a near-tie at this n. I suggest a paired bootstrap of the difference for the full runs.
2. **Drop v2a.** It is the slowest (21.9 s), and it has the most unusable answers: 24 retries, and 6 outputs
   still missing after the loop. Run v2c with the loop as a second arm only if compute allows. Its judge fact
   recall is the highest (91 %), but it fits less often (63 %), and its fit & complete is within noise of v1.
3. **Add the language check to the loop.** Three outputs with the loop for sentence 1525 are in English: v1
   at level 90, and v2b at both levels. They count as fits and as NLI kept, because neither the loop nor the
   judge checks the language. The identifier in `src/isochron/langid.py` is only used by the smoke-test
   checks. None of the three is fit & complete (the judge's recall is 0.40 to 0.73).
4. **Fix the judge before relying on any meaning figure from the full runs** (see the caveats).
   - It misses lost qualifiers and hedges, the most frequent loss in the go/no-go error analysis (80 % of
     dropped cases). It also misses insertions.
   - Options: the larger judge the protocol names for the HPC (Qwen3-14B), validated on the same half-A /
     half-B split plus new qualifier-level controls, and the native-speaker check of 50 German lines.
5. **Compute.** v1 with the loop took 15.6 s per output on this Apple M3 (16 GB).
   - Step 2 alone on German test, at the protocol's 4 levels × 3 seeds, is 347 × 4 × 3 = 4,164 outputs.
     That is about 18 h locally.
   - This is an estimate from the pilot's mean at levels 90 and 80. Levels 70 and 60 were not piloted and
     may need more rounds.
   - The HPC is the better place for the full runs.

## Caveats

- **Exploratory and small:** 30 sentences and one seed, so the intervals are wide.
- **The judge is lenient.**
  - It scored 91 % on held-out control pairs. But the control suite only deletes or inserts whole clauses,
    so it does not test the qualifier-level changes that dominate the pilot.
  - A careful reader (Claude, an LLM, not a native speaker) audited 24 random pilot outputs. It agreed with
    the judge on "complete" only 17 times.
    - In every disagreement the judge passed an output that loses a qualifier, a hedge, a name, a verb or a
      modality (*ein wenig*, *generell*, *könnten* → *gelten*, *Bitte* → *Forderung*).
    - Mean recall: 0.78 from the judge, 0.65 from the audit.
  - Its added-fact rate of about 0 % is not credible. It flagged an addition once in 453 answered outputs,
    and a targeted screen found clear insertions in fit outputs that it scored as complete.
  - So read fact recall and fit & complete as upper bounds, and treat added facts as unmeasured.
  - The misses occur in all four variants, so the audit cannot say whether the ranking holds.
  - Some stored fact lists are wrong, and each list is reused for every output of its sentence. In sentence
    1558, fact 5 is inverted. Facts in sentences 1533, 1550, 1594 and 1608 are badly extracted or vacuous.
- **How some columns are counted:**
  - "Avg. rounds" includes retries after an unusable answer. v2a's 1.32 includes 24 retries; it is 0.92
    without them.
  - "NLI kept" counts a missing output as not kept.
  - Time without the loop includes no NLI time (about 0.6 s per output).
- **Judge provenance:** the judge's run records show commit `c75706a` with uncommitted changes. The only
  changed tracked file was `docs/eval_protocol.md` (documentation); the judge code was committed. All 480
  verdicts re-derive exactly from the cached answers.
- **Model:** Apertus runs as a community Q4_K_M GGUF of a community text-only conversion of the official
  weights (see `docs/local_llm.md`).

## Also in phase 2

- **Error analysis of the go/no-go outputs** (`results/gonogo_error_analysis.md`).
  - Apertus over-shortens: the median output is 0.87 of the target.
  - Dropped content is mostly qualifiers (80 % of cases), other meaning changes (53 %) and whole clauses
    (33 %). It is never numbers.
- **Judge validation and selection** (`results/judge_validation_*.md`, `results/judge_tuning_*.md`).
  - Judge v1 failed on identical and paraphrased pairs (50 % and 40 %).
  - The per-fact judge was chosen on held-out pairs: 91 % against 69 % for v1.
- **A first pilot generation was superseded before it was judged.** It used one seed for every round, so a
  repeated revision prompt was replayed byte for byte.
- **Checks:** three independent agents.
  - One recomputed all 288 table cells from the raw files: all identical.
  - One audited the runs' integrity. No judge information reached generation; seeds, rounds and selection
    are correct; and all 480 verdicts re-derive from the cached answers.
  - One audited the judge (the caveat above).
