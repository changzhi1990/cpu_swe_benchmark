from __future__ import annotations

import math

from cpu_swe_benchmark.schemas import ConcurrencySummary, RunResult, to_jsonable


COMPLETED_STATUSES = {"success", "validation_failed", "not_submitted"}


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil((pct / 100.0) * len(ordered)))
    return ordered[min(rank - 1, len(ordered) - 1)]


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def model_call_values(runs: list[RunResult], key: str) -> list[float]:
    values: list[float] = []
    for run in runs:
        for call in run.model_call_log:
            if call.get("status") != "completed":
                continue
            value = call.get(key)
            if isinstance(value, (int, float)):
                values.append(float(value))
    return values


def model_call_token_totals(runs: list[RunResult]) -> tuple[int, int, int]:
    input_tokens = 0
    output_tokens = 0
    for run in runs:
        for call in run.model_call_log:
            if call.get("status") != "completed":
                continue
            prompt_tokens = int(call.get("prompt_tokens") or 0)
            completion_tokens = int(call.get("completion_tokens") or 0)
            input_tokens += prompt_tokens
            output_tokens += completion_tokens
    return input_tokens, output_tokens, input_tokens + output_tokens


def aggregate_runs(
    runs: list[RunResult],
    *,
    workload: str,
    concurrency: int,
    model: str,
    base_url: str,
    vllm_topology: str,
    batch_wall_time_seconds: float,
    waves: int = 1,
    system_metrics: dict[str, float] | None = None,
) -> ConcurrencySummary:
    submitted = len(runs)
    successful = sum(1 for run in runs if run.status == "success")
    completed = sum(1 for run in runs if run.status in COMPLETED_STATUSES)
    timeout = sum(1 for run in runs if run.status == "timeout")
    failed = submitted - successful
    latencies = [run.total_wall_time_seconds for run in runs]
    llm_times = [run.llm_time_total_seconds for run in runs]
    bash_times = [run.bash_time_total_seconds for run in runs]
    ttft_values = model_call_values(runs, "ttft_seconds")
    tpot_values = model_call_values(runs, "tpot_seconds")
    input_tokens_total, output_tokens_total, total_tokens_total = model_call_token_totals(runs)
    framework_times = [
        max(0.0, run.total_wall_time_seconds - run.llm_time_total_seconds - run.bash_time_total_seconds)
        for run in runs
    ]
    workload_metric_keys = sorted({key for run in runs for key in run.workload_system_metrics})
    workload_system_metrics = {
        key: mean([float(run.workload_system_metrics[key]) for run in runs if key in run.workload_system_metrics])
        for key in workload_metric_keys
    }
    merged_system_metrics = dict(system_metrics or {})
    merged_system_metrics.update(workload_system_metrics)
    safe_wall = batch_wall_time_seconds if batch_wall_time_seconds > 0 else 0.0

    def rate(count: int) -> float:
        return count / safe_wall if safe_wall else 0.0

    return ConcurrencySummary(
        workload=workload,
        concurrency=concurrency,
        waves=waves,
        model=model,
        endpoint=base_url,
        vllm_topology=vllm_topology,
        submitted_tasks=submitted,
        completed_tasks=completed,
        successful_tasks=successful,
        failed_tasks=failed,
        timeout_tasks=timeout,
        success_rate=successful / submitted if submitted else 0.0,
        completion_rate=completed / submitted if submitted else 0.0,
        batch_wall_time_seconds=batch_wall_time_seconds,
        throughput_submitted_tasks_per_sec=rate(submitted),
        throughput_completed_tasks_per_sec=rate(completed),
        throughput_successful_tasks_per_sec=rate(successful),
        latency_seconds={
            "mean": mean(latencies),
            "p50": percentile(latencies, 50),
            "p90": percentile(latencies, 90),
            "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99),
            "min": min(latencies) if latencies else 0.0,
            "max": max(latencies) if latencies else 0.0,
        },
        avg_model_calls_per_task=mean([float(run.model_calls) for run in runs]),
        avg_bash_calls_per_task=mean([float(run.bash_calls) for run in runs]),
        avg_llm_time_seconds_per_task=mean(llm_times),
        avg_bash_time_seconds_per_task=mean(bash_times),
        avg_framework_overhead_seconds_per_task=mean(framework_times),
        llm_input_tokens_total=input_tokens_total,
        llm_output_tokens_total=output_tokens_total,
        llm_total_tokens_total=total_tokens_total,
        llm_input_tokens_per_sec=rate(input_tokens_total),
        llm_output_tokens_per_sec=rate(output_tokens_total),
        llm_total_tokens_per_sec=rate(total_tokens_total),
        avg_input_tokens_per_task=input_tokens_total / submitted if submitted else 0.0,
        avg_output_tokens_per_task=output_tokens_total / submitted if submitted else 0.0,
        avg_total_tokens_per_task=total_tokens_total / submitted if submitted else 0.0,
        model_serving_seconds={
            "ttft_p50": percentile(ttft_values, 50),
            "ttft_p90": percentile(ttft_values, 90),
            "tpot_p50": percentile(tpot_values, 50),
            "tpot_p90": percentile(tpot_values, 90),
        },
        system_metrics=merged_system_metrics,
        runs=[to_jsonable(run) for run in runs],
    )
