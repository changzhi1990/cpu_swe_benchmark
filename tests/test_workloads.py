from cpu_swe_benchmark.workloads import REFERENCE_TASK_DESCRIPTIONS, get_workload, parse_workload_list


def test_default_workloads_contains_fast_synthetic_cpu_tasks():
    assert list(REFERENCE_TASK_DESCRIPTIONS) == [
        "sorting",
        "fibonacci",
        "prime_numbers",
        "numerical_integration",
        "matmul",
        "lu_decomposition",
        "knn",
        "fft_convolution",
        "memory_bandwidth_utilization",
        "algorithm_lab_sorting_bugfix",
    ]


def test_get_workload_prompt_contains_validation_marker_and_submit_command():
    workload = get_workload("sorting")
    prompt = workload.render_prompt()

    assert "VALIDATION_PASSED" in prompt
    assert "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" in prompt
    assert "mswea_bash_command" in prompt
    assert str(workload.command_timeout_seconds) in prompt


def test_sorting_workload_matches_cpu_centric_reference_sizes():
    workload = get_workload("sorting")
    prompt = workload.render_prompt()

    assert "10000" in prompt
    assert "20000" in prompt
    assert "n=3000" not in prompt


def test_workload_prompts_reuse_reference_task_description_style():
    expected_fragments = {
        "fibonacci": "Fibonacci Computation Benchmark",
        "prime_numbers": "Prime Number Computation Benchmark",
        "numerical_integration": "Numerical Integration Benchmark",
        "matmul": "Matrix Multiplication Benchmark",
        "lu_decomposition": "Vectorized NumPy LU Decomposition Benchmark",
        "knn": "k-NN Benchmark",
        "fft_convolution": "FFT-based 1D Convolution Benchmark",
        "memory_bandwidth_utilization": "CPU and Memory Bandwidth Utilization Benchmark",
    }

    for workload_name, fragment in expected_fragments.items():
        prompt = get_workload(workload_name).render_prompt()
        assert fragment in prompt
        assert "Problem Description:" in prompt
        assert "Please implement a complete solution" in prompt


def test_memory_bandwidth_utilization_workload_uses_requested_description_without_stress_word():
    prompt = get_workload("memory_bandwidth_utilization").render_prompt()

    assert "CPU and Memory Bandwidth Utilization Benchmark" in prompt
    assert "benchmark_memory_bandwidth_utilization.py" in prompt
    assert "100 million total elements" in prompt
    assert "VALIDATION_PASSED" in prompt
    assert "stress" not in prompt.lower()


def test_parse_workload_list_supports_default_and_single_workload():
    assert [w.name for w in parse_workload_list("sorting")] == ["sorting"]
    assert [w.name for w in parse_workload_list("all")] == list(REFERENCE_TASK_DESCRIPTIONS)


def test_parse_workload_list_rejects_unknown_workload():
    try:
        parse_workload_list("sorting,unknown")
    except ValueError as exc:
        assert "Unknown workload" in str(exc)
    else:
        raise AssertionError("unknown workload was accepted")
