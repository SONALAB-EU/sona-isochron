# Isochron: dubbing lines that fit their slot, with Apertus

[![CI](https://github.com/SONALAB-EU/isochron/actions/workflows/ci.yml/badge.svg)](https://github.com/SONALAB-EU/isochron/actions/workflows/ci.yml)
[![Dataset on Hugging Face](https://img.shields.io/badge/dataset-sonalab%2Fisochron-yellow?logo=huggingface)](https://huggingface.co/datasets/sonalab/isochron)

Hack Apertus 2026, Track 2B. A dubbed line has to fit the time the original actor speaks (isochrony),
and translations usually run long. In Isochron, Apertus 1.5 translates English lines into German or French
and shortens them to a length budget, in characters or syllables, with a **repair loop**: every candidate
is checked for length, meaning (NLI, both directions) and language, and Apertus revises with specific
feedback, at most twice. Apertus is used for inference only.

## Key results

FLEURS test, Apertus 1.5 8B in BF16, 347 German and 332 French sentences × 3 seeds; ranges over the four
settings (2 languages × 2 budgets). From the key-results table of the
[technical report](track_2b/technical_report.md), which gives every interval, n and caveat.

| Result | Plain translation | One step to the budget | Ours (repair loop) |
|---|---|---|---|
| Fit within ±10 % of the budget (%) | 19.6–55.6 | 44.7–71.6 | **69.9–80.2** |
| Too long, over +10 % (%, post-hoc) | 20.5–79.1 | **1.4–14.8** | 4.1–20.4 |
| Meaning kept vs the reference, main NLI (%) | 79.5–79.7 | 69.7–76.8 | **80.6–81.6** |
| Meaning kept vs the reference, second NLI (%, post-hoc) | **88.2** | 75.4–81.6 | 82.9–87.7 |
| Timing: spoken line fits the English slot ±10 %, budget calibrated to one TTS voice (of 99; exploratory) | 25 | – | **47** |

## Quick start

Requirements: Docker with Compose v2, and an OpenAI-compatible endpoint that serves Apertus 1.5. Go to the
project root:

```
cd track_2b
```

Set the endpoint with three variables, either in the environment or in `.env` next to the Makefile (copy
`.env.example`):

```
LLM_NAME=<the model name the endpoint serves>
LLM_BASE_URL=<the endpoint's base URL, ending in /v1>
LLM_API_KEY=<your API key>
```

Then run the method on the 10 sample lines (results in `output/`):

```
make run
```

Or run it with no network at all, on a local GGUF file served by llama.cpp next to the app:

```
make run-offline GGUF=/path/to/apertus.gguf LLM_QUANTISATION=Q4_K_M
```

Details, requirements and timings: [track_2b/README.md](track_2b/README.md).

## Layout

`track_2b/` is the project root, as the Hack Apertus template requires:

| Path | What it is |
|---|---|
| `track_2b/README.md` | How to run the project, its input and output |
| `track_2b/technical_report.md` | The technical report: method, results, limitations |
| `track_2b/Makefile` | `make run` and `make run-offline` (Docker) |
| `track_2b/src/` | The code (`isochron`) |
| `track_2b/data/` | FLEURS sentences, control pairs and the sample input |
| `track_2b/docs/` | Protocol, licences, setups, architecture, figures |
| `track_2b/results/` | Every results report, with its provenance |
| `.github/workflows/ci.yml` | CI: the tests and the linux/amd64 Docker build |

## Links

- Technical report: [track_2b/technical_report.md](track_2b/technical_report.md)
- Dataset: [huggingface.co/datasets/sonalab/isochron](https://huggingface.co/datasets/sonalab/isochron)
- Demo video: **[PLACEHOLDER: link to the demo video]**

## Team

SONALAB — Kaushik Mukherjee, Sören Hübner. Contact: soeren.huebner@sonalab.eu

## License and acknowledgements

Per the Hack Apertus terms (§6): the code is Apache-2.0 ([LICENSE](LICENSE)), the data files are
CC BY-SA 4.0, and the technical report is CC BY 4.0. Every model, dataset and tool, with its licence:
[track_2b/docs/licences.md](track_2b/docs/licences.md).

Thanks to the Swiss AI Initiative for Apertus 1.5; to the authors of FLEURS (CC BY 4.0; the sentences and recordings the
evaluation uses) and FLoRes-101 (CC BY-SA 4.0; the text of FLEURS); and to the Hasso Plattner Institute
(HPI) for compute on its H100 cluster.

Built from the [Hack Apertus project template](https://github.com/HackApertus/project-template).
