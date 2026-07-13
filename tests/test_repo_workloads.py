from pathlib import Path

from cpu_swe_benchmark.repo_workloads import copy_repo_template, repo_template_path
from cpu_swe_benchmark.workloads import get_workload


def test_algorithm_lab_sorting_bugfix_workload_points_to_repo_template():
    workload = get_workload("algorithm_lab_sorting_bugfix")
    prompt = workload.render_prompt()

    assert workload.repo_template == "algorithm_lab"
    assert "algorithm_lab" in prompt
    assert "PYTHONPATH=src python3 -m pytest tests/test_sorting.py" in prompt
    assert "Run pytest tests/test_sorting.py" not in prompt
    assert "Do not modify tests" in prompt
    assert "VALIDATION_PASSED" in prompt
    assert "10000" in prompt
    assert "CPU-intensive" in prompt
    assert "Python script" in prompt
    assert "sed regex" in prompt
    assert "Create exactly one Python file" not in prompt
    assert "benchmark_algorithm_lab_sorting_bugfix.py" not in prompt
    assert "Do not create replacement benchmark scripts" in prompt


def test_algorithm_lab_template_contains_python_package_and_failing_sorting_source():
    template = repo_template_path("algorithm_lab")
    sorting_source = (template / "src" / "algorithm_lab" / "sorting.py").read_text(encoding="utf-8")

    assert (template / "pyproject.toml").exists()
    assert (template / "src" / "algorithm_lab" / "sorting.py").exists()
    assert (template / "tests" / "test_sorting.py").exists()
    assert "for i in range(n):" in sorting_source
    assert "for j in range(0, n - i - 1):" in sorting_source
    assert "arr = list(arr)" in sorting_source
    assert "arr[j] < arr[j + 1]" in sorting_source
    assert "sorted(" not in sorting_source
    assert ".sort(" not in sorting_source


def test_algorithm_lab_template_requires_cpu_intensive_10000_item_sort():
    test_source = (repo_template_path("algorithm_lab") / "tests" / "test_sorting.py").read_text(encoding="utf-8")

    assert "range(10_000)" in test_source
    assert "random.Random" in test_source
    assert "sorted(values)" in test_source
    assert "inspect.getsource" in test_source
    assert "\"sorted(\" not in source" in test_source
    assert "\".sort(\" not in source" in test_source


def test_copy_repo_template_copies_files_without_aliasing(tmp_path: Path):
    destination = tmp_path / "workspace"

    copy_repo_template("algorithm_lab", destination)
    copied_sorting = destination / "src" / "algorithm_lab" / "sorting.py"
    copied_sorting.write_text("changed = True\n", encoding="utf-8")

    original_sorting = repo_template_path("algorithm_lab") / "src" / "algorithm_lab" / "sorting.py"
    assert "changed = True" not in original_sorting.read_text(encoding="utf-8")
