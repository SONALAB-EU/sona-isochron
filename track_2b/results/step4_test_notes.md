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
