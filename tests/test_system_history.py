from cpu_swe_benchmark.system_history import SystemHistory


def test_system_history_keeps_recent_cpu_and_gpu_points():
    history = SystemHistory(max_points=2)
    history.add_sample(
        {
            "timestamp": 10.0,
            "cpu": {"utilization_percent": 12.5},
            "gpus": [
                {"index": 0, "utilization_gpu_percent": 30.0},
                {"index": 1, "utilization_gpu_percent": 40.0},
            ],
        }
    )
    history.add_sample(
        {
            "timestamp": 20.0,
            "cpu": {"utilization_percent": 22.5},
            "gpus": [
                {"index": 0, "utilization_gpu_percent": 35.0},
                {"index": 1, "utilization_gpu_percent": 45.0},
            ],
        }
    )
    history.add_sample(
        {
            "timestamp": 30.0,
            "cpu": {"utilization_percent": 32.5},
            "gpus": [
                {"index": 0, "utilization_gpu_percent": 55.0},
                {"index": 1, "utilization_gpu_percent": 65.0},
            ],
        }
    )

    payload = history.to_payload()

    assert payload["cpu"] == [{"x": 20.0, "y": 22.5}, {"x": 30.0, "y": 32.5}]
    assert payload["gpus"][0]["points"] == [{"x": 20.0, "y": 35.0}, {"x": 30.0, "y": 55.0}]
    assert payload["gpus"][1]["points"] == [{"x": 20.0, "y": 45.0}, {"x": 30.0, "y": 65.0}]
