# NLI sanity suite

- Date: 2026-10-06 15:57 UTC
- Git commit: 326758c67d1199547ec10b8058243694b5d6bdec
- NLI model: MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 @ b5113eb, mps, float32, argmax label
- Data: `data/nli_controls.jsonl` (SHA-256 `73647308cacd2c204fb5adfda0318594244c43b42f1552a047c34ebb853aa827`), 200 pairs: 40 FLEURS train sentences × 5 control types; variants written by hand by Claude (AI assistant), not yet reviewed by a native speaker
- LLM, endpoint, TTS: none. Seeds: none (deterministic inference)
- Pass rule: every control type at least 80% correct over both languages

**Result: PASS**

| Control | Expected | DE | FR | All |
|---------|----------|---:|---:|---:|
| identity | kept | 90 % (18/20) | 100 % (20/20) | 95 % (38/40) |
| paraphrase | kept | 95 % (19/20) | 95 % (19/20) | 95 % (38/40) |
| clause_deleted | dropped, not added | 85 % (17/20) | 80 % (16/20) | 82 % (33/40) |
| clause_inserted | added, not dropped | 90 % (18/20) | 90 % (18/20) | 90 % (36/40) |
| negation | not kept | 100 % (20/20) | 100 % (20/20) | 100 % (40/40) |

## Pairs judged wrong (15)

| Id | Source ⇒ output | Output ⇒ source | Output |
|----|-----------------|-----------------|--------|
| de-878-identity | neutral | neutral | Eine Infektionskrankheit ist eine Krankheit, die durch einen Erreger, wie z. B. einen Virus, ein Bakterium, einen Pilz oder andere Parasiten, verursacht wird. |
| de-878-clause_deleted | entailment | entailment | Eine Infektionskrankheit ist eine Krankheit, die durch einen Erreger verursacht wird. |
| de-878-clause_inserted | neutral | neutral | Eine Infektionskrankheit ist eine Krankheit, die durch einen Erreger, wie z. B. einen Virus, ein Bakterium, einen Pilz oder andere Parasiten, verursacht wird und meist innerhalb einer Woche ausheilt. |
| de-735-clause_deleted | entailment | entailment | Sie benötigen eine Genehmigung, um in La Sirena zu übernachten. |
| de-1481-identity | neutral | neutral | Eine Fußsafari (auch „Buschgang“, „Wandersafari“ oder „Footing“ genannt) besteht aus einer Wanderung, die entweder ein paar Stunden oder mehrere Tage dauert. |
| de-1481-clause_deleted | entailment | entailment | Eine Fußsafari besteht aus einer Wanderung, die entweder ein paar Stunden oder mehrere Tage dauert. |
| de-1481-clause_inserted | neutral | neutral | Eine Fußsafari (auch „Buschgang“, „Wandersafari“ oder „Footing“ genannt) besteht aus einer Wanderung, die entweder ein paar Stunden oder mehrere Tage dauert und immer von einem bewaffneten Ranger begleitet wird. |
| de-671-paraphrase | neutral | entailment | Um den Canyon zu schützen, ist die Zahl der Lizenzen begrenzt; sie sind ab dem ersten Tag des Monats erhältlich, der vier Monate vor dem Startmonat liegt. |
| fr-825-clause_inserted | neutral | neutral | Jetez un coup d’œil aux voyages dont l’agent fait la promotion, que ce soit sur un site internet ou en vitrine, car ils sont souvent moins chers en hiver. |
| fr-804-paraphrase | neutral | entailment | Les alcools forts illicites peuvent renfermer différentes impuretés dangereuses, dont le méthanol, qui peut rendre aveugle ou tuer, même à faible dose. |
| fr-804-clause_inserted | neutral | neutral | Les spiritueux illicites peuvent contenir diverses impuretés dangereuses, y compris du méthanol, qui peut causer la cécité ou la mort, même à petites doses, et ils sont surtout vendus dans les zones rurales. |
| fr-654-clause_deleted | entailment | entailment | Les habitants autochtones du Groenland se nomment Inuit au Canada. |
| fr-887-clause_deleted | entailment | entailment | L’Antarctique est l’endroit le plus froid sur Terre. |
| fr-740-clause_deleted | entailment | entailment | L'archipel des îles Cook est un État en libre association avec la Nouvelle-Zélande. |
| fr-926-clause_deleted | neutral | neutral | Il ne faut même pas penser à enregistrer une vidéo. |
