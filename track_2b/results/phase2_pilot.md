# Phase 2 pilot (exploratory): prompt variants with and without the repair loop

- Date: 2026-10-10 14:12 UTC
- Git commit (report): 9978737d4398df7af6f0e008d1c97f37add9e5f6; runs: `20261009T155640Z_pilot_v1_de_dev` (e97b7b7), `20261009T161226Z_pilot_v2a_de_dev` (e97b7b7), `20261009T163426Z_pilot_v2b_de_dev` (5039e29), `20261009T165135Z_pilot_v2c_de_dev` (5039e29); judge: c75706a (with uncommitted changes to tracked files)
- Model: apertus-v1.5-8b-text-q4_k_m, quantisation Q4_K_M, endpoint http://127.0.0.1:8080/v1, backend b11429-d81235049
- Generation: {"temperature": 0.7, "top_p": 0.95, "top_k": 0, "min_p": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}, "samplers": ["temperature", "top_p"]}
- Prompts: v1 `shorten_syllables_v1` (fe4fbfdd800d), v2a `shorten_facts_v2a` (4ca4f463cb89), v2b `shorten_words_v2b` (bb46e6fdd739), v2c `shorten_graded_v2c` (ca197339b4c9); repair `revise_v1` (ab0593b9716e), at most 2 rounds
- Loop checks: eSpeak NG text-to-speech: 1.52.0 and NLI MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, mps, float32, argmax label; language check in the loop: none (the run predates it); the loop never sees the judge
- Scoring: an output in the wrong language counts as a failure (py3langid 0.4.0, restricted to de/en/fr/it; wrong language = top label is another language with probability >= 0.9)
- Judge (evaluation only): qwen3-8b-q4_k_m (Q4_K_M), endpoint http://127.0.0.1:8081/v1, backend b11429-d81235049, temperature 0, seed 0, prompts judge_facts_v1 (80c765ed80de), judge_fact_v3 (5b74445c3470), judge_added_v3 (61d024e29891)
- Items: 30 sentences (random.Random(0).sample of 30 of the 97 German dev sentences outside the go/no-go 50, kept in file order; de dev), levels [90, 80], seeds [0], round seeds: item seed + 1000 × round (round 0 uses the item seed); TTS: none
- 95 % intervals: bootstrap over sentences, 10000 resamples, seed 0. Dev split: exploratory, not a decision.

<!-- Hand-written summary section of results/phase2_pilot.md, inserted by `python -m isochron.pilot_report RUN_DIR... --notes results/phase2_pilot_notes.md`. Date, commit, model, endpoint, TTS, seeds and n are in that report's header. -->

## Summary

Exploratory pilot: 30 German dev sentences outside the go/no-go 50, levels 90 % and 80 %, seed 0, Apertus
1.5 8B (Q4_K_M) on a local llama-server. Meaning is scored by the final judge (Qwen3-8B, per-fact prompt),
which the repair loop never sees. Figures are from the "Both levels" table unless a level is named.

**Decision (2026-10-10): prompt v1 with the repair loop is our method; v2a is dropped.**

**Re-scored on 2026-10-10 with the language check, which the loop gained after the pilot.**
- Three outputs with the loop are in English, all for sentence 1525: v1 at level 90, and v2b at both
  levels. They now count as failures, like missing outputs.
- Fit falls by one output in 60 for v1 with the loop, and by two for v2b with the loop.
- Fit & complete and the recommendation do not change: none of the three was complete.

- **The repair loop is what helps.** With it, prompt v1 fits 73 % of the time instead of 33 %. Fact recall
  rises from 60 % to 83 %, and fit & complete from 18 % to 50 %. The cost is about 2.5 times the time: 15.6 s
  per output instead of 6.2 s, with 1.08 extra rounds on average.
- **The v2 prompts do not help on their own.** Without the loop, all three fit less often than v1: v2a 18 %,
  v2b 22 % and v2c 8 %, against 33 %. v2a's facts-first answer is often not valid JSON: 16 of its 60 round-0
  answers are unusable.
- **With the loop, the four variants are within noise of each other.** Fit & complete is 42 to 50 %, and all
  four 95 % intervals overlap. v1 leads v2c by one output in 60 (30 against 29).
- **Without the loop, Apertus still over-shortens.** Achieved ÷ target is 0.64 to 0.82. With the loop it is
  1.03 to 1.07.

## Recommendation for the full runs

1. **Main system: prompt v1 with the repair loop** (now decided).
   - The rule was fixed in code before any judge output was seen: recommend the condition with the highest
     fit & complete rate, and break near-ties (overlapping 95 % intervals) by time per output.
   - The rule does not name a table. It is applied to the table pooled over both levels, which was already the
     report's first table when the rule was written.
   - There, v1 with the loop has the highest rate: 50.0 % [38.3, 61.7], at 15.6 s per output. Its near-ties
     are the three other variants with the loop, all slower (16.6 to 21.9 s). No condition without the loop
     comes close: the best upper bound is 28.3 %.
   - Level 90 alone gives the same pick: 66.7 % [50.0, 83.3].
   - Level 80 alone does not. v2a and v2c with the loop tie at 36.7 % [20.0, 53.3], and v1 with the loop has
     33.3 %. At n = 30, six other intervals overlap the top one, so the time tie-break would pick v2b
     without the loop (13.3 %, 4.7 s). That pick is degenerate: overlapping intervals are too loose a test
     of a near-tie at this n. A paired bootstrap of the difference is suggested for the full runs.
2. **Drop v2a** (now decided). It is the slowest (21.9 s), and it has the most unusable answers: 24 retries,
   and 6 outputs still missing after the loop.
3. **Language check: done.**
   - The loop now checks every candidate with py3langid, restricted to German, English, French and Italian.
     A candidate counts as the wrong language when another of these languages is the top label with
     probability ≥ 0.9.
   - A wrong-language candidate is ranked last, never accepted, and answered with "answer in German".
     Reports count a wrong-language output as a failure.
   - The check flags exactly the three English pilot outputs, and none of the 1,956 German FLEURS
     sentences (`results/language_check.md`).
4. **Use a stronger judge than this one for the final numbers.** It is now measured on hard controls
   (`data/judge_controls_de.jsonl`, `results/judge_validation_hard_v3_all.md`).
   - Qwen3-8B catches only 36 % of qualifier changes (5 of 14) and 62 % of modal changes (8 of 13). It
     catches all 13 number changes and 85 % of inserted facts.
   - It also fails 3 of 20 same-meaning edits (*erlernen* → *lernen*, *Skifahren* → *Skilaufen*, words →
     digits), which it does not call complete. For comparison, the NLI catches 21 % of the qualifier
     changes.
   - Every HPC job validates Qwen3-14B on the same controls before judging (`docs/hpc.md`); the
     native-speaker check of 50 German lines is still open.
5. **Compute.**
   - Step 2 alone on German test, at the protocol's 4 levels × 3 seeds, is 347 × 4 × 3 = 4,164 outputs:
     about 18 h on this Apple M3. That is an estimate from the pilot's mean at levels 90 and 80; levels 70
     and 60 were not piloted.
   - The HPC kit runs it in about 1–2 GPU-hours for 8B (an estimate; `docs/hpc.md`).

## Caveats

- **Exploratory and small:** 30 sentences and one seed, so the intervals are wide.
- **The judge is lenient.**
  - The hard controls above measure it. A careful reader (Claude, an LLM, not a native speaker) also
    audited 24 random pilot outputs and agreed with the judge on "complete" only 17 times.
    - In every disagreement the judge passed an output that loses a qualifier, a hedge, a name, a verb or
      a modality (*ein wenig*, *generell*, *könnten* → *gelten*, *Bitte* → *Forderung*).
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
  - "NLI kept" counts a missing or wrong-language output as not kept.
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
  - One recomputed all 288 table cells from the raw files: all identical, before the language re-score.
  - One audited the runs' integrity. No judge information reached generation; seeds, rounds and selection
    are correct; and all 480 verdicts re-derive from the cached answers.
  - One audited the judge (the caveat above).

## Tables

Fit, fact recall, added-fact rate and fit & complete are in %. Time is per output (one sentence at one level
and seed). Fit & complete = fits, and the judge keeps every fact and finds nothing added. An output in the
wrong language counts as a failure.

### Both levels (90 % and 80 %)

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 60 | 33.3 [20.0, 46.7] | 59.9 [48.2, 71.3] | 0.0 [0.0, 0.0] | 18.3 [8.3, 28.3] | 60 % | 0.82 | 0.00 | 0 | 6.2 | 2 | 0 | 0 |
| v1 | with | 60 | 73.3 [61.7, 85.0] | 83.4 [75.1, 91.1] | 0.0 [0.0, 0.0] | 50.0 [38.3, 61.7] | 95 % | 1.03 | 1.08 | 2 | 15.6 | 0 | 1 | 0 |
| v2a | without | 60 | 18.3 [8.3, 30.0] | 42.9 [30.6, 55.2] | 0.0 [0.0, 0.0] | 15.0 [5.0, 26.7] | 35 % | 0.77 | 0.00 | 0 | 9.2 | 16 | 0 | 0 |
| v2a | with | 60 | 65.0 [53.3, 76.7] | 71.7 [59.4, 82.6] | 0.0 [0.0, 0.0] | 41.7 [28.3, 55.0] | 85 % | 1.04 | 1.32 | 24 | 21.9 | 6 | 0 | 0 |
| v2b | without | 60 | 21.7 [11.7, 33.3] | 53.6 [41.5, 65.6] | 1.7 [0.0, 5.0] | 10.0 [1.7, 20.0] | 45 % | 0.79 | 0.00 | 0 | 5.2 | 0 | 0 | 0 |
| v2b | with | 60 | 56.7 [43.3, 70.0] | 83.7 [73.3, 92.4] | 0.0 [0.0, 0.0] | 41.7 [30.0, 53.3] | 93 % | 1.05 | 1.38 | 0 | 17.0 | 0 | 2 | 0 |
| v2c | without | 60 | 8.3 [1.7, 18.3] | 48.4 [36.4, 60.6] | 0.0 [0.0, 0.0] | 6.7 [0.0, 15.0] | 37 % | 0.64 | 0.00 | 0 | 5.4 | 3 | 0 | 0 |
| v2c | with | 60 | 63.3 [50.0, 76.7] | 91.1 [84.2, 96.7] | 0.0 [0.0, 0.0] | 48.3 [35.0, 63.3] | 98 % | 1.07 | 1.38 | 3 | 16.6 | 0 | 0 | 0 |

### Level 90 %

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 30 | 23.3 [10.0, 40.0] | 64.9 [50.3, 78.9] | 0.0 [0.0, 0.0] | 13.3 [3.3, 26.7] | 63 % | 0.78 | 0.00 | 0 | 6.3 | 1 | 0 | 0 |
| v1 | with | 30 | 80.0 [63.3, 93.3] | 91.3 [81.3, 98.7] | 0.0 [0.0, 0.0] | 66.7 [50.0, 83.3] | 93 % | 1.02 | 1.00 | 1 | 15.2 | 0 | 1 | 0 |
| v2a | without | 30 | 16.7 [3.3, 30.0] | 42.6 [27.6, 58.1] | 0.0 [0.0, 0.0] | 13.3 [3.3, 26.7] | 30 % | 0.73 | 0.00 | 0 | 9.2 | 11 | 0 | 0 |
| v2a | with | 30 | 66.7 [50.0, 83.3] | 77.6 [64.0, 89.5] | 0.0 [0.0, 0.0] | 46.7 [30.0, 63.3] | 87 % | 1.02 | 1.33 | 15 | 22.2 | 2 | 0 | 0 |
| v2b | without | 30 | 13.3 [3.3, 26.7] | 58.2 [43.4, 72.7] | 0.0 [0.0, 0.0] | 6.7 [0.0, 16.7] | 57 % | 0.77 | 0.00 | 0 | 5.6 | 0 | 0 | 0 |
| v2b | with | 30 | 70.0 [53.3, 86.7] | 89.7 [79.4, 98.1] | 0.0 [0.0, 0.0] | 56.7 [40.0, 73.3] | 90 % | 1.04 | 1.30 | 0 | 17.1 | 0 | 1 | 0 |
| v2c | without | 30 | 6.7 [0.0, 16.7] | 56.1 [42.7, 69.2] | 0.0 [0.0, 0.0] | 6.7 [0.0, 16.7] | 47 % | 0.64 | 0.00 | 0 | 5.7 | 0 | 0 | 0 |
| v2c | with | 30 | 73.3 [56.7, 90.0] | 95.7 [90.7, 99.3] | 0.0 [0.0, 0.0] | 60.0 [43.3, 76.7] | 97 % | 1.03 | 1.27 | 0 | 16.2 | 0 | 0 | 0 |

### Level 80 %

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 30 | 43.3 [26.7, 60.0] | 54.9 [40.5, 69.4] | 0.0 [0.0, 0.0] | 23.3 [10.0, 40.0] | 57 % | 0.85 | 0.00 | 0 | 6.1 | 1 | 0 | 0 |
| v1 | with | 30 | 66.7 [50.0, 83.3] | 75.6 [63.3, 86.9] | 0.0 [0.0, 0.0] | 33.3 [16.7, 50.0] | 97 % | 1.03 | 1.17 | 1 | 16.1 | 0 | 0 | 0 |
| v2a | without | 30 | 20.0 [6.7, 33.3] | 43.3 [28.3, 58.2] | 0.0 [0.0, 0.0] | 16.7 [3.3, 30.0] | 40 % | 0.80 | 0.00 | 0 | 9.2 | 5 | 0 | 0 |
| v2a | with | 30 | 63.3 [46.7, 80.0] | 65.9 [51.4, 79.3] | 0.0 [0.0, 0.0] | 36.7 [20.0, 53.3] | 83 % | 1.06 | 1.30 | 9 | 21.6 | 4 | 0 | 0 |
| v2b | without | 30 | 30.0 [13.3, 46.7] | 48.9 [34.2, 62.9] | 3.3 [0.0, 10.0] | 13.3 [3.3, 26.7] | 33 % | 0.81 | 0.00 | 0 | 4.7 | 0 | 0 | 0 |
| v2b | with | 30 | 43.3 [26.7, 60.0] | 77.7 [64.7, 89.1] | 0.0 [0.0, 0.0] | 26.7 [10.0, 43.3] | 97 % | 1.07 | 1.47 | 0 | 16.9 | 0 | 1 | 0 |
| v2c | without | 30 | 10.0 [0.0, 23.3] | 40.8 [27.5, 54.4] | 0.0 [0.0, 0.0] | 6.7 [0.0, 16.7] | 27 % | 0.64 | 0.00 | 0 | 5.1 | 3 | 0 | 0 |
| v2c | with | 30 | 53.3 [36.7, 70.0] | 86.5 [75.6, 95.4] | 0.0 [0.0, 0.0] | 36.7 [20.0, 53.3] | 100 % | 1.10 | 1.50 | 3 | 17.0 | 0 | 0 | 0 |
