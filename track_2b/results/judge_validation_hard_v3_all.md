# Meaning judge validation: hard controls (German)

- Date: 2026-10-10 13:33 UTC
- Git commit: 1aae5c8c936e7ecd4068f0ba32b31584b01567a0
- Judge: {"model": "qwen3-8b-q4_k_m", "endpoint": "http://127.0.0.1:8081/v1", "backend": {"type": "llama.cpp llama-server", "build_info": "b11429-d81235049", "model_path": "/Users/kaushikmukherjee/models/Qwen3-8B-GGUF/Qwen3-8B-Q4_K_M.gguf", "n_ctx": 8192}, "quantisation": "Q4_K_M", "generation": {"temperature": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}}, "seed": 0, "mode": "perfact_v3", "prompts": {"judge_facts_v1": "80c765ed80def67ca4b13456fe389ac7b8c695d2422cb4e3cc5fa73a7f0a6fe1", "judge_fact_v3": "5b74445c3470663b94c768aad4833a295a6ee67c73d61deb7591670fab4a1587", "judge_added_v3": "61d024e2989124746bdf0e220432222d69b384071873362d61f3043ec3595c54"}}
- NLI (last column and agreement): MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, mps, float32, argmax label
- TTS: none. Seeds: judge seed 0 at temperature 0 (greedy)
- n: 140 pairs, half all of data/judge_controls_de.jsonl (all = 60 German FLEURS train sentences, each paired with itself; 40 with one modal, number or qualifier change, 20 with one inserted fact, and 20 of the changed ones also with a same-meaning edit; half A tunes judge prompts, half B is held out; see isochron.judge.control_half)
- Invalid judge answers: 0
- Mean accuracy over the 6 control types: 78 %

A pair counts as judged correctly when the judge's verdict matches its control type. The last column
repeats the NLI on the same pairs (its rule: identity and same meaning kept; a changed modal, number or qualifier not kept; an inserted fact added).

| Control | Expected (judge) | DE | All | NLI, all |
|---------|------------------|---:|---:|---:|
| identity | complete: recall 1, nothing added | 100 % (60/60) | 100 % (60/60) | 92 % (55/60) |
| same_meaning | complete: recall 1, nothing added | 85 % (17/20) | 85 % (17/20) | 90 % (18/20) |
| modal_changed | not complete | 62 % (8/13) | 62 % (8/13) | 77 % (10/13) |
| number_changed | not complete | 100 % (13/13) | 100 % (13/13) | 92 % (12/13) |
| qualifier_changed | not complete | 36 % (5/14) | 36 % (5/14) | 21 % (3/14) |
| fact_inserted | something added | 85 % (17/20) | 85 % (17/20) | 100 % (20/20) |

Of the 26 changed pairs the judge does not call complete, 26 are caught through a fact marked changed or dropped, the rest only through added information.

Agreement between the judge and the NLI on "kept" (judge: recall 1 and nothing added; NLI: entailment both ways): 112/140 = 80 %.

## Pairs judged wrong (20) or invalid (0)

| Id | Recall | Added | Edit | Output |
|----|-------:|------:|------|--------|
| de-752-modal_changed | 1.00 | 0 | kann schnell zu unerwünschten Reaktionen führen → führt schnell zu unerwünschten Reaktionen | Das Aufstellen eines Zeltes auf einem Privatgrundstück oder in einer beliebig großen Stadt führt schnell zu unerwünschten Reaktionen. |
| de-1248-modal_changed | 1.00 | 0 | weil man feststellen muss → weil man feststellen kann | Es macht wohl auch das Lesen einfacher, aber das Schreiben ist einigermaßen schwierig, weil man feststellen kann, ob ein Tunwort oder Eigenschaftswort als Hauptwort verwendet wird. |
| de-914-modal_changed | 1.00 | 0 | muss man sich separat → kann man sich separat | In vielen Fällen kann man sich separat eine globale Nummer kaufen, auf die man über das öffentliche Telefonnetz angerufen werden kann. Wo die Nummer herkommt, macht für die Leute, die Sie anrufen, einen Unterschied. |
| de-847-same_meaning | 0.50 | 0 | erlernen wollen → lernen wollen | Bumerangwerfen ist eine beliebte Fertigkeit, die viele Touristen lernen wollen. |
| de-702-modal_changed | 1.00 | 0 | sollten ein ecuadorianisches Konsulat aufsuchen → müssen ein ecuadorianisches Konsulat aufsuchen | Kubanische Staatsbürger, die Inhaber einer Green Card der USA sind, müssen ein ecuadorianisches Konsulat aufsuchen, um eine Befreiung von dieser Auflage zu erhalten. |
| de-1395-modal_changed | 1.00 | 0 | sollte in der Lage sein, weitere → ist in der Lage, weitere | Ihr örtlicher Telefondienstanbieter ist in der Lage, weitere Informationen über den Anschluss an diesen Dienst zu geben. |
| de-603-same_meaning | 1.00 | 2 | aus zwei Wasserstoffatomen und einem Sauerstoffatom → aus 2 Wasserstoffatomen und 1 Sauerstoffatom | Wasser ist ein weiteres Beispiel. Die Verbindung Wasser besteht aus 2 Wasserstoffatomen und 1 Sauerstoffatom. |
| de-1147-same_meaning | 0.00 | 0 | Die Idee des Skifahrens → Die Idee des Skilaufens | Die Idee des Skilaufens ist sehr alt – Höhlenmalereien mit Darstellungen von Skifahrern gehen bis 5000 v. Chr. zurück! |
| de-227-qualifier_changed | 1.00 | 0 | nur aufgrund → aufgrund | Man weiß von ihr aufgrund ihrer Auswirkungen auf die Ausdehnung des Universums. |
| de-1186-qualifier_changed | 1.00 | 0 | eine relativ einfache → eine einfache | Die persische Sprache hat eine einfache und größtenteils regelmäßige Grammatik. |
| de-761-qualifier_changed | 1.00 | 0 | erfordert für gewöhnlich bloß → erfordert bloß | Einem solchen Netzwerk beizutreten erfordert bloß das Ausfüllen eines Online-Formulars; obwohl einige Netzwerke zusätzliche Überprüfungen anbieten oder erfordern. |
| de-380-qualifier_changed | 1.00 | 0 | weil nur die der Sonne → weil die der Sonne | Phasen treten auf, weil die der Sonne zugewandte Seite der Venus (oder des Mondes) beleuchtet wird. Die Phasen der Venus stützen die Theorie von Kopernikus, dass die Planeten um die Sonne kreisen. |
| de-262-qualifier_changed | 1.00 | 0 | hat bereits angekündigt → hat angekündigt | Nigeria hat angekündigt, dass es plant in der Woche vor dem Gipfel AfCFTA beizutreten. |
| de-579-qualifier_changed | 1.00 | 0 | dass sie oft als Bausteine → dass sie als Bausteine | Zellen werden in der Erforschung des Lebens als so grundlegend und entscheidend angesehen, dass sie als Bausteine des Lebens bezeichnet werden. |
| de-1105-qualifier_changed | 1.00 | 0 | viele der kleineren Pyramiden → alle kleineren Pyramiden | Die große Pyramide wurde dem Pharao Cheops zu Ehren erbaut und alle kleineren Pyramiden, Grabmale und Tempel wurden zu Ehren von Cheops Ehefrauen und Familienmitgliedern errichtet. |
| de-992-qualifier_changed | 1.00 | 0 | rollen möglicherweise weiter → rollen weiter | Am Rande von Gletschern brechen riesige Blöcke ab, fallen herunter und springen oder rollen weiter vom Rand weg. |
| de-977-qualifier_changed | 1.00 | 0 | die sich sonst nur schwer → die sich nur schwer | Hilfssprachen sind künstliche oder konstruierte Sprachen, die mit dem Ziel geschaffen werden, die Kommunikation zwischen Völkern zu erleichtern, die sich nur schwer verständigen könnten. |
| de-771-fact_inserted | 1.00 | 0 | werden im Rahmen → werden jährlich im Rahmen | Die meisten Tempelfeste werden jährlich im Rahmen des Tempeljubiläums, des Geburtstags der obersten Gottheit oder anderer wichtiger Ereignisse im Zusammenhang mit dem Tempel gefeiert. |
| de-538-fact_inserted | 1.00 | 0 | als kultureller Tourismus bezeichnet → von Fachleuten als kultureller Tourismus bezeichnet | Wenn das Ziel des Besuches eines bestimmten Ortes ist, seine Geschichte und Kultur zu erfahren, dann wird diese Art des Tourismus von Fachleuten als kultureller Tourismus bezeichnet. |
| de-1093-fact_inserted | 1.00 | 0 | die jede Katze hat → die jede Katze von Geburt an hat | Das Geheimnis ihres Erfolgs ist das Konzept der Nische, eine besondere Aufgabe, die jede Katze von Geburt an hat und die dafür sorgt, dass sie nicht mit anderen konkurriert. |
