<!-- Hand-written summary section of results/step4_test_nli2.md, inserted by `python -m isochron.meaning_check report ... --notes results/step4_test_nli2_notes.md`. Date, commits, models, endpoints, TTS, seeds and n are in that report's header. -->

## Summary

This is post-hoc, added after test outputs existed: none of it was planned before the step 4 test outputs
existed. The pre-registered meaning numbers stay those of the evaluation NLI (`results/step4_test.md`).

**Why.** The repair loop chooses (c)'s candidates with the same NLI model that then scores step 4's
meaning: in the loop against the plain translation (a), in the evaluation against the human reference. A
second NLI model that the loop never sees, with another base model and other training data, shows how much
the meaning results depend on that model.

**The second NLI is lenient on small changes.** On the planted controls it accepts identities and
paraphrases at least as often as the evaluation NLI, and catches whole-clause deletions and insertions at
least as often (deletions in German and French: 39 of 40, against 33). But in German it catches only 1 of
13 modal changes, 1 of 14 qualifier changes and 9 of 13 number changes (the evaluation NLI: 10, 3 and
12). It is not a stricter check, only an independent one, and its "kept" rates are higher everywhere:
88.2 % for plain translation, against 79.5–79.7 %.

**Ours against plain translation.** Kept vs reference, paired over sentences, in percentage points:

| EN →, budget | (c) − (a), evaluation NLI | (c) − (a), second NLI | (c) − (b), second NLI |
|--------------|---------------------------|-----------------------|-----------------------|
| DE, characters | +1.1 [−1.4, +3.6] | −3.6 [−5.3, −1.8] | +6.4 [+2.9, +9.9] |
| DE, syllables | +2.0 [−0.7, +4.8] | −5.3 [−7.7, −3.0] | +2.6 [−0.7, +5.8] |
| FR, characters | +1.0 [−2.0, +4.1] | −2.8 [−4.9, −0.8] | +9.9 [+6.4, +13.5] |
| FR, syllables | +1.8 [+0.3, +3.5] | −0.5 [−1.5, +0.6] | +6.0 [+2.8, +9.3] |

- Under the evaluation NLI, ours keeps the meaning as often as plain translation. Under the second NLI it
  keeps it 2.8–5.3 points less often in three settings; French with syllables is level.
- Ours still keeps the meaning more often than one step to the budget in three settings under both
  models. German with syllables is within noise under the second.

**Is the difference the loop choosing with the evaluation NLI? Mostly not.** How much more each system
gains from the evaluation NLI than from the second (paired, points):

| EN →, budget | (c) − (a) | (b) − (a): no NLI chooses (b) | (c) − (b): what selection could add |
|--------------|-----------|-------------------------------|-------------------------------------|
| DE, characters | +4.6 [+1.8, +7.5] | +4.5 [+0.2, +8.9] | +0.1 [−4.0, +4.1] |
| DE, syllables | +7.3 [+3.8, +11.0] | +5.1 [+0.9, +9.3] | +2.2 [−1.9, +6.4] |
| FR, characters | +3.8 [+0.8, +6.8] | +2.7 [−1.6, +7.1] | +1.1 [−2.4, +4.6] |
| FR, syllables | +2.3 [+0.6, +4.2] | +1.7 [−2.4, +6.0] | +0.6 [−3.5, +4.7] |

- (b) shortens without any NLI, yet it shows almost the same gap as (c). What (c) adds beyond (b) is +0.1
  to +2.2 points, and every interval includes 0.
- So the two models mainly disagree about shortened lines in general. The second is more sensitive to
  omissions, and it rates shortened lines further below plain translations than the evaluation NLI does.
  These data cannot show a selection effect of the loop, nor rule out a small one.
- What holds: the claim that ours keeps the meaning as well as plain translation rests on the pre-registered
  NLI. An independent NLI finds that shortening costs 2.8–5.3 points of meaning in three settings. The
  native-speaker check (`docs/native_check.md`) compares (a) and (c) directly.

**Agreement between the two models** on kept vs reference, over usable outputs: 78–84 %, Cohen's kappa
0.31–0.43.

**The evaluation NLI's catch rates** on the planted controls, run again in this job, are identical to the
NLI column of every validation report (22 of 22 cells).

**Checked independently.** A separate script, written from scratch, reproduced every number above within
0.05 point. The placebo comparison with (b) came from that check.
