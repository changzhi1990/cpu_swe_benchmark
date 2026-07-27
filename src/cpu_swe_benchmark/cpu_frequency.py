from __future__ import annotations

import math
import os
import re
import subprocess
from collections import defaultdict, deque
from pathlib import Path
from typing import Iterable


ACTIVE_CORE_THRESHOLD_MHZ = 3000.0


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil((pct / 100.0) * len(ordered)))
    return ordered[min(rank - 1, len(ordered) - 1)]


def mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def read_proc_cpuinfo_frequency_by_cpu(path: Path = Path("/proc/cpuinfo")) -> dict[int, float]:
    frequencies: dict[int, float] = {}
    current_cpu: int | None = None
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("processor"):
                try:
                    current_cpu = int(line.split(":", 1)[1])
                except (IndexError, ValueError):
                    current_cpu = None
            elif line.startswith("cpu MHz") and current_cpu is not None:
                try:
                    frequencies[current_cpu] = float(line.split(":", 1)[1])
                except (IndexError, ValueError):
                    continue
    return frequencies


def read_proc_cpuinfo_frequencies(path: Path = Path("/proc/cpuinfo")) -> list[float]:
    frequencies_by_cpu = read_proc_cpuinfo_frequency_by_cpu(path)
    return [frequencies_by_cpu[cpu] for cpu in sorted(frequencies_by_cpu)]


def summarize_frequency_sample(
    frequencies: list[float],
    *,
    active_threshold_mhz: float = ACTIVE_CORE_THRESHOLD_MHZ,
) -> dict[str, float]:
    active = [mhz for mhz in frequencies if mhz >= active_threshold_mhz]
    return {
        "avg_mhz": mean(frequencies),
        "min_mhz": min(frequencies) if frequencies else 0.0,
        "max_mhz": max(frequencies) if frequencies else 0.0,
        "p95_mhz": percentile(frequencies, 95),
        "p99_mhz": percentile(frequencies, 99),
        "active_core_count": float(len(active)),
        "active_core_avg_mhz": mean(active),
        "active_core_max_mhz": max(active) if active else 0.0,
        "cores": float(len(frequencies)),
    }


def parse_proc_stat_fields(stat_text: str) -> dict[str, int]:
    text = stat_text.strip()
    close_paren = text.rfind(")")
    if close_paren < 0:
        raise ValueError("process stat line is missing command terminator")
    fields = text[close_paren + 2 :].split()
    if len(fields) <= 36:
        raise ValueError("process stat line does not include processor field")
    return {
        "ppid": int(fields[1]),
        "processor": int(fields[36]),
    }


def _iter_proc_pids(proc_root: Path) -> list[int]:
    pids: list[int] = []
    for child in proc_root.iterdir():
        if child.name.isdigit():
            pids.append(int(child.name))
    return pids


def _read_process_cmdline(proc_root: Path, pid: int) -> str:
    try:
        raw = (proc_root / str(pid) / "cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\0", b" ").decode("utf-8", errors="replace").strip()


def _read_process_table(proc_root: Path = Path("/proc")) -> dict[int, dict[str, int | str]]:
    processes: dict[int, dict[str, int | str]] = {}
    for pid in _iter_proc_pids(proc_root):
        try:
            stat_text = (proc_root / str(pid) / "stat").read_text(encoding="utf-8", errors="replace")
            fields = parse_proc_stat_fields(stat_text)
        except (OSError, ValueError):
            continue
        processes[pid] = {
            "ppid": fields["ppid"],
            "processor": fields["processor"],
            "cmdline": _read_process_cmdline(proc_root, pid),
        }
    return processes


def find_matching_process_tree_pids(
    *,
    proc_root: Path = Path("/proc"),
    match_terms: tuple[str, ...] = ("benchmark_latency.py",),
) -> set[int]:
    if not match_terms:
        return set()
    processes = _read_process_table(proc_root)
    roots = {
        pid
        for pid, process in processes.items()
        if all(term in str(process.get("cmdline", "")) for term in match_terms)
    }
    children_by_parent: dict[int, list[int]] = defaultdict(list)
    for pid, process in processes.items():
        children_by_parent[int(process["ppid"])].append(pid)

    selected: set[int] = set()
    queue: deque[int] = deque(sorted(roots))
    while queue:
        pid = queue.popleft()
        if pid in selected:
            continue
        selected.add(pid)
        queue.extend(children_by_parent.get(pid, []))
    return selected


def summarize_agent_frequency_sample(
    *,
    proc_root: Path = Path("/proc"),
    cpuinfo_path: Path = Path("/proc/cpuinfo"),
    match_terms: tuple[str, ...] = ("benchmark_latency.py",),
) -> dict[str, float]:
    frequencies_by_cpu = read_proc_cpuinfo_frequency_by_cpu(cpuinfo_path)
    processes = _read_process_table(proc_root)
    selected_pids = find_matching_process_tree_pids(proc_root=proc_root, match_terms=match_terms)
    selected_cpus = {
        int(processes[pid]["processor"])
        for pid in selected_pids
        if pid in processes and int(processes[pid]["processor"]) in frequencies_by_cpu
    }
    frequencies = [frequencies_by_cpu[cpu] for cpu in sorted(selected_cpus)]
    return {
        "agent_cpu_count": float(len(frequencies)),
        "agent_cpu_avg_mhz": mean(frequencies),
        "agent_cpu_min_mhz": min(frequencies) if frequencies else 0.0,
        "agent_cpu_max_mhz": max(frequencies) if frequencies else 0.0,
        "agent_cpu_p50_mhz": percentile(frequencies, 50),
        "agent_cpu_p95_mhz": percentile(frequencies, 95),
        "agent_cpu_p99_mhz": percentile(frequencies, 99),
    }


TOPOLOGY_CMD = "/home/user/zhi/AMDuProf_Nda_Linux_x64_5.0.1479/bin/AMDCpuTopology"
AVT_CMD = "/opt/AMD/AVT/AVTCMD"


def parse_amd_cpu_topology(text: str) -> dict[int, tuple[int, int, int, int]]:
    records = _parse_amd_cpu_topology_records(text)
    min_ccx_by_package, local_core_by_ccx = _local_topology_maps(records)

    mapping: dict[int, tuple[int, int, int, int]] = {}
    for package, _numa, ccx, core, thread in records:
        die = 0
        local_ccd = ccx - min_ccx_by_package[package]
        local_core = local_core_by_ccx[(package, ccx)][core]
        mapping[thread] = (package, die, local_ccd, local_core)
    return mapping


def _parse_amd_cpu_topology_records(text: str) -> list[tuple[int, int, int, int, int]]:
    records: list[tuple[int, int, int, int, int]] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 5 or not all(part.lstrip("-").isdigit() for part in parts):
            continue
        package, numa, ccx, core, thread = (int(part) for part in parts)
        records.append((package, numa, ccx, core, thread))
    return records


def _local_topology_maps(
    records: list[tuple[int, int, int, int, int]],
) -> tuple[dict[int, int], dict[tuple[int, int], dict[int, int]]]:
    min_ccx_by_package: dict[int, int] = {}
    cores_by_ccx: dict[tuple[int, int], set[int]] = defaultdict(set)
    for package, _numa, ccx, core, _thread in records:
        min_ccx_by_package[package] = min(ccx, min_ccx_by_package.get(package, ccx))
        cores_by_ccx[(package, ccx)].add(core)

    local_core_by_ccx = {
        key: {core: index for index, core in enumerate(sorted(cores))}
        for key, cores in cores_by_ccx.items()
    }
    return min_ccx_by_package, local_core_by_ccx


def build_linux_cpu_to_avt_core_mapping(
    topology_text: str,
    *,
    cpu_topology_root: Path = Path("/sys/devices/system/cpu"),
) -> dict[int, tuple[int, int, int, int]]:
    records = _parse_amd_cpu_topology_records(topology_text)
    min_ccx_by_package, local_core_by_ccx = _local_topology_maps(records)
    min_core_by_package: dict[int, int] = {}
    records_by_package_core: dict[tuple[int, int], tuple[int, int, int, int, int]] = {}
    for record in records:
        package, _numa, _ccx, core, _thread = record
        min_core_by_package[package] = min(core, min_core_by_package.get(package, core))
        records_by_package_core.setdefault((package, core), record)

    mapping: dict[int, tuple[int, int, int, int]] = {}
    for cpu_path in sorted(cpu_topology_root.glob("cpu[0-9]*"), key=lambda path: int(path.name[3:])):
        cpu = int(cpu_path.name[3:])
        topology_dir = cpu_path / "topology"
        try:
            package = int((topology_dir / "physical_package_id").read_text(encoding="utf-8").strip())
            kernel_core = int((topology_dir / "core_id").read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            continue
        topology_core = kernel_core
        if (package, topology_core) not in records_by_package_core and package in min_core_by_package:
            topology_core = kernel_core + min_core_by_package[package]
        record = records_by_package_core.get((package, topology_core))
        if record is None:
            continue
        _package, _numa, ccx, core, _thread = record
        die = 0
        local_ccd = ccx - min_ccx_by_package[package]
        local_core = local_core_by_ccx[(package, ccx)][core]
        mapping[cpu] = (package, die, local_ccd, local_core)
    return mapping


_AVT_CSTATE_RE = re.compile(
    r"CStates, \[Pkg:(?P<pkg>\d+), Die:(?P<die>\d+), CCD:(?P<ccd>\d+), "
    r"PhysicalCore:(?P<core>\d+)\].*?C0:(?P<c0>[0-9.]+).*?"
    r"Freq\(GHz\):(?P<freq>[0-9.]+), EffFreq\(GHz\):(?P<eff>[0-9.]+)"
)


def parse_avt_cstates(text: str) -> dict[tuple[int, int, int, int], dict[str, float]]:
    values: dict[tuple[int, int, int, int], dict[str, float]] = {}
    for line in text.splitlines():
        match = _AVT_CSTATE_RE.search(line)
        if not match:
            continue
        key = (
            int(match.group("pkg")),
            int(match.group("die")),
            int(match.group("ccd")),
            int(match.group("core")),
        )
        values[key] = {
            "c0_percent": float(match.group("c0")),
            "freq_ghz": float(match.group("freq")),
            "eff_freq_ghz": float(match.group("eff")),
        }
    return values


def _run_text(command: list[str], *, input_text: str | None = None) -> str:
    result = subprocess.run(
        command,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=30,
        check=True,
    )
    return result.stdout


def read_amd_cpu_topology(command: str = TOPOLOGY_CMD) -> str:
    return _run_text([command])


def read_avt_cstates(
    command: str = AVT_CMD,
    *,
    use_sudo: bool = True,
    sudo_password: str | None = None,
) -> str:
    base_command = [command, "-module", "pmm", "get_cstates()"]
    input_text = None
    if use_sudo:
        sudo_password = sudo_password if sudo_password is not None else os.environ.get("SUDO_PASSWORD")
        if sudo_password:
            base_command = ["sudo", "-S", "-p", "", *base_command]
            input_text = f"{sudo_password}\n"
        else:
            base_command = ["sudo", "-n", *base_command]
    return _run_text(base_command, input_text=input_text)


def summarize_agent_effective_frequency_sample(
    *,
    proc_root: Path = Path("/proc"),
    topology_text: str | None = None,
    cstates_text: str | None = None,
    topology_cmd: str = TOPOLOGY_CMD,
    avt_cmd: str = AVT_CMD,
    cpu_topology_root: Path = Path("/sys/devices/system/cpu"),
    use_sudo: bool = True,
    sudo_password: str | None = None,
    match_terms: tuple[str, ...] = ("benchmark_latency.py",),
) -> dict[str, float]:
    topology_text = topology_text if topology_text is not None else read_amd_cpu_topology(topology_cmd)
    cstates_text = cstates_text if cstates_text is not None else read_avt_cstates(
        avt_cmd,
        use_sudo=use_sudo,
        sudo_password=sudo_password,
    )
    linux_cpu_to_core = build_linux_cpu_to_avt_core_mapping(
        topology_text,
        cpu_topology_root=cpu_topology_root,
    )
    cstates = parse_avt_cstates(cstates_text)
    processes = _read_process_table(proc_root)
    selected_pids = find_matching_process_tree_pids(proc_root=proc_root, match_terms=match_terms)
    selected_threads = {
        int(processes[pid]["processor"])
        for pid in selected_pids
        if pid in processes and int(processes[pid]["processor"]) in linux_cpu_to_core
    }
    selected_core_keys = {linux_cpu_to_core[thread] for thread in selected_threads}
    selected_values = [cstates[key] for key in sorted(selected_core_keys) if key in cstates]
    eff_mhz = [value["eff_freq_ghz"] * 1000.0 for value in selected_values]
    freq_mhz = [value["freq_ghz"] * 1000.0 for value in selected_values]
    c0_values = [value["c0_percent"] for value in selected_values]
    return {
        "agent_cpu_count": float(len(selected_values)),
        "agent_eff_freq_avg_mhz": mean(eff_mhz),
        "agent_eff_freq_min_mhz": min(eff_mhz) if eff_mhz else 0.0,
        "agent_eff_freq_max_mhz": max(eff_mhz) if eff_mhz else 0.0,
        "agent_eff_freq_p50_mhz": percentile(eff_mhz, 50),
        "agent_eff_freq_p95_mhz": percentile(eff_mhz, 95),
        "agent_eff_freq_p99_mhz": percentile(eff_mhz, 99),
        "agent_freq_avg_mhz": mean(freq_mhz),
        "agent_c0_avg_percent": mean(c0_values),
    }


def parse_frequency_log_line(line: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for part in line.strip().split(",")[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        try:
            values[key] = float(value)
        except ValueError:
            continue
    return values


def summarize_cpu_frequency_log(path: Path | str) -> dict[str, float]:
    path = Path(path)
    sample_values: list[dict[str, float]] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            values = parse_frequency_log_line(line)
            if values:
                sample_values.append(values)

    def values_for(key: str) -> list[float]:
        return [sample[key] for sample in sample_values if key in sample]

    def agent_values_for(key: str) -> list[float]:
        return [
            sample[key]
            for sample in sample_values
            if sample.get("agent_cpu_count", 0.0) > 0.0 and key in sample
        ]

    return {
        "actual_cpu_avg_mhz": mean(values_for("avg_mhz")),
        "actual_cpu_max_mhz": max(values_for("max_mhz"), default=0.0),
        "actual_cpu_p95_mhz": mean(values_for("p95_mhz")),
        "actual_cpu_p99_mhz": mean(values_for("p99_mhz")),
        "active_core_count_avg": mean(values_for("active_core_count")),
        "active_core_avg_mhz": mean(values_for("active_core_avg_mhz")),
        "active_core_max_mhz": max(values_for("active_core_max_mhz"), default=0.0),
        "agent_cpu_count_avg": mean(agent_values_for("agent_cpu_count")),
        "agent_cpu_avg_mhz": mean(agent_values_for("agent_cpu_avg_mhz")),
        "agent_cpu_max_mhz": max(agent_values_for("agent_cpu_max_mhz"), default=0.0),
        "agent_cpu_p50_mhz": mean(agent_values_for("agent_cpu_p50_mhz")),
        "agent_cpu_p95_mhz": mean(agent_values_for("agent_cpu_p95_mhz")),
        "agent_cpu_p99_mhz": mean(agent_values_for("agent_cpu_p99_mhz")),
        "agent_eff_freq_avg_mhz": mean(agent_values_for("agent_eff_freq_avg_mhz")),
        "agent_eff_freq_min_mhz": min(agent_values_for("agent_eff_freq_min_mhz"), default=0.0),
        "agent_eff_freq_max_mhz": max(agent_values_for("agent_eff_freq_max_mhz"), default=0.0),
        "agent_eff_freq_p50_mhz": mean(agent_values_for("agent_eff_freq_p50_mhz")),
        "agent_eff_freq_p95_mhz": mean(agent_values_for("agent_eff_freq_p95_mhz")),
        "agent_eff_freq_p99_mhz": mean(agent_values_for("agent_eff_freq_p99_mhz")),
        "agent_freq_avg_mhz": mean(agent_values_for("agent_freq_avg_mhz")),
        "agent_c0_avg_percent": mean(agent_values_for("agent_c0_avg_percent")),
    }
