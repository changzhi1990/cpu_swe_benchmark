from __future__ import annotations

import argparse
import json
from pathlib import Path

from cpu_swe_benchmark.runner import (
    parse_concurrency_levels,
    parse_endpoints,
    run_concurrency_point,
    write_global_csv,
)
from cpu_swe_benchmark.schemas import to_jsonable
from cpu_swe_benchmark.workloads import parse_workload_list


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CPU-centric latency and throughput benchmark for mini-swe-agent with vLLM TP8."
    )
    parser.add_argument("--base-url", default="http://localhost:8000/v1", help="Comma-separated vLLM /v1 endpoints")
    parser.add_argument("--api-key", default="token-abc123", help="vLLM API key")
    parser.add_argument("--model", default="qwen2.5-coder-32b", help="Served model name")
    parser.add_argument("--vllm-topology", default="tp8", help="Topology label written to results")
    parser.add_argument("--workloads", default="sorting", help="Comma-separated workload names, or 'all'")
    parser.add_argument(
        "--concurrency-levels",
        default="1,2,4,8,16,32,64,128",
        help="Comma-separated agent concurrency points",
    )
    parser.add_argument("--output-dir", default="results/qwen32b_tp8_sorting_quick", help="Result directory")
    parser.add_argument(
        "--mini-swe-agent-src",
        default="/home/user/zhi/mini-swe-agent-latest/src",
        help="Path to latest mini-swe-agent src directory",
    )
    parser.add_argument("--task-timeout", type=int, default=600, help="Per-agent wall-clock timeout in seconds")
    parser.add_argument("--command-timeout", type=int, default=120, help="Per-command timeout in seconds")
    parser.add_argument("--cpu-threads-per-worker", type=int, default=1, help="OMP/MKL/OpenBLAS threads per worker")
    parser.add_argument("--model-max-tokens", type=int, default=2048, help="Max completion tokens per model call")
    parser.add_argument("--temperature", type=float, default=0.0, help="Model temperature")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    endpoints = parse_endpoints(args.base_url)
    concurrency_levels = parse_concurrency_levels(args.concurrency_levels)
    workloads = parse_workload_list(args.workloads)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    mini_swe_agent_src = Path(args.mini_swe_agent_src)
    if not mini_swe_agent_src.exists():
        raise SystemExit(f"mini-swe-agent src path does not exist: {mini_swe_agent_src}")

    summaries = []
    for workload in workloads:
        for concurrency in concurrency_levels:
            print(f"[benchmark] workload={workload.name} concurrency={concurrency}")
            summary = run_concurrency_point(
                workload=workload,
                concurrency=concurrency,
                endpoints=endpoints,
                model=args.model,
                api_key=args.api_key,
                output_dir=output_dir,
                mini_swe_agent_src=mini_swe_agent_src,
                vllm_topology=args.vllm_topology,
                task_timeout_seconds=args.task_timeout,
                command_timeout_seconds=args.command_timeout,
                cpu_threads_per_worker=args.cpu_threads_per_worker,
                model_max_tokens=args.model_max_tokens,
                model_temperature=args.temperature,
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

    csv_path = write_global_csv(summaries, output_dir)
    (output_dir / "global_summary.json").write_text(
        json.dumps([to_jsonable(summary) for summary in summaries], indent=2),
        encoding="utf-8",
    )
    print(f"[benchmark] wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
