#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_bench(backend: str, runs: int) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "bench_vision_actions.py"),
        "--backend",
        backend,
        "--runs",
        str(runs),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, env=os.environ.copy())
    if result.returncode != 0:
        return {"error": (result.stderr or result.stdout).strip(), "backend": backend}
    try:
        return json.loads(result.stdout)
    except Exception as exc:
        return {"error": f"invalid_json:{exc}", "backend": backend}


def _speedup(py: float, rs: float) -> float:
    if rs <= 0:
        return 0.0
    return py / rs


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Python vs Rust vision benchmarks")
    parser.add_argument("--runs", type=int, default=5, help="number of runs per metric")
    parser.add_argument("--output", type=str, help="output JSON path (optional)")
    args = parser.parse_args()

    py = _run_bench("python", args.runs)
    rs = _run_bench("rust", args.runs)

    summary = {
        "python": py,
        "rust": rs,
        "comparisons": [],
    }

    metrics = ["screenshot_capture", "ocr_fast", "ocr_full", "validator_full_ocr"]
    for metric in metrics:
        py_val = py.get("latency", {}).get(metric)
        rs_val = rs.get("latency", {}).get(metric)
        if isinstance(py_val, (int, float)) and isinstance(rs_val, (int, float)):
            summary["comparisons"].append(
                {
                    "metric": metric,
                    "python_ms": py_val,
                    "rust_ms": rs_val,
                    "speedup": round(_speedup(py_val, rs_val), 3),
                }
            )

    output = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
