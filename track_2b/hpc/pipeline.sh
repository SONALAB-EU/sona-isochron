#!/bin/bash
# One cluster job, run by hpc/run.sbatch (8B) and hpc/run_70b.sbatch (70B):
#   1. Apertus 1.5 in BF16 behind an OpenAI-compatible server on 127.0.0.1 (vLLM container, or the
#      transformers fallback); step 2 with prompt v1 and the repair loop against it; server stopped.
#   2. The judge Qwen3-14B (BF16) behind its own server: validation on both control suites, then
#      the same outputs, for evaluation only; server stopped.
#   3. Reports in results/.
# A job that hits its time limit can be submitted again: generation resumes from items.jsonl and
# the judge from its cache. The two servers never run at the same time.
#
# Settings (environment variables; the sbatch files set the first ones):
#   MODEL_KEY   8b or 70b
#   TP          tensor-parallel GPUs for Apertus (vLLM)            default 1
#   GPU_UTIL    vLLM --gpu-memory-utilization for Apertus           default 0.6
#   VLLM_EXTRA  more vLLM arguments for Apertus                     default none
#   SERVER      vllm or transformers                                default vllm
#   LANGS       target languages                                    default de
#   SPLIT       dev or test                                         default test
#   LEVELS      target levels in %                                  default 90 80 70 60
#   SEEDS       item seeds                                          default 0 1 2
#   WORKERS     items (and judge items) in flight at once           default 16
#   NLI_DEVICE  device of the loop's NLI                            default cuda
#   JUDGE_SEED_CACHE  a judge cache to start from, so two jobs share the same fact lists
#   PHASES      which steps run: generate, validate (judge on the control suites), judge (judge the
#               runs), report                                       default all four
#   IDS         FLEURS sentence ids to run (smoke tests)            default all sentences
#   RUN_SUFFIX  appended to the run names                           default none
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/env.sh"
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

case ${MODEL_KEY:?set MODEL_KEY to 8b or 70b} in
    8b) MODEL_DIR=$MODELS/$APERTUS_8B_REPO ;;
    70b) MODEL_DIR=$MODELS_70B/$APERTUS_70B_REPO ;;
    *) die "MODEL_KEY must be 8b or 70b" ;;
esac
SERVER=${SERVER:-vllm}
TP=${TP:-1}
GPU_UTIL=${GPU_UTIL:-0.6}
VLLM_EXTRA=${VLLM_EXTRA:-}
LANGS=${LANGS:-de}
SPLIT=${SPLIT:-test}
LEVELS=${LEVELS:-90 80 70 60}
SEEDS=${SEEDS:-0 1 2}
WORKERS=${WORKERS:-16}
NLI_DEVICE=${NLI_DEVICE:-cuda}
JUDGE_SEED_CACHE=${JUDGE_SEED_CACHE:-}
PHASES=${PHASES:-generate validate judge report}
IDS=${IDS:-}
RUN_SUFFIX=${RUN_SUFFIX:-}

has_phase() {
    case " $PHASES " in *" $1 "*) return 0 ;; esac
    return 1
}

require_compute_node
require_gpu
require_espeak
cd "$REPO"
[ -x .venv/bin/python ] || die "no project environment: run  bash hpc/setup.sh  first"
if has_phase generate; then
    [ -f "$MODEL_DIR/config.json" ] || die "no model at $MODEL_DIR: run  bash hpc/download_models.sh"
fi
if has_phase validate || has_phase judge; then
    [ -f "$MODELS/$JUDGE_REPO/config.json" ] || die "no judge model at $MODELS/$JUDGE_REPO: run  bash hpc/download_models.sh"
fi
export HF_HUB_OFFLINE=1
mkdir -p results/raw/logs
TAG=hpc_${MODEL_KEY}
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
trap stop_server EXIT
trap 'exit 143' TERM
log "job ${SLURM_JOB_ID}: phases $PHASES; $MODEL_DIR with $SERVER, languages $LANGS, split $SPLIT${IDS:+ (ids $IDS)}, levels $LEVELS, seeds $SEEDS"
[ "$SERVER" = transformers ] && WORKERS=2
runs=()
for lang in $LANGS; do
    runs+=("results/raw/${TAG}_step2_${lang}_${SPLIT}${RUN_SUFFIX}")
done

# 1. Generation
gen_port=
if has_phase generate; then
    apertus_name=apertus-v1.5-${MODEL_KEY}-bf16
    gen_port=$(free_port)
    gen_key=$(random_key)
    gen_log=results/raw/logs/server-${TAG}-apertus-${STAMP}.log
    if [ "$SERVER" = vllm ]; then
        # shellcheck disable=SC2086
        start_server vllm "$MODEL_DIR" "$apertus_name" "$gen_port" "$gen_key" "$gen_log" \
            --chat-template-content-format string --tensor-parallel-size "$TP" \
            --gpu-memory-utilization "$GPU_UTIL" --max-model-len 8192 $VLLM_EXTRA
    else
        start_server transformers "$MODEL_DIR" "$apertus_name" "$gen_port" "$gen_key" "$gen_log" --kind multimodal
    fi
    wait_healthy "$gen_port" 3600 "$gen_log"
    export LLM_NAME=$apertus_name LLM_BASE_URL=http://127.0.0.1:$gen_port/v1 LLM_API_KEY=$gen_key
    for run in "${runs[@]}"; do
        lang=${run#results/raw/"${TAG}"_step2_}
        lang=${lang%%_*}
        # shellcheck disable=SC2086
        uv run --no-sync python -m isochron.loop_run --variant v1 --lang "$lang" --split "$SPLIT" --allow-test \
            ${IDS:+--ids $IDS} --levels $LEVELS --seeds $SEEDS --quantisation BF16 --workers "$WORKERS" \
            --device "$NLI_DEVICE" --out "$run" --resume
    done
    stop_server
fi

# 2. Judge (evaluation only)
if has_phase validate || has_phase judge; then
    judge_port=$(free_port)
    while [ "$judge_port" = "$gen_port" ]; do judge_port=$(free_port); done
    judge_key=$(random_key)
    judge_log=results/raw/logs/server-${TAG}-judge-${STAMP}.log
    export ISOCHRON_JUDGE_CACHE=results/raw/judge_cache_${TAG}.jsonl
    if [ ! -f "$ISOCHRON_JUDGE_CACHE" ] && [ -n "$JUDGE_SEED_CACHE" ] && [ -f "$JUDGE_SEED_CACHE" ]; then
        cp "$JUDGE_SEED_CACHE" "$ISOCHRON_JUDGE_CACHE"
        log "judge cache started from $JUDGE_SEED_CACHE, so both jobs use the same fact lists"
    fi
    if [ "$SERVER" = vllm ]; then
        start_server vllm "$MODELS/$JUDGE_REPO" qwen3-14b-bf16 "$judge_port" "$judge_key" "$judge_log" \
            --tensor-parallel-size 1 --gpu-memory-utilization 0.85 --max-model-len 8192
    else
        start_server transformers "$MODELS/$JUDGE_REPO" qwen3-14b-bf16 "$judge_port" "$judge_key" "$judge_log" --kind causal
    fi
    wait_healthy "$judge_port" 3600 "$judge_log"
    export JUDGE_NAME=qwen3-14b-bf16 JUDGE_BASE_URL=http://127.0.0.1:$judge_port/v1 JUDGE_API_KEY=$judge_key
    judge=(uv run --no-sync python -m isochron.judge)
    if has_phase validate; then
        for suite in hard nli; do
            "${judge[@]}" controls --suite "$suite" --compare-prompt perfact_v3 --quantisation BF16 --workers "$WORKERS" \
                --out "results/judge_validation_${suite}_v3_qwen3-14b_${TAG}.md"
        done
    fi
    if has_phase judge; then
        "${judge[@]}" runs "${runs[@]}" --compare-prompt perfact_v3 --quantisation BF16 --workers "$WORKERS"
    fi
    stop_server
fi

# 3. Reports
if has_phase report; then
    for run in "${runs[@]}"; do
        name=${run##*/}
        uv run --no-sync python -m isochron.pilot_report "$run" --out "results/${name}.md" \
            --title "Step 2 (${name}): prompt v1 with and without the repair loop, Apertus 1.5 ${MODEL_KEY} BF16, judge Qwen3-14B" \
            > /dev/null
        log "wrote results/${name}.md"
    done
fi
log "done: phases $PHASES"
