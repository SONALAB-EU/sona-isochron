# Step 2 (hpc_8b_step2_de_test): prompt v1 with and without the repair loop, Apertus 1.5 8b BF16, judge Qwen3-14B

- Date: 2026-10-11 12:42 UTC
- Git commit (report): 68492f2b8ffc59be4c08c78fa26bd8728a6007e6 (synced copy, recorded by hpc/sync.sh); runs: `hpc_8b_step2_de_test` (68492f2 (synced copy, recorded by hpc/sync.sh)); judge: 68492f2 (synced copy, recorded by hpc/sync.sh)
- Model: apertus-v1.5-8b-bf16, quantisation BF16, endpoint http://127.0.0.1:38657/v1, backend vLLM 0.23.1rc1.dev1029+ga601a9d99
- Generation: {"temperature": 0.7, "top_p": 0.95, "top_k": 0, "min_p": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}}
- Prompts: v1 `shorten_syllables_v1` (fe4fbfdd800d); repair `revise_v1` (ab0593b9716e), at most 2 rounds
- Loop checks: eSpeak NG text-to-speech: 1.52.0 and NLI MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, cuda, float32, argmax label; language check in the loop: py3langid 0.4.0, restricted to de/en/fr/it; wrong language = top label is another language with probability >= 0.9; the loop never sees the judge
- Scoring: an output in the wrong language counts as a failure (py3langid 0.4.0, restricted to de/en/fr/it; wrong language = top label is another language with probability >= 0.9)
- Judge (evaluation only): qwen3-14b-bf16 (BF16), endpoint http://127.0.0.1:53663/v1, backend vLLM 0.23.1rc1.dev1029+ga601a9d99, temperature 0, seed 0, prompts judge_facts_v1 (80c765ed80de), judge_fact_v3 (5b74445c3470), judge_added_v3 (61d024e29891)
- Items: 347 sentences (all sentences in file order; de test), levels [90, 80, 70, 60], seeds [0, 1, 2], round seeds: item seed + 1000 × round (round 0 uses the item seed); TTS: none
- 95 % intervals: bootstrap over sentences, 10000 resamples, seed 0. Split: test.

## Tables

Fit, fact recall, added-fact rate and fit & complete are in %. Time is per output (one sentence at one level
and seed). Fit & complete = fits, and the judge keeps every fact and finds nothing added. An output in the
wrong language counts as a failure.

### All levels (90 % and 80 % and 70 % and 60 %)

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 4164 | 34.9 [32.5, 37.3] | 59.9 [57.0, 62.8] | 0.1 [0.0, 0.2] | 14.2 [12.4, 16.1] | 55 % | 0.83 | 0.00 | 0 | 0.7 | 28 | 0 | 0 |
| v1 | with | 4164 | 64.7 [62.1, 67.2] | 78.0 [75.9, 80.0] | 0.0 [0.0, 0.1] | 38.4 [35.7, 41.2] | 98 % | 1.05 | 1.21 | 33 | 10.5 | 0 | 0 | 0 |

### Level 90 %

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 1041 | 11.7 [9.0, 14.5] | 62.6 [59.5, 65.7] | 0.0 [0.0, 0.0] | 8.5 [6.3, 10.8] | 58 % | 0.71 | 0.00 | 0 | 0.7 | 6 | 0 | 0 |
| v1 | with | 1041 | 81.6 [78.4, 84.4] | 91.2 [89.5, 92.8] | 0.0 [0.0, 0.0] | 65.1 [61.4, 68.8] | 98 % | 1.02 | 1.16 | 8 | 10.5 | 0 | 0 | 0 |

### Level 80 %

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 1041 | 26.7 [23.2, 30.4] | 61.2 [58.0, 64.4] | 0.2 [0.0, 0.5] | 13.0 [10.5, 15.7] | 56 % | 0.79 | 0.00 | 0 | 0.7 | 6 | 0 | 0 |
| v1 | with | 1041 | 64.8 [61.2, 68.4] | 82.3 [79.8, 84.7] | 0.1 [0.0, 0.3] | 41.5 [37.7, 45.3] | 98 % | 1.03 | 1.26 | 6 | 10.8 | 0 | 0 | 0 |

### Level 70 %

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 1041 | 44.5 [40.3, 48.6] | 59.1 [55.9, 62.3] | 0.0 [0.0, 0.0] | 16.1 [13.4, 19.2] | 55 % | 0.87 | 0.00 | 0 | 0.7 | 7 | 0 | 0 |
| v1 | with | 1041 | 57.3 [53.5, 61.2] | 72.6 [69.6, 75.5] | 0.0 [0.0, 0.0] | 26.3 [22.9, 30.0] | 98 % | 1.04 | 1.22 | 8 | 10.4 | 0 | 0 | 0 |

### Level 60 %

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 1041 | 56.8 [52.7, 60.6] | 56.7 [53.6, 59.9] | 0.1 [0.0, 0.3] | 19.1 [15.9, 22.4] | 52 % | 0.96 | 0.00 | 0 | 0.7 | 9 | 0 | 0 |
| v1 | with | 1041 | 55.2 [51.3, 59.1] | 65.7 [62.7, 68.7] | 0.0 [0.0, 0.0] | 20.7 [17.4, 24.1] | 96 % | 1.08 | 1.22 | 11 | 10.5 | 0 | 0 | 0 |
