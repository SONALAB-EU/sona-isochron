# Running Apertus 1.5 8B locally (llama.cpp on Apple Silicon)

This is how the experiments reach Apertus on a Mac: llama-server runs a 4-bit
GGUF on the GPU (Metal) and exposes an OpenAI-compatible API, and the code
reaches it only through `LLM_NAME`, `LLM_BASE_URL` and `LLM_API_KEY`.
Everything below was set up and checked on 2026-10-09 on an Apple M3 with
16 GB RAM.

## What runs, and why this file

| Step | Artefact | Licence |
|------|----------|---------|
| Official model | [`swiss-ai/Apertus-v1.5-8B`](https://huggingface.co/swiss-ai/Apertus-v1.5-8B), revision `a411d83` (gated) | Apache-2.0 + Apertus 1.5 Acceptable Use Policy |
| Text-only conversion | [`andreasmartin/apertus-v1.5-8b-text`](https://huggingface.co/andreasmartin/apertus-v1.5-8b-text), revision `c0e7eeb` | Apache-2.0 (same policy) |
| 4-bit GGUF | [`Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF`](https://huggingface.co/Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF), revision `248ec68`, file `apertus-v1.5-8b-text-q4_k_m.gguf`, 5,059,027,136 bytes, SHA-256 `a037df8d87ff6caacee794ee85f55342f2152e0d359b7389033300c3bee5f299` | Apache-2.0 (same policy) |
| Server | llama.cpp 0.6.0, build 11429 (`d81235049`), Homebrew | MIT |

Why not the official checkpoint directly:
- Apertus 1.5 is published as the multimodal architecture
  `Apertus1p5ForConditionalGeneration`, and the official model's quantisation
  list has no GGUF.
- llama.cpp's own converter (build 11429) rejects it: `ERROR:hf-to-gguf:Model
  Apertus1p5ForConditionalGeneration is not supported`.

The only Q4_K_M GGUF of Apertus 1.5 8B is the one above. It was made with
ggml-org's GGUF-my-repo from the text-only conversion. That conversion, as
documented on its model card:
- copies the text backbone bit for bit into the `ApertusForCausalLM` format
  (the Apertus 1 architecture, which llama.cpp supports);
- cuts the input embeddings from 266,752 to 131,272 rows, dropping the image
  and audio codes;
- adds 200 untrained output rows for special tokens;
- removes the vision and audio towers.

Its author did not run a full logit comparison against the official model.

What we checked in the GGUF and the running server:
- architecture `apertus`, 32 layers, 131,272-token vocabulary;
- xIELU parameters per layer, RoPE base 4,000,000, and a `rope_freqs` tensor
  for the llama3-style RoPE scaling;
- end-of-turn token 68 `<|assistant_end|>`;
- every one of the 20 smoke-test requests ended with `finish_reason: stop`.

## Requirements

- Apple Silicon with at least 16 GB RAM, and about 6 GB of free disk space.
- llama.cpp from Homebrew (`brew install llama.cpp`; it was already installed
  here).
- Access to the gated official repo is not needed for the GGUF. The GGUF's
  card points to the Apertus 1.5 Acceptable Use Policy, which applies.

## Download the weights (into ~/models)

Run this from `track_2b/`, where `uv` provides `huggingface_hub`:

```
mkdir -p ~/models/apertus-v1.5-8b-text-Q4_K_M-GGUF
uv run python -c "from huggingface_hub import hf_hub_download; print(hf_hub_download('Colby/apertus-v1.5-8b-text-Q4_K_M-GGUF', 'apertus-v1.5-8b-text-q4_k_m.gguf', revision='248ec68a63e219e3f061e4c946fc8a20d63b9975', local_dir='$HOME/models/apertus-v1.5-8b-text-Q4_K_M-GGUF'))"
shasum -a 256 ~/models/apertus-v1.5-8b-text-Q4_K_M-GGUF/apertus-v1.5-8b-text-q4_k_m.gguf
```

The checksum must match the SHA-256 above.

## Start the server (in its own terminal)

```
llama-server -m ~/models/apertus-v1.5-8b-text-Q4_K_M-GGUF/apertus-v1.5-8b-text-q4_k_m.gguf --alias apertus-v1.5-8b-text-q4_k_m --host 127.0.0.1 --port 8080 -c 8192 -np 1 -ngl all --reasoning off
```

What the options do:
- `-ngl all` puts all 33 layers on the GPU through Metal. The log (with
  `-lv 4`) shows `offloaded 33/33 layers to GPU`, 4,817 MiB of model and
  1,024 MiB of KV cache.
- `-c 8192 -np 1` gives one slot with the full 8,192-token context. The
  default would split the context over several slots.
- `--reasoning off` turns thinking mode off. The rendered prompt then contains
  `Deliberation: disabled`. Each request also sends
  `chat_template_kwargs: {"enable_thinking": false}`.
  `--chat-template-kwargs '{"enable_thinking":false}'` works too, but this
  build marks it as deprecated.
- `--host 127.0.0.1` keeps the server local. It runs without an API key, so
  do not expose it on a network.

## Point the code at it

`track_2b/.env` (git-ignored) holds three variables:

```
LLM_NAME=<the --alias above>
LLM_BASE_URL=http://<--host>:<--port>/v1
LLM_API_KEY=<any non-empty string; the server ignores it>
```

## Check it works

Run these from `track_2b/`; they read the endpoint from `.env`:

```
set -a; . ./.env; set +a
curl -s "$LLM_BASE_URL/models"
curl -s -X POST "${LLM_BASE_URL%/v1}/apply-template" -H 'Content-Type: application/json' -d '{"messages":[{"role":"user","content":"Hallo"}]}'
```

The first command lists the alias with `n_vocab` 131272 and `ftype`
"Q4_K - Medium". The second shows the rendered prompt, which must contain
`Deliberation: disabled`.

## Measured speed (M3, 16 GB, step 2 smoke run, 2026-10-09)

- Generation: 18.3 tokens/s (1,865 tokens in 101.7 s).
- Prompt processing: 167.7 tokens/s.
- About 93 generated tokens and 5.7 s per step 2 request (4 candidates in one
  JSON answer).
- Requests run one at a time, with one server slot.

## The meaning judge (phase 2, evaluation only)

The final meaning judge is Qwen3-8B. It runs as a second llama-server on
port 8081, only after generation and only while the Apertus server is
stopped: the two models do not fit in 16 GB together. `isochron.judge`
refuses to run while the Apertus endpoint answers.

```
mkdir -p ~/models/Qwen3-8B-GGUF
uv run python -c "from huggingface_hub import hf_hub_download; print(hf_hub_download('Qwen/Qwen3-8B-GGUF', 'Qwen3-8B-Q4_K_M.gguf', revision='7c41481f57cb95916b40956ab2f0b139b296d974', local_dir='$HOME/models/Qwen3-8B-GGUF'))"
shasum -a 256 ~/models/Qwen3-8B-GGUF/Qwen3-8B-Q4_K_M.gguf
llama-server -m ~/models/Qwen3-8B-GGUF/Qwen3-8B-Q4_K_M.gguf --alias qwen3-8b-q4_k_m --host 127.0.0.1 --port 8081 -c 8192 -np 1 -ngl all --reasoning off
```

The SHA-256 must be
`d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`. The
judge is reached through three more variables in `.env`:

```
JUDGE_NAME=<the --alias above>
JUDGE_BASE_URL=http://<--host>:<--port>/v1
JUDGE_API_KEY=<any non-empty string>
```

## Warnings you will see

- `special_eos_id is not in special_eog_ids`: generation still ends at
  `<|assistant_end|>` (all smoke requests finished with `stop`).
- `no API key is set and CORS allows all origins`: bind to 127.0.0.1 only.
- `server default port will be changed to :9931`: we set `--port`
  explicitly.
