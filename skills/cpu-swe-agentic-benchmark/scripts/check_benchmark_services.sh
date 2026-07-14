#!/usr/bin/env bash
set -uo pipefail

ROOT="${BENCH_ROOT:-/home/user/zhi/cpu_swe_benchmark}"
API_KEY="${API_KEY:-token-abc123}"
VLLM_URL="${VLLM_URL:-http://localhost:8000/v1}"
DASHBOARD_HEALTH="${DASHBOARD_HEALTH:-http://localhost:8080/api/health}"
PCM_PATH="${AMDUPROFPCM_PATH:-/home/user/zhi/AMDuProf_Nda_Linux_x64_5.0.1479/bin/AMDuProfPcm}"

printf 'root=%s
' "$ROOT"
printf 'benchmark_processes:
'
pgrep -af 'benchmark_latency.py|AMDuProfPcm' || true

printf 'vllm_container:
'
docker ps --format 'table {{.Names}}	{{.Image}}	{{.Status}}' | sed -n '1,10p' || true

printf 'ports:
'
ss -ltnp | grep -E ':(8000|8080)' || true

printf 'vllm_models:
'
if curl -sS -m 5 -H "Authorization: Bearer ${API_KEY}" "${VLLM_URL}/models"; then
  printf '
'
else
  printf 'vllm_unreachable
'
fi

printf 'dashboard_health:
'
if curl -sS -m 5 "${DASHBOARD_HEALTH}"; then
  printf '
'
else
  printf 'dashboard_unreachable
'
fi

printf 'amd_pcm_path=%s exists=%s
' "$PCM_PATH" "$([[ -x "$PCM_PATH" ]] && echo yes || echo no)"
printf 'amd_pcm_sudo_env=%s
' "$([[ -n "${AMDUPROFPCM_SUDO_PASSWORD:-}" ]] && echo set || echo missing)"
