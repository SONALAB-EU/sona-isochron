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
| `results/native_check/rater/german_lines.xlsx` | the German checker: **send only this file** | the 50 rows of `step4_sheet_de.csv`, in the same order, with drop-down lists for the three marks, and an instructions tab with three worked examples |
| `results/native_check/step4_sheet_de.csv` | the German checker, if they prefer CSV | 50 rows: an English sentence and a German translation of it, with empty columns to fill |
| `results/native_check/step4_key_de.csv` | us only, **never the checker** | which system produced each line, and the verdicts of both NLI models and the judge; the key to the XLSX too, which has the same line numbers |
| `results/native_check/step2_sheet_de.csv`, `step2_key_de.csv` | backup | the step 2 sheet: a German sentence and a shortened version of it (instructions below) |
| `results/native_check/controls_de.csv` | a German checker (optional, second task) | 160 control pairs written by Claude, each with the property it should have |
| `results/native_check/controls_fr.csv` | a French checker (optional) | the same for 80 French pairs |

`isochron.native_check` built them, with fixed seeds:

```
uv run python -m isochron.native_check build-step4 results/raw/hpc_8b_step4_test --nli-cache results/raw/step4_test_nli_cache.jsonl --nli2-cache results/raw/meaning_check/step4_cache.jsonl
uv run python -m isochron.native_check xlsx
uv run python -m isochron.native_check build results/raw/hpc_8b_step2_de_test
uv run python -m isochron.native_check controls
```

`xlsx` reads the committed `step4_sheet_de.csv`, so it needs no raw runs, and it gives the same bytes each
time. It writes into `results/native_check/rater/`, a folder that holds only the checker's file: it stops
if the folder holds a key.

How the 50 step 4 lines are chosen (`build-step4`):
- 25 English test sentences, drawn with a fixed seed from those where both systems have a German output
  for generation seed 0.
- For each sentence, two lines: the plain translation (a), and ours (c): the translation shortened to the
  syllable budget with the repair loop.
- In 5 of the 25, (c) kept the plain translation, because it already fitted the budget, so both lines
  read the same. They stay in, because the rule chose them.
- The 50 rows are shuffled, and the sheet shows nothing that tells the system, beyond the texts
  themselves: (c) is often shorter. In 4 of its 25 lines (c) had no final full stop; since v2.26 the sheet
  adds one to every line without terminal punctuation (`native_check.full_stop`, the same rule for both
  systems), so every line ends with a full stop. The rater, however, received the version before this
  rule (`results/native_check/returned/step4_sheet_de_as_rated.csv`). One difference is left: 3 of (a)'s lines put a phrase in
  quotation marks ('Anarchie', 'Hausmarken', "nicht schwerwiegend"); none of (c)'s lines does.
- **Until the marks are back, the checker must not see this repository:** the key is committed, and the
  seeded draw can be rerun from the code. Send only the XLSX, to someone without access to the repo.

The CSV files are in UTF-8, with a byte-order mark so that Excel, Numbers and LibreOffice show umlauts
correctly.

## The XLSX for the checker

- **Tab "Instructions"** (shown first): the instructions below, and three worked examples, one for each
  meaning mark, which between them use both answers of the other two columns. Claude made the examples
  up; they are not among the 50 lines, and no native speaker has checked them.
- **Tab "Lines":** line number, English source, German translation, then Meaning (kept / minor loss /
  wrong), Added info (yes / no) and Natural German (yes / no), each from a drop-down list set to refuse
  other entries, and an optional comment. The header row stays in view, and the tab prints on A4 landscape.
- **Nothing tells the system:** no system, run, model or budget anywhere, no hidden tab, no document
  properties (author, title or dates), and the rows in the sheet's shuffled order.
- A neutral file name, no project words inside, and no document properties.
- Written with Python's standard library (`isochron.xlsx`); checked to open with openpyxl 3.1.5.

## Instructions for the checker (step4_sheet_de.csv and the XLSX)

Each row has an **English sentence** and a **German translation** of it, which may be shorter than a
full translation. Read both and fill in:

| Column | Write | When |
|--------|-------|------|
| `meaning` | kept, minor loss or wrong (erhalten, kleiner Verlust, falsch) | kept: the German says everything the English says. Minor loss: a detail is missing or weaker, such as a number, a name, a time, a condition, or words such as *almost*, *very*, *local*, *according to the police*. Wrong: the German says something else, or misses the main point. A missing qualifier or linking word is a minor loss; a detail replaced by another is a minor loss if the main point still holds, and wrong if not. |
| `added_info` | yes or no (ja / nein) | yes if the German says something the English does not: a new fact, a detail, or a stronger claim. A dropped qualifier counts under meaning, not here. |
| `natural_german` | yes or no (ja / nein) | yes if it is correct, natural German that you would accept in a dubbed film. A formal, written style is fine; ignore punctuation and quotation marks. |
| `comment` | optional | what was lost, added or unnatural, in a few words |

- Shorter wording is fine as long as nothing is lost. A shorter line is not a minor loss by itself.
- Each English sentence appears twice, each time with its own German translation; sometimes the two are
  the same. Judge each row on its own, and mark both.
- If two options seem to fit, choose the closer one and say why in the comment.
- Please do not change the English or German text; write corrections in the comment.
- If a cell shows no arrow, type exactly kept, minor loss, wrong, yes or no.
- Please do not use a dictionary, a translator or a chatbot, and do not look the sentences up online.
- It takes about 30–45 minutes. Send the file back as .xlsx, under any name (Numbers: File > Export To >
  Excel; Google Sheets: File > Download > Microsoft Excel).

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

As returned (protocol v2.34): `uv run python -m isochron.native_check score
results/native_check/returned/german_lines_rated_part1.xlsx --as-rated
results/native_check/returned/step4_sheet_de_as_rated.csv`. In pairs whose German is identical, the rated
copy's marks apply to both lines. Findings and rates: `results/human_check.md`.

```
uv run python -m isochron.native_check score FILLED_SHEET.xlsx
uv run python -m isochron.native_check score FILLED_SHEET.csv
```

The scorer recognises which sheet it was given. For step 4 it first checks that every marked line still
has the English and German text that `step4_sheet_de.csv` gave it, and stops if not: rows sorted apart
from their line numbers would otherwise be scored against the wrong key. If a text was only edited or
re-encoded, check by eye and add `--no-text-check`. It also stops on a mark that is not on the lists, and
on a row with marks but no line number.
- **Step 4 sheet:** it writes `results/native_check_step4_agreement.md`.
  - Per system: the share of lines kept, with a minor loss, wrong, adding information, and natural, each
    with a 95 % Wilson interval.
  - Agreement, as the share of lines and Cohen's kappa, with each automatic check: both NLI models
    against the reference and against the English source, and the judge.
- **Step 2 sheet:** it writes `results/native_check_agreement.md`, with agreement on added and dropped
  information.

Lines left empty are skipped and counted.
