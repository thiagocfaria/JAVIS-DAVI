#!/usr/bin/env python3
"""Compara WER e latência entre modelos."""
import json
from pathlib import Path


def compare_models() -> None:
    """Compara WER vs latência para tiny/small/base."""
    models = ["tiny", "small", "base"]
    base_dir = Path("Documentos/DOC_INTERFACE/benchmarks")

    print("=" * 80)
    print("MODEL COMPARISON: WER vs LATENCY TRADE-OFF")
    print("=" * 80)
    print()

    results = []
    for model in models:
        wer_file = base_dir / f"wer_{model}.json"
        lat_file = base_dir / f"latency_{model}.json"

        if not wer_file.exists():
            print(f"⚠️  {model}: wer_{model}.json not found")
            continue
        if not lat_file.exists():
            print(f"⚠️  {model}: latency_{model}.json not found")
            continue

        try:
            with open(wer_file) as f:
                wer_data = json.load(f)
            with open(lat_file) as f:
                lat_data = json.load(f)

            wer = wer_data.get("wer_global", 0) * 100
            p50 = lat_data.get("latency_ms_p50", 0)
            p95 = lat_data.get("latency_ms_p95", 0)

            results.append({"model": model, "wer": wer, "p50": p50, "p95": p95})
        except Exception as e:
            print(f"❌ {model}: Error reading JSON - {e}")

    if not results:
        print("❌ No valid results found")
        return

    print(f"{'Model':<8} | {'WER':<8} | {'p50 (ms)':<10} | {'p95 (ms)':<10} | GOLD OK?")
    print("-" * 80)
    for r in results:
        gold_ok = "✅" if r["p95"] < 1200 else "❌"
        print(f"{r['model']:<8} | {r['wer']:>6.1f}% | {r['p50']:>10.0f} | {r['p95']:>10.0f} | {gold_ok}")
    print()

    gold_candidates = [r for r in results if r["p95"] < 1200]
    if gold_candidates:
        best = min(gold_candidates, key=lambda x: x["wer"])
        print(f"✅ RECOMMENDATION: {best['model']} (WER: {best['wer']:.1f}% | p95: {best['p95']:.0f}ms)")
    else:
        fastest = min(results, key=lambda x: x["p95"])
        print(f"⚠️  No model meets GOLD target. Fastest: {fastest['model']} (p95: {fastest['p95']:.0f}ms)")


if __name__ == "__main__":
    compare_models()
