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
