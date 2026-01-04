#!/usr/bin/env python3
"""
Script para comparar resultados de benchmarks com baseline.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "Documentos" / "benchmarks" / "baseline.json"


def load_baseline() -> dict[str, Any]:
    """Carrega o arquivo de baseline."""
    if not BASELINE_PATH.exists():
        print(f"ERRO: Baseline não encontrado em {BASELINE_PATH}")
        sys.exit(1)
    with open(BASELINE_PATH, encoding="utf-8") as f:
        return json.load(f)


def compare_metrics(
    baseline: dict[str, Any], results: dict[str, Any], metric_type: str
) -> dict[str, Any]:
    """Compara métricas com baseline e retorna relatório."""
    report: dict[str, Any] = {
        "metric_type": metric_type,
        "comparisons": [],
        "regressions": [],
        "improvements": [],
    }

    baseline_metrics = baseline.get("metrics", {}).get(metric_type, {}).get("baseline", {})
    threshold = baseline.get("regression_threshold", {})

    for key, current_value in results.items():
        if key not in baseline_metrics:
            continue

        baseline_value = baseline_metrics[key]
        if baseline_value == 0:
            continue

        diff_pct = ((current_value - baseline_value) / baseline_value) * 100.0

        comparison = {
            "metric": key,
            "baseline": baseline_value,
            "current": current_value,
            "diff_pct": round(diff_pct, 2),
        }

        report["comparisons"].append(comparison)

        # Verificar regressão
        if metric_type == "latency":
            threshold_pct = threshold.get("latency_pct", 3.0)
            if diff_pct > threshold_pct:
                report["regressions"].append(comparison)
        elif metric_type == "cpu":
            threshold_pct = threshold.get("cpu_pct", 5.0)
            if diff_pct > threshold_pct:
                report["regressions"].append(comparison)
        elif metric_type == "memory":
            threshold_pct = threshold.get("memory_pct", 10.0)
            if diff_pct > threshold_pct:
                report["regressions"].append(comparison)

        # Melhorias (redução)
        if diff_pct < -5.0:
            report["improvements"].append(comparison)

    return report


def main() -> None:
    """Função principal."""
    if len(sys.argv) < 2:
        print("Uso: compare_baseline.py <arquivo_resultados.json>")
        sys.exit(1)

    results_path = Path(sys.argv[1])
    if not results_path.exists():
        print(f"ERRO: Arquivo de resultados não encontrado: {results_path}")
        sys.exit(1)

    baseline = load_baseline()
    with open(results_path, encoding="utf-8") as f:
        results = json.load(f)

    print("=" * 60)
    print("COMPARAÇÃO COM BASELINE")
    print("=" * 60)

    # Comparar cada tipo de métrica
    for metric_type in ["latency", "cpu", "memory"]:
        if metric_type not in results:
            continue

        report = compare_metrics(baseline, results[metric_type], metric_type)
        print(f"\n[{metric_type.upper()}]")
        print("-" * 60)

        if report["regressions"]:
            print("⚠️  REGRESSÕES DETECTADAS:")
            for reg in report["regressions"]:
                print(
                    f"  {reg['metric']}: {reg['baseline']:.2f} -> {reg['current']:.2f} "
                    f"(+{reg['diff_pct']:.2f}%)"
                )
        else:
            print("✓ Sem regressões")

        if report["improvements"]:
            print("\n✓ MELHORIAS:")
            for imp in report["improvements"]:
                print(
                    f"  {imp['metric']}: {imp['baseline']:.2f} -> {imp['current']:.2f} "
                    f"({imp['diff_pct']:.2f}%)"
                )

        if report["comparisons"] and not report["regressions"] and not report["improvements"]:
            print("→ Sem mudanças significativas")

    print("\n" + "=" * 60)
    print("FIM DA COMPARAÇÃO")
    print("=" * 60)


if __name__ == "__main__":
    main()



