# Architecture

Components, data flow and where each one runs. The technical report (`technical_report.md`, section 2)
summarises this page.

## The method at run time (`make run`)

```
 input line (text, lang, level)
        │
        ▼
 ┌──────────────────────────── app container (isochron.app, CPU) ────────────────────────────┐
 │  syllables of the line (eSpeak NG 1.52.0) → target T = level % of them                    │
 │        │                                                                                  │
 │        ▼                                                                                  │
 │  prompt v1 (shorten_syllables_v1) ──────────────► Apertus 1.5 ───────► 4 candidates        │
 │        ▲                    (OpenAI-compatible API: LLM_NAME, LLM_BASE_URL, LLM_API_KEY)   │
 │        │                                                    │                             │
 │        │                                                    ▼                             │
 │        │                       checks on every candidate:                                 │
 │        │                        - syllables vs T (±10 %)          eSpeak NG                │
 │        │                        - meaning both ways (NLI)         mDeBERTa-v3, on the CPU  │
 │        │                        - language                        py3langid                │
 │        │                                                    │                             │
 │        │      best candidate fails a check, revisions left? │                             │
 │        └──── revision prompt (revise_v1) with the feedback ◄┘  yes (at most 2 revisions)   │
 │                                                             │ no                          │
 │                                                             ▼                             │
 │                  best candidate over all rounds → output/results.jsonl, output/summary.md │
 └───────────────────────────────────────────────────────────────────────────────────────────┘
```

Selection, in order: right language, then fits and is kept by the NLI, then kept, then closest to T. The
loop never sees the evaluation judge.

## Where Apertus runs

| Setting | Server | Model | Network at run time |
|---------|--------|-------|---------------------|
| `make run` | any OpenAI-compatible endpoint you name | Apertus 1.5 (8B or 70B) | only to that endpoint |
| `make run-offline` | llama.cpp b11429 in a container without network interfaces; the app shares its namespace | a local GGUF, mounted read-only (we used the Q4_K_M text-only conversion, `docs/local_llm.md`) | none |
| Experiments on the Mac | llama-server on 127.0.0.1, Metal | the same Q4_K_M GGUF | none beyond localhost |
| Experiments on the HPC | the official vLLM container for Apertus 1.5 on one H100 (`docs/hpc.md`) | `swiss-ai/Apertus-v1.5-8B`, BF16, pinned revision | none (offline mode) |

## Evaluation (not part of the method)

```
 outputs (items.jsonl) ──► final judge: Qwen3-14B BF16 (HPC) or Qwen3-8B Q4 (Mac), temperature 0
                             - lists the source's facts once
                             - marks each fact kept / changed / dropped in each output
                             - lists added facts
                          ──► reports: fit, fact recall, added-fact rate, fit & complete,
                              bootstrap intervals over sentences (isochron.pilot_report, step2_report)
```

The judge is validated before use on two control suites (`data/nli_controls.jsonl`,
`data/judge_controls_de.jsonl`). It runs only after generation, on its own server, and never feeds
generation.

## Build time and run time

- **Build time** (`docker compose build`) needs the internet:
  - Debian packages;
  - the eSpeak NG 1.52.0 and sonic sources (pinned by SHA-256);
  - the Python packages of `uv.lock`, hash-checked, with torch at the locked version as its CPU build;
  - the NLI model from Hugging Face, at its pinned revision;
  - the base, uv and llama.cpp images, each pinned by digest.
- **Run time:**
  - `make run` needs only the LLM endpoint.
  - `make run-offline` needs nothing at all.
