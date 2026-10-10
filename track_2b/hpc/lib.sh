# Functions shared by the HPC scripts; they source this file after env.sh.

die() {
    echo "ERROR: $*" >&2
    exit 1
}

log() {
    echo "[$(date -u +%H:%M:%S)] $*"
}

require_compute_node() {
    [ -n "${SLURM_JOB_ID:-}" ] || die "run this on a compute node (srun or sbatch), never on the login node"
    [ "$(uname -m)" = x86_64 ] || die "this node is $(uname -m), not x86_64 (avoid ga03)"
}

require_gpu() {
    command -v nvidia-smi > /dev/null || die "no nvidia-smi: no GPU on this node"
    nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv,noheader
}

require_espeak() {
    command -v espeak-ng > /dev/null || die "espeak-ng not found: run  bash hpc/setup.sh  first"
    espeak-ng --version | grep -q "$ESPEAK_VERSION" || die "espeak-ng is not $ESPEAK_VERSION: $(espeak-ng --version)"
}

# The cluster's internet is slow per connection, and connections stall for minutes. fetch_chunked
# URL SIZE SHA256 DEST CHUNK_MB PARALLEL [GHCR_IMAGE] fetches a file in ranged chunks, PARALLEL at once.
# A chunk that fails or stalls (under 20 kB/s for 60 s) is tried again on its own, up to 40 times;
# finished chunks survive a restart (DEST.parts/). DEST appears only once the whole file matches its
# SHA-256. With GHCR_IMAGE, every try asks ghcr.io for an anonymous pull token.
# with_retries N COMMAND...: run COMMAND until it succeeds, at most N times, 10 s apart
with_retries() {
    local n=$1 i
    shift
    for ((i = 1; i <= n; i++)); do
        "$@" && return 0
        sleep 10
    done
    return 1
}

ghcr_token() {
    curl -fsS --max-time 60 "https://ghcr.io/token?scope=repository:$1:pull" | sed -E 's/.*"token":"([^"]+)".*/\1/'
}

fetch_range() {
    local url=$1 start=$2 end=$3 part=$4 image=$5 auth
    [ -f "$part" ] && [ "$(stat -c %s "$part")" -eq $((end - start + 1)) ] && return 0
    for _ in $(seq 1 40); do
        auth=()
        [ -z "$image" ] || auth=(-H "Authorization: Bearer $(ghcr_token "$image")")
        if curl -fsSL --connect-timeout 20 --speed-limit 20000 --speed-time 60 --max-time 1200 "${auth[@]}" \
            -r "$start-$end" -o "$part.tmp" "$url" && [ "$(stat -c %s "$part.tmp")" -eq $((end - start + 1)) ]; then
            mv "$part.tmp" "$part"
            return 0
        fi
        sleep 3
    done
    return 1
}
export -f ghcr_token fetch_range

fetch_chunked() {
    local url=$1 size=$2 sha=$3 dest=$4 chunk=$(($5 * 1024 * 1024)) parallel=$6 image=${7:-} parts n i s e code auth=()
    [ -f "$dest" ] && return 0
    # does the server serve byte ranges? Only a plain 200 says no; errors (403, timeouts) are tried again
    for _ in 1 2 3 4 5; do
        auth=()
        [ -z "$image" ] || auth=(-H "Authorization: Bearer $(ghcr_token "$image")")
        code=$(curl -sL --connect-timeout 20 --max-time 120 "${auth[@]}" -r 0-0 -o /dev/null -w '%{http_code}' "$url" || true)
        case $code in 206 | 200) break ;; esac
        sleep 5
    done
    if [ "$code" = 200 ]; then
        echo "note: $url ignores byte ranges; one stream instead" >&2
        chunk=$size
        parallel=1
    fi
    parts=$dest.parts
    mkdir -p "$parts"
    n=$(((size + chunk - 1) / chunk))
    # shellcheck disable=SC2016
    for ((i = 0; i < n; i++)); do
        s=$((i * chunk))
        e=$((s + chunk - 1 < size - 1 ? s + chunk - 1 : size - 1))
        printf '%s %s %s %s %s\n' "$url" "$s" "$e" "$parts/$(printf %06d "$i")" "${image:--}"
    done | xargs -P "$parallel" -n 5 bash -c 'fetch_range "$1" "$2" "$3" "$4" "${5#-}"' _ || return 1
    cat "$parts"/[0-9]* > "$dest.tmp"
    if [ "$(sha256sum "$dest.tmp" | cut -d' ' -f1)" != "$sha" ]; then
        rm -rf "$dest.tmp" "$parts"
        echo "ERROR: $dest does not match its SHA-256; its chunks were deleted" >&2
        return 1
    fi
    mv "$dest.tmp" "$dest"
    rm -rf "$parts"
}

free_port() {
    "$REPO/.venv/bin/python" -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])'
}

random_key() {
    head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n'
}

# start_server KIND MODEL_DIR SERVED_NAME PORT KEY LOG [extra vLLM arguments...]
# KIND is vllm (the container, through pyxis), transformers (hpc/hf_server.py in $HF_VENV)
# or llamacpp (llama-server with a GGUF file as MODEL_DIR; for testing this script on a laptop).
# Sets SERVER_PID. The server listens on 127.0.0.1 only and needs KEY as its API key.
start_server() {
    local kind=$1 model=$2 name=$3 port=$4 key=$5 logfile=$6
    shift 6
    case $kind in
        vllm)
            [ -f "$VLLM_SQSH" ] || die "no container at $VLLM_SQSH: run  bash hpc/setup.sh container"
            local mounts="$MODELS:$MODELS:ro"
            [ "$MODELS_70B" = "$MODELS" ] || mounts="$mounts,$MODELS_70B:$MODELS_70B:ro"
            VLLM_API_KEY=$key HF_HUB_OFFLINE=1 srun --overlap --ntasks=1 --nodes=1 \
                --container-image="$VLLM_SQSH" --container-name="$VLLM_CONTAINER" \
                --container-mounts="$mounts" \
                --container-env=VLLM_API_KEY,HF_HUB_OFFLINE \
                vllm serve "$model" --served-model-name "$name" --host 127.0.0.1 --port "$port" \
                --dtype bfloat16 --generation-config vllm --seed 0 "$@" > "$logfile" 2>&1 &
            ;;
        transformers)
            [ -x "$HF_VENV/bin/python" ] || die "no fallback environment: run  bash hpc/setup.sh fallback"
            ISOCHRON_SERVER_KEY=$key HF_HUB_OFFLINE=1 "$HF_VENV/bin/python" "$REPO/hpc/hf_server.py" \
                --model "$model" --served-model-name "$name" --host 127.0.0.1 --port "$port" "$@" > "$logfile" 2>&1 &
            ;;
        llamacpp)
            LLAMA_API_KEY=$key llama-server -m "$model" --alias "$name" --host 127.0.0.1 --port "$port" \
                -c 8192 -np 1 -ngl all --reasoning off > "$logfile" 2>&1 &
            ;;
        *)
            die "unknown server kind $kind (vllm, transformers or llamacpp)"
            ;;
    esac
    SERVER_PID=$!
    log "started $kind server for $name on port $port (pid $SERVER_PID, log $logfile)"
}

# wait_healthy PORT TIMEOUT_S LOG: until /health answers 200; fails if the server process dies
wait_healthy() {
    local port=$1 timeout=$2 logfile=$3 waited=0
    until [ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port/health")" = 200 ]; do
        if ! kill -0 "$SERVER_PID" 2> /dev/null; then
            tail -n 40 "$logfile" >&2
            die "the server exited before it was healthy (log: $logfile)"
        fi
        [ "$waited" -lt "$timeout" ] || die "the server was not healthy after $timeout s (log: $logfile)"
        sleep 10
        waited=$((waited + 10))
    done
    log "server on port $port healthy after about $waited s"
}

stop_server() {
    [ -n "${SERVER_PID:-}" ] || return 0
    if kill -0 "$SERVER_PID" 2> /dev/null; then
        kill -TERM "$SERVER_PID" 2> /dev/null || true
        for _ in $(seq 1 60); do
            kill -0 "$SERVER_PID" 2> /dev/null || break
            sleep 2
        done
        kill -KILL "$SERVER_PID" 2> /dev/null || true
    fi
    wait "$SERVER_PID" 2> /dev/null || true
    log "server stopped (pid $SERVER_PID)"
    SERVER_PID=
}
