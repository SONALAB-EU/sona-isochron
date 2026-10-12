# Native-speaker check

The protocol (`docs/eval_protocol.md`, "Native-speaker check") pre-registers this check. A native speaker
of German reads 50 lines without knowing which system produced each one. We then report how often each
system keeps the meaning, and how often the native speaker agrees with the automatic meaning checks: the
NLI that the loop also uses, a second NLI the loop never sees, and the final judge.

Since 2026-10-12 (protocol v2.21, before any line was rated) the sheet holds step 4 outputs, English →
German, so the checker compares each German line with its English source. The earlier step 2 sheet is
kept as a backup.

## The files

| File | For | What it is |
|------|-----|------------|
| `results/native_check/step4_sheet_de.csv` | the German checker | 50 rows: an English sentence and a German translation of it, with empty columns to fill |
| `results/native_check/step4_key_de.csv` | us only, **never the checker** | which system produced each line, and the verdicts of both NLI models and the judge |
| `results/native_check/step2_sheet_de.csv`, `step2_key_de.csv` | backup | the step 2 sheet: a German sentence and a shortened version of it (instructions below) |
| `results/native_check/controls_de.csv` | a German checker (optional, second task) | 160 control pairs written by Claude, each with the property it should have |
| `results/native_check/controls_fr.csv` | a French checker (optional) | the same for 80 French pairs |

`isochron.native_check` built them, with fixed seeds:

```
uv run python -m isochron.native_check build-step4 results/raw/hpc_8b_step4_test --nli-cache results/raw/step4_test_nli_cache.jsonl --nli2-cache results/raw/meaning_check/step4_cache.jsonl
uv run python -m isochron.native_check build results/raw/hpc_8b_step2_de_test
uv run python -m isochron.native_check controls
```

How the 50 step 4 lines are chosen (`build-step4`):
- 25 English test sentences, drawn with a fixed seed from those where both systems have a German output
  for generation seed 0.
- For each sentence, two lines: the plain translation (a), and ours (c): the translation shortened to the
  syllable budget with the repair loop.
- In 5 of the 25, (c) kept the plain translation, because it already fitted the budget, so both lines
  read the same. They stay in, because the rule chose them.
- The 50 rows are shuffled, and the sheet shows nothing that tells the system.

The files are CSV in UTF-8, with a byte-order mark so that Excel, Numbers and LibreOffice show umlauts
correctly.

## Instructions for the checker (step4_sheet_de.csv)

Each row has an **English sentence** and a **German translation** of it, which may be shorter than a
full translation. Read both and fill in:

| Column | Write | When |
|--------|-------|------|
| `meaning` | kept, minor loss or wrong (erhalten, kleiner Verlust, falsch) | kept: the German says everything the English says. Minor loss: a detail is missing or weaker, such as a number, a name, a time, a condition, or words such as *almost*, *very*, *local*, *according to the police*. Wrong: the German says something else, or misses the main point. |
| `added_info` | yes or no (ja / nein) | yes if the German says something the English does not: a new fact, a detail, or a stronger claim |
| `natural_german` | yes or no (ja / nein) | yes if it is correct, natural German that you would accept in a dubbed film |
| `comment` | optional | what was lost, added or unnatural, in a few words |

- Shorter wording is fine as long as nothing is lost. A shorter line is not a minor loss by itself.
- Judge each row on its own. Two rows can read the same; mark both.
- Please do not use a dictionary, a translator or a chatbot. About 30–45 minutes in total.
- Return the filled file under any name.

## Instructions for the backup sheet (step2_sheet_de.csv)

Each row has an **original** German sentence and a **shortened** version. Fill in `adds_information` and
`drops_information` (yes or no), `grammar_problem` (optional) and `comment` (optional), with the same
meaning as above. Two shortened lines are identical to their originals; mark them like any other row.

## Instructions for the control sheets (controls_de.csv, controls_fr.csv)

Each row has an original sentence, a variant, and the property the variant should have (`should_be`; for
the hard controls, `edit` shows the change). In `correct_as_described`, write yes if the variant really
has that property, no otherwise. Add a comment when it is no. Examples:
- A "same meaning" variant that changes the meaning is no.
- A "qualifier changed" variant whose change makes no difference to the meaning is no.

## Scoring

```
uv run python -m isochron.native_check score FILLED_SHEET.csv
```

The scorer recognises which sheet it was given.
- **Step 4 sheet:** it writes `results/native_check_step4_agreement.md`.
  - Per system: the share of lines kept, with a minor loss, wrong, adding information, and natural, each
    with a 95 % Wilson interval.
  - Agreement, as the share of lines and Cohen's kappa, with each automatic check: both NLI models
    against the reference and against the English source, and the judge.
- **Step 2 sheet:** it writes `results/native_check_agreement.md`, with agreement on added and dropped
  information.

Lines left empty are skipped and counted.
