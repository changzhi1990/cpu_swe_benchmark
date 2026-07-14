---
name: cpu-swe-agentic-benchmark
description: Use when running, maintaining, analyzing, troubleshooting, or publishing the CPU SWE agentic AI benchmark standard, including algorithm_lab_sorting_bugfix, memory_lab_bandwidth_bugfix, all-workload suite runs, mini-swe-agent, local vLLM Qwen service, concurrency sweeps, TTFT/TPOT/E2E/success metrics, system metrics, AMDuProfPcm memory bandwidth, and GitHub sync for cpu_swe_benchmark.
---

# CPU SWE Agentic Benchmark

Use this skill for the CPU SWE agentic AI benchmark project on the 5090 server.

## Project Paths

- Active project: `/home/user/zhi/cpu_swe_benchmark`
- GitHub clone: `/home/user/zhi/cpu_swe_benchmark_github`
- GitHub remote: `https://github.com/changzhi1990/cpu_swe_benchmark`
- mini-swe-agent source: `/home/user/zhi/mini-swe-agent-latest/src`
- vLLM endpoint: `http://localhost:8000/v1`
- served model: `qwen2.5-coder-32b`
- dashboard metrics endpoint: `http://localhost:8080/api/health`

Do not commit benchmark artifacts: `results/`, `logs/`, `__pycache__/`, `.pytest_cache/`, or copied worker workspaces. Do not store passwords, GitHub tokens, or sudo passwords in files.

## Benchmark Standard

The standard benchmark types are:

1. `algorithm_lab_sorting_bugfix`
2. `memory_lab_bandwidth_bugfix`
3. `all`

`all` means run every registered workload in the suite. For detailed workload behavior, read `references/workloads.md`.

## Standard Run Workflow

1. Enter the active project: `cd /home/user/zhi/cpu_swe_benchmark`.
2. Confirm the requested benchmark type is one of the standard types above.
3. Check no stale benchmark or AMDuProfPcm process is running.
4. Verify or start vLLM and dashboard metrics.
5. Set `AMDUPROFPCM_SUDO_PASSWORD` only in the current shell when AMDuProfPcm needs sudo.
6. Run the requested sweep with `scripts/run_benchmark_sweep.sh` from this skill or with `benchmark_latency.py` directly.
7. Wait for completion; do not report success before verification.
8. Summarize with `scripts/summarize_benchmark.py`.
9. Report output directory, log path, success rates, E2E p90, TTFT p90, TPOT p90, run results, and relevant system metrics.

## Useful Commands

Check services:

```bash
bash skills/cpu-swe-agentic-benchmark/scripts/check_benchmark_services.sh
```

Run a sweep:

```bash
bash skills/cpu-swe-agentic-benchmark/scripts/run_benchmark_sweep.sh   memory_lab_bandwidth_bugfix   1,2,4,8,16,32,64,128,160,180,200
```

Summarize a run:

```bash
python3 skills/cpu-swe-agentic-benchmark/scripts/summarize_benchmark.py   results/<run_dir>
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
- vLLM and dashboard metrics are still reachable if they were expected to remain up

## Interpretation Rules

- For concurrency `N`, the harness creates `N` independent workspaces from the workload repo template.
- Agents fix the same bug type in separate copied repositories; they do not edit one shared repo.
- Stable task shape makes concurrency points comparable.
- Use `PYTHONPATH=src python3 -m pytest tests -q` for project tests. Root `pytest -q` may collect historical `results/` workspaces.

## References

- `references/benchmark-standard.md`: suite definition and operating assumptions
- `references/workloads.md`: workload details and validation commands
- `references/metrics.md`: output metrics and interpretation
- `references/operations.md`: service startup, sweep, summary, GitHub sync
- `references/troubleshooting.md`: vLLM, AMDuProfPcm, pytest, and high-concurrency failures
