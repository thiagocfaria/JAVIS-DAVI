#!/usr/bin/env python3
"""Analisa long-run benchmark para detectar degradação."""
import json
import sys
from pathlib import Path


def analyze_longrun(json_file: str) -> None:
    """Analisa distribuição de slow runs para detectar degradação temporal."""
    path = Path(json_file)
    if not path.exists():
        print(f"❌ File not found: {json_file}")
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    repeat = data.get("repeat", 0)
    p95 = data.get("latency_ms_p95", 0)
    rss_mb = data.get("psutil_rss_bytes", 0) / 1024 / 1024

    top_10 = data.get("top_10_slow_runs", [])
    if not top_10:
        print("❌ No top_10_slow_runs data in JSON")
        sys.exit(1)

    slow_iters = [run["iteration"] for run in top_10]

    # Quartiles
    q1 = repeat // 4
    q2 = repeat // 2
    q3 = 3 * repeat // 4

    quartile_counts = {
        "Q1 (0-25%)": sum(1 for i in slow_iters if i < q1),
        "Q2 (25-50%)": sum(1 for i in slow_iters if q1 <= i < q2),
        "Q3 (50-75%)": sum(1 for i in slow_iters if q2 <= i < q3),
        "Q4 (75-100%)": sum(1 for i in slow_iters if i >= q3),
    }

    print("=" * 60)
    print("LONG-RUN DEGRADATION ANALYSIS")
    print("=" * 60)
    print(f"Total iterations: {repeat}")
    print(f"p95: {p95:.1f}ms")
    print(f"RSS: {rss_mb:.1f}MB")
    print()

    print("Slow runs distribution (top 10):")
    for quartile, count in quartile_counts.items():
        bar = "█" * count + "░" * (10 - count)
        print(f"  {quartile}: {count:2d}/10 {bar}")
    print()

    # Degradation check
    late_runs = quartile_counts["Q3 (50-75%)"] + quartile_counts["Q4 (75-100%)"]

    if late_runs > 7:
        print("⚠️  DEGRADATION DETECTED: Slow runs clustered in late iterations")
        print(f"   Late runs: {late_runs}/10 (> 70%)")
    elif late_runs > sum(quartile_counts.values()) // 2 * 2:
        print("⚠️  DEGRADATION SUSPECTED: 2x more slow runs in late iterations")
    else:
        print("✅ NO DEGRADATION: Slow runs evenly distributed")
    print()

    print("Memory leak check:")
    print(f"  Final RSS: {rss_mb:.1f}MB")
    if rss_mb > 500:
        print("  ⚠️  High RSS - possible leak")
    else:
        print("  ✅ RSS within expected range")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_longrun.py <json_file>")
        sys.exit(1)
    analyze_longrun(sys.argv[1])
