# Step 4 on test: translation to a length budget

- Date: 2026-10-12 16:01 UTC
- Git commit (report): b755fad08b6a84756fd96e36f1a4cf7871e75262; runs: `hpc_8b_step4_test` (7b22d93 (synced copy, recorded by hpc/sync.sh)), `hpc_8b_step4_test_fr` (7b22d93 (synced copy, recorded by hpc/sync.sh))
- Model: apertus-v1.5-8b-bf16, quantisation BF16, backend vLLM 0.23.1rc1.dev1029+ga601a9d99; endpoint de http://127.0.0.1:46167/v1, fr http://127.0.0.1:41569/v1
- Generation: {"temperature": 0.7, "top_p": 0.95, "top_k": 0, "min_p": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}}; seeds [0, 1, 2] ((a), (b): item seed; (c): item seed + 1000 × round)
- Prompts: `translate_plain_v1` (5fe6dd58bf7e), `translate_budget_chars_v1` (e81efebd7d4f), `translate_budget_syllables_v1` (a3ffa4ea51a7), `shorten_chars_v1` (004890c41f25), `shorten_syllables_v1` (fe4fbfdd800d), `revise_chars_v1` (62a308e266ab), `revise_v1` (ab0593b9716e)
- Systems: (b) closest of 4 candidates in the budget's unit; (c) prompt v1 with the repair loop in the budget's unit; (a) kept if at most 1.10 × the budget
- Budgets: {"isometric": "chars", "isosyllabic": "syllables"}; syllable rates {"en": 6.19, "de": 5.97, "fr": 7.18, "it": 6.99}; length counter eSpeak NG text-to-speech: 1.52.0
- Meaning: NLI MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, mps, float32, argmax label; language check py3langid 0.4.0, restricted to de/en/fr/it; wrong language = top label is another language with probability >= 0.9
- Judge (evaluation only): qwen3-14b-bf16 (BF16), backend vLLM 0.23.1rc1.dev1029+ga601a9d99, temperature 0, seed 0, mode perfact_v3, facts listed from the English source; endpoint http://127.0.0.1:41631/v1, http://127.0.0.1:52035/v1
- Items: all sentences in file order; sentences {"de": 347, "fr": 332}; split test; TTS: none
- 95 % intervals: bootstrap over sentences, 10000 resamples, seed 0. Test split: final numbers.

<!-- Hand-written summary section of results/step4_test.md, inserted by `python -m isochron.step4_report RUN_DIR... --notes results/step4_test_notes.md`. Date, commits, model, endpoint, TTS, seeds and n are in that report's header. -->

## Summary

These are the final numbers for step 4 on FLEURS test.
- Every sentence, English → German (347) and English → French (332), × seeds 0, 1 and 2, under both
  budgets, for all three systems. That is 1,041 German and 996 French outputs per system and budget.
- Everything was frozen as it ran on dev before any test output existed (protocol v2.17, commit
  7b22d93): the prompts (hashes in the header), closest-of-4 selection, translate-then-shorten with the
  repair loop, and the keep-plain rule.
- Apertus 1.5 8B ran in BF16 on vLLM, on one H100 per language. The judge, Qwen3-14B BF16, was used for
  evaluation only.
- Dev (`results/hpc_8b_step4_dev.md`) is exploratory.

Fit and fit & complete in %, for (a) plain translation / (b) one step to the budget / (c) translate,
then shorten (ours). Fit & complete comes from the judge, and is an upper bound (below):

| Direction, budget | Fit ±10 % | Fit & complete | (c) − (b), paired (post-hoc, added after test outputs existed), in points: fit; fit & complete |
|-------------------|-----------|----------------|---------------------------------------------------|
| EN → DE, characters | 27.2 / 59.4 / **80.2** | 26.8 / 53.7 / **70.5** | +20.8 [15.8, 25.9]; +16.8 [11.4, 22.2] |
| EN → DE, syllables | 19.6 / **71.6** / **70.3** | 19.5 / **61.5** / 56.9 | −1.2 [−6.0, +3.6]; −4.6 [−9.4, +0.2] |
| EN → FR, characters | 23.9 / 59.8 / **77.3** | 23.5 / 53.0 / **68.6** | +17.5 [12.2, 22.9]; +15.6 [10.0, 21.3] |
| EN → FR, syllables | 55.6 / 44.7 / **69.9** | 54.9 / 41.9 / **68.1** | +25.2 [20.0, 30.3]; +26.2 [20.9, 31.3] |

- **Translating first and then shortening fits most often in three of the four settings.** It beats one
  step to the budget by 17 to 25 points of fit.
- **German with the syllable budget is a tie on fit** (−1.2 points [−6.0, +3.6], paired, post-hoc, added after test outputs existed).
  There the two meaning checks disagree:
  - the judge gives one step 4.6 points more fit & complete (interval [−9.4, +0.2]);
  - the NLI against the reference finds that (c) keeps the meaning more often (+4.8 points [+1.1, +8.5]).
- **Meaning, by the main check** (NLI against the human reference):
  - (c) keeps it as often as plain translation: +1.0 to +2.0 points. In the paired intervals (post-hoc, added after test outputs existed),
    only French with syllables excludes 0 (+1.8 [+0.3, +3.5]).
  - One step to the budget keeps it less often: (c) − (b) is +4.8 to +11.0 points in all four settings.
- **Plain translation rarely meets the budget,** except French with syllables (55.6 %).
  - That budget is 1.16 × the English syllables, about the length of a French translation.
  - There (c) leaves the plain translation unchanged 79 % of the time.
- **Dev agreed for (c)** within 5 points of fit: 69.4–80.1 % on dev, 69.9–80.2 % on test. Two settings
  moved for (b):
  - German with syllables rose from 66.0 % to 71.6 %, level with (c).
  - French with characters fell from 67.4 % to 59.8 %, partly from more broken JSON (8.3 % of items,
    against 5.6 % on dev).

**The judge's numbers are upper bounds.** It lists the facts of the English source and judges the
German or French output against them.
- On the cross-lingual validation (tables below), every identity pair is right (100 %). So the rule
  fixed beforehand (under 90 % flags the judge) does not flag it.
- But it caught only 0 of 14 qualifier changes, 4 of 13 modal changes and 5 of 20 inserted facts. Within
  German it catches 7, 10 and 16.
- So fact recall and fit & complete overstate how much meaning is kept. The added-fact rate (0.0–0.1 %)
  is far too low.
- The NLI against the reference is monolingual, so this weakness does not affect it.

**A second NLI (post-hoc, added after test outputs existed; `results/step4_test_nli2.md`).** The loop
chooses (c)'s candidates with the same NLI that scores meaning here, so step 4 was re-scored with a second
NLI model that the loop never sees (`MoritzLaurer/bge-m3-zeroshot-v2.0-c`).
- Under it, (c) keeps the meaning 2.8–5.3 points less often than plain translation in three settings
  (level in French with syllables), and still more often than one step to the budget in three.
- (b), which no NLI chooses, shows a similar gap between the two models over all lines, so part of it is
  how the two models judge shortened lines. On the lines the loop shortened, (c) gains 1.4–6.0 points more
  from the evaluation NLI than (b) does; in German with syllables, +6.0 [+1.3, +10.7]. So the loop's
  selection probably inflates (c)'s score there, and elsewhere it can be neither shown nor ruled out.
- The second NLI is lenient on small changes (1 of 14 qualifier changes caught in German), so neither
  model settles the question. The native-speaker check compares (a) and (c) directly.

**Broken JSON is not fixed (as frozen): an answer that is not valid JSON is a miss** (no output, no fit,
no fact kept).
- (b) asks once for 4 candidates in one JSON answer, so one broken answer loses the item.
  - In French it lost 83 of 996 items with characters and 23 with syllables.
  - The causes, by the parser's first error: 69 apostrophes escaped as `\'`, 27 malformed `\u` escapes
    of accented letters, and 10 others (unescaped quotes, unfinished strings, one `\%`).
  - In German it lost 6 and 2.
- (a) asks again, at most 3 times. 3 German and 6 French items still had no translation, from two
  sentences, in every seed. (c) then has no output either.
  - One sentence (1670) quotes a speaker, and the answer leaves the double quotes unescaped (German and
    French).
  - The other (1873, French only) ends in a parenthesis, and the answer closes it after the JSON string.
- (c)'s loop gave no output for 9 more French items (characters) and 1 more German item (syllables).
- Counts per system are in the "No output" column, and per language and budget in "Parse failures".

**JSON sensitivity (post-hoc, added after test outputs existed; no new generation).** The row under (b)
re-reads only the answers strict JSON rejected, with one tolerant rule (`\'` becomes `'`), and chooses
as (b) does.
- It recovers 70 of the 114 rejected (b) answers: 51 of 83 French with characters, 18 of 23 French with
  syllables, 1 of 6 German with characters, 0 of 2 German with syllables. These are exactly the answers
  whose first parse error was `\'`.
- Fit of (b), strict → tolerant: French 59.8 → 63.2 % with characters and 44.7 → 45.3 % with syllables;
  German 59.4 → 59.5 % and 71.6 % unchanged.
- Kept against the reference (NLI), French: 69.7 → 73.8 % with characters, 74.9 → 76.6 % with
  syllables.
- So the order of the systems does not change. Paired (post-hoc, added after test outputs existed),
  (c) − (b) with (b) read this way is +14.2 [+9.0, +19.5] points of fit in French with characters
  (strict: +17.5), +24.6 [+19.4, +29.7] with syllables, and +20.7 [+15.7, +25.8] in German with
  characters; German with syllables stays a tie.
- The rule is applied to (b) only. It would also have given candidates in 62 of the 124 (c) rounds that
  gave none, but (c)'s later rounds depended on each failure, so (c) cannot be re-run without new
  generation. If anything, the comparison favours (b).
- The judge never saw the recovered outputs, so this row has no fit & complete.

**How (c)'s loop met parse failures** (table "Parse failures"; `isochron.repair`).
- A round whose answer is not valid JSON gives no candidate. If no earlier round gave one, the next
  round sends the first prompt again with a new seed (a retry). Otherwise the best candidate so far
  stays, and the next round revises it. There are at most 3 rounds; if none parsed, (c) has no output.
- Of the 124 rounds without a candidate, 79 were followed by a retry, 16 by the revision of the best
  candidate again, and 29 were already the last round.
- French with characters: 89 of 1,691 rounds (5.3 %) gave no candidate, in 60 of 739 loop runs. 51 of
  those runs still ended with an output, and 9 did not.
- Elsewhere it was rare: 15 of 1,662 rounds (German, characters), 13 of 1,841 (German, syllables) and 7
  of 461 (French, syllables). 1 German run ended without an output.

**Otherwise clean.** 2 of 10,185 outputs are in the wrong language, and none of the 10,185 judge
verdicts is invalid.
- Apertus often returned fewer candidates than the 4 asked for, mostly 1: 91 (b) answers and 686 of
  (c)'s 5,655 rounds. They are kept and scored, as frozen.
- 21 outputs contain a literal backslash from an over-escaped apostrophe (`L\'Islande`): 11 of (b) and 10
  of (c). They count as they are.

Fit, kept, added and dropped are in %. (a) is the same translation under both budgets; its fit says how
often plain translation already meets the budget.

### EN → DE, isometric budget (chars)

| System | Outputs | Fit ±10 % | Kept vs reference | Added vs ref. | Dropped vs ref. | Kept vs source | Achieved ÷ budget | Compression vs (a) | Chars / words / syllables | (a) kept | Avg. rounds | Wrong language | No output |
|--------|--------:|-----------|-------------------|--------------:|----------------:|----------------|------------------:|-------------------:|--------------------------|---------:|------------:|---------------:|----------:|
| (a) plain translation | 1041 | 27.2 [23.0, 31.4] | 79.5 [75.7, 83.3] | 13 % | 14 % | 78.2 [74.2, 82.1] | 1.17 | 1.00 | 130.4 / 21.2 / 44.1 | – | – | 0 | 3 |
| (b) one step to the budget | 1041 | 59.4 [55.1, 63.5] | 74.1 [70.3, 77.8] | 9 % | 21 % | 69.5 [65.7, 73.4] | 0.91 | 0.78 | 101.0 / 15.3 / 34.2 | – | – | 0 | 6 |
| (b), `\'` read as `'`: sensitivity (post-hoc, added after test outputs existed) | 1041 | 59.5 [55.2, 63.6] | 74.2 [70.4, 77.9] | 9 % | 21 % | 69.6 [65.8, 73.5] | 0.91 | 0.78 | 101.0 / 15.3 / 34.2 | – | – | 0 | 5 |
| (c) translate, then shorten | 1041 | 80.2 [77.1, 83.2] | 80.6 [77.0, 84.1] | 9 % | 15 % | 79.2 [75.6, 82.5] | 1.03 | 0.88 | 114.3 / 17.9 / 38.7 | 28 % | 0.88 | 0 | 3 |

### EN → DE, isometric budget (chars): final judge

| System | Outputs | Fit ±10 % | Fit & complete | Fact recall | Added-fact rate | Judge invalid |
|--------|--------:|-----------|----------------|-------------|----------------:|--------------:|
| (a) plain translation | 1041 | 27.2 [23.0, 31.4] | 26.8 [22.7, 31.0] | 99.1 [98.3, 99.7] | 0.0 % | 0 |
| (b) one step to the budget | 1041 | 59.4 [55.1, 63.5] | 53.7 [49.6, 57.8] | 91.6 [89.7, 93.3] | 0.0 % | 0 |
| (c) translate, then shorten | 1041 | 80.2 [77.1, 83.2] | 70.5 [66.8, 74.2] | 93.8 [92.1, 95.4] | 0.0 % | 0 |

### EN → DE, isometric budget (chars): paired differences (post-hoc, added after test outputs existed; percentage points)

| Difference | Fit ±10 % | Fit & complete | Kept vs reference |
|------------|-----------|----------------|-------------------|
| (c) − (b) | +20.8 [+15.8, +25.9] | +16.8 [+11.4, +22.2] | +6.5 [+2.8, +10.4] |
| (c) − (a) | +53.0 [+49.0, +57.3] | +43.7 [+39.7, +47.8] | +1.1 [-1.4, +3.6] |
| (c) − (b) with `\'` read as `'` (sensitivity) | +20.7 [+15.7, +25.8] | – | +6.4 [+2.7, +10.3] |

### EN → DE, isosyllabic budget (syllables)

| System | Outputs | Fit ±10 % | Kept vs reference | Added vs ref. | Dropped vs ref. | Kept vs source | Achieved ÷ budget | Compression vs (a) | Chars / words / syllables | (a) kept | Avg. rounds | Wrong language | No output |
|--------|--------:|-----------|-------------------|--------------:|----------------:|----------------|------------------:|-------------------:|--------------------------|---------:|------------:|---------------:|----------:|
| (a) plain translation | 1041 | 19.6 [15.8, 23.6] | 79.5 [75.7, 83.3] | 13 % | 14 % | 78.2 [74.2, 82.1] | 1.25 | 1.00 | 130.4 / 21.2 / 44.1 | – | – | 0 | 3 |
| (b) one step to the budget | 1041 | 71.6 [67.7, 75.2] | 76.8 [73.2, 80.2] | 11 % | 18 % | 72.5 [68.9, 76.1] | 1.01 | 0.81 | 105.9 / 16.3 / 35.5 | – | – | 1 | 2 |
| (b), `\'` read as `'`: sensitivity (post-hoc, added after test outputs existed) | 1041 | 71.6 [67.7, 75.2] | 76.8 [73.2, 80.2] | 11 % | 18 % | 72.5 [68.9, 76.1] | 1.01 | 0.81 | 105.9 / 16.3 / 35.5 | – | – | 1 | 2 |
| (c) translate, then shorten | 1041 | 70.3 [66.9, 73.8] | 81.6 [78.2, 84.6] | 8 % | 14 % | 77.7 [74.2, 81.1] | 1.04 | 0.84 | 108.9 / 17.0 / 36.7 | 21 % | 0.98 | 0 | 4 |

### EN → DE, isosyllabic budget (syllables): final judge

| System | Outputs | Fit ±10 % | Fit & complete | Fact recall | Added-fact rate | Judge invalid |
|--------|--------:|-----------|----------------|-------------|----------------:|--------------:|
| (a) plain translation | 1041 | 19.6 [15.8, 23.6] | 19.5 [15.8, 23.4] | 99.1 [98.3, 99.7] | 0.0 % | 0 |
| (b) one step to the budget | 1041 | 71.6 [67.7, 75.2] | 61.5 [57.4, 65.4] | 92.5 [90.9, 93.9] | 0.0 % | 0 |
| (c) translate, then shorten | 1041 | 70.3 [66.9, 73.8] | 56.9 [52.9, 60.7] | 90.4 [88.5, 92.1] | 0.0 % | 0 |

### EN → DE, isosyllabic budget (syllables): paired differences (post-hoc, added after test outputs existed; percentage points)

| Difference | Fit ±10 % | Fit & complete | Kept vs reference |
|------------|-----------|----------------|-------------------|
| (c) − (b) | -1.2 [-6.0, +3.6] | -4.6 [-9.4, +0.2] | +4.8 [+1.1, +8.5] |
| (c) − (a) | +50.7 [+46.8, +54.8] | +37.4 [+33.7, +41.1] | +2.0 [-0.7, +4.8] |
| (c) − (b) with `\'` read as `'` (sensitivity) | -1.2 [-6.0, +3.6] | – | +4.8 [+1.1, +8.5] |

### EN → FR, isometric budget (chars)

| System | Outputs | Fit ±10 % | Kept vs reference | Added vs ref. | Dropped vs ref. | Kept vs source | Achieved ÷ budget | Compression vs (a) | Chars / words / syllables | (a) kept | Avg. rounds | Wrong language | No output |
|--------|--------:|-----------|-------------------|--------------:|----------------:|----------------|------------------:|-------------------:|--------------------------|---------:|------------:|---------------:|----------:|
| (a) plain translation | 996 | 23.9 [19.7, 28.3] | 79.7 [75.7, 83.6] | 13 % | 16 % | 73.5 [69.0, 77.8] | 1.19 | 1.00 | 131.5 / 24.9 / 41.8 | – | – | 0 | 6 |
| (b) one step to the budget | 996 | 59.8 [55.5, 64.1] | 69.7 [65.8, 73.5] | 11 % | 19 % | 64.7 [60.7, 68.6] | 0.95 | 0.80 | 105.1 / 18.8 / 33.2 | – | – | 0 | 83 |
| (b), `\'` read as `'`: sensitivity (post-hoc, added after test outputs existed) | 996 | 63.2 [58.9, 67.3] | 73.8 [70.1, 77.4] | 10 % | 19 % | 68.5 [64.6, 72.3] | 0.95 | 0.79 | 104.9 / 18.8 / 33.1 | – | – | 0 | 32 |
| (c) translate, then shorten | 996 | 77.3 [74.0, 80.6] | 80.7 [77.1, 84.1] | 10 % | 14 % | 76.9 [73.1, 80.5] | 1.02 | 0.86 | 113.0 / 20.8 / 36.0 | 25 % | 0.96 | 0 | 15 |

### EN → FR, isometric budget (chars): final judge

| System | Outputs | Fit ±10 % | Fit & complete | Fact recall | Added-fact rate | Judge invalid |
|--------|--------:|-----------|----------------|-------------|----------------:|--------------:|
| (a) plain translation | 996 | 23.9 [19.7, 28.3] | 23.5 [19.4, 27.9] | 98.5 [97.2, 99.6] | 0.0 % | 0 |
| (b) one step to the budget | 996 | 59.8 [55.5, 64.1] | 53.0 [48.7, 57.3] | 85.0 [82.4, 87.6] | 0.0 % | 0 |
| (c) translate, then shorten | 996 | 77.3 [74.0, 80.6] | 68.6 [64.9, 72.2] | 92.0 [90.0, 93.8] | 0.0 % | 0 |

### EN → FR, isometric budget (chars): paired differences (post-hoc, added after test outputs existed; percentage points)

| Difference | Fit ±10 % | Fit & complete | Kept vs reference |
|------------|-----------|----------------|-------------------|
| (c) − (b) | +17.5 [+12.2, +22.9] | +15.6 [+10.0, +21.3] | +11.0 [+7.3, +14.9] |
| (c) − (a) | +53.4 [+49.0, +57.6] | +45.1 [+40.8, +49.3] | +1.0 [-2.0, +4.1] |
| (c) − (b) with `\'` read as `'` (sensitivity) | +14.2 [+9.0, +19.5] | – | +6.9 [+3.2, +10.6] |

### EN → FR, isosyllabic budget (syllables)

| System | Outputs | Fit ±10 % | Kept vs reference | Added vs ref. | Dropped vs ref. | Kept vs source | Achieved ÷ budget | Compression vs (a) | Chars / words / syllables | (a) kept | Avg. rounds | Wrong language | No output |
|--------|--------:|-----------|-------------------|--------------:|----------------:|----------------|------------------:|-------------------:|--------------------------|---------:|------------:|---------------:|----------:|
| (a) plain translation | 996 | 55.6 [50.9, 60.3] | 79.7 [75.7, 83.6] | 13 % | 16 % | 73.5 [69.0, 77.8] | 1.00 | 1.00 | 131.5 / 24.9 / 41.8 | – | – | 0 | 6 |
| (b) one step to the budget | 996 | 44.7 [40.1, 49.3] | 74.9 [71.2, 78.5] | 12 % | 18 % | 72.4 [68.6, 76.0] | 0.88 | 0.89 | 116.6 / 21.1 / 36.9 | – | – | 0 | 23 |
| (b), `\'` read as `'`: sensitivity (post-hoc, added after test outputs existed) | 996 | 45.3 [40.7, 49.9] | 76.6 [72.9, 80.1] | 12 % | 17 % | 73.7 [69.9, 77.3] | 0.88 | 0.89 | 116.6 / 21.1 / 36.9 | – | – | 0 | 5 |
| (c) translate, then shorten | 996 | 69.9 [65.7, 74.1] | 81.5 [77.8, 85.1] | 12 % | 15 % | 74.4 [70.2, 78.5] | 0.96 | 0.97 | 127.4 / 24.0 / 40.5 | 79 % | 0.26 | 1 | 6 |

### EN → FR, isosyllabic budget (syllables): final judge

| System | Outputs | Fit ±10 % | Fit & complete | Fact recall | Added-fact rate | Judge invalid |
|--------|--------:|-----------|----------------|-------------|----------------:|--------------:|
| (a) plain translation | 996 | 55.6 [50.9, 60.3] | 54.9 [50.2, 59.7] | 98.5 [97.2, 99.6] | 0.0 % | 0 |
| (b) one step to the budget | 996 | 44.7 [40.1, 49.3] | 41.9 [37.4, 46.4] | 94.2 [92.6, 95.7] | 0.1 % | 0 |
| (c) translate, then shorten | 996 | 69.9 [65.7, 74.1] | 68.1 [63.7, 72.4] | 97.7 [96.3, 98.9] | 0.0 % | 0 |

### EN → FR, isosyllabic budget (syllables): paired differences (post-hoc, added after test outputs existed; percentage points)

| Difference | Fit ±10 % | Fit & complete | Kept vs reference |
|------------|-----------|----------------|-------------------|
| (c) − (b) | +25.2 [+20.0, +30.3] | +26.2 [+20.9, +31.3] | +6.6 [+2.7, +10.6] |
| (c) − (a) | +14.3 [+11.2, +17.5] | +13.2 [+10.2, +16.3] | +1.8 [+0.3, +3.5] |
| (c) − (b) with `\'` read as `'` (sensitivity) | +24.6 [+19.4, +29.7] | – | +4.9 [+1.1, +8.7] |

### Parse failures (strict JSON, as frozen)

| Language, budget | (b) rejected | (b) recovered by the rule | (c) loop runs | (c) rounds | (c) rounds without a candidate | (c) retry rounds | (c) runs with such a round | of those, with an output | (c) runs without an output |
|------------------|-------------:|--------------------------:|--------------:|-----------:|-------------------------------:|-----------------:|---------------------------:|-------------------------:|---------------------------:|
| DE, isometric | 6 | 1 | 743 | 1662 | 15 | 13 | 11 | 11 | 0 |
| DE, isosyllabic | 2 | 0 | 823 | 1841 | 13 | 8 | 10 | 9 | 1 |
| FR, isometric | 83 | 51 | 739 | 1691 | 89 | 56 | 60 | 51 | 9 |
| FR, isosyllabic | 23 | 18 | 204 | 461 | 7 | 2 | 5 | 5 | 0 |

(a) asks again with the next seed after an unparsable answer, at most 3 times. DE: 4 of 1041 items needed another try, and 3 ended without a translation; FR: 6 of 996 items needed another try, and 6 ended without a translation. Without (a), (c) has no output either.

After a (c) round without a candidate, the next round sent: the first prompt again (a retry) 79; the revision of the best candidate again 16; none: it was the last round 29. The sensitivity rule (`\'` read as `'`) would have given candidates in 62 of these 124 rounds; (c) is left as it ran, because its later rounds depended on each failure.

Answers with fewer or more candidates than the 4 asked for (kept, and scored): (b) 91, (c)'s rounds 686. Outputs that contain a literal backslash (counted as they are): (a) 0, (b) 11, (c) 10.

## Judge validation

`results/judge_validation_nli_xl_v3_qwen3-14b_hpc_8b.md`: Mean accuracy over the 5 control types: 94 %

| Control | Expected (judge) | DE | FR | All | NLI, all |
|---------|------------------|---:|---:|---:|---:|
| identity | recall 1, nothing added | 100 % (20/20) | 100 % (20/20) | 100 % (40/40) | 72 % (29/40) |
| paraphrase | recall 1, nothing added | 100 % (20/20) | 95 % (19/20) | 98 % (39/40) | 88 % (35/40) |
| clause_deleted | recall < 1, nothing added | 100 % (20/20) | 80 % (16/20) | 90 % (36/40) | 85 % (34/40) |
| clause_inserted | recall 1, something added | 85 % (17/20) | 95 % (19/20) | 90 % (36/40) | 88 % (35/40) |
| negation | recall < 1 | 95 % (19/20) | 95 % (19/20) | 95 % (38/40) | 100 % (40/40) |

`results/judge_validation_hard_xl_v3_qwen3-14b_hpc_8b.md`: Mean accuracy over the 6 control types: 58 %

| Control | Expected (judge) | DE | All | NLI, all |
|---------|------------------|---:|---:|---:|
| identity | complete: recall 1, nothing added | 100 % (60/60) | 100 % (60/60) | 87 % (52/60) |
| same_meaning | complete: recall 1, nothing added | 100 % (20/20) | 100 % (20/20) | 80 % (16/20) |
| modal_changed | not complete | 31 % (4/13) | 31 % (4/13) | 54 % (7/13) |
| number_changed | not complete | 92 % (12/13) | 92 % (12/13) | 92 % (12/13) |
| qualifier_changed | not complete | 0 % (0/14) | 0 % (0/14) | 43 % (6/14) |
| fact_inserted | something added | 25 % (5/20) | 25 % (5/20) | 100 % (20/20) |

