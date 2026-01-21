#!/usr/bin/env python3
"""
Compara performance Python vs Rust para o validator.
"""
from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_measurement(rust_disabled: bool, cache_disabled: bool, label: str) -> dict:
    """Executa medição e retorna resultados."""
    env = {}
    if rust_disabled:
        env["JARVIS_DISABLE_RUST_VISION"] = "1"
    if cache_disabled:
        env["JARVIS_OCR_DISABLE_CACHE"] = "1"

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "measure_validator_weight.py"),
        "--runs",
        "5",
    ]
    if rust_disabled:
        cmd.append("--no-rust")
    if cache_disabled:
        cmd.append("--no-cache")

    merged_env = os.environ.copy()
    merged_env.update(env)
    result = subprocess.run(
        cmd, capture_output=True, text=True, env=merged_env, cwd=ROOT
    )

    if result.returncode != 0:
        error_text = (result.stderr or result.stdout or "").strip()
        return {
            "error": error_text or f"returncode={result.returncode}",
            "label": label,
        }

    # Parse output
    output = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            output[key.strip()] = value.strip()

    return {"label": label, **output}


def main() -> None:
    """Função principal."""

    print("=" * 60)
    print("COMPARAÇÃO PYTHON vs RUST")
    print("=" * 60)

    results = []

    # Python com cache
    print("\n[1/4] Medindo Python (com cache)...")
    results.append(
        run_measurement(
            rust_disabled=True, cache_disabled=False, label="Python (cache)"
        )
    )

    # Python sem cache
    print("[2/4] Medindo Python (sem cache)...")
    results.append(
        run_measurement(
            rust_disabled=True, cache_disabled=True, label="Python (no cache)"
        )
    )

    # Rust com cache
    print("[3/4] Medindo Rust (com cache)...")
    results.append(
        run_measurement(rust_disabled=False, cache_disabled=False, label="Rust (cache)")
    )

    # Rust sem cache
    print("[4/4] Medindo Rust (sem cache)...")
    results.append(
        run_measurement(
            rust_disabled=False, cache_disabled=True, label="Rust (no cache)"
        )
    )

    print("\n" + "=" * 60)
    print("RESULTADOS")
    print("=" * 60)

    for result in results:
        if "error" in result:
            print(f"\n❌ {result['label']}: ERRO")
            print(f"   {result['error']}")
        else:
            median = result.get("median_s", "N/A")
            weight = result.get("suggested_weight", "N/A")
            print(f"\n✓ {result['label']}:")
            print(f"   Mediana: {median}s")
            print(f"   Peso sugerido: {weight}")

    # Comparação
    print("\n" + "=" * 60)
    print("ANÁLISE")
    print("=" * 60)

    python_result = next(
        (r for r in results if r.get("label") == "Python (cache)"), None
    )
    rust_result = next((r for r in results if r.get("label") == "Rust (cache)"), None)

    if (
        python_result
        and rust_result
        and "median_s" in python_result
        and "median_s" in rust_result
    ):
        try:
            python_median = float(python_result["median_s"])
            rust_median = float(rust_result["median_s"])
            speedup = python_median / rust_median if rust_median > 0 else 0
            print(f"\n🚀 Speedup Rust vs Python: {speedup:.2f}x")
            if speedup > 1.2:
                print("   ✓ Rust é significativamente mais rápido")
            elif speedup < 0.8:
                print("   ⚠️  Python é mais rápido (verificar configuração)")
            else:
                print("   → Performance similar")
        except (ValueError, KeyError):
            print("\n⚠️  Não foi possível calcular speedup")


if __name__ == "__main__":
    main()
