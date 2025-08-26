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
