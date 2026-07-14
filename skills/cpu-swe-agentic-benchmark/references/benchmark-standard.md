# Benchmark Standard

The CPU SWE agentic AI benchmark evaluates coding-agent performance under controlled repo-based bugfix workloads on GPU servers. It is not tied to one machine SKU; compare servers by recording the server profile, model endpoint, model name, concurrency levels, and benchmark commit.

## Standard Benchmark Types

- `algorithm_lab_sorting_bugfix`
- `memory_lab_bandwidth_bugfix`
- `all`

`all` runs every registered workload in `src/cpu_swe_benchmark/workloads.py`.

## Execution Model

Each concurrency point starts `N` mini-swe-agent workers once. Each worker gets an independent copy of the workload repo template and must fix, validate, and submit. The benchmark aggregates success, latency, model serving, throughput, and system metrics per workload/concurrency point.

## Server Profile Fields

Record these for every GPU server benchmark:

- hostname and GPU inventory (`nvidia-smi` when available)
- CPU and NUMA topology (`lscpu`)
- memory capacity (`free -h`)
- benchmark commit and model server version if known
- `BENCH_ROOT`, model endpoint, model name, API key source, metrics endpoint
- AMDuProfPcm path or alternative memory bandwidth collector

## Success Criteria

A run is successful only when mini-swe-agent submits and at least one executed command prints `VALIDATION_PASSED` after the requested pytest command passes.
