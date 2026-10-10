#!/bin/bash
# Insurance in case the HPC setup fails: step 2 on the German test split with the current local
# setup (llama.cpp on Apple Silicon: Apertus 1.5 8B Q4_K_M, judge Qwen3-8B Q4_K_M), levels 90 and 80,
# seed 0, prompt v1 with the repair loop (both conditions come from the same run).
#
#   bash scripts/local_step2_de_test.sh              generate, judge, report
#   bash scripts/local_step2_de_test.sh generate     one phase only: generate, judge or report
#
# Resumable: run it again and it continues where it stopped (items.jsonl and the judge cache).
# It starts and stops the two llama-servers itself, never both at once, on the host and port of
# LLM_BASE_URL and JUDGE_BASE_URL in .env, with the aliases LLM_NAME and JUDGE_NAME, and logs them
# to results/raw/logs/. The GGUF files are those of docs/local_llm.md, or APERTUS_GGUF and JUDGE_GGUF.
# Estimated duration on the Apple M3 (16 GB): about 3 h to generate and 2 h to judge (docs/hpc.md).
#
# To check the script itself without touching the test split:
#   SPLIT=dev LIMIT=1 RUN=results/raw/check_local_script REPORT=/tmp/check.md bash scripts/local_step2_de_test.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[ -f .env ] || { echo "no .env (see docs/local_llm.md)" >&2; exit 1; }
set -a
. ./.env
set +a
APERTUS_GGUF=${APERTUS_GGUF:-$HOME/models/apertus-v1.5-8b-text-Q4_K_M-GGUF/apertus-v1.5-8b-text-q4_k_m.gguf}
JUDGE_GGUF=${JUDGE_GGUF:-$HOME/models/Qwen3-8B-GGUF/Qwen3-8B-Q4_K_M.gguf}
SPLIT=${SPLIT:-test}
RUN=${RUN:-results/raw/local_step2_de_${SPLIT}_v1loop}
REPORT=${REPORT:-results/local_step2_de_${SPLIT}.md}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
SERVER_PID=
mkdir -p results/raw/logs

say() {
    echo "[$(date +%H:%M:%S)] $*"
}

host_port() {
    [[ $1 =~ ^https?://([^/:]+):([0-9]+) ]] || { echo "cannot read host and port from $1" >&2; exit 1; }
    echo "${BASH_REMATCH[1]} ${BASH_REMATCH[2]}"
}

answers() {
    curl -s -o /dev/null --max-time 3 "http://$1:$2/health"
}

start_server() {
    local gguf=$1 alias=$2 host=$3 port=$4 logfile=$5
    [ -f "$gguf" ] || { echo "no model file $gguf" >&2; exit 1; }
    llama-server -m "$gguf" --alias "$alias" --host "$host" --port "$port" -c 8192 -np 1 -ngl all --reasoning off \
        > "$logfile" 2>&1 &
    SERVER_PID=$!
    for _ in $(seq 1 150); do
        [ "$(curl -s -o /dev/null -w '%{http_code}' "http://$host:$port/health")" = 200 ] && { say "$alias up on $host:$port (log $logfile)"; return; }
        kill -0 "$SERVER_PID" 2> /dev/null || { tail -n 20 "$logfile" >&2; echo "llama-server exited" >&2; exit 1; }
        sleep 2
    done
    echo "llama-server not healthy after 300 s (log $logfile)" >&2
    exit 1
}

stop_server() {
    [ -n "$SERVER_PID" ] || return 0
    kill -TERM "$SERVER_PID" 2> /dev/null || true
    wait "$SERVER_PID" 2> /dev/null || true
    say "server stopped"
    SERVER_PID=
}
trap stop_server EXIT

generate() {
    local host port limit=() pick=()
    read -r host port < <(host_port "$JUDGE_BASE_URL")
    ! answers "$host" "$port" || { echo "something answers on the judge's $host:$port: stop it first" >&2; exit 1; }
    read -r host port < <(host_port "$LLM_BASE_URL")
    ! answers "$host" "$port" || { echo "something already answers on $host:$port: stop it first" >&2; exit 1; }
    start_server "$APERTUS_GGUF" "$LLM_NAME" "$host" "$port" "results/raw/logs/llama-server-apertus-$port-$STAMP.log"
    [ -z "${LIMIT:-}" ] || limit=(--limit "$LIMIT")
    [ "$SPLIT" = test ] && pick=(--allow-test) || pick=(--exclude-gonogo)
    uv run --no-sync python -m isochron.loop_run --variant v1 --lang de --split "$SPLIT" "${pick[@]}" ${limit[@]+"${limit[@]}"} \
        --levels 90 80 --seeds 0 --quantisation Q4_K_M --workers 1 --out "$RUN" --resume
    stop_server
}

judge() {
    local host port
    read -r host port < <(host_port "$LLM_BASE_URL")
    ! answers "$host" "$port" || { echo "Apertus still answers on $host:$port: stop it first" >&2; exit 1; }
    read -r host port < <(host_port "$JUDGE_BASE_URL")
    ! answers "$host" "$port" || { echo "something already answers on $host:$port: stop it first" >&2; exit 1; }
    start_server "$JUDGE_GGUF" "$JUDGE_NAME" "$host" "$port" "results/raw/logs/llama-server-judge-$port-$STAMP.log"
    uv run --no-sync python -m isochron.judge runs "$RUN" --compare-prompt perfact_v3
    stop_server
}

report() {
    uv run --no-sync python -m isochron.pilot_report "$RUN" --out "$REPORT" \
        --title "Step 2 (German $SPLIT, local run): prompt v1 with and without the repair loop, Apertus 1.5 8B Q4_K_M, judge Qwen3-8B" \
        > /dev/null
    say "wrote $REPORT"
}

case ${1:-all} in
    generate) generate ;;
    judge) judge ;;
    report) report ;;
    all) generate && judge && report ;;
    *) echo "usage: bash scripts/local_step2_de_test.sh [generate|judge|report]" >&2; exit 1 ;;
esac
