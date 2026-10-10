# Meaning judge validation on the NLI control suite

- Date: 2026-10-10 09:28 UTC
- Git commit: d09f9afe9cc233095c351321743f08b01b172f22
- Judge: {"model": "qwen3-8b-q4_k_m", "endpoint": "http://127.0.0.1:8081/v1", "backend": {"type": "llama.cpp llama-server", "build_info": "b11429-d81235049", "model_path": "/Users/kaushikmukherjee/models/Qwen3-8B-GGUF/Qwen3-8B-Q4_K_M.gguf", "n_ctx": 8192}, "quantisation": "Q4_K_M", "generation": {"temperature": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}}, "seed": 0, "prompts": {"judge_facts_v1": "80c765ed80def67ca4b13456fe389ac7b8c695d2422cb4e3cc5fa73a7f0a6fe1", "judge_compare_v1": "924c58fe5c4f5f39fed95dc8bce60de59f40aaf4952f84a8a8f48a53c5bcc64a"}}
- NLI (last column and agreement): MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, mps, float32, argmax label
- TTS: none. Seeds: judge seed 0 at temperature 0 (greedy)
- n: 100 pairs, half B of data/nli_controls.jsonl (all = 20 German and 20 French FLEURS train sentences × 5 control types; half A = per language the 10 base sentences with the lowest FLEURS ids, used to tune judge prompts; half B = the other 10, held out)
- Invalid judge answers: 4

A pair counts as judged correctly when the judge's verdict matches its control type. The last column
repeats the NLI on the same pairs (its rule: identity and paraphrase kept; deletion dropped only;
insertion added only; negation not kept).

| Control | Expected (judge) | DE | FR | All | NLI, all |
|---------|------------------|---:|---:|---:|---:|
| identity | recall 1, nothing added | 50 % (5/10) | 50 % (5/10) | 50 % (10/20) | 95 % (19/20) |
| paraphrase | recall 1, nothing added | 70 % (7/10) | 30 % (3/10) | 50 % (10/20) | 100 % (20/20) |
| clause_deleted | recall < 1, nothing added | 100 % (10/10) | 80 % (8/10) | 90 % (18/20) | 85 % (17/20) |
| clause_inserted | recall 1, something added | 40 % (4/10) | 80 % (8/10) | 60 % (12/20) | 90 % (18/20) |
| negation | recall < 1 | 90 % (9/10) | 100 % (10/10) | 95 % (19/20) | 100 % (20/20) |

Agreement between the judge and the NLI on "kept" (judge: recall 1 and nothing added; NLI: entailment both ways): 77/96 = 80 %.

## Pairs judged wrong (27) or invalid (4)

| Id | Recall | Added | Output |
|----|-------:|------:|--------|
| de-1002-clause_inserted | 0.50 | 1 | Der Fotograf wurde in das Ronald Reagan UCLA Medical Center gebracht, wo er anschließend verstarb, nachdem seine Familie eingetroffen war. |
| de-1222-identity | 0.67 | 0 | Moldawien ist eine multiethnische Republik, die unter ethnischen Konflikte gelitten hat. |
| de-1222-clause_inserted | 0.67 | 1 | Moldawien ist eine multiethnische Republik, die unter ethnischen Konflikte gelitten hat und deshalb ihre Hauptstadt verlegte. |
| de-1160-identity | 0.75 | 0 | Die Mittel könnte man für hochwassersichere Häuser, eine bessere Wasserverwaltung und Nutzpflanzendiversifizierung verwenden. |
| de-1160-paraphrase | 0.75 | 1 | Man könnte die Mittel für hochwassersichere Häuser, ein besseres Wassermanagement und eine Diversifizierung der Nutzpflanzen einsetzen. |
| de-1160-clause_inserted | 0.75 | 1 | Die Mittel könnte man für hochwassersichere Häuser, eine bessere Wasserverwaltung und Nutzpflanzendiversifizierung verwenden, wie die Regierung bereits angekündigt hat. |
| de-1204-identity | 0.50 | 0 | Die Babylonier bauten jedem ihrer Götter einen Haupttempel, der als Haus des Gottes betrachtet wurde. |
| de-1204-clause_inserted | 0.50 | 1 | Die Babylonier bauten jedem ihrer Götter einen Haupttempel, der als Haus des Gottes betrachtet wurde und nur von Priesterinnen betreten werden durfte. |
| de-1481-identity | 0.60 | 0 | Eine Fußsafari (auch „Buschgang“, „Wandersafari“ oder „Footing“ genannt) besteht aus einer Wanderung, die entweder ein paar Stunden oder mehrere Tage dauert. |
| de-1481-paraphrase | 0.60 | 0 | Eine Fußsafari, die man auch „Buschgang“, „Wandersafari“ oder „Footing“ nennt, ist eine Wanderung von einigen Stunden oder mehreren Tagen. |
| de-1481-clause_inserted | 0.80 | 1 | Eine Fußsafari (auch „Buschgang“, „Wandersafari“ oder „Footing“ genannt) besteht aus einer Wanderung, die entweder ein paar Stunden oder mehrere Tage dauert und immer von einem bewaffneten Ranger begleitet wird. |
| fr-825-identity | 0.75 | 0 | Jetez un coup d’œil aux voyages dont l’agent fait la promotion, que ce soit sur un site internet ou en vitrine. |
| fr-825-paraphrase | 0.75 | 1 | Regardez les voyages que l’agent met en avant, que ce soit en vitrine ou sur un site internet. |
| fr-825-clause_inserted | 0.75 | 1 | Jetez un coup d’œil aux voyages dont l’agent fait la promotion, que ce soit sur un site internet ou en vitrine, car ils sont souvent moins chers en hiver. |
| fr-932-paraphrase | 0.50 | 0 | D'ordinaire, il faut obtenir un visa à l'avance pour un long séjour dans un pays étranger. |
| fr-1418-identity | 0.75 | 1 | Malheureusement, l'apparition de nouveaux modes de rédaction a relégué le stylo à un statut plus confidentiel et à des utilisations plus rares. |
| fr-1418-paraphrase | 0.75 | 1 | Hélas, avec l'arrivée de nouvelles façons d'écrire, le stylo est devenu plus confidentiel et on l'utilise plus rarement. |
| fr-1418-clause_deleted | 0.50 | 1 | Malheureusement, l'apparition de nouveaux modes de rédaction a relégué le stylo à un statut plus confidentiel. |
| fr-887-paraphrase | 0.50 | 0 | L’endroit le plus froid de la Terre est l’Antarctique, situé autour du pôle Sud. |
| fr-1069-paraphrase | 0.00 | 1 | Dans les zones isolées où il n'y a pas de réseau mobile, la téléphonie par satellite sera peut-être votre seule option. |
| fr-926-identity | 0.67 | 0 | S'il est interdit de prendre une simple photo de quelque chose, il ne faut même pas penser à en enregistrer une vidéo. |
| fr-926-paraphrase | 0.00 | 0 | Si une simple photo de quelque chose est interdite, inutile même d'envisager d'en filmer une vidéo. |
| fr-926-clause_inserted | 0.67 | 1 | S'il est interdit de prendre une simple photo de quelque chose, il ne faut même pas penser à en enregistrer une vidéo, sous peine de voir votre appareil confisqué. |
| fr-1360-identity | 1.00 | 1 | Il est presque impossible d’échanger de l’argent des Malouines en dehors des îles, alors changez-le avant de quitter les îles. |
| fr-1124-identity | 1.00 | 1 | Les réduves, tout comme les punaises de lit, sont nidicoles, c'est-à-dire adaptées pour vivre dans le nid ou l'habitat de leur hôte. |
| fr-1124-paraphrase | 1.00 | 1 | Comme les punaises de lit, les réduves sont nidicoles : elles sont adaptées à la vie dans le nid ou l'habitat de leur hôte. |
| fr-1124-clause_deleted | 1.00 | 1 | Les réduves sont nidicoles, c'est-à-dire adaptées pour vivre dans le nid ou l'habitat de leur hôte. |
| de-1136-identity | invalid | 2 judged facts instead of 3 | Das örtliche Leitungswasser kann man bedenkenlos trinken, aber wenn Sie sich Sorgen machen, finden Sie auch problemlos abgefülltes Wasser. |
| de-1136-paraphrase | invalid | 2 judged facts instead of 3 | Man kann das Leitungswasser vor Ort ohne Bedenken trinken; wer sich dennoch Sorgen macht, findet aber auch problemlos Wasser in Flaschen. |
| de-1136-clause_inserted | invalid | 2 judged facts instead of 3 | Das örtliche Leitungswasser kann man bedenkenlos trinken, aber wenn Sie sich Sorgen machen, finden Sie auch problemlos abgefülltes Wasser, das allerdings recht teuer ist. |
| de-1370-negation | invalid | 2 judged facts instead of 3 | Chambers, ein Agnostiker, argumentiert, dass seine Klage nicht „frivol“ sei und dass „jeder jeden verklagen kann“. |
