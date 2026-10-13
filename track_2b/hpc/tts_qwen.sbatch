#!/bin/bash
#SBATCH --job-name=isochron-tts-qwen
#SBATCH --account=aisc
#SBATCH --partition=pot-hpi-aisc-batch
#SBATCH --gres=gpu:h100:1
#SBATCH --exclude=ga03
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:18:00
#SBATCH --output=hpc/logs/%x-%j.out
#
# Qwen3-TTS for the time check and the demo (protocol v2.28): every text in the plan, in rounds of one batch,
# until it has 3 clean takes (Whisper) or 10 rounds have passed. One H100 for at most 18 min, so the job can
# never use more than 0.3 H100-hours; the script starts no round after 13 min.
# Before submitting: hpc/tts_qwen_setup.sh (as its batch job), and the plan in results/raw/time_check/plan.jsonl.
# Submit from track_2b/:  sbatch hpc/tts_qwen.sbatch
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
. hpc/env.sh
. hpc/lib.sh
require_compute_node
require_gpu
Q=$ISOCHRON_WORK/tts-qwen
[ -x "$Q/venv/bin/python" ] || die "no Qwen3-TTS environment: run hpc/tts_qwen_setup.sh first"
[ -s results/raw/time_check/plan.jsonl ] || die "no plan: copy results/raw/time_check/plan.jsonl first"
export HF_HUB_OFFLINE=1
log "job $SLURM_JOB_ID: Qwen3-TTS ($(cat .git_commit 2> /dev/null || echo 'no .git_commit'))"
"$Q/venv/bin/python" hpc/tts_qwen_synth.py results/raw/time_check/plan.jsonl --model "$Q/model" --whisper "$Q/whisper" \
    --out results/raw/time_check/qwen --budget-min 13
log "done"
