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

sha256_ok() {
    [ "$(sha256sum "$1" | cut -d' ' -f1)" = "$2" ]
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
                --container-image="$VLLM_SQSH" \
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
