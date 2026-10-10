# Status, 2026-10-10

**DONE, not blocked.** Phase 2 steps 1–6 are finished and committed. Nothing was pushed.

- **Recommendation for the full runs: prompt v1 with the repair loop.** This comes from an exploratory pilot;
  the details and caveats are in `results/phase2_pilot.md`.
- Both llama-server instances are stopped, and ports 8080 and 8081 are closed.
- Provenance:
  - Apertus 1.5 8B as a Q4_K_M GGUF on llama.cpp b11429.
  - Judge: Qwen3-8B, Q4_K_M.
  - TTS: none. Seed 0. n = 30 German dev sentences × 2 levels.
  - The endpoints and commits are in the report header.

## Pilot result (both levels pooled)

| Variant | Repair loop | Fit ±10 % | Fact recall | Fit & complete | Time / output |
|---------|-------------|----------:|------------:|---------------:|--------------:|
| v1  | without | 33.3 | 59.9 | 18.3 [8.3, 28.3] | 6.2 s |
| v1  | with    | 75.0 | 84.7 | **50.0 [38.3, 61.7]** | 15.6 s |
| v2a | without | 18.3 | 42.9 | 15.0 [5.0, 26.7] | 9.2 s |
| v2a | with    | 65.0 | 71.7 | 41.7 [28.3, 55.0] | 21.9 s |
| v2b | without | 21.7 | 53.6 | 10.0 [1.7, 20.0] | 5.2 s |
| v2b | with    | 60.0 | 85.5 | 41.7 [30.0, 53.3] | 17.0 s |
| v2c | without | 8.3 | 48.4 | 6.7 [0.0, 15.0] | 5.4 s |
| v2c | with    | 63.3 | 91.1 | 48.3 [35.0, 63.3] | 16.6 s |

- Figures are in %, with 95 % bootstrap intervals over sentences.
- Fact recall and fit & complete come from the Qwen3-8B judge, which is lenient, so read them as upper
  bounds.
- The judge's added-fact rate is 0 to 1.7 %, but in effect it is not measured (see the caveats).

## What ran

1. **Judge validation and selection.** Qwen3-8B ran on port 8081 with the Apertus server stopped.
   - Judge prompt v1 failed identical and paraphrased pairs: 50 % and 40 %.
   - I split the control suite so that no prompt is tuned on its validation data: tune on half A, choose
     on held-out half B (protocol v2.7). This was committed before any v2 result.
   - v2 also shows the original sentence, but it still failed paraphrases on half A (30 %).
   - So I added a per-fact judge, `perfact_v3`: one one-word call per fact, plus one call for added
     information. It scored 95 % on half A, then 91 % on half B against 69 % for v1, so it judges the pilot.
2. **Pilot judging.** 4 runs × 60 items × 2 conditions = 480 verdicts, none invalid.
3. **Report.** `results/phase2_pilot.md` has the summary, the recommendation and the caveats, then three
   tables: both levels, level 90 and level 80.
4. **Verification by three independent agents.**
   - One recomputed all 288 table cells from the raw files: all identical.
   - One audited integrity. No judge information reached generation. Seeds, rounds and selection are
     correct, and all 480 verdicts re-derive from the cached answers.
   - One audited the judge, which is lenient (see the caveats).
5. **Protocol v2.8:** the pilot result, its caveats and the open items for the full runs.

## Decisions I made without asking you

All are recorded in `docs/eval_protocol.md` (changelog v2.6 to v2.8).

- **First pilot generation superseded.** It reused the item seed in every round, so it was superseded before
  any judging. It was re-generated with one seed per round (item seed + 1000 × round), and retries are
  logged.
- **Judge prompt choice.** The judge prompt is chosen with the half-A / half-B rule, and `perfact_v3` was added
  as a candidate during tuning on half A.
- **Success measure and recommendation rule.** Both were fixed in code before any pilot judge output.
  - The measure is "fit & complete": the output fits, and the judge keeps every fact and finds nothing
    added.
  - The rule recommends the highest rate. Near-ties (overlapping 95 % intervals) are broken by time.
- **Applying the rule to the both-levels table.** The rule names no table; this table was already the
  report's first when the rule was written.
  - Level 90 alone gives the same pick.
  - At level 80 alone, the tie-break would pick v2b without the loop (13.3 %). That pick is degenerate,
    because at n = 30 almost every interval overlaps.

## Caveats

- **Small, exploratory sample.** 30 sentences and one seed, so the intervals are wide. With the loop, the four
  variants are within noise of each other; v1 leads v2c by one output in 60.
- **The judge is lenient.**
  - An LLM audit (not a native speaker) agreed with it on "complete" in only 17 of 24 outputs. Every
    disagreement was the judge passing an output that loses a qualifier, a hedge, a name or a verb.
  - It also misses insertions. It flagged one addition in 453 answered outputs, yet a targeted screen found
    clear ones.
- **English outputs count as fits.** Three outputs with the loop (sentence 1525) are in English and are counted
  as fits, because the loop has no language check. None is fit & complete.
- **Server log endings.** Both server logs end with a Metal `GGML_ASSERT` backtrace. In both, it comes after
  "all slots are idle" and "Received second interrupt" (my shutdown), so no request was affected.

## Next steps (your call)

1. **Main system.** Confirm v1 with the loop. Drop v2a, and keep v2c with the loop as a second arm only if
   compute allows.
2. **Language check.** Add the identifier in `src/isochron/langid.py` to the repair loop.
3. **Judge for the full runs.** The protocol names Qwen3-14B on the HPC. Validate it on halves A and B, plus
   new qualifier-level controls. Also plan the native-speaker check of 50 German lines.
4. **Near-ties.** Test them on paired differences instead of overlapping intervals.
5. **Full runs, on the HPC.** Step 2 alone on German test, at 4 levels × 3 seeds, is 4,164 outputs. That is
   about 18 h on this M3. This is an estimate from the pilot's mean; levels 70 and 60 were not piloted.

## Where things are

- **Report:** `results/phase2_pilot.md`.
  - Its hand-written summary is `results/phase2_pilot_notes.md`.
  - To regenerate it from `track_2b/`:

    ```
    uv run --no-sync python -m isochron.pilot_report results/raw/20261009T155640Z_pilot_v1_de_dev results/raw/20261009T161226Z_pilot_v2a_de_dev results/raw/20261009T163426Z_pilot_v2b_de_dev results/raw/20261009T165135Z_pilot_v2c_de_dev --notes results/phase2_pilot_notes.md
    ```
- **Pilot runs** (git-ignored): the four directories above, each with `items.jsonl`, `judge.jsonl`,
  `config.json` and `judge_config.json`.
  - The superseded runs are `…T151900Z_pilot_v1_de_dev` and `…T153417Z_pilot_v2a_de_dev`. They were never
    judged.
- **Judge validation:** `results/judge_validation_*.md` and `results/judge_tuning_*.md`.
- **Error analysis:** `results/gonogo_error_analysis.md`.
- **Logs** (git-ignored): server and judge logs are in `results/raw/logs/`.
- **Verification scripts:** only in the session scratchpad, not in the repository.
- **Commits** since the judge work: `d09f9af`, `c75706a`, `0936933`, `b3ca9b7`, `0fc2442`, and the commit that
  adds this file.
