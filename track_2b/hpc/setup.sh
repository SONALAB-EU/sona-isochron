#!/bin/bash
# Set up the cluster side, on an H100 node (through srun, so the architecture matches):
#
#   bash hpc/setup.sh             uv (pinned), uv-managed Python, the project environment from uv.lock
#                                 (torch from PyPI), eSpeak NG 1.52.0 built from source, then the tests
#   bash hpc/setup.sh container   import the vLLM container for Apertus 1.5 into a squashfs file
#   bash hpc/setup.sh fallback    a second environment with the transformers fork (if vLLM fails)
#
# Every download is pinned by version and checked by SHA-256 where a file is fetched directly.
# Running a step again skips what is already in place.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

install_uv() {
    if [ -x "$ISOCHRON_WORK/bin/uv" ] && [ "$("$ISOCHRON_WORK/bin/uv" --version | cut -d' ' -f2)" = "$UV_VERSION" ]; then
        log "uv $UV_VERSION already installed"
        return
    fi
    local tmp
    tmp=$(mktemp -d "$ISOCHRON_WORK/tmp.XXXXXX")
    curl -fsSL -o "$tmp/uv.tar.gz" "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-unknown-linux-gnu.tar.gz"
    sha256_ok "$tmp/uv.tar.gz" "$UV_SHA256" || die "uv download does not match its SHA-256"
    tar -xzf "$tmp/uv.tar.gz" -C "$tmp"
    mkdir -p "$ISOCHRON_WORK/bin"
    install -m 0755 "$tmp/uv-x86_64-unknown-linux-gnu/uv" "$tmp/uv-x86_64-unknown-linux-gnu/uvx" "$ISOCHRON_WORK/bin/"
    rm -rf "$tmp"
    log "installed $(uv --version)"
}

build_espeak() {
    local prefix=$ISOCHRON_WORK/espeak-ng-$ESPEAK_VERSION tools=$ISOCHRON_WORK/buildtools tmp
    if [ -x "$prefix/bin/espeak-ng" ] && "$prefix/bin/espeak-ng" --version | grep -q "$ESPEAK_VERSION"; then
        log "espeak-ng $ESPEAK_VERSION already installed"
        return
    fi
    command -v cc > /dev/null || command -v gcc > /dev/null || die "no C compiler on this node (is there a gcc module to load?)"
    tmp=$(mktemp -d "$ISOCHRON_WORK/tmp.XXXXXX")
    curl -fsSL -o "$tmp/espeak.tar.gz" "$ESPEAK_URL"
    sha256_ok "$tmp/espeak.tar.gz" "$ESPEAK_SHA256" || die "eSpeak NG source does not match its SHA-256"
    curl -fsSL -o "$tmp/sonic.tar.gz" "$SONIC_URL"
    sha256_ok "$tmp/sonic.tar.gz" "$SONIC_SHA256" || die "sonic source does not match its SHA-256"
    mkdir "$tmp/espeak" "$tmp/sonic"
    tar -xzf "$tmp/espeak.tar.gz" -C "$tmp/espeak" --strip-components=1
    tar -xzf "$tmp/sonic.tar.gz" -C "$tmp/sonic" --strip-components=1
    [ -x "$tools/bin/python" ] || uv venv --python "$PYTHON_VERSION" "$tools"
    uv pip install --python "$tools/bin/python" "cmake==$CMAKE_VERSION" "ninja==$NINJA_VERSION"
    "$tools/bin/cmake" -S "$tmp/espeak" -B "$tmp/build" -G Ninja -DCMAKE_MAKE_PROGRAM="$tools/bin/ninja" \
        -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$prefix" -DBUILD_SHARED_LIBS=OFF \
        -DUSE_MBROLA=OFF -DUSE_LIBPCAUDIO=OFF -DUSE_ASYNC=OFF -DBUILD_TESTING=OFF \
        -DFETCHCONTENT_FULLY_DISCONNECTED=ON "-DFETCHCONTENT_SOURCE_DIR_SONIC-GIT=$tmp/sonic"
    "$tools/bin/cmake" --build "$tmp/build" -j "${SLURM_CPUS_PER_TASK:-4}"
    "$tools/bin/cmake" --install "$tmp/build"
    rm -rf "$tmp"
    log "installed $("$prefix/bin/espeak-ng" --version)"
}

setup_env() {
    install_uv
    uv python install "$PYTHON_VERSION"
    cd "$REPO"
    uv sync --frozen --python "$PYTHON_VERSION"
    .venv/bin/python -c 'import torch; print("torch", torch.__version__, "CUDA", torch.version.cuda, "GPU", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none")'
    .venv/bin/python -c 'import torch; assert torch.cuda.is_available(), "torch sees no GPU"'
    build_espeak
    require_espeak
    mkdir -p "$REPO/hpc/logs" "$REPO/results/raw/logs"
    log "running the tests (the NLI tests are skipped until hpc/download_models.sh has run)"
    uv run --no-sync python -m pytest -q
}

setup_container() {
    command -v enroot > /dev/null || die "enroot is not available on this node"
    if [ -f "$VLLM_SQSH" ]; then
        log "container already imported: $VLLM_SQSH"
        return
    fi
    mkdir -p "$(dirname "$VLLM_SQSH")"
    enroot import -o "$VLLM_SQSH" "docker://$VLLM_IMAGE"
    log "imported $VLLM_IMAGE into $VLLM_SQSH"
}

setup_fallback() {
    install_uv
    uv python install "$PYTHON_VERSION"
    [ -x "$HF_VENV/bin/python" ] || uv venv --python "$PYTHON_VERSION" "$HF_VENV"
    uv pip install --python "$HF_VENV/bin/python" "torch==$HF_FALLBACK_TORCH" "$HF_FALLBACK_TRANSFORMERS" "accelerate>=1.0"
    "$HF_VENV/bin/python" -c 'import torch, transformers; from transformers import AutoModelForMultimodalLM, AutoProcessor; print("transformers", transformers.__version__, "torch", torch.__version__, "GPU", torch.cuda.is_available())'
}

require_compute_node
require_gpu
mkdir -p "$ISOCHRON_WORK"
case ${1:-env} in
    env) setup_env ;;
    container) setup_container ;;
    fallback) setup_fallback ;;
    *) die "unknown step ${1}: env, container or fallback" ;;
esac
log "done: setup ${1:-env}"
