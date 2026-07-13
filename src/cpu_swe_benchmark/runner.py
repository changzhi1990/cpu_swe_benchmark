from __future__ import annotations

import concurrent.futures
import json
import time
from pathlib import Path

from cpu_swe_benchmark.aggregate import aggregate_runs
from cpu_swe_benchmark.schemas import ConcurrencySummary, RunResult, to_jsonable
from cpu_swe_benchmark.system_sampler import SystemSampler
from cpu_swe_benchmark.worker import WorkerConfig, run_worker
from cpu_swe_benchmark.workloads import Workload


def parse_concurrency_levels(spec: str) -> list[int]:
    try:
        levels = [int(part.strip()) for part in spec.split(",") if part.strip()]
    except ValueError as exc:
        raise ValueError(f"Invalid concurrency level list: {spec!r}") from exc
    if not levels:
        raise ValueError("At least one concurrency level is required")
    if any(level <= 0 for level in levels):
        raise ValueError("Concurrency levels must be positive")
    if len(set(levels)) != len(levels):
        raise ValueError("Concurrency levels must not contain duplicates")
    return levels


def parse_endpoints(spec: str) -> list[str]:
    endpoints = [part.strip().rstrip("/") for part in spec.split(",") if part.strip()]
    if not endpoints:
        raise ValueError("At least one endpoint is required")
    return endpoints


def endpoint_for_worker(worker_index: int, endpoints: list[str]) -> str:
    if not endpoints:
        raise ValueError("At least one endpoint is required")
    return endpoints[worker_index % len(endpoints)]


def run_concurrency_point(
    *,
    workload: Workload,
    concurrency: int,
    endpoints: list[str],
    model: str,
    api_key: str,
    output_dir: Path,
    mini_swe_agent_src: Path,
    vllm_topology: str,
    task_timeout_seconds: int,
    command_timeout_seconds: int,
    cpu_threads_per_worker: int,
    model_max_tokens: int,
    model_temperature: float,
) -> ConcurrencySummary:
    point_dir = output_dir / workload.name / f"c{concurrency:03d}"
    point_dir.mkdir(parents=True, exist_ok=True)
    runs_dir = point_dir / "runs"
    runs_dir.mkdir(exist_ok=True)
    batch_start = time.time()
    futures: list[concurrent.futures.Future[RunResult]] = []
    results: list[RunResult] = []
    sampler = SystemSampler(interval_seconds=1.0)
    sampler.start()

    try:
        with concurrent.futures.ProcessPoolExecutor(max_workers=concurrency) as pool:
            for worker_index in range(concurrency):
                run_id = f"{workload.name}_c{concurrency:03d}_w{worker_index:03d}"
                config = WorkerConfig(
                    run_id=run_id,
                    worker_index=worker_index,
                    workload=workload,
                    concurrency=concurrency,
                    endpoint=endpoint_for_worker(worker_index, endpoints),
                    model=model,
                    api_key=api_key,
                    run_dir=runs_dir / run_id,
                    mini_swe_agent_src=mini_swe_agent_src,
                    task_timeout_seconds=task_timeout_seconds,
                    command_timeout_seconds=command_timeout_seconds,
                    cpu_threads_per_worker=cpu_threads_per_worker,
                    model_max_tokens=model_max_tokens,
                    model_temperature=model_temperature,
                )
                futures.append(pool.submit(run_worker, config))
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
    finally:
        system_metrics = sampler.stop()

    batch_wall = time.time() - batch_start
    results.sort(key=lambda run: run.run_id)
    summary = aggregate_runs(
        results,
        workload=workload.name,
        concurrency=concurrency,
        model=model,
        base_url=",".join(endpoints),
        vllm_topology=vllm_topology,
        batch_wall_time_seconds=batch_wall,
        waves=1,
        system_metrics=system_metrics,
    )
    (point_dir / "summary.json").write_text(json.dumps(to_jsonable(summary), indent=2), encoding="utf-8")
    with (point_dir / "runs.jsonl").open("w", encoding="utf-8") as handle:
        for run in results:
            handle.write(json.dumps(to_jsonable(run)) + "\n")
    return summary


def write_global_csv(summaries: list[ConcurrencySummary], output_dir: Path) -> Path:
    path = output_dir / "global_summary.csv"
    headers = [
        "workload",
        "concurrency",
        "submitted_tasks",
        "successful_tasks",
        "failed_tasks",
        "success_rate",
        "batch_wall_time_seconds",
        "throughput_successful_tasks_per_sec",
        "latency_p50",
        "latency_p90",
        "latency_p95",
        "latency_p99",
        "avg_llm_time_seconds_per_task",
        "avg_bash_time_seconds_per_task",
        "avg_model_calls_per_task",
        "avg_bash_calls_per_task",
        "cpu_util_avg_percent",
        "cpu_util_p50_percent",
        "cpu_util_p90_percent",
        "cpu_util_max_percent",
        "memory_used_avg_percent",
        "memory_used_max_percent",
        "gpu_util_avg_percent",
        "gpu_util_p50_percent",
        "gpu_util_p90_percent",
        "gpu_util_max_percent",
        "gpu_memory_used_avg_percent",
        "gpu_memory_used_max_percent",
        "workload_cpu_util_avg_percent",
        "workload_cpu_util_p50_percent",
        "workload_cpu_util_p90_percent",
        "workload_cpu_util_max_percent",
        "workload_memory_used_avg_percent",
        "workload_memory_used_max_percent",
        "workload_gpu_util_avg_percent",
        "workload_gpu_util_p50_percent",
        "workload_gpu_util_p90_percent",
        "workload_gpu_util_max_percent",
        "workload_gpu_memory_used_avg_percent",
        "workload_gpu_memory_used_max_percent",
    ]
    lines = [",".join(headers)]
    for summary in summaries:
        row = [
            summary.workload,
            str(summary.concurrency),
            str(summary.submitted_tasks),
            str(summary.successful_tasks),
            str(summary.failed_tasks),
            f"{summary.success_rate:.6f}",
            f"{summary.batch_wall_time_seconds:.6f}",
            f"{summary.throughput_successful_tasks_per_sec:.6f}",
            f"{summary.latency_seconds['p50']:.6f}",
            f"{summary.latency_seconds['p90']:.6f}",
            f"{summary.latency_seconds['p95']:.6f}",
            f"{summary.latency_seconds['p99']:.6f}",
            f"{summary.avg_llm_time_seconds_per_task:.6f}",
            f"{summary.avg_bash_time_seconds_per_task:.6f}",
            f"{summary.avg_model_calls_per_task:.6f}",
            f"{summary.avg_bash_calls_per_task:.6f}",
            f"{summary.system_metrics.get('cpu_util_avg_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('cpu_util_p50_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('cpu_util_p90_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('cpu_util_max_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('memory_used_avg_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('memory_used_max_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('gpu_util_avg_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('gpu_util_p50_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('gpu_util_p90_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('gpu_util_max_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('gpu_memory_used_avg_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('gpu_memory_used_max_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('workload_cpu_util_avg_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('workload_cpu_util_p50_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('workload_cpu_util_p90_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('workload_cpu_util_max_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('workload_memory_used_avg_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('workload_memory_used_max_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('workload_gpu_util_avg_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('workload_gpu_util_p50_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('workload_gpu_util_p90_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('workload_gpu_util_max_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('workload_gpu_memory_used_avg_percent', 0.0):.6f}",
            f"{summary.system_metrics.get('workload_gpu_memory_used_max_percent', 0.0):.6f}",
        ]
        lines.append(",".join(row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
