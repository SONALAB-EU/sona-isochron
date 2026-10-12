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

| Direction, budget | Fit ±10 % | Fit & complete | (c) − (b), paired, in points: fit; fit & complete |
|-------------------|-----------|----------------|---------------------------------------------------|
| EN → DE, characters | 27.2 / 59.4 / **80.2** | 26.8 / 53.7 / **70.5** | +20.8 [15.8, 25.9]; +16.8 [11.4, 22.2] |
| EN → DE, syllables | 19.6 / **71.6** / **70.3** | 19.5 / **61.5** / 56.9 | −1.2 [−6.0, +3.6]; −4.6 [−9.4, +0.2] |
| EN → FR, characters | 23.9 / 59.8 / **77.3** | 23.5 / 53.0 / **68.6** | +17.5 [12.2, 22.9]; +15.6 [10.0, 21.3] |
| EN → FR, syllables | 55.6 / 44.7 / **69.9** | 54.9 / 41.9 / **68.1** | +25.2 [20.0, 30.3]; +26.2 [20.9, 31.3] |

- **Translating first and then shortening fits most often in three of the four settings.** It beats one
  step to the budget by 17 to 25 points of fit.
- **German with the syllable budget is a tie on fit** (−1.2 points [−6.0, +3.6]). There the two meaning
  checks disagree:
  - the judge gives one step 4.6 points more fit & complete (interval [−9.4, +0.2]);
  - the NLI against the reference finds that (c) keeps the meaning more often (+4.8 points [+1.1, +8.5]).
- **Meaning, by the main check** (NLI against the human reference):
  - (c) keeps it as often as plain translation: +1.0 to +2.0 points. Only French with syllables
    excludes 0 (+1.8 [+0.3, +3.5]).
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
- Counts per system are in the "No output" column.

**Otherwise clean.** 2 of 10,185 outputs are in the wrong language, and none of the 10,185 judge
verdicts is invalid.
