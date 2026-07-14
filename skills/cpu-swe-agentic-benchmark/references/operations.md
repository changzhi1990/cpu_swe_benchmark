# Operations

## Start vLLM

```bash
cd /home/user/zhi/cpu_swe_benchmark
bash scripts/start_vllm_tp8_qwen32b.sh
```

Run under `nohup` for long benchmark sessions and keep the log.

## Start Dashboard Metrics

```bash
cd /home/user/zhi/cpu_swe_benchmark
PORT=8080 bash scripts/start_dashboard.sh
```

Health endpoint:

```bash
curl -sS http://localhost:8080/api/health
```

## Run Benchmark Directly

```bash
python3 benchmark_latency.py   --base-url http://localhost:8000/v1   --api-key token-abc123   --model-path qwen2.5-coder-32b   --benchmark-type <algorithm_lab_sorting_bugfix|memory_lab_bandwidth_bugfix|all>   --concurrency-levels <comma-separated-levels>   --mini-swe-agent-src /home/user/zhi/mini-swe-agent-latest/src   --output-dir results/<run-name>
```

## GitHub Sync

The active benchmark directory is not necessarily the Git repository. Sync source changes into `/home/user/zhi/cpu_swe_benchmark_github`, excluding benchmark artifacts, then commit and push to `origin main`. Confirm `git status --short --branch` before and after.
