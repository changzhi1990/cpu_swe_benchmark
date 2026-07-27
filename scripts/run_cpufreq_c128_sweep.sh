#!/usr/bin/env bash
set -uo pipefail

ROOT="${BENCH_ROOT:-/home/user/zhi/cpu_swe_benchmark}"
BENCH_USER="${BENCH_USER:-user}"
RUNSET_ID="${RUNSET_ID:-cpufreq_c128_$(date +%Y%m%d_%H%M%S)}"
WORKLOAD="${WORKLOAD:-algorithm_lab_sorting_bugfix}"
CONCURRENCY="${CONCURRENCY:-128}"
BASE_URL="${BASE_URL:-http://localhost:8000/v1}"
VLLM_URL="${VLLM_URL:-$BASE_URL}"
MODEL="${MODEL:-qwen2.5-coder-32b}"
API_KEY="${API_KEY:-token-abc123}"
MINI_SWE_AGENT_SRC="${MINI_SWE_AGENT_SRC:-/home/user/zhi/mini-swe-agent-latest/src}"
AVT_CMD="${AVT_CMD:-/opt/AMD/AVT/AVTCMD}"

RUN_ROOT="${ROOT}/results/${RUNSET_ID}"
MANIFEST="${RUN_ROOT}/manifest.csv"
STATUS_FILE="${RUN_ROOT}/status.txt"
AGGREGATE_CSV="${RUN_ROOT}/aggregate_samples.csv"
SUMMARY_CSV="${RUN_ROOT}/summary_by_fmax.csv"
CPU_FREQ_DIR="${ROOT}/logs/cpu_freq/${RUNSET_ID}"
SAMPLE_LOG_DIR="${ROOT}/logs/${RUNSET_ID}"
AVT_LOG="${SAMPLE_LOG_DIR}/avt_commands.log"

mkdir -p "${RUN_ROOT}" "${CPU_FREQ_DIR}" "${SAMPLE_LOG_DIR}"
chown -R "${BENCH_USER}:${BENCH_USER}" "${RUN_ROOT}" "${CPU_FREQ_DIR}" "${SAMPLE_LOG_DIR}" 2>/dev/null || true

if [[ ! -f "${MANIFEST}" ]]; then
  echo "runset_id,run_id,fmax_mhz,concurrency,repeat,kind,status,started_at,ended_at,exit_code,run_dir,run_log,cpu_freq_log,avt_log" > "${MANIFEST}"
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

restore_fmax() {
  set_fmax 4300 || true
}

on_signal() {
  write_status "stopped_by_signal at $(date --iso-8601=seconds); restoring cclk_fmax=4300"
  restore_fmax
  exit 130
}

trap on_signal INT TERM

start_freq_logger() {
  local fmax="$1"
  local log_path="$2"
  as_user "python3 -u - <<'PY' > '${log_path}' 2>&1 &
import sys
import time

sys.path.insert(0, '${ROOT}/src')
from cpu_swe_benchmark.cpu_frequency import read_proc_cpuinfo_frequencies, summarize_frequency_sample

fmax = '${fmax}'
while True:
    sample = summarize_frequency_sample(read_proc_cpuinfo_frequencies())
    if sample['cores']:
        print(
            f\"{time.time():.6f},fmax_mhz={fmax},\"
            f\"avg_mhz={sample['avg_mhz']:.2f},min_mhz={sample['min_mhz']:.2f},\"
            f\"max_mhz={sample['max_mhz']:.2f},p95_mhz={sample['p95_mhz']:.2f},\"
            f\"p99_mhz={sample['p99_mhz']:.2f},\"
            f\"active_core_count={sample['active_core_count']:.0f},\"
            f\"active_core_avg_mhz={sample['active_core_avg_mhz']:.2f},\"
            f\"active_core_max_mhz={sample['active_core_max_mhz']:.2f},\"
            f\"cores={sample['cores']:.0f}\",
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
    "${RUNSET_ID}" "${run_id}" "${fmax}" "${concurrency}" "${repeat}" "${kind}" "${status}" \
    "${started_at}" "${ended_at}" "${exit_code}" "${run_dir}" "${run_log}" "${cpu_freq_log}" "${AVT_LOG}" >> "${MANIFEST}"
}

run_sample() {
  local fmax="$1"
  local concurrency="$2"
  local repeat="$3"
  local kind="$4"
  local run_id="9535_fmax${fmax}_c${concurrency}_r${repeat}_${RUNSET_ID}"
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

manifest = pathlib.Path('${MANIFEST}')
out = pathlib.Path('${AGGREGATE_CSV}')
summary_out = pathlib.Path('${SUMMARY_CSV}')
rows = list(csv.DictReader(manifest.open(encoding='utf-8')))
fields = [
    'runset_id', 'run_id', 'fmax_mhz', 'concurrency', 'repeat', 'kind', 'status',
    'submitted_tasks', 'successful_tasks', 'failed_tasks', 'timeout_tasks',
    'success_rate', 'completion_rate', 'E2E_p90_seconds', 'TTFT_p90', 'TPOT_p90',
    'llm_total_tokens_total', 'llm_total_tokens_per_sec', 'avg_total_tokens_per_task',
    'tokens_per_submitted_task', 'tokens_per_successful_task',
    'avg_llm_time_seconds_per_task', 'avg_bash_time_seconds_per_task',
    'avg_framework_overhead_seconds_per_task', 'actual_cpu_avg_mhz', 'actual_cpu_max_mhz',
    'actual_cpu_p95_mhz', 'actual_cpu_p99_mhz', 'active_core_count_avg',
    'active_core_avg_mhz', 'active_core_max_mhz',
    'run_dir', 'run_log', 'cpu_freq_log',
]

import sys
sys.path.insert(0, '${ROOT}/src')
from cpu_swe_benchmark.cpu_frequency import summarize_cpu_frequency_log

aggregate_rows = []
for item in rows:
    run_dir = pathlib.Path(item['run_dir'])
    summary_path = run_dir / 'global_summary.csv'
    if not summary_path.exists():
        continue
    summary = next(csv.DictReader(summary_path.open(encoding='utf-8')))
    submitted = float(summary.get('submitted_tasks') or 0)
    successful = float(summary.get('successful_tasks') or 0)
    total_tokens = float(summary.get('llm_total_tokens_total') or 0)
    cpu_freq = summarize_cpu_frequency_log(item['cpu_freq_log'])
    aggregate_rows.append({
        'runset_id': item['runset_id'],
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
        'actual_cpu_avg_mhz': format(cpu_freq.get('actual_cpu_avg_mhz', 0.0), '.2f'),
        'actual_cpu_max_mhz': format(cpu_freq.get('actual_cpu_max_mhz', 0.0), '.2f'),
        'actual_cpu_p95_mhz': format(cpu_freq.get('actual_cpu_p95_mhz', 0.0), '.2f'),
        'actual_cpu_p99_mhz': format(cpu_freq.get('actual_cpu_p99_mhz', 0.0), '.2f'),
        'active_core_count_avg': format(cpu_freq.get('active_core_count_avg', 0.0), '.2f'),
        'active_core_avg_mhz': format(cpu_freq.get('active_core_avg_mhz', 0.0), '.2f'),
        'active_core_max_mhz': format(cpu_freq.get('active_core_max_mhz', 0.0), '.2f'),
        'run_dir': item['run_dir'],
        'run_log': item['run_log'],
        'cpu_freq_log': item['cpu_freq_log'],
    })

with out.open('w', newline='', encoding='utf-8') as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    writer.writerows(aggregate_rows)

summary_fields = [
    'fmax_mhz', 'sample_count', 'success_rate_median', 'successful_tasks_median',
    'failed_tasks_median', 'E2E_p90_median', 'TTFT_p90_median', 'TPOT_p90_median',
    'llm_total_tokens_per_sec_median', 'avg_total_tokens_per_task_median',
    'avg_llm_time_seconds_per_task_median', 'avg_bash_time_seconds_per_task_median',
    'actual_cpu_avg_mhz_median', 'actual_cpu_max_mhz_median',
    'actual_cpu_p95_mhz_median', 'actual_cpu_p99_mhz_median',
    'active_core_count_avg_median', 'active_core_avg_mhz_median',
    'active_core_max_mhz_median',
]
phase1_rows = [row for row in aggregate_rows if row['kind'] == 'phase1' and row['status'] == 'completed']
with summary_out.open('w', newline='', encoding='utf-8') as handle:
    writer = csv.DictWriter(handle, fieldnames=summary_fields)
    writer.writeheader()
    for fmax in sorted({row['fmax_mhz'] for row in phase1_rows}, key=int):
        bucket = [row for row in phase1_rows if row['fmax_mhz'] == fmax]
        def med(key):
            vals = [float(row[key]) for row in bucket if row.get(key) not in {'', None}]
            return f'{statistics.median(vals):.6f}' if vals else ''
        writer.writerow({
            'fmax_mhz': fmax,
            'sample_count': len(bucket),
            'success_rate_median': med('success_rate'),
            'successful_tasks_median': med('successful_tasks'),
            'failed_tasks_median': med('failed_tasks'),
            'E2E_p90_median': med('E2E_p90_seconds'),
            'TTFT_p90_median': med('TTFT_p90'),
            'TPOT_p90_median': med('TPOT_p90'),
            'llm_total_tokens_per_sec_median': med('llm_total_tokens_per_sec'),
            'avg_total_tokens_per_task_median': med('avg_total_tokens_per_task'),
            'avg_llm_time_seconds_per_task_median': med('avg_llm_time_seconds_per_task'),
            'avg_bash_time_seconds_per_task_median': med('avg_bash_time_seconds_per_task'),
            'actual_cpu_avg_mhz_median': med('actual_cpu_avg_mhz'),
            'actual_cpu_max_mhz_median': med('actual_cpu_max_mhz'),
            'actual_cpu_p95_mhz_median': med('actual_cpu_p95_mhz'),
            'actual_cpu_p99_mhz_median': med('actual_cpu_p99_mhz'),
            'active_core_count_avg_median': med('active_core_count_avg'),
            'active_core_avg_mhz_median': med('active_core_avg_mhz'),
            'active_core_max_mhz_median': med('active_core_max_mhz'),
        })
print(out)
print(summary_out)
PY"
}

main() {
  local failures=0
  write_status "starting runset_id=${RUNSET_ID}"

  run_sample 4300 32 warmup warmup || failures=$((failures + 1))
  write_aggregate || true

  local samples=(
    "4300 ${CONCURRENCY} 1"
    "4000 ${CONCURRENCY} 1"
    "3600 ${CONCURRENCY} 1"
    "4000 ${CONCURRENCY} 2"
    "3600 ${CONCURRENCY} 2"
    "4300 ${CONCURRENCY} 2"
    "3600 ${CONCURRENCY} 3"
    "4300 ${CONCURRENCY} 3"
    "4000 ${CONCURRENCY} 3"
  )

  local fmax
  local concurrency
  local repeat
  for sample in "${samples[@]}"; do
    read -r fmax concurrency repeat <<< "${sample}"
    run_sample "${fmax}" "${concurrency}" "${repeat}" phase1 || failures=$((failures + 1))
    write_aggregate || true
    if [[ "${failures}" -gt 0 ]]; then
      write_status "stopping runset_id=${RUNSET_ID} failures=${failures}; restoring cclk_fmax=4300"
      restore_fmax
      write_aggregate || true
      exit 1
    fi
  done

  restore_fmax
  write_aggregate || true
  write_status "completed runset_id=${RUNSET_ID} failures=${failures}; cclk_fmax restored to 4300"
}

main "$@"
