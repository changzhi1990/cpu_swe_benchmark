import sys
from pathlib import Path

from cpu_swe_benchmark.validation import classify_run, run_harness_validation, validation_command_for_workload


def test_classify_run_requires_submitted_and_validation_marker():
    assert classify_run("Submitted", ["setup", "VALIDATION_PASSED\nok"], None) == "success"
    assert classify_run("Submitted", ["no marker"], None) == "validation_failed"
    assert classify_run("LimitsExceeded", ["VALIDATION_PASSED"], None) == "not_submitted"
    assert classify_run("Submitted", ["VALIDATION_PASSED"], "boom") == "exception"


def _write_sorting_workspace(path: Path, *, comparison: str) -> None:
    (path / "src" / "algorithm_lab").mkdir(parents=True)
    (path / "tests").mkdir()
    (path / "src" / "algorithm_lab" / "__init__.py").write_text("", encoding="utf-8")
    (path / "src" / "algorithm_lab" / "sorting.py").write_text(
        """
def bubble_sort(arr):
    arr = list(arr)
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] {comparison} arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
""".format(comparison=comparison).strip()
        + "\n",
        encoding="utf-8",
    )
    (path / "tests" / "test_sorting.py").write_text(
        """
from algorithm_lab.sorting import bubble_sort


def test_bubble_sort_ascending_copy():
    values = [3, 1, 2]
    assert bubble_sort(values) == [1, 2, 3]
    assert values == [3, 1, 2]
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_validation_command_uses_current_python_executable():
    command = validation_command_for_workload("algorithm_lab_sorting_bugfix")

    assert command[:3] == [sys.executable, "-m", "pytest"]
    assert command[-1] == "tests/test_sorting.py"


def test_run_harness_validation_passes_with_current_python(tmp_path):
    _write_sorting_workspace(tmp_path, comparison=">")

    result = run_harness_validation("algorithm_lab_sorting_bugfix", tmp_path, timeout_seconds=30)

    assert result["status"] == "passed"
    assert result["returncode"] == 0
    assert "passed" in result["output"]


def test_run_harness_validation_fails_when_workspace_is_still_buggy(tmp_path):
    _write_sorting_workspace(tmp_path, comparison="<")

    result = run_harness_validation("algorithm_lab_sorting_bugfix", tmp_path, timeout_seconds=30)

    assert result["status"] == "failed"
    assert result["returncode"] != 0
