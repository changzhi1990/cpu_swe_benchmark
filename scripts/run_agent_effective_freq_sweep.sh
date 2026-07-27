#!/usr/bin/env bash
set -uo pipefail

ROOT="${BENCH_ROOT:-/home/user/zhi/cpu_swe_benchmark}"
RUNSET_ID="${RUNSET_ID:-agent_effective_freq_$(date +%Y%m%d_%H%M%S)}"
WORKLOAD="${WORKLOAD:-algorithm_lab_sorting_bugfix}"
CONCURRENCY_LEVELS="${CONCURRENCY_LEVELS:-1,2,4,8,16,32,64,128,180}"
REPEATS="${REPEATS:-1}"
BASE_URL="${BASE_URL:-http://localhost:8000/v1}"
VLLM_URL="${VLLM_URL:-$BASE_URL}"
MODEL="${MODEL:-qwen2.5-coder-32b}"
API_KEY="${API_KEY:-token-abc123}"
MINI_SWE_AGENT_SRC="${MINI_SWE_AGENT_SRC:-/home/user/zhi/mini-swe-agent-latest/src}"
AVT_CMD="${AVT_CMD:-/opt/AMD/AVT/AVTCMD}"
TOPOLOGY_CMD="${TOPOLOGY_CMD:-/home/user/zhi/AMDuProf_Nda_Linux_x64_5.0.1479/bin/AMDCpuTopology}"
NOFILE_LIMIT="${NOFILE_LIMIT:-1048576}"
TASK_TIMEOUT="${TASK_TIMEOUT:-3600}"
AGENT_CPUSET="${AGENT_CPUSET:-8-760}"
VLLM_CPUSET="${VLLM_CPUSET:-0-7}"

RUN_ROOT="${ROOT}/results/${RUNSET_ID}"
MANIFEST="${RUN_ROOT}/manifest.csv"
STATUS_FILE="${RUN_ROOT}/status.txt"
AGGREGATE_CSV="${RUN_ROOT}/aggregate_samples.csv"
SUMMARY_CSV="${RUN_ROOT}/summary_by_concurrency.csv"
CPU_FREQ_DIR="${RUN_ROOT}/cpu_freq"
SAMPLE_LOG_DIR="${ROOT}/logs/${RUNSET_ID}"

mkdir -p "${RUN_ROOT}" "${CPU_FREQ_DIR}" "${SAMPLE_LOG_DIR}"

if [[ ! -f "${MANIFEST}" ]]; then
  echo "runset_id,run_id,concurrency,repeat,status,started_at,ended_at,exit_code,run_dir,run_log,cpu_freq_log,agent_cpuset,vllm_cpuset,task_timeout" > "${MANIFEST}"
fi

write_status() {
  printf "%s\n" "$*" | tee "${STATUS_FILE}"
}

check_services() {
  curl -sS -m 10 -H "Authorization: Bearer ${API_KEY}" "${BASE_URL}/models" >/dev/null || return 1
}

check_effective_frequency_tools() {
  "${TOPOLOGY_CMD}" >/dev/null || return 1
  if [[ -n "${SUDO_PASSWORD:-}" ]]; then
    printf "%s\n" "${SUDO_PASSWORD}" | sudo -S -p "" "${AVT_CMD}" -module pmm "get_cstates()" >/dev/null || return 1
  else
    sudo -n "${AVT_CMD}" -module pmm "get_cstates()" >/dev/null || return 1
  fi
}

start_freq_logger() {
  local log_path="$1"
  python3 -u - <<PY > "${log_path}" 2>&1 &
import sys
import time

sys.path.insert(0, "${ROOT}/src")
from cpu_swe_benchmark.cpu_frequency import summarize_agent_effective_frequency_sample

while True:
    try:
        sample = summarize_agent_effective_frequency_sample(
            topology_cmd="${TOPOLOGY_CMD}",
            avt_cmd="${AVT_CMD}",
            use_sudo=True,
            sudo_password=None,
        )
        print(
            f"{time.time():.6f},"
            f"agent_cpu_count={sample['agent_cpu_count']:.0f},"
            f"agent_eff_freq_avg_mhz={sample['agent_eff_freq_avg_mhz']:.2f},"
            f"agent_eff_freq_min_mhz={sample['agent_eff_freq_min_mhz']:.2f},"
            f"agent_eff_freq_max_mhz={sample['agent_eff_freq_max_mhz']:.2f},"
            f"agent_eff_freq_p50_mhz={sample['agent_eff_freq_p50_mhz']:.2f},"
            f"agent_eff_freq_p95_mhz={sample['agent_eff_freq_p95_mhz']:.2f},"
            f"agent_eff_freq_p99_mhz={sample['agent_eff_freq_p99_mhz']:.2f},"
            f"agent_freq_avg_mhz={sample['agent_freq_avg_mhz']:.2f},"
            f"agent_c0_avg_percent={sample['agent_c0_avg_percent']:.2f}",
            flush=True,
        )
    except Exception as exc:
        print(f"{time.time():.6f},agent_cpu_count=0,agent_eff_freq_error={type(exc).__name__}:{exc}", flush=True)
    time.sleep(1)
PY
  echo $!
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
  local concurrency="$2"
  local repeat="$3"
  local status="$4"
  local started_at="$5"
  local ended_at="$6"
  local exit_code="$7"
  local run_dir="$8"
  local run_log="$9"
  local cpu_freq_log="${10}"
  python3 - "${MANIFEST}" \
    "${RUNSET_ID}" "${run_id}" "${concurrency}" "${repeat}" "${status}" \
    "${started_at}" "${ended_at}" "${exit_code}" "${run_dir}" "${run_log}" "${cpu_freq_log}" \
    "${AGENT_CPUSET}" "${VLLM_CPUSET}" "${TASK_TIMEOUT}" <<'PY'
import csv
import sys

path = sys.argv[1]
row = sys.argv[2:]
with open(path, "a", newline="", encoding="utf-8") as handle:
    csv.writer(handle).writerow(row)
PY
}

write_aggregate() {
  python3 - <<PY
import csv
import pathlib
import statistics
import sys

sys.path.insert(0, "${ROOT}/src")
from cpu_swe_benchmark.cpu_frequency import summarize_cpu_frequency_log

manifest = pathlib.Path("${MANIFEST}")
out = pathlib.Path("${AGGREGATE_CSV}")
summary_out = pathlib.Path("${SUMMARY_CSV}")
rows = list(csv.DictReader(manifest.open(encoding="utf-8")))
fields = [
    "runset_id", "run_id", "concurrency", "repeat", "status",
    "submitted_tasks", "successful_tasks", "failed_tasks", "timeout_tasks",
    "success_rate", "completion_rate", "E2E_p90_seconds", "TTFT_p90", "TPOT_p90",
    "llm_total_tokens_total", "llm_total_tokens_per_sec", "avg_total_tokens_per_task",
    "avg_llm_time_seconds_per_task", "avg_bash_time_seconds_per_task",
    "avg_framework_overhead_seconds_per_task", "agent_cpu_count_avg",
    "agent_eff_freq_avg_mhz", "agent_eff_freq_min_mhz", "agent_eff_freq_max_mhz",
    "agent_eff_freq_p50_mhz", "agent_eff_freq_p95_mhz", "agent_eff_freq_p99_mhz",
    "agent_freq_avg_mhz", "agent_c0_avg_percent", "run_dir", "run_log", "cpu_freq_log",
]
aggregate_rows = []
for item in rows:
    run_dir = pathlib.Path(item["run_dir"])
    summary_path = run_dir / "global_summary.csv"
    if not summary_path.exists():
        continue
    summary = next(csv.DictReader(summary_path.open(encoding="utf-8")))
    cpu_freq = summarize_cpu_frequency_log(item["cpu_freq_log"])
    aggregate_rows.append({
        "runset_id": item["runset_id"],
        "run_id": item["run_id"],
        "concurrency": item["concurrency"],
        "repeat": item["repeat"],
        "status": item["status"],
        "submitted_tasks": summary.get("submitted_tasks", ""),
        "successful_tasks": summary.get("successful_tasks", ""),
        "failed_tasks": summary.get("failed_tasks", ""),
        "timeout_tasks": summary.get("timeout_tasks", ""),
        "success_rate": summary.get("success_rate", ""),
        "completion_rate": summary.get("completion_rate", ""),
        "E2E_p90_seconds": summary.get("E2E_p90_seconds", ""),
        "TTFT_p90": summary.get("TTFT_p90", ""),
        "TPOT_p90": summary.get("TPOT_p90", ""),
        "llm_total_tokens_total": summary.get("llm_total_tokens_total", ""),
        "llm_total_tokens_per_sec": summary.get("llm_total_tokens_per_sec", ""),
        "avg_total_tokens_per_task": summary.get("avg_total_tokens_per_task", ""),
        "avg_llm_time_seconds_per_task": summary.get("avg_llm_time_seconds_per_task", ""),
        "avg_bash_time_seconds_per_task": summary.get("avg_bash_time_seconds_per_task", ""),
        "avg_framework_overhead_seconds_per_task": summary.get("avg_framework_overhead_seconds_per_task", ""),
        "agent_cpu_count_avg": format(cpu_freq.get("agent_cpu_count_avg", 0.0), ".2f"),
        "agent_eff_freq_avg_mhz": format(cpu_freq.get("agent_eff_freq_avg_mhz", 0.0), ".2f"),
        "agent_eff_freq_min_mhz": format(cpu_freq.get("agent_eff_freq_min_mhz", 0.0), ".2f"),
        "agent_eff_freq_max_mhz": format(cpu_freq.get("agent_eff_freq_max_mhz", 0.0), ".2f"),
        "agent_eff_freq_p50_mhz": format(cpu_freq.get("agent_eff_freq_p50_mhz", 0.0), ".2f"),
        "agent_eff_freq_p95_mhz": format(cpu_freq.get("agent_eff_freq_p95_mhz", 0.0), ".2f"),
        "agent_eff_freq_p99_mhz": format(cpu_freq.get("agent_eff_freq_p99_mhz", 0.0), ".2f"),
        "agent_freq_avg_mhz": format(cpu_freq.get("agent_freq_avg_mhz", 0.0), ".2f"),
        "agent_c0_avg_percent": format(cpu_freq.get("agent_c0_avg_percent", 0.0), ".2f"),
        "run_dir": item["run_dir"],
        "run_log": item["run_log"],
        "cpu_freq_log": item["cpu_freq_log"],
    })

with out.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    writer.writerows(aggregate_rows)

summary_fields = [
    "concurrency", "sample_count", "success_rate_median", "successful_tasks_median",
    "failed_tasks_median", "E2E_p90_median", "TTFT_p90_median", "TPOT_p90_median",
    "avg_bash_time_seconds_per_task_median", "agent_cpu_count_avg_median",
    "agent_eff_freq_avg_mhz_median", "agent_eff_freq_min_mhz_median",
    "agent_eff_freq_max_mhz_median", "agent_eff_freq_p50_mhz_median",
    "agent_eff_freq_p95_mhz_median", "agent_eff_freq_p99_mhz_median",
    "agent_freq_avg_mhz_median", "agent_c0_avg_percent_median",
]
completed_rows = [row for row in aggregate_rows if row["status"] == "completed"]
with summary_out.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=summary_fields)
    writer.writeheader()
    for concurrency in sorted({row["concurrency"] for row in completed_rows}, key=int):
        bucket = [row for row in completed_rows if row["concurrency"] == concurrency]
        def med(key):
            vals = [float(row[key]) for row in bucket if row.get(key) not in {"", None}]
            return f"{statistics.median(vals):.6f}" if vals else ""
        writer.writerow({
            "concurrency": concurrency,
            "sample_count": len(bucket),
            "success_rate_median": med("success_rate"),
            "successful_tasks_median": med("successful_tasks"),
            "failed_tasks_median": med("failed_tasks"),
            "E2E_p90_median": med("E2E_p90_seconds"),
            "TTFT_p90_median": med("TTFT_p90"),
            "TPOT_p90_median": med("TPOT_p90"),
            "avg_bash_time_seconds_per_task_median": med("avg_bash_time_seconds_per_task"),
            "agent_cpu_count_avg_median": med("agent_cpu_count_avg"),
            "agent_eff_freq_avg_mhz_median": med("agent_eff_freq_avg_mhz"),
            "agent_eff_freq_min_mhz_median": med("agent_eff_freq_min_mhz"),
            "agent_eff_freq_max_mhz_median": med("agent_eff_freq_max_mhz"),
            "agent_eff_freq_p50_mhz_median": med("agent_eff_freq_p50_mhz"),
            "agent_eff_freq_p95_mhz_median": med("agent_eff_freq_p95_mhz"),
            "agent_eff_freq_p99_mhz_median": med("agent_eff_freq_p99_mhz"),
            "agent_freq_avg_mhz_median": med("agent_freq_avg_mhz"),
            "agent_c0_avg_percent_median": med("agent_c0_avg_percent"),
        })
print(out)
print(summary_out)
PY
}

write_standard_metrics() {
  python3 "${ROOT}/scripts/aggregate_standard_metrics.py" "${RUN_ROOT}"
}

run_sample() {
  local concurrency="$1"
  local repeat="$2"
  local run_id="agentfreq_c${concurrency}_r${repeat}_${RUNSET_ID}"
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
  write_status "running run_id=${run_id} concurrency=${concurrency} repeat=${repeat}"

  if pgrep -af '[b]enchmark_latency.py' >/dev/null; then
    ended_at="$(date --iso-8601=seconds)"
    append_manifest "${run_id}" "${concurrency}" "${repeat}" "blocked_existing_benchmark" "${started_at}" "${ended_at}" "98" "${run_dir}" "${run_log}" "${cpu_freq_log}"
    return 98
  fi

  if ! check_services; then
    ended_at="$(date --iso-8601=seconds)"
    append_manifest "${run_id}" "${concurrency}" "${repeat}" "blocked_services_unhealthy" "${started_at}" "${ended_at}" "97" "${run_dir}" "${run_log}" "${cpu_freq_log}"
    return 97
  fi

  if ! check_effective_frequency_tools; then
    ended_at="$(date --iso-8601=seconds)"
    append_manifest "${run_id}" "${concurrency}" "${repeat}" "blocked_effective_frequency_tools" "${started_at}" "${ended_at}" "94" "${run_dir}" "${run_log}" "${cpu_freq_log}"
    return 94
  fi

  freq_pid="$(start_freq_logger "${cpu_freq_log}")"
  (
    cd "${ROOT}" && \
      RUN_LABEL="${run_label}" \
      OUTPUT_DIR="${run_dir}" \
      LOG_PATH="${run_log}" \
      BENCH_ROOT="${ROOT}" \
      BASE_URL="${BASE_URL}" \
      VLLM_URL="${VLLM_URL}" \
      MODEL="${MODEL}" \
      API_KEY="${API_KEY}" \
      MINI_SWE_AGENT_SRC="${MINI_SWE_AGENT_SRC}" \
      TASK_TIMEOUT="${TASK_TIMEOUT}" \
      taskset -c "${AGENT_CPUSET}" \
      bash skills/cpu-swe-agentic-benchmark/scripts/run_benchmark_sweep.sh "${WORKLOAD}" "${concurrency}"
  ) > >(tee -a "${sample_stdout}") 2>&1
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

  append_manifest "${run_id}" "${concurrency}" "${repeat}" "${status}" "${started_at}" "${ended_at}" "${exit_code}" "${run_dir}" "${run_log}" "${cpu_freq_log}"
  write_status "finished run_id=${run_id} status=${status} exit_code=${exit_code}"
  return "${exit_code}"
}

main() {
  local failures=0
  if ! ulimit -n "${NOFILE_LIMIT}" >/dev/null 2>&1; then
    write_status "warning unable_to_set_nofile_limit=${NOFILE_LIMIT} current_nofile=$(ulimit -n)"
  fi
  write_status "starting runset_id=${RUNSET_ID} workload=${WORKLOAD} concurrency_levels=${CONCURRENCY_LEVELS} repeats=${REPEATS}"
  IFS=',' read -r -a levels <<< "${CONCURRENCY_LEVELS}"
  for repeat in $(seq 1 "${REPEATS}"); do
    for raw_level in "${levels[@]}"; do
      concurrency="$(echo "${raw_level}" | xargs)"
      [[ -n "${concurrency}" ]] || continue
      run_sample "${concurrency}" "${repeat}" || failures=$((failures + 1))
      write_aggregate || true
      write_standard_metrics || true
      if [[ "${failures}" -gt 0 ]]; then
        write_status "stopping runset_id=${RUNSET_ID} failures=${failures}"
        exit 1
      fi
    done
  done
  write_aggregate || true
  write_standard_metrics || true
  write_status "completed runset_id=${RUNSET_ID} failures=${failures}"
}

main "$@"
