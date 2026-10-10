# Data

The data files in this directory are licensed **CC BY-SA 4.0**. The code in
this repository stays **Apache-2.0** (see [LICENSE](../../LICENSE)).

The sentences come from FLEURS (Conneau et al., 2022; CC BY 4.0), whose text
is taken from FLoRes-101 (Goyal et al., 2022; CC BY-SA 4.0). That ShareAlike
licence carries over to these files. Sources, revisions and full attribution
are in [docs/licences.md](../docs/licences.md). No audio is stored here.

| Files | Content | Schema (`src/isochron/schema.py`) |
|-------|---------|-----------------------------------|
| `fleurs_{de,fr,it}_{dev,test}.jsonl` | One line per FLEURS sentence: English source and human reference translation | `SentenceRecord` |
| `overlong_{de,fr,it}_{dev,test}.jsonl` | Lines with `ref_tgt_s > 1.10 × slot_s`, plus `overrun` | `OverlongRecord` |
| `nli_controls.jsonl` | 200 checks for the NLI metric: 20 German and 20 French FLEURS train sentences, each paired with itself, a paraphrase, a version with a clause deleted, one with a made-up clause inserted, and a negation. The variants were written by hand by Claude (AI assistant) and have not yet been reviewed by a native speaker. | `ControlPair` |
| `judge_controls_de.jsonl` | 140 hard checks for any meaning judge, on 60 German FLEURS train sentences (none of them in `nli_controls.jsonl`): 40 with one modal, number or qualifier change, 20 with one inserted fact, 20 same-meaning edits and 60 identity pairs. `note` gives each edit as "old → new". Selected in a seeded order and built by `uv run python -m isochron.data.build_judge_controls`; the edits were written by Claude (AI assistant) and have not yet been reviewed by a native speaker. | `ControlPair` |

Built by `uv run python -m isochron.data.build_fleurs`. Statistics:
[results/fleurs_stats.md](../results/fleurs_stats.md).

**The audio fields are not valid yet.** `slot_s`, `ref_tgt_s` and the
`overlong_*` files come from silence-trimmed human recordings, and trimming
fails on noisy ones. `noisy_src` and `noisy_tgt` mark recordings whose noise
floor is above −30 dB (5th percentile of frame RMS, in dB relative to the
loudest frame); there, trimming leaves the noise in place. The main
experiments use only the text fields.
