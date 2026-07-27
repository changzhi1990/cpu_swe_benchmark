from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_vllm_start_script_uses_docker_image_and_local_model_mount():
    script = (ROOT / "scripts" / "start_vllm_tp8_qwen32b.sh").read_text(encoding="utf-8")

    assert "vllm/vllm-openai:latest" in script
    assert "/home/user/models/Qwen2.5-Coder-32B-Instruct" in script
    assert "--gpus all" in script
    assert "--ipc=host" in script
    assert "-v \"${HOST_MODEL_PATH}:${CONTAINER_MODEL_PATH}:ro\"" in script
    assert "--tensor-parallel-size 8" in script
    assert "--model \"${CONTAINER_MODEL_PATH}\"" in script


def test_quick_script_runs_algorithm_lab_sorting_bugfix_workload():
    script = (ROOT / "scripts" / "run_sorting_quick.sh").read_text(encoding="utf-8")

    assert "--benchmark-type algorithm_lab_sorting_bugfix" in script
    assert "qwen32b_tp8_algorithm_lab_sorting_bugfix_quick" in script
    assert "--benchmark-type sorting" not in script


def test_agent_effective_frequency_sweep_tracks_agent_cpu_fields():
    script = (ROOT / "scripts" / "run_agent_effective_freq_sweep.sh").read_text(encoding="utf-8")

    assert "WORKLOAD=\"${WORKLOAD:-algorithm_lab_sorting_bugfix}\"" in script
    assert "CONCURRENCY_LEVELS=\"${CONCURRENCY_LEVELS:-1,2,4,8,16,32,64,128,180}\"" in script
    assert "summary_by_concurrency.csv" in script
    assert "summarize_agent_effective_frequency_sample" in script
    assert "get_cstates()" in script
    assert "AMDCpuTopology" in script
    assert "agent_eff_freq_avg_mhz" in script
    assert 'TASK_TIMEOUT="${TASK_TIMEOUT:-3600}"' in script
    assert 'AGENT_CPUSET="${AGENT_CPUSET:-8-760}"' in script
    assert 'VLLM_CPUSET="${VLLM_CPUSET:-0-7}"' in script
    assert 'taskset -c "${AGENT_CPUSET}"' in script
    assert "agent_cpu_avg_mhz" not in script
    assert "actual_cpu_avg_mhz" not in script
