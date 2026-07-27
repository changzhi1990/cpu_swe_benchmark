# Metrics

Primary report fields:

- `workload`
- `concurrency`
- `E2E_p90_seconds`
- `TTFT_p90`
- `TPOT_p90`
- `success_rate`
- `run_results`

System-oriented report fields:

- `memory_bandwidth_total_p90_gbps`
- `memory_bandwidth_total_max_gbps`
- `memory_bandwidth_read_p90_gbps`
- `memory_bandwidth_read_max_gbps`
- `memory_bandwidth_write_p90_gbps`
- `memory_bandwidth_write_max_gbps`
- `cpu_util_p90_percent`
- `gpu_util_p90_percent`
- `throughput_successful_tasks_per_sec`

`run_results` should be derived from `successful_tasks`, `submitted_tasks`, and `failed_tasks`, for example `200/200 success, 0 failed`.

TTFT and TPOT are seconds. Memory bandwidth fields are GB/s from AMDuProfPcm output when available.

## Agentic Throughput And Efficiency Metrics

Report successful-work metrics for agentic workloads because raw model throughput can include failed or unsubmitted
agent trajectories. In standard CSV outputs, use `successful_agent_total_tokens_total` as the successful-token
numerator and `successful_tasks` as the successful-agent numerator.

- `successful_total_tokens / second`: successful-token throughput.

  ```text
  successful_agent_total_tokens_per_sec =
      successful_agent_total_tokens_total / batch_wall_time_seconds
  ```

- `successful_total_tokens / watt`: successful-token power efficiency.

  ```text
  successful_total_tokens / watt =
      successful_agent_total_tokens_total / average_power_watts
  ```

- `successful_agents / watt`: task-success power efficiency.

  ```text
  successful_agents / watt =
      successful_tasks / average_power_watts
  ```

For watt-normalized metrics, state the power source explicitly, for example average GPU power, CPU package power,
or average system power. The power denominator must be measured over the same batch window used for
`batch_wall_time_seconds`. For energy-normalized reporting, divide the same successful numerators by total joules
instead of average watts.

## Standard Runset Metrics Files

Every completed runset should expose one all-in-one metrics table plus three root-level domain views:

- `global_metrics.csv`
- `cpu_metrics.csv`
- `gpu_metrics.csv`
- `vllm_metrics.csv`

Each table must include shared run context fields: `runset_id`, `run_id`, `workload`, `concurrency`,
`status`, submitted/successful/failed/timeout task counts, `success_rate`, `E2E_p90_seconds`,
`TTFT_p90`, `TPOT_p90`, timestamps, exit code, run paths, CPU affinity, vLLM affinity, and task timeout.

`global_metrics.csv` merges shared run context, all general benchmark fields from `global_summary.csv`,
CPU and memory metrics, AVT effective-frequency metrics, GPU metrics, and vLLM serving metrics.

`cpu_metrics.csv` merges shared run context, each point's `cpu_memory.csv` row, and AVT
effective-frequency summaries from `cpu_freq/*.aggregate.csv`. It must include CPU utilization,
workload CPU utilization, memory usage,
memory bandwidth, AVT sample count, AVT frequency-log paths, effective-frequency avg/min/max/p50/p95/p99,
nominal frequency, and C0 residency.

`gpu_metrics.csv` merges shared run context and per-point `gpu_metrics.csv` rows.

`vllm_metrics.csv` merges shared run context and per-point `llm_serving.csv` rows.

Per-core AVT samples remain in `per_core_freq/*.per_core.csv`, and the Linux CPU to AVT
`Pkg/Die/CCD/PhysicalCore` mapping is stored in `linux_cpu_to_avt_mapping.csv`. These are raw
provenance logs referenced by `cpu_metrics.csv`; they are not the standard analysis tables.

Operational files such as `manifest.csv`, `summary_by_concurrency.csv`, and `aggregate_samples.csv`
may be present to support the runner, but downstream metric analysis should use `global_metrics.csv`
or one of the three domain metrics views.

## AVT CPU Mapping Rule

Do not treat `AMDCpuTopology` `Thread` as the Linux CPU number. Map Linux CPU IDs by using kernel topology:

1. Read `/sys/devices/system/cpu/cpuN/topology/physical_package_id`.
2. Read `/sys/devices/system/cpu/cpuN/topology/core_id`.
3. Match that package/core to `AMDCpuTopology` `Package/Core`.
4. Convert the matched `CCX/Core` to AVT `Pkg/Die/CCD/PhysicalCore` using local CCX core index.

For example, Linux CPU `10` maps to `Pkg:0, Die:0, CCD:0, PhysicalCore:10`, while
`Pkg:0, Die:0, CCD:4, PhysicalCore:4` maps to Linux CPUs `20,404` on the 5090 profile.
