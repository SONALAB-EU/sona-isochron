# Running the experiments on the HPI cluster

This runbook takes the experiments from this repository to the cluster and back: Apertus 1.5 in
BF16 behind an OpenAI-compatible server, step 2 with our method (prompt v1 and the repair loop),
then the judge Qwen3-14B on the same outputs. Nothing has been run on the cluster yet: the
commands below are written and checked locally, but not yet tried there.

## What runs where

| File | What it does | How it is started |
|------|--------------|-------------------|
| `hpc/sync_include.txt` | rsync allowlist: code, data and reports; never `.env`, audio, weights, caches or `results/raw/` | `rsync --filter='merge hpc/sync_include.txt'` |
| `hpc/setup.sh` | uv 0.12.3, Python 3.11.15 (uv-managed), the locked environment (torch from PyPI), eSpeak NG 1.52.0 built from source, then the tests; `container`: imports the vLLM image; `fallback`: the transformers fork | `srun … bash hpc/setup.sh [container\|fallback]` |
| `hpc/download_models.sh` | Apertus 1.5 8B (gated), Qwen3-14B and the NLI model at pinned revisions; `--70b` adds Apertus 1.5 70B. `HF_TOKEN` comes from the environment only and is never written to disk | `srun … bash hpc/download_models.sh [--70b]` |
| `hpc/run.sbatch` | Apertus 1.5 8B, one H100 | `sbatch hpc/run.sbatch` |
| `hpc/run_70b.sbatch` | Apertus 1.5 70B, two H100s, tensor parallelism 2 | `sbatch hpc/run_70b.sbatch` |
| `hpc/pipeline.sh` | what both jobs do (below) | called by the sbatch files |
| `hpc/env.sh`, `hpc/lib.sh` | pinned versions and checksums; server start, health check and stop | sourced |
| `hpc/hf_server.py` | the fallback server on the transformers fork | called by `hpc/pipeline.sh` with `SERVER=transformers` |

A job (`hpc/pipeline.sh`) does three things, and it resumes where an earlier job stopped:

1. It starts Apertus in the official vLLM container `ghcr.io/swiss-ai/vllm_apertus_1.5_release`
   (through pyxis) on `127.0.0.1` with a random port and API key, and waits for `/health`.
   - It runs step 2 against it: German test sentences, levels 90, 80, 70 and 60 %, seeds 0, 1 and 2,
     prompt v1 with the repair loop, 16 items in flight. That is 4,164 items.
   - It then stops the server.
2. It starts Qwen3-14B the same way.
   - It validates the judge on both control suites (`data/judge_controls_de.jsonl`,
     `data/nli_controls.jsonl`), then judges the outputs of step 1.
   - It then stops that server. The two servers never run at once.
3. It writes `results/hpc_<8b|70b>_step2_de_test.md` and
   `results/judge_validation_{hard,nli}_v3_qwen3-14b_hpc_<8b|70b>.md`.

The vLLM settings follow the Apertus 1.5 model card: `--chat-template-content-format string`, and 60 %
of the GPU memory for the 8B model. Two settings are ours:
- `--max-model-len 8192`, as the local setup uses.
- `--generation-config vllm`, so the model's own generation defaults never mix with ours. Every
  request sends temperature 0.7 and top_p 0.95, with no top_k or min_p, as in
  `docs/eval_protocol.md`.

Thinking stays off (`enable_thinking: false` in every request).

## Before you start

- The HPI VPN is connected.
- Your Hugging Face account has accepted the terms of `swiss-ai/Apertus-v1.5-8B` (and
  `swiss-ai/Apertus-v1.5-70B` for the 70B job), and you have a read token at hand.
- Disk: `$HOME/isochron_work` gets about 90 GB, or about 235 GB with the 70B model. If your home
  quota is smaller, put `export ISOCHRON_WORK=<a larger directory>` before every `srun` and `sbatch`
  below.

## Commands, in order

### 1. On the Mac: copy the code (from `track_2b/`)

```
ssh kaushik.mukherjee@hpc.sci.hpi.de mkdir -p isochron/track_2b
rsync -av --filter='merge hpc/sync_include.txt' ./ kaushik.mukherjee@hpc.sci.hpi.de:isochron/track_2b/
```

The same `rsync` command copies later code changes. It never deletes files on the cluster.

### 2. Log in, and check the GPU type name

```
ssh kaushik.mukherjee@hpc.sci.hpi.de
cd ~/isochron/track_2b
sinfo -p pot-hpi-aisc-batch,pot-hpi-aisc-shortrun -o "%25P %15N %45G %f"
```

The scripts ask for H100s as `--gres=gpu:h100:N`. If the GRES column names them differently, use
that type name instead of `h100` in every command below. For the sbatch files, add
`--gres=gpu:<type>:1` (or `:2` for the 70B job) to the `sbatch` command; it overrides the file.

### 3. Set up (once): environment and eSpeak NG, then the container

```
srun --account=aisc --partition=pot-hpi-aisc-shortrun --gres=gpu:h100:1 --exclude=ga03 --cpus-per-task=8 --mem=32G --time=01:00:00 bash hpc/setup.sh
srun --account=aisc --partition=pot-hpi-aisc-shortrun --gres=gpu:h100:1 --exclude=ga03 --cpus-per-task=8 --mem=32G --time=01:00:00 bash hpc/setup.sh container
```

The first command ends with the test suite.
- `tests/test_syllable_reference.py` must pass: the cluster's eSpeak NG then counts every German and
  French reference sentence exactly as the Mac does. A CMake build from source matched Homebrew's
  1.52.0 on all 963 sentences locally.
- The NLI tests are skipped until step 4.

### 4. Download the models (once)

```
read -rs HF_TOKEN
export HF_TOKEN
srun --account=aisc --partition=pot-hpi-aisc-shortrun --gres=gpu:h100:1 --exclude=ga03 --cpus-per-task=8 --mem=32G --time=01:00:00 bash hpc/download_models.sh
srun --account=aisc --partition=pot-hpi-aisc-shortrun --gres=gpu:h100:1 --exclude=ga03 --cpus-per-task=8 --mem=32G --time=01:00:00 bash hpc/download_models.sh --70b
unset HF_TOKEN
```

- `read -rs` waits for you to paste the token and press Enter; it shows nothing and keeps nothing
  in the shell history.
- The `--70b` line is only for the 70B job (about 145 GB). If it runs into the one-hour limit, run
  the same line again: downloads resume.

### 5. Run the 8B job

```
sbatch hpc/run.sbatch
squeue -u $USER
tail -f hpc/logs/isochron-8b-<job id>.out
```

### 6. Run the 70B job, after the 8B job

```
sbatch --dependency=afterany:<8B job id> hpc/run_70b.sbatch
```

Starting after the 8B job lets the 70B job's judge reuse the 8B job's cache, so both runs are
judged against the same fact lists for each sentence.

### 7. If a job runs out of time

Submit the same `sbatch` command again. Generation continues from `items.jsonl`, and the judge from
its cache.

### 8. Only if vLLM fails: the transformers fallback

```
srun --account=aisc --partition=pot-hpi-aisc-shortrun --gres=gpu:h100:1 --exclude=ga03 --cpus-per-task=8 --mem=32G --time=01:00:00 bash hpc/setup.sh fallback
sbatch --export=ALL,SERVER=transformers hpc/run.sbatch
```

This uses the transformers fork named on the model card, at its pinned commit. Requests run one at
a time, so expect it to be several times slower than vLLM.

### 9. On the Mac: copy the results back (from `track_2b/`)

```
rsync -av --include='/results/' --include='/results/*.md' --exclude='*' kaushik.mukherjee@hpc.sci.hpi.de:isochron/track_2b/ ./
rsync -av kaushik.mukherjee@hpc.sci.hpi.de:isochron/track_2b/results/raw/hpc_8b_step2_de_test results/raw/
rsync -av kaushik.mukherjee@hpc.sci.hpi.de:isochron/track_2b/results/raw/hpc_70b_step2_de_test results/raw/
```

- The first line brings the reports.
- The other two bring the raw runs (`items.jsonl`, `judge.jsonl`, configs). They stay in the
  git-ignored `results/raw/`, as locally.

## GPU-hours per run (estimates, not measurements)

| Job | GPUs | Wall time | GPU-hours |
|-----|-----:|----------:|----------:|
| Setup, container and downloads (shortrun; the GPU only fixes the architecture) | 1 | 1–2 h | 1–2 |
| `run.sbatch`: 8B, German test, 4 levels × 3 seeds (4,164 items), plus the judge | 1 | 1–2 h | 1–2 |
| `run_70b.sbatch`: 70B, the same | 2 | 2–4 h | 4–8 |

How these were estimated:
- **Generation.** Measured locally, v1 with the loop needs 2.08 requests per item, with 442 prompt
  and 220 completion tokens (`results/raw/20261009T155640Z_pilot_v1_de_dev`). For 4,164 items that
  is 0.92 M completion tokens.
- **Judge.** About 3.8 requests per output, from the pilot's judge cache. For about 6,900 distinct
  outputs that is about 26,000 short requests; prefix caching helps, because all the questions about
  one output share their start.
- **Assumed vLLM throughput with 16 sequences in flight** (not measured): 1,000–2,000 completion
  tokens/s for 8B BF16 on one H100, and 250–500 for 70B BF16 on two.
- **Start-up.** Loading weights and compiling: 10–30 min per server.
- **Real figures.** The job log and the report's time column give them after the first job. Adding
  French (`LANGS="de fr"`) roughly doubles generation and judging.

## Choices made here

- **Languages.** The jobs run German only (`LANGS=de`): the method was piloted on German, and the
  hard judge controls are German. For French as well, submit with `--export=ALL,LANGS="de fr"`.
- **NLI.** It runs on the GPU next to vLLM. For the 70B model, vLLM gets 92 % of each GPU, and the
  NLI the rest.
- **Run-to-run reproducibility.** Items run 16 at a time against one server. Seeds are fixed per
  item and round, but batching changes the arithmetic slightly, so outputs need not match a
  sequential run bit for bit. Each run's `config.json` records the number of workers and every
  session.

## If something goes wrong

- **`Invalid generic resource (gres) specification`:** the GPU type name differs; see step 2.
- **`no C compiler on this node`:** look for a compiler module with `module avail gcc`, load it
  with `module load <name>`, then run step 3 again.
- **The 70B server runs out of memory at start-up:** try
  `sbatch --export=ALL,GPU_UTIL=0.95 hpc/run_70b.sbatch`. If that is not enough, add `--enforce-eager`
  to `VLLM_EXTRA`, or move the NLI to the CPU with `NLI_DEVICE=cpu`.
- **`enroot import` runs out of space:** set `ENROOT_CACHE_PATH` and `ENROOT_TEMP_PATH` to a directory
  under `ISOCHRON_WORK`, then run the container step again.
- **The server log:** `results/raw/logs/server-hpc_<8b|70b>-<apertus|judge>-<time>.log`.
