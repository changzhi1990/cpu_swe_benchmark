from cpu_swe_benchmark.instrumented_environment import is_workload_command


def test_is_workload_command_detects_generated_benchmark_python_execution():
    assert is_workload_command("python benchmark_sorting.py")
    assert is_workload_command("python3 benchmark_fft_convolution.py")
    assert is_workload_command("OMP_NUM_THREADS=1 python benchmark_knn.py")
    assert is_workload_command("pytest tests/test_sorting.py")
    assert is_workload_command("pytest tests/test_sorting.py && echo VALIDATION_PASSED")
    assert not is_workload_command("cat > benchmark_sorting.py <<EOF")
    assert not is_workload_command("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT")
