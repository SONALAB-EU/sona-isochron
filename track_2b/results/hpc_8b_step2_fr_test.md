# Step 2 (hpc_8b_step2_fr_test): prompt v1 with and without the repair loop, Apertus 1.5 8b BF16, judge Qwen3-14B

- Date: 2026-10-11 13:57 UTC
- Git commit (report): 68492f2b8ffc59be4c08c78fa26bd8728a6007e6 (synced copy, recorded by hpc/sync.sh); runs: `hpc_8b_step2_fr_test` (68492f2 (synced copy, recorded by hpc/sync.sh)); judge: 68492f2 (synced copy, recorded by hpc/sync.sh)
- Model: apertus-v1.5-8b-bf16, quantisation BF16, endpoint http://127.0.0.1:51465/v1, backend vLLM 0.23.1rc1.dev1029+ga601a9d99
- Generation: {"temperature": 0.7, "top_p": 0.95, "top_k": 0, "min_p": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}}
- Prompts: v1 `shorten_syllables_v1` (fe4fbfdd800d); repair `revise_v1` (ab0593b9716e), at most 2 rounds
- Loop checks: eSpeak NG text-to-speech: 1.52.0 and NLI MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, cuda, float32, argmax label; language check in the loop: py3langid 0.4.0, restricted to de/en/fr/it; wrong language = top label is another language with probability >= 0.9; the loop never sees the judge
- Scoring: an output in the wrong language counts as a failure (py3langid 0.4.0, restricted to de/en/fr/it; wrong language = top label is another language with probability >= 0.9)
- Judge (evaluation only): qwen3-14b-bf16 (BF16), endpoint http://127.0.0.1:51087/v1, backend vLLM 0.23.1rc1.dev1029+ga601a9d99, temperature 0, seed 0, prompts judge_facts_v1 (80c765ed80de), judge_fact_v3 (5b74445c3470), judge_added_v3 (61d024e29891)
- Items: 332 sentences (all sentences in file order; fr test), levels [90, 80, 70, 60], seeds [0, 1, 2], round seeds: item seed + 1000 × round (round 0 uses the item seed); TTS: none
- 95 % intervals: bootstrap over sentences, 10000 resamples, seed 0. Split: test.

## Tables

Fit, fact recall, added-fact rate and fit & complete are in %. Time is per output (one sentence at one level
and seed). Fit & complete = fits, and the judge keeps every fact and finds nothing added. An output in the
wrong language counts as a failure.

### All levels (90 % and 80 % and 70 % and 60 %)

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 3984 | 34.4 [31.7, 37.0] | 61.6 [58.6, 64.7] | 0.1 [0.0, 0.2] | 15.5 [13.5, 17.6] | 59 % | 0.82 | 0.00 | 0 | 0.7 | 89 | 0 | 0 |
| v1 | with | 3984 | 67.6 [65.0, 70.2] | 80.2 [78.0, 82.3] | 0.1 [0.0, 0.1] | 44.2 [41.3, 47.0] | 98 % | 1.03 | 1.17 | 112 | 10.2 | 11 | 0 | 0 |

### Level 90 %

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 996 | 9.9 [7.5, 12.6] | 63.6 [60.4, 66.7] | 0.1 [0.0, 0.3] | 6.5 [4.7, 8.5] | 63 % | 0.71 | 0.00 | 0 | 0.7 | 23 | 0 | 0 |
| v1 | with | 996 | 81.6 [78.6, 84.4] | 91.9 [90.1, 93.6] | 0.1 [0.0, 0.3] | 68.3 [64.7, 71.8] | 99 % | 1.01 | 1.18 | 29 | 10.6 | 3 | 0 | 0 |

### Level 80 %

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 996 | 25.9 [22.3, 29.6] | 63.3 [59.9, 66.5] | 0.1 [0.0, 0.3] | 14.6 [11.8, 17.4] | 60 % | 0.78 | 0.00 | 0 | 0.7 | 21 | 0 | 0 |
| v1 | with | 996 | 65.9 [62.1, 69.7] | 86.2 [83.9, 88.4] | 0.0 [0.0, 0.0] | 47.5 [43.5, 51.5] | 99 % | 1.02 | 1.23 | 27 | 10.5 | 3 | 0 | 0 |

### Level 70 %

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 996 | 46.6 [42.2, 50.8] | 61.7 [58.3, 64.9] | 0.0 [0.0, 0.0] | 21.7 [18.4, 25.0] | 59 % | 0.86 | 0.00 | 0 | 0.7 | 23 | 0 | 0 |
| v1 | with | 996 | 63.4 [59.6, 67.1] | 75.6 [72.6, 78.4] | 0.0 [0.0, 0.0] | 36.1 [32.2, 40.2] | 97 % | 1.02 | 1.14 | 30 | 10.0 | 4 | 0 | 0 |

### Level 60 %

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 996 | 55.1 [51.0, 59.2] | 58.1 [54.7, 61.5] | 0.0 [0.0, 0.0] | 19.3 [16.2, 22.5] | 56 % | 0.94 | 0.00 | 0 | 0.7 | 22 | 0 | 0 |
| v1 | with | 996 | 59.6 [55.7, 63.6] | 67.1 [63.7, 70.5] | 0.1 [0.0, 0.3] | 24.7 [21.2, 28.3] | 98 % | 1.05 | 1.14 | 26 | 9.8 | 1 | 0 | 0 |
