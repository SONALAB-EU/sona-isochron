#!/bin/bash
#SBATCH --job-name=isochron-8b
#SBATCH --account=aisc
#SBATCH --partition=pot-hpi-aisc-batch
#SBATCH --gres=gpu:h100:1
#SBATCH --exclude=ga03
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=12:00:00
#SBATCH --output=hpc/logs/%x-%j.out
#
# Apertus 1.5 8B in BF16 on one H100: vLLM container (or SERVER=transformers), step 2 with prompt v1
# and the repair loop against it, then the judge Qwen3-14B on the same outputs (hpc/pipeline.sh).
# Submit from track_2b/:  sbatch hpc/run.sbatch
# vLLM gets 60 % of the GPU memory (the model card's setting); the loop's NLI uses the rest.
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
export MODEL_KEY=8b TP=1 GPU_UTIL=${GPU_UTIL:-0.6}
exec bash hpc/pipeline.sh
