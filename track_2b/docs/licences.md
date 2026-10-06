# Data and model licences

Every dataset and model used by this project, with its licence and source.

| Item | Kind | Source | Licence | Used for |
|------|------|--------|---------|----------|
| FLEURS: configs `en_us`, `de_de`, `fr_fr`, `it_it`; splits `validation` (our `dev`), `test` | Dataset: read speech with transcripts | [huggingface.co/datasets/google/fleurs](https://huggingface.co/datasets/google/fleurs), revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd` | CC BY 4.0 | Source sentences and reference translations in `data/fleurs_*.jsonl`; the audio fields there (stretch goal only) |
| FLoRes-101: `dev` and `devtest`, with their article metadata | Dataset: multi-way parallel sentences | [dl.fbaipublicfiles.com/flores101/dataset/flores101_dataset.tar.gz](https://dl.fbaipublicfiles.com/flores101/dataset/flores101_dataset.tar.gz) (Meta's public archive, no login; SHA-256 `49fa80207b09fcc0eca8253ed13303b3a0ae0f16081af862601c73ac76f2cba6`) | CC BY-SA 4.0 | Origin of the FLEURS text; step 1 texts (sentences grouped by article) |

**Our data files** (`data/*.jsonl`) contain FLoRes text, so they are
licensed **CC BY-SA 4.0** (see [data/README.md](../data/README.md)). The code
stays Apache-2.0.

## Attribution

**FLEURS.** Conneau, A., Ma, M., Khanuja, S., Zhang, Y., Axelrod, V.,
Dalmia, S., Riesa, J., Rivera, C. and Bapna, A. (2022). *FLEURS: Few-shot
Learning Evaluation of Universal Representations of Speech.*
[arXiv:2205.12446](https://arxiv.org/abs/2205.12446). Licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

**FLoRes-101.** Goyal, N. et al. (2022). *The Flores-101 Evaluation
Benchmark for Low-Resource and Multilingual Machine Translation.*
Transactions of the Association for Computational Linguistics 10.
[arXiv:2106.03193](https://arxiv.org/abs/2106.03193). Licensed under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), as stated in
the [facebookresearch/flores README](https://github.com/facebookresearch/flores)
and on the [facebook/flores](https://huggingface.co/datasets/facebook/flores)
dataset card. The archive itself has no licence file.

What we changed: we keep only the configs and splits above, join English and
target-language lines by sentence id, choose one recording per sentence, and
add silence-trimmed durations and noise flags
(`src/isochron/data/build_fleurs.py`). We do not redistribute any audio.
