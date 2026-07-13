from __future__ import annotations

import csv
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from cpu_swe_benchmark.aggregate import percentile


DEFAULT_AMDUPROFPCM_PATH = Path("/home/user/zhi/AMDuProf_Nda_Linux_x64_5.0.1479/bin/AMDuProfPcm")
SUDO_PASSWORD_ENV = "AMDUPROFPCM_SUDO_PASSWORD"


def build_amd_pcm_command(pcm_path: Path, output_dir: Path) -> list[str]:
    return [
        str(pcm_path),
        "--msr",
        "-r",
        "-m",
        "memory",
        "-a",
        "-I",
        "1000",
        "-A",
        "system",
        "-O",
        str(output_dir),
    ]


def _empty_memory_bandwidth_metrics() -> dict[str, float]:
    return {
        "memory_bandwidth_total_p90_gbps": 0.0,
        "memory_bandwidth_total_max_gbps": 0.0,
        "memory_bandwidth_read_p90_gbps": 0.0,
        "memory_bandwidth_read_max_gbps": 0.0,
        "memory_bandwidth_write_p90_gbps": 0.0,
        "memory_bandwidth_write_max_gbps": 0.0,
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

    def start(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        command = build_amd_pcm_command(self.pcm_path, self.output_dir)
        if os.geteuid() != 0:
            if self.sudo_password:
                command = ["sudo", "-S", "-p", "", *command]
            else:
                command = ["sudo", "-n", *command]
        try:
            stdout = self.stdout_path.open("w", encoding="utf-8")
            stderr = self.stderr_path.open("w", encoding="utf-8")
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE if self.sudo_password and os.geteuid() != 0 else subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                text=True,
                start_new_session=True,
            )
            if self.sudo_password and self.process.stdin is not None:
                self.process.stdin.write(f"{self.sudo_password}\n")
                self.process.stdin.close()
            time.sleep(0.2)
            if self.process.poll() is not None:
                self.error = f"AMDuProfPcm exited early with code {self.process.returncode}"
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
        metrics: dict[str, Any] = _empty_memory_bandwidth_metrics()
        report_path = _find_report_csv(self.output_dir)
        if report_path is not None:
            metrics.update(parse_amd_pcm_memory_report(report_path.read_text(encoding="utf-8", errors="ignore")))
            metrics["amd_pcm_report_csv"] = str(report_path)
        else:
            metrics["amd_pcm_error"] = self.error or "AMDuProfPcm report.csv was not created"
        return metrics
