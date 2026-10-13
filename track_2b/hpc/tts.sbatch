#!/bin/bash
#SBATCH --job-name=isochron-tts
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
# The time check's speech (exploratory, post-hoc, added after test outputs existed; protocol v2.24): Chatterbox
# multilingual reads every text in the plan 3 times (seeds 0, 1, 2), with its default voice. One H100 for at
# most 30 min, so the job can never use more than 0.5 H100-hours; the script stops starting clips after 22.
# Before submitting: bash hpc/tts_setup.sh (as its batch job), and the plan copied to
# results/raw/time_check/plan.jsonl. Submit from track_2b/:  sbatch hpc/tts.sbatch
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
. hpc/env.sh
. hpc/lib.sh
require_compute_node
require_gpu
TTS=$ISOCHRON_WORK/tts
[ -x "$TTS/venv/bin/python" ] || die "no TTS environment: run hpc/tts_setup.sh first"
[ -s results/raw/time_check/plan.jsonl ] || die "no plan: copy results/raw/time_check/plan.jsonl first"
export HF_HUB_OFFLINE=1
log "job $SLURM_JOB_ID: TTS ($(cat .git_commit 2> /dev/null || echo 'no .git_commit'))"
"$TTS/venv/bin/python" hpc/tts_synth.py results/raw/time_check/plan.jsonl --ckpt "$TTS/chatterbox" \
    --out results/raw/time_check/tts --takes 3 --budget-min 22
log "done"
