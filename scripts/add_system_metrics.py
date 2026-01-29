#!/usr/bin/env python3
"""Adiciona métricas de sistema ao benchmark JSON."""
import json
import sys
from pathlib import Path


def add_metrics(json_file: str, temp: str, load: str):
    """Adiciona pre_run_temp_celsius e pre_run_load_avg ao benchmark config."""
    path = Path(json_file)
    with open(path) as f:
        data = json.load(f)

    if "benchmark_config" not in data:
        data["benchmark_config"] = {}

    data["benchmark_config"]["pre_run_temp_celsius"] = temp
    data["benchmark_config"]["pre_run_load_avg"] = load

    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"✅ Added system metrics to {path.name}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python add_system_metrics.py <json_file> <temp> <load>")
        sys.exit(1)
    add_metrics(sys.argv[1], sys.argv[2], sys.argv[3])
