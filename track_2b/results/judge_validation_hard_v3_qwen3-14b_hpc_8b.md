# Meaning judge validation: hard controls (German)

- Date: 2026-10-10 18:21 UTC
- Git commit: 5820d9d6adf8a93ccb88793a7ff5079b9bea1843 (added by hand: the job ran in an rsync copy, not a git checkout, so the generated line said unknown; after the job, every synced file was checked identical to this commit with rsync --checksum, and the code has not changed since 1f71399)
- Judge: {"model": "qwen3-14b-bf16", "endpoint": "http://127.0.0.1:48211/v1", "backend": {"type": "vLLM", "build_info": "vLLM 0.23.1rc1.dev1029+ga601a9d99", "model_path": "/sc/home/kaushik.mukherjee/isochron_work/models/Qwen/Qwen3-14B", "max_model_len": 8192}, "quantisation": "BF16", "generation": {"temperature": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}}, "seed": 0, "mode": "perfact_v3", "prompts": {"judge_facts_v1": "80c765ed80def67ca4b13456fe389ac7b8c695d2422cb4e3cc5fa73a7f0a6fe1", "judge_fact_v3": "5b74445c3470663b94c768aad4833a295a6ee67c73d61deb7591670fab4a1587", "judge_added_v3": "61d024e2989124746bdf0e220432222d69b384071873362d61f3043ec3595c54"}}
- NLI (last column and agreement): MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, cuda, float32, argmax label
- TTS: none. Seeds: judge seed 0 at temperature 0 (greedy)
- n: 140 pairs, half all of data/judge_controls_de.jsonl (all = 60 German FLEURS train sentences, each paired with itself; 40 with one modal, number or qualifier change, 20 with one inserted fact, and 20 of the changed ones also with a same-meaning edit; half A tunes judge prompts, half B is held out; see isochron.judge.control_half)
- Invalid judge answers: 0
- Mean accuracy over the 6 control types: 84 %

A pair counts as judged correctly when the judge's verdict matches its control type. The last column
repeats the NLI on the same pairs (its rule: identity and same meaning kept; a changed modal, number or qualifier not kept; an inserted fact added).

| Control | Expected (judge) | DE | All | NLI, all |
|---------|------------------|---:|---:|---:|
| identity | complete: recall 1, nothing added | 100 % (60/60) | 100 % (60/60) | 92 % (55/60) |
| same_meaning | complete: recall 1, nothing added | 100 % (20/20) | 100 % (20/20) | 90 % (18/20) |
| modal_changed | not complete | 77 % (10/13) | 77 % (10/13) | 77 % (10/13) |
| number_changed | not complete | 100 % (13/13) | 100 % (13/13) | 92 % (12/13) |
| qualifier_changed | not complete | 50 % (7/14) | 50 % (7/14) | 21 % (3/14) |
| fact_inserted | something added | 80 % (16/20) | 80 % (16/20) | 100 % (20/20) |

Of the 30 changed pairs the judge does not call complete, 30 are caught through a fact marked changed or dropped, the rest only through added information.

Agreement between the judge and the NLI on "kept" (judge: recall 1 and nothing added; NLI: entailment both ways): 120/140 = 86 %.

## Pairs judged wrong (14) or invalid (0)

| Id | Recall | Added | Edit | Output |
|----|-------:|------:|------|--------|
| de-752-modal_changed | 1.00 | 0 | kann schnell zu unerwünschten Reaktionen führen → führt schnell zu unerwünschten Reaktionen | Das Aufstellen eines Zeltes auf einem Privatgrundstück oder in einer beliebig großen Stadt führt schnell zu unerwünschten Reaktionen. |
| de-939-modal_changed | 1.00 | 0 | kann die Zollkontrolle ein Ärgernis sein → ist die Zollkontrolle ein Ärgernis | Während es normalerweise keine Einreisekontrolle bei der Ankunft in Ihrem Heimatland gibt oder dies lediglich eine Formalität ist, ist die Zollkontrolle ein Ärgernis. |
| de-1006-modal_changed | 1.00 | 0 | betreten werden durfte → betreten wurde | Jeder Tempel hatte einen offenen Tempelhof und dann einen inneren Altarraum, der nur von Priestern betreten wurde. |
| de-1186-qualifier_changed | 1.00 | 0 | eine relativ einfache → eine einfache | Die persische Sprache hat eine einfache und größtenteils regelmäßige Grammatik. |
| de-761-qualifier_changed | 1.00 | 0 | erfordert für gewöhnlich bloß → erfordert bloß | Einem solchen Netzwerk beizutreten erfordert bloß das Ausfüllen eines Online-Formulars; obwohl einige Netzwerke zusätzliche Überprüfungen anbieten oder erfordern. |
| de-380-qualifier_changed | 1.00 | 0 | weil nur die der Sonne → weil die der Sonne | Phasen treten auf, weil die der Sonne zugewandte Seite der Venus (oder des Mondes) beleuchtet wird. Die Phasen der Venus stützen die Theorie von Kopernikus, dass die Planeten um die Sonne kreisen. |
| de-262-qualifier_changed | 1.00 | 0 | hat bereits angekündigt → hat angekündigt | Nigeria hat angekündigt, dass es plant in der Woche vor dem Gipfel AfCFTA beizutreten. |
| de-999-qualifier_changed | 1.00 | 0 | Aber unabhängig → Unabhängig | Unabhängig von seiner Entdeckung lebten Eskimo-Stämme dort bereits zu jener Zeit. |
| de-579-qualifier_changed | 1.00 | 0 | dass sie oft als Bausteine → dass sie als Bausteine | Zellen werden in der Erforschung des Lebens als so grundlegend und entscheidend angesehen, dass sie als Bausteine des Lebens bezeichnet werden. |
| de-977-qualifier_changed | 1.00 | 0 | die sich sonst nur schwer → die sich nur schwer | Hilfssprachen sind künstliche oder konstruierte Sprachen, die mit dem Ziel geschaffen werden, die Kommunikation zwischen Völkern zu erleichtern, die sich nur schwer verständigen könnten. |
| de-1272-fact_inserted | 1.00 | 0 | von Orangutangs in Borneo → von Orangutangs im Regenwald von Borneo | Ein Beispiel dafür ist der Besuch, das Fotografieren und das Studieren von Orangutangs im Regenwald von Borneo. |
| de-538-fact_inserted | 1.00 | 0 | als kultureller Tourismus bezeichnet → von Fachleuten als kultureller Tourismus bezeichnet | Wenn das Ziel des Besuches eines bestimmten Ortes ist, seine Geschichte und Kultur zu erfahren, dann wird diese Art des Tourismus von Fachleuten als kultureller Tourismus bezeichnet. |
| de-363-fact_inserted | 1.00 | 0 | in der Glühbirne irgendwann aus → in der Glühbirne wegen der Hitze irgendwann aus | Nach hunderten Betriebsstunden brennt der Glühfaden in der Glühbirne wegen der Hitze irgendwann aus und die Glühbirne funktioniert nicht mehr. |
| de-1093-fact_inserted | 1.00 | 0 | die jede Katze hat → die jede Katze von Geburt an hat | Das Geheimnis ihres Erfolgs ist das Konzept der Nische, eine besondere Aufgabe, die jede Katze von Geburt an hat und die dafür sorgt, dass sie nicht mit anderen konkurriert. |
