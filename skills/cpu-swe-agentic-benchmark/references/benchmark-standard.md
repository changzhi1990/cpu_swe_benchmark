# Benchmark Standard

The CPU SWE agentic AI benchmark evaluates local coding-agent performance under controlled repo-based bugfix workloads.

## Standard Benchmark Types

- `algorithm_lab_sorting_bugfix`
- `memory_lab_bandwidth_bugfix`
- `all`

`all` runs every registered workload in `src/cpu_swe_benchmark/workloads.py`.

## Execution Model

Each concurrency point starts `N` mini-swe-agent workers once. Each worker gets an independent copy of the workload repo template and must fix, validate, and submit. The benchmark aggregates success, latency, model serving, throughput, and system metrics per workload/concurrency point.

## Standard Services

- vLLM OpenAI-compatible endpoint: `http://localhost:8000/v1`
- model: `qwen2.5-coder-32b`
- API key: `token-abc123`
- metrics dashboard: `http://localhost:8080`
- AMDuProfPcm path: `/home/user/zhi/AMDuProf_Nda_Linux_x64_5.0.1479/bin/AMDuProfPcm`

## Success Criteria

A run is successful only when mini-swe-agent submits and at least one executed command prints `VALIDATION_PASSED` after the requested pytest command passes.
