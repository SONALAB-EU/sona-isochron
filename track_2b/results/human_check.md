# Native-speaker check of step 4 (descriptive)

- Date: 2026-10-13; rater: one German native speaker; git commit: see the commit that adds this file.
- Sheet: 50 German lines from step 4 on FLEURS test (Apertus 1.5 8B, BF16; vLLM on the cluster, run
  `hpc_8b_step4_test`, its endpoint in `results/step4_test.md`; generation seed 0; syllable budget): 25 English
  sources, each with plain translation (a) and ours (c), shuffled, without system labels
  (`docs/native_check.md`). TTS: none. n: 30 lines with marks.
- The sheet as rated is `results/native_check/returned/step4_sheet_de_as_rated.csv`: the version before the
  full-stop rule (protocol v2.26), so 4 of ours' lines (2, 37, 42, 46) had no final full stop.
- The rater rated one line per English source and marked the other "duplicate". In the 5 pairs whose German
  is identical, the rating applies to both lines (protocol v2.34). In the other 20 pairs only one version is
  rated, so the per-system rates below come from different sentences, not from pairs: they describe, and
  the systems are not compared by a test.

## What the rater found

| Line | System | Finding |
|-----:|--------|---------|
| 8 | ours | "Zoll" (inches) replaced by the symbol `"`, to fit. The rater: cheating, because the spoken length does not shrink. |
| 11 | ours | Ends in a one-word fragment ("…, Luxusstrandresorts."). |
| 21 | ours | Broken grammar that confuses the reported speech. |
| 32 | ours | Dropped "some" ("einige"), which changes the meaning: marked wrong. |
| 23 and 33 | both | "sharpener" mistranslated as "Spitze" (the rater: "Anspitzer"); 23 (plain) marked wrong. |
| 29 and 38 | both | "spotted deer" mistranslated as "Hirschziegen". |

Other comments: unnatural wording in both systems (lines 1, 5, 14, 34, 36). On six lines the rater noted
that a line "looks longer" or "way longer" (12, 13, 16, 20, 39, 43): the rater saw both lines of a pair, so
blinding was partial.

**Symbols and the syllable count (line 8 and its pair, line 48).** eSpeak NG 1.52.0, which counts the
syllables, reads `"` as nothing (0 syllables, where "Zoll" is 1). Line 8 (ours) counts 48 syllables as
written and 53 as spoken ("neunundzwanzig dreiviertel Zoll mal vierundzwanzig einhalb Zoll"); line 48
(plain), which writes "Zoll", counts 60 either way. With a budget of 49 (±10 %: 44–53.9), line 8 fits
either way here, but replacing words with symbols is a way the loop can game the count: the count drops
and the spoken length does not.

## Rates per system (95 % Wilson intervals)

| System | n | Meaning kept | Minor loss | Wrong | Adds information | Natural German |
|--------|--:|--------------|------------|-------|------------------|----------------|
| (a) plain translation | 14 | 86 % [60, 96] (12/14) | 7 % [1, 31] (1/14) | 7 % [1, 31] (1/14) | 0 % [0, 22] (0/14) | 71 % [45, 88] (10/14) |
| (c) ours | 16 | 75 % [51, 90] (12/16) | 19 % [7, 43] (3/16) | 6 % [1, 28] (1/16) | 0 % [0, 19] (0/16) | 69 % [44, 86] (11/16) |

Agreement with the automatic meaning checks, from the same 30 lines: `results/native_check_step4_agreement.md`.
