# Step 4 on test: a second meaning check (post-hoc, added after test outputs existed)

- Date: 2026-10-12 16:55 UTC
- Git commit (report): 618c4600615e88e41ceb61fdf8e88b9cc097f612; scores: f0e566c3136cb51f87b906ccaccf228d85dd1d36 (synced copy, recorded by hpc/sync.sh) (job 2647862, NVIDIA H100 80GB HBM3, torch 2.14.1+cu130, transformers 5.18.0); runs: `hpc_8b_step4_test` (7b22d93 (synced copy, recorded by hpc/sync.sh)), `hpc_8b_step4_test_fr` (7b22d93 (synced copy, recorded by hpc/sync.sh))
- Outputs scored: apertus-v1.5-8b-bf16, quantisation BF16; endpoint de http://127.0.0.1:46167/v1, fr http://127.0.0.1:41569/v1; seeds [0, 1, 2]; TTS: none
- Evaluation NLI (the loop's own model): MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, mps, float32, argmax label
- Second NLI: MoritzLaurer/bge-m3-zeroshot-v2.0-c @ 705510d, cuda, float32, argmax label. Licence: MIT (model card metadata). Base: BAAI/bge-m3-retromae (XLM-RoBERTa-large architecture; MIT). Training data: English only: MNLI and FEVER-NLI, plus synthetic zero-shot data written by Mixtral-8x7B-Instruct; no XNLI, ANLI, WANLI or LingNLI and no machine translations. Shared with the evaluation NLI: MNLI and FEVER-NLI: many of the loop model's German and French training pairs are machine translations of English pairs in this model's data; the same author; XLM-R and mDeBERTa-v3 were both pretrained on CC100. It was chosen before any of its scores on step 4's outputs or the controls existed.
- Where each score comes from: the controls, both models on the job's GPU; step 4, the evaluation NLI from isochron.step4_report's cache (`step4_test_nli_cache.jsonl`) and the second NLI from the job. Both run locally (no endpoint).
- Sentences: {"de": 347, "fr": 332}; split test. 95 % intervals: bootstrap over sentences, 10000 resamples, seed 0.

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

**Is the difference the loop choosing with the evaluation NLI? In part, at least in one setting.** How
much more each system gains from the evaluation NLI than from the second (paired, points):

| EN →, budget | All lines: (c) − (a) | (b) − (a): no NLI chooses (b) | (c) − (b) | Lines the loop shortened: (c) − (b) |
|--------------|----------------------|-------------------------------|-----------|-------------------------------------|
| DE, characters | +4.6 [+1.8, +7.5] | +4.5 [+0.2, +8.9] | +0.1 [−4.0, +4.1] | +2.0 [−2.6, +6.6] (743 lines) |
| DE, syllables | +7.3 [+3.8, +11.0] | +5.1 [+0.9, +9.3] | +2.2 [−1.9, +6.4] | +6.0 [+1.3, +10.7] (823) |
| FR, characters | +3.8 [+0.8, +6.8] | +2.7 [−1.6, +7.1] | +1.1 [−2.4, +4.6] | +1.4 [−2.5, +5.2] (739) |
| FR, syllables | +2.3 [+0.6, +4.2] | +1.7 [−2.4, +6.0] | +0.6 [−3.5, +4.7] | +5.9 [−2.5, +14.2] (204) |

- (b) shortens without any NLI, yet it shows a similar gap over all lines. So part of the difference is
  how the two models judge shortened lines: the second is more sensitive to omissions.
- Over all lines, what (c) adds beyond (b) is +0.1 to +2.2 points, every interval including 0. But (c)
  is the plain translation itself on 21–79 % of lines, which dilutes this. On the lines the loop
  shortened, it is +1.4 to +6.0 points, and in German with syllables +6.0 [+1.3, +10.7] excludes 0.
- So the loop's selection with the evaluation NLI probably inflates (c)'s meaning score in German with
  syllables. Elsewhere it can be neither shown nor ruled out.
- What holds: ours keeps the meaning as well as plain translation only by the pre-registered NLI, which is
  the loop's own. By an independent NLI, shortening costs 2.8–5.3 points of meaning in three settings.
  The native-speaker sheet (`docs/native_check.md`) compares (a) and (c) directly, but with 25 sources
  per system it can show only large differences.

**Agreement between the two models** on kept vs reference, over usable outputs: 78–84 %, Cohen's kappa
0.31–0.43.

**The evaluation NLI's catch rates** on the planted controls, run again in this job, are identical to the
NLI column of every validation report (22 of 22 cells).

**Checked independently.** A separate script, written from scratch, reproduced every all-lines number
above within 0.05 point. The placebo comparison with (b), and its restriction to the lines the loop
shortened, came from that check and from a review of the report; the report tool now prints both. The
reviewers' versions of the shortened-lines comparison, with slightly different filters, gave similar
values (German with syllables: +5.9 and +6.1, both excluding 0).

Kept: the NLI finds entailment in both directions. A missing or wrong-language output counts as not kept.

## Planted controls

### NLI control suite

The judge's column is copied from `results/judge_validation_nli_v3_qwen3-14b_hpc_8b.md`. Rule for both NLI models: identity and paraphrase kept; deletion dropped only; insertion added only; negation not kept.

| Control | Pairs | Evaluation NLI (the loop's) | Second NLI | Judge (Qwen3-14B) | Same as the validation report's NLI column |
|---------|------:|-----------------------------|------------|-------------------|-------------------------------|
| identity | 40 | 95 % (38/40) | 100 % (40/40) | 100 % (40/40) | yes |
| paraphrase | 40 | 95 % (38/40) | 100 % (40/40) | 98 % (39/40) | yes |
| clause_deleted | 40 | 82 % (33/40) | 98 % (39/40) | 98 % (39/40) | yes |
| clause_inserted | 40 | 90 % (36/40) | 100 % (40/40) | 100 % (40/40) | yes |
| negation | 40 | 100 % (40/40) | 100 % (40/40) | 100 % (40/40) | yes |

### hard controls (German)

The judge's column is copied from `results/judge_validation_hard_v3_qwen3-14b_hpc_8b.md`. Rule for both NLI models: identity and same meaning kept; a changed modal, number or qualifier not kept; an inserted fact added.

| Control | Pairs | Evaluation NLI (the loop's) | Second NLI | Judge (Qwen3-14B) | Same as the validation report's NLI column |
|---------|------:|-----------------------------|------------|-------------------|-------------------------------|
| identity | 60 | 92 % (55/60) | 100 % (60/60) | 100 % (60/60) | yes |
| same_meaning | 20 | 90 % (18/20) | 95 % (19/20) | 100 % (20/20) | yes |
| modal_changed | 13 | 77 % (10/13) | 8 % (1/13) | 77 % (10/13) | yes |
| number_changed | 13 | 92 % (12/13) | 69 % (9/13) | 100 % (13/13) | yes |
| qualifier_changed | 14 | 21 % (3/14) | 7 % (1/14) | 50 % (7/14) | yes |
| fact_inserted | 20 | 100 % (20/20) | 100 % (20/20) | 80 % (16/20) | yes |

### NLI control suite, English sources (cross-lingual)

The judge's column is copied from `results/judge_validation_nli_xl_v3_qwen3-14b_hpc_8b.md`. Rule for both NLI models: identity and paraphrase kept; deletion dropped only; insertion added only; negation not kept.

| Control | Pairs | Evaluation NLI (the loop's) | Second NLI | Judge (Qwen3-14B) | Same as the validation report's NLI column |
|---------|------:|-----------------------------|------------|-------------------|-------------------------------|
| identity | 40 | 72 % (29/40) | 95 % (38/40) | 100 % (40/40) | yes |
| paraphrase | 40 | 88 % (35/40) | 98 % (39/40) | 98 % (39/40) | yes |
| clause_deleted | 40 | 85 % (34/40) | 85 % (34/40) | 90 % (36/40) | yes |
| clause_inserted | 40 | 88 % (35/40) | 100 % (40/40) | 90 % (36/40) | yes |
| negation | 40 | 100 % (40/40) | 98 % (39/40) | 95 % (38/40) | yes |

### hard controls (German), English sources (cross-lingual)

The judge's column is copied from `results/judge_validation_hard_xl_v3_qwen3-14b_hpc_8b.md`. Rule for both NLI models: identity and same meaning kept; a changed modal, number or qualifier not kept; an inserted fact added.

| Control | Pairs | Evaluation NLI (the loop's) | Second NLI | Judge (Qwen3-14B) | Same as the validation report's NLI column |
|---------|------:|-----------------------------|------------|-------------------|-------------------------------|
| identity | 60 | 87 % (52/60) | 97 % (58/60) | 100 % (60/60) | yes |
| same_meaning | 20 | 80 % (16/20) | 100 % (20/20) | 100 % (20/20) | yes |
| modal_changed | 13 | 54 % (7/13) | 0 % (0/13) | 31 % (4/13) | yes |
| number_changed | 13 | 92 % (12/13) | 38 % (5/13) | 92 % (12/13) | yes |
| qualifier_changed | 14 | 43 % (6/14) | 7 % (1/14) | 0 % (0/14) | yes |
| fact_inserted | 20 | 100 % (20/20) | 70 % (14/20) | 25 % (5/20) | yes |

## Step 4 re-scored

### EN → DE, isometric budget (chars)

| System | Outputs | Kept vs reference: evaluation NLI | Kept vs reference: second NLI | Agreement (κ) | Kept vs source: evaluation NLI | Kept vs source: second NLI |
|--------|--------:|-----------------------------------|-------------------------------|--------------:|-------------------------------|----------------------------|
| (a) plain translation | 1041 | 79.5 [75.7, 83.3] | 88.2 [85.0, 91.3] | 84 % (0.40) | 78.2 [74.2, 82.1] | 95.0 [92.8, 97.0] |
| (b) one step to the budget | 1041 | 74.1 [70.3, 77.8] | 78.2 [74.6, 81.7] | 78 % (0.40) | 69.5 [65.7, 73.4] | 88.7 [86.0, 91.4] |
| (b), `\'` read as `'`: sensitivity (post-hoc, added after test outputs existed) | 1041 | 74.2 [70.4, 77.9] | 78.3 [74.7, 81.7] | 78 % (0.40) | 69.6 [65.8, 73.5] | 88.8 [86.1, 91.4] |
| (c) translate, then shorten | 1041 | 80.6 [77.0, 84.1] | 84.6 [81.3, 87.8] | 84 % (0.43) | 79.2 [75.6, 82.5] | 93.9 [91.5, 96.0] |

### EN → DE, isometric budget (chars): paired differences (post-hoc, added after test outputs existed; percentage points)

| Difference | Kept vs reference: evaluation NLI | Kept vs reference: second NLI |
|------------|-----------------------------------|-------------------------------|
| (c) − (a) | +1.1 [-1.4, +3.6] | -3.6 [-5.3, -1.8] |
| (c) − (b) | +6.5 [+2.8, +10.4] | +6.4 [+2.9, +9.9] |
| (b) − (a) | -5.5 [-9.6, -1.3] | -10.0 [-13.4, -6.5] |

How much more a system gains from the evaluation NLI than from the second, on kept vs reference (evaluation minus second NLI, paired, points): (c) − (a) +4.6 [+1.8, +7.5]; (b) − (a) +4.5 [+0.2, +8.9]; (c) − (b) +0.1 [-4.0, +4.1]. No NLI chooses (b)'s output, so the part that selection by the evaluation NLI inside the loop could add is (c) − (b).

The same on the 743 lines that the loop shortened (elsewhere (c) is the plain translation itself): (c) − (a) +6.5 [+2.6, +10.6]; (b) − (a) +4.4 [-0.5, +9.4]; (c) − (b) +2.0 [-2.6, +6.6].

### EN → DE, isosyllabic budget (syllables)

| System | Outputs | Kept vs reference: evaluation NLI | Kept vs reference: second NLI | Agreement (κ) | Kept vs source: evaluation NLI | Kept vs source: second NLI |
|--------|--------:|-----------------------------------|-------------------------------|--------------:|-------------------------------|----------------------------|
| (a) plain translation | 1041 | 79.5 [75.7, 83.3] | 88.2 [85.0, 91.3] | 84 % (0.40) | 78.2 [74.2, 82.1] | 95.0 [92.8, 97.0] |
| (b) one step to the budget | 1041 | 76.8 [73.2, 80.2] | 80.3 [76.8, 83.7] | 80 % (0.40) | 72.5 [68.9, 76.1] | 90.8 [88.3, 93.1] |
| (b), `\'` read as `'`: sensitivity (post-hoc, added after test outputs existed) | 1041 | 76.8 [73.2, 80.2] | 80.3 [76.8, 83.7] | 80 % (0.40) | 72.5 [68.9, 76.1] | 90.8 [88.3, 93.1] |
| (c) translate, then shorten | 1041 | 81.6 [78.2, 84.6] | 82.9 [79.5, 86.0] | 82 % (0.39) | 77.7 [74.2, 81.1] | 92.2 [89.8, 94.4] |

### EN → DE, isosyllabic budget (syllables): paired differences (post-hoc, added after test outputs existed; percentage points)

| Difference | Kept vs reference: evaluation NLI | Kept vs reference: second NLI |
|------------|-----------------------------------|-------------------------------|
| (c) − (a) | +2.0 [-0.7, +4.8] | -5.3 [-7.7, -3.0] |
| (c) − (b) | +4.8 [+1.1, +8.5] | +2.6 [-0.7, +5.8] |
| (b) − (a) | -2.8 [-6.5, +1.2] | -7.9 [-11.0, -4.7] |

How much more a system gains from the evaluation NLI than from the second, on kept vs reference (evaluation minus second NLI, paired, points): (c) − (a) +7.3 [+3.8, +11.0]; (b) − (a) +5.1 [+0.9, +9.3]; (c) − (b) +2.2 [-1.9, +6.4]. No NLI chooses (b)'s output, so the part that selection by the evaluation NLI inside the loop could add is (c) − (b).

The same on the 823 lines that the loop shortened (elsewhere (c) is the plain translation itself): (c) − (a) +9.2 [+4.9, +13.8]; (b) − (a) +3.3 [-1.3, +8.0]; (c) − (b) +6.0 [+1.3, +10.7].

### EN → FR, isometric budget (chars)

| System | Outputs | Kept vs reference: evaluation NLI | Kept vs reference: second NLI | Agreement (κ) | Kept vs source: evaluation NLI | Kept vs source: second NLI |
|--------|--------:|-----------------------------------|-------------------------------|--------------:|-------------------------------|----------------------------|
| (a) plain translation | 996 | 79.7 [75.7, 83.6] | 88.2 [84.7, 91.4] | 82 % (0.31) | 73.5 [69.0, 77.8] | 94.6 [92.2, 96.8] |
| (b) one step to the budget | 996 | 69.7 [65.8, 73.5] | 75.4 [71.7, 79.1] | 78 % (0.33) | 64.7 [60.7, 68.6] | 80.8 [77.3, 84.2] |
| (b), `\'` read as `'`: sensitivity (post-hoc, added after test outputs existed) | 996 | 73.8 [70.1, 77.4] | 79.8 [76.4, 83.2] | 78 % (0.33) | 68.5 [64.6, 72.3] | 85.3 [82.1, 88.4] |
| (c) translate, then shorten | 996 | 80.7 [77.1, 84.1] | 85.3 [81.9, 88.5] | 83 % (0.35) | 76.9 [73.1, 80.5] | 89.6 [86.5, 92.5] |

### EN → FR, isometric budget (chars): paired differences (post-hoc, added after test outputs existed; percentage points)

| Difference | Kept vs reference: evaluation NLI | Kept vs reference: second NLI |
|------------|-----------------------------------|-------------------------------|
| (c) − (a) | +1.0 [-2.0, +4.1] | -2.8 [-4.9, -0.8] |
| (c) − (b) | +11.0 [+7.3, +14.9] | +9.9 [+6.4, +13.5] |
| (b) − (a) | -10.0 [-14.6, -5.5] | -12.8 [-16.5, -9.1] |

How much more a system gains from the evaluation NLI than from the second, on kept vs reference (evaluation minus second NLI, paired, points): (c) − (a) +3.8 [+0.8, +6.8]; (b) − (a) +2.7 [-1.6, +7.1]; (c) − (b) +1.1 [-2.4, +4.6]. No NLI chooses (b)'s output, so the part that selection by the evaluation NLI inside the loop could add is (c) − (b).

The same on the 739 lines that the loop shortened (elsewhere (c) is the plain translation itself): (c) − (a) +5.1 [+1.1, +9.2]; (b) − (a) +3.8 [-1.2, +8.7]; (c) − (b) +1.4 [-2.5, +5.2].

### EN → FR, isosyllabic budget (syllables)

| System | Outputs | Kept vs reference: evaluation NLI | Kept vs reference: second NLI | Agreement (κ) | Kept vs source: evaluation NLI | Kept vs source: second NLI |
|--------|--------:|-----------------------------------|-------------------------------|--------------:|-------------------------------|----------------------------|
| (a) plain translation | 996 | 79.7 [75.7, 83.6] | 88.2 [84.7, 91.4] | 82 % (0.31) | 73.5 [69.0, 77.8] | 94.6 [92.2, 96.8] |
| (b) one step to the budget | 996 | 74.9 [71.2, 78.5] | 81.6 [78.1, 85.0] | 78 % (0.31) | 72.4 [68.6, 76.0] | 90.3 [87.6, 92.8] |
| (b), `\'` read as `'`: sensitivity (post-hoc, added after test outputs existed) | 996 | 76.6 [72.9, 80.1] | 83.2 [79.8, 86.6] | 78 % (0.31) | 73.7 [69.9, 77.3] | 91.9 [89.3, 94.3] |
| (c) translate, then shorten | 996 | 81.5 [77.8, 85.1] | 87.7 [84.3, 90.8] | 83 % (0.31) | 74.4 [70.2, 78.5] | 93.8 [91.3, 96.1] |

### EN → FR, isosyllabic budget (syllables): paired differences (post-hoc, added after test outputs existed; percentage points)

| Difference | Kept vs reference: evaluation NLI | Kept vs reference: second NLI |
|------------|-----------------------------------|-------------------------------|
| (c) − (a) | +1.8 [+0.3, +3.5] | -0.5 [-1.5, +0.6] |
| (c) − (b) | +6.6 [+2.7, +10.6] | +6.0 [+2.8, +9.3] |
| (b) − (a) | -4.8 [-8.9, -0.8] | -6.5 [-9.7, -3.4] |

How much more a system gains from the evaluation NLI than from the second, on kept vs reference (evaluation minus second NLI, paired, points): (c) − (a) +2.3 [+0.6, +4.2]; (b) − (a) +1.7 [-2.4, +6.0]; (c) − (b) +0.6 [-3.5, +4.7]. No NLI chooses (b)'s output, so the part that selection by the evaluation NLI inside the loop could add is (c) − (b).

The same on the 204 lines that the loop shortened (elsewhere (c) is the plain translation itself): (c) − (a) +11.3 [+3.0, +20.0]; (b) − (a) +5.4 [-3.9, +15.0]; (c) − (b) +5.9 [-2.5, +14.2].

