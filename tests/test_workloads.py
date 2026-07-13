from cpu_swe_benchmark.workloads import REFERENCE_TASK_DESCRIPTIONS, get_workload, parse_workload_list


def test_default_workloads_contains_only_algorithm_lab_sorting_bugfix():
    assert list(REFERENCE_TASK_DESCRIPTIONS) == ["algorithm_lab_sorting_bugfix"]


def test_get_workload_prompt_contains_validation_marker_and_submit_command():
    workload = get_workload("algorithm_lab_sorting_bugfix")
    prompt = workload.render_prompt()

    assert "VALIDATION_PASSED" in prompt
    assert "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" in prompt
    assert "mswea_bash_command" in prompt
    assert "10000" in prompt
    assert str(workload.command_timeout_seconds) in prompt


def test_parse_workload_list_supports_default_and_single_workload():
    assert [w.name for w in parse_workload_list("algorithm_lab_sorting_bugfix")] == ["algorithm_lab_sorting_bugfix"]
    assert [w.name for w in parse_workload_list("all")] == list(REFERENCE_TASK_DESCRIPTIONS)


def test_parse_workload_list_rejects_unknown_workload():
    try:
        parse_workload_list("sorting,unknown")
    except ValueError as exc:
        assert "Unknown workload" in str(exc)
    else:
        raise AssertionError("unknown workload was accepted")
