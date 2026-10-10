# Settings shared by the HPC scripts; they source this file. Nothing here is secret.
#
# ISOCHRON_WORK holds everything large that is not in the repository: tools, the
# uv-managed Python, caches, model weights and the vLLM container. It needs about
# 90 GB; Apertus 1.5 70B adds about 145 GB. The home quota on the HPI cluster is
# 200 GB, so the 70B weights can go elsewhere: export ISOCHRON_MODELS_70B (a directory
# with space) before the 70B download and the 70B job.

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ISOCHRON_WORK=${ISOCHRON_WORK:-$HOME/isochron_work}

UV_VERSION=0.12.3
UV_SHA256=600cf9a742aca00d292673b16b5acffaa7b8c269a364ad0c2e79498dcb1fe101
PYTHON_VERSION=3.11.15

ESPEAK_VERSION=1.52.0
ESPEAK_URL=https://github.com/espeak-ng/espeak-ng/archive/refs/tags/1.52.0.tar.gz
ESPEAK_SHA256=bb4338102ff3b49a81423da8a1a158b420124b055b60fa76cfb4b18677130a23
# eSpeak NG's CMake build fetches sonic at this commit; we download it ourselves so no git is needed
SONIC_URL=https://github.com/waywardgeek/sonic/archive/fbf75c3d6d846bad3bb3d456cbc5d07d9fd8c104.tar.gz
SONIC_SHA256=715827b5a39b79e56e44397d7b845910df996d4cca74777b3b61629b1ddc98c1
CMAKE_VERSION=3.31.6
NINJA_VERSION=1.11.1.4

# The official vLLM build for Apertus 1.5 (model card). On 2026-10-10 the tag pointed to
# sha256:d85533f251c8272218ae2e519510836376e5a335b44f2204f193018e37753bc6
# (vLLM fork commit a601a9d, transformers fork commit 3797303, CUDA 13.0, Python 3.12).
VLLM_IMAGE='ghcr.io#swiss-ai/vllm_apertus_1.5_release:latest-amd64'
VLLM_SQSH=$ISOCHRON_WORK/containers/vllm_apertus_1.5_release-latest-amd64.sqsh

# The fallback when vLLM fails: the transformers fork named on the Apertus 1.5 model card
# (git+https://github.com/swiss-ai/transformers.git@3797303...), as GitHub's archive of the same commit,
# so that installing it needs no git on the node
HF_FALLBACK_TRANSFORMERS='transformers[torch,vision,audio] @ https://github.com/swiss-ai/transformers/archive/3797303dda74844e3d1f8977ff5518bb91f818b4.tar.gz'
HF_FALLBACK_TORCH=2.14.1
HF_VENV=$ISOCHRON_WORK/venv-hf

MODELS=$ISOCHRON_WORK/models
MODELS_70B=${ISOCHRON_MODELS_70B:-$MODELS}
APERTUS_8B_REPO=swiss-ai/Apertus-v1.5-8B
APERTUS_8B_REV=a411d838600baf0e3635a3daf66fb7c55fc97bb6
APERTUS_70B_REPO=swiss-ai/Apertus-v1.5-70B
APERTUS_70B_REV=59e744e313e967811aefabde3732609b64201acc
JUDGE_REPO=Qwen/Qwen3-14B
JUDGE_REV=40c069824f4251a91eefaf281ebe4c544efd3e18

export UV_CACHE_DIR=$ISOCHRON_WORK/uv-cache
# The cluster's internet is throttled per connection (2026-10-10: PyPI about 0.2 MB/s, Hugging Face
# about 2 MB/s per connection), so downloads get long timeouts and retries instead of failing
export UV_HTTP_TIMEOUT=600
export UV_HTTP_RETRIES=10
export ENROOT_TRANSFER_RETRIES=10
export ENROOT_CONNECT_TIMEOUT=60
export UV_PYTHON_INSTALL_DIR=$ISOCHRON_WORK/uv-python
export UV_PYTHON_BIN_DIR=$ISOCHRON_WORK/bin
export UV_PYTHON_PREFERENCE=only-managed
export HF_HOME=$ISOCHRON_WORK/hf
export HF_HUB_DISABLE_TELEMETRY=1
export PATH=$ISOCHRON_WORK/bin:$ISOCHRON_WORK/espeak-ng-$ESPEAK_VERSION/bin:$PATH
