# Running the experiments on the HPI cluster

This runbook takes the experiments from this repository to the cluster and back: Apertus 1.5 in
BF16 behind an OpenAI-compatible server, step 2 with our method (prompt v1 and the repair loop),
then the judge Qwen3-14B on the same outputs.

On 2026-10-10 the cluster facts below were checked; the code was copied, `hpc/setup.sh` was run and the
vLLM image was pulled (see "What has been run"). No models have been downloaded and no experiment has run.

## What runs where

| File | What it does | How it is started |
|------|--------------|-------------------|
| `hpc/sync_include.txt` | rsync allowlist: code, data and reports; never `.env`, audio, weights, caches or `results/raw/` | `rsync --filter='merge hpc/sync_include.txt'` |
| `hpc/setup.sh` | `prefetch`: uv 0.12.3, Python 3.11.15 (uv-managed), the locked environment (torch from PyPI) and eSpeak NG 1.52.0 built from source, without a GPU; `container`: imports the vLLM image; no argument: whatever is missing, then the GPU check and the tests; `fallback`: the transformers fork | `sbatch … --wrap="bash hpc/setup.sh prefetch"`, then `srun … bash hpc/setup.sh` |
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

## Cluster facts (checked on 2026-10-10)

- **Access.** `ssh hpi-login`, the alias in `~/.ssh/config` for `kaushik.mukherjee@hpc.sci.hpi.de`; it uses
  a key and needs the VPN. The login node is `lx01` (x86_64, bash).
  - There, `/sc/home` and `/sc/projects` are mounted `noexec`, so scripts are started as
    `bash script.sh`.
  - On the login node: only file operations, `squeue`, `sbatch`, `srun` and short checks.
- **GPUs.** H100s are GRES `gpu:h100`: nodes gx07–gx12 and gx14 have 8 each (80 GB), and gx13v1 has 4.
  - Their features include `GPU_SKU:H100` and `ARCH:X86`.
  - The batch partition also has A30s (gx17v1) and two L40s on the ARM node ga03. So every job asks
    for `gpu:h100` and excludes ga03.
- **Partitions.**
  - `pot-hpi-aisc-shortrun`: at most 1 h, default 30 min.
  - `pot-hpi-aisc-batch`: at most 7 days, default 1 day.
  - QoS `aisc` or `normal`. There is no default memory limit, so every job sets `--mem`.
- **Compute nodes** (checked on gx07).
  - Ubuntu 24.04.4, glibc 2.39, NVIDIA driver 590.48.01 (CUDA 13.1).
  - gcc 13.3, make, cmake, git and curl. There is no `module` command.
  - Internet to huggingface.co, ghcr.io, github.com and pypi.org works, but it is **throttled per
    connection**. Measured with 20–25 s downloads on gx07, gx08 and the login node:

    | Source | One connection | Eight connections |
    |--------|---------------:|------------------:|
    | PyPI (files.pythonhosted.org) | 0.1–0.6 MB/s | 0.9 MB/s |
    | Hugging Face | 0.6–4 MB/s | 34 MB/s |
    | ghcr.io | 0.1–2.9 MB/s | not measured |

    - uv fetches each wheel over one connection, so the torch wheel alone (about 900 MB) takes about
      an hour. That is why the downloads in step 3 run as batch jobs.
    - Hugging Face downloads (hf-xet) use many connections and are much faster.
  - CPU-only jobs are accepted, so downloads need not hold a GPU.
  - `/sc/home` is executable there. `$TMPDIR` is the job's local scratch (`/scratch/<job id>`).
- **Storage.**
  - Home is a 200 GB quota on VAST (174 GB free on 2026-10-10). That is enough for everything except
    the 70B weights (about 145 GB).
  - Larger places: the group-writable project directory `/sc/projects/sci-aisc` (group
    `aisc-storage`), and the GPFS scratch `/sc/scratch` (305 TB free; its purge policy is not
    known).
- **Containers.** pyxis (`--container-image`, `--container-save`) with enroot 4.2.1.
  - pyxis runs the image's entrypoint.
  - enroot keeps its layer cache in `~/.cache/enroot` and running containers in
    `~/.local/share/enroot`.
  - A pyxis pull of the 8.9 GB vLLM image started fine (registry reachable, image found), but at
    these rates it did not finish within shortrun's hour; large layers stalled and restarted.
  - So step 3 imports the image with `enroot import` in a batch job with retries. The layers already
    downloaded stay in enroot's cache and are reused.

## Before you start

- The HPI VPN is connected.
- Your Hugging Face account has accepted the terms of `swiss-ai/Apertus-v1.5-8B` (and
  `swiss-ai/Apertus-v1.5-70B` for the 70B job), and you have a read token at hand.
- Disk: `$HOME/isochron_work` gets about 90 GB, which fits the home quota. For the 70B model, put
  the weights elsewhere: `export ISOCHRON_MODELS=<a larger directory>` before the 70B download and
  every 70B job. That directory is your choice; `/sc/projects/sci-aisc` is shared with your group.

## Commands, in order

### 1. On the Mac: copy the code (from `track_2b/`)

```
ssh hpi-login mkdir -p isochron/track_2b
rsync -av --filter='merge hpc/sync_include.txt' ./ hpi-login:isochron/track_2b/
```

The same `rsync` command copies later code changes. It never deletes files on the cluster.

### 2. Log in

```
ssh hpi-login
cd ~/isochron/track_2b
mkdir -p hpc/logs
```

The H100 GRES name is `gpu:h100` (checked; see the cluster facts above), which every command below uses.

### 3. Set up (once): downloads as CPU-only batch jobs, then the checks on an H100

```
sbatch --account=aisc --partition=pot-hpi-aisc-batch --nodes=1 --exclude=ga03 --cpus-per-task=8 --mem=32G --time=06:00:00 --job-name=isochron-prefetch --output=hpc/logs/%x-%j.out --wrap="bash hpc/setup.sh prefetch"
sbatch --account=aisc --partition=pot-hpi-aisc-batch --nodes=1 --exclude=ga03 --cpus-per-task=8 --mem=32G --time=06:00:00 --job-name=isochron-container --output=hpc/logs/%x-%j.out --wrap="bash hpc/setup.sh container"
squeue -u $USER
srun --account=aisc --partition=pot-hpi-aisc-shortrun --nodes=1 --gres=gpu:h100:1 --exclude=ga03 --cpus-per-task=8 --mem=32G --time=01:00:00 bash hpc/setup.sh
```

The two batch jobs do every download and the eSpeak NG build without a GPU.
- Run the last command when `squeue` no longer lists them.
- Their logs are `hpc/logs/isochron-prefetch-<job id>.out` and `hpc/logs/isochron-container-<job id>.out`.

The last command checks the GPU and ends with the test suite.
- `tests/test_syllable_reference.py` must pass: the cluster's eSpeak NG then counts every German and
  French reference sentence exactly as the Mac does. A CMake build from source matched Homebrew's
  1.52.0 on all 963 sentences locally.
- The NLI tests are skipped until step 4.

### 4. Download the models (once, in your own SSH session)

```
read -rs HF_TOKEN
export HF_TOKEN
srun --account=aisc --partition=pot-hpi-aisc-shortrun --nodes=1 --exclude=ga03 --cpus-per-task=8 --mem=32G --time=01:00:00 bash hpc/download_models.sh
unset HF_TOKEN
```

- `read -rs` waits for you to paste the token and press Enter. It shows nothing and keeps nothing in
  the shell history.
- `srun` hands the token to the job in memory. Do not use `sbatch` here: Slurm stores a batch job's
  environment on its controller.
- Apertus 1.5 8B, Qwen3-14B and the NLI model come to about 48 GB. At the rates above that should
  take about 25–40 minutes (an estimate). If the job hits the one-hour limit, run the same `srun` line
  again: downloads resume.
- For the 70B job only (about 145 GB, more than the home quota leaves), choose a directory with
  space. Then run, each time with your token exported:

  ```
  export ISOCHRON_MODELS_70B=<a directory with space>
  srun --account=aisc --partition=pot-hpi-aisc-shortrun --nodes=1 --exclude=ga03 --cpus-per-task=8 --mem=32G --time=01:00:00 bash hpc/download_models.sh --70b
  ```

  Repeat the `srun` line until it ends with "models:" (each run resumes). Keep `ISOCHRON_MODELS_70B`
  exported when you submit the 70B job.

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
srun --account=aisc --partition=pot-hpi-aisc-shortrun --nodes=1 --gres=gpu:h100:1 --exclude=ga03 --cpus-per-task=8 --mem=32G --time=01:00:00 bash hpc/setup.sh fallback
sbatch --export=ALL,SERVER=transformers hpc/run.sbatch
```

This uses the transformers fork named on the model card, at its pinned commit. Requests run one at
a time, so expect it to be several times slower than vLLM.

### 9. On the Mac: copy the results back (from `track_2b/`)

```
rsync -av --include='/results/' --include='/results/*.md' --exclude='*' hpi-login:isochron/track_2b/ ./
rsync -av hpi-login:isochron/track_2b/results/raw/hpc_8b_step2_de_test results/raw/
rsync -av hpi-login:isochron/track_2b/results/raw/hpc_70b_step2_de_test results/raw/
```

- The first line brings the reports.
- The other two bring the raw runs (`items.jsonl`, `judge.jsonl`, configs). They stay in the
  git-ignored `results/raw/`, as locally.

## GPU-hours per run (estimates, not measurements)

| Job | GPUs | Wall time | GPU-hours |
|-----|-----:|----------:|----------:|
| Setup: downloads and container import (CPU-only batch jobs), then the checks on an H100 | 0, then 1 | 1–3 h, then about 10 min | about 0.2 |
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

- **`Invalid generic resource (gres) specification`:** check the GRES names with
  `sinfo -p pot-hpi-aisc-batch -o "%20N %40G"`; on 2026-10-10 the H100s were `gpu:h100`.
- **The 70B server runs out of memory at start-up:** try
  `sbatch --export=ALL,GPU_UTIL=0.95 hpc/run_70b.sbatch`. If that is not enough, add `--enforce-eager`
  to `VLLM_EXTRA`, or move the NLI to the CPU with `NLI_DEVICE=cpu`.
- **`enroot import` runs out of space:** set `ENROOT_CACHE_PATH` and `ENROOT_TEMP_PATH` to a directory
  under `ISOCHRON_WORK`, then run the container step again.
- **The server log:** `results/raw/logs/server-hpc_<8b|70b>-<apertus|judge>-<time>.log`.
