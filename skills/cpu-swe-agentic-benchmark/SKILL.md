---
name: cpu-swe-agentic-benchmark
description: Use when running, maintaining, analyzing, troubleshooting, or publishing the CPU SWE agentic AI benchmark standard on a GPU server, including algorithm_lab_sorting_bugfix, memory_lab_bandwidth_bugfix, all-workload suite runs, mini-swe-agent, vLLM or OpenAI-compatible model serving, concurrency sweeps, TTFT/TPOT/E2E/success metrics, system metrics, AMD/Intel CPU memory bandwidth, AMDuProfPcm, Intel perf uncore IMC, and GitHub sync for cpu_swe_benchmark.
---

# CPU SWE Agentic Benchmark

Use this skill for the CPU SWE agentic AI benchmark standard on any GPU server. The local host values are defaults only; override them with a server profile when testing another GPU server or agentic AI environment.

## Server Profile

Confirm or set these before running a benchmark:

| Variable | Default | Meaning |
| --- | --- | --- |
| `BENCH_ROOT` | `/home/user/zhi/cpu_swe_benchmark` | active benchmark project |
| `GITHUB_CLONE` | `/home/user/zhi/cpu_swe_benchmark_github` | Git checkout used for commits |
| `MINI_SWE_AGENT_SRC` | `/home/user/zhi/mini-swe-agent-latest/src` | mini-swe-agent source |
| `VLLM_URL` / `BASE_URL` | `http://localhost:8000/v1` | OpenAI-compatible model endpoint |
| `MODEL` | `qwen2.5-coder-32b` | served model name |
| `API_KEY` | `token-abc123` | model API key |
| `DASHBOARD_HEALTH` | `http://localhost:8080/api/health` | metrics health endpoint |
| `AMDUPROFPCM_PATH` | `/home/user/zhi/AMDuProf_Nda_Linux_x64_5.0.1479/bin/AMDuProfPcm` | AMD memory bandwidth tool; Intel hosts fall back to `perf` uncore IMC events |
| `RUN_LABEL` | `qwen32b_tp8` | output directory label |

Do not commit benchmark artifacts: `results/`, `logs/`, `__pycache__/`, `.pytest_cache/`, or copied worker workspaces. Do not store passwords, GitHub tokens, or sudo passwords in files.

## Benchmark Standard

The standard benchmark types are:

1. `algorithm_lab_sorting_bugfix`
2. `memory_lab_bandwidth_bugfix`
3. `all`

`all` runs every registered workload in the suite. For workload details, read `references/workloads.md`.

Primary agentic performance reporting should include successful-work metrics:

- `successful_total_tokens / second`: successful-token throughput, computed as
  `successful_agent_total_tokens_total / batch_wall_time_seconds`.
- `successful_total_tokens / watt`: successful-token power efficiency, computed as
  `successful_agent_total_tokens_total / average_power_watts` with a clearly stated power source.
- `successful_agents / watt`: task-success power efficiency, computed as
  `successful_tasks / average_power_watts` with the same power source used for token-per-watt reporting.

Use `successful_agent_total_tokens_total` as the standard CSV field for successful total tokens.
When reporting watt-normalized metrics, state whether the denominator is average GPU power, CPU package power,
or average system power, and measure it over the same batch window as `batch_wall_time_seconds`.

## Standard Bar Chart Reporting

When asked to visualize agent-point benchmark results, use `global_metrics.csv as the raw source`.
Do not treat ad-hoc Excel workbooks as canonical inputs; they may be reference material only.

Generate one bar chart for each of these `global_metrics.csv` fields:

- `batch_wall_time_seconds`
- `throughput_successful_tasks_per_sec`
- `E2E_p90_seconds`
- `avg_llm_time_seconds_per_task`
- `successful_agent_total_tokens_per_sec`

Use the `concurrency` field as the x-axis agent point and label points as `c<N>`.
If the table has `server_name`, use it as the preferred server dimension. When `server_name` is absent but multiple
servers are being compared, add a server label from the server profile or runset identity before concatenating
multiple `global_metrics.csv` files. If the combined data has multiple servers, draw grouped bars for each
agent point with one color per server and a visible legend. If there is only one server, draw one bar per agent point.

If multiple rows exist for the same server and `concurrency` because of repeats, aggregate numeric metric values by
mean before plotting and write the aggregated plotting data to `plot_data_mean_by_server_concurrency.csv`. If the
user explicitly requests per-repeat bars, skip aggregation for that view and label repeats as `c<N>-r<M>` using the
`repeat` field.

Write chart outputs under the runset directory in `bar_charts/`: one PNG per metric and, when practical, a combined
multi-page PDF containing the same five charts. Include `server_name`/server legend information in the figure when
more than one server is present.

## Memory Bandwidth Collector Selection

The benchmark memory bandwidth sampler supports both AMD and Intel hosts:

- AMD: use `AMDuProfPcm top --msr -r -m memory -a -I 1000` when the configured `AMDUPROFPCM_PATH` exists.
- Intel: use `perf stat -a -I 1000` with `uncore_imc/cas_count_read_sch*` and `uncore_imc/cas_count_write_sch*` events when AMDuProfPcm is unavailable and Intel uncore IMC events exist.

Use `AMDUPROFPCM_SUDO_PASSWORD` only in the current shell for unattended sampling that requires sudo. The name is retained for compatibility and is used by both AMD AMDuProfPcm and Intel perf paths. Do not store sudo passwords in files.

`memory_bandwidth_source` identifies the selected path in each point `summary.json`; expected values include `amd_pcm_top`, `amd_pcm_report`, and `intel_perf_uncore_imc`. Numeric bandwidth fields use the existing `memory_bandwidth_*_gbps` names. On Intel hosts the sampler logs still live under the per-point `amd_pcm/` directory for backward-compatible result parsing, but the contents are `perf stat` stdout/stderr.

## Standard Run Workflow

1. Identify the target GPU server and server profile. Do not assume any fixed GPU model, host path, endpoint, or model name.
2. Enter the active project: `cd "$BENCH_ROOT"`.
3. Confirm the requested benchmark type is one of the standard types above.
4. Check no stale benchmark or AMDuProfPcm process is running.
5. Verify or start the model server and dashboard metrics for this server profile.
6. Set `AMDUPROFPCM_SUDO_PASSWORD` only in the current shell when AMDuProfPcm or Intel `perf` memory-bandwidth sampling needs sudo.
7. Run the requested sweep with `scripts/run_benchmark_sweep.sh` from this skill or with `benchmark_latency.py` directly.
8. Wait for completion; do not report success before verification.
9. Summarize runsets with `scripts/aggregate_standard_metrics.py` so `global_metrics.csv`, `cpu_metrics.csv`, `gpu_metrics.csv`, and `vllm_metrics.csv` exist.
10. When charts are requested, generate standard bar charts from `global_metrics.csv` using the Standard Bar Chart Reporting rules.
11. Report output directory, log path, success rates, E2E p90, TTFT p90, TPOT p90, run results, chart paths when generated, and relevant system metrics.

## Useful Commands

Check a GPU server profile:

```bash
BENCH_ROOT=/path/to/cpu_swe_benchmark \
VLLM_URL=http://localhost:8000/v1 \
MODEL=qwen2.5-coder-32b \
bash skills/cpu-swe-agentic-benchmark/scripts/check_benchmark_services.sh
```

Run a sweep:

```bash
BENCH_ROOT=/path/to/cpu_swe_benchmark \
RUN_LABEL=my_gpu_agentic_ai \
bash skills/cpu-swe-agentic-benchmark/scripts/run_benchmark_sweep.sh \
  memory_lab_bandwidth_bugfix \
  1,2,4,8,16,32,64,128,160,180,200
```

Summarize a run:

```bash
python3 skills/cpu-swe-agentic-benchmark/scripts/summarize_benchmark.py \
  results/<run_dir>
```

Aggregate standard runset metrics:

```bash
python3 scripts/aggregate_standard_metrics.py \
  results/<runset_dir>
```

## Verification Checklist

Before claiming a benchmark run is complete, verify:

- benchmark exit code is `0`
- `global_summary.csv` exists
- row count matches requested workload/concurrency combinations
- runset `global_metrics.csv`, `cpu_metrics.csv`, `gpu_metrics.csv`, and `vllm_metrics.csv` exist with one row per requested concurrency
- each standard metrics table includes task counts, `success_rate`, `E2E_p90_seconds`, `TTFT_p90`, `TPOT_p90`, run paths, CPU affinity, vLLM affinity, and task timeout
- TTFT/TPOT/E2E metrics are present and nonzero for successful model runs
- memory bandwidth fields are present when the AMD/Intel memory-bandwidth sampler ran
- AVT effective-frequency fields are present in `cpu_metrics.csv` when AVT sampling ran
- CPU, GPU, vLLM, and general benchmark fields are all present in `global_metrics.csv`
- requested bar charts are generated from `global_metrics.csv`, include the five standard chart metrics, and use grouped bars with server labels when multiple servers are present
- benchmark log has no traceback, connection refused, EngineDeadError, CUDA OOM, or unexpected failures
- model and dashboard metrics endpoints are reachable if expected to remain up

## Interpretation Rules

- For concurrency `N`, the harness creates `N` independent workspaces from the workload repo template.
- Agents fix the same bug type in separate copied repositories; they do not edit one shared repo.
- Stable task shape makes concurrency points comparable across GPU servers.
- Use `PYTHONPATH=src python3 -m pytest tests -q` for project tests. Root `pytest -q` may collect historical `results/` workspaces.
- For high-concurrency points such as 512+, start the run shell with `ulimit -n 1048576` before spawning agents.
- For AVT effective frequency, map Linux CPUs through kernel `physical_package_id` and `core_id`; do not treat `AMDCpuTopology` `Thread` as the Linux CPU number.
- On the 5090 server profile, bind vLLM to Linux CPUs `0-7` and bind agents to Linux CPUs `8-760` for every sweep point. Record these as `vllm_cpuset` and `agent_cpuset`.

## References

- `references/benchmark-standard.md`: suite definition and operating assumptions
- `references/workloads.md`: workload details and validation commands
- `references/metrics.md`: output metrics and interpretation
- `references/operations.md`: service startup, sweep, summary, GitHub sync
- `references/troubleshooting.md`: model serving, AMDuProfPcm, pytest, and high-concurrency failures
