[![CI](https://github.com/SONALAB-EU/isochron/actions/workflows/ci.yml/badge.svg)](https://github.com/SONALAB-EU/isochron/actions/workflows/ci.yml)

# Isochron: dubbing lines that fit their slot, with Apertus

Hack Apertus 2026, Track 2B (own project). Built with Apertus 1.5.

A dubbed line has to fit the time the original actor speaks: that is isochrony. Translations are often
longer than the original, so a dubbing editor shortens them by hand without changing what they say.
Isochron does that step with **Apertus 1.5**. It shortens a line to a target length in syllables, as a
proxy for spoken time, and it checks that nothing was dropped or added.

- **Input:** a line, its language (German or French) and a target length, as a percentage of its syllables.
- **Output:** a shorter line in the same language, with its syllable count. Two checks are reported:
  whether it fits within ±10 % of the target, and whether a meaning check finds the same content in both
  directions.

## How it works

The method is prompt v1 with a **repair loop**. Asking for a character count (isometric prompting) is a
baseline for comparison, not the method.

1. **Round 0.** Apertus gets the line and the syllable target and writes 4 candidates.
2. **Checks.** Each candidate is checked three ways:
   - **Length:** its syllables are counted with eSpeak NG 1.52.0.
   - **Meaning:** a multilingual NLI model (mDeBERTa-v3, XNLI) must find entailment in both directions
     between the line and the candidate. One direction failing means information was added; the other,
     that it was dropped.
   - **Language:** a language identifier (py3langid) checks that the candidate is in the line's language.
3. **Repair.** If the best candidate fails a check, Apertus gets one revision prompt with specific
   feedback: "4 syllables too long (about 1 word)", "information is missing", "information was added" or
   "answer in German".
4. **Stop.** After at most 2 revisions, the best candidate over all rounds is returned. Every round is
   logged.

The loop never sees the evaluation judge.

Results on FLEURS test (Apertus 1.5 8B in BF16; every sentence × 4 levels × 3 seeds; scored by an
independent judge, Qwen3-14B):

| Share of outputs | German: without the loop | German: with it | French: without the loop | French: with it |
|------------------|------------------:|-------------:|------------------:|-------------:|
| Fit the target | 34.9 % | 64.7 % | 34.4 % | 67.6 % |
| Fit, with every fact kept and nothing added | 14.2 % | 38.4 % | 15.5 % | 44.2 % |

- The gain is largest for small cuts (90 % of the syllables) and small at 60 %, where the loop keeps the
  meaning rather than the length.
- Details are in `technical_report.md` and `results/step2_test.md`.
- When translating from English to a length budget (the translation task, on test), translating first and then
  shortening with the loop met the budget most often in three of four settings: 70–80 % within ±10 %. In
  German with a syllable budget, translating to the budget in one step did as well. Meaning held up as
  well as in plain translation (`results/step4_test.md`).

## Run it

### `make run` (Docker)

Requirements:
- Docker with Compose v2 (the `docker compose` command).
- An OpenAI-compatible endpoint that serves Apertus 1.5, given by three variables, either in the
  environment or in `.env` next to this file (copy `.env.example`):

  ```
  LLM_NAME=<the model name the endpoint serves>
  LLM_BASE_URL=<the endpoint's base URL, ending in /v1>
  LLM_API_KEY=<your API key>
  ```

  For a server on the Docker host itself, `http://localhost:<port>/v1` (or `127.0.0.1`) works: on a
  Linux host, `make run` then gives the app the host's network; on a Mac (Docker Desktop or Colima), it
  uses `host.docker.internal` instead, which they forward to the host. `make run` prints which one it
  chose.
  (Not with rootless Docker, whose host network is not the host's: there, give an address the
  container can reach.)
  `LLM_QUANTISATION` is optional: if set, it is recorded in the summary.
- With Docker Desktop or Colima, the checkout must be in a folder Docker's VM can see (your home folder,
  by default). `make run` checks this once the image is built, before the method runs, and says so if
  not.

Then run, from this directory:

```
make run
```

What happens:
- The image is built (only the first time) and the method runs on the 10 lines of
  `data/sample_input.jsonl`.
- The results go to `output/results.jsonl` and `output/summary.md`.
- The NLI and the language check run on the CPU, inside the container.
- Measured on an Apple M3 (Docker in Colima, arm64, 6 CPUs, 10 GiB): the first build took 40 min, a
  later rebuild 13 min, and the run 4–6 min against llama-server on the same Mac.
- The image also builds for `linux/amd64` on a native amd64 runner in CI (GitHub Actions, on every push).
  `make run` on amd64 was tested under emulation on the Mac: the same results as arm64, line for line. Under that emulation (Rosetta), the build crashed at random and passed when
  run again; a native amd64 host emulates nothing. `results/docker_check.md` has every timing, and the
  checks behind them.

### `make run-offline` (no network at all)

The same run with no network connection. llama.cpp's server (build 11429, the build used for all local
results) runs a GGUF file from local disk next to the app:

```
make run-offline GGUF=/path/to/apertus.gguf LLM_QUANTISATION=Q4_K_M
```

- The server's container has no network interfaces. The app joins its network namespace, so the two
  reach each other on 127.0.0.1 and nothing else.
- The GGUF is mounted read-only. It is never copied into the image or the repository.
- `docs/local_llm.md` explains which GGUF the experiments used and its caveat: it is a text-only conversion of the
  official weights.
- Build the images once while online. After that, `make run-offline` needs no network.
- Everything runs on the CPU here, so it is slower than with a GPU server. On the Apple M3 (6 CPUs for
  Docker), the 10 lines took 10 min, including 1 min to load the GGUF, with the Mac's own llama-server
  stopped; an earlier run took 26 min.

### Without Docker

Install Python 3.11 with [uv](https://docs.astral.sh/uv/), and eSpeak NG 1.52.0 (`brew install
espeak-ng` on a Mac). Set the three variables, then run:

```
uv sync
uv run python -m isochron.app --input data/sample_input.jsonl --out output
```

Add `--mock` for a dry run without an LLM. Run the tests with `uv run pytest`.

### The experiments

- `docs/eval_protocol.md`: the pre-registered protocol, its changelog and every decision with its date.
- `docs/local_llm.md`: Apertus on a Mac (llama.cpp).
- `docs/hpc.md`: Apertus 1.5 in BF16 on H100s (vLLM).
- `results/`: every report. Each one records its date, git commit, model and quantisation, endpoint,
  TTS engine and voice (none, except the timing checks), seeds and n.
- `make figures` redraws the report's figures (`docs/figures/`: PDF, PNG and the CSV behind each) with
  matplotlib, from committed results files only.
- `uv run scripts/report_pdf.py` renders `technical_report.md` to PDF (A4, two columns) with headless
  Chrome and counts its pages. The limit is 6.

## Input and output

**Input** (`--input`, JSON lines), one object per line:

```json
{"id": "1513", "lang": "de", "text": "Argentinien ist bekannt dafür, dass sein Polo-Team und die Spieler zu den besten der Welt gehören.", "level": 70}
```

| Field | Meaning |
|-------|---------|
| `id` | A unique string |
| `lang` | `de` or `fr`: the language of the line |
| `text` | The line to shorten |
| `level` | The target length in % of the line's syllables, a whole number from 1 to 100. The target is `level × syllables / 100`, rounded half up. |

Other fields, such as `license` and `source` in the sample, are ignored.

**Output** (`--out`, default `output/`):

- `results.jsonl`: one object per input line, in input order.

  | Field | Meaning |
  |-------|---------|
  | `id`, `lang`, `level`, `input` | From the input |
  | `input_syllables`, `target_syllables` | The line's syllables and the target |
  | `output`, `output_syllables` | The shortened line and its syllables (`null` if Apertus gave no usable answer) |
  | `fit` | The output is within ±10 % of the target |
  | `nli_kept` | The NLI finds entailment in both directions between line and output |
  | `language`, `wrong_language` | The identified language of the output, and whether it is not `lang` |
  | `accepted` | `fit` and `nli_kept`, in the right language |
  | `revisions`, `retries` | Rounds after round 0 (0 to 2), and how many of them repeated round 0 after an unusable answer |
  | `round0` | The closest of the first 4 candidates, before any revision: `output`, `output_syllables`, `fit`, `nli_kept` |
  | `time_s` | Seconds for this line, all rounds and checks included |

  An output in the wrong language counts as neither fitting nor kept.
- `summary.md`: how the run was made, one row per line, and totals.
  - Provenance: date, git commit, model, quantisation, endpoint, server, prompts, generation settings,
    seeds and n.
  - Totals: fit and kept, after the loop and at round 0.
- `raw/<time>/`: the full log of every round (each prompt, raw answer, candidate and check), in the same
  format as the experiments.

## Repository layout

| Path | What it is |
|------|------------|
| `src/isochron/app.py` | `make run`: the method on an input file |
| `src/isochron/repair.py`, `loop_run.py` | The repair loop, and the runner the experiments and `make run` share |
| `src/isochron/metrics/` | Syllable counting (eSpeak NG) and the NLI meaning check |
| `src/isochron/language.py` | The language check |
| `src/isochron/prompts/` | Every prompt, versioned |
| `src/isochron/judge.py`, `pilot_report.py`, `step2_report.py` | The evaluation-only judge, and the reports |
| `src/isochron/step4.py` | Translation to a length budget |
| `data/` | FLEURS sentences, control pairs and the sample input (`data/README.md`) |
| `docs/` | Protocol, licences, setups, architecture |
| `hpc/` | Scripts for the H100 runs (`docs/hpc.md`) |
| `results/` | Reports; raw runs stay local (`results/raw/`, git-ignored) |
| `Dockerfile`, `docker-compose*.yml`, `Makefile` | `make run` and `make run-offline` |

## Licences

- **Code:** Apache-2.0 ([LICENSE](../LICENSE)).
- **Technical report and documentation:** CC BY 4.0, as the organisers' template sets.
- **Data** (`data/*.jsonl`): CC BY-SA 4.0. The sentences come from FLEURS (CC BY 4.0), whose text comes
  from FLoRes-101 (CC BY-SA 4.0). See `data/README.md`.
- **Models:**
  - Apertus 1.5: Apache-2.0, plus the Apertus 1.5 Acceptable Use Policy.
  - The NLI model `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`: MIT.
  - The evaluation judges Qwen3-14B and Qwen3-8B: Apache-2.0. They never take part in generation.
- **Programs:**
  - eSpeak NG 1.52.0: GPL-3.0-or-later. It runs as a separate program; the Docker image builds it from
    its upstream source at build time.
  - llama.cpp: MIT. vLLM: Apache-2.0. py3langid: BSD-3-Clause. PyTorch: BSD-3-Clause.

Every item, with source, revision and licence: `docs/licences.md`.
