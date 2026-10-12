# Meaning judge validation: NLI control suite, English sources (cross-lingual)

- Date: 2026-10-12 11:36 UTC
- Git commit: 7b22d93e7e052f8272d7a033db73d74abc479388 (synced copy, recorded by hpc/sync.sh)
- Judge: {"model": "qwen3-14b-bf16", "endpoint": "http://127.0.0.1:50193/v1", "backend": {"type": "vLLM", "build_info": "vLLM 0.23.1rc1.dev1029+ga601a9d99", "model_path": "/sc/home/kaushik.mukherjee/isochron_work/models/Qwen/Qwen3-14B", "max_model_len": 8192}, "quantisation": "BF16", "generation": {"temperature": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}}, "seed": 0, "mode": "perfact_v3", "prompts": {"judge_facts_v1": "80c765ed80def67ca4b13456fe389ac7b8c695d2422cb4e3cc5fa73a7f0a6fe1", "judge_fact_v3": "5b74445c3470663b94c768aad4833a295a6ee67c73d61deb7591670fab4a1587", "judge_added_v3": "61d024e2989124746bdf0e220432222d69b384071873362d61f3043ec3595c54"}}
- NLI (last column and agreement): MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, cuda, float32, argmax label
- TTS: none. Seeds: judge seed 0 at temperature 0 (greedy)
- n: 200 pairs, half all of data/nli_controls_xl.jsonl (all = the nli suite with each source replaced by its English original (cross-lingual); half A tunes judge prompts, half B is held out; see isochron.judge.control_half)
- Invalid judge answers: 0
- Mean accuracy over the 5 control types: 94 %

A pair counts as judged correctly when the judge's verdict matches its control type. The last column
repeats the NLI on the same pairs (its rule: identity and paraphrase kept; deletion dropped only; insertion added only; negation not kept).

| Control | Expected (judge) | DE | FR | All | NLI, all |
|---------|------------------|---:|---:|---:|---:|
| identity | recall 1, nothing added | 100 % (20/20) | 100 % (20/20) | 100 % (40/40) | 72 % (29/40) |
| paraphrase | recall 1, nothing added | 100 % (20/20) | 95 % (19/20) | 98 % (39/40) | 88 % (35/40) |
| clause_deleted | recall < 1, nothing added | 100 % (20/20) | 80 % (16/20) | 90 % (36/40) | 85 % (34/40) |
| clause_inserted | recall 1, something added | 85 % (17/20) | 95 % (19/20) | 90 % (36/40) | 88 % (35/40) |
| negation | recall < 1 | 95 % (19/20) | 95 % (19/20) | 95 % (38/40) | 100 % (40/40) |

Agreement between the judge and the NLI on "kept" (judge: recall 1 and nothing added; NLI: entailment both ways): 175/200 = 88 %.

## Pairs judged wrong (11) or invalid (0)

| Id | Recall | Added | Edit | Output |
|----|-------:|------:|------|--------|
| xl-de-1160-negation | 1.00 | 0 |  | Die Mittel könnte man nicht für hochwassersichere Häuser, eine bessere Wasserverwaltung und Nutzpflanzendiversifizierung verwenden. |
| xl-de-1136-clause_inserted | 0.50 | 1 |  | Das örtliche Leitungswasser kann man bedenkenlos trinken, aber wenn Sie sich Sorgen machen, finden Sie auch problemlos abgefülltes Wasser, das allerdings recht teuer ist. |
| xl-de-424-clause_inserted | 0.50 | 1 |  | Mit der Zeit verschmolzen viele Wörter, die aus dem Deutschen entlehnt worden waren, vor allem in der Hauptstadt. Das war der Beginn der Aufklärung. |
| xl-de-1481-clause_inserted | 0.50 | 1 |  | Eine Fußsafari (auch „Buschgang“, „Wandersafari“ oder „Footing“ genannt) besteht aus einer Wanderung, die entweder ein paar Stunden oder mehrere Tage dauert und immer von einem bewaffneten Ranger begleitet wird. |
| xl-fr-1366-clause_deleted | 1.00 | 0 |  | De plus, des tournois et des matchs de moindre envergure sont parfois organisés ici. |
| xl-fr-825-negation | 1.00 | 0 |  | Ne jetez pas un coup d’œil aux voyages dont l’agent fait la promotion, que ce soit sur un site internet ou en vitrine. |
| xl-fr-932-clause_deleted | 1.00 | 0 |  | En général, vous devez obtenir au préalable un visa. |
| xl-fr-932-clause_inserted | 0.00 | 1 |  | En général, pour séjourner dans un pays étranger sur une longue période, vous devez obtenir au préalable un visa, ce qui prend au moins trois mois. |
| xl-fr-1418-paraphrase | 0.50 | 0 |  | Hélas, avec l'arrivée de nouvelles façons d'écrire, le stylo est devenu plus confidentiel et on l'utilise plus rarement. |
| xl-fr-1418-clause_deleted | 1.00 | 0 |  | Malheureusement, l'apparition de nouveaux modes de rédaction a relégué le stylo à un statut plus confidentiel. |
| xl-fr-1069-clause_deleted | 1.00 | 0 |  | Vous n'aurez peut-être pas d'autre choix que de recourir à la téléphonie par satellite. |
