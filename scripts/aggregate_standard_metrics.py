#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate standard global/CPU/GPU/vLLM metrics for a runset")
    parser.add_argument("runset_dir", help="Runset directory containing manifest.csv")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "src"))
    from cpu_swe_benchmark.standard_metrics import aggregate_standard_metrics

    outputs = aggregate_standard_metrics(Path(args.runset_dir))
    print(f"cpu_metrics={outputs.cpu_metrics}")
    print(f"gpu_metrics={outputs.gpu_metrics}")
    print(f"vllm_metrics={outputs.vllm_metrics}")
    print(f"global_metrics={outputs.global_metrics}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
