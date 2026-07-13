from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Any


class SystemHistory:
    def __init__(self, max_points: int = 120):
        self.max_points = max_points
        self._cpu: deque[dict[str, float]] = deque(maxlen=max_points)
        self._gpus: dict[int, deque[dict[str, float]]] = {}
        self._lock = Lock()

    def add_sample(self, metrics: dict[str, Any]) -> None:
        timestamp = float(metrics.get("timestamp", 0.0))
        cpu_util = metrics.get("cpu", {}).get("utilization_percent")
        with self._lock:
            if isinstance(cpu_util, (int, float)):
                self._cpu.append({"x": timestamp, "y": float(cpu_util)})
            for gpu in metrics.get("gpus", []):
                index = gpu.get("index")
                util = gpu.get("utilization_gpu_percent")
                if not isinstance(index, int) or not isinstance(util, (int, float)):
                    continue
                if index not in self._gpus:
                    self._gpus[index] = deque(maxlen=self.max_points)
                self._gpus[index].append({"x": timestamp, "y": float(util)})

    def to_payload(self) -> dict[str, Any]:
        with self._lock:
            return {
                "cpu": list(self._cpu),
                "gpus": [
                    {"index": index, "label": f"GPU {index}", "points": list(points)}
                    for index, points in sorted(self._gpus.items())
                ],
            }
