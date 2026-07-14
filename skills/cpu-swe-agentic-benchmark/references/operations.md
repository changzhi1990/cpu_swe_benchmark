# Operations

All commands are parameterized for arbitrary GPU servers. Use defaults only on the known local benchmark server.

## Configure Server Profile

```bash
export BENCH_ROOT=/home/user/zhi/cpu_swe_benchmark
export MINI_SWE_AGENT_SRC=/home/user/zhi/mini-swe-agent-latest/src
export BASE_URL=http://localhost:8000/v1
export VLLM_URL=http://localhost:8000/v1
export MODEL=qwen2.5-coder-32b
export API_KEY=token-abc123
export DASHBOARD_HEALTH=http://localhost:8080/api/health
export RUN_LABEL=qwen32b_tp8
```

For another GPU server, set these to that server's paths and endpoints before running scripts.

## Start Model Server

If using the bundled local vLLM script on the default host:

```bash
cd "$BENCH_ROOT"
nohup bash scripts/start_vllm_tp8_qwen32b.sh > logs/vllm_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

For other GPU servers, start any OpenAI-compatible endpoint and set `BASE_URL`, `VLLM_URL`, `MODEL`, and `API_KEY` accordingly.

## Start Dashboard Metrics

```bash
cd "$BENCH_ROOT"
PORT=8080 nohup bash scripts/start_dashboard.sh > logs/dashboard_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

Health endpoint:

```bash
curl -sS "$DASHBOARD_HEALTH"
```

## Run Benchmark Directly

```bash
cd "$BENCH_ROOT"
python3 benchmark_latency.py \
  --base-url "$BASE_URL" \
  --api-key "$API_KEY" \
  --model-path "$MODEL" \
  --benchmark-type <algorithm_lab_sorting_bugfix|memory_lab_bandwidth_bugfix|all> \
  --concurrency-levels <comma-separated-levels> \
  --mini-swe-agent-src "$MINI_SWE_AGENT_SRC" \
  --output-dir results/<run-name>
```

## GitHub Sync

The active benchmark directory may not be the Git checkout. Use `GITHUB_CLONE` for commits and exclude benchmark artifacts. Confirm `git status --short --branch` before and after. Push with the available credential method; on networks blocking GitHub SSH port 22, use SSH over port 443:

```bash
git push ssh://git@ssh.github.com:443/changzhi1990/cpu_swe_benchmark.git main
```
