from pathlib import Path

from cpu_swe_benchmark.amd_pcm import build_amd_pcm_command, parse_amd_pcm_memory_report


def test_parse_amd_pcm_memory_report_returns_p90_and_max_bandwidth():
    report = """
AMDuProfPcm Report

Profile Time: 2026/07/13 19:03:24:444
DF METRICS,,,
System (Aggregated),,,
Total Mem Bw (GB/s),Total Mem RdBw (GB/s),Total Mem WrBw (GB/s),
10.0,6.0,4.0,
30.0,20.0,10.0,
20.0,12.0,8.0,
"""

    metrics = parse_amd_pcm_memory_report(report)

    assert metrics["memory_bandwidth_total_p90_gbps"] == 30.0
    assert metrics["memory_bandwidth_total_max_gbps"] == 30.0
    assert metrics["memory_bandwidth_read_p90_gbps"] == 20.0
    assert metrics["memory_bandwidth_read_max_gbps"] == 20.0
    assert metrics["memory_bandwidth_write_p90_gbps"] == 10.0
    assert metrics["memory_bandwidth_write_max_gbps"] == 10.0


def test_build_amd_pcm_command_uses_required_memory_bandwidth_arguments():
    command = build_amd_pcm_command(Path("/opt/AMDuProfPcm"), Path("/tmp/pcm"))

    assert command == [
        "/opt/AMDuProfPcm",
        "--msr",
        "-r",
        "-m",
        "memory",
        "-a",
        "-I",
        "1000",
        "-A",
        "system",
        "-O",
        "/tmp/pcm",
    ]
