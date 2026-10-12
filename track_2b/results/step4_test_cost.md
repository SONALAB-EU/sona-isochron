# Step 4 on test: cost per line

- Date: 2026-10-12 14:29 UTC
- Git commit (report): 95a195ea522a14e1c9a69bfb3e165e195f65c4f4; runs: `hpc_8b_step4_test` (7b22d93 (synced copy, recorded by hpc/sync.sh)), `hpc_8b_step4_test_fr` (7b22d93 (synced copy, recorded by hpc/sync.sh))
- Model: apertus-v1.5-8b-bf16, quantisation BF16, backend vLLM 0.23.1rc1.dev1029+ga601a9d99, one H100 per language, 16 items in flight; endpoint de http://127.0.0.1:46167/v1, fr http://127.0.0.1:41569/v1
- Seeds [0, 1, 2]; items {"de": 1041, "fr": 996}; TTS: none
- Generation windows (measured, from the job logs: server healthy to server stopped; server start and judging excluded): de 1,689 s, fr 1,207 s
- Calls, seconds and tokens are measured. H100-seconds per line are an estimate: each window shared out by one of two rules (module docstring).

A line is one output; (c) includes the (a) translation it starts from. Means per line.

### DE, isometric budget

| System | Lines | LLM calls | LLM seconds | Prompt / completion tokens | Loop evaluation s | H100-s, worker time (estimate) | H100-s, completion tokens (estimate) |
|--------|------:|----------:|------------:|---------------------------:|------------------:|-------------------------------:|------------------------------------:|
| (a) plain translation | 1041 | 1.01 | 0.41 | 121 / 42 | – | 0.035 | 0.107 |
| (b) one step to the budget | 1041 | 1.00 | 0.86 | 182 / 114 | – | 0.073 | 0.290 |
| (c) translate, then shorten | 1041 | 2.60 | 1.72 | 478 / 216 | 6.91 | 0.731 | 0.547 |
| (c), shortening only | 1041 | 1.60 | 1.31 | 357 / 174 | 6.91 | 0.696 | 0.441 |

### DE, isosyllabic budget

| System | Lines | LLM calls | LLM seconds | Prompt / completion tokens | Loop evaluation s | H100-s, worker time (estimate) | H100-s, completion tokens (estimate) |
|--------|------:|----------:|------------:|---------------------------:|------------------:|-------------------------------:|------------------------------------:|
| (a) plain translation | 1041 | 1.01 | 0.41 | 121 / 42 | – | 0.035 | 0.107 |
| (b) one step to the budget | 1041 | 1.00 | 0.91 | 179 / 121 | – | 0.077 | 0.307 |
| (c) translate, then shorten | 1041 | 2.78 | 1.83 | 509 / 231 | 7.33 | 0.776 | 0.585 |
| (c), shortening only | 1041 | 1.77 | 1.42 | 388 / 189 | 7.33 | 0.741 | 0.478 |

### FR, isometric budget

| System | Lines | LLM calls | LLM seconds | Prompt / completion tokens | Loop evaluation s | H100-s, worker time (estimate) | H100-s, completion tokens (estimate) |
|--------|------:|----------:|------------:|---------------------------:|------------------:|-------------------------------:|------------------------------------:|
| (a) plain translation | 996 | 1.01 | 0.42 | 122 / 43 | – | 0.039 | 0.093 |
| (b) one step to the budget | 996 | 1.00 | 0.98 | 182 / 131 | – | 0.091 | 0.286 |
| (c) translate, then shorten | 996 | 2.71 | 1.92 | 496 / 243 | 6.87 | 0.822 | 0.531 |
| (c), shortening only | 996 | 1.70 | 1.50 | 374 / 200 | 6.87 | 0.783 | 0.438 |

### FR, isosyllabic budget

| System | Lines | LLM calls | LLM seconds | Prompt / completion tokens | Loop evaluation s | H100-s, worker time (estimate) | H100-s, completion tokens (estimate) |
|--------|------:|----------:|------------:|---------------------------:|------------------:|-------------------------------:|------------------------------------:|
| (a) plain translation | 996 | 1.01 | 0.42 | 122 / 43 | – | 0.039 | 0.093 |
| (b) one step to the budget | 996 | 1.00 | 0.97 | 179 / 130 | – | 0.091 | 0.283 |
| (c) translate, then shorten | 996 | 1.47 | 0.80 | 223 / 94 | 1.84 | 0.247 | 0.205 |
| (c), shortening only | 996 | 0.46 | 0.39 | 101 / 51 | 1.84 | 0.208 | 0.112 |

### All languages and budgets

| System | Lines | LLM calls | LLM seconds | Prompt / completion tokens | Loop evaluation s | H100-s, worker time (estimate) | H100-s, completion tokens (estimate) |
|--------|------:|----------:|------------:|---------------------------:|------------------:|-------------------------------:|------------------------------------:|
| (a) plain translation | 2037 | 1.01 | 0.41 | 121 / 42 | – | 0.037 | 0.100 |
| (b) one step to the budget | 4074 | 1.00 | 0.93 | 180 / 124 | – | 0.083 | 0.291 |
| (c) translate, then shorten | 4074 | 2.40 | 1.57 | 428 / 197 | 5.77 | 0.647 | 0.469 |
| (c), shortening only | 4074 | 1.39 | 1.16 | 306 / 154 | 5.77 | 0.610 | 0.369 |

Share of each window for (a) / (b) / (c)'s shortening, by rule: worker time, DE: 2.2 % / 9.2 % / 88.6 %; worker time, FR: 3.2 % / 15.0 % / 81.8 %; completion tokens, DE: 6.6 % / 36.8 % / 56.6 %; completion tokens, FR: 7.7 % / 46.9 % / 45.4 %.
