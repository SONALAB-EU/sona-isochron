# Meaning judge validation: hard controls (German), English sources (cross-lingual)

- Date: 2026-10-12 11:37 UTC
- Git commit: 7b22d93e7e052f8272d7a033db73d74abc479388 (synced copy, recorded by hpc/sync.sh)
- Judge: {"model": "qwen3-14b-bf16", "endpoint": "http://127.0.0.1:50193/v1", "backend": {"type": "vLLM", "build_info": "vLLM 0.23.1rc1.dev1029+ga601a9d99", "model_path": "/sc/home/kaushik.mukherjee/isochron_work/models/Qwen/Qwen3-14B", "max_model_len": 8192}, "quantisation": "BF16", "generation": {"temperature": 0.0, "max_tokens": 1024, "chat_template_kwargs": {"enable_thinking": false}}, "seed": 0, "mode": "perfact_v3", "prompts": {"judge_facts_v1": "80c765ed80def67ca4b13456fe389ac7b8c695d2422cb4e3cc5fa73a7f0a6fe1", "judge_fact_v3": "5b74445c3470663b94c768aad4833a295a6ee67c73d61deb7591670fab4a1587", "judge_added_v3": "61d024e2989124746bdf0e220432222d69b384071873362d61f3043ec3595c54"}}
- NLI (last column and agreement): MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, cuda, float32, argmax label
- TTS: none. Seeds: judge seed 0 at temperature 0 (greedy)
- n: 140 pairs, half all of data/judge_controls_xl.jsonl (all = the hard suite with each source replaced by its English original (cross-lingual); half A tunes judge prompts, half B is held out; see isochron.judge.control_half)
- Invalid judge answers: 0
- Mean accuracy over the 6 control types: 58 %

A pair counts as judged correctly when the judge's verdict matches its control type. The last column
repeats the NLI on the same pairs (its rule: identity and same meaning kept; a changed modal, number or qualifier not kept; an inserted fact added).

| Control | Expected (judge) | DE | All | NLI, all |
|---------|------------------|---:|---:|---:|
| identity | complete: recall 1, nothing added | 100 % (60/60) | 100 % (60/60) | 87 % (52/60) |
| same_meaning | complete: recall 1, nothing added | 100 % (20/20) | 100 % (20/20) | 80 % (16/20) |
| modal_changed | not complete | 31 % (4/13) | 31 % (4/13) | 54 % (7/13) |
| number_changed | not complete | 92 % (12/13) | 92 % (12/13) | 92 % (12/13) |
| qualifier_changed | not complete | 0 % (0/14) | 0 % (0/14) | 43 % (6/14) |
| fact_inserted | something added | 25 % (5/20) | 25 % (5/20) | 100 % (20/20) |

Of the 16 changed pairs the judge does not call complete, 16 are caught through a fact marked changed or dropped, the rest only through added information.

Agreement between the judge and the NLI on "kept" (judge: recall 1 and nothing added; NLI: entailment both ways): 99/140 = 71 %.

## Pairs judged wrong (39) or invalid (0)

| Id | Recall | Added | Edit | Output |
|----|-------:|------:|------|--------|
| xl-de-1237-modal_changed | 1.00 | 0 | übernehmen kann. → übernehmen muss. | Bei einer Adoption geben die leiblichen Eltern ihre Elternrechte auf, so dass ein anderes Paar die Elternschaft übernehmen muss. |
| xl-de-1427-modal_changed | 1.00 | 0 | eine Diagnose stellen kann → eine Diagnose stellen darf | Eine innere Vergiftung lässt sich möglicherweise nicht sofort erkennen. Die Symptome, beispielsweise Erbrechen, sind so allgemein, dass man nicht sofort eine Diagnose stellen darf. |
| xl-de-1248-modal_changed | 1.00 | 0 | weil man feststellen muss → weil man feststellen kann | Es macht wohl auch das Lesen einfacher, aber das Schreiben ist einigermaßen schwierig, weil man feststellen kann, ob ein Tunwort oder Eigenschaftswort als Hauptwort verwendet wird. |
| xl-de-914-modal_changed | 1.00 | 0 | muss man sich separat → kann man sich separat | In vielen Fällen kann man sich separat eine globale Nummer kaufen, auf die man über das öffentliche Telefonnetz angerufen werden kann. Wo die Nummer herkommt, macht für die Leute, die Sie anrufen, einen Unterschied. |
| xl-de-939-modal_changed | 1.00 | 0 | kann die Zollkontrolle ein Ärgernis sein → ist die Zollkontrolle ein Ärgernis | Während es normalerweise keine Einreisekontrolle bei der Ankunft in Ihrem Heimatland gibt oder dies lediglich eine Formalität ist, ist die Zollkontrolle ein Ärgernis. |
| xl-de-702-modal_changed | 1.00 | 0 | sollten ein ecuadorianisches Konsulat aufsuchen → müssen ein ecuadorianisches Konsulat aufsuchen | Kubanische Staatsbürger, die Inhaber einer Green Card der USA sind, müssen ein ecuadorianisches Konsulat aufsuchen, um eine Befreiung von dieser Auflage zu erhalten. |
| xl-de-1006-modal_changed | 1.00 | 0 | betreten werden durfte → betreten wurde | Jeder Tempel hatte einen offenen Tempelhof und dann einen inneren Altarraum, der nur von Priestern betreten wurde. |
| xl-de-1017-modal_changed | 1.00 | 0 | sollte bis zum 16. September durch die Vereinigten Staaten und Kanada touren → tourte bis zum 16. September durch die Vereinigten Staaten und Kanada | Die Rockband tourte bis zum 16. September durch die Vereinigten Staaten und Kanada. |
| xl-de-1395-modal_changed | 1.00 | 0 | sollte in der Lage sein, weitere → ist in der Lage, weitere | Ihr örtlicher Telefondienstanbieter ist in der Lage, weitere Informationen über den Anschluss an diesen Dienst zu geben. |
| xl-de-1458-number_changed | 1.00 | 0 | mehr als 100 Fuß → 100 Fuß | Es bedarf einer gigantischen Rakete mit einer Höhe von 100 Fuß, um einen Satelliten oder ein Teleskop in den Weltraum zu schießen. |
| xl-de-464-qualifier_changed | 1.00 | 0 | höchstwahrscheinlich auch → auch | Leider werden die Ränder auch abgeschnitten, wenn man eine DVD macht, und wenn im Video die Untertitel zu nahe am unteren Rand stehen, werden sie nicht vollständig angezeigt. |
| xl-de-227-qualifier_changed | 1.00 | 0 | nur aufgrund → aufgrund | Man weiß von ihr aufgrund ihrer Auswirkungen auf die Ausdehnung des Universums. |
| xl-de-1186-qualifier_changed | 1.00 | 0 | eine relativ einfache → eine einfache | Die persische Sprache hat eine einfache und größtenteils regelmäßige Grammatik. |
| xl-de-761-qualifier_changed | 1.00 | 0 | erfordert für gewöhnlich bloß → erfordert bloß | Einem solchen Netzwerk beizutreten erfordert bloß das Ausfüllen eines Online-Formulars; obwohl einige Netzwerke zusätzliche Überprüfungen anbieten oder erfordern. |
| xl-de-380-qualifier_changed | 1.00 | 0 | weil nur die der Sonne → weil die der Sonne | Phasen treten auf, weil die der Sonne zugewandte Seite der Venus (oder des Mondes) beleuchtet wird. Die Phasen der Venus stützen die Theorie von Kopernikus, dass die Planeten um die Sonne kreisen. |
| xl-de-262-qualifier_changed | 1.00 | 0 | hat bereits angekündigt → hat angekündigt | Nigeria hat angekündigt, dass es plant in der Woche vor dem Gipfel AfCFTA beizutreten. |
| xl-de-714-qualifier_changed | 1.00 | 0 | Die meisten Menschen buchen → Die Menschen buchen | Die Menschen buchen ihren Platz lange im Voraus (da die Boote während der Hochsaison normalerweise voll sind). |
| xl-de-999-qualifier_changed | 1.00 | 0 | Aber unabhängig → Unabhängig | Unabhängig von seiner Entdeckung lebten Eskimo-Stämme dort bereits zu jener Zeit. |
| xl-de-579-qualifier_changed | 1.00 | 0 | dass sie oft als Bausteine → dass sie als Bausteine | Zellen werden in der Erforschung des Lebens als so grundlegend und entscheidend angesehen, dass sie als Bausteine des Lebens bezeichnet werden. |
| xl-de-1105-qualifier_changed | 1.00 | 0 | viele der kleineren Pyramiden → alle kleineren Pyramiden | Die große Pyramide wurde dem Pharao Cheops zu Ehren erbaut und alle kleineren Pyramiden, Grabmale und Tempel wurden zu Ehren von Cheops Ehefrauen und Familienmitgliedern errichtet. |
| xl-de-992-qualifier_changed | 1.00 | 0 | rollen möglicherweise weiter → rollen weiter | Am Rande von Gletschern brechen riesige Blöcke ab, fallen herunter und springen oder rollen weiter vom Rand weg. |
| xl-de-778-qualifier_changed | 1.00 | 0 | ist am verbreitetsten → ist verbreitet | Im Laufe der Jahre wurden viele verschiedene Filmformate verwendet. Der normale 35-mm-Film (Negative mit Maßen von 36 x 24 mm) ist verbreitet. |
| xl-de-977-qualifier_changed | 1.00 | 0 | die sich sonst nur schwer → die sich nur schwer | Hilfssprachen sind künstliche oder konstruierte Sprachen, die mit dem Ziel geschaffen werden, die Kommunikation zwischen Völkern zu erleichtern, die sich nur schwer verständigen könnten. |
| xl-de-1063-qualifier_changed | 1.00 | 0 | der Personenkraftwagen unumgänglich die Entwicklung → der Personenkraftwagen die Entwicklung | Man kann etwa behaupten, dass der Personenkraftwagen die Entwicklung von Straßen mit sich bringt. |
| xl-de-865-fact_inserted | 1.00 | 0 | Montezumas Rache → Montezumas Rache in Mexiko | Daher die Geißeln von Delhi Belly, der Pharaonenfluch, Montezumas Rache in Mexiko und ihre vielen Freunde. |
| xl-de-268-fact_inserted | 1.00 | 0 | Der Fall wurde in Virginia → Der Fall wurde 2003 in Virginia | Der Fall wurde 2003 in Virginia strafrechtlich verfolgt, weil dort der führende Internetserviceanbieter AOL seinen Sitz hat, die Firma, die die Klage auf den Weg gebracht hat. |
| xl-de-738-fact_inserted | 1.00 | 0 | stellt Genehmigungen → stellt kostenpflichtige Genehmigungen | Die Parkverwaltung (MINAE) stellt kostenpflichtige Genehmigungen  für den Park nicht früher als einen Monat vor der geplanten Ankunft aus. |
| xl-de-518-fact_inserted | 1.00 | 0 | des Schimpansen → des erwachsenen Schimpansen | Die Hand und der Fuß des erwachsenen Schimpansen sind von ähnlicher Größe und Länge, was die Verwendung der Hand zur Gewichtsbelastung beim Knöchelgang widerspiegelt. |
| xl-de-1272-fact_inserted | 1.00 | 0 | von Orangutangs in Borneo → von Orangutangs im Regenwald von Borneo | Ein Beispiel dafür ist der Besuch, das Fotografieren und das Studieren von Orangutangs im Regenwald von Borneo. |
| xl-de-771-fact_inserted | 1.00 | 0 | werden im Rahmen → werden jährlich im Rahmen | Die meisten Tempelfeste werden jährlich im Rahmen des Tempeljubiläums, des Geburtstags der obersten Gottheit oder anderer wichtiger Ereignisse im Zusammenhang mit dem Tempel gefeiert. |
| xl-de-538-fact_inserted | 1.00 | 0 | als kultureller Tourismus bezeichnet → von Fachleuten als kultureller Tourismus bezeichnet | Wenn das Ziel des Besuches eines bestimmten Ortes ist, seine Geschichte und Kultur zu erfahren, dann wird diese Art des Tourismus von Fachleuten als kultureller Tourismus bezeichnet. |
| xl-de-363-fact_inserted | 1.00 | 0 | in der Glühbirne irgendwann aus → in der Glühbirne wegen der Hitze irgendwann aus | Nach hunderten Betriebsstunden brennt der Glühfaden in der Glühbirne wegen der Hitze irgendwann aus und die Glühbirne funktioniert nicht mehr. |
| xl-de-880-fact_inserted | 0.00 | 0 | impfen lassen → kostenlos impfen lassen | Viele Regierungen fordern von einreisenden Besuchern oder abreisenden Einwohnern in ihren Ländern, dass sie sich gegen eine Reihe von Krankheiten kostenlos impfen lassen. |
| xl-de-742-fact_inserted | 1.00 | 0 | werden die Inseln manchmal → werden die Inseln von Touristen manchmal | Mit der gleichen Zeitzone wie Hawaii werden die Inseln von Touristen manchmal als „Hawaii Down Under“ bezeichnet. |
| xl-de-293-fact_inserted | 1.00 | 0 | wurden am Fuß des Berges gemeldet → wurden am Montagmorgen am Fuß des Berges gemeldet | Dunkle Wolken ohne Zusammenhang mit jeglicher vulkanischer Aktivität wurden am Montagmorgen am Fuß des Berges gemeldet. |
| xl-de-1425-fact_inserted | 1.00 | 0 | dass der Baum → dass der 150 Jahre alte Baum | Beamte der Stadt Amsterdam und des Anne-Frank-Museums geben an, dass der 150 Jahre alte Baum mit einem Pilz infiziert ist und eine Gefahr für die öffentliche Gesundheit darstellt, da er jederzeit umfallen könne. |
| xl-de-933-fact_inserted | 1.00 | 0 | andere Anforderungen → andere und strengere Anforderungen | Studierendenvisa haben grundsätzlich andere und strengere Anforderungen und Bewerbungsverfahren als normale Touristen- oder Geschäftsvisa. |
| xl-de-1036-fact_inserted | 1.00 | 0 | Das Hershey-Chase-Experiment → Das Hershey-Chase-Experiment von 1952 | Das Hershey-Chase-Experiment von 1952 war eines der maßgeblichen Indizien, dass DNA ein genetisches Material ist. |
| xl-de-1093-fact_inserted | 1.00 | 0 | die jede Katze hat → die jede Katze von Geburt an hat | Das Geheimnis ihres Erfolgs ist das Konzept der Nische, eine besondere Aufgabe, die jede Katze von Geburt an hat und die dafür sorgt, dass sie nicht mit anderen konkurriert. |
