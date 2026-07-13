#!/usr/bin/env bash
set -euo pipefail

IMAGE="${IMAGE:-vllm/vllm-openai:latest}"
HOST_MODEL_PATH="${HOST_MODEL_PATH:-/home/user/models/Qwen2.5-Coder-32B-Instruct}"
CONTAINER_MODEL_PATH="${CONTAINER_MODEL_PATH:-/models/Qwen2.5-Coder-32B-Instruct}"
SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-qwen2.5-coder-32b}"
API_KEY="${API_KEY:-token-abc123}"
PORT="${PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
CONTAINER_NAME="${CONTAINER_NAME:-vllm-qwen25-coder-32b-tp8}"
DOCKER_ARGS="${DOCKER_ARGS:-}"

if [[ ! -d "${HOST_MODEL_PATH}" ]]; then
  echo "Model path does not exist: ${HOST_MODEL_PATH}" >&2
  exit 1
fi

docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

docker run --rm \
  --name "${CONTAINER_NAME}" \
  --gpus all \
  --ipc=host \
  --network host \
  -v "${HOST_MODEL_PATH}:${CONTAINER_MODEL_PATH}:ro" \
  ${DOCKER_ARGS} \
  "${IMAGE}" \
  --model "${CONTAINER_MODEL_PATH}" \
  --api-key "${API_KEY}" \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --served-model-name "${SERVED_MODEL_NAME}" \
  --tensor-parallel-size 8 \
  --dtype bfloat16 \
  --max-model-len "${MAX_MODEL_LEN}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}" \
  --trust-remote-code
