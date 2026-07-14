# Troubleshooting

## Model Endpoint Connection Refused

Check whether the model server is running and whether the configured endpoint is reachable:

```bash
ss -ltnp | grep ':8000'
curl -sS -m 5 -H "Authorization: Bearer $API_KEY" "$VLLM_URL/models"
```

For non-vLLM servers, use the equivalent OpenAI-compatible models endpoint.

## HTTP 500 or EngineDeadError

Inspect model server logs for CUDA OOM or engine errors. If high concurrency causes CUDA OOM, lower GPU memory utilization, reduce the concurrency point, or restart the model server after collecting evidence. Do not blindly rerun.

## AMDuProfPcm Has Zero Bandwidth

Check `AMDUPROFPCM_SUDO_PASSWORD`, `amd_pcm.stdout.log`, and `amd_pcm.stderr.log`. If a GPU server lacks AMDuProfPcm, report memory bandwidth fields as unavailable and keep the rest of the benchmark metrics.

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

Terminate only matching benchmark/sampler processes. Do not kill the model server unless it is unhealthy or explicitly being restarted.

## GitHub Push Prompts for HTTPS Username

Check credential helper, `.git-credentials`, `.netrc`, `gh`, and SSH. If SSH to `github.com:22` times out but the key is valid, test SSH-over-443:

```bash
ssh -T -p 443 git@ssh.github.com
```

Then push with `ssh://git@ssh.github.com:443/<owner>/<repo>.git`.
