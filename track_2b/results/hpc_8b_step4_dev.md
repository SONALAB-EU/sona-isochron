# Step 4 (hpc_8b_step4_dev): translation to a length budget

- Date: 2026-10-11 14:47 UTC
- Git commit (report): 68492f2b8ffc59be4c08c78fa26bd8728a6007e6 (synced copy, recorded by hpc/sync.sh); run: `hpc_8b_step4_dev` (68492f2)
- Model: apertus-v1.5-8b-bf16, quantisation BF16, endpoint http://127.0.0.1:53947/v1, backend vLLM 0.23.1rc1.dev1029+ga601a9d99
- Generation: {"temperature": 0.7, "top_p": 0.95, "top_k": 0, "min_p": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}}; seeds [0, 1, 2] ((a), (b): item seed; (c): item seed + 1000 × round)
- Prompts: `translate_plain_v1` (5fe6dd58bf7e), `translate_budget_chars_v1` (e81efebd7d4f), `translate_budget_syllables_v1` (a3ffa4ea51a7), `shorten_chars_v1` (004890c41f25), `shorten_syllables_v1` (fe4fbfdd800d), `revise_chars_v1` (62a308e266ab), `revise_v1` (ab0593b9716e)
- Systems: (b) closest of 4 candidates in the budget's unit; (c) prompt v1 with the repair loop in the budget's unit; (a) kept if at most 1.10 × the budget
- Budgets: {"isometric": "chars", "isosyllabic": "syllables"}; syllable rates {"en": 6.19, "de": 5.97, "fr": 7.18, "it": 6.99}; length counter eSpeak NG text-to-speech: 1.52.0
- Meaning: NLI MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, cuda, float32, argmax label; language check py3langid 0.4.0, restricted to de/en/fr/it; wrong language = top label is another language with probability >= 0.9
- Items: all sentences in file order, excluding the go/no-go ids; sentences {"de": 97, "fr": 90}; split dev; TTS: none
- 95 % intervals: bootstrap over sentences, 10000 resamples, seed 0. Dev split: exploratory.

Fit, kept, added and dropped are in %. (a) is the same translation under both budgets; its fit says how
often plain translation already meets the budget.

### EN → DE, isometric budget (chars)

| System | Outputs | Fit ±10 % | Kept vs reference | Added vs ref. | Dropped vs ref. | Kept vs source | Achieved ÷ budget | Compression vs (a) | Chars / words / syllables | (a) kept | Avg. rounds | Wrong language | No output |
|--------|--------:|-----------|-------------------|--------------:|----------------:|----------------|------------------:|-------------------:|--------------------------|---------:|------------:|---------------:|----------:|
| (a) plain translation | 291 | 26.8 [19.6, 34.7] | 79.0 [71.8, 85.9] | 14 % | 15 % | 75.9 [68.4, 83.2] | 1.18 | 1.00 | 124.2 / 20.2 / 42.3 | – | – | 0 | 2 |
| (b) one step to the budget | 291 | 58.1 [50.2, 65.6] | 76.3 [69.4, 82.8] | 10 % | 17 % | 71.1 [63.6, 78.4] | 0.92 | 0.78 | 96.4 / 14.6 / 33.1 | – | – | 0 | 1 |
| (c) translate, then shorten | 291 | 80.1 [73.9, 85.6] | 81.8 [75.3, 88.0] | 10 % | 13 % | 76.3 [69.4, 82.8] | 1.03 | 0.88 | 109.2 / 17.2 / 37.4 | 27 % | 0.88 | 0 | 2 |

### EN → DE, isosyllabic budget (syllables)

| System | Outputs | Fit ±10 % | Kept vs reference | Added vs ref. | Dropped vs ref. | Kept vs source | Achieved ÷ budget | Compression vs (a) | Chars / words / syllables | (a) kept | Avg. rounds | Wrong language | No output |
|--------|--------:|-----------|-------------------|--------------:|----------------:|----------------|------------------:|-------------------:|--------------------------|---------:|------------:|---------------:|----------:|
| (a) plain translation | 291 | 13.4 [7.6, 19.9] | 79.0 [71.8, 85.9] | 14 % | 15 % | 75.9 [68.4, 83.2] | 1.27 | 1.00 | 124.2 / 20.2 / 42.3 | – | – | 0 | 2 |
| (b) one step to the budget | 291 | 66.0 [58.4, 72.9] | 82.8 [77.3, 88.0] | 7 % | 13 % | 78.4 [71.8, 84.5] | 1.03 | 0.82 | 101.3 / 15.8 / 34.4 | – | – | 0 | 1 |
| (c) translate, then shorten | 291 | 69.4 [62.5, 75.9] | 79.0 [72.5, 85.2] | 10 % | 14 % | 77.3 [70.8, 83.5] | 1.04 | 0.83 | 101.9 / 15.9 / 34.8 | 13 % | 1.05 | 0 | 2 |

### EN → FR, isometric budget (chars)

| System | Outputs | Fit ±10 % | Kept vs reference | Added vs ref. | Dropped vs ref. | Kept vs source | Achieved ÷ budget | Compression vs (a) | Chars / words / syllables | (a) kept | Avg. rounds | Wrong language | No output |
|--------|--------:|-----------|-------------------|--------------:|----------------:|----------------|------------------:|-------------------:|--------------------------|---------:|------------:|---------------:|----------:|
| (a) plain translation | 270 | 17.4 [10.7, 24.8] | 73.3 [64.4, 81.5] | 19 % | 18 % | 75.6 [67.0, 83.3] | 1.19 | 1.00 | 125.1 / 23.3 / 39.6 | – | – | 0 | 3 |
| (b) one step to the budget | 270 | 67.4 [59.6, 74.4] | 73.7 [65.9, 80.7] | 11 % | 19 % | 72.2 [64.8, 79.3] | 0.94 | 0.80 | 98.2 / 17.5 / 31.0 | – | – | 0 | 15 |
| (c) translate, then shorten | 270 | 79.3 [72.6, 85.6] | 78.9 [71.5, 85.6] | 10 % | 15 % | 77.0 [70.0, 83.7] | 1.02 | 0.86 | 106.9 / 19.3 / 34.0 | 21 % | 0.94 | 0 | 4 |

### EN → FR, isosyllabic budget (syllables)

| System | Outputs | Fit ±10 % | Kept vs reference | Added vs ref. | Dropped vs ref. | Kept vs source | Achieved ÷ budget | Compression vs (a) | Chars / words / syllables | (a) kept | Avg. rounds | Wrong language | No output |
|--------|--------:|-----------|-------------------|--------------:|----------------:|----------------|------------------:|-------------------:|--------------------------|---------:|------------:|---------------:|----------:|
| (a) plain translation | 270 | 60.7 [51.9, 69.6] | 73.3 [64.4, 81.5] | 19 % | 18 % | 75.6 [67.0, 83.3] | 0.99 | 1.00 | 125.1 / 23.3 / 39.6 | – | – | 0 | 3 |
| (b) one step to the budget | 270 | 46.7 [38.5, 54.8] | 72.6 [64.1, 80.4] | 15 % | 18 % | 75.9 [68.5, 83.0] | 0.89 | 0.91 | 111.8 / 20.0 / 35.2 | – | – | 0 | 8 |
| (c) translate, then shorten | 270 | 74.8 [66.3, 82.6] | 74.8 [66.3, 83.0] | 17 % | 18 % | 76.7 [68.9, 84.1] | 0.97 | 0.98 | 122.4 / 22.8 / 38.8 | 81 % | 0.20 | 0 | 3 |

