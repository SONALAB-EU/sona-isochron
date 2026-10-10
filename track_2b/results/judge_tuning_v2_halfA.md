# Meaning judge validation on the NLI control suite

- Date: 2026-10-10 09:50 UTC
- Git commit: c75706a1d0a1be3f2f61ae05fb26b1007a84896e
- Judge: {"model": "qwen3-8b-q4_k_m", "endpoint": "http://127.0.0.1:8081/v1", "backend": {"type": "llama.cpp llama-server", "build_info": "b11429-d81235049", "model_path": "/Users/kaushikmukherjee/models/Qwen3-8B-GGUF/Qwen3-8B-Q4_K_M.gguf", "n_ctx": 8192}, "quantisation": "Q4_K_M", "generation": {"temperature": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}}, "seed": 0, "mode": "single call", "prompts": {"judge_facts_v1": "80c765ed80def67ca4b13456fe389ac7b8c695d2422cb4e3cc5fa73a7f0a6fe1", "judge_compare_v2": "7fccc64498529bcec13e6f486ad7d022f4f5c9d8830fadf8868bdcb3266ad07e"}}
- NLI (last column and agreement): MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, mps, float32, argmax label
- TTS: none. Seeds: judge seed 0 at temperature 0 (greedy)
- n: 100 pairs, half A of data/nli_controls.jsonl (all = 20 German and 20 French FLEURS train sentences × 5 control types; half A = per language the 10 base sentences with the lowest FLEURS ids, used to tune judge prompts; half B = the other 10, held out)
- Invalid judge answers: 0

A pair counts as judged correctly when the judge's verdict matches its control type. The last column
repeats the NLI on the same pairs (its rule: identity and paraphrase kept; deletion dropped only;
insertion added only; negation not kept).

| Control | Expected (judge) | DE | FR | All | NLI, all |
|---------|------------------|---:|---:|---:|---:|
| identity | recall 1, nothing added | 90 % (9/10) | 100 % (10/10) | 95 % (19/20) | 95 % (19/20) |
| paraphrase | recall 1, nothing added | 30 % (3/10) | 30 % (3/10) | 30 % (6/20) | 90 % (18/20) |
| clause_deleted | recall < 1, nothing added | 100 % (10/10) | 100 % (10/10) | 100 % (20/20) | 80 % (16/20) |
| clause_inserted | recall 1, something added | 80 % (8/10) | 90 % (9/10) | 85 % (17/20) | 90 % (18/20) |
| negation | recall < 1 | 100 % (10/10) | 100 % (10/10) | 100 % (20/20) | 100 % (20/20) |

Agreement between the judge and the NLI on "kept" (judge: recall 1 and nothing added; NLI: entailment both ways): 80/100 = 80 %.

## Pairs judged wrong (18) or invalid (0)

| Id | Recall | Added | Output |
|----|-------:|------:|--------|
| de-163-paraphrase | 0.75 | 0 | In einer Stellungnahme erklärten sie außerdem: „Das Team arbeitet derzeit an der Entscheidung, wie das Schiff am besten sicher geborgen werden kann.“ |
| de-691-paraphrase | 0.67 | 0 | Es lohnt sich, den Hügel zu besteigen, wegen der düsteren Atmosphäre des Tempels und des Blicks über den Tonle-Sap-See. |
| de-691-clause_inserted | 0.67 | 1 | Die düstere Atmosphäre des Tempels und der Blick über den Tonle-Sap-See sind es wert, den Hügel zu besteigen, der allerdings nur morgens geöffnet ist. |
| de-784-paraphrase | 0.50 | 0 | Für Wildtierfotografie braucht man häufig lange Teleobjektive, auch wenn Motive wie ein Vogelschwarm oder ein kleines Lebewesen andere Objektive erfordern. |
| de-878-paraphrase | 0.83 | 0 | Infektionskrankheiten sind Krankheiten, die von Erregern wie Viren, Bakterien, Pilzen oder anderen Parasiten ausgelöst werden. |
| de-424-paraphrase | 0.67 | 0 | Im Laufe der Zeit verschmolzen viele aus dem Deutschen entlehnte Wörter. Damit begann die Aufklärung. |
| de-427-identity | 0.67 | 0 | Charles war das erste Mitglied der britischen Königsfamilie, dem ein Hochschulabschluss verliehen wurde. |
| de-427-paraphrase | 0.67 | 0 | Als erstes Mitglied der britischen Königsfamilie erhielt Charles einen Hochschulabschluss. |
| de-427-clause_inserted | 0.67 | 1 | Charles war das erste Mitglied der britischen Königsfamilie, dem ein Hochschulabschluss verliehen wurde, und zwar in Geschichte. |
| de-319-paraphrase | 0.60 | 0 | China hat in den vergangenen dreißig Jahren eine Marktwirtschaft aufgebaut, obwohl es offiziell ein kommunistischer Staat geblieben ist. |
| fr-775-paraphrase | 0.75 | 2 | Les salons horticoles internationaux sont des événements spécialisés où l'on présente des vitrines florales, des jardins botaniques et tout ce qui a trait aux plantes. |
| fr-165-paraphrase | 0.50 | 1 | Il est rattaché à la septième flotte de la marine américaine, avec Sasebo (Nagasaki, Japon) comme port d'attache. |
| fr-804-paraphrase | 0.80 | 0 | Les alcools forts illicites peuvent renfermer différentes impuretés dangereuses, dont le méthanol, qui peut rendre aveugle ou tuer, même à faible dose. |
| fr-654-paraphrase | 0.67 | 0 | Au Canada, les habitants autochtones du Groenland sont appelés Inuit ; au Groenland, on les appelle Kalaalleq (pluriel Kalaallit), Groenlandais. |
| fr-740-paraphrase | 0.75 | 0 | Situé en Polynésie, au cœur du Pacifique sud, l'archipel des îles Cook est un État librement associé à la Nouvelle-Zélande. |
| fr-527-clause_inserted | 0.91 | 1 | Dans une embuscade à l'est de Bardia, les Britanniques ont capturé l'ingénieur en chef de la dixième armée italienne, le général Lastucci, ainsi que deux de ses officiers. |
| fr-388-paraphrase | 0.50 | 0 | Au départ, il a appelé l’alphabet Hangeul Hunmin Jeongeum, ce qui veut dire « les sons corrects pour instruire le peuple ». |
| fr-612-paraphrase | 0.33 | 0 | Les ordinateurs sont capables de produire des animations complexes, que la télévision et le cinéma utilisent de plus en plus. |
