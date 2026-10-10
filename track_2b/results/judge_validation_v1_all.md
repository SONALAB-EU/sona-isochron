# Meaning judge validation on the NLI control suite

- Date: 2026-10-10 09:28 UTC
- Git commit: d09f9afe9cc233095c351321743f08b01b172f22
- Judge: {"model": "qwen3-8b-q4_k_m", "endpoint": "http://127.0.0.1:8081/v1", "backend": {"type": "llama.cpp llama-server", "build_info": "b11429-d81235049", "model_path": "/Users/kaushikmukherjee/models/Qwen3-8B-GGUF/Qwen3-8B-Q4_K_M.gguf", "n_ctx": 8192}, "quantisation": "Q4_K_M", "generation": {"temperature": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}}, "seed": 0, "prompts": {"judge_facts_v1": "80c765ed80def67ca4b13456fe389ac7b8c695d2422cb4e3cc5fa73a7f0a6fe1", "judge_compare_v1": "924c58fe5c4f5f39fed95dc8bce60de59f40aaf4952f84a8a8f48a53c5bcc64a"}}
- NLI (last column and agreement): MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, mps, float32, argmax label
- TTS: none. Seeds: judge seed 0 at temperature 0 (greedy)
- n: 200 pairs, half all of data/nli_controls.jsonl (all = 20 German and 20 French FLEURS train sentences × 5 control types; half A = per language the 10 base sentences with the lowest FLEURS ids, used to tune judge prompts; half B = the other 10, held out)
- Invalid judge answers: 14

A pair counts as judged correctly when the judge's verdict matches its control type. The last column
repeats the NLI on the same pairs (its rule: identity and paraphrase kept; deletion dropped only;
insertion added only; negation not kept).

| Control | Expected (judge) | DE | FR | All | NLI, all |
|---------|------------------|---:|---:|---:|---:|
| identity | recall 1, nothing added | 35 % (7/20) | 65 % (13/20) | 50 % (20/40) | 95 % (38/40) |
| paraphrase | recall 1, nothing added | 50 % (10/20) | 30 % (6/20) | 40 % (16/40) | 95 % (38/40) |
| clause_deleted | recall < 1, nothing added | 90 % (18/20) | 85 % (17/20) | 88 % (35/40) | 82 % (33/40) |
| clause_inserted | recall 1, something added | 50 % (10/20) | 80 % (16/20) | 65 % (26/40) | 90 % (36/40) |
| negation | recall < 1 | 90 % (18/20) | 95 % (19/20) | 92 % (37/40) | 100 % (40/40) |

Agreement between the judge and the NLI on "kept" (judge: recall 1 and nothing added; NLI: entailment both ways): 142/186 = 76 %.

## Pairs judged wrong (52) or invalid (14)

| Id | Recall | Added | Output |
|----|-------:|------:|--------|
| de-1002-clause_inserted | 0.50 | 1 | Der Fotograf wurde in das Ronald Reagan UCLA Medical Center gebracht, wo er anschließend verstarb, nachdem seine Familie eingetroffen war. |
| de-163-identity | 0.50 | 1 | Sie sagten auch in einer Stellungnahme: „Die Mannschaft arbeitet momentan an der Entscheidung, was die beste Methode ist, das Schiff sicher zu bergen.“ |
| de-163-paraphrase | 0.50 | 1 | In einer Stellungnahme erklärten sie außerdem: „Das Team arbeitet derzeit an der Entscheidung, wie das Schiff am besten sicher geborgen werden kann.“ |
| de-163-clause_deleted | 0.50 | 1 | Sie sagten auch in einer Stellungnahme: „Die Mannschaft arbeitet momentan an einer Entscheidung.“ |
| de-163-clause_inserted | 0.50 | 3 | Sie sagten auch in einer Stellungnahme: „Die Mannschaft arbeitet momentan an der Entscheidung, was die beste Methode ist, das Schiff sicher zu bergen, und rechnet mit einer Bergung noch in dieser Woche.“ |
| de-691-identity | 0.67 | 0 | Die düstere Atmosphäre des Tempels und der Blick über den Tonle-Sap-See sind es wert, den Hügel zu besteigen. |
| de-691-paraphrase | 0.67 | 1 | Es lohnt sich, den Hügel zu besteigen, wegen der düsteren Atmosphäre des Tempels und des Blicks über den Tonle-Sap-See. |
| de-1222-identity | 0.67 | 0 | Moldawien ist eine multiethnische Republik, die unter ethnischen Konflikte gelitten hat. |
| de-1222-clause_inserted | 0.67 | 1 | Moldawien ist eine multiethnische Republik, die unter ethnischen Konflikte gelitten hat und deshalb ihre Hauptstadt verlegte. |
| de-1160-identity | 0.75 | 0 | Die Mittel könnte man für hochwassersichere Häuser, eine bessere Wasserverwaltung und Nutzpflanzendiversifizierung verwenden. |
| de-1160-paraphrase | 0.75 | 1 | Man könnte die Mittel für hochwassersichere Häuser, ein besseres Wassermanagement und eine Diversifizierung der Nutzpflanzen einsetzen. |
| de-1160-clause_inserted | 0.75 | 1 | Die Mittel könnte man für hochwassersichere Häuser, eine bessere Wasserverwaltung und Nutzpflanzendiversifizierung verwenden, wie die Regierung bereits angekündigt hat. |
| de-784-paraphrase | 0.50 | 0 | Für Wildtierfotografie braucht man häufig lange Teleobjektive, auch wenn Motive wie ein Vogelschwarm oder ein kleines Lebewesen andere Objektive erfordern. |
| de-607-identity | 0.80 | 1 | Die Zeit wird seit Jahrtausenden von religiösen, philosophischen und wissenschaftlichen Denkern erforscht. |
| de-607-paraphrase | 0.80 | 0 | Seit Jahrtausenden erforschen religiöse, philosophische und wissenschaftliche Denker die Zeit. |
| de-1204-identity | 0.50 | 0 | Die Babylonier bauten jedem ihrer Götter einen Haupttempel, der als Haus des Gottes betrachtet wurde. |
| de-1204-clause_inserted | 0.50 | 1 | Die Babylonier bauten jedem ihrer Götter einen Haupttempel, der als Haus des Gottes betrachtet wurde und nur von Priesterinnen betreten werden durfte. |
| de-735-identity | 0.50 | 1 | Genehmigungen müssen im Voraus bestellt werden. Sie benötigen eine Genehmigung, um in La Sirena zu übernachten. |
| de-427-identity | 0.33 | 0 | Charles war das erste Mitglied der britischen Königsfamilie, dem ein Hochschulabschluss verliehen wurde. |
| de-427-paraphrase | 0.67 | 0 | Als erstes Mitglied der britischen Königsfamilie erhielt Charles einen Hochschulabschluss. |
| de-427-clause_inserted | 0.33 | 1 | Charles war das erste Mitglied der britischen Königsfamilie, dem ein Hochschulabschluss verliehen wurde, und zwar in Geschichte. |
| de-319-identity | 0.80 | 0 | Während der letzten drei Jahrzehnte hat China eine Marktwirtschaft entwickelt, obwohl es offiziell ein kommunistischer Staat blieb. |
| de-319-clause_inserted | 0.80 | 1 | Während der letzten drei Jahrzehnte hat China eine Marktwirtschaft entwickelt, vor allem in den Küstenprovinzen, obwohl es offiziell ein kommunistischer Staat blieb. |
| de-1481-identity | 0.60 | 0 | Eine Fußsafari (auch „Buschgang“, „Wandersafari“ oder „Footing“ genannt) besteht aus einer Wanderung, die entweder ein paar Stunden oder mehrere Tage dauert. |
| de-1481-paraphrase | 0.60 | 0 | Eine Fußsafari, die man auch „Buschgang“, „Wandersafari“ oder „Footing“ nennt, ist eine Wanderung von einigen Stunden oder mehreren Tagen. |
| de-1481-clause_inserted | 0.80 | 1 | Eine Fußsafari (auch „Buschgang“, „Wandersafari“ oder „Footing“ genannt) besteht aus einer Wanderung, die entweder ein paar Stunden oder mehrere Tage dauert und immer von einem bewaffneten Ranger begleitet wird. |
| de-671-identity | 0.33 | 0 | Lizenzen sind zum Schutz des Canyons limitiert und sind ab dem Monatsersten, vier Monate vor dem Startmonat, erhältlich. |
| de-671-paraphrase | 0.67 | 0 | Um den Canyon zu schützen, ist die Zahl der Lizenzen begrenzt; sie sind ab dem ersten Tag des Monats erhältlich, der vier Monate vor dem Startmonat liegt. |
| fr-825-identity | 0.75 | 0 | Jetez un coup d’œil aux voyages dont l’agent fait la promotion, que ce soit sur un site internet ou en vitrine. |
| fr-825-paraphrase | 0.75 | 1 | Regardez les voyages que l’agent met en avant, que ce soit en vitrine ou sur un site internet. |
| fr-825-clause_inserted | 0.75 | 1 | Jetez un coup d’œil aux voyages dont l’agent fait la promotion, que ce soit sur un site internet ou en vitrine, car ils sont souvent moins chers en hiver. |
| fr-165-paraphrase | 0.50 | 1 | Il est rattaché à la septième flotte de la marine américaine, avec Sasebo (Nagasaki, Japon) comme port d'attache. |
| fr-932-paraphrase | 0.50 | 0 | D'ordinaire, il faut obtenir un visa à l'avance pour un long séjour dans un pays étranger. |
| fr-1418-identity | 0.75 | 1 | Malheureusement, l'apparition de nouveaux modes de rédaction a relégué le stylo à un statut plus confidentiel et à des utilisations plus rares. |
| fr-1418-paraphrase | 0.75 | 1 | Hélas, avec l'arrivée de nouvelles façons d'écrire, le stylo est devenu plus confidentiel et on l'utilise plus rarement. |
| fr-1418-clause_deleted | 0.50 | 1 | Malheureusement, l'apparition de nouveaux modes de rédaction a relégué le stylo à un statut plus confidentiel. |
| fr-654-paraphrase | 0.67 | 0 | Au Canada, les habitants autochtones du Groenland sont appelés Inuit ; au Groenland, on les appelle Kalaalleq (pluriel Kalaallit), Groenlandais. |
| fr-887-paraphrase | 0.50 | 0 | L’endroit le plus froid de la Terre est l’Antarctique, situé autour du pôle Sud. |
| fr-740-identity | 0.75 | 0 | L'archipel des îles Cook est un État en libre association avec la Nouvelle-Zélande, situé en Polynésie, au milieu de l'océan Pacifique sud. |
| fr-740-paraphrase | 0.75 | 1 | Situé en Polynésie, au cœur du Pacifique sud, l'archipel des îles Cook est un État librement associé à la Nouvelle-Zélande. |
| fr-740-clause_inserted | 0.75 | 1 | L'archipel des îles Cook est un État en libre association avec la Nouvelle-Zélande, situé en Polynésie, au milieu de l'océan Pacifique sud, dont la monnaie est le dollar australien. |
| fr-1069-paraphrase | 0.00 | 1 | Dans les zones isolées où il n'y a pas de réseau mobile, la téléphonie par satellite sera peut-être votre seule option. |
| fr-527-paraphrase | 0.91 | 0 | Lors d'une embuscade à l'est de Bardia, le général Lastucci, ingénieur en chef de la dixième armée italienne, a été capturé par les Britanniques. |
| fr-926-identity | 0.67 | 0 | S'il est interdit de prendre une simple photo de quelque chose, il ne faut même pas penser à en enregistrer une vidéo. |
| fr-926-paraphrase | 0.00 | 0 | Si une simple photo de quelque chose est interdite, inutile même d'envisager d'en filmer une vidéo. |
| fr-926-clause_inserted | 0.67 | 1 | S'il est interdit de prendre une simple photo de quelque chose, il ne faut même pas penser à en enregistrer une vidéo, sous peine de voir votre appareil confisqué. |
| fr-612-paraphrase | 0.33 | 1 | Les ordinateurs sont capables de produire des animations complexes, que la télévision et le cinéma utilisent de plus en plus. |
| fr-1360-identity | 1.00 | 1 | Il est presque impossible d’échanger de l’argent des Malouines en dehors des îles, alors changez-le avant de quitter les îles. |
| fr-315-paraphrase | 0.67 | 0 | Il a employé dans ses notes des mots jugés grossiers par certains parents et aurait juré en classe. |
| fr-1124-identity | 1.00 | 1 | Les réduves, tout comme les punaises de lit, sont nidicoles, c'est-à-dire adaptées pour vivre dans le nid ou l'habitat de leur hôte. |
| fr-1124-paraphrase | 1.00 | 1 | Comme les punaises de lit, les réduves sont nidicoles : elles sont adaptées à la vie dans le nid ou l'habitat de leur hôte. |
| fr-1124-clause_deleted | 1.00 | 1 | Les réduves sont nidicoles, c'est-à-dire adaptées pour vivre dans le nid ou l'habitat de leur hôte. |
| de-1136-identity | invalid | 2 judged facts instead of 3 | Das örtliche Leitungswasser kann man bedenkenlos trinken, aber wenn Sie sich Sorgen machen, finden Sie auch problemlos abgefülltes Wasser. |
| de-1136-paraphrase | invalid | 2 judged facts instead of 3 | Man kann das Leitungswasser vor Ort ohne Bedenken trinken; wer sich dennoch Sorgen macht, findet aber auch problemlos Wasser in Flaschen. |
| de-1136-clause_inserted | invalid | 2 judged facts instead of 3 | Das örtliche Leitungswasser kann man bedenkenlos trinken, aber wenn Sie sich Sorgen machen, finden Sie auch problemlos abgefülltes Wasser, das allerdings recht teuer ist. |
| de-1370-negation | invalid | 2 judged facts instead of 3 | Chambers, ein Agnostiker, argumentiert, dass seine Klage nicht „frivol“ sei und dass „jeder jeden verklagen kann“. |
| de-424-identity | invalid | 2 judged facts instead of 3 | Mit der Zeit verschmolzen viele Wörter, die aus dem Deutschen entlehnt worden waren. Das war der Beginn der Aufklärung. |
| de-424-paraphrase | invalid | 2 judged facts instead of 3 | Im Laufe der Zeit verschmolzen viele aus dem Deutschen entlehnte Wörter. Damit begann die Aufklärung. |
| de-424-clause_deleted | invalid | 2 judged facts instead of 3 | Mit der Zeit verschmolzen viele Wörter, die aus dem Deutschen entlehnt worden waren. |
| de-424-clause_inserted | invalid | 2 judged facts instead of 3 | Mit der Zeit verschmolzen viele Wörter, die aus dem Deutschen entlehnt worden waren, vor allem in der Hauptstadt. Das war der Beginn der Aufklärung. |
| de-424-negation | invalid | 2 judged facts instead of 3 | Mit der Zeit verschmolzen viele Wörter, die aus dem Deutschen entlehnt worden waren. Das war nicht der Beginn der Aufklärung. |
| fr-586-paraphrase | invalid | 2 judged facts instead of 3 | Cependant, c'est en Europe, à la fin du XVIe siècle, que furent fabriqués les premiers véritables télescopes. |
| fr-586-clause_deleted | invalid | 2 judged facts instead of 3 | Toutefois, les premiers vrais télescopes furent fabriqués en Europe. |
| fr-586-negation | invalid | 2 judged facts instead of 3 | Toutefois, les premiers vrais télescopes ne furent pas fabriqués en Europe à la fin du XVIe siècle. |
| fr-654-identity | invalid | 2 judged facts instead of 3 | Les habitants autochtones du Groenland se nomment Inuit au Canada et Kalaalleq (pluriel Kalaallit), Groenlandais, au Groenland. |
| fr-654-clause_inserted | invalid | 2 judged facts instead of 3 | Les habitants autochtones du Groenland se nomment Inuit au Canada et Kalaalleq (pluriel Kalaallit), Groenlandais, au Groenland, où ils représentent la grande majorité de la population. |
