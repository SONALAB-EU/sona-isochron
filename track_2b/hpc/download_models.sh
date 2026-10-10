#!/bin/bash
# Download the models into $ISOCHRON_WORK, on a compute node (through srun), at pinned revisions:
#   Apertus 1.5 8B (BF16, gated) and the judge Qwen3-14B into $ISOCHRON_WORK/models,
#   the NLI model into the Hugging Face cache, and with --70b also Apertus 1.5 70B.
#
#   bash hpc/download_models.sh [--70b]
#
# HF_TOKEN is read from the environment only (the Apertus repositories are gated). It is never
# written to disk: no login, no token file. Downloads resume if they are interrupted.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

require_compute_node
[ -n "${HF_TOKEN:-}" ] || die "HF_TOKEN is not set in the environment (see docs/hpc.md)"
[ -x "$REPO/.venv/bin/python" ] || die "no project environment: run  bash hpc/setup.sh  first"
with_70b=0
[ "${1:-}" = --70b ] && with_70b=1
mkdir -p "$MODELS"
cd "$REPO"

uv run --no-sync python - "$MODELS" "$with_70b" \
    "$APERTUS_8B_REPO" "$APERTUS_8B_REV" "$JUDGE_REPO" "$JUDGE_REV" "$APERTUS_70B_REPO" "$APERTUS_70B_REV" <<'PY'
import os
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

models, with_70b, *pinned = sys.argv[1:]
repos = list(zip(pinned[0::2], pinned[1::2]))
if with_70b != "1":
    repos = repos[:2]
token = os.environ["HF_TOKEN"]  # passed to each call; huggingface_hub never stores it unless asked to log in
for repo, rev in repos:
    target = Path(models) / repo
    print(f"downloading {repo} @ {rev} to {target}", flush=True)
    snapshot_download(repo, revision=rev, local_dir=target, token=token, ignore_patterns=["*.pdf", "assets/*"])
    size = sum(p.stat().st_size for p in target.rglob("*") if p.is_file() and ".cache" not in p.parts)
    print(f"  {repo}: {size / 1e9:.1f} GB", flush=True)

from isochron.metrics.meaning import MODEL_ID, REVISION, NLI

NLI(device="cpu")  # downloads exactly the files the NLI loads into the Hugging Face cache
print(f"NLI model {MODEL_ID} @ {REVISION} is in {os.environ['HF_HOME']}", flush=True)
PY
log "models in $MODELS:"
du -sh "$MODELS"/*/* 2> /dev/null || true
