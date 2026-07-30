from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


VALIDATION_MARKER = "VALIDATION_PASSED"
VALIDATION_TESTS_BY_WORKLOAD = {
    "algorithm_lab_sorting_bugfix": ("tests/test_sorting.py",),
    "memory_lab_bandwidth_bugfix": ("tests/test_bandwidth.py",),
}


def classify_run(exit_status: str, command_outputs: list[str], error: str | None) -> str:
    if error:
        return "exception"
    if exit_status != "Submitted":
        return "not_submitted"
    if any(VALIDATION_MARKER in output for output in command_outputs):
        return "success"
    return "validation_failed"


def validation_command_for_workload(workload_name: str, python_executable: str | None = None) -> list[str]:
    tests = VALIDATION_TESTS_BY_WORKLOAD.get(workload_name)
    if not tests:
        return []
    return [python_executable or sys.executable, "-m", "pytest", *tests]


def format_validation_command(command: list[str]) -> str:
    if not command:
        return ""
    return "PYTHONPATH=src " + " ".join(shlex.quote(part) for part in command)


def _prepend_env_path(value: str, prefix: str) -> str:
    if not value:
        return prefix
    parts = value.split(os.pathsep)
    if parts and parts[0] == prefix:
        return value
    return os.pathsep.join([prefix, *parts])


def _coerce_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def run_harness_validation(
    workload_name: str,
    workspace: str | Path,
    *,
    timeout_seconds: int,
    python_executable: str | None = None,
) -> dict[str, Any]:
    command = validation_command_for_workload(workload_name, python_executable=python_executable)
    if not command:
        return {
            "status": "skipped",
            "command": "",
            "returncode": None,
            "duration_seconds": 0.0,
            "output": f"No harness validation command registered for workload {workload_name!r}",
        }

    workspace_path = Path(workspace)
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = "src" + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
    python_bin = str(Path(command[0]).resolve().parent)
    env["PATH"] = _prepend_env_path(env.get("PATH", ""), python_bin)

    start = time.time()
    try:
        completed = subprocess.run(
            command,
            cwd=workspace_path,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        output = _coerce_output(exc.stdout) + _coerce_output(exc.stderr)
        return {
            "status": "timeout",
            "command": format_validation_command(command),
            "returncode": None,
            "duration_seconds": time.time() - start,
            "output": output,
        }

    output = completed.stdout + completed.stderr
    return {
        "status": "passed" if completed.returncode == 0 else "failed",
        "command": format_validation_command(command),
        "returncode": completed.returncode,
        "duration_seconds": time.time() - start,
        "output": output,
    }
