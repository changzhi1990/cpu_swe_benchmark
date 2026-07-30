from __future__ import annotations

import csv
import os
import re
import signal
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from cpu_swe_benchmark.aggregate import percentile


DEFAULT_AMDUPROFPCM_PATH = Path("/home/user/zhi/AMDuProf_Nda_Linux_x64_5.0.1479/bin/AMDuProfPcm")
SUDO_PASSWORD_ENV = "AMDUPROFPCM_SUDO_PASSWORD"
INTEL_PERF_EVENTS = [
    "uncore_imc/cas_count_read_sch0/",
    "uncore_imc/cas_count_write_sch0/",
    "uncore_imc/cas_count_read_sch1/",
    "uncore_imc/cas_count_write_sch1/",
]


def build_amd_pcm_command(pcm_path: Path, output_dir: Path) -> list[str]:
    return [
        str(pcm_path),
        "top",
        "--msr",
        "-r",
        "-m",
        "memory",
        "-a",
        "-I",
        "1000",
    ]


def build_intel_perf_memory_command(perf_path: str = "perf") -> list[str]:
    return [perf_path, "stat", "-a", "-I", "1000", "-e", ",".join(INTEL_PERF_EVENTS)]


def _has_intel_uncore_imc_events() -> bool:
    return any(Path("/sys/devices").glob("uncore_imc_*/events/cas_count_read_sch0"))


def _empty_memory_bandwidth_metrics() -> dict[str, float]:
    return {
        "memory_bandwidth_total_p90_gbps": 0.0,
        "memory_bandwidth_total_max_gbps": 0.0,
        "memory_bandwidth_read_p90_gbps": 0.0,
        "memory_bandwidth_read_max_gbps": 0.0,
        "memory_bandwidth_write_p90_gbps": 0.0,
        "memory_bandwidth_write_max_gbps": 0.0,
    }


def _bandwidth_metrics_from_series(
    *,
    read_values: list[float],
    write_values: list[float],
    total_values: list[float],
) -> dict[str, float]:
    if not total_values:
        return _empty_memory_bandwidth_metrics()
    return {
        "memory_bandwidth_total_p90_gbps": percentile(total_values, 90),
        "memory_bandwidth_total_max_gbps": max(total_values),
        "memory_bandwidth_read_p90_gbps": percentile(read_values, 90),
        "memory_bandwidth_read_max_gbps": max(read_values),
        "memory_bandwidth_write_p90_gbps": percentile(write_values, 90),
        "memory_bandwidth_write_max_gbps": max(write_values),
    }


def parse_amd_pcm_memory_report(text: str) -> dict[str, float]:
    rows = list(csv.reader(text.splitlines()))
    total_values: list[float] = []
    read_values: list[float] = []
    write_values: list[float] = []
    for index, row in enumerate(rows):
        normalized = [cell.strip() for cell in row]
        if "Total Mem Bw (GB/s)" not in normalized:
            continue
        total_idx = normalized.index("Total Mem Bw (GB/s)")
        read_idx = normalized.index("Total Mem RdBw (GB/s)")
        write_idx = normalized.index("Total Mem WrBw (GB/s)")
        for sample in rows[index + 1 :]:
            if len(sample) <= max(total_idx, read_idx, write_idx):
                break
            try:
                total_values.append(float(sample[total_idx]))
                read_values.append(float(sample[read_idx]))
                write_values.append(float(sample[write_idx]))
            except ValueError:
                break
        break
    return _bandwidth_metrics_from_series(read_values=read_values, write_values=write_values, total_values=total_values)


def _first_system_value(line: str) -> float | None:
    parts = [part.strip() for part in line.split("|")]
    if len(parts) < 2:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", parts[1])
    return float(match.group(0)) if match else None


def parse_amd_pcm_top_output(text: str) -> dict[str, float]:
    total_values: list[float] = []
    read_values: list[float] = []
    write_values: list[float] = []
    for line in text.splitlines():
        if "Total Mem Bw (GB/s)" in line:
            value = _first_system_value(line)
            if value is not None:
                total_values.append(value)
        elif "Total Mem RdBw (GB/s)" in line:
            value = _first_system_value(line)
            if value is not None:
                read_values.append(value)
        elif "Total Mem WrBw (GB/s)" in line:
            value = _first_system_value(line)
            if value is not None:
                write_values.append(value)
    return _bandwidth_metrics_from_series(read_values=read_values, write_values=write_values, total_values=total_values)


_PERF_INTERVAL_RE = re.compile(
    r"^\s*(?P<time>\d+(?:\.\d+)?)\s+"
    r"(?P<count>[\d,]+(?:\.\d+)?)\s+"
    r"(?P<unit>[KMGT]?i?B)\s+"
    r"(?P<event>\S+)"
)


def _to_mib(value: float, unit: str) -> float:
    normalized = unit.lower()
    if normalized in {"kib", "kb"}:
        return value / 1024.0
    if normalized in {"mib", "mb"}:
        return value
    if normalized in {"gib", "gb"}:
        return value * 1024.0
    if normalized in {"tib", "tb"}:
        return value * 1024.0 * 1024.0
    return value


def parse_intel_perf_memory_output(text: str) -> dict[str, float]:
    samples_by_time: dict[float, dict[str, float]] = {}
    for line in text.splitlines():
        match = _PERF_INTERVAL_RE.match(line)
        if match is None:
            continue
        event = match.group("event")
        if "cas_count" not in event:
            continue
        try:
            timestamp = float(match.group("time"))
            value = float(match.group("count").replace(",", ""))
        except ValueError:
            continue
        value_mib = _to_mib(value, match.group("unit"))
        sample = samples_by_time.setdefault(timestamp, {"read_mib": 0.0, "write_mib": 0.0})
        if "read" in event:
            sample["read_mib"] += value_mib
        elif "write" in event:
            sample["write_mib"] += value_mib

    read_values: list[float] = []
    write_values: list[float] = []
    total_values: list[float] = []
    previous_timestamp = 0.0
    for timestamp in sorted(samples_by_time):
        interval_seconds = max(timestamp - previous_timestamp, 1e-9)
        previous_timestamp = timestamp
        read_gbps = samples_by_time[timestamp]["read_mib"] / 1024.0 / interval_seconds
        write_gbps = samples_by_time[timestamp]["write_mib"] / 1024.0 / interval_seconds
        read_values.append(read_gbps)
        write_values.append(write_gbps)
        total_values.append(read_gbps + write_gbps)

    return _bandwidth_metrics_from_series(read_values=read_values, write_values=write_values, total_values=total_values)


def _find_report_csv(output_dir: Path) -> Path | None:
    reports = sorted(output_dir.glob("AMDuProfPcm-*/report.csv"))
    return reports[-1] if reports else None


class AMDuProfPcmMemorySampler:
    def __init__(
        self,
        output_dir: Path,
        *,
        pcm_path: Path = DEFAULT_AMDUPROFPCM_PATH,
        sudo_password: str | None = None,
    ):
        self.output_dir = output_dir
        self.pcm_path = pcm_path
        self.sudo_password = sudo_password if sudo_password is not None else os.environ.get(SUDO_PASSWORD_ENV)
        self.process: subprocess.Popen[str] | None = None
        self.error: str | None = None
        self.stdout_path = self.output_dir / "amd_pcm.stdout.log"
        self.stderr_path = self.output_dir / "amd_pcm.stderr.log"
        self._stdout_handle = None
        self._stderr_handle = None
        self.source: str | None = None

    def _sudo_prefix(self) -> tuple[list[str], bool]:
        if os.geteuid() == 0:
            return [], False
        if self.sudo_password:
            return ["sudo", "-S", "-p", ""], True
        return ["sudo", "-n"], False

    def _select_command(self) -> list[str] | None:
        if self.pcm_path.exists():
            self.source = "amd_pcm"
            return build_amd_pcm_command(self.pcm_path, self.output_dir)
        perf_path = shutil.which("perf")
        if perf_path and _has_intel_uncore_imc_events():
            self.source = "intel_perf_uncore_imc"
            return build_intel_perf_memory_command(perf_path)
        self.error = f"No supported memory bandwidth sampler found: missing {self.pcm_path} and Intel perf uncore_imc events"
        return None

    def start(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        command = self._select_command()
        if command is None:
            self.process = None
            return
        sudo_prefix, needs_password = self._sudo_prefix()
        command = [*sudo_prefix, *command]
        try:
            self._stdout_handle = self.stdout_path.open("w", encoding="utf-8")
            self._stderr_handle = self.stderr_path.open("w", encoding="utf-8")
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE if needs_password else subprocess.DEVNULL,
                stdout=self._stdout_handle,
                stderr=self._stderr_handle,
                text=True,
                start_new_session=True,
            )
            if needs_password and self.process.stdin is not None:
                self.process.stdin.write(f"{self.sudo_password}\n")
                self.process.stdin.close()
            time.sleep(0.2)
            if self.process.poll() is not None:
                self.error = f"{self.source or 'memory sampler'} exited early with code {self.process.returncode}"
        except Exception as exc:
            self.error = str(exc)
            self.process = None

    def stop(self) -> dict[str, Any]:
        if self.process is not None and self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGINT)
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(self.process.pid, signal.SIGTERM)
                    self.process.wait(timeout=5)
                except Exception:
                    os.killpg(self.process.pid, signal.SIGKILL)
                    self.process.wait(timeout=5)
            except ProcessLookupError:
                pass
        if self._stdout_handle is not None:
            self._stdout_handle.close()
        if self._stderr_handle is not None:
            self._stderr_handle.close()

        metrics: dict[str, Any] = _empty_memory_bandwidth_metrics()
        stdout_text = self.stdout_path.read_text(encoding="utf-8", errors="ignore") if self.stdout_path.exists() else ""
        stderr_text = self.stderr_path.read_text(encoding="utf-8", errors="ignore") if self.stderr_path.exists() else ""

        if self.source == "intel_perf_uncore_imc":
            perf_metrics = parse_intel_perf_memory_output(f"{stdout_text}\n{stderr_text}")
            if perf_metrics["memory_bandwidth_total_max_gbps"] > 0.0:
                metrics.update(perf_metrics)
                metrics["memory_bandwidth_source"] = "intel_perf_uncore_imc"
                metrics["intel_perf_stdout_log"] = str(self.stdout_path)
                metrics["intel_perf_stderr_log"] = str(self.stderr_path)
            else:
                metrics["intel_perf_error"] = self.error or "perf stat produced no parseable uncore_imc samples"
            return metrics

        report_path = _find_report_csv(self.output_dir)
        top_metrics = parse_amd_pcm_top_output(stdout_text)
        if top_metrics["memory_bandwidth_total_max_gbps"] > 0.0:
            metrics.update(top_metrics)
            metrics["memory_bandwidth_source"] = "amd_pcm_top"
            metrics["amd_pcm_stdout_log"] = str(self.stdout_path)
        elif report_path is not None and report_path.stat().st_size > 0:
            metrics.update(parse_amd_pcm_memory_report(report_path.read_text(encoding="utf-8", errors="ignore")))
            metrics["memory_bandwidth_source"] = "amd_pcm_report"
            metrics["amd_pcm_report_csv"] = str(report_path)
        else:
            metrics["amd_pcm_error"] = self.error or "AMDuProfPcm report.csv was not created"
        return metrics
