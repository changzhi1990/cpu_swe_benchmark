#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT_DIR}/src:${PYTHONPATH:-}"

python3 "${ROOT_DIR}/benchmark_latency.py" \
  --base-url "${BASE_URL:-http://localhost:8000/v1}" \
  --api-key "${API_KEY:-token-abc123}" \
  --model-path "${MODEL_NAME:-qwen2.5-coder-32b}" \
  --vllm-topology tp8 \
  --benchmark-type sorting \
  --concurrency-levels "${CONCURRENCY_LEVELS:-1,2,4,8,16,32,64,128}" \
  --task-timeout "${TASK_TIMEOUT:-600}" \
  --command-timeout "${COMMAND_TIMEOUT:-120}" \
  --cpu-threads-per-worker "${CPU_THREADS_PER_WORKER:-1}" \
  --mini-swe-agent-src "${MINI_SWE_AGENT_SRC:-/home/user/zhi/mini-swe-agent-latest/src}" \
  --output-dir "${OUTPUT_DIR:-${ROOT_DIR}/results/qwen32b_tp8_sorting_quick}"
