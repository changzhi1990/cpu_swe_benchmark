from cpu_swe_benchmark.schemas import RunResult, to_jsonable
from cpu_swe_benchmark.worker import DEFAULT_AGENT_STEP_LIMIT


def test_worker_default_agent_step_limit_allows_debug_fix_validate_submit_loop():
    assert DEFAULT_AGENT_STEP_LIMIT == 20


def test_run_result_serializes_task_total_tokens():
    result = RunResult(
        run_id="sorting_c001_w000",
        workload="sorting",
        concurrency=1,
        status="success",
        exit_status="Submitted",
        total_wall_time_seconds=10.0,
        llm_time_total_seconds=3.0,
        bash_time_total_seconds=6.0,
        model_calls=2,
        bash_calls=2,
        validation_passed=True,
        endpoint="http://localhost:8000/v1",
        trajectory_path=None,
        error=None,
        prompt_tokens=100,
        completion_tokens=20,
        total_tokens=135,
    )

    assert to_jsonable(result)["total_tokens"] == 135
