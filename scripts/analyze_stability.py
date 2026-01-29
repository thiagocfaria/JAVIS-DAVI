#!/usr/bin/env python3
"""
Analisa estabilidade dos benchmarks de eos_to_first_audio.

Valida se p95 < 1200ms em múltiplos runs.
"""

import json
import os
import sys
from pathlib import Path


def analyze_stability(json_files: list[str]) -> None:
    """Analisa estabilidade através de múltiplos benchmarks."""
    print("=" * 60)
    print("ANÁLISE DE ESTABILIDADE - eos_to_first_audio")
    print("=" * 60)
    print()

    results = []
    for json_file in json_files:
        path = Path(json_file)
        if not path.exists():
            print(f"⚠️  {path.name}: Arquivo não encontrado")
            continue

        with open(path) as f:
            data = json.load(f)

        p50 = data.get("eos_to_first_audio_ms_p50", 0)
        p95 = data.get("eos_to_first_audio_ms_p95", 0)
        p99 = data.get("latency_ms_p99", 0)  # Fixed: use latency_ms_p99 (was looking for eos_to_first_audio_ms_p99)
        cpu_time = data.get("cpu_time_s_avg", 0)
        cpu_percent = data.get("cpu_percent", 0)
        rss_mb = data.get("psutil_rss_bytes", 0) / 1024 / 1024
        backend = data.get("benchmark_config", {}).get("stt_backend", "unknown")

        # Validação adicional com multi-thread support
        # Fallback: se não tiver cpu_threads no JSON, usar os.cpu_count()
        cpu_threads = data.get("benchmark_config", {}).get("cpu_threads")
        if cpu_threads is None:
            cpu_threads = os.cpu_count() or 1  # Fallback to actual CPU count
        cpu_limit = max(200, cpu_threads * 100 * 1.1)  # Min 200% to allow single-thread spikes
        cpu_contention = cpu_percent > cpu_limit

        # p99 validation: considerar null, 0, ou ausente como inválido
        p99_invalid = (p99 is None) or (p99 == 0)

        temp = data.get("benchmark_config", {}).get("pre_run_temp_celsius", "N/A")
        load = data.get("benchmark_config", {}).get("pre_run_load_avg", "N/A")

        results.append({
            "file": path.name,
            "backend": backend,
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "cpu_time": cpu_time,
            "cpu_percent": cpu_percent,
            "cpu_threads": cpu_threads,
            "cpu_limit": cpu_limit,
            "rss_mb": rss_mb,
            "valid": not (cpu_contention or p99_invalid),
            "issues": [],
        })

        if cpu_contention:
            results[-1]["issues"].append(f"CPU contention (cpu_percent={cpu_percent:.1f}% > {cpu_limit:.0f}%)")
        if p99_invalid:
            results[-1]["issues"].append(f"Invalid p99 data (p99={p99})")

        status = "✅ PASS" if p95 < 1200 and results[-1]["valid"] else "❌ FAIL"
        print(f"{path.name}:")
        print(f"  Backend: {backend}")
        print(f"  System: TEMP={temp}°C LOAD={load}")
        print(f"  p50: {p50:.1f}ms | p95: {p95:.1f}ms | p99: {p99 if p99 else 'NULL'}ms")
        print(f"  CPU: {cpu_time:.2f}s ({cpu_percent:.1f}% / limit: {cpu_limit:.0f}%) | Threads: {cpu_threads} | RSS: {rss_mb:.1f}MB")
        if results[-1]["issues"]:
            print(f"  ⚠️  Issues: {', '.join(results[-1]['issues'])}")
        print(f"  Status: {status} (p95 < 1200ms, p99 valid, cpu% <= {cpu_limit:.0f}%)")
        print()

    if not results:
        print("❌ Nenhum resultado encontrado")
        return

    # Summary
    print("=" * 60)
    print("RESUMO")
    print("=" * 60)
    print()

    p95_values = [r["p95"] for r in results]
    p95_min = min(p95_values)
    p95_max = max(p95_values)
    p95_avg = sum(p95_values) / len(p95_values)
    p95_variance = max(p95_values) - min(p95_values)

    print(f"Runs analisados: {len(results)}")
    print(f"p95 MIN: {p95_min:.1f}ms")
    print(f"p95 MAX: {p95_max:.1f}ms")
    print(f"p95 AVG: {p95_avg:.1f}ms")
    print(f"p95 VARIANCE: {p95_variance:.1f}ms")
    print()

    all_pass = all(r["p95"] < 1200 and r["valid"] for r in results)
    all_p95_pass = all(r["p95"] < 1200 for r in results)

    if all_pass:
        print("✅ ESTABILIDADE VALIDADA: Todos os runs passaram (p95 < 1200ms + válidos)")
    elif all_p95_pass:
        print("⚠️  P95 PASSOU mas alguns runs têm problemas (CPU contention ou p99 inválido):")
        for r in results:
            if not r["valid"]:
                print(f"   {r['file']}: {', '.join(r['issues'])}")
    else:
        fails = [r["file"] for r in results if r["p95"] >= 1200]
        print(f"❌ ESTABILIDADE FALHOU: {len(fails)} run(s) com p95 >= 1200ms")
        print(f"   Fails: {', '.join(fails)}")

    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python analyze_stability.py <json1> <json2> ...")
        sys.exit(1)

    analyze_stability(sys.argv[1:])
