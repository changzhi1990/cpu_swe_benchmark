from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ModelCall:
    call_number: int
    timestamp_start: float
    timestamp_end: float
    duration_seconds: float
    ttft_seconds: float | None = None
    tpot_seconds: float | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    status: str = "completed"
    error: str | None = None


@dataclass
class CommandExecution:
    command: str
    timestamp_start: float
    timestamp_end: float
    duration_seconds: float
    returncode: int | None
    stdout_size: int
    status: str
    output_preview: str = ""
    exception_info: str = ""


@dataclass
class RunResult:
    run_id: str
    workload: str
    concurrency: int
    status: str
    exit_status: str
    total_wall_time_seconds: float
    llm_time_total_seconds: float
    bash_time_total_seconds: float
    model_calls: int
    bash_calls: int
    validation_passed: bool
    endpoint: str
    trajectory_path: str | None
    error: str | None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    workload_system_metrics: dict[str, float] = field(default_factory=dict)
    workspace: str | None = None
    task_timeout_seconds: int = 600
    command_timeout_seconds: int = 120
    model_call_log: list[dict[str, Any]] = field(default_factory=list)
    bash_execution_log: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ConcurrencySummary:
    workload: str
    concurrency: int
    waves: int
    model: str
    endpoint: str
    vllm_topology: str
    submitted_tasks: int
    completed_tasks: int
    successful_tasks: int
    failed_tasks: int
    timeout_tasks: int
    success_rate: float
    completion_rate: float
    batch_wall_time_seconds: float
    throughput_submitted_tasks_per_sec: float
    throughput_completed_tasks_per_sec: float
    throughput_successful_tasks_per_sec: float
    latency_seconds: dict[str, float]
    avg_model_calls_per_task: float
    avg_bash_calls_per_task: float
    avg_llm_time_seconds_per_task: float
    avg_bash_time_seconds_per_task: float
    avg_framework_overhead_seconds_per_task: float
    model_serving_seconds: dict[str, float] = field(default_factory=dict)
    system_metrics: dict[str, float] = field(default_factory=dict)
    runs: list[dict[str, Any]] = field(default_factory=list)


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return {k: to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    return value
