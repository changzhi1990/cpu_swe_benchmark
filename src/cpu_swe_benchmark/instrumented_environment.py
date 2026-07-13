from __future__ import annotations

import time
from typing import Any

from cpu_swe_benchmark.system_sampler import SystemSampler


def is_workload_command(command: str) -> bool:
    normalized = " ".join(command.strip().split())
    if normalized.startswith("pytest ") or " pytest " in f" {normalized} ":
        return True
    return (
        "benchmark_" in normalized
        and ".py" in normalized
        and ("python benchmark_" in normalized or "python3 benchmark_" in normalized)
        and "cat >" not in normalized
    )


class InstrumentedEnvironment:
    def __init__(self, inner):
        self.inner = inner
        self.execution_log: list[dict[str, Any]] = []

    @property
    def config(self):
        return self.inner.config

    def execute(self, action: dict[str, Any], cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        command = action.get("command", "")
        start = time.time()
        workload_sampler = SystemSampler(interval_seconds=0.5) if is_workload_command(command) else None
        if workload_sampler is not None:
            workload_sampler.start()
        try:
            output = self.inner.execute(action, cwd=cwd, timeout=timeout)
        except Exception as exc:
            end = time.time()
            workload_metrics = workload_sampler.stop() if workload_sampler is not None else {}
            self.execution_log.append(
                {
                    "command": command,
                    "timestamp_start": start,
                    "timestamp_end": end,
                    "duration_seconds": end - start,
                    "returncode": None,
                    "stdout_size": 0,
                    "status": type(exc).__name__,
                    "output": "",
                    "output_preview": "",
                    "exception_info": str(exc),
                    "workload_system_metrics": workload_metrics,
                }
            )
            raise
        end = time.time()
        workload_metrics = workload_sampler.stop() if workload_sampler is not None else {}
        raw_output = output.get("output", "")
        self.execution_log.append(
            {
                "command": command,
                "timestamp_start": start,
                "timestamp_end": end,
                "duration_seconds": end - start,
                "returncode": output.get("returncode"),
                "stdout_size": len(raw_output),
                "status": "completed",
                "output": raw_output,
                "output_preview": raw_output[:1000],
                "exception_info": output.get("exception_info", ""),
                "workload_system_metrics": workload_metrics,
            }
        )
        return output

    def get_template_vars(self, **kwargs) -> dict[str, Any]:
        return self.inner.get_template_vars(**kwargs)

    def serialize(self) -> dict[str, Any]:
        data = self.inner.serialize()
        data.setdefault("info", {}).setdefault("benchmark", {})["environment_instrumented"] = True
        return data
