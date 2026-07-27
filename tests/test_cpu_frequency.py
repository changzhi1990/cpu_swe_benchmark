from pathlib import Path

from cpu_swe_benchmark.cpu_frequency import (
    build_linux_cpu_to_avt_core_mapping,
    parse_amd_cpu_topology,
    parse_avt_cstates,
    parse_proc_stat_fields,
    read_proc_cpuinfo_frequency_by_cpu,
    summarize_agent_effective_frequency_sample,
    summarize_agent_frequency_sample,
    summarize_cpu_frequency_log,
)


def _stat_text(pid: int, ppid: int, processor: int, comm: str = "python3") -> str:
    fields_after_comm = ["S", str(ppid)] + ["0"] * 34 + [str(processor)]
    return f"{pid} ({comm}) " + " ".join(fields_after_comm)


def _write_proc_entry(proc_root: Path, pid: int, ppid: int, processor: int, cmdline: list[str]) -> None:
    proc_dir = proc_root / str(pid)
    proc_dir.mkdir(parents=True)
    proc_dir.joinpath("stat").write_text(_stat_text(pid, ppid, processor), encoding="utf-8")
    proc_dir.joinpath("cmdline").write_bytes("\0".join(cmdline).encode() + b"\0")


def _write_cpu_topology(cpu_root: Path, cpu: int, package: int, core_id: int) -> None:
    topology = cpu_root / f"cpu{cpu}" / "topology"
    topology.mkdir(parents=True)
    topology.joinpath("physical_package_id").write_text(str(package), encoding="utf-8")
    topology.joinpath("core_id").write_text(str(core_id), encoding="utf-8")


def test_summarize_cpu_frequency_log_reports_active_core_stats(tmp_path: Path):
    log_path = tmp_path / "freq.csv"
    log_path.write_text(
        "\n".join(
            [
                "1.0,fmax_mhz=4300,avg_mhz=2500.00,min_mhz=2400.00,max_mhz=4300.00,"
                "p95_mhz=4100.00,p99_mhz=4300.00,active_core_count=2,"
                "active_core_avg_mhz=4200.00,active_core_max_mhz=4300.00,cores=4",
                "2.0,fmax_mhz=4300,avg_mhz=2600.00,min_mhz=2400.00,max_mhz=4200.00,"
                "p95_mhz=4000.00,p99_mhz=4200.00,active_core_count=1,"
                "active_core_avg_mhz=4200.00,active_core_max_mhz=4200.00,cores=4",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = summarize_cpu_frequency_log(log_path)

    assert summary["actual_cpu_avg_mhz"] == 2550.0
    assert summary["actual_cpu_max_mhz"] == 4300.0
    assert summary["actual_cpu_p95_mhz"] == 4050.0
    assert summary["actual_cpu_p99_mhz"] == 4250.0
    assert summary["active_core_count_avg"] == 1.5
    assert summary["active_core_avg_mhz"] == 4200.0
    assert summary["active_core_max_mhz"] == 4300.0


def test_summarize_cpu_frequency_log_reports_agent_cpu_stats_and_ignores_idle_agent_samples(tmp_path: Path):
    log_path = tmp_path / "freq.csv"
    log_path.write_text(
        "\n".join(
            [
                "1.0,avg_mhz=2500.00,max_mhz=4300.00,agent_cpu_count=0,"
                "agent_cpu_avg_mhz=0.00,agent_cpu_max_mhz=0.00,agent_cpu_p50_mhz=0.00,"
                "agent_cpu_p95_mhz=0.00,agent_cpu_p99_mhz=0.00,"
                "agent_eff_freq_avg_mhz=0.00,agent_eff_freq_max_mhz=0.00,agent_c0_avg_percent=0.00",
                "2.0,avg_mhz=2600.00,max_mhz=4200.00,agent_cpu_count=2,"
                "agent_cpu_avg_mhz=4100.00,agent_cpu_max_mhz=4200.00,agent_cpu_p50_mhz=4000.00,"
                "agent_cpu_p95_mhz=4200.00,agent_cpu_p99_mhz=4200.00,"
                "agent_eff_freq_avg_mhz=3900.00,agent_eff_freq_max_mhz=4100.00,agent_c0_avg_percent=90.00",
                "3.0,avg_mhz=2400.00,max_mhz=3600.00,agent_cpu_count=1,"
                "agent_cpu_avg_mhz=3600.00,agent_cpu_max_mhz=3600.00,agent_cpu_p50_mhz=3600.00,"
                "agent_cpu_p95_mhz=3600.00,agent_cpu_p99_mhz=3600.00,"
                "agent_eff_freq_avg_mhz=3500.00,agent_eff_freq_max_mhz=3500.00,agent_c0_avg_percent=100.00",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = summarize_cpu_frequency_log(log_path)

    assert summary["agent_cpu_count_avg"] == 1.5
    assert summary["agent_cpu_avg_mhz"] == 3850.0
    assert summary["agent_cpu_max_mhz"] == 4200.0
    assert summary["agent_cpu_p50_mhz"] == 3800.0
    assert summary["agent_cpu_p95_mhz"] == 3900.0
    assert summary["agent_cpu_p99_mhz"] == 3900.0
    assert summary["agent_eff_freq_avg_mhz"] == 3700.0
    assert summary["agent_eff_freq_max_mhz"] == 4100.0
    assert summary["agent_c0_avg_percent"] == 95.0


def test_read_proc_cpuinfo_frequency_by_cpu_uses_processor_ids(tmp_path: Path):
    cpuinfo = tmp_path / "cpuinfo"
    cpuinfo.write_text(
        "\n".join(
            [
                "processor\t: 0",
                "cpu MHz\t\t: 2400.000",
                "",
                "processor\t: 3",
                "cpu MHz\t\t: 4100.500",
            ]
        ),
        encoding="utf-8",
    )

    assert read_proc_cpuinfo_frequency_by_cpu(cpuinfo) == {0: 2400.0, 3: 4100.5}


def test_parse_proc_stat_fields_handles_process_names_with_spaces():
    fields = parse_proc_stat_fields(_stat_text(42, ppid=7, processor=5, comm="python worker"))

    assert fields["ppid"] == 7
    assert fields["processor"] == 5


def test_summarize_agent_frequency_sample_uses_only_matching_process_tree_cpus(tmp_path: Path):
    cpuinfo = tmp_path / "cpuinfo"
    cpuinfo.write_text(
        "\n".join(
            [
                "processor\t: 0",
                "cpu MHz\t\t: 2000.000",
                "processor\t: 1",
                "cpu MHz\t\t: 3000.000",
                "processor\t: 2",
                "cpu MHz\t\t: 4000.000",
                "processor\t: 3",
                "cpu MHz\t\t: 4200.000",
            ]
        ),
        encoding="utf-8",
    )
    proc_root = tmp_path / "proc"
    proc_root.mkdir()
    _write_proc_entry(proc_root, 10, ppid=1, processor=2, cmdline=["python3", "benchmark_latency.py"])
    _write_proc_entry(proc_root, 11, ppid=10, processor=3, cmdline=["python3", "-m", "pytest"])
    _write_proc_entry(proc_root, 12, ppid=11, processor=2, cmdline=["python3", "worker_child.py"])
    _write_proc_entry(proc_root, 20, ppid=1, processor=1, cmdline=["python3", "unrelated.py"])

    summary = summarize_agent_frequency_sample(
        proc_root=proc_root,
        cpuinfo_path=cpuinfo,
        match_terms=("benchmark_latency.py",),
    )

    assert summary["agent_cpu_count"] == 2.0
    assert summary["agent_cpu_avg_mhz"] == 4100.0
    assert summary["agent_cpu_min_mhz"] == 4000.0
    assert summary["agent_cpu_max_mhz"] == 4200.0
    assert summary["agent_cpu_p50_mhz"] == 4000.0
    assert summary["agent_cpu_p95_mhz"] == 4200.0


def test_parse_amd_cpu_topology_maps_linux_thread_to_avt_core_key():
    topology = """
-------------------------------------
 Package Numa    CCX    Core    Thread
-------------------------------------
 0         0       0     0      0
 0         0       4     24     6
 0         0       4     25     7
 0         0       4     26     8
 0         0       4     27     9
 0         0       4     28     10
 0         0       4     28     154
 1         1       12    72     72
 1         1       17    102    132
 1         1       17    103    133
 1         1       17    104    134
 1         1       17    105    135
 1         1       17    106    136
 1         1       17    107    137
 1         1       17    107    281
-------------------------------------
"""

    mapping = parse_amd_cpu_topology(topology)

    assert mapping[10] == (0, 0, 4, 4)
    assert mapping[154] == (0, 0, 4, 4)
    assert mapping[137] == (1, 0, 5, 5)


def test_build_linux_cpu_to_avt_core_mapping_uses_kernel_package_and_core_id(tmp_path: Path):
    cpu_root = tmp_path / "sys" / "devices" / "system" / "cpu"
    _write_cpu_topology(cpu_root, 10, package=0, core_id=10)
    _write_cpu_topology(cpu_root, 394, package=0, core_id=10)
    _write_cpu_topology(cpu_root, 20, package=0, core_id=68)
    _write_cpu_topology(cpu_root, 404, package=0, core_id=68)
    topology = """
 Package Numa    CCX    Core    Thread
 0         0       0     10     20
 0         0       0     10     21
 0         0       4     68     136
 0         0       4     68     137
"""

    mapping = build_linux_cpu_to_avt_core_mapping(topology, cpu_topology_root=cpu_root)

    assert mapping[10] == (0, 0, 0, 0)
    assert mapping[394] == (0, 0, 0, 0)
    assert mapping[20] == (0, 0, 4, 0)
    assert mapping[404] == (0, 0, 4, 0)


def test_parse_avt_cstates_extracts_efffreq_by_physical_core_key():
    cstates = """
Command Success, Approximate Residency:
CStates, [Pkg:0, Die:0, CCD:4, PhysicalCore:1], C0:100.00, CC1:0.00, CC6:0.00, Freq(GHz):3.700, EffFreq(GHz):3.766
CStates, [Pkg:1, Die:0, CCD:0, PhysicalCore:0], C0:50.00, CC1:50.00, CC6:0.00, Freq(GHz):3.418, EffFreq(GHz):1.709
CStates, [Pkg:1, Die:0], CstateBoost:0, DfCstate:0, SystemIdle:0
"""

    parsed = parse_avt_cstates(cstates)

    assert parsed[(0, 0, 4, 1)]["eff_freq_ghz"] == 3.766
    assert parsed[(0, 0, 4, 1)]["c0_percent"] == 100.0
    assert parsed[(1, 0, 0, 0)]["freq_ghz"] == 3.418


def test_summarize_agent_effective_frequency_sample_uses_avt_efffreq_for_agent_cores(tmp_path: Path):
    proc_root = tmp_path / "proc"
    proc_root.mkdir()
    _write_proc_entry(proc_root, 10, ppid=1, processor=10, cmdline=["python3", "benchmark_latency.py"])
    _write_proc_entry(proc_root, 11, ppid=10, processor=154, cmdline=["python3", "-m", "pytest"])
    _write_proc_entry(proc_root, 12, ppid=10, processor=137, cmdline=["python3", "worker_child.py"])
    _write_proc_entry(proc_root, 20, ppid=1, processor=6, cmdline=["python3", "unrelated.py"])
    cpu_root = tmp_path / "sys" / "devices" / "system" / "cpu"
    _write_cpu_topology(cpu_root, 10, package=0, core_id=28)
    _write_cpu_topology(cpu_root, 154, package=0, core_id=28)
    _write_cpu_topology(cpu_root, 137, package=1, core_id=35)
    _write_cpu_topology(cpu_root, 6, package=0, core_id=24)
    topology = """
 Package Numa    CCX    Core    Thread
 0         0       0     0      0
 0         0       4     24     6
 0         0       4     25     7
 0         0       4     26     8
 0         0       4     27     9
 0         0       4     28     10
 0         0       4     28     154
 1         1       12    72     72
 1         1       17    102    132
 1         1       17    103    133
 1         1       17    104    134
 1         1       17    105    135
 1         1       17    106    136
 1         1       17    107    137
"""
    cstates = """
CStates, [Pkg:0, Die:0, CCD:4, PhysicalCore:4], C0:100.00, CC1:0.00, CC6:0.00, Freq(GHz):3.700, EffFreq(GHz):3.766
CStates, [Pkg:1, Die:0, CCD:5, PhysicalCore:5], C0:50.00, CC1:50.00, CC6:0.00, Freq(GHz):3.418, EffFreq(GHz):1.709
"""

    summary = summarize_agent_effective_frequency_sample(
        proc_root=proc_root,
        topology_text=topology,
        cstates_text=cstates,
        cpu_topology_root=cpu_root,
        match_terms=("benchmark_latency.py",),
    )

    assert summary["agent_cpu_count"] == 2.0
    assert summary["agent_eff_freq_avg_mhz"] == 2737.5
    assert summary["agent_eff_freq_min_mhz"] == 1709.0
    assert summary["agent_eff_freq_max_mhz"] == 3766.0
    assert summary["agent_eff_freq_p50_mhz"] == 1709.0
    assert summary["agent_eff_freq_p95_mhz"] == 3766.0
    assert summary["agent_c0_avg_percent"] == 75.0


def test_summarize_cpu_frequency_log_handles_old_logs_without_active_stats(tmp_path: Path):
    log_path = tmp_path / "old_freq.csv"
    log_path.write_text(
        "1.0,fmax_mhz=4300,avg_mhz=2500.00,min_mhz=2400.00,max_mhz=4300.00,cores=4\n",
        encoding="utf-8",
    )

    summary = summarize_cpu_frequency_log(log_path)

    assert summary["actual_cpu_avg_mhz"] == 2500.0
    assert summary["actual_cpu_max_mhz"] == 4300.0
    assert summary["active_core_count_avg"] == 0.0
    assert summary["active_core_avg_mhz"] == 0.0
    assert summary["agent_cpu_count_avg"] == 0.0
    assert summary["agent_cpu_avg_mhz"] == 0.0
    assert summary["agent_eff_freq_avg_mhz"] == 0.0
