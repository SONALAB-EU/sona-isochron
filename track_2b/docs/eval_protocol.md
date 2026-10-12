# Evaluation protocol

Version 2.1, 2026-10-06, written before any model output has been scored.
Version 1 (commit `90f7cca`) measured fit against audio slots; version 2
(commit `fa777d8`) moved to text length. Both are in git history.

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
  `LLM_NAME`, `LLM_BASE_URL` and `LLM_API_KEY`.
  - Locally it runs as the Q4_K_M GGUF of a text-only conversion of the
    official weights: `Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF`, made from
    `andreasmartin/apertus-v1.5-8b-text`, file SHA-256 `a037df8d…5f299`.
  - It is served by llama.cpp build 11429 with every layer on Metal and an
    8,192-token context (`docs/local_llm.md`).
  - This is a deviation from the official checkpoint. The official model has
    no GGUF, and llama.cpp cannot convert `Apertus1p5ForConditionalGeneration`.
    The conversion copies the text backbone bit for bit, but its author did
    not check that the outputs match the official model.
- **Generation settings, for every system:** temperature 0.7, top_p 0.95,
  seeds 0, 1 and 2, thinking mode off. Thinking is switched off by sending the
  chat-template argument `enable_thinking: false`, which is Apertus 1.5's
  switch. At most 1024 new tokens.
  - Sampling means temperature first, then the nucleus (top_p), with no other
    truncation. This is the vLLM / transformers order.
  - Requests therefore also send `top_k: 0` and `min_p: 0`, and on
    llama-server `samplers: ["temperature", "top_p"]`. Without these,
    llama-server adds top_k 40 and min_p 0.05 and applies temperature last.
  - Every run records its backend in `config.json`.
- **Independent models.** These are open-weights models other than Apertus,
  with their licences in `docs/licences.md`; the technical report describes
  their role.
  - *NLI:* `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` (MIT),
    pinned to revision `b5113eb`. It runs locally on CPU or Apple's mps.
  - *Judge* (for step 1, and to list what was added or dropped): deferred to
    the HPC. The candidate is Qwen3-14B. Its licence (Apache-2.0) was
    verified on 2026-10-06, and it is a different model family from Apertus.
- **Splits.** Prompts are tuned on FLEURS dev only. Numbers are reported on
  FLEURS test, using frozen prompts identified by their git commit.
- **Generation and scoring are separate.** `isochron.run` saves every
  candidate and a `config.json` (date, commit, model, quantisation, endpoint,
  seeds, prompt version). `isochron.score` does the selection and all metrics
  offline, and can be re-run.
- **Results files** record: date, git commit, model + quantisation, endpoint,
  TTS engine + voice (none for steps 1–4), seeds, n and split.

## Prompts

- Zero-shot, version 1. Each prompt is a plain-text file in
  `src/isochron/prompts/`: `shorten_syllables_v1.txt` and
  `shorten_words_v1.txt` so far.
- Each prompt names the language and gives an explicit numeric target in
  words or syllables. It tells the model: keep every piece of information,
  add nothing; you may reorder, use shorter synonyms, drop filler words and
  merge clauses.
- The output is JSON with 4 candidates and no explanations.
- If examples are added later, they come from FLEURS train only.
- **Frozen on 2026-10-09, before the go/no-go run:** `shorten_syllables_v1.txt`,
  SHA-256 `fe4fbfdd800d69b613fd49ba747507aa44a9a868556ceca15421d33edd661a5c`.
  Any change makes a new version (v2), and every run records the hash it used.

## Length units

Lengths are always counted by code, the same way for inputs, targets and
outputs, after Unicode NFC normalisation (`src/isochron/metrics/length.py`).

| Unit | Definition |
|------|------------|
| Characters | Code points with spaces removed; punctuation counts. This is how the IWSLT 2022 isometric scorer counts (`amazon-science/isometric-slt`, `scripts/isometric_slt_stat.py`). |
| Words | Whitespace-separated tokens that contain at least one letter or digit. |
| Syllables | eSpeak NG 1.52.0 converts the text to IPA as it would be spoken, so numbers and abbreviations count as spoken. We count the syllabic nuclei in that output. |

More on syllables:
- eSpeak NG is GPL-3.0. It runs as a separate program and is never imported.
- Two corrections for how it writes glides: in French, "y" before "i" is [ɥ]
  (*nuit*, *depuis*); in German, an unstressed i before another vowel is [i̯]
  (*Familie*, *Region*).
- If eSpeak NG is missing, a vowel-group heuristic is used as a fallback. Each
  run records which counter it used.
- German years are read as years. Before eSpeak NG runs, 4-digit numbers
  1100–1999 not followed by a unit or currency are rewritten (1959 →
  "19 hundert 59", and decades too: 1970er → "19 hundert 70er"). French is
  unchanged, because French reads years as full numbers.
- **Documented limitation.** On the spot-check list (`results/syllable_spotcheck.md`:
  40 words and 10 sentences with numbers, against hand counts not yet
  checked by a native speaker), eSpeak NG gets 46 of 50 items exact (92 %).
  The vowel-group heuristic gets 21 of 50. The remaining errors:
  - German hiatus words, where eSpeak NG's own transcription merges two
    vowels: *naiv* 1 instead of 2, *Zoologie* 3 instead of 4, *Melodien* 3
    instead of 4.
  - German ordinals read as cardinals: "15." is counted as *fünfzehn* (2), not
    *fünfzehnten* (3).
  - A number next to a noun that is not a unit is read as a year (*1500 Mann*
    becomes *fünfzehnhundert*).
  Inputs and outputs are counted the same way, so these errors mostly cancel
  in hit rates.

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
  FLEURS train (matched on the English text), so no step 1 text overlaps
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
    that the source text does not entail. This uses the NLI model, with the
    whole source text as the premise.
  - The achieved length ratio is reported but not scored.
- **No tuning.** One prompt. If it has to change, try the new prompt on other
  qualifying articles, never on the 20.

## Step 2: shorten one sentence in the same language

- **Input.** A FLEURS reference sentence (`ref_text`), German first and French
  second.
- **Targets.** 90, 80, 70 and 60 % of the input's syllables. The prompt gives
  the target as a syllable count.
- **All meaning must be kept.**
- **Scored output.** The candidate closest to the target. The first candidate
  is reported alongside.

## Step 3: hit a length target

- **Input and levels** as in step 2. The target is given to the model as a
  count, in **words** or in **syllables** (two conditions).
- **With selection.** Apertus writes 4 candidates in one JSON answer. Code
  counts each in the target's unit and keeps the one closest to T; on a tie,
  the earlier candidate wins.
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
- **Meaning.** The main check is monolingual NLI between the output and the
  human reference (`ref_text`), in the target language. The secondary check
  is cross-lingual NLI against the English source. In a first probe, the
  cross-lingual check labelled a correct German–French pair as
  "contradiction" in one direction.
- **Implementation (2026-10-10, v2.10; `src/isochron/step4.py`,
  `src/isochron/step4_report.py`).**
  - Step 3 has not been run, so (b) and (c) use step 2's selection: the
    closest of 4 candidates in the budget's unit. That rule is fixed here,
    before any test run.
  - (c) shortens (a) with our method: prompt v1 and the repair loop, in the
    budget's unit. The loop's NLI compares the candidates with (a).
  - The character prompts (`shorten_chars_v1`, `revise_chars_v1`,
    `translate_budget_chars_v1`) differ from the syllable ones only in the
    length instruction.
  - Budgets:
    - isometric: the English source's characters without spaces;
    - isosyllabic: its syllables (eSpeak NG, `en-us`) × the rate ratio,
      rounded half up.
  - (a) asks again, with the next seed, if its answer is not JSON (at most 3
    tries).
  - A wrong-language output counts as a failure.
  - Seeds: (a) and (b) use the item seed, (c) item seed + 1000 × round.
- **Local smoke test (2026-10-10; exploratory, 5 dev sentences per language
  outside the go/no-go 50, seed 0, Apertus Q4_K_M;
  `results/step4_smoke_local.md`).**
  - For German, (a) never met the syllable budget and met the character
    budget 2 of 5 times.
  - Under the character budget, (b) fit every time but kept the meaning
    against the reference in 2 of 5. (c) fit every time and kept it in 4
    of 5.
  - Five sentences per cell is too few to read any difference; this only
    shows that the pipeline works.
- **Test run: frozen on 2026-10-12, before any test output was generated
  (v2.17).**
  - **Frozen as it ran on dev** (job 2636594, run commit `68492f2`). The
    code that generates step 4 has not changed since `68492f2`: `step4.py`,
    `repair.py`, `candidates.py`, `loop_run.py`, `run.py`, `llm.py`,
    `language.py`, `metrics/length.py`, `metrics/meaning.py` and
    `prompts/` (empty `git diff`).
  - **Prompts (SHA-256), the same as the dev run recorded:**
    - `translate_plain_v1` `5fe6dd58bf7e05da0bfaaf005877876cdb9cbbe1d99375105aa7a4f3772e7d2f`
    - `translate_budget_chars_v1` `e81efebd7d4f6b6d9aab91f1170c32a9efa2dd07efb86f5d30e5a300b16d7a30`
    - `translate_budget_syllables_v1` `a3ffa4ea51a78b1a943be2c4ae8ecb5811bea136b4a76dab67cdb06baef2a319`
    - `shorten_chars_v1` `004890c41f2573c07be89204ac43f8fb7a6c8e999fca1ea38ff9b28124d0630e`
    - `shorten_syllables_v1` `fe4fbfdd800d69b613fd49ba747507aa44a9a868556ceca15421d33edd661a5c`
    - `revise_chars_v1` `62a308e266abffad9bb7bfa7a28d4d51356ccc319cf676a8f89ae9b8d0f47f2e`
    - `revise_v1` `ab0593b9716e97e17444e36c243206f65a62f5d46d3421423cfdeda2f55c5c57`
  - **Systems.**
    - (a): plain translation.
    - (b): one step to the budget, the closest of 4 candidates in the
      budget's unit.
    - (c): (a) kept unchanged if at most 1.10 × the budget; otherwise
      shortened with prompt v1 and the repair loop in the budget's unit (at
      most 2 revisions; the loop's NLI compares with (a)).
  - **Budgets, ±10 %.**
    - Isometric: the English characters without spaces.
    - Isosyllabic: the English syllables × target rate ÷ English rate
      (German 0.964, French 1.160), rounded half up.
  - **Generation:** as on dev. Seeds 0, 1 and 2; (a) and (b) use the item
    seed, and round r of (c) uses item seed + 1000 × r. Apertus 1.5 8B BF16
    on vLLM, one H100, 16 items in flight.
  - **Not fixed:** French answers that break JSON (apostrophes escaped as
    `\'`). A broken answer counts as a miss and is reported.
  - **Data:** FLEURS test, every sentence. EN → DE: 347 sentences, 1,041
    items. EN → FR: 332 sentences, 996 items.
  - **Scoring, fixed now, as in step 2.**
    - Fit within ±10 % of the budget in its unit. The language check: a
      missing or wrong-language output fails.
    - NLI against the human reference (main) and against the English source
      (secondary).
    - The final judge, Qwen3-14B BF16 (`perfact_v3`). It lists the facts of
      the English source once, in English. It marks each fact kept, changed
      or dropped in the output, and lists added facts.
    - Fit & complete: fits, every fact kept, nothing added.
    - 95 % bootstrap intervals over sentences (10,000 resamples, seed 0).
  - **Cross-lingual judge validation.** The judge is validated in the same
    pipeline on the cross-lingual versions of both suites: `nli_xl` and
    `hard_xl`, the same pairs with the English original as the source
    (`isochron.data.build_xl_controls`).
    - If it calls fewer than 90 % of the identity pairs complete, the judge's
      numbers are reported but flagged as unreliable, and the NLI against
      the reference stays the main meaning check.
  - **Where scoring runs.** The cluster jobs generate, validate and judge.
    The lengths, the language check and the NLI are computed on the Mac
    from the logged outputs (`isochron.step4_report`), so no GPU idles on
    CPU work.
  - **Jobs, chained (`afterok`):**
    1. A sanity check on dev: 5 sentences per language, seed 0. The test
       jobs wait at a gate until it is checked.
    2. EN → DE test.
    3. EN → FR test.
  - **Compute** (an estimate): about 1.6 H100-hours. The limits (1, 1.5 and
    1.5 h) keep even the worst case at 8.5 of the 12 H100-hours, with 4.46
    already used.

## Metrics for steps 2–4

- **Length hit rate** within ±10 % of the target, with characters, words and
  syllables side by side. In steps 2–3 we report the hit rate in each unit,
  with T computed in that unit. In step 4 we report the hit rate in the
  budget's unit and the achieved length in all three units.
- **Compression ratio**, in each unit: output length ÷ input length in steps
  2–3, and output length ÷ plain translation (a) in step 4.
- **Entailment in both directions**, with the NLI model above. The predicted
  label is the argmax. Steps 2–3 compare input and output; step 4 compares
  output and reference (main) and output and source (secondary).
  - *Added content:* source ⇒ output is not "entailment".
  - *Dropped content:* output ⇒ source is not "entailment".
  - *Kept:* both directions are "entailment".
  - An answer without usable candidates counts as a miss and as not kept.
  - As a diagnostic, we report how many inputs the NLI does not accept as
    entailing themselves.
- **Native-speaker check** of 50 German lines, without being told which system
  produced each one. For each line the checker marks added content (yes/no) and
  dropped content (yes/no). We report how often they agree with the NLI model.

## NLI sanity suite

`data/nli_controls.jsonl` holds 20 German and 20 French FLEURS train
sentences. Each is paired with itself, a true paraphrase, a version with a
clause deleted, one with a made-up clause inserted, and a negation. The
variants were written by hand by Claude (AI assistant).

The rule: if any control type scores below 80 %, the NLI metric is not used.
Result: **pass**. It was first run on 2026-10-06 at commit `326758c` and
re-run in float32 on 2026-10-09 at commit `6edfd20` with the same scores
(`results/nli_sanity.md`).

| Control | Expected | DE | FR | All |
|---------|----------|---:|---:|----:|
| identity | kept | 90 % | 100 % | 95 % |
| paraphrase | kept | 95 % | 95 % | 95 % |
| clause deleted | dropped, not added | 85 % | 80 % | 82 % |
| clause inserted | added, not dropped | 90 % | 90 % | 90 % |
| negation | not kept | 100 % | 100 % | 100 % |

Notes:
- Two long German sentences are judged "neutral" even against themselves.
  CPU and mps agree, so this is the model, not the device.
- Deletions are the weakest type: the metric under-reports dropped content.
- An audit of 20 go/no-go outputs, read by an LLM rather than a native
  speaker, confirms this. The NLI judged 11 of them "kept" although a
  modifier or detail was dropped or changed, and two of those are clear
  meaning errors. So NLI "kept" rates are upper bounds for "every piece of
  information kept". The native-speaker check is needed before relying on
  them (`results/gonogo_step2_de.md`).
- The model runs in float32. Until commit `6edfd20` it ran in the
  checkpoint's float16 although reports said float32. Re-running in float32
  changed no label in the sanity suite or the go/no-go.

## Statistics

- 3 seeds per system and condition: 0, 1 and 2.
- 95 % bootstrap confidence intervals. Input items are resampled with
  replacement, and each item's score is averaged over the 3 seeds. We use
  percentile intervals over 10,000 resamples, with bootstrap seed 0.

## Go/no-go: Wednesday 7 October 2026

Fixed before any output has been seen (`src/isochron/gonogo.py`).

- **Task:** step 2 in German, with a target of 80 % of the input's syllables.
- **Sentences:** 50 drawn at random, with seed 0, from
  `data/fleurs_de_dev.jsonl` in file order (by sentence id). No hand-picking.
  Smoke tests use other dev sentences, never these 50.
- **Scored output:** the candidate closest to the syllable target. The first
  candidate is reported alongside but does not decide.
- **GO if both hold**, pooled over seeds 0, 1 and 2 (150 outputs):
  1. at least 60 % land within ±10 % of the syllable target, **and**
  2. of those, at least 80 % keep meaning (entailment holds both ways).
- **Otherwise NO-GO.** We report it as a null result and do not lower the
  thresholds after the fact.
- **Smoke test before the run** (2026-10-09, run `20261009T131902Z`): the same
  5 other dev sentences as the dry run, all 4 levels, seed 0, 20 requests.
  The three required checks passed:
  - every answer is JSON with 4 candidates;
  - all 80 candidates are non-empty German, by the character n-gram
    identifier in `src/isochron/langid.py` (trained on FLEURS train; 578/578
    dev sentences right) and by reading each one;
  - the NLI scored all 40 pairs.

  A first, function-word version of the language check wrongly failed 16
  short German candidates and was replaced before the go/no-go run.
- **A first go/no-go generation was superseded before anyone scored or read
  it** (run `20261009T132800Z`, kept in `results/raw/`).
  - A blind review of the scoring code found that every request so far had
    sampled with llama-server's defaults: top_k 40 and min_p 0.05, with
    temperature applied last. The server log shows this for all 171 requests.
    That is not the decided sampling.
  - The review also found that German decade forms (*1970er*) escaped the year
    rule, which changed one go/no-go target (sentence 1604: 110 instead of
    108).
  - Both were fixed (commit `0ddd55f`), the smoke test was re-run (run
    `20261009T141025Z`, all three checks pass), and the go/no-go was
    generated again. The superseded run is not scored for the decision.
- **Result (2026-10-09, run `20261009T141318Z`; `results/gonogo_step2_de.md`):
  NO-GO.**
  - Fit was 40.7 % [31.3, 50.0] (61/150); 60 % was needed.
  - Kept among fits was 62.3 % [46.6, 77.0] (38/61); 80 % was needed.
  - Both criteria fail, each on its own. Three independent agents reproduced
    the numbers. As pre-registered, this is reported as a null result, and
    the thresholds stay as they are.
- **This result is final:** prompt v1 with Apertus 1.5 8B Q4_K_M is NO-GO. It
  is not re-run or re-scored.

## Phase 2 (exploratory, from 2026-10-09)

Everything after the go/no-go is exploratory. Tuning uses only the 97 German
dev sentences outside the go/no-go 50, which are never used for tuning. Final
numbers are reported on test, as before. The work goes in this order.

1. **Error analysis** of the go/no-go outputs, closest candidate only. It is
   analysis, not re-scoring:
   - a histogram of achieved ÷ target syllables;
   - 30 "dropped" cases (NLI) drawn with seed 0, each classified by what was
     lost: number, name, date, clause, qualifier or other.

   Saved to `results/gonogo_error_analysis.md`.
2. **Prompt v2 variants**, versioned files in `src/isochron/prompts/`. Fit
   and closest selection are still measured in syllables, against level % of
   the input's syllables.
   - *v2a facts-first:* list the sentence's facts, then write the shortest
     sentence that keeps all of them, near the syllable target.
   - *v2b word target:* give the source word count and an equivalent word
     target, level % of the source words rounded half up.
   - *v2c graded candidates:* 4 candidates at level +15, +10, +5 and +0
     percentage points of the input's syllables, capped at 100 %. That is
     95/90/85/80 % at level 80 and 100/100/95/90 % at level 90.
3. **Repair loop (our method).**
   - Selection prefers a candidate in the requested language (since v2.9),
     then one that is both within ±10 % and kept by the NLI, then one that is
     kept, then the closest.
   - If the selected candidate fails either test, Apertus gets one revision
     prompt with specific feedback: how many syllables too long or short (with
     the word equivalent), that information is missing, or that information
     was added.
   - At most 2 revision rounds. The best candidate over all rounds is kept,
     and every round is logged.
   - Each round uses its own seed: the item seed plus 1000 × the round
     number. Without that, an unchanged prompt would be replayed byte for
     byte.
   - If no round has given a usable answer yet, the round-0 prompt is sent
     again, and that round is logged as a retry.
   - **Language check (added 2026-10-10, after the pilot).** Every candidate
     is checked with py3langid 0.4.0 (BSD-3-Clause), restricted to German,
     English, French and Italian.
     - A candidate is in the wrong language when another of these languages
       is the top label with probability ≥ 0.9. The rule was chosen on FLEURS
       train and dev sentences and on dev outputs (`results/language_check.md`).
     - A wrong-language candidate is never accepted. When the best candidate
       is in the wrong language, the only feedback is "It is not in German.
       Answer in German."
     - Scoring counts a wrong-language output as a failure in both
       conditions, like a missing output.
   - The loop uses only the language identifier, the syllable counter and the
     NLI, never the final judge.
   - "Without the loop" means the closest candidate of round 0 of the same
     run.
4. **Final meaning judge, for evaluation only.**
   - Model: Qwen3-8B (`Qwen/Qwen3-8B-GGUF`, Q4_K_M, Apache-2.0), a different
     model family from Apertus.
   - It runs on llama-server port 8081, only after generation and with the
     Apertus server stopped. Thinking is off, temperature 0. It is reached
     through `JUDGE_NAME`, `JUDGE_BASE_URL` and `JUDGE_API_KEY`.
   - It lists each source sentence's facts once; the list is stored and reused
     for every system. For each output it then marks each fact as kept,
     dropped or changed, and lists any added facts, as JSON.
   - Metrics: *fact recall* (kept facts ÷ facts, per output, averaged) and the
     *added-fact rate* (share of outputs with at least one added fact).
   - It is validated on the NLI control suite before use.
   - **Judge prompt selection (added 2026-10-10, before any v2 result).**
     - Validation of `judge_compare_v1` showed two failure modes. It does not
       see the original sentence, so it marks its own paraphrased facts as
       "changed" even on identical pairs. It also often answers with fewer
       entries than there are facts.
     - `judge_compare_v2` therefore also shows the original sentence, defines
       "kept" as the same information in any wording, and states the number
       of entries expected.
     - To avoid tuning on the validation data, the control suite is split. Half
       A (per language the 10 base sentences with the lowest FLEURS ids) is
       used to tune judge prompts; half B (the other 10) is held out.
     - The prompt with the higher mean accuracy over the 5 control types on
       half B judges the pilot. Ties are broken by fewer invalid answers.
     - A third candidate, `perfact_v3`, was added during tuning. It asks one
       one-word question per fact (`judge_fact_v3`: kept / changed /
       dropped, showing the original and the new version) plus one call for
       added information (`judge_added_v3`). On half A it beat v2: mean 95 %
       against 82 %, because v2 still failed paraphrases (30 %). So
       `perfact_v3` went to half B.
     - **Result on half B:** `perfact_v3` 91 % against v1 69 % (v1: 4 invalid
       answers; v3: 0). So `perfact_v3` judges the pilot.
       - Per type on half B: identity 100 / 50, paraphrase 100 / 50,
         deletion 85 / 90, insertion 70 / 60, negation 100 / 95 (v3 / v1).
       - Over all 200 pairs, v3 scores 100 / 100 / 92 / 72 / 100 %.
       - Its weak spot is insertions in German (50 %), so added-fact rates are
         likely undercounted.
       - Reports: `results/judge_validation_v1_all.md`, `…_v1_halfB.md`,
         `…_v3_halfB.md`, `…_v3_all.md`; tuning in `results/judge_tuning_*`.
   - **Hard controls (added 2026-10-10).** The NLI suite changes whole clauses;
     the losses that dominate our outputs are smaller.
     - `data/judge_controls_de.jsonl` has 60 German FLEURS train sentences,
       none of them in the NLI suite, selected in a seeded order
       (`src/isochron/data/build_judge_controls.py`): 40 with one modal, number
       or qualifier change, 20 with one inserted fact, 20 same-meaning edits
       and 60 identity pairs.
     - Claude wrote the edits; no native speaker has reviewed them yet.
     - Any judge is validated on both suites before use, with halves A and B
       as for the NLI suite (per edit type).
     - **Qwen3-8B with `perfact_v3`, all 140 pairs**
       (`results/judge_validation_hard_v3_all.md`): identity 100 %, same
       meaning 85 %, modal changed 62 %, number changed 100 %, qualifier
       changed 36 %, fact inserted 85 % (mean 78 %). The NLI scores
       92 / 90 / 77 / 92 / 21 / 100 % on the same pairs.
     - So this judge misses most lost qualifiers.
   - On the HPC the judge is Qwen3-14B (BF16, Apache-2.0) under vLLM. Every
     job validates it on both suites before it judges (`docs/hpc.md`).
   - **Qwen3-14B result (2026-10-10, job 2634364,
     `results/judge_validation_{hard,nli}_v3_qwen3-14b_hpc_8b.md`).**
     - Hard controls: identity 100 %, same meaning 100 %, modal changed 77 %,
       number changed 100 %, qualifier changed 50 %, fact inserted 80 % (mean
       84 %).
     - NLI suite: mean 99 %.
     - Rule, fixed before this result: Qwen3-14B becomes the main judge if it
       catches more than Qwen3-8B's 13 of the 27 qualifier and modal changes
       and is not lower in either category. It caught 17 (qualifier 7, modal
       10), so it is the main judge for the full runs.
     - The difference is within noise. On the same 27 pairs, only the 14B
       judge caught 7 and only the 8B judge caught 3 (exact McNemar,
       two-sided p = 0.34). The two judges also differ in quantisation and
       backend, not only in size.
     - It still misses half the lost qualifiers, so fact recall stays an upper
       bound.
5. **Pilot.**
   - 30 German dev sentences outside the go/no-go 50
     (`random.Random(0).sample` of the other 97), seed 0, levels 90 % and 80 %.
   - v1, v2a, v2b and v2c, each with and without the repair loop.
   - Table: fit rate, fact recall, added-fact rate, average rounds and time
     per sentence.
   - A first pilot generation was superseded before any of it was judged
     (`results/raw/20261009T151900Z_pilot_v1_de_dev`, complete, and
     `…T153417Z_pilot_v2a_de_dev`, partial). A code review found that every
     round reused the item seed, so an unchanged revision prompt was replayed.
     The runs are kept in `results/raw/` but never judged or reported.
   - **Result (2026-10-10, `results/phase2_pilot.md`; exploratory).**
     - The repair loop helps; the v2 prompts do not help on their own. Pooled
       over both levels, v1 with the loop fits 73.3 % [61.7, 85.0] and is fit
       & complete in 50.0 % [38.3, 61.7]. Without the loop the figures are
       33.3 % and 18.3 %. The loop costs 15.6 s per output instead of 6.2 s.
     - Re-scored on 2026-10-10 with the language check.
       - Three outputs with the loop are in English, all for sentence 1525
         (v1 at level 90, v2b at both levels). They now count as failures.
       - Fit falls by one output in 60 for v1 and by two for v2b. Fit &
         complete and the pick are unchanged.
     - With the loop, the four variants are within noise of each other: fit &
       complete is 41.7 to 50.0 %, and the intervals overlap.
     - The rule picks v1 with the loop. The rule does not name a table, so it
       is applied to the both-levels table, which was the report's first
       table when the rule was written. Level 90 alone gives the same pick.
       Level 80 alone would pick v2b without the loop through the time
       tie-break, because at n = 30 the intervals overlap widely.
     - Caveats:
       - The judge is lenient on lost qualifiers and misses insertions. An
         LLM audit agreed with it on "complete" in 17 of 24 outputs. So fact
         recall and fit & complete are upper bounds, and added facts are not
         measured.
   - **Decided on 2026-10-10:** prompt v1 with the repair loop is the method;
     v2a is dropped.
6. **Full runs (planned 2026-10-10; German and French test done on
   2026-10-11).**
   - **HPC** (`docs/hpc.md`).
     - Models: Apertus 1.5 8B and 70B in BF16, the official weights in the
       official vLLM container.
     - Task: step 2 on German test, levels 90, 80, 70 and 60 %, seeds 0, 1
       and 2. That is 4,164 items per model, with prompt v1 and the loop.
     - Judge: Qwen3-14B, validated on both suites in the same job.
     - French is optional.
     - **German test result (2026-10-11, job 2636592, run commit 68492f2;
       `results/step2_test.md`).**
       - Apertus 1.5 8B BF16, 347 sentences × 4 levels × 3 seeds, 4,164
         outputs per condition.
       - Pooled: fit 34.9 % [32.5, 37.3] without the loop and 64.7 %
         [62.1, 67.2] with it.
       - Fit & complete: 14.2 % [12.4, 16.1] and 38.4 % [35.7, 41.2].
       - Paired differences: +29.8 points [27.2, 32.4] fit, and +24.3
         [22.2, 26.3] fit & complete.
       - The gain in fit & complete shrinks with the level: +56.7 points at
         90 %, +28.5 at 80 %, +10.2 at 70 %, and +1.6 [−0.6, +3.8] at 60 %.
       - At 60 % the loop does not improve fit (−1.5 points [−5.6, +2.5]): it
         keeps the meaning (NLI kept 52 % → 96 %) and outputs run long.
     - **French test result (2026-10-11, job 2636593, run commit 68492f2;
       `results/step2_test.md`).**
       - 332 sentences × 4 levels × 3 seeds, 3,984 outputs per condition.
       - Pooled: fit 34.4 % [31.7, 37.0] without the loop and 67.6 %
         [65.0, 70.2] with it.
       - Fit & complete: 15.5 % [13.5, 17.6] and 44.2 % [41.3, 47.0].
       - Paired differences: +33.2 points [30.6, 35.8] fit, and +28.6
         [26.4, 30.9] fit & complete.
       - The gain in fit & complete: +61.7 points at 90 %, +32.9 at 80 %,
         +14.5 at 70 %, and +5.4 [3.2, 7.6] at 60 %.
       - French answers break JSON more often (2.9 % of rounds against 0.5 %),
         mostly with apostrophes escaped as `\'`. 11 items are left without
         an answer, and they count as failures.
   - **Step 4 on dev (2026-10-11, job 2636594, run commit 68492f2;
     `results/hpc_8b_step4_dev.md`; exploratory).**
     - Apertus 1.5 8B BF16; 97 German and 90 French dev sentences outside the
       go/no-go 50; seeds 0, 1 and 2.
     - Fit within ±10 % of the budget, (a) / (b) / (c):
       - EN → DE: 26.8 / 58.1 / 80.1 % with characters, and 13.4 / 66.0 /
         69.4 % with syllables.
       - EN → FR: 17.4 / 67.4 / 79.3 % with characters, and 60.7 / 46.7 /
         74.8 % with syllables.
     - Kept against the reference (NLI): (c) is about level with (a), and (b)
       is no better than (c).
   - **Insurance, if the HPC setup fails** (`scripts/local_step2_de_test.sh`).
     - The local setup: llama.cpp with Q4_K_M, and the judge Qwen3-8B.
     - Task: step 2 on German test, levels 90 and 80, seed 0.
     - About 5 h on the Apple M3 (an estimate from the pilot: 694 items at
       15.6 s, then 1,388 outputs judged at about 5.4 s).

## Stretch: isochrony

Only after steps 1–4. English slots will come from VAD-trimmed audio, which
replaces the current librosa trimming. Outputs will be measured in TTS
seconds, trimmed the same way. A line fits when its spoken length is within
±10 % of the slot. Until then, the `slot_s` and `ref_tgt_s` fields are not
used.

## Still open

- The HPC runs themselves (kit ready, see `docs/hpc.md`). Each run records its
  endpoint, backend and quantisation.
- The judge for the final runs: decided on 2026-10-10 by the rule fixed
  beforehand. Qwen3-14B is the main judge (see the judge section above). It
  is not clearly better than Qwen3-8B (p = 0.34), and it misses half the lost
  qualifiers. So the native-speaker check still carries the meaning results
  for qualifiers.
- Which outputs the 50 native-speaker lines come from, and who checks them.
- A native-speaker review of the NLI control pairs.
- A near-tie test on paired differences, instead of overlapping intervals
  (suggested by the pilot). For step 2 on test, the report now gives the
  loop's effect as a paired difference (v2.12); the recommendation rule
  itself is unchanged.
- A native-speaker review of the hard judge controls.

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
  go/no-go on step 2 (commit `fa777d8`).
- 2026-10-06, v2.1: decided the generation settings, prompts (v1, JSON with 4
  candidates), syllable counter (eSpeak NG), NLI model and sanity suite, judge
  (deferred to the HPC) and the step 4 meaning check. The v2 choices are
  confirmed: German step 1, "without selection" = first candidate, (c) keeps a
  translation that already fits, a random go/no-go sample pooled over seeds,
  and (b)/(c) inherit the better step 3 setting. Added: the go/no-go scores
  the closest candidate. Step 3's 4 candidates now come from one JSON answer,
  not 4 samples.
- 2026-10-09, v2.2: German years are counted as spoken years. The
  syllable-counter accuracy and its remaining errors are documented.
- 2026-10-09, v2.3, before the go/no-go run: prompt v1 frozen (hash above);
  the local model artefact recorded; smoke test passed; the language check now
  uses a character n-gram identifier.
- 2026-10-09, v2.4, before any go/no-go output was scored or read: the
  sampling is made explicit (temperature then top_p, no top_k or min_p), and
  decade forms are read as years. The first go/no-go generation is superseded
  and the go/no-go is generated again. The scorer only decides for a
  complete, frozen-prompt run with unchanged targets.
- 2026-10-09, v2.5: go/no-go result recorded (NO-GO) and declared final: it
  is not re-run or re-scored. The NLI now loads in float32 explicitly. The
  NLI-leniency caveat is added. Phase 2 (exploratory) is defined: error
  analysis, prompt v2 variants, the repair loop, a final meaning judge
  (Qwen3-8B, evaluation only) and a pilot on dev sentences outside the
  go/no-go 50. Final numbers stay on test.
- 2026-10-09, v2.6, before any pilot output was judged: each repair round gets
  its own seed, and retries are logged. The first pilot generation is
  superseded. Fixes from the code review: no-output handling, reproducible
  intervals, the judge's placeholder and server guards, and the record of the
  NLI used in judge validation.
- 2026-10-10, v2.7, before any judge v2 result: the judge prompt selection
  rule (tune on half A of the control suite, choose on held-out half B).
  The pilot report gets the "fit & complete" success measure and a
  recommendation rule (highest rate, near-ties broken by time), fixed before
  any judge output of the pilot.
- 2026-10-10, v2.8: pilot result recorded (exploratory). v1 with the repair
  loop is recommended for the full runs. The rule is applied to the
  both-levels table, which it did not name. Caveats added: the judge is
  lenient, and the loop has no language check. Open items for the full runs
  added.
- 2026-10-10, v2.9: decided: v1 with the repair loop is the method, and v2a
  is dropped. Added: the language check in the loop (py3langid, wrong
  language = another language at p ≥ 0.9), with the pilot re-scored; the hard
  judge controls, and Qwen3-8B's result on them; the full-run plan (HPC kit,
  local insurance run).
- 2026-10-10, v2.10: step 4 implemented (selection, units, budgets, seeds, as
  above) and smoke-tested locally on 5 dev sentences per language. The repair
  loop now takes a unit (syllables by default, characters for step 4). The
  HPC setup was adapted to the cluster's per-connection throttling: chunked,
  digest-checked downloads (`docs/hpc.md`).
- 2026-10-10, v2.11: judge for the full runs decided. Qwen3-14B (BF16, vLLM)
  passed the rule fixed before its result (17 of 27 qualifier and modal
  changes, against 13, lower in neither), so it is the main judge. The paired
  difference is within noise (p = 0.34), which is recorded with the decision.
  Results made on the cluster now record their commit through `hpc/sync.sh`
  (the copy there is not a git checkout).
- 2026-10-10, v2.12: before any step 2 output on test exists, the step 2
  report (`isochron.step2_report`) adds the effect of the repair loop: with
  minus without, in percentage points, for fit, fact recall, added-fact rate
  and fit & complete, pooled and per level. Its 95 % interval is a paired
  bootstrap: sentences are resampled once per resample (10,000, seed 0), and
  both conditions are scored on the same resample. The per-condition
  intervals stay as they were.
- 2026-10-11, v2.13: the step 2 result on German test is recorded (section
  "Phase 2", item 6). French and step 4 on dev are still running. The method
  and the metrics are unchanged.
- 2026-10-11, v2.14: the step 2 result on French test is recorded. The
  method and the metrics are unchanged.
- 2026-10-11, v2.15: step 4 on dev (exploratory) is recorded. No step 4
  test run is planned yet.
- 2026-10-12, v2.16: analysis only, with no new generation or judging. Fit and fit & complete after each
  round of the loop are computed from the logged test runs (`isochron.rounds`,
  `results/step2_test_rounds.md`). Where the judge never scored a round's best candidate, fit & complete
  is given as a low–high range. The method and the metrics are unchanged.
- 2026-10-12, v2.17: step 4 frozen for the test run before generation:
  prompts with hashes, systems, budgets, seeds and scoring. The final judge
  joins the step 4 scoring, validated on cross-lingual versions of both
  suites. The method is unchanged.
