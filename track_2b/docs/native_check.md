# Native-speaker check

The protocol (`docs/eval_protocol.md`, "Native-speaker check") pre-registers this check. A native speaker
reads 50 German lines without knowing which system produced each one. They mark whether each line adds
or drops information. We then report how often they agree with the NLI model and with the final judge,
the two automatic meaning checks.

## The files

| File | For | What it is |
|------|-----|------------|
| `results/native_check/sheet_de.csv` | the German checker | 50 rows: an original German sentence and a shortened version, with empty columns to fill |
| `results/native_check/key_de.csv` | us only, **never the checker** | which system produced each line, the NLI's labels and the judge's verdict |
| `results/native_check/controls_de.csv` | a German checker (optional, second task) | 160 control pairs written by Claude, each with the property it should have |
| `results/native_check/controls_fr.csv` | a French checker (optional) | the same for 80 French pairs |

`isochron.native_check` built them, with fixed seeds:

```
uv run python -m isochron.native_check build results/raw/hpc_8b_step2_de_test
uv run python -m isochron.native_check controls
```

How the 50 lines are chosen (`build`):
- They are German step 2 test outputs from 50 different sentences.
- 25 come from the closest round-0 candidate (without the loop) and 25 from the final output (with it).
- Levels 90, 80, 70 and 60 % come in turn, with seed 0. A line with no German output would take the
  next seed; none did.
- The rows are shuffled, and the sheet shows nothing that tells the system.
- Two shortened lines are identical to their originals: the model returned the input unchanged. They stay
  in, because the rule chose them.

The files are CSV in UTF-8, with a byte-order mark so that Excel, Numbers and LibreOffice show umlauts
correctly.

## Instructions for the checker (sheet_de.csv)

Each row has an **original** German sentence and a **shortened** version. Read both and fill in:

| Column | Write | When |
|--------|-------|------|
| `adds_information` | yes or no (ja / nein) | yes if the shortened version says something the original does not: a new fact, a detail, or a stronger or weaker claim |
| `drops_information` | yes or no (ja / nein) | yes if anything the original says is missing or changed in meaning. That includes small things: a number, a name, a time, a condition, or words such as *fast*, *sehr*, *lokal*, *laut der Polizei*. |
| `grammar_problem` | yes or no, optional | yes if the shortened version is not correct, natural German |
| `comment` | optional | what was added, dropped or wrong, in a few words |

- Different wording, word order, or one sentence split into two, is fine as long as the meaning is the
  same. That is neither "adds" nor "drops".
- Judge each row on its own. Rows can be similar; there is no right number of yes answers.
- A shortened version can be the same as the original. Mark it like any other row.
- Please do not use a dictionary, a translator or a chatbot. About 25–40 minutes in total.
- Return the filled file under any name.

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

This writes `results/native_check_agreement.md`: the share of lines on which the native speaker agrees
with the NLI and with the judge, and Cohen's kappa, separately for added and dropped information. Lines
left empty are skipped and counted.
