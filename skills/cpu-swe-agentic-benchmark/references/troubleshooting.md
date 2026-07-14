# Troubleshooting

## vLLM Connection Refused

Check whether the container is running and whether port 8000 is listening:

```bash
docker ps
ss -ltnp | grep ':8000'
```

Inspect the vLLM log before rerunning. Do not restart vLLM while a benchmark is still running.

## HTTP 500 or EngineDeadError

Inspect vLLM logs for CUDA OOM or EngineCore errors. If high concurrency causes CUDA OOM, lower `GPU_MEMORY_UTILIZATION`, reduce the concurrency point, or restart vLLM after collecting evidence.

## AMDuProfPcm Has Zero Bandwidth

Check `AMDUPROFPCM_SUDO_PASSWORD`, `amd_pcm.stdout.log`, and `amd_pcm.stderr.log`. Very short workloads can produce sparse samples; the memory workload is intentionally sustained to reduce this risk.

## Root Pytest Collects Results

Do not use root `pytest -q` in a dirty benchmark workspace with historical `results/`. Use:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## Interrupted Benchmark

If interrupted, stop orphaned benchmark and AMDuProfPcm processes before starting another run:

```bash
pgrep -af 'benchmark_latency.py|AMDuProfPcm'
```

Terminate only matching benchmark/sampler processes. Do not kill vLLM unless it is unhealthy or explicitly being restarted.
