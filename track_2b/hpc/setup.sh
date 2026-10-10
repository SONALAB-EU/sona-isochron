#!/bin/bash
# Set up the cluster side:
#
#   bash hpc/setup.sh prefetch    every download and build that needs no GPU: uv (pinned), the
#                                 uv-managed Python, the project environment from uv.lock (torch from
#                                 PyPI) and eSpeak NG 1.52.0 built from source. The cluster's internet
#                                 is slow per connection, so run this as a CPU-only batch job.
#   bash hpc/setup.sh container   import the vLLM container for Apertus 1.5 into a squashfs file
#                                 (also CPU-only; it resumes from enroot's layer cache)
#   bash hpc/setup.sh             on an H100 (through srun, so the architecture matches): whatever
#                                 prefetch has not done yet, then the GPU check and the tests
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
    fetch_chunked "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-unknown-linux-gnu.tar.gz" \
        "$UV_SIZE" "$UV_SHA256" "$tmp/uv.tar.gz" 4 6 || die "uv could not be downloaded"
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
    command -v cc > /dev/null || command -v gcc > /dev/null || die "no C compiler on this node"
    tmp=$(mktemp -d "${TMPDIR:-$ISOCHRON_WORK}/espeak-build.XXXXXX")
    fetch_chunked "$ESPEAK_URL" "$ESPEAK_SIZE" "$ESPEAK_SHA256" "$tmp/espeak.tar.gz" 4 6 || die "eSpeak NG source could not be downloaded"
    fetch_chunked "$SONIC_URL" "$SONIC_SIZE" "$SONIC_SHA256" "$tmp/sonic.tar.gz" 4 6 || die "sonic source could not be downloaded"
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

# uv downloads each wheel over one connection and starts it again from zero after a stall; on this
# cluster the large CUDA wheels then never arrive. So the locked Linux wheels over 20 MB are fetched with
# fetch_chunked (checked against uv.lock's hashes), installed from those files, and the rest of the
# lock is installed with uv pip from `uv export` (hash-checked). Versions and hashes are uv.lock's.
fetch_wheels() {
    local py url size sha name
    py=$(uv python find "$PYTHON_VERSION")
    mkdir -p "$WHEELS"
    while read -r url size sha name; do
        [ -f "$WHEELS/$name" ] && continue
        log "fetching $name ($((size / 1000000)) MB)"
        fetch_chunked "$url" "$size" "$sha" "$WHEELS/$name" 16 24 || die "$name could not be fetched"
    done < <("$py" - "$REPO/uv.lock" <<'PY'
import re, sys, tomllib

lock = tomllib.load(open(sys.argv[1], "rb"))
for pkg in lock["package"]:
    for w in pkg.get("wheels", []):
        name = w["url"].rsplit("/", 1)[1]
        if ("manylinux" in name and "x86_64" in name and w.get("size", 0) > 20_000_000
                and re.search(r"-(cp311|py3|py2\.py3)-(cp311|none|abi3)-", name)):
            print(w["url"], w["size"], w["hash"].split(":", 1)[1], name)
PY
)
}

install_env() {
    cd "$REPO"
    [ -x .venv/bin/python ] || uv venv --python "$PYTHON_VERSION" .venv
    uv export --frozen --format requirements-txt --no-emit-project --quiet --output-file "$ISOCHRON_WORK/requirements.txt"
    uv pip install --python .venv/bin/python --no-deps "$WHEELS"/*.whl
    uv pip install --python .venv/bin/python -r "$ISOCHRON_WORK/requirements.txt"
    uv pip install --python .venv/bin/python --no-deps -e .
}

prefetch() {
    install_uv
    uv python install "$PYTHON_VERSION"
    fetch_wheels
    install_env
    build_espeak
    require_espeak
    mkdir -p "$REPO/hpc/logs" "$REPO/results/raw/logs"
    touch "$ISOCHRON_WORK/.env-ready"
    log "environment ready (marker $ISOCHRON_WORK/.env-ready, which the model download waits for)"
}

setup_env() {
    prefetch
    require_gpu
    .venv/bin/python -c 'import torch; print("torch", torch.__version__, "CUDA", torch.version.cuda, "GPU", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none")'
    .venv/bin/python -c 'import torch; assert torch.cuda.is_available(), "torch sees no GPU"'
    log "running the tests (the NLI tests are skipped until hpc/download_models.sh has run)"
    uv run --no-sync python -m pytest -q
}

# ghcr.io throttles each connection (about 1 MB/s here), and a stalled layer makes enroot start that layer
# again from zero. So the image's blobs are fetched first with fetch_chunked (hpc/lib.sh) into enroot's
# cache, each checked against its digest; enroot import then finds every layer cached.
fetch_layers() {
    local registry=${VLLM_IMAGE%%#*} rest=${VLLM_IMAGE#*#} image tag cache tok manifest hex size
    image=${rest%:*}
    tag=${rest##*:}
    if [ "$registry" != ghcr.io ]; then
        log "the chunked fetch knows only ghcr.io; enroot downloads $VLLM_IMAGE itself"
        return 0
    fi
    cache=${ENROOT_CACHE_PATH:-${XDG_CACHE_HOME:-$HOME/.cache}/enroot}
    mkdir -p "$cache"
    tok=$(with_retries 10 ghcr_token "$image") || die "no token from ghcr.io"
    manifest=$(with_retries 10 curl -fsS --connect-timeout 30 --max-time 120 -H "Authorization: Bearer $tok" \
        -H "Accept: application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json" \
        "https://ghcr.io/v2/$image/manifests/$tag") || die "no manifest from ghcr.io"
    while read -r hex size; do
        [ -f "$cache/$hex" ] && continue
        find "$cache" -maxdepth 1 -name "$hex.??????????" -type f -delete
        log "fetching blob ${hex:0:12} ($((size / 1000000)) MB)"
        fetch_chunked "https://ghcr.io/v2/$image/blobs/sha256:$hex" "$size" "$hex" "$cache/$hex" 32 24 "$image" ||
            die "blob ${hex:0:12} could not be fetched"
        chmod 0640 "$cache/$hex"
    done < <(python3 -c 'import json, sys
m = json.load(sys.stdin)
for b in [m["config"], *m["layers"]]:
    print(b["digest"].split(":", 1)[1], b["size"])' <<< "$manifest")
    log "every blob of $VLLM_IMAGE is in $cache"
}

setup_container() {
    command -v enroot > /dev/null || die "enroot is not available on this node"
    if [ -f "$VLLM_SQSH" ]; then
        log "container already imported: $VLLM_SQSH"
        return
    fi
    fetch_layers
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
mkdir -p "$ISOCHRON_WORK"
case ${1:-env} in
    env) setup_env ;;
    prefetch) prefetch ;;
    container) setup_container ;;
    fallback) require_gpu && setup_fallback ;;
    *) die "unknown step ${1}: env, prefetch, container or fallback" ;;
esac
log "done: setup ${1:-env}"
