from __future__ import annotations

import threading
import time
from typing import Any

from cpu_swe_benchmark.aggregate import mean, percentile
from cpu_swe_benchmark.system_metrics import read_system_metrics


def _numeric(values: list[Any]) -> list[float]:
    return [float(value) for value in values if isinstance(value, (int, float))]


def summarize_system_samples(samples: list[dict[str, Any]], prefix: str = "") -> dict[str, float]:
    cpu_values = _numeric([sample.get("cpu", {}).get("utilization_percent") for sample in samples])
    memory_values = _numeric([sample.get("memory", {}).get("used_percent") for sample in samples])
    gpu_util_values = []
    gpu_memory_values = []
    for sample in samples:
        for gpu in sample.get("gpus", []):
            gpu_util_values.extend(_numeric([gpu.get("utilization_gpu_percent")]))
            gpu_memory_values.extend(_numeric([gpu.get("memory_used_percent")]))
    return {
        f"{prefix}cpu_util_avg_percent": mean(cpu_values),
        f"{prefix}cpu_util_p50_percent": percentile(cpu_values, 50),
        f"{prefix}cpu_util_p90_percent": percentile(cpu_values, 90),
        f"{prefix}cpu_util_max_percent": max(cpu_values) if cpu_values else 0.0,
        f"{prefix}memory_used_avg_percent": mean(memory_values),
        f"{prefix}memory_used_max_percent": max(memory_values) if memory_values else 0.0,
        f"{prefix}gpu_util_avg_percent": mean(gpu_util_values),
        f"{prefix}gpu_util_p50_percent": percentile(gpu_util_values, 50),
        f"{prefix}gpu_util_p90_percent": percentile(gpu_util_values, 90),
        f"{prefix}gpu_util_max_percent": max(gpu_util_values) if gpu_util_values else 0.0,
        f"{prefix}gpu_memory_used_avg_percent": mean(gpu_memory_values),
        f"{prefix}gpu_memory_used_max_percent": max(gpu_memory_values) if gpu_memory_values else 0.0,
    }


class SystemSampler:
    def __init__(self, interval_seconds: float = 1.0):
        self.interval_seconds = interval_seconds
        self.samples: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, float]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(2.0, self.interval_seconds * 2))
        summary = summarize_system_samples(self.samples)
        summary["_samples"] = list(self.samples)
        return summary

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.samples.append(read_system_metrics())
            except Exception as exc:
                self.samples.append({"error": str(exc), "timestamp": time.time()})
            self._stop.wait(self.interval_seconds)
