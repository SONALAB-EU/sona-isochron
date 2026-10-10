#!/bin/bash
# Download the models into $ISOCHRON_WORK, on a compute node (through srun), at pinned revisions:
#   Apertus 1.5 8B (BF16, gated) and the judge Qwen3-14B into $ISOCHRON_WORK/models,
#   the NLI model into the Hugging Face cache, and with --70b also Apertus 1.5 70B
#   (into $ISOCHRON_MODELS_70B if set: it does not fit the home quota with the rest).
#
#   bash hpc/download_models.sh [--70b]
#   bash hpc/download_models.sh --open      only the models that need no token: Qwen3-14B and the NLI model
#
# HF_TOKEN is read from the environment only (the Apertus repositories are gated). It is never
# written to disk: no login, no token file. Downloads resume if they are interrupted; two downloads of
# the same files can run at once (huggingface_hub locks each file).
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

main() {
    local with_70b=0 open_only=0
    require_compute_node
    case ${1:-} in
        --70b) with_70b=1 ;;
        --open) open_only=1 ;;
        "") ;;
        *) die "unknown option $1: --70b or --open" ;;
    esac
    [ "$open_only" = 1 ] || [ -n "${HF_TOKEN:-}" ] || die "HF_TOKEN is not set in the environment (see docs/hpc.md)"
    [ -x "$REPO/.venv/bin/python" ] || die "no project environment: run  bash hpc/setup.sh  first"
    mkdir -p "$MODELS" "$MODELS_70B"
    cd "$REPO"
    uv run --no-sync python - "$with_70b" "$open_only" "$MODELS" "$APERTUS_8B_REPO" "$APERTUS_8B_REV" "$MODELS" \
        "$JUDGE_REPO" "$JUDGE_REV" "$MODELS_70B" "$APERTUS_70B_REPO" "$APERTUS_70B_REV" <<'PY'
import os
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

with_70b, open_only, *pinned = sys.argv[1:]
repos = list(zip(pinned[0::3], pinned[1::3], pinned[2::3]))
if open_only == "1":
    repos = repos[1:2]  # the judge only: the Apertus repositories are gated
elif with_70b != "1":
    repos = repos[:2]
token = os.environ.get("HF_TOKEN")  # passed to each call; huggingface_hub never stores it unless asked to log in
for root, repo, rev in repos:
    target = Path(root) / repo
    print(f"downloading {repo} @ {rev} to {target}", flush=True)
    snapshot_download(repo, revision=rev, local_dir=target, token=token, ignore_patterns=["*.pdf", "assets/*"])
    size = sum(p.stat().st_size for p in target.rglob("*") if p.is_file() and ".cache" not in p.parts)
    print(f"  {repo}: {size / 1e9:.1f} GB", flush=True)

from isochron.metrics.meaning import MODEL_ID, REVISION, NLI

NLI(device="cpu")  # downloads exactly the files the NLI loads into the Hugging Face cache
print(f"NLI model {MODEL_ID} @ {REVISION} is in {os.environ['HF_HOME']}", flush=True)
PY
    log "models:"
    du -sh "$MODELS"/*/* "$MODELS_70B"/*/* 2> /dev/null | sort -u || true
}

# bash reads a script while it runs it; with everything in main and this one last line, the file is read to
# the end before anything runs, so replacing it (an rsync) cannot break a running job
main "$@"; exit
