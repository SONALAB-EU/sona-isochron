# Evaluation protocol

Version 2, written on 2026-10-06 before any model output has been scored. It
replaces version 1 (commit `90f7cca`, in git history), which measured fit
against audio slots.

Plan agreed with Sören: the main target is **text length, in words and
syllables**. Audio and seconds are a stretch goal.

Any later change is recorded in the changelog at the end, with the date and
the reason.

## Overview

| Step | Task | Input | Length target | Meaning |
|------|------|-------|---------------|---------|
| 1 | Summarise (warm-up, capability check) | 20 short German texts from FLoRes-101 | about 50 % of the words | details may go |
| 2 | Shorten one sentence, same language | FLEURS reference sentence: DE first, FR second | 90 / 80 / 70 / 60 % of the syllables | all kept |
| 3 | Hit a length target | as step 2 | a word count or a syllable count | all kept |
| 4 | Translate to a length budget | FLEURS English sentence → DE, FR (IT if time allows) | isometric or isosyllabic budget | all kept |
| Stretch | Isochrony | as step 4 | VAD-trimmed audio slot, TTS seconds | all kept |

## Ground rules

- **No audio in steps 1–4.** Nothing in the main experiments may depend on
  `slot_s`, `ref_tgt_s`, the `noisy_*` flags or the `overlong_*` files. They
  come from silence trimming that fails on noisy recordings (see
  `results/fleurs_stats.md`).
- **Model.** Apertus 1.5 8B (`swiss-ai/Apertus-v1.5-8B`), reached through
  `LLM_NAME`, `LLM_BASE_URL` and `LLM_API_KEY`. One fixed temperature for all
  steps, set on dev and then frozen. 3 seeds per condition.
- **Independent models.** The NLI model and the step 1 judge are open-weights
  models other than Apertus, with their licences in `docs/licences.md`. The
  technical report describes their role.
- **Splits.** Prompts and the temperature are tuned on FLEURS dev. Numbers are
  reported on FLEURS test, using frozen prompts identified by their git commit.
- **Results files** record: date, git commit, model + quantisation, endpoint,
  TTS engine + voice (none for steps 1–4), seeds, n and split.

## Length units

Lengths are always counted by code, the same way for inputs, targets and
outputs, after Unicode NFC normalisation.

| Unit | Definition |
|------|------------|
| Characters | Code points with spaces removed; punctuation counts. This is how the IWSLT 2022 isometric scorer counts (`amazon-science/isometric-slt`, `scripts/isometric_slt_stat.py`). |
| Words | Whitespace-separated tokens that contain at least one letter or digit. |
| Syllables | A counter per language, fixed before the first dev run (see the end). |

A target T is a whole number: the share or budget, rounded half up. An output
**hits** T when |length − T| ≤ 0.10 × T.

## Data

- **FLEURS** (`data/fleurs_{de,fr,it}_{dev,test}.jsonl`): only the text fields
  `src_text` (English) and `ref_text` (human translation) are used.
- **FLoRes-101** (CC BY-SA 4.0), from Meta's public archive (no login). Its
  metadata gives each sentence's article URL, and the sentences of one article
  are consecutive (562 articles, mostly 2–5 sentences each). Used for step 1.

## Step 1: summarise (warm-up, capability check)

- **Texts.** 20 German texts, each made of 3–5 consecutive FLoRes-101 sentences
  from one article. An article qualifies only if all its sentences are in
  FLEURS train (matched on the English text). That way no step 1 text overlaps
  FLEURS dev or test. On 2026-10-06, 227 articles qualified, with 38–140
  German words each. The 20 are drawn at random, with seed 0, from the
  qualifying articles sorted by URL.
- **Task.** Summarise to about 50 % of the text's words. Losing details is
  allowed.
- **Metrics.**
  - *Main-point coverage.* For each source text, the judge lists the key facts
    once. The list is stored and reused for every system and seed. For each
    summary, the judge marks every fact as kept or not. Coverage is the share
    of facts kept.
  - *Added-content rate.* The share of summaries with at least one sentence
    that the source text does not entail. This uses the NLI model from steps
    2–4, with the whole source text as the premise.
  - The achieved length ratio is reported but not scored.
- **No tuning.** One prompt. If it has to change, try the new prompt on other
  qualifying articles, never on the 20.

## Step 2: shorten one sentence in the same language

- **Input.** A FLEURS reference sentence (`ref_text`), German first and French
  second.
- **Targets.** 90, 80, 70 and 60 % of the input's syllables.
- **All meaning must be kept.**

## Step 3: hit a length target

- **Input and levels** as in step 2. The target is given to the model as a
  count, in **words** or in **syllables** (two conditions).
- **With selection.** Apertus writes 4 candidates (4 samples of the same
  prompt). Code counts each in the target's unit and keeps the one closest to
  T; on a tie, the earlier candidate wins.
- **Without selection.** The first of the same 4 candidates. This measures how
  well Apertus controls length on its own, on the same generations.

## Step 4: translate to a length budget

- **Directions.** EN → DE and EN → FR; EN → IT if time allows. Input:
  `src_text`.
- **Systems.**
  - (a) Plain translation.
  - (b) Translate to the budget in one step.
  - (c) Translate (that is, (a)), then shorten to the budget. If (a) is
    already at or below 1.10 × the budget, it is kept unchanged.
- **Budgets**, each with ±10 % tolerance:
  - *Isometric:* the source's character count (IWSLT 2022 definition).
  - *Isosyllabic:* source syllables × target rate ÷ source rate. The rates come
    from Pellegrino et al. (2011): EN 6.19, DE 5.97, FR 7.18 and IT 6.99
    syllables per second. That gives factors of 0.964 for DE, 1.160 for FR
    and 1.129 for IT.
- (b) and (c) use whichever step 3 setting (with or without selection) does
  better on dev. It is fixed before any test run.

## Metrics for steps 2–4

- **Length hit rate** within ±10 % of the target, with characters, words and
  syllables side by side. In steps 2–3 we report the hit rate in each unit,
  with T computed in that unit. In step 4 we report the hit rate in the
  budget's unit and the achieved length in all three units.
- **Compression ratio**, in each unit: output length ÷ input length in steps
  2–3, and output length ÷ plain translation (a) in step 4.
- **Entailment in both directions**, using the independent multilingual NLI
  model. In steps 2–3 this compares input and output, in the same language. In
  step 4 it compares the English source and the output.
  - *Added content:* the input or source does not entail the output.
  - *Dropped content:* the output does not entail the input or source.
  - *Meaning kept:* both directions hold.
- **Native-speaker check** of 50 German lines, without being told which system
  produced each one. For each line the checker marks added content (yes/no) and
  dropped content (yes/no). We report how often they agree with the NLI model.

## Statistics

- 3 seeds per system and condition.
- 95 % bootstrap confidence intervals. Input items are resampled with
  replacement, and each item's score is averaged over the 3 seeds. We use
  percentile intervals over 10,000 resamples, with the bootstrap seed
  recorded.

## Go/no-go: Wednesday 7 October 2026

Fixed now, before any output has been seen.

- **Task:** step 2 in German, with a target of 80 % of the input's syllables.
- **Sentences:** 50 drawn at random, with seed 0, from
  `data/fleurs_de_dev.jsonl` in file order (by sentence id). No hand-picking.
- **GO if both hold**, pooled over the 3 seeds (150 outputs):
  1. at least 60 % land within ±10 % of the syllable target, **and**
  2. of those, at least 80 % keep meaning (entailment holds both ways).
- **Otherwise NO-GO.** We report it as a null result and do not lower the
  thresholds after the fact.

## Stretch: isochrony

Only after steps 1–4. English slots will come from VAD-trimmed audio, which
replaces the current librosa trimming. Outputs will be measured in TTS
seconds, trimmed the same way. A line fits when its spoken length is within
±10 % of the slot. Until then, the `slot_s` and `ref_tgt_s` fields are not
used.

## To fix before the first dev run

These choices are not made yet. Each will be recorded here, with its licence
in `docs/licences.md`, before any output is scored.

- The syllable counter for EN (needed for isosyllabic budgets), DE, FR and
  later IT. It will be checked against a small hand-counted sample, and its
  accuracy reported.
- The NLI model, and how its output is turned into "entails".
- The judge model for step 1.
- The prompt for each step, the temperature, and the exact Apertus
  checkpoint, quantisation and endpoint.
- Which outputs the 50 native-speaker lines come from, and who checks them.

## References

- Pellegrino, F., Coupé, C. and Marsico, E. (2011). A cross-language
  perspective on speech information rate. *Language* 87(3).
- IWSLT 2022 isometric spoken language translation task,
  [iwslt.org/2022/isometric](https://iwslt.org/2022/isometric).

## Changelog

- 2026-10-06, v1: first version, measuring against audio slots (commit `90f7cca`).
- 2026-10-06, v2: rewritten to Sören's plan. Text length (words, syllables) is
  the main target, and audio is a stretch goal because FLEURS trimming is
  unreliable on noisy recordings. Steps 1–4 plus a stretch step, with a new
  go/no-go on step 2.
