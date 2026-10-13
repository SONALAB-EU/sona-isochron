#!/bin/bash
# The TTS environment and weights for the time check, without a GPU (docs/hpc.md, "TTS for the time check").
# - A venv of its own, $ISOCHRON_WORK/tts/venv, from the hashed lock hpc/tts_requirements.txt: torch,
#   torchaudio, triton and the CUDA libraries from download.pytorch.org (fast from the cluster), every other
#   wheel from $ISOCHRON_WORK/tts/wheels, copied there from the Mac (the cluster's PyPI is throttled; on the
#   Mac: pip download -r hpc/tts_requirements.txt --platform manylinux_2_28_x86_64 --python-version 3.11
#   --only-binary=:all: --no-deps). chatterbox-tts 0.1.7 goes in without its dependencies: they are in the
#   lock, without its gradio demo.
# - Chatterbox's multilingual weights at a pinned revision, the files its from_pretrained() fetches, into
#   $ISOCHRON_WORK/tts/chatterbox. MIT; no token needed.
# Submit from track_2b/:
#   sbatch --account=aisc --partition=pot-hpi-aisc-batch --nodes=1 --exclude=ga03 --cpus-per-task=8 --mem=16G --time=00:45:00 --job-name=isochron-tts-setup --output=hpc/logs/%x-%j.out --wrap="bash hpc/tts_setup.sh"
set -euo pipefail
. hpc/env.sh
. hpc/lib.sh
require_compute_node
TTS=$ISOCHRON_WORK/tts
CHATTERBOX_REVISION=5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18
if [ ! -x "$TTS/venv/bin/python" ]; then
    uv venv --python 3.11 "$TTS/venv"
    VIRTUAL_ENV=$TTS/venv uv pip install --index-url https://download.pytorch.org/whl/cu124 \
        --find-links "$TTS/wheels" --index-strategy unsafe-best-match --require-hashes -r hpc/tts_requirements.txt
    VIRTUAL_ENV=$TTS/venv uv pip install --offline --no-index --find-links "$TTS/wheels" --no-deps chatterbox-tts==0.1.7
fi
"$TTS/venv/bin/python" -c "import chatterbox.mtl_tts, torch; print('chatterbox ok, torch', torch.__version__)"
.venv/bin/python - "$TTS/chatterbox" "$CHATTERBOX_REVISION" <<'PY'
import sys
from huggingface_hub import snapshot_download
path = snapshot_download("ResembleAI/chatterbox", revision=sys.argv[2], local_dir=sys.argv[1],
                         allow_patterns=["ve.pt", "t3_mtl23ls_v2.safetensors", "s3gen.pt",
                                         "grapheme_mtl_merged_expanded_v1.json", "conds.pt", "Cangjie5_TC.json"])
print("weights in", path)
PY
du -sh "$TTS/venv" "$TTS/chatterbox"
log "TTS setup done"
