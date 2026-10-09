# Data and model licences

Every dataset, model and external program used by this project, with its
licence and source.

| Item | Kind | Source | Licence | Used for |
|------|------|--------|---------|----------|
| FLEURS: configs `en_us`, `de_de`, `fr_fr`, `it_it`; splits `validation` (our `dev`), `test` | Dataset: read speech with transcripts | [huggingface.co/datasets/google/fleurs](https://huggingface.co/datasets/google/fleurs), revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd` | CC BY 4.0 | Source sentences and reference translations in `data/fleurs_*.jsonl`; the audio fields there (stretch goal only) |
| FLoRes-101: `dev` and `devtest`, with their article metadata | Dataset: multi-way parallel sentences | [dl.fbaipublicfiles.com/flores101/dataset/flores101_dataset.tar.gz](https://dl.fbaipublicfiles.com/flores101/dataset/flores101_dataset.tar.gz) (Meta's public archive, no login; SHA-256 `49fa80207b09fcc0eca8253ed13303b3a0ae0f16081af862601c73ac76f2cba6`) | CC BY-SA 4.0 | Origin of the FLEURS text; step 1 texts (sentences grouped by article) |
| mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 (Moritz Laurer) | Model: multilingual NLI classifier | [huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7), revision `b5113eb38ab63efdd7f280f8c144ea8b13f978ce` | MIT | Meaning metric: bidirectional NLI (`src/isochron/metrics/meaning.py`) |
| Apertus 1.5 8B (Swiss AI Initiative) | Model: the LLM under test | [huggingface.co/swiss-ai/Apertus-v1.5-8B](https://huggingface.co/swiss-ai/Apertus-v1.5-8B), revision `a411d838600baf0e3635a3daf66fb7c55fc97bb6` (gated: terms accepted) | Apache-2.0, plus the [Apertus 1.5 Acceptable Use Policy](https://github.com/swiss-ai/apertus-legal/blob/main/apertus_1.5/USAGE_POLICY.pdf) | Source of the weights we run |
| apertus-v1.5-8b-text (Andreas Martin) | Model: text-only derivative of Apertus 1.5 8B | [huggingface.co/andreasmartin/apertus-v1.5-8b-text](https://huggingface.co/andreasmartin/apertus-v1.5-8b-text), revision `c0e7eeb69c55c7810c91de3a1f97dde4d4b14b01` | Apache-2.0 (Apertus 1.5 Acceptable Use Policy applies) | Intermediate step: the text backbone repackaged as `ApertusForCausalLM`, which llama.cpp supports. See `docs/local_llm.md`. |
| apertus-v1.5-8b-text-Q4_K_M-GGUF (Colby) | Model: Q4_K_M GGUF of the text-only derivative | [huggingface.co/Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF](https://huggingface.co/Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF), revision `248ec68a63e219e3f061e4c946fc8a20d63b9975`, file `apertus-v1.5-8b-text-q4_k_m.gguf` | Apache-2.0 (Apertus 1.5 Acceptable Use Policy applies) | The weights llama-server runs locally (`docs/local_llm.md`) |
| Qwen3-8B, Q4_K_M GGUF (Qwen team) | Model: meaning judge, used for evaluation only | [huggingface.co/Qwen/Qwen3-8B-GGUF](https://huggingface.co/Qwen/Qwen3-8B-GGUF), revision `7c41481f57cb95916b40956ab2f0b139b296d974`, file `Qwen3-8B-Q4_K_M.gguf` (SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`) | Apache-2.0 | Phase 2 final meaning judge: fact recall and added facts (`src/isochron/judge.py`). It is a different model family from Apertus and never feeds generation. |
| llama.cpp 0.6.0 (build 11429, commit `d81235049`) | External program: LLM inference server | [github.com/ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp), installed with Homebrew (`llama.cpp`) | MIT | Serves Apertus locally through an OpenAI-compatible API |
| eSpeak NG 1.52.0 | External program: text to phonemes | [github.com/espeak-ng/espeak-ng](https://github.com/espeak-ng/espeak-ng), installed with Homebrew (`espeak-ng`) | GPL-3.0-or-later | Syllable counts (`src/isochron/metrics/length.py`). Run as a separate program; its IPA output is parsed. It is never imported, linked or redistributed, so our code stays Apache-2.0. |

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
