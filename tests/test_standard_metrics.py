from __future__ import annotations

import csv
from pathlib import Path

from cpu_swe_benchmark.standard_metrics import aggregate_standard_metrics, summarize_avt_aggregate_log


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_summarize_avt_aggregate_log_supports_key_value_logs(tmp_path: Path):
    log = tmp_path / "agentfreq.csv"
    log.write_text(
        "\n".join(
            [
                "1.0,agent_cpu_count=5,agent_eff_freq_avg_mhz=100.00,"
                "agent_eff_freq_min_mhz=1.00,agent_eff_freq_max_mhz=300.00,"
                "agent_eff_freq_p50_mhz=90.00,agent_eff_freq_p95_mhz=250.00,"
                "agent_eff_freq_p99_mhz=280.00,agent_freq_avg_mhz=3200.00,"
                "agent_c0_avg_percent=3.00",
                "2.0,agent_cpu_count=7,agent_eff_freq_avg_mhz=200.00,"
                "agent_eff_freq_min_mhz=2.00,agent_eff_freq_max_mhz=400.00,"
                "agent_eff_freq_p50_mhz=180.00,agent_eff_freq_p95_mhz=350.00,"
                "agent_eff_freq_p99_mhz=380.00,agent_freq_avg_mhz=3300.00,"
                "agent_c0_avg_percent=6.00",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = summarize_avt_aggregate_log(log)

    assert summary["avt_sample_count"] == "2"
    assert summary["avt_agent_cpu_count_avg"] == "6.000000"
    assert summary["agent_eff_freq_avg_mhz"] == "150.000000"
    assert summary["agent_eff_freq_min_mhz"] == "1.000000"
    assert summary["agent_eff_freq_max_mhz"] == "400.000000"
    assert summary["agent_eff_freq_p95_mhz"] == "300.000000"


def test_aggregate_standard_metrics_writes_cpu_gpu_and_vllm_tables(tmp_path: Path):
    runset = tmp_path / "results" / "runset"
    c1_dir = tmp_path / "results" / "run_c001"
    c2_dir = tmp_path / "results" / "run_c002"
    c1_freq = runset / "cpu_freq" / "c1.aggregate.csv"
    c2_freq = runset / "cpu_freq" / "c2.aggregate.csv"
    c1_per_core = runset / "per_core_freq" / "c1.per_core.csv"
    c2_per_core = runset / "per_core_freq" / "c2.per_core.csv"
    c1_per_core.parent.mkdir(parents=True, exist_ok=True)
    c1_per_core.write_text("timestamp,linux_cpu,eff_freq_mhz\n", encoding="utf-8")
    c2_per_core.write_text("timestamp,linux_cpu,eff_freq_mhz\n", encoding="utf-8")
    runset.mkdir(parents=True, exist_ok=True)

    write_csv(
        runset / "manifest.csv",
        [
            {
                "runset_id": "runset",
                "run_id": "c1",
                "concurrency": "1",
                "status": "completed",
                "run_dir": str(c1_dir),
                "aggregate_freq_log": str(c1_freq),
                "per_core_freq_log": str(c1_per_core),
            },
            {
                "runset_id": "runset",
                "run_id": "c2",
                "concurrency": "2",
                "status": "completed",
                "run_dir": str(c2_dir),
                "aggregate_freq_log": str(c2_freq),
                "per_core_freq_log": str(c2_per_core),
            },
        ],
    )
    for concurrency, run_dir in [("1", c1_dir), ("2", c2_dir)]:
        write_csv(
            run_dir / "global_summary.csv",
            [
                {
                    "workload": "algorithm_lab_sorting_bugfix",
                    "concurrency": concurrency,
                    "submitted_tasks": concurrency,
                    "successful_tasks": str(int(concurrency) - 1),
                    "failed_tasks": "1",
                    "timeout_tasks": "0",
                    "success_rate": "0.500000",
                    "batch_wall_time_seconds": "90.000000",
                    "throughput_successful_tasks_per_sec": "0.100000",
                    "latency_p50": "40.000000",
                    "latency_p90": "42.000000",
                    "latency_p95": "44.000000",
                    "latency_p99": "48.000000",
                    "E2E_p90_seconds": "42.000000",
                    "TTFT_p90": "1.250000",
                    "TPOT_p90": "0.050000",
                    "avg_llm_time_seconds_per_task": "7.500000",
                    "avg_bash_time_seconds_per_task": "3.250000",
                    "avg_model_calls_per_task": "8.000000",
                    "avg_bash_calls_per_task": "4.000000",
                }
            ],
        )
        write_csv(
            run_dir / "cpu_memory.csv",
            [
                {
                    "workload": "algorithm_lab_sorting_bugfix",
                    "concurrency": concurrency,
                    "cpu_util_avg_percent": f"{float(concurrency):.6f}",
                    "memory_used_max_percent": "3.000000",
                }
            ],
        )
        write_csv(
            run_dir / "gpu_metrics.csv",
            [
                {
                    "workload": "algorithm_lab_sorting_bugfix",
                    "concurrency": concurrency,
                    "gpu_util_avg_percent": "99.000000",
                }
            ],
        )
        write_csv(
            run_dir / "llm_serving.csv",
            [
                {
                    "workload": "algorithm_lab_sorting_bugfix",
                    "concurrency": concurrency,
                    "TTFT_p90": "1.250000",
                    "TPOT_p90": "0.050000",
                    "llm_input_tokens_total": "123",
                }
            ],
        )

    write_csv(
        c1_freq,
        [
            {
                "timestamp": "1",
                "pid_count": "2",
                "agent_logical_cpu_count": "2",
                "agent_physical_core_count": "1",
                "agent_eff_freq_avg_mhz": "1000",
                "agent_eff_freq_min_mhz": "900",
                "agent_eff_freq_max_mhz": "1100",
                "agent_eff_freq_p50_mhz": "1000",
                "agent_eff_freq_p95_mhz": "1080",
                "agent_eff_freq_p99_mhz": "1090",
                "agent_freq_avg_mhz": "3000",
                "agent_c0_avg_percent": "25",
                "agent_logical_cpus": "10;394",
            },
            {
                "timestamp": "2",
                "pid_count": "3",
                "agent_logical_cpu_count": "3",
                "agent_physical_core_count": "2",
                "agent_eff_freq_avg_mhz": "2000",
                "agent_eff_freq_min_mhz": "1500",
                "agent_eff_freq_max_mhz": "2500",
                "agent_eff_freq_p50_mhz": "2000",
                "agent_eff_freq_p95_mhz": "2400",
                "agent_eff_freq_p99_mhz": "2450",
                "agent_freq_avg_mhz": "3500",
                "agent_c0_avg_percent": "50",
                "agent_logical_cpus": "10;11;394",
            },
        ],
    )
    write_csv(
        c2_freq,
        [
            {
                "timestamp": "1",
                "pid_count": "4",
                "agent_logical_cpu_count": "4",
                "agent_physical_core_count": "2",
                "agent_eff_freq_avg_mhz": "1200",
                "agent_eff_freq_min_mhz": "800",
                "agent_eff_freq_max_mhz": "1800",
                "agent_eff_freq_p50_mhz": "1200",
                "agent_eff_freq_p95_mhz": "1700",
                "agent_eff_freq_p99_mhz": "1750",
                "agent_freq_avg_mhz": "3200",
                "agent_c0_avg_percent": "35",
                "agent_logical_cpus": "20;404",
            }
        ],
    )

    outputs = aggregate_standard_metrics(runset)

    assert outputs.cpu_metrics == runset / "cpu_metrics.csv"
    assert outputs.gpu_metrics == runset / "gpu_metrics.csv"
    assert outputs.vllm_metrics == runset / "vllm_metrics.csv"
    assert outputs.global_metrics == runset / "global_metrics.csv"

    cpu_rows = list(csv.DictReader(outputs.cpu_metrics.open(encoding="utf-8")))
    gpu_rows = list(csv.DictReader(outputs.gpu_metrics.open(encoding="utf-8")))
    vllm_rows = list(csv.DictReader(outputs.vllm_metrics.open(encoding="utf-8")))
    global_rows = list(csv.DictReader(outputs.global_metrics.open(encoding="utf-8")))

    assert [row["concurrency"] for row in cpu_rows] == ["1", "2"]
    assert [row["concurrency"] for row in gpu_rows] == ["1", "2"]
    assert [row["concurrency"] for row in vllm_rows] == ["1", "2"]
    assert [row["concurrency"] for row in global_rows] == ["1", "2"]
    for rows in (cpu_rows, gpu_rows, vllm_rows, global_rows):
        assert rows[0]["submitted_tasks"] == "1"
        assert rows[0]["successful_tasks"] == "0"
        assert rows[0]["failed_tasks"] == "1"
        assert rows[0]["timeout_tasks"] == "0"
        assert rows[0]["success_rate"] == "0.500000"
        assert rows[0]["E2E_p90_seconds"] == "42.000000"
        assert rows[0]["TTFT_p90"] == "1.250000"
        assert rows[0]["TPOT_p90"] == "0.050000"
        assert rows[0]["run_dir"] == str(c1_dir)
        assert rows[0]["avg_bash_time_seconds_per_task"] == "3.250000"
    assert cpu_rows[0]["avt_sample_count"] == "2"
    assert cpu_rows[0]["avt_agent_eff_freq_avg_mhz_avg"] == "1500.000000"
    assert cpu_rows[0]["avt_agent_eff_freq_min_mhz_min"] == "900.000000"
    assert cpu_rows[0]["avt_agent_eff_freq_max_mhz_max"] == "2500.000000"
    assert cpu_rows[0]["agent_eff_freq_p95_mhz"] == "1740.000000"
    assert cpu_rows[0]["avt_per_core_freq_log"] == str(c1_per_core)
    assert global_rows[0]["cpu_util_avg_percent"] == "1.000000"
    assert global_rows[0]["gpu_util_avg_percent"] == "99.000000"
    assert global_rows[0]["llm_input_tokens_total"] == "123"
    assert global_rows[0]["avt_agent_eff_freq_avg_mhz_avg"] == "1500.000000"
    assert not (c1_dir / "cpu_metrics.csv").exists()
    assert not (c2_dir / "cpu_metrics.csv").exists()
