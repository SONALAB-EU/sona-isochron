# Meaning judge validation on the NLI control suite

- Date: 2026-10-10 10:17 UTC
- Git commit: c75706a1d0a1be3f2f61ae05fb26b1007a84896e
- Judge: {"model": "qwen3-8b-q4_k_m", "endpoint": "http://127.0.0.1:8081/v1", "backend": {"type": "llama.cpp llama-server", "build_info": "b11429-d81235049", "model_path": "/Users/kaushikmukherjee/models/Qwen3-8B-GGUF/Qwen3-8B-Q4_K_M.gguf", "n_ctx": 8192}, "quantisation": "Q4_K_M", "generation": {"temperature": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}}, "seed": 0, "mode": "perfact_v3", "prompts": {"judge_facts_v1": "80c765ed80def67ca4b13456fe389ac7b8c695d2422cb4e3cc5fa73a7f0a6fe1", "judge_fact_v3": "5b74445c3470663b94c768aad4833a295a6ee67c73d61deb7591670fab4a1587", "judge_added_v3": "61d024e2989124746bdf0e220432222d69b384071873362d61f3043ec3595c54"}}
- NLI (last column and agreement): MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, mps, float32, argmax label
- TTS: none. Seeds: judge seed 0 at temperature 0 (greedy)
- n: 200 pairs, half all of data/nli_controls.jsonl (all = 20 German and 20 French FLEURS train sentences × 5 control types; half A = per language the 10 base sentences with the lowest FLEURS ids, used to tune judge prompts; half B = the other 10, held out)
- Invalid judge answers: 0

A pair counts as judged correctly when the judge's verdict matches its control type. The last column
repeats the NLI on the same pairs (its rule: identity and paraphrase kept; deletion dropped only;
insertion added only; negation not kept).

| Control | Expected (judge) | DE | FR | All | NLI, all |
|---------|------------------|---:|---:|---:|---:|
| identity | recall 1, nothing added | 100 % (20/20) | 100 % (20/20) | 100 % (40/40) | 95 % (38/40) |
| paraphrase | recall 1, nothing added | 100 % (20/20) | 100 % (20/20) | 100 % (40/40) | 95 % (38/40) |
| clause_deleted | recall < 1, nothing added | 100 % (20/20) | 85 % (17/20) | 92 % (37/40) | 82 % (33/40) |
| clause_inserted | recall 1, something added | 50 % (10/20) | 95 % (19/20) | 72 % (29/40) | 90 % (36/40) |
| negation | recall < 1 | 100 % (20/20) | 100 % (20/20) | 100 % (40/40) | 100 % (40/40) |

Agreement between the judge and the NLI on "kept" (judge: recall 1 and nothing added; NLI: entailment both ways): 189/200 = 94 %.

## Pairs judged wrong (14) or invalid (0)

| Id | Recall | Added | Output |
|----|-------:|------:|--------|
| de-1002-clause_inserted | 0.00 | 0 | Der Fotograf wurde in das Ronald Reagan UCLA Medical Center gebracht, wo er anschließend verstarb, nachdem seine Familie eingetroffen war. |
| de-163-clause_inserted | 0.50 | 1 | Sie sagten auch in einer Stellungnahme: „Die Mannschaft arbeitet momentan an der Entscheidung, was die beste Methode ist, das Schiff sicher zu bergen, und rechnet mit einer Bergung noch in dieser Woche.“ |
| de-691-clause_inserted | 0.67 | 1 | Die düstere Atmosphäre des Tempels und der Blick über den Tonle-Sap-See sind es wert, den Hügel zu besteigen, der allerdings nur morgens geöffnet ist. |
| de-1222-clause_inserted | 0.67 | 1 | Moldawien ist eine multiethnische Republik, die unter ethnischen Konflikte gelitten hat und deshalb ihre Hauptstadt verlegte. |
| de-1136-clause_inserted | 0.67 | 1 | Das örtliche Leitungswasser kann man bedenkenlos trinken, aber wenn Sie sich Sorgen machen, finden Sie auch problemlos abgefülltes Wasser, das allerdings recht teuer ist. |
| de-424-clause_inserted | 0.67 | 1 | Mit der Zeit verschmolzen viele Wörter, die aus dem Deutschen entlehnt worden waren, vor allem in der Hauptstadt. Das war der Beginn der Aufklärung. |
| de-427-clause_inserted | 0.00 | 0 | Charles war das erste Mitglied der britischen Königsfamilie, dem ein Hochschulabschluss verliehen wurde, und zwar in Geschichte. |
| de-1481-clause_inserted | 0.80 | 1 | Eine Fußsafari (auch „Buschgang“, „Wandersafari“ oder „Footing“ genannt) besteht aus einer Wanderung, die entweder ein paar Stunden oder mehrere Tage dauert und immer von einem bewaffneten Ranger begleitet wird. |
| de-671-clause_inserted | 0.67 | 1 | Lizenzen sind zum Schutz des Canyons limitiert, kosten jeweils hundert Dollar und sind ab dem Monatsersten, vier Monate vor dem Startmonat, erhältlich. |
| de-1266-clause_inserted | 0.75 | 1 | Obwohl viele der Tiere im Park den Anblick von Menschen gewohnt sehen, sind die Wildtiere trotzdem wild und sollten nicht gefüttert oder gestört werden; wer dagegen verstößt, muss eine hohe Strafe zahlen. |
| fr-932-clause_inserted | 0.75 | 1 | En général, pour séjourner dans un pays étranger sur une longue période, vous devez obtenir au préalable un visa, ce qui prend au moins trois mois. |
| fr-887-clause_deleted | 1.00 | 0 | L’Antarctique est l’endroit le plus froid sur Terre. |
| fr-1069-clause_deleted | 1.00 | 0 | Vous n'aurez peut-être pas d'autre choix que de recourir à la téléphonie par satellite. |
| fr-1124-clause_deleted | 1.00 | 0 | Les réduves sont nidicoles, c'est-à-dire adaptées pour vivre dans le nid ou l'habitat de leur hôte. |
