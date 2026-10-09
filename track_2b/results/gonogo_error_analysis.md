# Error analysis of the go/no-go outputs (closest candidate)

Analysis only: the go/no-go result is final and is not re-scored.

- Date: 2026-10-09 15:27 UTC
- Git commit: c0dcbcbcbd50f060d8d6b80ee13fa288c2bb2270
- Run: `results/raw/20261009T141318Z_step2_de_dev_syllables` (Apertus 1.5 8B Q4_K_M, prompt v1, seeds 0/1/2, level 80 %); model, endpoint and generation settings as in `results/gonogo_step2_de.md`; TTS: none
- n: 149 outputs with a usable answer; 67 flagged as dropped by the NLI; 30 of those drawn with `random.Random(0)` after sorting by (id, seed)
- Annotators: annotator-A, annotator-B, annotator-C. Three independent LLM annotators (Claude agents), each reading all 30 cases in a different order, without seeing the others; not native speakers.

## Achieved ÷ target syllables

| Achieved ÷ target | Outputs | |
|------------------:|--------:|-|
| < 0.40 | 0 |  |
| 0.40–0.45 | 0 |  |
| 0.45–0.50 | 7 | ███████ |
| 0.50–0.55 | 2 | ██ |
| 0.55–0.60 | 3 | ███ |
| 0.60–0.65 | 8 | ████████ |
| 0.65–0.70 | 9 | █████████ |
| 0.70–0.75 | 12 | ████████████ |
| 0.75–0.80 | 13 | █████████████ |
| 0.80–0.85 | 12 | ████████████ |
| 0.85–0.90 | 20 | ████████████████████ |
| 0.90–0.95 | 23 | ███████████████████████ ← fit band |
| 0.95–1.00 | 10 | ██████████ ← fit band |
| 1.00–1.05 | 22 | ██████████████████████ ← fit band |
| 1.05–1.10 | 6 | ██████ ← fit band |
| 1.10–1.15 | 0 |  |
| 1.15–1.20 | 2 | ██ |
| 1.20–1.25 | 0 |  |
| 1.25–1.30 | 0 |  |
| ≥ 1.30 | 0 |  |

n = 149; median 0.87 (quartiles 0.74–0.95); below 0.90: 86, within 0.90–1.10: 61, above 1.10: 2. (Fit uses integer arithmetic, so outputs exactly on 0.90 or 1.10 count as fits.)

## What was lost in 30 dropped cases

A case can lose several kinds of information. A category counts when at least 2 of the 3 annotators
chose it; `none` means the annotators found nothing lost (an NLI false alarm).

| Category | Cases (majority) | Share of the 30 | Pairwise agreement |
|----------|-----------------:|----------------:|-------------------:|
| number | 0 | 0 % | 100 % |
| name | 3 | 10 % | 98 % |
| date | 2 | 7 % | 100 % |
| clause | 10 | 33 % | 93 % |
| qualifier | 24 | 80 % | 96 % |
| other | 16 | 53 % | 84 % |
| none | 0 | 0 % | 100 % |

Definitions given to the annotators: Categories (choose all that apply; "lost" also covers information that is changed into something with a different meaning): number: a quantity, count, measurement, percentage or other numeral (e.g. "40", "zehn", "Millionen"). name: a proper name of a person, place, organisation, event, work or title. date: a date, year, time of day, period or duration ("1979", "seit drei Jahren", "im Sommer"). clause: a whole proposition that is gone entirely: an event, action, reason, purpose, condition, consequence, or an item of a list. qualifier: a word or phrase that grades, limits or specifies a claim that is otherwise kept: adjectives, adverbs, hedges, quantifiers, comparatives ("fast", "sehr", "lokal", "insbesondere", "vor allem", "relativ"). other: anything else lost or changed in meaning (e.g. a changed agent or relation, a modality such as "verlangt" becoming "sieht vor", a wrong word). none: nothing from the input is missing or changed in the output (the NLI "dropped" flag is a false alarm). Use "none" only alone.

## Cases

| # | Id | Seed | Target | Syll. | Lost (majority) | What was lost (one note per annotator) |
|--:|---:|-----:|-------:|------:|-----------------|----------------------------------------|
| 1 | 1522 | 1 | 42 | 40 | clause, qualifier, other | 'Virtuelle Exkursionen stellen eine technische Lösung dar' gone and 'virtuelle' became 'Technische Ausflüge'; 'schöne' and 'vom Klassenzimmer aus' lost; 'ein Aquarium besuchen' became 'Tiere'; modal 'können' dropped / 'Virtuelle Exkursionen stellen eine technische Lösung dar' became 'Technische Ausflüge' ('virtuelle' and the 'Lösung' claim lost); 'vom Klassenzimmer aus' and 'schöne' dropped; 'ein Aquarium besuchen' became 'Tiere'; 'können' lost / 'stellen eine technische Lösung dar' lost; 'Virtuelle' became 'Technische'; 'vom Klassenzimmer aus', 'schöne' and modal 'können' lost; 'ein Aquarium besuchen' became 'Tiere' |
| 2 | 1536 | 1 | 42 | 32 | qualifier, other | 'lokalen' and 'in der Nähe der Anlage' lost; 'ermahnen ... dazu' became 'warnen' (can read as warn against); 'sich innerhalb von Gebäuden aufzuhalten' became 'Gebäude zu nutzen' / 'lokalen' and 'in der Nähe der Anlage' dropped; 'sich innerhalb von Gebäuden aufzuhalten' became 'Gebäude zu nutzen' (use buildings) / 'lokalen' and 'in der Nähe der Anlage' lost; 'ermahnen … sich innerhalb von Gebäuden aufzuhalten' became 'warnen …, Gebäude zu nutzen' |
| 3 | 1536 | 2 | 42 | 37 | qualifier | 'lokalen' and 'in der Nähe der Anlage' lost; 'ermahnen' became the wrong verb 'fordern ... an' (anfordern = requisition, not auffordern) / 'lokalen' and 'in der Nähe der Anlage' dropped ('fordern ... an' is a slip for 'auffordern', meaning recoverable) / 'lokalen' and 'in der Nähe der Anlage' lost ('fordern … an' is a slip for 'auffordern', meaning kept) |
| 4 | 1546 | 0 | 71 | 35 | clause, qualifier | List item 'oder zum Herzeigen' and clause 'obwohl es sich um den Schwanz eines jungen Dinosauriers handelt' lost; hedges 'eher' and 'Die Forscher vermuteten' lost; 'Daunen' generalised to 'Kükenfedern' / 'oder zum Herzeigen' and 'obwohl es sich um den Schwanz eines jungen Dinosauriers handelt' dropped; hedges 'eher' and 'Die Forscher vermuteten' dropped; 'Daunen' generalised to 'Kükenfedern' / 'oder zum Herzeigen', 'Die Forscher vermuteten' and the whole 'obwohl … Schwanz eines jungen Dinosauriers' clause lost; 'eher' lost; 'Daunen' became generic 'Federn' |
| 5 | 1546 | 1 | 71 | 46 | clause, qualifier, other | List item 'oder zum Herzeigen' lost; 'eher' and 'Die Forscher vermuteten' lost; concessive 'obwohl' reduced to apposition 'ein junger Dinosaurierschwanz'; 'nicht zum Fliegen verwendet' became 'nicht auf Flugfähigkeit' / 'oder zum Herzeigen' dropped; hedges 'eher' and 'Die Forscher vermuteten' dropped; concessive 'obwohl' reduced to a plain apposition / 'oder zum Herzeigen' and 'Die Forscher vermuteten' lost; 'eher' lost; concessive 'obwohl' reduced to an apposition ('ein junger Dinosaurierschwanz') |
| 6 | 1551 | 2 | 29 | 23 | name, other | 'die Erde' lost: 'wie die Erde davon beeinträchtigt werden wird' became generic 'dessen Auswirkungen' / 'wie die Erde davon beeinträchtigt werden wird' reduced to 'dessen Auswirkungen' ('die Erde' lost); agent 'Sie' dropped by passive 'werden ... untersucht' / 'die Erde' lost (effects on what is unstated); subject 'Sie' dropped via passive; future 'beeinträchtigt werden wird' lost |
| 7 | 1556 | 1 | 45 | 34 | name, qualifier | Title 'Rühmliche Heldentaten schwedischer Könige' became 'Gemälde schwedischer Könige'; 'David Klöcker' dropped, 'Ehrenstrahl' misspelt 'Ehrenstrahß'; 'Guinness-Buch der Rekorde' cut to 'Guinness-Buch'; 'prächtige' lost / Title 'Rühmliche Heldentaten schwedischer Könige' cut to 'Gemälde schwedischer Könige'; 'David Klöcker' dropped and 'Ehrenstrahl' misspelt 'Ehrenstrahß'; 'der Rekorde' dropped; 'prächtige' dropped / painting title 'Rühmliche Heldentaten …' and 'David Klöcker' lost, 'Ehrenstrahl' misspelt 'Ehrenstrahß'; 'prächtige' lost |
| 8 | 1562 | 0 | 20 | 17 | clause, other | 'Dies wurde üblich' (with 'doch') lost; 'das Eisen sorgte für mehr Verschleiß an den hölzernen Rädern' became 'Wagenräder tragen stärkeren Eisenverschleiß' (wear of the iron); past became present / 'Dies wurde üblich, doch' dropped; 'das Eisen sorgte für mehr Verschleiß an den hölzernen Rädern' became 'tragen stärkeren Eisenverschleiß' (iron no longer the cause); past 'sorgte' became present / 'Dies wurde üblich' lost; 'das Eisen sorgte für mehr Verschleiß an den … Rädern' became 'Wagenräder tragen stärkeren Eisenverschleiß' (cause garbled, past became present) |
| 9 | 1562 | 1 | 20 | 18 | clause, other | 'Dies wurde üblich' lost; past, specific 'das Eisen sorgte' became present, generic 'Eisen verursacht' / 'Dies wurde üblich, doch' dropped; past 'das Eisen sorgte' became generic present 'Eisen verursacht' / 'Dies wurde üblich' lost; past 'das Eisen sorgte' became generic present 'Eisen verursacht' |
| 10 | 1567 | 0 | 19 | 17 | qualifier, other | 'größte ... des Jahres' lost; 'findet ... auf ... statt' became the wrong verb 'stattet' (garbled, 'auf' lost) / 'größte' and 'des Jahres' dropped; 'findet ... auf ... statt' garbled into 'stattet' with no preposition / 'größte … des Jahres' lost ('stattet' is a garbled 'findet … statt', meaning still recoverable) |
| 11 | 1567 | 1 | 19 | 14 | qualifier, other | 'größte' and 'Polofeldern' lost; 'Turnier des Jahres' became 'Jahresturnier' (annual); 'findet im Dezember statt' became 'spielt Dezember' / 'größte' dropped; 'Turnier des Jahres' became 'Jahresturnier' (annual tournament); 'Polofeldern' dropped / 'größte' and 'Polofeldern' lost (only 'Las Cañitas' remains) |
| 12 | 1571 | 2 | 23 | 18 | clause, qualifier, other | 'auf den Komoren und in Mayotte war er sehr erfolgreich' lost; 'auch' lost; destination 'ins Land' replaced by 'nach Komoren und Mayotte' / 'auf den Komoren und in Mayotte war er sehr erfolgreich' dropped; 'auch' dropped; 'ins Land' replaced by 'nach Komoren und Mayotte' / 'war er sehr erfolgreich' and 'auch' lost; 'ins Land' replaced by 'nach Komoren und Mayotte' (destination changed) |
| 13 | 1575 | 2 | 47 | 32 | date | 'ab der Unterzeichnung der Vereinbarung' lost; 'will ... akzeptieren' became 'akzeptiert'; 'hingegen' dropped / 'ab der Unterzeichnung der Vereinbarung' (start point of the ten years) dropped / 'ab der Unterzeichnung der Vereinbarung' lost (start point of the ten years) |
| 14 | 1577 | 0 | 11 | 5 | clause, qualifier | 'Das erschien mir nicht sinnvoll' lost; 'ganz gewiss' lost / 'Das erschien mir nicht sinnvoll' dropped; 'ganz gewiss' dropped / 'Das erschien mir nicht sinnvoll' and intensifier 'ganz gewiss' lost |
| 15 | 1582 | 0 | 20 | 18 | other | 'der hebräischen Familie' became 'jüdische Familienleben' (Hebrew changed to Jewish) / 'hebräischen' changed to 'jüdische' (Hebrew became Jewish) / 'hebräischen' changed to 'jüdische' |
| 16 | 1582 | 1 | 20 | 15 | qualifier | 'hebräischen' lost ('der hebräischen Familie' became 'die Familie') / 'hebräischen' dropped / 'hebräischen' lost |
| 17 | 1582 | 2 | 20 | 20 | qualifier | 'hebräischen' lost; 'Der größte Teil' weakened to 'Vieles' / 'hebräischen' dropped; 'Der größte Teil' weakened to 'Vieles' / 'hebräischen' lost; 'Der größte Teil' weakened to 'Vieles' |
| 18 | 1583 | 2 | 58 | 49 | clause, qualifier, other | 'die darauf drängten, dass Verhütungsmittel als medizinische Notwendigkeit angesehen werden sollten' lost, its content moved into her 'Schlussfolgerung'; 'sowohl von Männern als auch von Frauen' became 'beiderseitige' / 'sowohl von Männern als auch von Frauen' became 'beiderseitige' (mutual); 'die darauf drängten, dass ...' dropped and its content recast as the topic of 'ihrer Schlussfolgerung' / 'sowohl von Männern als auch von Frauen' became vague 'beiderseitige'; 'die darauf drängten, dass … angesehen werden sollten' lost, its content moved into 'ihrer Schlussfolgerung' |
| 19 | 1588 | 0 | 25 | 25 | qualifier | Attribution 'Laut Polizei' lost / Attribution 'Laut Polizei' dropped / attribution 'Laut Polizei' lost |
| 20 | 1588 | 1 | 25 | 25 | qualifier | Attribution 'Laut Polizei' lost / Attribution 'Laut Polizei' dropped / attribution 'Laut Polizei' lost |
| 21 | 1601 | 1 | 38 | 22 | clause, other | Second sentence 'Sie schnuppern danach, wo sie sich am Boden aufgehalten haben' lost; 'verfolgen und finden Beute' now grammatically has 'Wissenschaftler' as subject / Second sentence 'Sie schnuppern danach, wo sie sich am Boden aufgehalten haben' dropped; 'verfolgen und finden Beute' now grammatically has 'Wissenschaftler' as subject / second sentence 'Sie schnuppern danach, wo sie sich am Boden aufgehalten haben' lost; 'verfolgen und finden Beute' now has 'Wissenschaftler' as grammatical subject |
| 22 | 1602 | 2 | 38 | 28 | qualifier | '(insbesondere Schweinefleisch)', 'stets' and 'ähnlichen' lost / '(insbesondere Schweinefleisch)', 'stets' and 'ähnlichen' dropped / '(insbesondere Schweinefleisch)', 'stets' and 'ähnlichen' lost |
| 23 | 1603 | 2 | 37 | 23 | qualifier, other | 'sowohl für zivile als auch für militärische Einsätze' lost; implied link stated as explicit causation 'verursacht' / 'sowohl für zivile als auch für militärische Einsätze' dropped; background relative clause turned into an explicit cause 'verursacht' / 'sowohl für zivile als auch für militärische Einsätze' lost; implied link stated as explicit cause 'verursacht' |
| 24 | 1609 | 0 | 31 | 27 | qualifier | 'die höchste Punktzahl der Innings' lost / 'die höchste Punktzahl der Innings' dropped / 'die höchste Punktzahl der Innings' lost |
| 25 | 1609 | 2 | 31 | 27 | qualifier | 'die höchste Punktzahl der Innings' and 'nur' lost / 'die höchste Punktzahl der Innings' and 'nur' dropped / 'die höchste Punktzahl der Innings' and 'nur' lost |
| 26 | 1627 | 0 | 34 | 28 | name, date, qualifier, other | 'in späteren Jahrhunderten' and 'nach Europa' lost (claim now covers all American or Asian food); 'alten' lost; 'konnten ... enthalten' became 'enthielten' / 'in späteren Jahrhunderten ... nach Europa kamen' dropped (now excludes all American or Asian food); 'alten' dropped; 'konnten ... enthalten' became 'enthielten' / 'in späteren Jahrhunderten … nach Europa kamen' lost; 'alten' lost; 'konnten … enthalten' became 'enthielten' |
| 27 | 1641 | 0 | 38 | 35 | qualifier, other | 'mächtigen', 'verbliebenen', 'jedoch' and 'nicht nur ... auch' lost; relative clause now makes the 'Dschungelbestände', not the 'Dschungel', cover the 'Gangesebene' / 'mächtigen' and 'verbliebenen' dropped; 'der einst die Gangesebene bedeckte' re-attached from the jungle to the 'Dschungelbestände'; 'jedoch' dropped / 'mächtigen', 'verbliebenen', 'nicht nur … auch' and 'jedoch' lost; 'die einst … bedeckten' now refers to the stands, not the jungle |
| 28 | 1642 | 0 | 30 | 25 | clause, qualifier, other | 'Eroberung' lost ('bei der Eroberung der Philippinen' became 'für die Philippinen'); 'Imperialisten' and 'selbst' lost / 'bei der Eroberung der Philippinen' became 'für die Philippinen'; 'Imperialisten' and 'selbst' dropped / 'Eroberung' lost ('bei der Eroberung der' became 'für die'); 'Imperialisten' and 'selbst' lost |
| 29 | 1656 | 1 | 18 | 9 | qualifier | Attribution 'Die Polizei sagte' and hedges 'schien' and 'etwa' lost / Attribution 'Die Polizei sagte' and hedges 'schien' and 'etwa' dropped / 'Die Polizei sagte' lost; hedge 'schien' and 'etwa' lost |
| 30 | 1656 | 2 | 18 | 14 | qualifier | Attribution 'Die Polizei sagte' lost / Attribution 'Die Polizei sagte' dropped / attribution clause 'Die Polizei sagte' lost |
