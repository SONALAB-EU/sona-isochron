---
license: cc-by-sa-4.0
language:
- en
- de
- fr
pretty_name: 'isochron: length-fitted dubbing translations by Apertus 1.5'
task_categories:
- translation
tags:
- dubbing
- isochrony
- length-control
- apertus
- llm-as-a-judge
- natural-language-inference
annotations_creators:
- machine-generated
language_creators:
- found
- machine-generated
multilinguality:
- translation
source_datasets:
- google/fleurs
size_categories:
- 10K<n<100K
dataset_info:
- config_name: step4_responses
  features:
  - name: row_id
    dtype: string
  - name: case_id
    dtype: string
  - name: split
    dtype: string
  - name: split_role
    dtype: string
  - name: run
    dtype: string
  - name: lang
    dtype: string
  - name: fleurs_id
    dtype: string
  - name: seed
    dtype: int64
  - name: budget
    dtype: string
  - name: unit
    dtype: string
  - name: target
    dtype: int64
  - name: system
    dtype: string
  - name: system_name
    dtype: string
  - name: post_hoc
    dtype: bool
  - name: output_text
    dtype: string
  - name: no_output
    dtype: bool
  - name: language_label
    dtype: string
  - name: language_p
    dtype: float64
  - name: wrong_language
    dtype: bool
  - name: usable
    dtype: bool
  - name: output_chars
    dtype: int64
  - name: output_words
    dtype: int64
  - name: output_syllables
    dtype: int64
  - name: output_length
    dtype: int64
  - name: ratio
    dtype: float64
  - name: compression_vs_a
    dtype: float64
  - name: fit
    dtype: bool
  - name: nli_ref_kept
    dtype: bool
  - name: nli_ref_added
    dtype: bool
  - name: nli_ref_dropped
    dtype: bool
  - name: nli_src_kept
    dtype: bool
  - name: nli2_ref_kept
    dtype: bool
  - name: nli2_ref_added
    dtype: bool
  - name: nli2_ref_dropped
    dtype: bool
  - name: nli2_src_kept
    dtype: bool
  - name: judge_valid
    dtype: bool
  - name: judge_recall
    dtype: float64
  - name: judge_n_facts
    dtype: int64
  - name: judge_dropped
    dtype: int64
  - name: judge_changed
    dtype: int64
  - name: judge_added_count
    dtype: int64
  - name: judge_added_any
    dtype: bool
  - name: judge_facts
    list:
    - name: fact
      dtype: string
    - name: status
      dtype: string
  - name: judge_added
    list: string
  - name: fit_and_complete
    dtype: bool
  - name: kept_plain
    dtype: bool
  - name: loop_revisions
    dtype: int64
  - name: loop_rounds
    dtype: int64
  - name: loop_retries
    dtype: int64
  - name: loop_rounds_without_candidate
    dtype: int64
  - name: a_tries
    dtype: int64
  - name: b_parse_error
    dtype: string
  - name: b_candidates
    dtype: int64
- config_name: step4_inputs
  features:
  - name: case_id
    dtype: string
  - name: split
    dtype: string
  - name: split_role
    dtype: string
  - name: lang
    dtype: string
  - name: fleurs_id
    dtype: string
  - name: source_en
    dtype: string
  - name: reference
    dtype: string
  - name: budget_chars
    dtype: int64
  - name: budget_syllables
    dtype: int64
  - name: source_chars
    dtype: int64
  - name: source_syllables
    dtype: int64
  - name: license
    dtype: string
- config_name: step2_responses
  features:
  - name: row_id
    dtype: string
  - name: case_id
    dtype: string
  - name: split
    dtype: string
  - name: split_role
    dtype: string
  - name: run
    dtype: string
  - name: variant
    dtype: string
  - name: prompt
    dtype: string
  - name: lang
    dtype: string
  - name: fleurs_id
    dtype: string
  - name: level
    dtype: int64
  - name: seed
    dtype: int64
  - name: condition
    dtype: string
  - name: output_text
    dtype: string
  - name: no_output
    dtype: bool
  - name: output_syllables
    dtype: int64
  - name: output_chars
    dtype: int64
  - name: output_words
    dtype: int64
  - name: target_syllables
    dtype: int64
  - name: ratio
    dtype: float64
  - name: fit
    dtype: bool
  - name: language_label
    dtype: string
  - name: language_p
    dtype: float64
  - name: wrong_language
    dtype: bool
  - name: nli_forward
    dtype: string
  - name: nli_backward
    dtype: string
  - name: nli_kept
    dtype: bool
  - name: nli_added
    dtype: bool
  - name: nli_dropped
    dtype: bool
  - name: judge_valid
    dtype: bool
  - name: judge_recall
    dtype: float64
  - name: judge_n_facts
    dtype: int64
  - name: judge_dropped
    dtype: int64
  - name: judge_changed
    dtype: int64
  - name: judge_added_count
    dtype: int64
  - name: judge_added_any
    dtype: bool
  - name: judge_facts
    list:
    - name: fact
      dtype: string
    - name: status
      dtype: string
  - name: judge_added
    list: string
  - name: fit_and_complete
    dtype: bool
  - name: rounds
    dtype: int64
  - name: retries
    dtype: int64
  - name: time_s
    dtype: float64
- config_name: step2_inputs
  features:
  - name: case_id
    dtype: string
  - name: split
    dtype: string
  - name: split_role
    dtype: string
  - name: lang
    dtype: string
  - name: fleurs_id
    dtype: string
  - name: level
    dtype: int64
  - name: input_text
    dtype: string
  - name: input_syllables
    dtype: int64
  - name: target_syllables
    dtype: int64
  - name: source_en
    dtype: string
  - name: license
    dtype: string
- config_name: judge_controls
  features:
  - name: pair_id
    dtype: string
  - name: suite
    dtype: string
  - name: lang
    dtype: string
  - name: source_lang
    dtype: string
  - name: fleurs_id
    dtype: string
  - name: control
    dtype: string
  - name: source
    dtype: string
  - name: output
    dtype: string
  - name: edit
    dtype: string
  - name: nli_forward
    dtype: string
  - name: nli_backward
    dtype: string
  - name: nli_correct
    dtype: bool
  - name: nli2_forward
    dtype: string
  - name: nli2_backward
    dtype: string
  - name: nli2_correct
    dtype: bool
  - name: judge_correct
    dtype: bool
  - name: judge_invalid
    dtype: bool
  - name: split
    dtype: string
- config_name: metadata
  features:
  - name: instance_id
    dtype: string
  - name: split
    dtype: string
  - name: lang
    dtype: string
  - name: fleurs_id
    dtype: string
  - name: license
    dtype: string
  - name: source
    dtype: string
  - name: note
    dtype: string
  - name: used_in
    list: string
- config_name: runs
  features:
  - name: run
    dtype: string
  - name: step
    dtype: int64
  - name: split
    dtype: string
  - name: split_role
    dtype: string
  - name: date
    dtype: string
  - name: git_commit
    dtype: string
  - name: model
    dtype: string
  - name: quantisation
    dtype: string
  - name: backend
    dtype: string
  - name: langs
    list: string
  - name: seeds
    list: int64
  - name: prompts
    list:
    - name: name
      dtype: string
    - name: sha256
      dtype: string
  - name: judge_model
    dtype: string
  - name: judge_quantisation
    dtype: string
  - name: judge_git_commit
    dtype: string
  - name: config_json
    dtype: string
  - name: judge_config_json
    dtype: string
configs:
- config_name: step4_responses
  default: true
  data_files:
  - split: dev
    path: step4_responses/dev.jsonl
  - split: test
    path: step4_responses/test.jsonl
- config_name: step4_inputs
  data_files:
  - split: dev
    path: step4_inputs/dev.jsonl
  - split: test
    path: step4_inputs/test.jsonl
- config_name: step2_responses
  data_files:
  - split: dev
    path: step2_responses/dev.jsonl
  - split: test
    path: step2_responses/test.jsonl
- config_name: step2_inputs
  data_files:
  - split: dev
    path: step2_inputs/dev.jsonl
  - split: test
    path: step2_inputs/test.jsonl
- config_name: judge_controls
  data_files:
  - split: controls
    path: judge_controls/controls.jsonl
- config_name: metadata
  data_files:
  - split: dev
    path: metadata/dev.jsonl
  - split: test
    path: metadata/test.jsonl
  - split: controls
    path: metadata/controls.jsonl
- config_name: runs
  data_files:
  - split: dev
    path: runs/dev.jsonl
  - split: test
    path: runs/test.jsonl
---

# Dataset Card for isochron: length-fitted dubbing translations by Apertus 1.5

This dataset holds every test case, every model output and every per-line score of the isochron project
(Hack Apertus 2026, Track 2B). The project adapts dubbing translations so that the target line fits the
source line's length, without adding or dropping meaning, using Apertus 1.5 8B. Two experiments are
included:

- **Step 4, translation to a length budget** (the main result). An English FLEURS sentence is translated
  into German or French so that it fits a budget in characters (isometric) or in syllables
  (isosyllabic). Three systems are compared: (a) plain translation, (b) one prompt asking for the budget,
  and (c) translate, then shorten with a repair loop (ours).
- **Step 2, shortening in the same language** (the engine). A German or French FLEURS sentence is
  shortened to 90, 80, 70 or 60 % of its syllables, without and with the repair loop.

The **dev** split is exploratory: prompts and settings were chosen on it. The **test** split holds the
reported numbers, and everything was frozen before any test output existed. No audio is included.

## Dataset Details

- **Curated by:** the isochron team, Hack Apertus 2026, Track 2B
- **Funded by [optional]:** SONALAB
- **Shared by [optional]:** SONALAB
- **Language(s) (NLP):** English (sources), German and French (references and outputs)
- **License:** CC BY-SA 4.0 (see [Data Instance Licenses](#data-instance-licenses))
- **Git repository:** [More Information Needed]

## Uses

### Direct Use

- Reproducing every number reported for step 2 and step 4. Each table in the project's results files
  can be recomputed from these files alone (see [Data Processing and Quality Control](#data-processing-and-quality-control)).
- Studying length-controlled translation and shortening by an LLM: how often each system fits a budget,
  how much meaning it loses, and how different meaning checks disagree on the same lines.
- Studying meaning checks themselves: `judge_controls` gives two NLI models' and an LLM judge's
  verdicts on 680 planted meaning changes, and `step4_responses` gives both NLI models' verdicts and
  the judge's per-fact verdicts on the same 16,296 outputs.

### Out-of-Scope Use

- Training a production dubbing or translation system. The outputs are machine-generated, are not
  checked by native speakers, and include outputs that drop or change meaning (by design: they are the
  measured failures).
- Treating the judge's fit & complete rate or fact recall as a measurement of meaning preservation.
  They are upper bounds (see [Risks, Bias, and Limitations](#risks-bias-and-limitations)).
- Treating fit as fit in seconds. No speech was synthesised; length is measured in characters and in
  eSpeak NG syllables.
- Any use the source licences or the Apertus 1.5 Acceptable Use Policy do not permit.

## Specifications

### Metrics

Every metric is a field of every response row, so each can be recomputed.

- **Fit ±10 %:** the output is within ±10 % of the target in the target's unit: characters without spaces
  (isometric), or syllables counted by eSpeak NG 1.52.0 phonemes (isosyllabic, and all of step 2). A
  missing output, or one in the wrong language, is a miss.
- **Language check:** py3langid 0.4.0, restricted to de/en/fr/it. An output is in the wrong language
  when the top label is another language with probability ≥ 0.9. It then counts as a failure everywhere.
- **Kept (NLI):** entailment in both directions. Added: the output is not entailed by the premise.
  Dropped: the premise is not entailed by the output.
  - Step 4, main check: against the human reference translation (monolingual). Secondary: against the
    English source (cross-lingual).
  - Step 4, second NLI (post-hoc, added after test outputs existed): the same checks with a model that
    the repair loop never sees.
  - Step 2: the loop's own check, against the input sentence. The reports use it as a screen only.
- **Judge (evaluation only, never seen by the loop):** the judge lists the facts of the source once,
  then marks each fact as kept, changed or dropped in the output, and lists added facts.
  - Fact recall = kept ÷ facts.
  - Fit & complete = fits, and the judge keeps every fact and finds nothing added.
  - In step 4 the facts are listed from the English source. In step 2 they are listed from the input.
- **Rounds:** revision rounds of the repair loop after round 0 (0 to 2), with retries after an
  unusable answer counted separately.
- Intervals in the results files: bootstrap over sentences (each carrying all its seeds and levels),
  10,000 resamples, seed 0.

### Headline numbers (step 4, test)

Fit ±10 % and kept vs reference (main NLI) in %, from `results/step4_test.md`. Recomputed from
`step4_responses/test.jsonl`, they match exactly.

| Direction, budget | (a) plain translation: fit / kept | (b) one step to the budget: fit / kept | (c) translate, then shorten: fit / kept |
|---|---|---|---|
| EN → DE, characters | 27.2 / 79.5 | 59.4 / 74.1 | 80.2 / 80.6 |
| EN → DE, syllables | 19.6 / 79.5 | 71.6 / 76.8 | 70.3 / 81.6 |
| EN → FR, characters | 23.9 / 79.7 | 59.8 / 69.7 | 77.3 / 80.7 |
| EN → FR, syllables | 55.6 / 79.7 | 44.7 / 74.9 | 69.9 / 81.5 |

Under the second NLI, (c) keeps the meaning 2.8–5.3 points less often than plain translation in three of
the four settings (`results/step4_test_nli2.md`). The results files give the intervals, the paired
differences and the judge's numbers.

## Dataset Structure

The template's three components map to seven JSONL configs. Load one with
`datasets.load_dataset("<repo>", "<config>")`.

| Component | Config | Splits and rows | One row per |
|---|---|---|---|
| Evaluation dataset | `step4_inputs` | dev 187, test 679 | sentence and target language |
| Evaluation dataset | `step2_inputs` | dev 60, test 2,716 | sentence, language and level |
| Model responses | `step4_responses` | dev 3,366, test 16,296 | sentence, seed, budget and system |
| Model responses | `step2_responses` | dev 480, test 16,296 | sentence, level, seed, prompt variant and condition |
| Model responses | `judge_controls` | controls 680 | planted control pair, with every check's verdict |
| Metadata | `metadata` | dev 187, test 679, controls 680 | sentence or control pair, with its licence and source |
| Metadata | `runs` | dev 5, test 4 | generation run, with its full configuration |

Responses link to inputs by `case_id`, and to runs by `run`. Metadata rows link by `split`, `lang` and
`fleurs_id` (sentences) or by `instance_id` = `controls/` + `pair_id` (controls). `export.json` names
the raw runs and the git commit of the export.

### Fields

Fields that do not apply to a row are `null`.

**`step4_inputs`:**
- `case_id`, `split`, `split_role` (`exploratory` or `reported`), `lang` (target language), `fleurs_id`
- `source_en`: the English source
- `reference`: the human reference translation
- `budget_chars`: the English characters without spaces
- `budget_syllables`: the English syllables × the target/English syllable-rate ratio (de 0.964, fr 1.160),
  rounded half up
- `source_chars`, `source_syllables`, `license`

**`step4_responses`:**
- Keys: `row_id`, `case_id`, `split`, `split_role`, `run`, `lang`, `fleurs_id`, `seed` (0, 1, 2)
- Setting: `budget` (`isometric`, `isosyllabic`), `unit` (`chars`, `syllables`), `target`
- System: `system` (`a`, `b`, `c`, or `b_tolerant` on test only), `system_name`. `post_hoc` is true for
  `b_tolerant`: (b)'s answers that strict JSON rejected, re-read with `\'` as `'` (a sensitivity analysis,
  added after test outputs existed; never judged). (a) is the same translation under both budgets, so
  it appears once per budget.
- Output: `output_text` (null when there is no output), `no_output`, `language_label`, `language_p`,
  `wrong_language`, `usable` (an answer in the right language)
- Lengths: `output_chars`, `output_words`, `output_syllables`; `output_length` (in the budget's unit);
  `ratio` (output ÷ target); `compression_vs_a` (output ÷ (a), in the budget's unit); `fit`
- Main NLI: `nli_ref_kept`, `nli_ref_added`, `nli_ref_dropped` (against the reference), and
  `nli_src_kept` (against the English source)
- Second NLI, test only: `nli2_ref_kept`, `nli2_ref_added`, `nli2_ref_dropped`, `nli2_src_kept`
- Judge, test only: `judge_valid`, `judge_recall` (0 for a wrong-language output), `judge_n_facts`,
  `judge_dropped`, `judge_changed`, `judge_added_count`, `judge_added_any`, `judge_facts` (the list of
  {`fact`, `status`}), `judge_added` (the added facts), and `fit_and_complete`
- (c) only: `kept_plain` ((a) kept because it was at most 1.10 × the budget), `loop_revisions`,
  `loop_rounds`, `loop_retries`, `loop_rounds_without_candidate` (rounds whose answer was not valid JSON)
- (a) only: `a_tries` (asks again after unparsable JSON, at most 3 times)
- (b) and `b_tolerant` only: `b_parse_error` (null when the answer parsed), `b_candidates` (the number
  of candidates returned; 4 were asked for)

**`step2_inputs`:**
- `case_id`, `split`, `split_role`, `lang`, `fleurs_id`, `level` (90, 80, 70, 60)
- `input_text`: the FLEURS sentence in German or French
- `input_syllables`
- `target_syllables`: level % of the input's syllables
- `source_en`: the English FLEURS sentence, for reference; the task never sees it
- `license`

**`step2_responses`:**
- Keys: `row_id`, `case_id`, `split`, `split_role`, `run`, `lang`, `fleurs_id`, `level`, `seed`
- Prompt: `variant` (`v1` on test; `v1`, `v2a`, `v2b`, `v2c` on dev), `prompt` (its name)
- `condition`: `without` is the closest round-0 candidate, `with` is the repair loop's final output. Both
  come from the same generation.
- Output: `output_text`, `no_output`, `output_syllables`, `output_chars`, `output_words`,
  `target_syllables`, `ratio`, `fit`, `language_label`, `language_p`, `wrong_language`
- The loop's NLI against the input: `nli_forward`, `nli_backward` (labels), `nli_kept`, `nli_added`,
  `nli_dropped`
- Judge: the same `judge_*` fields as in step 4, and `fit_and_complete`
- Loop: `rounds` (revision rounds), `retries`, `time_s` (seconds per output: round 0 without the loop;
  every round with it, NLI included)

**`judge_controls`:**
- `pair_id`, `suite`, `lang` (the output's language), `source_lang`, `fleurs_id`, `split`
- `control`: identity, paraphrase, clause_deleted, clause_inserted, negation, same_meaning,
  modal_changed, number_changed, qualifier_changed or fact_inserted
- `source`, `output`, `edit` ("old → new" for the hard edits)
- Main NLI: `nli_forward`, `nli_backward`, `nli_correct`. Second NLI: `nli2_forward`, `nli2_backward`,
  `nli2_correct`. Correct means the verdict matches the control type, by the rule in the validation
  reports.
- Qwen3-14B judge: `judge_correct`, `judge_invalid`. These come from the committed validation reports
  (`results/judge_validation_*_v3_qwen3-14b_hpc_8b.md`), which list every pair judged wrong or invalid.
  The judge's per-fact answers on the controls are not in this dataset.
- Suites:
  - `nli` (200 pairs): German and French sources
  - `hard` (140 pairs): German sources, one modal, number or qualifier change, one inserted fact, or a
    same-meaning edit
  - `nli_xl` and `hard_xl`: the same pairs with the English original as the source (cross-lingual, as
    in step 4)

**`metadata`:** `instance_id`, `split`, `lang`, `fleurs_id`, `license`, `source` (FLEURS repository,
revision, configs and split), `note`, `used_in` (`step2`, `step4`, `judge_controls`).

**`runs`:**
- `run`, `step`, `split`, `split_role`, `date`, `git_commit` (the commit the run was made from)
- Model: `model`, `quantisation`, `backend`
- `langs`, `seeds`, `prompts` (names and SHA-256)
- Judge: `judge_model`, `judge_quantisation`, `judge_git_commit`
- `config_json` and `judge_config_json`: the run's full configuration as recorded. Local model paths are
  removed, and endpoints are named only as loopback servers.

### Splits

- **dev (exploratory).**
  - Step 2: the phase 2 pilot. 30 German FLEURS dev sentences outside the 50 go/no-go sentences, levels
    90 and 80 %, seed 0, four prompt variants. Apertus 1.5 8B ran as Q4_K_M GGUF under llama.cpp; the
    judge was Qwen3-8B (Q4_K_M).
  - Step 4: every German (97) and French (90) dev sentence outside the go/no-go sentences, seeds 0–2.
    Apertus ran in BF16 under vLLM. There was no judge on dev.
- **test (reported).**
  - Step 2: every German (347) and French (332) FLEURS test sentence × levels 90/80/70/60 × seeds 0–2.
  - Step 4: the same sentences × seeds 0–2 × both budgets × all systems.
  - Apertus 1.5 8B in BF16 under vLLM, one H100 per language; judge Qwen3-14B in BF16.
- **controls.** The planted control pairs, built from FLEURS train sentences.

## Dataset Creation

### Curation Rationale

Dubbing needs a translation that fits the time the original line takes, without adding or dropping
meaning. The dataset records every output, so that fit and meaning loss can be checked line by line,
and so that the reported numbers can be recomputed independently of the project's code.

### Source Data

| Source | Role | Revision | Licence |
|---|---|---|---|
| FLEURS (Conneau et al., 2022), configs `en_us`, `de_de`, `fr_fr` | Sentences and reference translations: `validation` (our dev), `test`, and `train` for the controls | `google/fleurs` @ `70bb2e84b976b7e960aa89f1c648e09c59f894dd` | CC BY 4.0 |
| FLoRes-101 (Goyal et al., 2022) | Origin of the FLEURS text | Meta's public archive | CC BY-SA 4.0 |
| Apertus 1.5 8B (Swiss AI Initiative) | Generates every output: BF16 on dev and test | `swiss-ai/Apertus-v1.5-8B` @ `a411d838600baf0e3635a3daf66fb7c55fc97bb6` | Apache-2.0, plus the Apertus 1.5 Acceptable Use Policy |
| apertus-v1.5-8b-text Q4_K_M GGUF | Generates the step 2 dev pilot | `Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF` @ `248ec68a63e219e3f061e4c946fc8a20d63b9975` (from `andreasmartin/apertus-v1.5-8b-text` @ `c0e7eeb`) | Apache-2.0, Apertus 1.5 AUP |
| Qwen3-14B (Qwen team) | Judge on test, and on the control suites (evaluation only) | `Qwen/Qwen3-14B` @ `40c069824f4251a91eefaf281ebe4c544efd3e18`, BF16 | Apache-2.0 |
| Qwen3-8B Q4_K_M GGUF (Qwen team) | Judge of the step 2 dev pilot (evaluation only) | `Qwen/Qwen3-8B-GGUF` @ `7c41481f57cb95916b40956ab2f0b139b296d974` | Apache-2.0 |
| mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 (Laurer) | Main NLI: inside the repair loop and in the evaluation | `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` @ `b5113eb38ab63efdd7f280f8c144ea8b13f978ce` | MIT |
| bge-m3-zeroshot-v2.0-c (Laurer) | Second NLI, post-hoc, never used by the loop | `MoritzLaurer/bge-m3-zeroshot-v2.0-c` @ `705510dfe0f35d223a4bf6f5d2695ec5fd162341` | MIT |
| eSpeak NG 1.52.0 | Syllable counts (from phonemes) | 1.52.0 | GPL-3.0-or-later (program only; nothing redistributed) |
| py3langid 0.4.0 | Language check | 0.4.0 | BSD-3-Clause |

The repository's `docs/licences.md` gives full attribution for each source.

#### Data Collection

- **Protocol:** `docs/eval_protocol.md`, version 2.23 at export. Step 2 was frozen for test in v2.12 and
  step 4 in v2.17, before any test output existed. The second NLI (v2.20) and the JSON sensitivity row
  are post-hoc, added after test outputs existed, and are marked as such.
- **Generation:** temperature 0.7, top-p 0.95, top-k 0, min-p 0, max 1,024 tokens, thinking off.
  - Seeds 0, 1 and 2 per sentence (the step 2 dev pilot: seed 0).
  - Step 4 (a) and (b) use the item seed. The repair loop uses item seed + 1000 × round.
  - The judge runs at temperature 0, seed 0.
- **Prompts** (name: first 12 hex digits of SHA-256; the full hashes are in `runs`):

  | Step | Prompts |
  |---|---|
  | Step 4 | `translate_plain_v1` 5fe6dd58bf7e, `translate_budget_chars_v1` e81efebd7d4f, `translate_budget_syllables_v1` a3ffa4ea51a7, `shorten_chars_v1` 004890c41f25, `shorten_syllables_v1` fe4fbfdd800d, `revise_chars_v1` 62a308e266ab, `revise_v1` ab0593b9716e |
  | Step 2 test | `shorten_syllables_v1` fe4fbfdd800d with `revise_v1` ab0593b9716e |
  | Judge | `judge_facts_v1` 80c765ed80de, `judge_fact_v3` 5b74445c3470, `judge_added_v3` 61d024e29891 (mode perfact_v3) |

- **Backends:** vLLM 0.23.1rc1.dev1029+ga601a9d99 on H100 GPUs (dev and test), and llama.cpp
  llama-server b11429 (step 2 dev pilot).
- **Git commits** of the runs: step 2 test 68492f2, step 4 dev 68492f2, step 4 test 7b22d93, second NLI
  f0e566c. The export's commit is in `export.json`.

#### Data Processing and Quality Control

`isochron.hf_export build` reads the raw runs and scores every output with the project's own
report code (`isochron.pilot_report`, `isochron.step4_report`, `isochron.meaning_check`).

- The step 4 test NLI scores come from the evaluation's cache: no test line was scored again.
- Step 4 dev's NLI scores were never cached, so they were scored again with the same model at the same
  revision (on Apple MPS; the dev report ran on CUDA). Every dev cell still matches.
- `isochron.hf_export check` recomputes the results tables from these files alone and compares them cell
  by cell with the committed results files. At export, all 1,206 cells were identical:

  | Results file | Cells |
  |---|---:|
  | `step4_test.md` | 304 |
  | `step4_test_nli2.md` | 130 |
  | `hpc_8b_step4_dev.md` | 156 |
  | `step2_test.md` | 260 |
  | `phase2_pilot.md` | 312 |
  | the four Qwen3-14B validation reports | 44 |

  The cells cover counts, means, the bootstrap intervals and the paired differences.

The export stores no audio, no model weights, no local paths, and no endpoints beyond "loopback". The
raw generation logs (prompts, every candidate of every round) are not included.

#### Source Data Producers and Data Subjects

The source sentences are FLoRes-101 sentences from English Wikinews, Wikijunior and Wikivoyage, and
their professional translations. FLEURS added read speech, which is not used here. The outputs are
machine-generated by Apertus 1.5. The controls' edited copies were written by Claude (an AI assistant).

#### Ownership and Consent Management

All source text is openly licensed (CC BY 4.0, CC BY-SA 4.0). The models used are openly licensed
(Apache-2.0 or MIT). No personal data was collected.

#### Data Instance Licenses

Every row is CC BY-SA 4.0, because the FLoRes text it contains is ShareAlike. The `license` field of
every input, metadata and control row says so. The model outputs are released under the same licence.
Apertus 1.5's Acceptable Use Policy applies to its use, not to its outputs' licence.

## Annotations

### Annotation Process

There are no human annotations yet. Every label is machine-made: the NLI models, the LLM judge, the
eSpeak NG syllable counter and the language identifier. The planted controls' types are known by
construction.

### Annotator Details

- The judge is Qwen3-14B (test) or Qwen3-8B (step 2 dev pilot). It is a different model family from
  Apertus, never feeds generation, and runs after it.
- The controls' edits were written by Claude (an AI assistant) and have not been reviewed by a native
  speaker.

## Risks, Bias, and Limitations

- **The judge's figures are upper bounds.**
  - On the cross-lingual hard controls (English source, German output; `hard_xl`), Qwen3-14B passes
    every identity and same-meaning pair.
  - But it catches only 0 of 14 qualifier changes, 4 of 13 modal changes and 5 of 20 inserted facts.
  - So fact recall and fit & complete overstate how much meaning is kept, and the added-fact rate
    (0.0–0.1 %) is far too low.
- **NLI caveats.**
  - The repair loop selects (c)'s candidates with the same NLI model that scores meaning here, so (c)'s
    main-NLI scores may be inflated. The second NLI was added to check this. Under it, (c) keeps the
    meaning less often than plain translation in three settings.
  - The second NLI is lenient on small changes. It catches 1 of 14 qualifier changes and 1 of 13 modal
    changes within German, so neither model settles the question.
  - Kept vs source is cross-lingual and weaker: on `nli_xl`, the main NLI keeps only 29 of 40 identity
    pairs.
- **The human check is pending.** A native-speaker rating of 25 step 4 test sources ((a) against (c),
  German, syllable budget) is under way. Its sheet and key are not in this dataset and will be added
  when the ratings are in. Until then, no meaning figure here is human-validated.
- **Fit is in text units, not seconds.** No speech was synthesised, and syllables come from eSpeak NG
  phonemes. FLEURS's timing fields are not used, because silence trimming fails on noisy recordings.
- **Broken JSON counts as a miss, as frozen.** In French with the character budget, (b) lost 83 of
  996 items this way. `b_tolerant` shows the effect of reading `\'` as `'`.
- **Coverage.** Two target languages (German and French), one domain (encyclopaedic and news-like
  sentences), one 8B model. The step 2 dev pilot is small (30 sentences, one seed) and used a quantised
  model and a different judge.

### Personally Identifiable Information

None was collected. FLoRes sentences can name public figures from news articles.

### Sensitive Information

None beyond what the FLoRes source sentences contain (news and travel topics).

### Recommendations

- Report fit together with a meaning check.
- Prefer the NLI against the reference over the judge, and show both NLI models where they disagree.
- Treat dev numbers as exploratory, and use test for comparisons.

## Citations [optional]

- Conneau, A. et al. (2022). FLEURS: Few-shot Learning Evaluation of Universal Representations of
  Speech. arXiv:2205.12446.
- Goyal, N. et al. (2022). The Flores-101 Evaluation Benchmark for Low-Resource and Multilingual
  Machine Translation. TACL 10.

## Glossary [optional]

- **Isometric:** a length budget in characters (without spaces).
- **Isosyllabic:** a length budget in syllables.
- **Repair loop:** up to two revision rounds that ask Apertus to fix a candidate's length. Candidates
  are checked with the syllable or character counter, the language check and the NLI. The judge is
  never used.
- **Go/no-go sentences:** 50 dev sentences used for an early decision, and left out of the later dev
  runs.

## More Information [optional]

The method, the protocol and the full results are in the project's repository (`technical_report.md`,
`docs/eval_protocol.md`, `results/`). The repository's code is Apache-2.0.

## Dataset Card Authors [optional]

The isochron team.

## Dataset Card Contact

[More Information Needed]
