from cpu_swe_benchmark.cli import build_parser


def test_cli_defaults_to_algorithm_lab_sorting_bugfix_only():
    args = build_parser().parse_args([])

    assert args.workloads == "algorithm_lab_sorting_bugfix"
    assert "algorithm_lab_sorting_bugfix" in args.output_dir
    assert args.model_max_tokens == 512
