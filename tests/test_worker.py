from cpu_swe_benchmark.worker import DEFAULT_AGENT_STEP_LIMIT


def test_worker_default_agent_step_limit_allows_debug_fix_validate_submit_loop():
    assert DEFAULT_AGENT_STEP_LIMIT == 20
