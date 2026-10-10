#!/bin/bash
#SBATCH --job-name=isochron-70b
#SBATCH --account=aisc
#SBATCH --partition=pot-hpi-aisc-batch
#SBATCH --gres=gpu:h100:2
#SBATCH --exclude=ga03
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=256G
#SBATCH --time=36:00:00
#SBATCH --output=hpc/logs/%x-%j.out
#
# Apertus 1.5 70B in BF16 on two H100s with tensor parallelism (vLLM), the same experiments as
# hpc/run.sbatch, then the judge Qwen3-14B. Submit from track_2b/, best after the 8B job, so the
# judge starts from the 8B job's cache and both runs are judged against the same fact lists:
#   sbatch --dependency=afterany:<8B job id> hpc/run_70b.sbatch
#
# The weights take about 67 GiB on each GPU, so vLLM gets 92 % of the memory and few sequences
# at once; the loop's NLI (about 2 GiB) uses what is left. The fused all-reduce RMS pass is off,
# as the model card advises for tensor parallelism.
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
if [ -z "${VLLM_EXTRA:-}" ]; then
    VLLM_EXTRA="--max-num-seqs 16 --max-num-batched-tokens 4096 --compilation-config.pass_config.fuse_allreduce_rms false"
fi
export MODEL_KEY=70b TP=2 GPU_UTIL=${GPU_UTIL:-0.92} VLLM_EXTRA
export JUDGE_SEED_CACHE=${JUDGE_SEED_CACHE:-results/raw/judge_cache_hpc_8b.jsonl}
exec bash hpc/pipeline.sh
