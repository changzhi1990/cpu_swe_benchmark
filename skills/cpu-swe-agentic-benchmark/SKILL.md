---
name: cpu-swe-agentic-benchmark
description: Use when running, maintaining, analyzing, troubleshooting, or publishing the CPU SWE agentic AI benchmark standard on a GPU server, including algorithm_lab_sorting_bugfix, memory_lab_bandwidth_bugfix, all-workload suite runs, mini-swe-agent, vLLM or OpenAI-compatible model serving, concurrency sweeps, TTFT/TPOT/E2E/success metrics, system metrics, AMDuProfPcm memory bandwidth, and GitHub sync for cpu_swe_benchmark.
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
| `AMDUPROFPCM_PATH` | `/home/user/zhi/AMDuProf_Nda_Linux_x64_5.0.1479/bin/AMDuProfPcm` | memory bandwidth tool |
| `RUN_LABEL` | `qwen32b_tp8` | output directory label |

Do not commit benchmark artifacts: `results/`, `logs/`, `__pycache__/`, `.pytest_cache/`, or copied worker workspaces. Do not store passwords, GitHub tokens, or sudo passwords in files.

## Benchmark Standard

The standard benchmark types are:

1. `algorithm_lab_sorting_bugfix`
2. `memory_lab_bandwidth_bugfix`
3. `all`

`all` runs every registered workload in the suite. For workload details, read `references/workloads.md`.

## Standard Run Workflow

1. Identify the target GPU server and server profile. Do not assume any fixed GPU model, host path, endpoint, or model name.
2. Enter the active project: `cd "$BENCH_ROOT"`.
3. Confirm the requested benchmark type is one of the standard types above.
4. Check no stale benchmark or AMDuProfPcm process is running.
5. Verify or start the model server and dashboard metrics for this server profile.
6. Set `AMDUPROFPCM_SUDO_PASSWORD` only in the current shell when AMDuProfPcm needs sudo.
7. Run the requested sweep with `scripts/run_benchmark_sweep.sh` from this skill or with `benchmark_latency.py` directly.
8. Wait for completion; do not report success before verification.
9. Summarize with `scripts/summarize_benchmark.py`.
10. Report output directory, log path, success rates, E2E p90, TTFT p90, TPOT p90, run results, and relevant system metrics.

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

## Verification Checklist

Before claiming a benchmark run is complete, verify:

- benchmark exit code is `0`
- `global_summary.csv` exists
- row count matches requested workload/concurrency combinations
- `success_rate` and `run_results` are present
- TTFT/TPOT/E2E metrics are present and nonzero for successful model runs
- memory bandwidth fields are present when AMDuProfPcm ran
- benchmark log has no traceback, connection refused, EngineDeadError, CUDA OOM, or unexpected failures
- model and dashboard metrics endpoints are reachable if expected to remain up

## Interpretation Rules

- For concurrency `N`, the harness creates `N` independent workspaces from the workload repo template.
- Agents fix the same bug type in separate copied repositories; they do not edit one shared repo.
- Stable task shape makes concurrency points comparable across GPU servers.
- Use `PYTHONPATH=src python3 -m pytest tests -q` for project tests. Root `pytest -q` may collect historical `results/` workspaces.

## References

- `references/benchmark-standard.md`: suite definition and operating assumptions
- `references/workloads.md`: workload details and validation commands
- `references/metrics.md`: output metrics and interpretation
- `references/operations.md`: service startup, sweep, summary, GitHub sync
- `references/troubleshooting.md`: model serving, AMDuProfPcm, pytest, and high-concurrency failures
