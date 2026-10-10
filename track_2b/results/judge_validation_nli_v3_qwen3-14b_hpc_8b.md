# Meaning judge validation: NLI control suite

- Date: 2026-10-10 18:22 UTC
- Git commit: 5820d9d6adf8a93ccb88793a7ff5079b9bea1843 (added by hand: the job ran in an rsync copy, not a git checkout, so the generated line said unknown; after the job, every synced file was checked identical to this commit with rsync --checksum, and the code has not changed since 1f71399)
- Judge: {"model": "qwen3-14b-bf16", "endpoint": "http://127.0.0.1:48211/v1", "backend": {"type": "vLLM", "build_info": "vLLM 0.23.1rc1.dev1029+ga601a9d99", "model_path": "/sc/home/kaushik.mukherjee/isochron_work/models/Qwen/Qwen3-14B", "max_model_len": 8192}, "quantisation": "BF16", "generation": {"temperature": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}}, "seed": 0, "mode": "perfact_v3", "prompts": {"judge_facts_v1": "80c765ed80def67ca4b13456fe389ac7b8c695d2422cb4e3cc5fa73a7f0a6fe1", "judge_fact_v3": "5b74445c3470663b94c768aad4833a295a6ee67c73d61deb7591670fab4a1587", "judge_added_v3": "61d024e2989124746bdf0e220432222d69b384071873362d61f3043ec3595c54"}}
- NLI (last column and agreement): MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, cuda, float32, argmax label
- TTS: none. Seeds: judge seed 0 at temperature 0 (greedy)
- n: 200 pairs, half all of data/nli_controls.jsonl (all = 20 German and 20 French FLEURS train sentences × 5 control types; half A tunes judge prompts, half B is held out; see isochron.judge.control_half)
- Invalid judge answers: 0
- Mean accuracy over the 5 control types: 99 %

A pair counts as judged correctly when the judge's verdict matches its control type. The last column
repeats the NLI on the same pairs (its rule: identity and paraphrase kept; deletion dropped only; insertion added only; negation not kept).

| Control | Expected (judge) | DE | FR | All | NLI, all |
|---------|------------------|---:|---:|---:|---:|
| identity | recall 1, nothing added | 100 % (20/20) | 100 % (20/20) | 100 % (40/40) | 95 % (38/40) |
| paraphrase | recall 1, nothing added | 100 % (20/20) | 95 % (19/20) | 98 % (39/40) | 95 % (38/40) |
| clause_deleted | recall < 1, nothing added | 100 % (20/20) | 95 % (19/20) | 98 % (39/40) | 82 % (33/40) |
| clause_inserted | recall 1, something added | 100 % (20/20) | 100 % (20/20) | 100 % (40/40) | 90 % (36/40) |
| negation | recall < 1 | 100 % (20/20) | 100 % (20/20) | 100 % (40/40) | 100 % (40/40) |

Agreement between the judge and the NLI on "kept" (judge: recall 1 and nothing added; NLI: entailment both ways): 188/200 = 94 %.

## Pairs judged wrong (2) or invalid (0)

| Id | Recall | Added | Edit | Output |
|----|-------:|------:|------|--------|
| fr-932-clause_deleted | 1.00 | 0 |  | En général, vous devez obtenir au préalable un visa. |
| fr-1418-paraphrase | 0.80 | 0 |  | Hélas, avec l'arrivée de nouvelles façons d'écrire, le stylo est devenu plus confidentiel et on l'utilise plus rarement. |
