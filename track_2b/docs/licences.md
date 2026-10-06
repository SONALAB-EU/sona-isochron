# Data and model licences

Every dataset and model used by this project, with its licence and source.

| Item | Kind | Source | Licence | Used for |
|------|------|--------|---------|----------|
| FLEURS: configs `en_us`, `de_de`, `fr_fr`, `it_it`; splits `validation` (our `dev`), `test` | Dataset: read speech with transcripts | [huggingface.co/datasets/google/fleurs](https://huggingface.co/datasets/google/fleurs), revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd` | CC BY 4.0 | Source sentences, reference translations and slot durations in `data/fleurs_*.jsonl` and `data/overlong_*.jsonl` |

## Attribution

**FLEURS.** Conneau, A., Ma, M., Khanuja, S., Zhang, Y., Axelrod, V.,
Dalmia, S., Riesa, J., Rivera, C. and Bapna, A. (2022). *FLEURS: Few-shot
Learning Evaluation of Universal Representations of Speech.*
[arXiv:2205.12446](https://arxiv.org/abs/2205.12446). Licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

What we changed: we keep only the configs and splits above, join English and
target-language lines by sentence id, choose one recording per sentence, and
add silence-trimmed durations (`src/isochron/data/build_fleurs.py`). We do not
redistribute any audio.

## Open questions

- The FLEURS sentences come from FLoRes-101 (its dev and devtest sets). FLoRes
  is listed as CC BY-SA 4.0 upstream: see the
  [facebookresearch/flores README](https://github.com/facebookresearch/flores)
  and the [facebook/flores](https://huggingface.co/datasets/facebook/flores)
  dataset card. Our JSONL files contain these sentences. To decide: whether
  the data files should also carry CC BY-SA 4.0.
