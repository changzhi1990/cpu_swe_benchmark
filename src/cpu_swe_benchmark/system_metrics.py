from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any


def _cpu_fields(line: str) -> list[int]:
    parts = line.split()
    if not parts or parts[0] != "cpu":
        raise ValueError("expected aggregate cpu line")
    return [int(value) for value in parts[1:]]


def parse_cpu_utilization(previous: str, current: str) -> float:
    prev = _cpu_fields(previous)
    curr = _cpu_fields(current)
    prev_idle = prev[3] + (prev[4] if len(prev) > 4 else 0)
    curr_idle = curr[3] + (curr[4] if len(curr) > 4 else 0)
    prev_total = sum(prev)
    curr_total = sum(curr)
    total_delta = curr_total - prev_total
    idle_delta = curr_idle - prev_idle
    if total_delta <= 0:
        return 0.0
    return round(max(0.0, min(100.0, (1.0 - idle_delta / total_delta) * 100.0)), 2)


def parse_loadavg(text: str) -> dict[str, float]:
    parts = text.split()
    return {
        "load_1m": float(parts[0]),
        "load_5m": float(parts[1]),
        "load_15m": float(parts[2]),
    }


def parse_meminfo(text: str) -> dict[str, float | int]:
    values: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        amount = rest.strip().split()[0]
        if amount.isdigit():
            values[key] = int(amount) * 1024
    total = values.get("MemTotal", 0)
    available = values.get("MemAvailable", 0)
    used = max(0, total - available)
    return {
        "total_bytes": total,
        "available_bytes": available,
        "used_bytes": used,
        "used_percent": round((used / total) * 100.0, 2) if total else 0.0,
    }


def read_cpu_utilization(proc_stat: Path = Path("/proc/stat")) -> float:
    previous = proc_stat.read_text(encoding="utf-8").splitlines()[0]
    time.sleep(0.1)
    current = proc_stat.read_text(encoding="utf-8").splitlines()[0]
    return parse_cpu_utilization(previous, current)


def read_gpu_metrics() -> list[dict[str, Any]]:
    query = "index,name,memory.used,memory.total,utilization.gpu,utilization.memory"
    try:
        result = subprocess.run(
            ["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"],
            text=True,
            capture_output=True,
            timeout=5,
            check=True,
        )
    except Exception as exc:
        return [{"error": str(exc)}]
    gpus = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 6:
            continue
        index, name, mem_used, mem_total, util, memory_bandwidth_util = parts
        total = float(mem_total)
        used = float(mem_used)
        gpus.append(
            {
                "index": int(index),
                "name": name,
                "memory_used_mib": used,
                "memory_total_mib": total,
                "memory_used_percent": round((used / total) * 100.0, 2) if total else 0.0,
                "utilization_gpu_percent": float(util),
                "memory_bandwidth_util_percent": float(memory_bandwidth_util),
            }
        )
    return gpus


def read_container_status(container_name: str = "vllm-qwen25-coder-32b-tp8") -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Status}}", container_name],
            text=True,
            capture_output=True,
            timeout=5,
            check=True,
        )
        return {"name": container_name, "status": result.stdout.strip()}
    except Exception as exc:
        return {"name": container_name, "status": "unknown", "error": str(exc)}


def read_system_metrics() -> dict[str, Any]:
    return {
        "timestamp": time.time(),
        "cpu": {"utilization_percent": read_cpu_utilization()},
        "load": parse_loadavg(Path("/proc/loadavg").read_text(encoding="utf-8")),
        "memory": parse_meminfo(Path("/proc/meminfo").read_text(encoding="utf-8")),
        "gpus": read_gpu_metrics(),
        "vllm_container": read_container_status(),
    }


def read_basic_system_metrics() -> dict[str, Any]:
    return {
        "timestamp": time.time(),
        "cpu": {"utilization_percent": read_cpu_utilization()},
        "load": parse_loadavg(Path("/proc/loadavg").read_text(encoding="utf-8")),
        "memory": parse_meminfo(Path("/proc/meminfo").read_text(encoding="utf-8")),
    }
