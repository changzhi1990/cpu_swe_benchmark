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
