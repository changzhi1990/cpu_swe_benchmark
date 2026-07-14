from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any


METRIC_GROUP_SPECS: list[dict[str, Any]] = [
    {
        "key": "volume",
        "title": "Task Volume",
        "unit": "tasks",
        "metrics": [
            ("submitted_tasks", "Submitted"),
            ("successful_tasks", "Successful"),
            ("failed_tasks", "Failed"),
        ],
    },
    {
        "key": "success",
        "title": "Success Rate",
        "unit": "ratio",
        "metrics": [
            ("success_rate", "Success rate"),
        ],
    },
    {
        "key": "throughput",
        "title": "Throughput",
        "unit": "tasks/s",
        "metrics": [
            ("throughput_successful_tasks_per_sec", "Successful tasks/s"),
        ],
    },
    {
        "key": "latency",
        "title": "Latency",
        "unit": "seconds",
        "metrics": [
            ("latency_p50", "p50"),
            ("latency_p90", "p90"),
            ("latency_p95", "p95"),
            ("latency_p99", "p99"),
            ("batch_wall_time_seconds", "Batch wall"),
        ],
    },
    {
        "key": "timing",
        "title": "Timing Breakdown",
        "unit": "seconds/task",
        "metrics": [
            ("avg_llm_time_seconds_per_task", "LLM"),
            ("avg_bash_time_seconds_per_task", "Bash"),
        ],
    },
    {
        "key": "calls",
        "title": "Call Counts",
        "unit": "calls/task",
        "metrics": [
            ("avg_model_calls_per_task", "Model calls"),
            ("avg_bash_calls_per_task", "Bash calls"),
        ],
    },
    {
        "key": "system_cpu",
        "title": "CPU Utilization by Concurrency",
        "unit": "percent",
        "metrics": [
            ("cpu_util_avg_percent", "CPU avg"),
            ("cpu_util_p50_percent", "CPU p50"),
            ("cpu_util_p90_percent", "CPU p90"),
            ("cpu_util_max_percent", "CPU max"),
        ],
    },
    {
        "key": "system_gpu",
        "title": "GPU Utilization by Concurrency",
        "unit": "percent",
        "metrics": [
            ("gpu_util_avg_percent", "GPU avg"),
            ("gpu_util_p50_percent", "GPU p50"),
            ("gpu_util_p90_percent", "GPU p90"),
            ("gpu_util_max_percent", "GPU max"),
            ("gpu_memory_bandwidth_util_avg_percent", "GPU memory bandwidth avg"),
            ("gpu_memory_bandwidth_util_p90_percent", "GPU memory bandwidth p90"),
            ("gpu_memory_bandwidth_util_max_percent", "GPU memory bandwidth max"),
        ],
    },
    {
        "key": "system_memory",
        "title": "Memory by Concurrency",
        "unit": "percent",
        "metrics": [
            ("memory_used_avg_percent", "Memory avg"),
            ("memory_used_max_percent", "Memory max"),
            ("gpu_memory_used_avg_percent", "GPU memory avg"),
            ("gpu_memory_used_max_percent", "GPU memory max"),
        ],
    },
    {
        "key": "workload_cpu",
        "title": "Workload CPU Utilization",
        "unit": "percent",
        "metrics": [
            ("workload_cpu_util_avg_percent", "Workload CPU avg"),
            ("workload_cpu_util_p50_percent", "Workload CPU p50"),
            ("workload_cpu_util_p90_percent", "Workload CPU p90"),
            ("workload_cpu_util_max_percent", "Workload CPU max"),
        ],
    },
    {
        "key": "workload_gpu",
        "title": "Workload GPU Utilization",
        "unit": "percent",
        "metrics": [
            ("workload_gpu_util_avg_percent", "Workload GPU avg"),
            ("workload_gpu_util_p50_percent", "Workload GPU p50"),
            ("workload_gpu_util_p90_percent", "Workload GPU p90"),
            ("workload_gpu_util_max_percent", "Workload GPU max"),
            ("workload_gpu_memory_bandwidth_util_avg_percent", "Workload GPU memory bandwidth avg"),
            ("workload_gpu_memory_bandwidth_util_p90_percent", "Workload GPU memory bandwidth p90"),
            ("workload_gpu_memory_bandwidth_util_max_percent", "Workload GPU memory bandwidth max"),
        ],
    },
]


def _coerce(value: str) -> str | int | float:
    if value == "":
        return value
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def discover_runs(results_dir: Path = Path("results")) -> list[dict[str, Any]]:
    if not results_dir.exists():
        return []
    runs = []
    for csv_path in results_dir.glob("*/global_summary.csv"):
        run_dir = csv_path.parent
        stat = csv_path.stat()
        runs.append(
            {
                "name": run_dir.name,
                "path": str(run_dir),
                "global_summary_csv": str(csv_path),
                "modified_time": stat.st_mtime,
            }
        )
    runs.sort(key=lambda item: item["modified_time"], reverse=True)
    return runs


def load_business_summary(results_dir: Path = Path("results"), run: str | None = None) -> dict[str, Any]:
    runs = discover_runs(results_dir)
    if not runs:
        return {"timestamp": time.time(), "runs": [], "selected_run": None, "rows": [], "latest": None}
    selected = None
    if run:
        for candidate in runs:
            if run in {candidate["name"], candidate["path"]}:
                selected = candidate
                break
    selected = selected or runs[0]
    rows = []
    with Path(selected["global_summary_csv"]).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append({key: _coerce(value) for key, value in row.items()})
    latest = rows[-1] if rows else None
    return {
        "timestamp": time.time(),
        "runs": runs,
        "selected_run": selected,
        "rows": rows,
        "metric_groups": build_metric_groups(rows),
        "latest": latest,
    }


def build_metric_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = []
    for group_spec in METRIC_GROUP_SPECS:
        series = []
        for metric_key, label in group_spec["metrics"]:
            points = []
            for row in rows:
                x_value = row.get("concurrency")
                y_value = row.get(metric_key)
                if isinstance(x_value, (int, float)) and isinstance(y_value, (int, float)):
                    points.append({"x": x_value, "y": y_value})
            if points:
                series.append({"key": metric_key, "label": label, "points": points})
        groups.append(
            {
                "key": group_spec["key"],
                "title": group_spec["title"],
                "unit": group_spec["unit"],
                "series": series,
            }
        )
    return groups
