from pathlib import Path
import subprocess

from cpu_swe_benchmark.business_metrics import build_metric_groups, discover_runs, load_business_summary
from cpu_swe_benchmark import system_metrics
from cpu_swe_benchmark.system_metrics import parse_cpu_utilization, parse_loadavg, parse_meminfo, read_basic_system_metrics


def test_parse_cpu_utilization_from_two_proc_stat_snapshots():
    previous = "cpu  100 0 100 800 0 0 0 0 0 0\n"
    current = "cpu  150 0 150 900 0 0 0 0 0 0\n"

    assert parse_cpu_utilization(previous, current) == 50.0


def test_parse_loadavg_reads_1_5_15_minute_values():
    assert parse_loadavg("1.25 2.50 3.75 4/100 12345\n") == {
        "load_1m": 1.25,
        "load_5m": 2.5,
        "load_15m": 3.75,
    }


def test_parse_meminfo_returns_used_and_total_percent():
    data = "MemTotal:       1000000 kB\nMemAvailable:    250000 kB\n"

    parsed = parse_meminfo(data)

    assert parsed["total_bytes"] == 1024000000
    assert parsed["available_bytes"] == 256000000
    assert parsed["used_percent"] == 75.0


def test_read_gpu_metrics_includes_memory_bandwidth_utilization(monkeypatch):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="0, NVIDIA GeForce RTX 5090, 1234, 32607, 42, 17\n",
            stderr="",
        )

    monkeypatch.setattr(system_metrics.subprocess, "run", fake_run)

    gpus = system_metrics.read_gpu_metrics()

    assert gpus[0]["memory_used_percent"] == 3.78
    assert gpus[0]["utilization_gpu_percent"] == 42.0
    assert gpus[0]["memory_bandwidth_util_percent"] == 17.0


def test_read_basic_system_metrics_excludes_expensive_gpu_and_container_calls(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("basic metrics must not spawn subprocesses")

    monkeypatch.setattr(system_metrics.subprocess, "run", fail_if_called)

    metrics = read_basic_system_metrics()

    assert "cpu" in metrics
    assert "load" in metrics
    assert "memory" in metrics
    assert "gpus" not in metrics
    assert "vllm_container" not in metrics


def test_discover_runs_and_load_business_summary(tmp_path: Path):
    run_dir = tmp_path / "results" / "run_a"
    run_dir.mkdir(parents=True)
    (run_dir / "global_summary.csv").write_text(
        "workload,concurrency,submitted_tasks,successful_tasks,failed_tasks,success_rate,"
        "batch_wall_time_seconds,throughput_successful_tasks_per_sec,latency_p50,latency_p90,"
        "latency_p95,latency_p99,avg_llm_time_seconds_per_task,avg_bash_time_seconds_per_task,"
        "avg_model_calls_per_task,avg_bash_calls_per_task\n"
        "sorting,1,1,1,0,1.000000,34.1,0.029,34.0,34.0,34.0,34.0,5.0,28.0,3.0,3.0\n",
        encoding="utf-8",
    )

    runs = discover_runs(tmp_path / "results")
    summary = load_business_summary(tmp_path / "results", str(runs[0]["path"]))

    assert runs[0]["name"] == "run_a"
    assert summary["rows"][0]["workload"] == "sorting"
    assert summary["rows"][0]["success_rate"] == 1.0
    assert summary["latest"]["throughput_successful_tasks_per_sec"] == 0.029


def test_build_metric_groups_classifies_business_metrics_for_charts():
    rows = [
        {
            "workload": "sorting",
            "concurrency": 1,
            "submitted_tasks": 1,
            "successful_tasks": 1,
            "failed_tasks": 0,
            "success_rate": 1.0,
            "batch_wall_time_seconds": 34.1,
            "throughput_successful_tasks_per_sec": 0.029,
            "latency_p50": 34.0,
            "latency_p90": 35.0,
            "latency_p95": 36.0,
            "latency_p99": 37.0,
            "avg_llm_time_seconds_per_task": 5.0,
            "avg_bash_time_seconds_per_task": 28.0,
            "avg_model_calls_per_task": 3.0,
            "avg_bash_calls_per_task": 3.0,
            "cpu_util_avg_percent": 20.0,
            "cpu_util_p50_percent": 20.0,
            "cpu_util_p90_percent": 25.0,
            "cpu_util_max_percent": 30.0,
            "gpu_util_avg_percent": 10.0,
            "gpu_util_p50_percent": 8.0,
            "gpu_util_p90_percent": 18.0,
            "gpu_util_max_percent": 20.0,
            "workload_cpu_util_avg_percent": 50.0,
            "workload_cpu_util_p50_percent": 50.0,
            "workload_cpu_util_p90_percent": 60.0,
            "workload_cpu_util_max_percent": 70.0,
            "workload_gpu_util_avg_percent": 1.0,
            "workload_gpu_util_p50_percent": 0.0,
            "workload_gpu_util_p90_percent": 4.0,
            "workload_gpu_util_max_percent": 5.0,
        },
        {
            "workload": "sorting",
            "concurrency": 2,
            "submitted_tasks": 2,
            "successful_tasks": 2,
            "failed_tasks": 0,
            "success_rate": 1.0,
            "batch_wall_time_seconds": 35.0,
            "throughput_successful_tasks_per_sec": 0.057,
            "latency_p50": 34.5,
            "latency_p90": 35.5,
            "latency_p95": 36.5,
            "latency_p99": 37.5,
            "avg_llm_time_seconds_per_task": 6.0,
            "avg_bash_time_seconds_per_task": 29.0,
            "avg_model_calls_per_task": 3.0,
            "avg_bash_calls_per_task": 3.0,
            "cpu_util_avg_percent": 30.0,
            "cpu_util_p50_percent": 30.0,
            "cpu_util_p90_percent": 35.0,
            "cpu_util_max_percent": 40.0,
            "gpu_util_avg_percent": 11.0,
            "gpu_util_p50_percent": 9.0,
            "gpu_util_p90_percent": 19.0,
            "gpu_util_max_percent": 21.0,
            "workload_cpu_util_avg_percent": 55.0,
            "workload_cpu_util_p50_percent": 55.0,
            "workload_cpu_util_p90_percent": 65.0,
            "workload_cpu_util_max_percent": 75.0,
            "workload_gpu_util_avg_percent": 2.0,
            "workload_gpu_util_p50_percent": 1.0,
            "workload_gpu_util_p90_percent": 5.0,
            "workload_gpu_util_max_percent": 6.0,
        },
    ]

    groups = build_metric_groups(rows)

    assert [group["key"] for group in groups] == [
        "volume",
        "success",
        "throughput",
        "latency",
        "timing",
        "calls",
        "system_cpu",
        "system_gpu",
        "system_memory",
        "workload_cpu",
        "workload_gpu",
    ]
    assert groups[3]["title"] == "Latency"
    assert groups[3]["series"][0]["key"] == "latency_p50"
    assert groups[3]["series"][0]["points"] == [{"x": 1, "y": 34.0}, {"x": 2, "y": 34.5}]
    assert groups[4]["series"][0]["key"] == "avg_llm_time_seconds_per_task"
    assert groups[6]["title"] == "CPU Utilization by Concurrency"
    assert groups[6]["series"][0]["key"] == "cpu_util_avg_percent"
    assert groups[9]["title"] == "Workload CPU Utilization"
    assert groups[9]["series"][0]["key"] == "workload_cpu_util_avg_percent"
