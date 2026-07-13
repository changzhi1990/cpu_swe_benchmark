from cpu_swe_benchmark.system_sampler import summarize_system_samples


def test_summarize_system_samples_reports_cpu_and_gpu_utilization_stats():
    samples = [
        {
            "cpu": {"utilization_percent": 10.0},
            "memory": {"used_percent": 20.0},
            "gpus": [
                {"index": 0, "utilization_gpu_percent": 30.0, "memory_used_percent": 80.0},
                {"index": 1, "utilization_gpu_percent": 50.0, "memory_used_percent": 90.0},
            ],
        },
        {
            "cpu": {"utilization_percent": 30.0},
            "memory": {"used_percent": 40.0},
            "gpus": [
                {"index": 0, "utilization_gpu_percent": 70.0, "memory_used_percent": 85.0},
                {"index": 1, "utilization_gpu_percent": 90.0, "memory_used_percent": 95.0},
            ],
        },
    ]

    summary = summarize_system_samples(samples)

    assert summary["cpu_util_avg_percent"] == 20.0
    assert summary["cpu_util_p50_percent"] == 10.0
    assert summary["cpu_util_p90_percent"] == 30.0
    assert summary["cpu_util_max_percent"] == 30.0
    assert summary["memory_used_avg_percent"] == 30.0
    assert summary["memory_used_max_percent"] == 40.0
    assert summary["gpu_util_avg_percent"] == 60.0
    assert summary["gpu_util_p50_percent"] == 50.0
    assert summary["gpu_util_p90_percent"] == 90.0
    assert summary["gpu_util_max_percent"] == 90.0
    assert summary["gpu_memory_used_avg_percent"] == 87.5
    assert summary["gpu_memory_used_max_percent"] == 95.0


def test_summarize_system_samples_supports_prefix_for_workload_phase():
    samples = [
        {"cpu": {"utilization_percent": 10.0}, "memory": {"used_percent": 20.0}, "gpus": []},
        {"cpu": {"utilization_percent": 30.0}, "memory": {"used_percent": 40.0}, "gpus": []},
    ]

    summary = summarize_system_samples(samples, prefix="workload_")

    assert summary["workload_cpu_util_avg_percent"] == 20.0
    assert summary["workload_cpu_util_p90_percent"] == 30.0
    assert "cpu_util_avg_percent" not in summary
