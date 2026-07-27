# CPU SWE Benchmark

CPU-centric latency and throughput benchmark for latest `mini-swe-agent` with a local vLLM TP8 Qwen2.5-Coder-32B-Instruct service.

The benchmark runs repo-based coding workloads across concurrency points such as `1,2,4,8,16,32,64,128`. Each concurrency point starts that many local mini-swe-agent workers once (`waves=1`) and reports task completion latency, success rate, successful-task throughput, system utilization, workload execution phase utilization, LLM serving TTFT/TPOT metrics, and AMDuProfPcm memory bandwidth metrics.

## Workloads

- `algorithm_lab_sorting_bugfix`
- `memory_lab_bandwidth_bugfix`

`algorithm_lab_sorting_bugfix` copies `repo_templates/algorithm_lab` into each worker workspace. The agent must inspect the repository, fix `src/algorithm_lab/sorting.py`, run `PYTHONPATH=src python3 -m pytest tests/test_sorting.py`, avoid modifying tests, print `VALIDATION_PASSED`, and then submit. The initial bug still performs Python-level bubble-sort work in the wrong order, so pytest runs CPU-intensive 10000- and 20000-integer sorts before it fails and again after the fix.

`memory_lab_bandwidth_bugfix` copies `repo_templates/memory_lab` into each worker workspace. The agent must inspect the repository, fix `src/memory_lab/bandwidth.py`, run `PYTHONPATH=src python3 -m pytest tests/test_bandwidth.py`, avoid modifying tests, print `VALIDATION_PASSED`, and then submit. The initial bug still performs NumPy vectorized streaming reads and writes but omits one input stream, so pytest runs the memory-bandwidth-sensitive workload before it fails and again after the fix.

The agent step limit is 20 to leave enough room for reproduce, inspect, fix, validate, and submit commands.

## Start vLLM

```bash
cd /home/user/zhi/cpu_swe_benchmark
bash scripts/start_vllm_tp8_qwen32b.sh
```

The default endpoint is `http://localhost:8000/v1`, served model name is `qwen2.5-coder-32b`, and API key is `token-abc123`.
Each LLM call defaults to `max_tokens=512` so long agent histories remain under the local vLLM context limit.

## Run Quick Benchmark

```bash
cd /home/user/zhi/cpu_swe_benchmark
bash scripts/run_sorting_quick.sh
```

For a faster smoke test:

```bash
CONCURRENCY_LEVELS=1,2,4 bash scripts/run_sorting_quick.sh
```

## Run Benchmark

```bash
python3 benchmark_latency.py \
  --base-url http://localhost:8000/v1 \
  --api-key token-abc123 \
  --model-path qwen2.5-coder-32b \
  --benchmark-type algorithm_lab_sorting_bugfix \
  --concurrency-levels 1,2,4,8,16,32,64,128 \
  --mini-swe-agent-src /home/user/zhi/mini-swe-agent-latest/src \
  --output-dir results/qwen32b_tp8_algorithm_lab_sorting_bugfix
```

For the memory-bandwidth-sensitive workload, use:

```bash
python3 benchmark_latency.py \
  --base-url http://localhost:8000/v1 \
  --api-key token-abc123 \
  --model-path qwen2.5-coder-32b \
  --benchmark-type memory_lab_bandwidth_bugfix \
  --concurrency-levels 1,2,4,8,16,32,64,128 \
  --mini-swe-agent-src /home/user/zhi/mini-swe-agent-latest/src \
  --output-dir results/qwen32b_tp8_memory_lab_bandwidth_bugfix
```

## Output

Each `(workload, concurrency)` point writes:

- `summary.json`: success rate, completion rate, throughput, latency percentiles, LLM/bash timing breakdown, TTFT/TPOT metrics, and AMDuProfPcm memory bandwidth metrics when available.
- `runs.jsonl`: one JSON object per agent run.
- `runs/<run_id>/trajectory.json`: mini-swe-agent trajectory when available.
- `runs/<run_id>/run_result.json`: full per-run benchmark record.
- `runs/<run_id>/workspace/`: worker workspace, including generated scripts or copied repo templates.

The root output directory also gets:

- `global_summary.csv`
- `global_summary.json`

Runset-level sweep directories standardize analysis metrics into one all-in-one table plus three domain views:

- `global_metrics.csv`: all shared, CPU, GPU, vLLM, memory, bandwidth, and AVT effective-frequency metrics.
- `cpu_metrics.csv`: CPU, memory, memory bandwidth, and AVT effective-frequency summaries.
- `gpu_metrics.csv`: GPU utilization, GPU memory bandwidth utilization, and GPU memory usage summaries.
- `vllm_metrics.csv`: vLLM serving metrics such as TTFT, TPOT, tokens, and per-task LLM timing.

Each of these tables includes shared context fields such as `status`, submitted/successful/failed/timeout
task counts, `success_rate`, `E2E_p90_seconds`, `TTFT_p90`, `TPOT_p90`, run paths, CPU affinity,
vLLM affinity, and `task_timeout`. Operational provenance files such as `manifest.csv`, `summary_by_concurrency.csv`,
and `aggregate_samples.csv` may still be present, but downstream metric analysis should use `global_metrics.csv`
or one of the three domain metrics views.

## Agentic Throughput And Efficiency Metrics

Agentic AI benchmark analysis should focus on successful work, not just raw model generation. In the standard
tables, `successful_agent_total_tokens_total` is the successful-token total, and
`successful_agent_total_tokens_per_sec` is the successful-token throughput:

```text
successful_total_tokens / second = successful_agent_total_tokens_total / batch_wall_time_seconds
```

Power-normalized metrics should use one clearly stated watt denominator, such as average GPU power or average
system power measured over the same batch window:

```text
successful_total_tokens / watt = successful_agent_total_tokens_total / average_power_watts
successful_agents / watt = successful_tasks / average_power_watts
```

Use `successful_total_tokens / second` to compare end-to-end agentic throughput, `successful_total_tokens / watt`
to compare token-level energy efficiency, and `successful_agents / watt` to compare task-success efficiency.
For energy-normalized reporting, use the same successful numerator divided by total joules instead of average watts.

For high-concurrency sweeps, raise the open-file limit before launching the run:

```bash
ulimit -n 1048576
```

This prevents `Too many open files` while spawning hundreds of worker processes.

For the 5090 server profile, use fixed CPU affinity for every sweep point:

- vLLM: Linux CPUs `0-7`
- agents: Linux CPUs `8-760`

Each agent worker is intended to consume one CPU from the agent CPU set. Record both `agent_cpuset`
and `vllm_cpuset` in the standard metrics tables.

## Memory Bandwidth Metrics

Each concurrency point starts AMDuProfPcm around the point execution and parses system-level memory bandwidth from the generated `report.csv`.

Default AMDuProfPcm command:

```bash
/home/user/zhi/AMDuProf_Nda_Linux_x64_5.0.1479/bin/AMDuProfPcm \
  top --msr -r -m memory -a -I 1000
```

`--msr` requires sudo. For unattended benchmark runs, provide the sudo password through:

```bash
export AMDUPROFPCM_SUDO_PASSWORD=...
```

The global CSV includes:

- `memory_bandwidth_total_p90_gbps`
- `memory_bandwidth_total_max_gbps`
- `memory_bandwidth_read_p90_gbps`
- `memory_bandwidth_read_max_gbps`
- `memory_bandwidth_write_p90_gbps`
- `memory_bandwidth_write_max_gbps`

## AVT Effective Frequency Metrics

Agent effective-frequency metrics are sampled with:

```bash
/opt/AMD/AVT/AVTCMD -module pmm "get_cstates()"
```

Linux CPU IDs are mapped to AVT `Pkg/Die/CCD/PhysicalCore` keys through:

1. `/sys/devices/system/cpu/cpuN/topology/physical_package_id`
2. `/sys/devices/system/cpu/cpuN/topology/core_id`
3. `AMDCpuTopology` `Package/Core`
4. local CCX core index used by AVT

The runset stores:

- `linux_cpu_to_avt_mapping.csv`: Linux CPU to AVT core mapping.
- `cpu_freq/*.aggregate.csv`: sampled aggregate AVT effective-frequency metrics per sweep point.
- `per_core_freq/*.per_core.csv`: sampled per-Linux-CPU AVT metrics per sweep point.

The runset-level `cpu_metrics.csv` merges shared run context, `cpu_memory.csv`, and AVT aggregate fields such as
`agent_eff_freq_avg_mhz`, `agent_eff_freq_p95_mhz`, `agent_freq_avg_mhz`, and `agent_c0_avg_percent`.
The runset-level `global_metrics.csv` merges those CPU metrics with GPU metrics, vLLM serving metrics,
and all general benchmark fields from `global_summary.csv`.

## Success Criteria

A run is successful only if:

1. mini-swe-agent exits with `Submitted`, and
2. at least one executed command output contains `VALIDATION_PASSED`.

This prevents a model from submitting without actually running the workload validation.

## Dashboard

Start the Web UI:

```bash
cd /home/user/zhi/cpu_swe_benchmark
bash scripts/start_dashboard.sh
```

The default port is `80`. Binding port `80` usually requires root privileges or a Linux capability. If running as a normal user, use:

```bash
PORT=8080 bash scripts/start_dashboard.sh
```

The dashboard exposes:

- `/`: single-page UI
- `/api/system`: CPU, load, memory, GPU, and vLLM container metrics
- `/api/business`: latest benchmark business metrics from `results/**/global_summary.csv`
- `/api/system/history`: recent CPU/GPU utilization history
- `/api/health`: health check
