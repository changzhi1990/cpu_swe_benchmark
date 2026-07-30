from cpu_swe_benchmark.workloads import REFERENCE_TASK_DESCRIPTIONS, get_workload, parse_workload_list


def test_default_workloads_contains_compute_and_memory_repo_workloads():
    assert list(REFERENCE_TASK_DESCRIPTIONS) == [
        "algorithm_lab_sorting_bugfix",
        "memory_lab_bandwidth_bugfix",
    ]


def test_get_workload_prompt_contains_validation_marker_and_submit_command():
    workload = get_workload("algorithm_lab_sorting_bugfix")
    prompt = workload.render_prompt()

    assert "VALIDATION_PASSED" in prompt
    assert "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" in prompt
    assert "mswea_bash_command" in prompt
    assert "10000" in prompt
    assert str(workload.command_timeout_seconds) in prompt


def test_algorithm_lab_sorting_prompt_contains_ordering_hard_constraints():
    workload = get_workload("algorithm_lab_sorting_bugfix")
    prompt = workload.render_prompt()

    assert "Sorting-specific hard constraints" in prompt
    assert "arr[j] > arr[j + 1]" in prompt
    assert "Do not add nested contradictory comparisons" in prompt
    assert "pytest still shows descending output" in prompt
    assert "Do not combine source edits and pytest in the same bash command" in prompt
    assert "After any command that edits files under `src/`, wait for the next assistant step before running pytest" in prompt


def test_memory_lab_bandwidth_bugfix_prompt_describes_streaming_memory_workload():
    workload = get_workload("memory_lab_bandwidth_bugfix")
    prompt = workload.render_prompt()

    assert workload.repo_template == "memory_lab"
    assert "memory_lab" in prompt
    assert "PYTHONPATH=src python3 -m pytest tests/test_bandwidth.py" in prompt
    assert "NumPy vectorized streaming" in prompt
    assert "Do not use Python element-wise loops" in prompt
    assert "VALIDATION_PASSED" in prompt
    assert "16_000_000" in prompt
    assert "256" in prompt
    assert "sustained memory bandwidth" in prompt


def test_parse_workload_list_supports_default_and_single_workload():
    assert [w.name for w in parse_workload_list("algorithm_lab_sorting_bugfix")] == ["algorithm_lab_sorting_bugfix"]
    assert [w.name for w in parse_workload_list("memory_lab_bandwidth_bugfix")] == ["memory_lab_bandwidth_bugfix"]
    assert [w.name for w in parse_workload_list("all")] == list(REFERENCE_TASK_DESCRIPTIONS)


def test_parse_workload_list_rejects_unknown_workload():
    try:
        parse_workload_list("sorting,unknown")
    except ValueError as exc:
        assert "Unknown workload" in str(exc)
    else:
        raise AssertionError("unknown workload was accepted")
