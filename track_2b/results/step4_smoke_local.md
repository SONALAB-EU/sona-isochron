# Step 4 (step4_smoke_local): translation to a length budget

- Date: 2026-10-10 16:44 UTC
- Git commit (report): 359527bcf31d692eef0869737aaa9cbd2947e368; run: `step4_smoke_local` (f564cf2)
- Model: apertus-v1.5-8b-text-q4_k_m, quantisation Q4_K_M, endpoint http://127.0.0.1:8080/v1, backend b11429-d81235049
- Generation: {"temperature": 0.7, "top_p": 0.95, "top_k": 0, "min_p": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}, "samplers": ["temperature", "top_p"]}; seeds [0] ((a), (b): item seed; (c): item seed + 1000 × round)
- Prompts: `translate_plain_v1` (5fe6dd58bf7e), `translate_budget_chars_v1` (e81efebd7d4f), `translate_budget_syllables_v1` (a3ffa4ea51a7), `shorten_chars_v1` (004890c41f25), `shorten_syllables_v1` (fe4fbfdd800d), `revise_chars_v1` (62a308e266ab), `revise_v1` (ab0593b9716e)
- Systems: (b) closest of 4 candidates in the budget's unit; (c) prompt v1 with the repair loop in the budget's unit; (a) kept if at most 1.10 × the budget
- Budgets: {"isometric": "chars", "isosyllabic": "syllables"}; syllable rates {"en": 6.19, "de": 5.97, "fr": 7.18, "it": 6.99}; length counter eSpeak NG text-to-speech: 1.52.0
- Meaning: NLI MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, mps, float32, argmax label; language check py3langid 0.4.0, restricted to de/en/fr/it; wrong language = top label is another language with probability >= 0.9
- Items: all sentences in file order, excluding the go/no-go ids, first 5 per language; sentences {"de": 5, "fr": 5}; split dev; TTS: none
- 95 % intervals: bootstrap over sentences, 10000 resamples, seed 0. Dev split: exploratory.

Fit, kept, added and dropped are in %. (a) is the same translation under both budgets; its fit says how
often plain translation already meets the budget.

### EN → DE, isometric budget (chars)

| System | Outputs | Fit ±10 % | Kept vs reference | Added vs ref. | Dropped vs ref. | Kept vs source | Achieved ÷ budget | Compression vs (a) | Chars / words / syllables | (a) kept | Avg. rounds | Wrong language | No output |
|--------|--------:|-----------|-------------------|--------------:|----------------:|----------------|------------------:|-------------------:|--------------------------|---------:|------------:|---------------:|----------:|
| (a) plain translation | 5 | 40.0 [0.0, 80.0] | 100.0 [100.0, 100.0] | 0 % | 0 % | 80.0 [40.0, 100.0] | 1.23 | 1.00 | 120.4 / 20.8 / 41.8 | – | – | 0 | 0 |
| (b) one step to the budget | 5 | 100.0 [100.0, 100.0] | 40.0 [0.0, 80.0] | 40 % | 60 % | 40.0 [0.0, 80.0] | 0.99 | 0.82 | 100.4 / 16.0 / 35.0 | – | – | 0 | 0 |
| (c) translate, then shorten | 5 | 100.0 [100.0, 100.0] | 80.0 [40.0, 100.0] | 0 % | 20 % | 80.0 [40.0, 100.0] | 1.03 | 0.86 | 107.0 / 17.8 / 39.2 | 40 % | 0.20 | 0 | 0 |

### EN → DE, isosyllabic budget (syllables)

| System | Outputs | Fit ±10 % | Kept vs reference | Added vs ref. | Dropped vs ref. | Kept vs source | Achieved ÷ budget | Compression vs (a) | Chars / words / syllables | (a) kept | Avg. rounds | Wrong language | No output |
|--------|--------:|-----------|-------------------|--------------:|----------------:|----------------|------------------:|-------------------:|--------------------------|---------:|------------:|---------------:|----------:|
| (a) plain translation | 5 | 0.0 [0.0, 0.0] | 100.0 [100.0, 100.0] | 0 % | 0 % | 80.0 [40.0, 100.0] | 1.34 | 1.00 | 120.4 / 20.8 / 41.8 | – | – | 0 | 0 |
| (b) one step to the budget | 5 | 60.0 [20.0, 100.0] | 80.0 [40.0, 100.0] | 20 % | 0 % | 100.0 [100.0, 100.0] | 1.10 | 0.83 | 104.2 / 17.0 / 35.4 | – | – | 0 | 0 |
| (c) translate, then shorten | 5 | 60.0 [20.0, 100.0] | 100.0 [100.0, 100.0] | 0 % | 0 % | 100.0 [100.0, 100.0] | 1.07 | 0.81 | 98.2 / 16.4 / 34.0 | 0 % | 1.00 | 0 | 0 |

### EN → FR, isometric budget (chars)

| System | Outputs | Fit ±10 % | Kept vs reference | Added vs ref. | Dropped vs ref. | Kept vs source | Achieved ÷ budget | Compression vs (a) | Chars / words / syllables | (a) kept | Avg. rounds | Wrong language | No output |
|--------|--------:|-----------|-------------------|--------------:|----------------:|----------------|------------------:|-------------------:|--------------------------|---------:|------------:|---------------:|----------:|
| (a) plain translation | 5 | 0.0 [0.0, 0.0] | 80.0 [40.0, 100.0] | 20 % | 20 % | 100.0 [100.0, 100.0] | 1.20 | 1.00 | 123.6 / 23.2 / 39.4 | – | – | 0 | 0 |
| (b) one step to the budget | 5 | 80.0 [40.0, 100.0] | 80.0 [40.0, 100.0] | 0 % | 0 % | 40.0 [0.0, 80.0] | 1.00 | 0.86 | 82.8 / 14.2 / 25.2 | – | – | 0 | 1 |
| (c) translate, then shorten | 5 | 60.0 [20.0, 100.0] | 80.0 [40.0, 100.0] | 20 % | 20 % | 60.0 [20.0, 100.0] | 1.06 | 0.89 | 106.6 / 16.6 / 33.2 | 0 % | 1.40 | 0 | 0 |

### EN → FR, isosyllabic budget (syllables)

| System | Outputs | Fit ±10 % | Kept vs reference | Added vs ref. | Dropped vs ref. | Kept vs source | Achieved ÷ budget | Compression vs (a) | Chars / words / syllables | (a) kept | Avg. rounds | Wrong language | No output |
|--------|--------:|-----------|-------------------|--------------:|----------------:|----------------|------------------:|-------------------:|--------------------------|---------:|------------:|---------------:|----------:|
| (a) plain translation | 5 | 60.0 [20.0, 100.0] | 80.0 [40.0, 100.0] | 20 % | 20 % | 100.0 [100.0, 100.0] | 1.01 | 1.00 | 123.6 / 23.2 / 39.4 | – | – | 0 | 0 |
| (b) one step to the budget | 5 | 100.0 [100.0, 100.0] | 60.0 [20.0, 100.0] | 20 % | 40 % | 80.0 [40.0, 100.0] | 1.01 | 1.01 | 119.8 / 20.6 / 38.2 | – | – | 0 | 0 |
| (c) translate, then shorten | 5 | 80.0 [40.0, 100.0] | 80.0 [40.0, 100.0] | 20 % | 20 % | 100.0 [100.0, 100.0] | 0.97 | 0.96 | 115.0 / 21.2 / 36.8 | 80 % | 0.00 | 0 | 0 |


Note (added by hand, 2026-10-10): the run started before the step 4 code was committed, so its config records
commit f564cf2 with uncommitted changes. The code that ran (step4.py, repair.py, the step 4 prompts) was committed
unchanged as b342dca. Five sentences per language and seed 0: a smoke test, not a measurement.
