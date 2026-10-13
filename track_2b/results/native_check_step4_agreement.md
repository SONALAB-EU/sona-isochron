# Native-speaker check on step 4: rates and agreement

Descriptive. 20 of 50 lines have no rating: where a pair's two German lines differ, the rater rated one and marked the other a duplicate. So the per-system rates come from different sentences, not from pairs, and the systems are not compared by a test.

- Date: 2026-10-13 15:55 UTC; git commit a4439b9cbc6f57a0aefba3ccbbecde715a1d20f6
- Sheet: `results/native_check/returned/german_lines_rated_part1.xlsx`; key: `results/native_check/step4_key_de.csv`; 30 of 50 lines marked (meaning and added information), 5 of them copied from an identical pair (protocol v2.34); texts checked against `results/native_check/returned/step4_sheet_de_as_rated.csv`
- Rater: one German native speaker.
- The checker saw the English source and one German output per line, not the system. TTS: none.
- 95 % Wilson intervals. Lines left empty are skipped.

| System | Lines | Meaning kept | Minor loss | Wrong | Adds information | Natural German |
|--------|------:|--------------|------------|-------|------------------|----------------|
| (a) plain translation | 14 | 86 % [60, 96] (12/14) | 7 % [1, 31] (1/14) | 7 % [1, 31] (1/14) | 0 % [0, 22] (0/14) | 71 % [45, 88] (10/14) |
| (c) ours: translate, then shorten | 16 | 75 % [51, 90] (12/16) | 19 % [7, 43] (3/16) | 6 % [1, 28] (1/16) | 0 % [0, 19] (0/16) | 69 % [44, 86] (11/16) |

| Native speaker vs | On | Lines | Agree | Cohen's kappa |
|---|---|---:|---:|---:|
| Evaluation NLI (the loop's model), vs the reference | kept, nothing added | 30 | 67 % | 0.17 |
| Evaluation NLI (the loop's model), vs the reference | information lost (minor or wrong) | 30 | 80 % | 0.37 |
| Evaluation NLI (the loop's model), vs the reference | information added | 30 | 80 % | 0.00 |
| Evaluation NLI, vs the English source | kept, nothing added | 30 | 70 % | 0.21 |
| Second NLI, vs the reference | kept, nothing added | 30 | 83 % | 0.44 |
| Second NLI, vs the reference | information lost (minor or wrong) | 30 | 83 % | 0.44 |
| Second NLI, vs the reference | information added | 30 | 97 % | 0.00 |
| Second NLI, vs the English source | kept, nothing added | 30 | 70 % | -0.15 |
| Final judge (Qwen3-14B), vs the English source's facts | kept, nothing added | 30 | 77 % | 0.10 |
| Final judge (Qwen3-14B), vs the English source's facts | information lost (minor or wrong) | 30 | 77 % | 0.10 |
| Final judge (Qwen3-14B), vs the English source's facts | information added | 30 | 100 % | – |
