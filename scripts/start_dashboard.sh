#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-80}"
PYTHON_BIN="${PYTHON_BIN:-}"

if [[ -z "${PYTHON_BIN}" && -x "/home/user/cpu_swe_runs/venv/bin/python" ]]; then
  PYTHON_BIN="/home/user/cpu_swe_runs/venv/bin/python"
fi
if [[ -z "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

cd "${ROOT_DIR}"
export PYTHONPATH="${ROOT_DIR}/src:${PYTHONPATH:-}"

exec "${PYTHON_BIN}" -m uvicorn cpu_swe_benchmark.dashboard:app   --host "${HOST}"   --port "${PORT}"
