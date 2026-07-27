#!/usr/bin/env bash
set -uo pipefail

ROOT="${BENCH_ROOT:-/home/user/zhi/cpu_swe_benchmark}"
BENCH_USER="${BENCH_USER:-user}"
PHASE1_ID="${PHASE1_ID:-cpufreq_phase1_$(date +%Y%m%d_%H%M%S)}"
WORKLOAD="${WORKLOAD:-algorithm_lab_sorting_bugfix}"
BASE_URL="${BASE_URL:-http://localhost:8000/v1}"
VLLM_URL="${VLLM_URL:-$BASE_URL}"
MODEL="${MODEL:-qwen2.5-coder-32b}"
API_KEY="${API_KEY:-token-abc123}"
MINI_SWE_AGENT_SRC="${MINI_SWE_AGENT_SRC:-/home/user/zhi/mini-swe-agent-latest/src}"
AVT_CMD="${AVT_CMD:-/opt/AMD/AVT/AVTCMD}"

RUN_ROOT="${ROOT}/results/${PHASE1_ID}"
MANIFEST="${RUN_ROOT}/manifest.csv"
STATUS_FILE="${RUN_ROOT}/status.txt"
AGGREGATE_CSV="${RUN_ROOT}/aggregate_samples.csv"
CPU_FREQ_DIR="${ROOT}/logs/cpu_freq/${PHASE1_ID}"
SAMPLE_LOG_DIR="${ROOT}/logs/${PHASE1_ID}"
AVT_LOG="${SAMPLE_LOG_DIR}/avt_commands.log"

mkdir -p "${RUN_ROOT}" "${CPU_FREQ_DIR}" "${SAMPLE_LOG_DIR}"
chown -R "${BENCH_USER}:${BENCH_USER}" "${RUN_ROOT}" "${CPU_FREQ_DIR}" "${SAMPLE_LOG_DIR}" 2>/dev/null || true

if [[ ! -f "${MANIFEST}" ]]; then
  echo "phase1_id,run_id,fmax_mhz,concurrency,repeat,kind,status,started_at,ended_at,exit_code,run_dir,run_log,cpu_freq_log,avt_log" > "${MANIFEST}"
fi

write_status() {
  printf "%s\n" "$*" | tee "${STATUS_FILE}"
}

as_user() {
  runuser -u "${BENCH_USER}" -- bash -lc "$*"
}

check_services() {
  curl -sS -m 10 -H "Authorization: Bearer ${API_KEY}" "${BASE_URL}/models" >/dev/null || return 1
  curl -sS -m 10 "http://localhost:8080/api/health" >/dev/null || return 1
}

set_fmax() {
  local fmax="$1"
  echo "[$(date --iso-8601=seconds)] set_cclk_fmax(${fmax})" | tee -a "${AVT_LOG}"
  "${AVT_CMD}" -module pmm "set_cclk_fmax(${fmax})" 2>&1 | tee -a "${AVT_LOG}"
}

start_freq_logger() {
  local fmax="$1"
  local log_path="$2"
  as_user "python3 -u - <<'PY' > '${log_path}' 2>&1 &
import pathlib
import time

fmax = '${fmax}'
while True:
    count = 0
    total = 0.0
    min_mhz = None
    max_mhz = 0.0
    with open('/proc/cpuinfo', encoding='utf-8') as handle:
        for line in handle:
            if line.startswith('cpu MHz'):
                mhz = float(line.split(':', 1)[1])
                count += 1
                total += mhz
                min_mhz = mhz if min_mhz is None or mhz < min_mhz else min_mhz
                max_mhz = max(max_mhz, mhz)
    if count:
        print(
            f\"{time.time():.6f},fmax_mhz={fmax},avg_mhz={total / count:.2f},\"
            f\"min_mhz={min_mhz:.2f},max_mhz={max_mhz:.2f},cores={count}\",
            flush=True,
        )
    time.sleep(1)
PY
echo \$!"
}

stop_freq_logger() {
  local pid="$1"
  if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
    kill "${pid}" >/dev/null 2>&1 || true
    wait "${pid}" >/dev/null 2>&1 || true
  fi
}

append_manifest() {
  local run_id="$1"
  local fmax="$2"
  local concurrency="$3"
  local repeat="$4"
  local kind="$5"
  local status="$6"
  local started_at="$7"
  local ended_at="$8"
  local exit_code="$9"
  local run_dir="${10}"
  local run_log="${11}"
  local cpu_freq_log="${12}"
  printf "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" \
    "${PHASE1_ID}" "${run_id}" "${fmax}" "${concurrency}" "${repeat}" "${kind}" "${status}" \
    "${started_at}" "${ended_at}" "${exit_code}" "${run_dir}" "${run_log}" "${cpu_freq_log}" "${AVT_LOG}" >> "${MANIFEST}"
}

run_sample() {
  local fmax="$1"
  local concurrency="$2"
  local repeat="$3"
  local kind="$4"
  local run_id="9535_fmax${fmax}_c${concurrency}_r${repeat}_${PHASE1_ID}"
  local run_label="qwen32b_tp8_${run_id}"
  local run_dir="${ROOT}/results/${run_label}_${WORKLOAD}_sweep"
  local run_log="${ROOT}/logs/${run_label}_${WORKLOAD}_sweep.log"
  local cpu_freq_log="${CPU_FREQ_DIR}/${run_id}.csv"
  local sample_stdout="${SAMPLE_LOG_DIR}/${run_id}.runner.log"
  local started_at
  local ended_at
  local exit_code
  local status
  local freq_pid

  started_at="$(date --iso-8601=seconds)"
  write_status "running run_id=${run_id} fmax=${fmax} concurrency=${concurrency} repeat=${repeat} kind=${kind}"

  if pgrep -af '[b]enchmark_latency.py' >/dev/null; then
    ended_at="$(date --iso-8601=seconds)"
    append_manifest "${run_id}" "${fmax}" "${concurrency}" "${repeat}" "${kind}" "blocked_existing_benchmark" "${started_at}" "${ended_at}" "98" "${run_dir}" "${run_log}" "${cpu_freq_log}"
    return 98
  fi

  set_fmax "${fmax}" > >(tee -a "${sample_stdout}") 2>&1
  if ! check_services; then
    ended_at="$(date --iso-8601=seconds)"
    append_manifest "${run_id}" "${fmax}" "${concurrency}" "${repeat}" "${kind}" "blocked_services_unhealthy" "${started_at}" "${ended_at}" "97" "${run_dir}" "${run_log}" "${cpu_freq_log}"
    return 97
  fi

  freq_pid="$(start_freq_logger "${fmax}" "${cpu_freq_log}")"
  sleep 2

  as_user "cd '${ROOT}' && \
    RUN_LABEL='${run_label}' \
    OUTPUT_DIR='${run_dir}' \
    LOG_PATH='${run_log}' \
    BENCH_ROOT='${ROOT}' \
    BASE_URL='${BASE_URL}' \
    VLLM_URL='${VLLM_URL}' \
    MODEL='${MODEL}' \
    API_KEY='${API_KEY}' \
    MINI_SWE_AGENT_SRC='${MINI_SWE_AGENT_SRC}' \
    bash skills/cpu-swe-agentic-benchmark/scripts/run_benchmark_sweep.sh '${WORKLOAD}' '${concurrency}'" \
    > >(tee -a "${sample_stdout}") 2>&1
  exit_code=$?

  stop_freq_logger "${freq_pid}"
  ended_at="$(date --iso-8601=seconds)"

  if [[ "${exit_code}" -ne 0 ]]; then
    status="benchmark_exit_${exit_code}"
  elif [[ ! -f "${run_dir}/global_summary.csv" ]]; then
    status="missing_global_summary"
    exit_code=96
  elif grep -Eiq 'traceback|connection refused|EngineDeadError|CUDA out of memory|CUDA OOM' "${run_log}"; then
    status="log_error_scan_failed"
    exit_code=95
  else
    status="completed"
  fi

  append_manifest "${run_id}" "${fmax}" "${concurrency}" "${repeat}" "${kind}" "${status}" "${started_at}" "${ended_at}" "${exit_code}" "${run_dir}" "${run_log}" "${cpu_freq_log}"
  write_status "finished run_id=${run_id} status=${status} exit_code=${exit_code}"
  return "${exit_code}"
}

write_aggregate() {
  as_user "python3 - <<'PY'
import csv
import pathlib
import statistics

root = pathlib.Path('${ROOT}')
manifest = pathlib.Path('${MANIFEST}')
out = pathlib.Path('${AGGREGATE_CSV}')
rows = list(csv.DictReader(manifest.open(encoding='utf-8')))
fields = [
    'phase1_id', 'run_id', 'fmax_mhz', 'concurrency', 'repeat', 'kind', 'status',
    'submitted_tasks', 'successful_tasks', 'failed_tasks', 'timeout_tasks',
    'success_rate', 'completion_rate', 'E2E_p90_seconds', 'TTFT_p90', 'TPOT_p90',
    'llm_total_tokens_total', 'llm_total_tokens_per_sec', 'avg_total_tokens_per_task',
    'tokens_per_submitted_task', 'tokens_per_successful_task',
    'avg_llm_time_seconds_per_task', 'avg_bash_time_seconds_per_task',
    'avg_framework_overhead_seconds_per_task', 'actual_cpu_avg_mhz', 'actual_cpu_max_mhz',
    'run_dir', 'run_log', 'cpu_freq_log',
]

def freq_stats(path_text):
    path = pathlib.Path(path_text)
    if not path.exists():
        return 0.0, 0.0
    avgs = []
    maxes = []
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        parts = dict(part.split('=', 1) for part in line.split(',')[1:] if '=' in part)
        if 'avg_mhz' in parts:
            avgs.append(float(parts['avg_mhz']))
        if 'max_mhz' in parts:
            maxes.append(float(parts['max_mhz']))
    return (statistics.mean(avgs) if avgs else 0.0, max(maxes) if maxes else 0.0)

with out.open('w', newline='', encoding='utf-8') as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    for item in rows:
        run_dir = pathlib.Path(item['run_dir'])
        summary_path = run_dir / 'global_summary.csv'
        if not summary_path.exists():
            continue
        summary = next(csv.DictReader(summary_path.open(encoding='utf-8')))
        submitted = float(summary.get('submitted_tasks') or 0)
        successful = float(summary.get('successful_tasks') or 0)
        total_tokens = float(summary.get('llm_total_tokens_total') or 0)
        avg_cpu, max_cpu = freq_stats(item['cpu_freq_log'])
        writer.writerow({
            'phase1_id': item['phase1_id'],
            'run_id': item['run_id'],
            'fmax_mhz': item['fmax_mhz'],
            'concurrency': item['concurrency'],
            'repeat': item['repeat'],
            'kind': item['kind'],
            'status': item['status'],
            'submitted_tasks': summary.get('submitted_tasks', ''),
            'successful_tasks': summary.get('successful_tasks', ''),
            'failed_tasks': summary.get('failed_tasks', ''),
            'timeout_tasks': summary.get('timeout_tasks', ''),
            'success_rate': summary.get('success_rate', ''),
            'completion_rate': summary.get('completion_rate', ''),
            'E2E_p90_seconds': summary.get('E2E_p90_seconds', ''),
            'TTFT_p90': summary.get('TTFT_p90', ''),
            'TPOT_p90': summary.get('TPOT_p90', ''),
            'llm_total_tokens_total': summary.get('llm_total_tokens_total', ''),
            'llm_total_tokens_per_sec': summary.get('llm_total_tokens_per_sec', ''),
            'avg_total_tokens_per_task': summary.get('avg_total_tokens_per_task', ''),
            'tokens_per_submitted_task': f'{(total_tokens / submitted) if submitted else 0.0:.6f}',
            'tokens_per_successful_task': f'{(total_tokens / successful) if successful else 0.0:.6f}',
            'avg_llm_time_seconds_per_task': summary.get('avg_llm_time_seconds_per_task', ''),
            'avg_bash_time_seconds_per_task': summary.get('avg_bash_time_seconds_per_task', ''),
            'avg_framework_overhead_seconds_per_task': summary.get('avg_framework_overhead_seconds_per_task', ''),
            'actual_cpu_avg_mhz': f'{avg_cpu:.2f}',
            'actual_cpu_max_mhz': f'{max_cpu:.2f}',
            'run_dir': item['run_dir'],
            'run_log': item['run_log'],
            'cpu_freq_log': item['cpu_freq_log'],
        })
print(out)
PY"
}

main() {
  local failures=0
  write_status "starting phase1_id=${PHASE1_ID}"

  run_sample 4300 32 warmup warmup || failures=$((failures + 1))

  local samples=(
    "4300 128 1" "4000 128 1" "3600 128 1"
    "4300 160 1" "4000 160 1" "3600 160 1"
    "4300 180 1" "4000 180 1" "3600 180 1"
    "4000 128 2" "3600 128 2" "4300 128 2"
    "4000 160 2" "3600 160 2" "4300 160 2"
    "4000 180 2" "3600 180 2" "4300 180 2"
    "3600 128 3" "4300 128 3" "4000 128 3"
    "3600 160 3" "4300 160 3" "4000 160 3"
    "3600 180 3" "4300 180 3" "4000 180 3"
  )

  local fmax
  local concurrency
  local repeat
  for sample in "${samples[@]}"; do
    read -r fmax concurrency repeat <<< "${sample}"
    run_sample "${fmax}" "${concurrency}" "${repeat}" phase1 || failures=$((failures + 1))
    write_aggregate || true
    if [[ "${failures}" -gt 0 ]]; then
      write_status "stopping phase1_id=${PHASE1_ID} failures=${failures}"
      set_fmax 4300 || true
      write_aggregate || true
      exit 1
    fi
  done

  set_fmax 4300 || true
  write_aggregate || true
  write_status "completed phase1_id=${PHASE1_ID} failures=${failures}"
}

main "$@"
