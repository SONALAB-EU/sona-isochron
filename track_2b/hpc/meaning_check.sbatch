#!/bin/bash
#SBATCH --job-name=isochron-nli2
#SBATCH --account=aisc
#SBATCH --partition=pot-hpi-aisc-batch
#SBATCH --gres=gpu:h100:1
#SBATCH --exclude=ga03
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:30:00
#SBATCH --output=hpc/logs/%x-%j.out
#
# Post-hoc, added after test outputs existed: a second NLI model, which the repair loop never sees, scores
# every step 4 test output, and both NLI models score the planted controls (isochron.meaning_check score).
# Inference only, offline. Before submitting, from track_2b/ on the Mac (docs/hpc.md, "A second NLI model"):
#   the pairs file in results/raw/meaning_check/pairs.jsonl, and the model in the Hugging Face cache.
# Submit from track_2b/:  sbatch hpc/meaning_check.sbatch
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
. hpc/env.sh
. hpc/lib.sh
require_compute_node
require_gpu
[ -x .venv/bin/python ] || die "no project environment: run  bash hpc/setup.sh  first"
[ -s results/raw/meaning_check/pairs.jsonl ] || die "no pairs: copy results/raw/meaning_check/pairs.jsonl first"
export HF_HUB_OFFLINE=1
log "job $SLURM_JOB_ID: isochron.meaning_check score ($(cat .git_commit 2> /dev/null || echo 'no .git_commit'))"
uv run --no-sync python -m isochron.meaning_check score --pairs results/raw/meaning_check/pairs.jsonl \
    --out results/raw/meaning_check --device cuda
log "done"
