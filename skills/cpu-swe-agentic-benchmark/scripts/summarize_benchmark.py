#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path

FIELDS = [
    "workload",
    "concurrency",
    "E2E_p90_seconds",
    "TTFT_p90",
    "TPOT_p90",
    "success_rate",
    "run_results",
    "memory_bandwidth_total_p90_gbps",
    "memory_bandwidth_total_max_gbps",
    "memory_bandwidth_read_p90_gbps",
    "memory_bandwidth_read_max_gbps",
    "memory_bandwidth_write_p90_gbps",
    "memory_bandwidth_write_max_gbps",
]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: summarize_benchmark.py <benchmark-output-dir>", file=sys.stderr)
        return 2

    out = Path(sys.argv[1])
    src = out / "global_summary.csv"
    if not src.exists():
        print(f"missing global summary: {src}", file=sys.stderr)
        return 1

    rows = []
    with src.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append({
                "workload": row.get("workload", ""),
                "concurrency": row.get("concurrency", ""),
                "E2E_p90_seconds": row.get("E2E_p90_seconds", ""),
                "TTFT_p90": row.get("TTFT_p90", ""),
                "TPOT_p90": row.get("TPOT_p90", ""),
                "success_rate": row.get("success_rate", ""),
                "run_results": f"{row.get('successful_tasks', '')}/{row.get('submitted_tasks', '')} success, {row.get('failed_tasks', '')} failed",
                "memory_bandwidth_total_p90_gbps": row.get("memory_bandwidth_total_p90_gbps", ""),
                "memory_bandwidth_total_max_gbps": row.get("memory_bandwidth_total_max_gbps", ""),
                "memory_bandwidth_read_p90_gbps": row.get("memory_bandwidth_read_p90_gbps", ""),
                "memory_bandwidth_read_max_gbps": row.get("memory_bandwidth_read_max_gbps", ""),
                "memory_bandwidth_write_p90_gbps": row.get("memory_bandwidth_write_p90_gbps", ""),
                "memory_bandwidth_write_max_gbps": row.get("memory_bandwidth_write_max_gbps", ""),
            })

    dst = out / "requested_metrics.csv"
    with dst.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"requested_csv={dst}")
    print(f"row_count={len(rows)}")
    print(",".join(FIELDS))
    for row in rows:
        print(",".join(row[field] for field in FIELDS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
