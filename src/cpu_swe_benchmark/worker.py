from __future__ import annotations

import json
import os
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

from cpu_swe_benchmark.instrumented_environment import InstrumentedEnvironment
from cpu_swe_benchmark.repo_workloads import copy_repo_template
from cpu_swe_benchmark.schemas import RunResult, to_jsonable
from cpu_swe_benchmark.system_sampler import summarize_system_samples
from cpu_swe_benchmark.validation import classify_run
from cpu_swe_benchmark.vllm_text_model import VLLMTextModel
from cpu_swe_benchmark.workloads import Workload


SYSTEM_TEMPLATE = """You are a software engineering agent that can execute bash commands.
Every assistant response must contain exactly one fenced command block tagged `mswea_bash_command`.
Use non-interactive commands only. Keep commands concise.
"""

INSTANCE_TEMPLATE = "{{ task }}"
DEFAULT_AGENT_STEP_LIMIT = 20


@dataclass(frozen=True)
class WorkerConfig:
    run_id: str
    worker_index: int
    workload: Workload
    concurrency: int
    endpoint: str
    model: str
    api_key: str
    run_dir: Path
    mini_swe_agent_src: Path
    task_timeout_seconds: int
    command_timeout_seconds: int
    cpu_threads_per_worker: int
    model_max_tokens: int
    model_temperature: float


def _set_cpu_env(threads: int):
    value = str(threads)
    os.environ["OMP_NUM_THREADS"] = value
    os.environ["MKL_NUM_THREADS"] = value
    os.environ["OPENBLAS_NUM_THREADS"] = value
    os.environ["NUMEXPR_NUM_THREADS"] = value
    os.environ["TOKENIZERS_PARALLELISM"] = "false"


def _ensure_mini_swe_agent_path(path: Path):
    resolved = str(path.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


def run_worker(config: WorkerConfig) -> RunResult:
    _set_cpu_env(config.cpu_threads_per_worker)
    _ensure_mini_swe_agent_path(config.mini_swe_agent_src)
    config.run_dir.mkdir(parents=True, exist_ok=True)
    workspace = config.run_dir / "workspace"
    if config.workload.repo_template:
        copy_repo_template(config.workload.repo_template, workspace)
    else:
        workspace.mkdir(exist_ok=True)
    trajectory_path = config.run_dir / "trajectory.json"
    start = time.time()
    error = None
    exit_status = ""
    model = VLLMTextModel(
        base_url=config.endpoint,
        api_key=config.api_key,
        model_name=config.model,
        max_tokens=config.model_max_tokens,
        temperature=config.model_temperature,
    )
    env = None

    try:
        from minisweagent.agents.default import AgentConfig, DefaultAgent
        from minisweagent.environments.local import LocalEnvironment

        local_env = LocalEnvironment(
            cwd=str(workspace),
            env={
                "OMP_NUM_THREADS": str(config.cpu_threads_per_worker),
                "MKL_NUM_THREADS": str(config.cpu_threads_per_worker),
                "OPENBLAS_NUM_THREADS": str(config.cpu_threads_per_worker),
                "NUMEXPR_NUM_THREADS": str(config.cpu_threads_per_worker),
                "TOKENIZERS_PARALLELISM": "false",
            },
            timeout=config.command_timeout_seconds,
        )
        env = InstrumentedEnvironment(local_env)
        agent_config = AgentConfig(
            system_template=SYSTEM_TEMPLATE,
            instance_template=INSTANCE_TEMPLATE,
            step_limit=DEFAULT_AGENT_STEP_LIMIT,
            cost_limit=0.0,
            wall_time_limit_seconds=config.task_timeout_seconds,
            output_path=trajectory_path,
        )
        agent = DefaultAgent(model, env, config_class=lambda **_: agent_config)
        result = agent.run(config.workload.render_prompt())
        exit_status = result.get("exit_status", "")
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        (config.run_dir / "exception.txt").write_text(traceback.format_exc(), encoding="utf-8")

    end = time.time()
    command_outputs = [entry.get("output", "") for entry in (env.execution_log if env else [])]
    status = classify_run(exit_status, command_outputs, error)
    if status == "exception" and error and "TimeExceeded" in error:
        status = "timeout"
    llm_time = sum(float(call.get("duration_seconds", 0.0)) for call in model.call_log)
    bash_log = env.execution_log if env else []
    bash_time = sum(float(entry.get("duration_seconds", 0.0)) for entry in bash_log)
    workload_samples = []
    for entry in bash_log:
        workload_samples.extend(entry.get("workload_system_metrics", {}).get("_samples", []))
    workload_system_metrics = summarize_system_samples(workload_samples, prefix="workload_") if workload_samples else {}
    prompt_tokens = sum(int(call.get("prompt_tokens", 0)) for call in model.call_log)
    completion_tokens = sum(int(call.get("completion_tokens", 0)) for call in model.call_log)
    run_result = RunResult(
        run_id=config.run_id,
        workload=config.workload.name,
        concurrency=config.concurrency,
        status=status,
        exit_status=exit_status,
        total_wall_time_seconds=end - start,
        llm_time_total_seconds=llm_time,
        bash_time_total_seconds=bash_time,
        model_calls=model.n_calls,
        bash_calls=len(bash_log),
        validation_passed=status == "success",
        endpoint=config.endpoint,
        trajectory_path=str(trajectory_path) if trajectory_path.exists() else None,
        error=error,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        workload_system_metrics=workload_system_metrics,
        workspace=str(workspace),
        task_timeout_seconds=config.task_timeout_seconds,
        command_timeout_seconds=config.command_timeout_seconds,
        model_call_log=model.call_log,
        bash_execution_log=bash_log,
    )
    (config.run_dir / "run_result.json").write_text(json.dumps(to_jsonable(run_result), indent=2), encoding="utf-8")
    return run_result
