#!/usr/bin/env bash
set -uo pipefail

ROOT="${BENCH_ROOT:-/home/user/zhi/cpu_swe_benchmark}"
API_KEY="${API_KEY:-token-abc123}"
VLLM_URL="${VLLM_URL:-${BASE_URL:-http://localhost:8000/v1}}"
DASHBOARD_HEALTH="${DASHBOARD_HEALTH:-http://localhost:8080/api/health}"
PCM_PATH="${AMDUPROFPCM_PATH:-/home/user/zhi/AMDuProf_Nda_Linux_x64_5.0.1479/bin/AMDuProfPcm}"

printf 'server_profile:\n'
printf '  host=%s\n' "$(hostname 2>/dev/null || echo unknown)"
printf '  user=%s\n' "$(whoami 2>/dev/null || echo unknown)"
printf '  root=%s\n' "$ROOT"
printf '  vllm_url=%s\n' "$VLLM_URL"
printf '  dashboard_health=%s\n' "$DASHBOARD_HEALTH"
printf '  amd_pcm_path=%s\n' "$PCM_PATH"

printf 'gpu_inventory:\n'
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv,noheader,nounits 2>/dev/null || nvidia-smi -L || true
else
  printf '  nvidia-smi_not_found\n'
fi

printf 'cpu_summary:\n'
if command -v lscpu >/dev/null 2>&1; then
  lscpu | grep -E '^(CPU\(s\)|Model name|Socket\(s\)|Core\(s\) per socket|Thread\(s\) per core|NUMA node\(s\)):' || true
else
  printf '  lscpu_not_found\n'
fi

printf 'memory_summary:\n'
free -h 2>/dev/null || true

printf 'benchmark_processes:\n'
pgrep -af 'benchmark_latency.py|AMDuProfPcm' || true

printf 'containers:\n'
if command -v docker >/dev/null 2>&1; then
  docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | sed -n '1,20p' || true
else
  printf '  docker_not_found\n'
fi

printf 'listening_ports:\n'
ss -ltnp 2>/dev/null | grep -E ':(8000|8080)([[:space:]]|$)' || true

printf 'model_endpoint:\n'
if curl -sS -m 5 -H "Authorization: Bearer ${API_KEY}" "${VLLM_URL}/models"; then
  printf '\n'
else
  printf 'model_endpoint_unreachable\n'
fi

printf 'dashboard_health:\n'
if curl -sS -m 5 "${DASHBOARD_HEALTH}"; then
  printf '\n'
else
  printf 'dashboard_unreachable\n'
fi

printf 'amd_pcm_status:\n'
printf '  exists=%s\n' "$([[ -x "$PCM_PATH" ]] && echo yes || echo no)"
printf '  sudo_env=%s\n' "$([[ -n "${AMDUPROFPCM_SUDO_PASSWORD:-}" ]] && echo set || echo missing)"
