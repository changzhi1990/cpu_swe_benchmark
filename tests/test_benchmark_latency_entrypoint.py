import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_benchmark_latency():
    spec = importlib.util.spec_from_file_location("benchmark_latency", ROOT / "benchmark_latency.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_benchmark_latency_exposes_reference_style_benchmarker():
    module = load_benchmark_latency()

    assert hasattr(module, "LatencyBenchmarker")
    benchmarker = module.LatencyBenchmarker(
        model_config={
            "model_name": "qwen2.5-coder-32b",
            "base_url": "http://localhost:8000/v1",
            "api_key": "token-abc123",
        },
        output_dir="results/test",
    )
    assert benchmarker.model_config["model_name"] == "qwen2.5-coder-32b"
    assert benchmarker.output_dir == Path("results/test")
    assert hasattr(benchmarker, "run_algorithm_lab_sorting_bugfix_benchmark")


def test_benchmark_latency_parser_defaults_to_algorithm_lab_sorting_bugfix_sweep():
    module = load_benchmark_latency()
    parser = module.build_parser()
    args = parser.parse_args([])

    assert args.benchmark_type == "algorithm_lab_sorting_bugfix"
    assert args.concurrency_levels == "1,2,4,8,16,32,64,128"
    assert args.model_path == "qwen2.5-coder-32b"
    assert args.base_url == "http://localhost:8000/v1"
    assert args.max_tokens == 512


def test_benchmark_latency_rejects_removed_synthetic_workloads():
    module = load_benchmark_latency()
    parser = module.build_parser()

    try:
        parser.parse_args(["--benchmark-type", "memory_bandwidth_utilization"])
    except SystemExit:
        return

    raise AssertionError("removed synthetic workload was accepted")
