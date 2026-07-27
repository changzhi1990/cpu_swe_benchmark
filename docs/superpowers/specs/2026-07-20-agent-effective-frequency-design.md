# Agent Effective Frequency Design

## Goal

Run `algorithm_lab_sorting_bugfix` at concurrency levels `1,2,4,8,16,32,64,128,180` and report AVT effective frequency for the physical cores currently running benchmark agent processes, not whole-machine average CPU frequency.

## Metric Definition

Each sampler tick identifies the current benchmark process tree by matching processes whose command line contains `benchmark_latency.py`, then adding all descendants. For each matched PID, the sampler reads `/proc/<pid>/stat` field 39, the current Linux CPU number. It maps Linux CPU numbers through `AMDCpuTopology`, then reads `/opt/AMD/AVT/AVTCMD -module pmm "get_cstates()"` and uses the matching `EffFreq(GHz)` per physical core.

The per-sample agent metric is computed over that deduplicated CPU set:

- `agent_cpu_count`
- `agent_eff_freq_avg_mhz`
- `agent_eff_freq_min_mhz`
- `agent_eff_freq_max_mhz`
- `agent_eff_freq_p50_mhz`
- `agent_eff_freq_p95_mhz`
- `agent_eff_freq_p99_mhz`
- `agent_c0_avg_percent`

Samples with `agent_cpu_count=0` are ignored when producing run-level agent frequency summaries, because the frequency logger starts before the benchmark process appears and can outlive it briefly during shutdown.

## Files

- `src/cpu_swe_benchmark/cpu_frequency.py`: add `/proc` parsing helpers and agent CPU frequency summary functions.
- `tests/test_cpu_frequency.py`: cover CPU-info parsing, `/proc/<pid>/stat` parsing, process-tree filtering, and log aggregation.
- `scripts/run_agent_effective_freq_sweep.sh`: run the requested concurrency sweep and emit `aggregate_samples.csv` and `summary_by_concurrency.csv` with only `agent_cpu_*` frequency columns.
- `tests/test_scripts.py`: verify the new sweep script uses the requested workload, concurrency list, and agent frequency fields.

## Non-Goals

- Do not change the benchmark workload prompt or validation logic.
- Do not change LLM serving settings.
- Do not use `/proc/cpuinfo` MHz as the requested effective-frequency metric.
- Do not average idle or unrelated machine CPUs into the requested metric.

## Verification

Run focused tests:

```bash
python3 -m pytest tests/test_cpu_frequency.py tests/test_scripts.py
```

After tests pass, run the sweep script when the vLLM and dashboard services are healthy:

```bash
bash scripts/run_agent_effective_freq_sweep.sh
```
