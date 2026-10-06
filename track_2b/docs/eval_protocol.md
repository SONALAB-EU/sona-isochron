# Evaluation protocol

Written on 2026-10-06, before any results exist. Scope agreed with Sören:
**shortening only**. Translations that are too short for the slot are out of
scope.

Any change to this protocol after the first results is recorded in the
changelog at the end, with the date and the reason.

## Research questions

- **RQ1 Shorten.** Given a translation that is too long for the slot, can
  Apertus rephrase it to fit while keeping the meaning?
- **RQ2 One step vs two.** Should Apertus translate straight to the target
  length, or translate first and then shorten? Which keeps more meaning at the
  same length?
- **RQ3 Compression curve.** Ask for 90 / 80 / 70 / 60 % of the original
  length. How much meaning survives at each level?

## Data

- **FLEURS** (CC BY 4.0). FLEURS is n-way parallel, so every target line has
  an English source sentence with English audio.
- **Language pairs.** EN→DE is the main pair; EN→FR and EN→IT are secondary.
- **Slot S.** S is the duration of the English source audio, trimmed of
  leading and trailing silence, in seconds.
- **Too long.** A line is too long when its spoken length is more than
  1.10 × S.
- **Original length.** The original length of a line is the length of the
  plain Apertus translation (B1). Compression targets and achieved ratios are
  relative to it.

## Splits

- **Dev** is for prompt tuning and for the go/no-go check. It may be used
  without limit.
- **Test** is used only for the numbers we report. Nothing is tuned on it. All
  test runs use the frozen prompts and settings, identified by their git
  commit.

## Length

Every output is measured in three units:

| Unit | Use | Status |
|------|-----|--------|
| Syllables | development | **estimate**: computed from text, not measured |
| TTS seconds | final numbers | **measurement**: duration of synthesised audio, trimmed the same way as the English source |
| Characters | comparison with isometric MT | count from text |

Syllable-based results are always labelled as estimates. Only TTS seconds are
reported as measured duration.

## Meaning

**Bidirectional entailment.** An independent multilingual NLI model (not
Apertus) compares each output with the **English source**, not the FLEURS
reference translation. It runs in both directions:

- If the source entails the output, the output adds nothing. When this fails,
  the line counts as **added content**.
- If the output entails the source, the output drops nothing. When this fails,
  the line counts as **dropped content**.
- A line **keeps meaning** when both directions hold.

**Native-speaker check.** A native speaker checks 50 EN→DE lines without
being told which system produced each one. For each line they mark: added
content (yes/no), dropped content (yes/no). We report how often the speaker
and the NLI model agree, so the NLI-based rates can be trusted or discounted.

We report the **added-content rate** and the **dropped-content rate**
separately for every system.

## Systems

| ID | System | Length control |
|----|--------|----------------|
| B1 | Plain Apertus translation | none |
| B2 | Apertus, isometric | character-count target in the prompt |
| A1 | Apertus, one step | translate straight to the target length |
| A2 | Apertus, two steps | translate (= B1), then shorten to the target length |

B2 is the isometric baseline. Our method is A1/A2, which target spoken length
rather than characters.

For RQ2, A1 and A2 get the same length target on the same lines. We compare
meaning (a) on lines where both fit and (b) as meaning against achieved
compression across all lines.

## Metrics

- **Fit rate.** The share of lines whose spoken length is within ±10 % of S,
  that is, 0.90 S ≤ length ≤ 1.10 S.
- **Achieved compression ratio.** Output length ÷ original (B1) length, in
  each unit.
- **Entailment, both directions.** Source ⇒ output and output ⇒ source, each
  reported as a rate, plus the share of lines where both hold.
- **Added-content rate and dropped-content rate**, as defined above.

## Statistics

- **3 seeds** per system and condition. Seeds are listed in every results file.
- **95 % bootstrap confidence intervals.** Lines are resampled with
  replacement, and each line's score is averaged over the 3 seeds. We use
  percentile intervals over 10,000 resamples, with the bootstrap seed recorded.
- Every results file records: date, git commit, model + quantisation,
  endpoint, TTS engine + voice, seeds, n, and split.

## Go/no-go: Wednesday 7 October 2026

Fixed now, before any data has been seen.

- **Lines:** 50 EN→DE dev lines whose B1 translation is too long
  (> 1.10 × S). We take the first 50 such lines in FLEURS dev order, with no
  hand-picking.
- **System:** RQ1 shortening, with S as the target.
- **GO if both hold:**
  1. at least 60 % of the 50 lines (≥ 30) fit the slot (within ±10 % of S),
     **and**
  2. of the lines that fit, at least 80 % keep meaning (entailment holds in
     both directions).
- **Otherwise NO-GO.** We report it as a null result and do not lower the
  thresholds after the fact.
- The results file states whether length was measured with TTS seconds or
  estimated from syllables.

## To fix before the first dev run

These choices are not made yet. Each will be recorded here, with its licence
in `docs/licences.md`, before any output is scored.

- NLI model and its entailment threshold.
- TTS engine and voice for each language.
- Syllable counter for each language, and the syllables-to-seconds conversion
  used for estimates.
- Silence-trimming method for the English audio and the TTS output.
- B2 character target. Default: the English source character count (the usual
  isometric setup).
- Which systems the 50 native-speaker lines are drawn from, and who checks
  them.

## Changelog

- 2026-10-06: first version.
