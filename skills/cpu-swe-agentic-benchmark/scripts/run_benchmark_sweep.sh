#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <algorithm_lab_sorting_bugfix|memory_lab_bandwidth_bugfix|all> <comma-separated-concurrency-levels>" >&2
  exit 2
fi

WORKLOAD="$1"
LEVELS="$2"
case "$WORKLOAD" in
  algorithm_lab_sorting_bugfix|memory_lab_bandwidth_bugfix|all) ;;
  *) echo "unknown benchmark type: ${WORKLOAD}" >&2; exit 2 ;;
esac

ROOT="${BENCH_ROOT:-/home/user/zhi/cpu_swe_benchmark}"
BASE_URL="${BASE_URL:-${VLLM_URL:-http://localhost:8000/v1}}"
API_KEY="${API_KEY:-token-abc123}"
MODEL="${MODEL:-qwen2.5-coder-32b}"
MINI_SWE_AGENT_SRC="${MINI_SWE_AGENT_SRC:-/home/user/zhi/mini-swe-agent-latest/src}"
VLLM_TOPOLOGY="${VLLM_TOPOLOGY:-tp8}"
RUN_LABEL="${RUN_LABEL:-qwen32b_tp8}"
TASK_TIMEOUT="${TASK_TIMEOUT:-600}"
COMMAND_TIMEOUT="${COMMAND_TIMEOUT:-120}"
CPU_THREADS_PER_WORKER="${CPU_THREADS_PER_WORKER:-1}"
MAX_TOKENS="${MAX_TOKENS:-512}"
TEMPERATURE="${TEMPERATURE:-0.0}"
RUN_TAG="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="${OUTPUT_DIR:-${ROOT}/results/${RUN_LABEL}_${WORKLOAD}_sweep_${RUN_TAG}}"
LOG="${LOG_PATH:-${ROOT}/logs/${RUN_LABEL}_${WORKLOAD}_sweep_${RUN_TAG}.log}"

cd "$ROOT"
mkdir -p "$(dirname "$OUT_DIR")" "$(dirname "$LOG")"

if pgrep -af 'benchmark_latency.py' >/dev/null; then
  echo "existing benchmark process detected; inspect before starting another run" >&2
  pgrep -af 'benchmark_latency.py' >&2
  exit 1
fi

cat <<EOF
benchmark_type=${WORKLOAD}
concurrency_levels=${LEVELS}
bench_root=${ROOT}
base_url=${BASE_URL}
model=${MODEL}
mini_swe_agent_src=${MINI_SWE_AGENT_SRC}
vllm_topology=${VLLM_TOPOLOGY}
run_label=${RUN_LABEL}
output_dir=${OUT_DIR}
log=${LOG}
EOF

python3 benchmark_latency.py \
  --base-url "$BASE_URL" \
  --api-key "$API_KEY" \
  --model-path "$MODEL" \
  --benchmark-type "$WORKLOAD" \
  --concurrency-levels "$LEVELS" \
  --mini-swe-agent-src "$MINI_SWE_AGENT_SRC" \
  --vllm-topology "$VLLM_TOPOLOGY" \
  --task-timeout "$TASK_TIMEOUT" \
  --command-timeout "$COMMAND_TIMEOUT" \
  --cpu-threads-per-worker "$CPU_THREADS_PER_WORKER" \
  --max-tokens "$MAX_TOKENS" \
  --temperature "$TEMPERATURE" \
  --output-dir "$OUT_DIR" \
  2>&1 | tee "$LOG"
