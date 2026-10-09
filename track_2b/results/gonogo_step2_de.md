# Go/no-go, step 2 (shorten one German sentence to 80 % of its syllables): NO-GO

Pre-registered in `docs/eval_protocol.md` (go/no-go section, v2.4). Raw
outputs: `results/raw/20261009T141318Z_step2_de_dev_syllables/` (kept locally,
git-ignored): `config.json`, `candidates.jsonl`, `scores.jsonl`, `summary.md`.

- Date: generated 2026-10-09 14:13–14:28 UTC; scored 2026-10-09 14:46 UTC
- Git commit: run `6bebb94`, scoring `6edfd20`
- Model + quantisation: Apertus 1.5 8B, text-only conversion, GGUF Q4_K_M
  (`Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF`, SHA-256 `a037df8d…5f299`; see
  `docs/local_llm.md`)
- Endpoint: local llama-server, llama.cpp build b11429 (`d81235049`), Metal,
  context 8192, one slot (`http://127.0.0.1:8080/v1`)
- Generation: temperature 0.7, then top_p 0.95, with no top_k or min_p; thinking
  off; 4 candidates per JSON answer; prompt `shorten_syllables_v1` (SHA-256
  `fe4fbfdd…61a5c`, frozen)
- TTS engine + voice: none
- Seeds: 0, 1, 2 (bootstrap seed 0)
- n: 50 sentences (`random.Random(0).sample` of `data/fleurs_de_dev.jsonl`),
  150 outputs
- Syllables: eSpeak NG 1.52.0
- NLI: `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` @ `b5113eb`,
  mps, float32, argmax label

## Decision

| Selection | Role | Outputs | Fit ±10 % | Kept both ways, among fits | Added | Dropped | Decision |
|-----------|------|--------:|-----------|----------------------------|-------|---------|----------|
| closest | decides | 150 | 40.7 % [31.3, 50.0] (61/150) | 62.3 % [46.6, 77.0] (38/61) | 8.7 % [4.0, 14.8] (13/149) | 45.0 % [34.0, 55.7] (67/149) | **NO-GO** |
| first | reported only | 150 | 22.0 % [14.0, 30.7] (33/150) | 69.7 % [47.4, 89.3] (23/33) | 11.4 % [4.8, 19.3] (17/149) | 50.3 % [38.0, 62.7] (75/149) | – |

How to read the table:
- GO needs fit ≥ 60 % and kept among fits ≥ 80 %. Both fail, each on its own.
- Shares are pooled over the 150 outputs. The 95 % intervals resample the 50
  sentences, each with its 3 outputs.
- Added and dropped are shares of the 149 outputs with a usable answer.

## What else the run shows

- **Apertus over-shortens.** Asked for 80 % of the input's syllables, the
  chosen outputs average 67 % (60 % of the words, 66 % of the characters).
  Most misses are too short, not too long.
- **Selection helps.** Picking the closest of 4 candidates instead of the
  first raises the fit from 22.0 % to 40.7 %.
- **Answer format.** 8 of 150 answers broke it:
  - 7 gave one candidate instead of 4, and were scored on that one;
  - 1 (sentence 1618, seed 1) was invalid JSON. It counts as a miss and as not
    kept, as pre-registered.
- **NLI diagnostics.** The NLI does not accept 2 of the 50 inputs (1556, 1604)
  as entailing themselves.
- **Points near a threshold** (none of them can change the decision):
  - Exactly one NLI direction has a top-2 logit gap below 0.05 (1544, seed 1,
    kept).
  - Two fits sit exactly on the ±10 % line.

## Run history

- **Smoke test** (5 other dev sentences, 4 levels, seed 0): all three checks
  passed.
  - The first run (`20261009T131902Z`) used llama-server's default sampling.
  - The re-run (`20261009T141025Z`) used the decided sampling.
- **A first go/no-go generation (`20261009T132800Z`) was superseded before
  anyone scored or read it.** A blind review of the scoring code found two
  problems:
  - llama-server had added top_k 40 and min_p 0.05 and applied temperature
    last;
  - German decade forms escaped the year rule, which changed one target.

  Both were fixed (commits `0ddd55f`, `6bebb94`) and the go/no-go was generated
  again. The superseded run stays unscored.

## Independent verification (after scoring, before reporting)

Three separate agents checked the result:

1. **Recompute from the raw answers.** Its own parser, target, selection, hit
   and pooling code, with NLI labels looked up from `scores.jsonl`. It
   reproduced every number above and every interval. It found 0 differences
   over all 300 rows, and the 50 sentence ids are identical.
2. **NLI labels.** It re-ran the model one pair at a time on mps in float32
   and cross-checked on CPU. 0 of 298 directional labels differ.
   - It also found that scoring had run in float16, although the summary said
     float32. transformers 5 loads the checkpoint's stored dtype by default.
     That was fixed (`6edfd20`) and the run was re-scored in float32. 0 of 300
     labels changed.
3. **Qualitative audit of 20 random decided outputs**, read by an LLM (Claude)
   as a careful reader of German, not a native speaker.
   - The NLI is too lenient for "keep every piece of information": 11 of the
     20 are judged "kept" although a modifier or detail was dropped or
     changed (for example *lokal*, *Bundes-*, *sehr*, *fast*).
   - Two of those are clear meaning errors. One is a counted fit: "Israel
     verlangt …" became "Die Vereinbarung sieht … vor".
   - The NLI never rejected an output the reader would keep on a strict
     reading.
   - Among the 9 fits in the sample, the NLI keeps 7 and a strict reading 2.

   So "kept among fits" (62.3 %) is an upper bound, and the native-speaker
   check is needed before any meaning-preservation figure is relied on.

## Speed

- 150 requests took 14.5 minutes: 5.8 s and 94 generated tokens per request
  on average.
- Generation ran at 17.3 tokens/s and prompt processing at 115.7 tokens/s.
