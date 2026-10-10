# Language check: validation of the rule

- Date: 2026-10-10 13:32 UTC
- Git commit: 1aae5c8c936e7ecd4068f0ba32b31584b01567a0
- Identifier: py3langid 0.4.0, restricted to de/en/fr/it; wrong language = top label is another language with probability >= 0.9
- Model under test: none (this checks the identifier). The outputs are those of Apertus 1.5 8B Q4_K_M in the pilot runs and the go/no-go run on German dev sentences: `20261009T151900Z_pilot_v1_de_dev`, `20261009T153417Z_pilot_v2a_de_dev`, `20261009T155640Z_pilot_v1_de_dev`, `20261009T161226Z_pilot_v2a_de_dev`, `20261009T163426Z_pilot_v2b_de_dev`, `20261009T165135Z_pilot_v2c_de_dev`, `20261009T131902Z_step2_de_dev_syllables`, `20261009T132800Z_step2_de_dev_syllables`, `20261009T141025Z_step2_de_dev_syllables`, `20261009T141318Z_step2_de_dev_syllables`
- TTS: none. Seeds: none (the identifier is deterministic).
- n: see the table; 2643 distinct outputs.

The rule was chosen on the "Choice" rows: FLEURS train and dev sentences, and outputs of dev runs. The
"Held out" rows use test sentences and the French and Italian files, and did not inform the choice. (An
earlier, informal look at word prefixes also included test sentences; the chosen rule is the same without
them.) Prefix rows cut each sentence after its first k words, as a stand-in for very short outputs.

| Set | Sentences | Should be flagged | 139 languages, top label ≠ target | 4 languages, top label ≠ target | 4 languages, top label ≠ target, p ≥ 0.9 (used) |
|-----|----------:|-------------------|---:|---:|---:|
| Choice: German: FLEURS train + dev sentences | 1609 | none | 0 | 0 | 0 |
| Choice: German: their first 3 words | 1609 | none | 127 | 25 | 2 |
| Choice: German: their first 5 words | 1608 | none | 26 | 6 | 1 |
| Choice: English: FLEURS train + dev sentences | 1623 | all | 1623 | 1623 | 1620 |
| Choice: English: their first 3 words | 1623 | all | 1615 | 1599 | 1019 |
| Choice: English: their first 5 words | 1623 | all | 1623 | 1618 | 1453 |
| Choice: Apertus outputs, German dev runs (distinct texts) | 2643 | the English ones | 15 | 3 | 3 |
| Held out: German: FLEURS test sentences | 347 | none | 0 | 0 | 0 |
| Held out: German: their first 3 words | 347 | none | 24 | 6 | 0 |
| Held out: English: FLEURS test sentences | 347 | all | 347 | 347 | 347 |
| Held out: English: their first 3 words | 347 | all | 347 | 340 | 206 |
| Held out: French: FLEURS dev + test, checked as German | 469 | all | 469 | 469 | 469 |
| Held out: Italian: FLEURS dev + test, checked as German | 493 | all | 493 | 493 | 493 |
| Held out: French: FLEURS dev + test, checked as French | 469 | none | 0 | 0 | 0 |

Reading the table: the used rule flags 0 of the 1956 whole German sentences, and 2929 of the 2932 whole English, French and Italian sentences. It misses many 3-word English fragments: that is the price of not flagging German
fragments led by a foreign name. The wrong-language outputs seen so far were whole translations into English.

## Outputs the rule flags (3)

- `20261009T155640Z_pilot_v1_de_dev`: Broad avenues, glass buildings and modern shopping centers are characterized by classic red-tiled roofs, the 18th-century market as well as old mosques and churches, although the city radiates a Mediterranean European atmosphere rather than that of traditional Turkey.
- `20261009T163426Z_pilot_v2b_de_dev`: Broad avenues, glass buildings, modern shopping centers are marked by classic red-tiled roofs, the 18th-century market, and old mosques and churches, while the city radiates a Mediterranean European atmosphere more than that of traditional Turkey.
- `20261009T163426Z_pilot_v2b_de_dev`: Broad avenues, glass buildings, modern shopping centers feature red-tiled roofs, an 18th-century market, old mosques and churches, yet the city radiates a Mediterranean European ambiance over traditional Turkish style.

## False alarms: sentences or fragments in the target language that the rule flags (3)

- en 0.922: Go Running Tours,
- fr 0.904: Jardín de la
- fr 0.961: Nach Fray Bartolomé de las

## Outputs with another top label that the rule does not flag (0)

None.
