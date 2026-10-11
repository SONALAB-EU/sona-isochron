# Step 2 (hpc_8b_step2_de_dev_smoke): prompt v1 with and without the repair loop, Apertus 1.5 8b BF16, judge Qwen3-14B

- Date: 2026-10-11 11:40 UTC
- Git commit (report): 68492f2b8ffc59be4c08c78fa26bd8728a6007e6 (synced copy, recorded by hpc/sync.sh); runs: `hpc_8b_step2_de_dev_smoke` (68492f2 (synced copy, recorded by hpc/sync.sh)); judge: 68492f2 (synced copy, recorded by hpc/sync.sh)
- Model: apertus-v1.5-8b-bf16, quantisation BF16, endpoint http://127.0.0.1:38093/v1, backend vLLM 0.23.1rc1.dev1029+ga601a9d99
- Generation: {"temperature": 0.7, "top_p": 0.95, "top_k": 0, "min_p": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}}
- Prompts: v1 `shorten_syllables_v1` (fe4fbfdd800d); repair `revise_v1` (ab0593b9716e), at most 2 rounds
- Loop checks: eSpeak NG text-to-speech: 1.52.0 and NLI MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, cuda, float32, argmax label; language check in the loop: py3langid 0.4.0, restricted to de/en/fr/it; wrong language = top label is another language with probability >= 0.9; the loop never sees the judge
- Scoring: an output in the wrong language counts as a failure (py3langid 0.4.0, restricted to de/en/fr/it; wrong language = top label is another language with probability >= 0.9)
- Judge (evaluation only): qwen3-14b-bf16 (BF16), endpoint http://127.0.0.1:52029/v1, backend vLLM 0.23.1rc1.dev1029+ga601a9d99, temperature 0, seed 0, prompts judge_facts_v1 (80c765ed80de), judge_fact_v3 (5b74445c3470), judge_added_v3 (61d024e29891)
- Items: 5 sentences (ids 1516 1525 1528 1533 1537; de dev), levels [90, 80], seeds [0], round seeds: item seed + 1000 × round (round 0 uses the item seed); TTS: none
- 95 % intervals: bootstrap over sentences, 10000 resamples, seed 0. Dev split: exploratory, not a decision.

## Tables

Fit, fact recall, added-fact rate and fit & complete are in %. Time is per output (one sentence at one level
and seed). Fit & complete = fits, and the judge keeps every fact and finds nothing added. An output in the
wrong language counts as a failure.

### Both levels (90 % and 80 %)

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 10 | 30.0 [0.0, 70.0] | 68.6 [40.9, 95.0] | 0.0 [0.0, 0.0] | 10.0 [0.0, 30.0] | 70 % | 0.82 | 0.00 | 0 | 0.7 | 0 | 0 | 0 |
| v1 | with | 10 | 70.0 [50.0, 90.0] | 83.6 [50.9, 100.0] | 0.0 [0.0, 0.0] | 50.0 [20.0, 80.0] | 100 % | 1.06 | 1.00 | 0 | 9.3 | 0 | 0 | 0 |

### Level 90 %

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 5 | 40.0 [0.0, 80.0] | 73.6 [40.9, 100.0] | 0.0 [0.0, 0.0] | 20.0 [0.0, 60.0] | 80 % | 0.81 | 0.00 | 0 | 0.7 | 0 | 0 | 0 |
| v1 | with | 5 | 100.0 [100.0, 100.0] | 83.6 [50.9, 100.0] | 0.0 [0.0, 0.0] | 80.0 [40.0, 100.0] | 100 % | 1.00 | 0.60 | 0 | 8.2 | 0 | 0 | 0 |

### Level 80 %

| Variant | Repair loop | Outputs | Fit ±10 % | Fact recall | Added-fact rate | Fit & complete | NLI kept | Achieved ÷ target | Avg. rounds | Retries | Time / output (s) | No output | Wrong language | Judge invalid |
|---------|-------------|--------:|-----------|-------------|-----------------|----------------|---------:|------------------:|------------:|--------:|------------------:|----------:|---------------:|--------------:|
| v1 | without | 5 | 20.0 [0.0, 60.0] | 63.6 [37.3, 90.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 60 % | 0.83 | 0.00 | 0 | 0.6 | 0 | 0 | 0 |
| v1 | with | 5 | 40.0 [0.0, 80.0] | 83.6 [50.9, 100.0] | 0.0 [0.0, 0.0] | 20.0 [0.0, 60.0] | 100 % | 1.12 | 1.40 | 0 | 10.4 | 0 | 0 | 0 |
