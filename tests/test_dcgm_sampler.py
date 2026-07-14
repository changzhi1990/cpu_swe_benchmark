from pathlib import Path

from cpu_swe_benchmark.dcgm_sampler import DCGM_FIELDS, DCGMGPUSampler, parse_dcgm_dmon_output


def test_parse_dcgm_dmon_output_summarizes_gpu_metrics():
    output = """
#Entity         GPUTL             MCUTL             FBTTL             FBUSD             DRAMA
ID
GPU 0           10                20                1000              800               N/A
GPU 1           30                40                1000              900               N/A
GPU 0           50                60                1000              850               70.000
GPU 1           70                80                1000              950               90.000
"""

    metrics = parse_dcgm_dmon_output(output)

    assert metrics["dcgm_sample_count"] == 4
    assert metrics["gpu_util_avg_percent"] == 40.0
    assert metrics["gpu_util_p50_percent"] == 30.0
    assert metrics["gpu_util_p90_percent"] == 70.0
    assert metrics["gpu_util_max_percent"] == 70.0
    assert metrics["gpu_memory_used_avg_percent"] == 87.5
    assert metrics["gpu_memory_used_max_percent"] == 95.0
    assert metrics["gpu_memory_bandwidth_util_avg_percent"] == 80.0
    assert metrics["gpu_memory_bandwidth_util_p50_percent"] == 70.0
    assert metrics["gpu_memory_bandwidth_util_p90_percent"] == 90.0
    assert metrics["gpu_memory_bandwidth_util_max_percent"] == 90.0
    assert metrics["gpu_memory_bandwidth_util_source"] == "dcgm_drama"


def test_parse_dcgm_dmon_output_falls_back_to_mem_copy_utilization():
    output = """
#Entity         GPUTL             MCUTL             FBTTL             FBUSD             DRAMA
ID
GPU 0           10                20                1000              800               N/A
GPU 1           30                40                1000              900               N/A
"""

    metrics = parse_dcgm_dmon_output(output)

    assert metrics["gpu_memory_bandwidth_util_avg_percent"] == 30.0
    assert metrics["gpu_memory_bandwidth_util_p90_percent"] == 40.0
    assert metrics["gpu_memory_bandwidth_util_max_percent"] == 40.0
    assert metrics["gpu_memory_bandwidth_util_source"] == "dcgm_mcutl"


def test_dcgm_sampler_builds_expected_command(tmp_path: Path):
    sampler = DCGMGPUSampler(tmp_path)

    command = sampler.build_command()

    assert command == ["dcgmi", "dmon", "-e", DCGM_FIELDS, "-d", "1000"]
