#!/bin/bash
# The Qwen3-TTS environment and weights (protocol v2.28), without a GPU.
# - A venv of its own, $ISOCHRON_WORK/tts-qwen/venv, from the hashed lock hpc/tts_qwen_requirements.txt: torch,
#   torchaudio, triton and the CUDA libraries from download.pytorch.org, every other wheel from
#   $ISOCHRON_WORK/tts-qwen/wheels (copied from the Mac; the cluster's PyPI is throttled). sox and openai-whisper
#   come only as source, so their pure-Python wheels were built on the Mac (pip wheel --no-deps) and go in
#   without hash checks, like qwen-tts 0.1.1, which goes in without its dependencies (no gradio demo).
# - Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice at a pinned revision, and Whisper small (its loader checks the
#   SHA-256), into $ISOCHRON_WORK/tts-qwen.
# Submit from track_2b/:
#   sbatch --account=aisc --partition=pot-hpi-aisc-batch --nodes=1 --exclude=ga03 --cpus-per-task=8 --mem=16G --time=00:45:00 --job-name=isochron-tts-qwen-setup --output=hpc/logs/%x-%j.out --wrap="bash hpc/tts_qwen_setup.sh"
set -euo pipefail
. hpc/env.sh
. hpc/lib.sh
require_compute_node
Q=$ISOCHRON_WORK/tts-qwen
QWEN_REVISION=0c0e3051f131929182e2c023b9537f8b1c68adfe
if [ ! -x "$Q/venv/bin/python" ]; then
    uv venv --python 3.11 "$Q/venv"
    python3 - hpc/tts_qwen_requirements.txt "$Q/hashed.txt" <<'PY'
import re, sys
out, keep = [], True
for line in open(sys.argv[1]).read().split("\n"):
    m = re.match(r"^([a-z0-9_.-]+)==", line)
    if m:
        keep = m.group(1) not in ("sox", "openai-whisper")
    if keep:
        out.append(line)
open(sys.argv[2], "w").write("\n".join(out))
PY
    VIRTUAL_ENV=$Q/venv uv pip install --index-url https://download.pytorch.org/whl/cu124 \
        --find-links "$Q/wheels" --index-strategy unsafe-best-match --require-hashes -r "$Q/hashed.txt"
    VIRTUAL_ENV=$Q/venv uv pip install --offline --no-index --find-links "$Q/wheels" --no-deps \
        qwen-tts==0.1.1 sox==1.5.0 openai-whisper==20250625
fi
"$Q/venv/bin/python" -c "import qwen_tts, whisper, torch; print('qwen-tts ok, torch', torch.__version__)"
.venv/bin/python -c "
from huggingface_hub import snapshot_download
print(snapshot_download('Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice', revision='$QWEN_REVISION', local_dir='$Q/model'))"
"$Q/venv/bin/python" -c "import whisper; whisper.load_model('small', device='cpu', download_root='$Q/whisper'); print('whisper ok')"
du -sh "$Q/venv" "$Q/model" "$Q/whisper"
log "Qwen3-TTS setup done"
