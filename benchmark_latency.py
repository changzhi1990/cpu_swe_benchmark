#!/usr/bin/env python3
"""CPU-centric mini-swe-agent latency benchmark.

This is the primary project entrypoint, intentionally shaped after
`cpu-centric-agentic-ai/mini-swe-agent/benchmark_latency.py`: a
`LatencyBenchmarker` owns model configuration, runs selected benchmark types,
and writes per-concurrency latency/throughput summaries.

The implementation is adapted to latest mini-swe-agent v2 and a local vLLM
OpenAI-compatible TP8 service.
"""

from __future__ import annotations

import argparse
import json
import sys
import timeit
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_swe_benchmark.runner import (  # noqa: E402
    parse_concurrency_levels,
    parse_endpoints,
    run_concurrency_point,
    write_global_csv,
)
from cpu_swe_benchmark.schemas import ConcurrencySummary, to_jsonable  # noqa: E402
from cpu_swe_benchmark.workloads import get_workload, parse_workload_list  # noqa: E402


class LatencyBenchmarker:
    """Run CPU-centric mini-swe-agent benchmarks and aggregate latency metrics."""

    def __init__(
        self,
        model_config: dict[str, Any],
        output_dir: str | Path = "benchmark_results",
        *,
        mini_swe_agent_src: str | Path = "/home/user/zhi/mini-swe-agent-latest/src",
        vllm_topology: str = "tp8",
        task_timeout_seconds: int = 600,
        command_timeout_seconds: int = 120,
        cpu_threads_per_worker: int = 1,
    ):
        self.model_config = model_config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mini_swe_agent_src = Path(mini_swe_agent_src)
        self.vllm_topology = vllm_topology
        self.task_timeout_seconds = task_timeout_seconds
        self.command_timeout_seconds = command_timeout_seconds
        self.cpu_threads_per_worker = cpu_threads_per_worker

    def run_sorting_benchmark(self, concurrency_levels: list[int]) -> list[ConcurrencySummary]:
        """Run the reference sorting benchmark across concurrency points."""
        return self.run_workloads(["sorting"], concurrency_levels)

    def run_workloads(self, workload_names: list[str], concurrency_levels: list[int]) -> list[ConcurrencySummary]:
        endpoints = parse_endpoints(self.model_config.get("base_url", "http://localhost:8000/v1"))
        model = self.model_config.get("model_name", "qwen2.5-coder-32b")
        api_key = self.model_config.get("api_key", "token-abc123")
        max_tokens = int(self.model_config.get("max_tokens", 2048))
        temperature = float(self.model_config.get("temperature", 0.0))
        summaries: list[ConcurrencySummary] = []

        for workload_name in workload_names:
            workload = get_workload(workload_name)
            for concurrency in concurrency_levels:
                print(f"[benchmark] workload={workload.name} concurrency={concurrency}")
                summary = run_concurrency_point(
                    workload=workload,
                    concurrency=concurrency,
                    endpoints=endpoints,
                    model=model,
                    api_key=api_key,
                    output_dir=self.output_dir,
                    mini_swe_agent_src=self.mini_swe_agent_src,
                    vllm_topology=self.vllm_topology,
                    task_timeout_seconds=self.task_timeout_seconds,
                    command_timeout_seconds=self.command_timeout_seconds,
                    cpu_threads_per_worker=self.cpu_threads_per_worker,
                    model_max_tokens=max_tokens,
                    model_temperature=temperature,
                )
                summaries.append(summary)
                print(
                    "[summary] "
                    f"success={summary.successful_tasks}/{summary.submitted_tasks} "
                    f"success_rate={summary.success_rate:.3f} "
                    f"throughput_success={summary.throughput_successful_tasks_per_sec:.4f}/s "
                    f"p50={summary.latency_seconds['p50']:.2f}s "
                    f"p90={summary.latency_seconds['p90']:.2f}s"
                )
        self._write_global_outputs(summaries)
        return summaries

    def _write_global_outputs(self, summaries: list[ConcurrencySummary]) -> None:
        csv_path = write_global_csv(summaries, self.output_dir)
        (self.output_dir / "global_summary.json").write_text(
            json.dumps([to_jsonable(summary) for summary in summaries], indent=2),
            encoding="utf-8",
        )
        print(f"[benchmark] wrote {csv_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark mini-swe-agent latency with local vLLM TP8.")
    parser.add_argument("--model-path", default="qwen2.5-coder-32b", help="Served vLLM model name")
    parser.add_argument("--base-url", default="http://localhost:8000/v1", help="Comma-separated vLLM endpoints")
    parser.add_argument("--api-key", default="token-abc123", help="Local vLLM API key")
    parser.add_argument("--max-tokens", type=int, default=2048, help="Max completion tokens per model call")
    parser.add_argument("--temperature", type=float, default=0.0, help="Model temperature")
    parser.add_argument("--output-dir", default="benchmark_results", help="Output directory")
    parser.add_argument("--mini-swe-agent-src", default="/home/user/zhi/mini-swe-agent-latest/src")
    parser.add_argument("--vllm-topology", default="tp8")
    parser.add_argument("--task-timeout", type=int, default=600)
    parser.add_argument("--command-timeout", type=int, default=120)
    parser.add_argument("--cpu-threads-per-worker", type=int, default=1)
    parser.add_argument(
        "--benchmark-type",
        choices=[
            "sorting",
            "fibonacci",
            "prime_numbers",
            "numerical_integration",
            "matmul",
            "lu_decomposition",
            "knn",
            "fft_convolution",
            "memory_bandwidth_utilization",
            "algorithm_lab_sorting_bugfix",
            "all",
        ],
        default="sorting",
    )
    parser.add_argument("--workloads", default="", help="Optional comma-separated workload list; overrides type")
    parser.add_argument("--concurrency-levels", default="1,2,4,8,16,32,64,128")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    start_time = timeit.default_timer()
    model_config = {
        "model_name": args.model_path,
        "base_url": args.base_url,
        "api_key": args.api_key,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
    }
    benchmarker = LatencyBenchmarker(
        model_config,
        args.output_dir,
        mini_swe_agent_src=args.mini_swe_agent_src,
        vllm_topology=args.vllm_topology,
        task_timeout_seconds=args.task_timeout,
        command_timeout_seconds=args.command_timeout,
        cpu_threads_per_worker=args.cpu_threads_per_worker,
    )
    concurrency_levels = parse_concurrency_levels(args.concurrency_levels)
    workload_spec = args.workloads or args.benchmark_type
    workloads = [workload.name for workload in parse_workload_list(workload_spec)]
    benchmarker.run_workloads(workloads, concurrency_levels)
    print(f"[benchmark] total elapsed: {timeit.default_timer() - start_time:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
