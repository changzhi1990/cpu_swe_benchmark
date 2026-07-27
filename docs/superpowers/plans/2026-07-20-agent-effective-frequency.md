# Agent Effective Frequency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an agent-process AVT effective frequency sampler and a requested `algorithm_lab_sorting_bugfix` concurrency sweep.

**Architecture:** Extend `cpu_frequency.py` with small `/proc` parsing helpers and a process-tree sampler. Add a separate sweep script so existing fmax sweep scripts keep their current behavior.

**Tech Stack:** Python standard library, Bash, pytest, Linux `/proc`, AMDuProf `AMDCpuTopology`, AMD AVT `get_cstates()`.

---

### Task 1: Agent CPU Frequency Helpers

**Files:**
- Modify: `src/cpu_swe_benchmark/cpu_frequency.py`
- Test: `tests/test_cpu_frequency.py`

- [ ] **Step 1: Write failing tests**

Add tests that require these functions:

```python
read_proc_cpuinfo_frequency_by_cpu(path)
parse_proc_stat_fields(stat_text)
summarize_agent_frequency_sample(proc_root, cpuinfo_path, match_terms)
```

The tests must prove that only CPUs used by the matched benchmark process tree are included.

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python3 -m pytest tests/test_cpu_frequency.py -q
```

Expected: import failures for the new functions.

- [ ] **Step 3: Implement helpers**

Add helpers to parse CPU MHz by processor id, parse `/proc/<pid>/stat`, find matching process trees, and summarize unique current CPUs for the process tree.

- [ ] **Step 4: Verify helper tests pass**

Run:

```bash
python3 -m pytest tests/test_cpu_frequency.py -q
```

Expected: all tests in `tests/test_cpu_frequency.py` pass.

### Task 2: Agent Frequency Log Aggregation

**Files:**
- Modify: `src/cpu_swe_benchmark/cpu_frequency.py`
- Test: `tests/test_cpu_frequency.py`

- [ ] **Step 1: Write failing aggregation test**

Add a log test that includes `agent_cpu_*` fields and verifies samples with `agent_cpu_count=0` do not lower the aggregate.

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python3 -m pytest tests/test_cpu_frequency.py -q
```

Expected: assertion failure for missing or zero `agent_cpu_*` summary fields.

- [ ] **Step 3: Implement aggregation fields**

Add `agent_cpu_count_avg`, `agent_cpu_avg_mhz`, `agent_cpu_max_mhz`, `agent_cpu_p50_mhz`, `agent_cpu_p95_mhz`, and `agent_cpu_p99_mhz` to `summarize_cpu_frequency_log`.

- [ ] **Step 4: Verify aggregation tests pass**

Run:

```bash
python3 -m pytest tests/test_cpu_frequency.py -q
```

Expected: all tests in `tests/test_cpu_frequency.py` pass.

### Task 3: Requested Sweep Script

**Files:**
- Create: `scripts/run_agent_effective_freq_sweep.sh`
- Modify: `tests/test_scripts.py`

- [ ] **Step 1: Write failing script test**

Assert the script defaults to `algorithm_lab_sorting_bugfix`, concurrency levels `1,2,4,8,16,32,64,128,180`, imports `summarize_agent_frequency_sample`, and writes `summary_by_concurrency.csv` with `agent_cpu_*` fields.

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
python3 -m pytest tests/test_scripts.py -q
```

Expected: file-not-found failure for the new script.

- [ ] **Step 3: Create script**

Implement the script to run each concurrency point once by default, start a 1-second AVT effective-frequency logger around each benchmark run, and aggregate `agent_cpu_*` metrics by concurrency.

- [ ] **Step 4: Verify focused tests pass**

Run:

```bash
python3 -m pytest tests/test_cpu_frequency.py tests/test_scripts.py -q
```

Expected: all focused tests pass.

### Task 4: Runtime Launch

**Files:**
- Runtime artifacts only under `results/` and `logs/`.

- [ ] **Step 1: Check no benchmark is already running**

Run:

```bash
pgrep -af '[b]enchmark_latency.py' || true
```

Expected: no output.

- [ ] **Step 2: Start the requested sweep**

Run:

```bash
RUNSET_ID="agent_effective_freq_$(date +%Y%m%d_%H%M%S)" bash scripts/run_agent_effective_freq_sweep.sh
```

Expected: the script writes `results/<RUNSET_ID>/summary_by_concurrency.csv`.
