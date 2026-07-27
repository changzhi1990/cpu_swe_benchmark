from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


AVT_NUMERIC_FIELDS = [
    "pid_count",
    "agent_cpu_count",
    "agent_logical_cpu_count",
    "agent_physical_core_count",
    "agent_eff_freq_avg_mhz",
    "agent_eff_freq_min_mhz",
    "agent_eff_freq_max_mhz",
    "agent_eff_freq_p50_mhz",
    "agent_eff_freq_p95_mhz",
    "agent_eff_freq_p99_mhz",
    "agent_freq_avg_mhz",
    "agent_c0_avg_percent",
]

COMMON_AVT_ALIASES = {
    "agent_eff_freq_avg_mhz": ("avg", "agent_eff_freq_avg_mhz"),
    "agent_eff_freq_min_mhz": ("min", "agent_eff_freq_min_mhz"),
    "agent_eff_freq_max_mhz": ("max", "agent_eff_freq_max_mhz"),
    "agent_eff_freq_p50_mhz": ("avg", "agent_eff_freq_p50_mhz"),
    "agent_eff_freq_p95_mhz": ("avg", "agent_eff_freq_p95_mhz"),
    "agent_eff_freq_p99_mhz": ("avg", "agent_eff_freq_p99_mhz"),
    "agent_freq_avg_mhz": ("avg", "agent_freq_avg_mhz"),
    "agent_c0_avg_percent": ("avg", "agent_c0_avg_percent"),
}

COMMON_FIELDS = [
    "runset_id",
    "run_id",
    "repeat",
    "workload",
    "concurrency",
    "status",
    "submitted_tasks",
    "successful_tasks",
    "failed_tasks",
    "timeout_tasks",
    "success_rate",
    "batch_wall_time_seconds",
    "throughput_successful_tasks_per_sec",
    "latency_p50",
    "latency_p90",
    "latency_p95",
    "latency_p99",
    "E2E_p90_seconds",
    "TTFT_p90",
    "TPOT_p90",
    "avg_llm_time_seconds_per_task",
    "avg_bash_time_seconds_per_task",
    "avg_model_calls_per_task",
    "avg_bash_calls_per_task",
    "started_at",
    "ended_at",
    "exit_code",
    "run_dir",
    "run_log",
    "agent_cpuset",
    "vllm_cpuset",
    "task_timeout",
]


@dataclass(frozen=True)
class StandardMetricsOutputs:
    cpu_metrics: Path
    gpu_metrics: Path
    vllm_metrics: Path
    global_metrics: Path


def _read_single_csv_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise ValueError(f"expected exactly one row in {path}, got {len(rows)}")
    return rows[0]


def _write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _finite_float(raw: str | None) -> float | None:
    if raw in {"", None}:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _values_for(rows: Iterable[dict[str, str]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = _finite_float(row.get(key))
        if value is not None:
            values.append(value)
    return values


def _format_avg(values: list[float]) -> str:
    return f"{(sum(values) / len(values)):.6f}" if values else "0.000000"


def _format_min(values: list[float]) -> str:
    return f"{min(values):.6f}" if values else "0.000000"


def _format_max(values: list[float]) -> str:
    return f"{max(values):.6f}" if values else "0.000000"


def _format_stat(values: list[float], stat: str) -> str:
    if stat == "avg":
        return _format_avg(values)
    if stat == "min":
        return _format_min(values)
    if stat == "max":
        return _format_max(values)
    raise ValueError(f"unknown statistic: {stat}")


def summarize_avt_aggregate_log(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"missing AVT aggregate log: {path}")
    rows = _read_avt_aggregate_rows(path)

    metrics: dict[str, str] = {
        "avt_sample_count": str(len(rows)),
        "avt_aggregate_freq_log": str(path),
    }
    for key in AVT_NUMERIC_FIELDS:
        values = _values_for(rows, key)
        metrics[f"avt_{key}_avg"] = _format_avg(values)
        metrics[f"avt_{key}_min"] = _format_min(values)
        metrics[f"avt_{key}_max"] = _format_max(values)

    for output_key, (stat, source_key) in COMMON_AVT_ALIASES.items():
        metrics[output_key] = _format_stat(_values_for(rows, source_key), stat)
    return metrics


def _read_avt_aggregate_rows(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return []
    first_token = lines[0].split(",", 1)[0]
    try:
        float(first_token)
        first_token_is_timestamp = True
    except ValueError:
        first_token_is_timestamp = False
    if "," in lines[0] and not first_token_is_timestamp and "=" not in first_token:
        with path.open(newline="", encoding="utf-8") as handle:
            return [
                row
                for row in csv.DictReader(handle)
                if not row.get("agent_logical_cpus", "").startswith("error:")
            ]
    rows: list[dict[str, str]] = []
    for line in lines:
        parts = line.strip().split(",")
        if not parts:
            continue
        row: dict[str, str] = {"timestamp": parts[0]}
        is_error = False
        for part in parts[1:]:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            if key.endswith("_error"):
                is_error = True
            row[key] = value
        if row and not is_error:
            rows.append(row)
    return rows


def _manifest_rows(runset_dir: Path) -> list[dict[str, str]]:
    manifest = runset_dir / "manifest.csv"
    if not manifest.exists():
        raise FileNotFoundError(f"missing manifest: {manifest}")
    with manifest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows = [_repair_legacy_cpuset_manifest_row(row) for row in rows]
    completed = [row for row in rows if row.get("status") == "completed"]
    return sorted(completed, key=lambda row: int(row["concurrency"]))


def _repair_legacy_cpuset_manifest_row(row: dict[str, str]) -> dict[str, str]:
    extra = row.get(None)
    if not extra:
        return row
    if (
        len(extra) == 2
        and row.get("agent_cpuset")
        and row.get("vllm_cpuset")
        and row.get("task_timeout")
    ):
        repaired = dict(row)
        repaired.pop(None, None)
        repaired["agent_cpuset"] = f"{row['agent_cpuset']},{row['vllm_cpuset']}"
        repaired["vllm_cpuset"] = f"{row['task_timeout']},{extra[0]}"
        repaired["task_timeout"] = extra[1]
        return repaired
    repaired = dict(row)
    repaired.pop(None, None)
    return repaired


def _aggregate_freq_log_for(row: dict[str, str]) -> Path:
    value = row.get("aggregate_freq_log") or row.get("cpu_freq_log")
    if not value:
        raise ValueError(f"manifest row has no aggregate frequency log: {row}")
    return Path(value)


def _per_core_freq_log_for(row: dict[str, str]) -> str:
    return row.get("per_core_freq_log", "")


def _common_context(row: dict[str, str]) -> dict[str, str]:
    run_dir = Path(row["run_dir"])
    summary = _read_single_csv_row(run_dir / "global_summary.csv")
    return {
        "runset_id": row.get("runset_id", ""),
        "run_id": row.get("run_id", ""),
        "repeat": row.get("repeat", ""),
        "workload": summary.get("workload", ""),
        "concurrency": summary.get("concurrency", row.get("concurrency", "")),
        "status": row.get("status", ""),
        "submitted_tasks": summary.get("submitted_tasks", ""),
        "successful_tasks": summary.get("successful_tasks", ""),
        "failed_tasks": summary.get("failed_tasks", ""),
        "timeout_tasks": summary.get("timeout_tasks", ""),
        "success_rate": summary.get("success_rate", ""),
        "batch_wall_time_seconds": summary.get("batch_wall_time_seconds", ""),
        "throughput_successful_tasks_per_sec": summary.get("throughput_successful_tasks_per_sec", ""),
        "latency_p50": summary.get("latency_p50", ""),
        "latency_p90": summary.get("latency_p90", ""),
        "latency_p95": summary.get("latency_p95", ""),
        "latency_p99": summary.get("latency_p99", ""),
        "E2E_p90_seconds": summary.get("E2E_p90_seconds", ""),
        "TTFT_p90": summary.get("TTFT_p90", ""),
        "TPOT_p90": summary.get("TPOT_p90", ""),
        "avg_llm_time_seconds_per_task": summary.get("avg_llm_time_seconds_per_task", ""),
        "avg_bash_time_seconds_per_task": summary.get("avg_bash_time_seconds_per_task", ""),
        "avg_model_calls_per_task": summary.get("avg_model_calls_per_task", ""),
        "avg_bash_calls_per_task": summary.get("avg_bash_calls_per_task", ""),
        "started_at": row.get("started_at", ""),
        "ended_at": row.get("ended_at", ""),
        "exit_code": row.get("exit_code", ""),
        "run_dir": str(run_dir),
        "run_log": row.get("run_log", ""),
        "agent_cpuset": row.get("agent_cpuset", ""),
        "vllm_cpuset": row.get("vllm_cpuset", ""),
        "task_timeout": row.get("task_timeout", ""),
    }


def _summary_row_for(row: dict[str, str]) -> dict[str, str]:
    return _read_single_csv_row(Path(row["run_dir"]) / "global_summary.csv")


def _without_common_fields(row: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in row.items() if key not in set(COMMON_FIELDS)}


def _fieldnames_for(rows: list[dict[str, str]], preferred_prefix: list[str]) -> list[str]:
    fieldnames = list(preferred_prefix)
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    return fieldnames


def _aggregate_source_csv(
    *,
    manifest_rows: list[dict[str, str]],
    source_name: str,
    output_path: Path,
) -> Path:
    rows = [
        {
            **_common_context(row),
            **_without_common_fields(_read_single_csv_row(Path(row["run_dir"]) / source_name)),
        }
        for row in manifest_rows
    ]
    fields = COMMON_FIELDS + [field for field in rows[0] if field not in COMMON_FIELDS] if rows else COMMON_FIELDS
    _write_csv(output_path, rows, fields)
    return output_path


def aggregate_standard_metrics(runset_dir: Path | str) -> StandardMetricsOutputs:
    runset_dir = Path(runset_dir)
    rows = _manifest_rows(runset_dir)

    cpu_rows: list[dict[str, str]] = []
    global_rows: list[dict[str, str]] = []
    for row in rows:
        run_dir = Path(row["run_dir"])
        summary_row = _summary_row_for(row)
        cpu_row = {
            **_common_context(row),
            **_without_common_fields(_read_single_csv_row(run_dir / "cpu_memory.csv")),
        }
        avt_row = summarize_avt_aggregate_log(_aggregate_freq_log_for(row))
        cpu_row.update(avt_row)
        cpu_row["avt_per_core_freq_log"] = _per_core_freq_log_for(row)
        cpu_rows.append(cpu_row)

        global_row = {
            **_common_context(row),
            **_without_common_fields(summary_row),
            **_without_common_fields(_read_single_csv_row(run_dir / "cpu_memory.csv")),
            **avt_row,
            "avt_per_core_freq_log": _per_core_freq_log_for(row),
            **_without_common_fields(_read_single_csv_row(run_dir / "gpu_metrics.csv")),
            **_without_common_fields(_read_single_csv_row(run_dir / "llm_serving.csv")),
        }
        global_rows.append(global_row)

    cpu_fields = _fieldnames_for(cpu_rows, COMMON_FIELDS)
    cpu_metrics = runset_dir / "cpu_metrics.csv"
    _write_csv(cpu_metrics, cpu_rows, cpu_fields)

    global_metrics = runset_dir / "global_metrics.csv"
    _write_csv(global_metrics, global_rows, _fieldnames_for(global_rows, COMMON_FIELDS))

    gpu_metrics = _aggregate_source_csv(
        manifest_rows=rows,
        source_name="gpu_metrics.csv",
        output_path=runset_dir / "gpu_metrics.csv",
    )
    vllm_metrics = _aggregate_source_csv(
        manifest_rows=rows,
        source_name="llm_serving.csv",
        output_path=runset_dir / "vllm_metrics.csv",
    )
    return StandardMetricsOutputs(
        cpu_metrics=cpu_metrics,
        gpu_metrics=gpu_metrics,
        vllm_metrics=vllm_metrics,
        global_metrics=global_metrics,
    )
