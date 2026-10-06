# FLEURS line statistics

- Date: 2026-10-06 14:11 UTC
- Git commit: 773a6edbbc79f83c3a22a15733d81b2c3507f000
- Built by: `uv run python -m isochron.data.build_fleurs` (in `track_2b/`)
- Data: [google/fleurs](https://huggingface.co/datasets/google/fleurs) at revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd`, licence CC BY 4.0; configs en_us, de_de, fr_fr, it_it; FLEURS splits `validation` (our `dev`) and `test`
- Trimming: `librosa.effects.trim(top_db=30, ref=np.max, frame_length=2048, hop_length=512)` at the native 16000 Hz, no resampling; durations rounded to 1 ms
- Recording choice: per sentence and language, the recording with the smallest numeric recording id
- Over-long: `ref_tgt_s > 1.10 × slot_s`, on the rounded durations
- Model + quantisation, endpoint, TTS engine + voice: none. No model or TTS is involved; every duration here is measured on a human FLEURS recording
- Seeds: 0 (only used to pick the sample pairs printed to the console)
- n: 1456 joined lines (dev 431, test 1025)
- Libraries: librosa 0.11.0, numpy 2.4.6, soundfile 0.14.0, pyarrow 25.0.1, huggingface_hub 2.1.1

`ref_tgt_s / slot_s` compares two different speakers, each reading at their own pace,
so it mixes the length of the language with the tempo of the speaker.

**Known issue:** for recordings whose noise floor is above −30 dB, trim removes little
or nothing, so their durations are too long. See the end of this file.

## Lines per split and language

| Pair | Split | EN sentences (recordings) | Target sentences (recordings) | Joined lines | EN only | Target only |
|------|-------|--------------------------:|------------------------------:|-------------:|--------:|------------:|
| en→de | dev | 150 (394) | 147 (363) | 147 | 3 | 0 |
| en→de | test | 350 (647) | 347 (862) | 347 | 3 | 0 |
| en→fr | dev | 150 (394) | 137 (289) | 137 | 13 | 0 |
| en→fr | test | 350 (647) | 332 (676) | 332 | 18 | 0 |
| en→it | dev | 150 (394) | 147 (391) | 147 | 3 | 0 |
| en→it | test | 350 (647) | 346 (865) | 346 | 4 | 0 |

## Checks

- Parquet vs raw release: every parquet split lists the same (sentence id, recording id) pairs as the matching raw TSV.
- Split separation: no sentence id occurs in two different splits (train, dev, test), within or across en_us, de_de, fr_fr, it_it.
- Texts: every recording of a sentence has the same `raw_transcription` (the build stops otherwise).
- Alignment: lines where EN or target text contains digits, and how many have identical digit runs.
  Numbers spelled out in one language and not the other cause some mismatches even when the alignment is right.

| Pair | Lines with digits | Identical digit runs | Share |
|------|------------------:|---------------------:|------:|
| en→de | 90 | 81 | 90.0 % |
| en→fr | 91 | 74 | 81.3 % |
| en→it | 90 | 75 | 83.3 % |

## Slot duration `slot_s` (s)

| Pair | Split | n | mean | min | p10 | p25 | median | p75 | p90 | max |
|------|-------|--:|-----:|----:|----:|----:|-------:|----:|----:|----:|
| en→de | dev | 147 | 8.81 | 2.91 | 5.28 | 6.61 | 8.40 | 10.16 | 12.52 | 30.59 |
| en→de | test | 347 | 9.40 | 3.14 | 5.57 | 6.96 | 8.96 | 11.23 | 13.66 | 28.99 |
| en→fr | dev | 137 | 8.68 | 2.91 | 5.28 | 6.62 | 8.45 | 10.14 | 12.45 | 21.00 |
| en→fr | test | 332 | 9.37 | 3.14 | 5.57 | 6.97 | 8.95 | 11.22 | 13.50 | 28.99 |
| en→it | dev | 147 | 8.86 | 2.91 | 5.28 | 6.61 | 8.40 | 10.18 | 12.60 | 30.59 |
| en→it | test | 346 | 9.43 | 3.14 | 5.57 | 6.98 | 8.99 | 11.23 | 13.68 | 28.99 |

## Reference length relative to the slot, `ref_tgt_s / slot_s`

| Pair | Split | n | p25 | median | p75 |
|------|-------|--:|----:|-------:|----:|
| en→de | dev | 147 | 0.873 | **1.090** | 1.515 |
| en→de | test | 347 | 0.855 | **1.084** | 1.447 |
| en→de | dev+test | 494 | 0.856 | **1.085** | 1.479 |
| en→fr | dev | 137 | 0.702 | **0.919** | 1.092 |
| en→fr | test | 332 | 0.696 | **0.876** | 1.058 |
| en→fr | dev+test | 469 | 0.699 | **0.889** | 1.063 |
| en→it | dev | 147 | 1.110 | **1.408** | 1.743 |
| en→it | test | 346 | 1.107 | **1.390** | 1.716 |
| en→it | dev+test | 493 | 1.107 | **1.397** | 1.726 |

## Over-long lines, `ref_tgt_s > 1.10 × slot_s`

The last column counts over-long lines where the EN or the target recording has a noise floor above −30 dB
(see the known issue at the end).

| Pair | Split | Lines | Over-long | Share | Over-long with a noisy recording |
|------|-------|------:|----------:|------:|---------------------------------:|
| en→de | dev | 147 | 69 | 46.9 % | 33 |
| en→de | test | 347 | 169 | 48.7 % | 86 |
| en→fr | dev | 137 | 33 | 24.1 % | 13 |
| en→fr | test | 332 | 67 | 20.2 % | 27 |
| en→it | dev | 147 | 111 | 75.5 % | 41 |
| en→it | test | 346 | 260 | 75.1 % | 88 |

## Trimming, chosen recordings

| Language | Split | Recordings | Median raw (s) | Median trimmed (s) | Median removed (s) | Noise floor above −30 dB |
|----------|-------|-----------:|---------------:|-------------------:|-------------------:|-------------------------:|
| en | dev | 150 | 8.76 | 8.45 | 0.31 | 53 (35.3 %) |
| en | test | 350 | 9.62 | 8.99 | 0.32 | 117 (33.4 %) |
| de | dev | 147 | 11.16 | 9.31 | 0.66 | 18 (12.2 %) |
| de | test | 347 | 11.64 | 9.60 | 0.72 | 37 (10.7 %) |
| fr | dev | 137 | 10.02 | 7.14 | 1.70 | 0 (0.0 %) |
| fr | test | 332 | 9.96 | 7.78 | 1.49 | 0 (0.0 %) |
| it | dev | 147 | 13.92 | 11.90 | 2.12 | 0 (0.0 %) |
| it | test | 346 | 14.43 | 12.58 | 2.11 | 0 (0.0 %) |

### Known issue: noise floors above −30 dB

`top_db=30` only removes frames more than 30 dB below the loudest frame. When a
recording's background noise is louder than that, trim leaves the leading and trailing
non-speech in place, and its duration comes out too long. Noise floor = 5th percentile of
frame RMS in dB relative to the loudest frame, on the same frames trim uses. Characters per
second (text length incl. spaces ÷ trimmed duration) is a rough tempo check; it also varies
by speaker and language. The trimming method is an open item in `docs/eval_protocol.md`.

| Language | Noise floor | Recordings | Median removed (s) | Nothing removed | Median chars/s |
|----------|-------------|-----------:|-------------------:|----------------:|---------------:|
| en | ≤ −30 dB | 330 | 0.58 | 8 (2.4 %) | 14.1 |
| en | > −30 dB | 170 | 0.03 | 78 (45.9 %) | 15.5 |
| de | ≤ −30 dB | 439 | 1.22 | 1 (0.2 %) | 16.6 |
| de | > −30 dB | 55 | 0.03 | 25 (45.5 %) | 7.4 |
| fr | ≤ −30 dB | 469 | 1.52 | 0 (0.0 %) | 19.9 |
| it | ≤ −30 dB | 493 | 2.11 | 1 (0.2 %) | 12.5 |
