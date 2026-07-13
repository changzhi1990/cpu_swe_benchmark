from cpu_swe_benchmark.aggregate import aggregate_runs, percentile
from cpu_swe_benchmark.runner import write_global_csv
from cpu_swe_benchmark.schemas import RunResult


def make_run(run_id, *, status="success", wall=10.0, llm=6.0, bash=3.0, model_call_log=None):
    return RunResult(
        run_id=run_id,
        workload="sorting",
        concurrency=4,
        status=status,
        exit_status="Submitted" if status == "success" else "Error",
        total_wall_time_seconds=wall,
        llm_time_total_seconds=llm,
        bash_time_total_seconds=bash,
        model_calls=2,
        bash_calls=2,
        validation_passed=status == "success",
        endpoint="http://localhost:8000/v1",
        trajectory_path=None,
        error=None,
        model_call_log=model_call_log or [],
    )


def test_percentile_uses_nearest_rank_with_sorted_copy():
    values = [30.0, 10.0, 20.0, 40.0]

    assert percentile(values, 50) == 20.0
    assert percentile(values, 90) == 40.0
    assert values == [30.0, 10.0, 20.0, 40.0]


def test_aggregate_runs_reports_success_rate_and_successful_throughput():
    runs = [
        make_run("r1", status="success", wall=10.0, llm=5.0, bash=4.0),
        make_run("r2", status="success", wall=20.0, llm=12.0, bash=6.0),
        make_run("r3", status="validation_failed", wall=30.0, llm=18.0, bash=9.0),
        make_run("r4", status="timeout", wall=40.0, llm=20.0, bash=10.0),
    ]

    summary = aggregate_runs(
        runs,
        workload="sorting",
        concurrency=4,
        model="qwen2.5-coder-32b",
        base_url="http://localhost:8000/v1",
        vllm_topology="tp8",
        batch_wall_time_seconds=50.0,
        system_metrics={"cpu_util_avg_percent": 42.0, "gpu_util_avg_percent": 7.0},
    )

    assert summary.submitted_tasks == 4
    assert summary.successful_tasks == 2
    assert summary.failed_tasks == 2
    assert summary.success_rate == 0.5
    assert summary.throughput_successful_tasks_per_sec == 0.04
    assert summary.latency_seconds["p50"] == 20.0
    assert summary.avg_llm_time_seconds_per_task == 13.75
    assert summary.avg_bash_time_seconds_per_task == 7.25
    assert summary.system_metrics["cpu_util_avg_percent"] == 42.0


def test_aggregate_runs_reports_model_serving_p90_from_completed_calls():
    runs = [
        make_run(
            "r1",
            model_call_log=[
                {"status": "completed", "ttft_seconds": 0.1, "tpot_seconds": 0.01},
                {"status": "completed", "ttft_seconds": 0.2, "tpot_seconds": 0.02},
            ],
        ),
        make_run(
            "r2",
            model_call_log=[
                {"status": "completed", "ttft_seconds": 0.4, "tpot_seconds": 0.04},
                {"status": "error", "ttft_seconds": 9.9, "tpot_seconds": 9.9},
            ],
        ),
    ]

    summary = aggregate_runs(
        runs,
        workload="sorting",
        concurrency=2,
        model="qwen2.5-coder-32b",
        base_url="http://localhost:8000/v1",
        vllm_topology="tp8",
        batch_wall_time_seconds=50.0,
        system_metrics={
            "memory_bandwidth_total_p90_gbps": 12.5,
            "memory_bandwidth_total_max_gbps": 15.0,
            "memory_bandwidth_read_p90_gbps": 8.5,
            "memory_bandwidth_read_max_gbps": 10.0,
            "memory_bandwidth_write_p90_gbps": 4.0,
            "memory_bandwidth_write_max_gbps": 5.0,
        },
    )

    assert summary.model_serving_seconds["ttft_p90"] == 0.4
    assert summary.model_serving_seconds["tpot_p90"] == 0.04


def test_write_global_csv_includes_e2e_ttft_and_tpot_p90_columns(tmp_path):
    summary = aggregate_runs(
        [
            make_run(
                "r1",
                wall=10.0,
                model_call_log=[{"status": "completed", "ttft_seconds": 0.1, "tpot_seconds": 0.01}],
            ),
            make_run(
                "r2",
                wall=20.0,
                model_call_log=[{"status": "completed", "ttft_seconds": 0.4, "tpot_seconds": 0.04}],
            ),
        ],
        workload="sorting",
        concurrency=2,
        model="qwen2.5-coder-32b",
        base_url="http://localhost:8000/v1",
        vllm_topology="tp8",
        batch_wall_time_seconds=50.0,
        system_metrics={
            "memory_bandwidth_total_p90_gbps": 12.5,
            "memory_bandwidth_total_max_gbps": 15.0,
            "memory_bandwidth_read_p90_gbps": 8.5,
            "memory_bandwidth_read_max_gbps": 10.0,
            "memory_bandwidth_write_p90_gbps": 4.0,
            "memory_bandwidth_write_max_gbps": 5.0,
        },
    )

    csv_path = write_global_csv([summary], tmp_path)
    header, row = csv_path.read_text(encoding="utf-8").splitlines()
    columns = header.split(",")
    values = dict(zip(columns, row.split(",")))

    assert values["E2E_p90_seconds"] == "20.000000"
    assert values["TTFT_p90"] == "0.400000"
    assert values["TPOT_p90"] == "0.040000"
    assert values["memory_bandwidth_total_p90_gbps"] == "12.500000"
    assert values["memory_bandwidth_total_max_gbps"] == "15.000000"
    assert values["memory_bandwidth_read_p90_gbps"] == "8.500000"
    assert values["memory_bandwidth_read_max_gbps"] == "10.000000"
    assert values["memory_bandwidth_write_p90_gbps"] == "4.000000"
    assert values["memory_bandwidth_write_max_gbps"] == "5.000000"
