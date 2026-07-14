from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path
from typing import Any

from cpu_swe_benchmark.aggregate import mean, percentile


DCGM_FIELDS = "203,204,250,252,1005"


def _as_float(value: str) -> float | None:
    if value == "N/A":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _summary(values: list[float], prefix: str) -> dict[str, float]:
    return {
        f"{prefix}_avg_percent": mean(values),
        f"{prefix}_p50_percent": percentile(values, 50),
        f"{prefix}_p90_percent": percentile(values, 90),
        f"{prefix}_max_percent": max(values) if values else 0.0,
    }


def parse_dcgm_dmon_output(text: str) -> dict[str, Any]:
    gpu_util_values: list[float] = []
    mem_copy_util_values: list[float] = []
    dram_active_values: list[float] = []
    memory_used_values: list[float] = []
    sample_count = 0

    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 7 or parts[0] != "GPU":
            continue
        gpu_util = _as_float(parts[2])
        mem_copy_util = _as_float(parts[3])
        fb_total = _as_float(parts[4])
        fb_used = _as_float(parts[5])
        dram_active = _as_float(parts[6])
        if gpu_util is None or mem_copy_util is None or fb_total is None or fb_used is None:
            continue
        sample_count += 1
        gpu_util_values.append(gpu_util)
        mem_copy_util_values.append(mem_copy_util)
        if fb_total > 0:
            memory_used_values.append(round((fb_used / fb_total) * 100.0, 2))
        if dram_active is not None:
            dram_active_values.append(dram_active)

    bandwidth_values = dram_active_values or mem_copy_util_values
    bandwidth_source = "dcgm_drama" if dram_active_values else "dcgm_mcutl"
    metrics: dict[str, Any] = {
        "dcgm_sample_count": sample_count,
        "gpu_memory_bandwidth_util_source": bandwidth_source,
        "gpu_memory_used_avg_percent": mean(memory_used_values),
        "gpu_memory_used_max_percent": max(memory_used_values) if memory_used_values else 0.0,
    }
    metrics.update(_summary(gpu_util_values, "gpu_util"))
    metrics.update(_summary(bandwidth_values, "gpu_memory_bandwidth_util"))
    return metrics


class DCGMGPUSampler:
    def __init__(self, output_dir: Path, *, interval_ms: int = 1000, dcgmi_path: str = "dcgmi"):
        self.output_dir = output_dir
        self.interval_ms = interval_ms
        self.dcgmi_path = dcgmi_path
        self.process: subprocess.Popen[str] | None = None
        self.stdout_path = self.output_dir / "dcgm_dmon.stdout.log"
        self.stderr_path = self.output_dir / "dcgm_dmon.stderr.log"
        self._stdout_handle = None
        self._stderr_handle = None
        self.error: str | None = None

    def build_command(self) -> list[str]:
        return [self.dcgmi_path, "dmon", "-e", DCGM_FIELDS, "-d", str(self.interval_ms)]

    def start(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._stdout_handle = self.stdout_path.open("w", encoding="utf-8")
            self._stderr_handle = self.stderr_path.open("w", encoding="utf-8")
            self.process = subprocess.Popen(
                self.build_command(),
                stdout=self._stdout_handle,
                stderr=self._stderr_handle,
                text=True,
                start_new_session=True,
            )
        except Exception as exc:
            self.error = str(exc)
            self.process = None

    def stop(self) -> dict[str, Any]:
        if self.process is not None and self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGINT)
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGTERM)
                self.process.wait(timeout=5)
            except ProcessLookupError:
                pass
        if self._stdout_handle is not None:
            self._stdout_handle.close()
        if self._stderr_handle is not None:
            self._stderr_handle.close()

        stdout_text = self.stdout_path.read_text(encoding="utf-8", errors="ignore") if self.stdout_path.exists() else ""
        metrics = parse_dcgm_dmon_output(stdout_text)
        metrics["dcgm_stdout_log"] = str(self.stdout_path)
        metrics["dcgm_stderr_log"] = str(self.stderr_path)
        if metrics["dcgm_sample_count"] == 0:
            metrics["dcgm_error"] = self.error or "dcgmi dmon produced no parseable samples"
        return metrics
