#!/usr/bin/env python3
import argparse
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jarvis.cerebro.actions import Action
from jarvis.validacao.validator import Validator


def measure(runs: int, disable_rust: bool, disable_cache: bool) -> list[float]:
    if disable_rust:
        os.environ["JARVIS_DISABLE_RUST_VISION"] = "1"
    else:
        os.environ.pop("JARVIS_DISABLE_RUST_VISION", None)
    if disable_cache:
        os.environ["JARVIS_OCR_DISABLE_CACHE"] = "1"
    else:
        os.environ.pop("JARVIS_OCR_DISABLE_CACHE", None)

    validator = Validator(enable_ocr=True, save_screenshots=False)
    action = Action(action_type="open_url", params={"url": "https://example.com"})
    timings = []
    for _ in range(runs):
        t0 = time.perf_counter()
        validator.validate(action)
        timings.append(time.perf_counter() - t0)
        time.sleep(0.05)
    return timings


def weight_from_median(median_s: float) -> int:
    return max(1, min(100, round(median_s * 20)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure Olhos do sistema weight")
    parser.add_argument("--runs", type=int, default=5, help="number of runs")
    parser.add_argument("--no-rust", action="store_true", help="force Python fallback")
    parser.add_argument("--no-cache", action="store_true", help="disable OCR cache")
    args = parser.parse_args()

    times = measure(args.runs, args.no_rust, args.no_cache)
    median_s = statistics.median(times)
    weight = weight_from_median(median_s)

    mode = "python" if args.no_rust else "rust"
    print(f"mode={mode}")
    print(f"times_s={times}")
    print(f"median_s={median_s:.4f}")
    print(f"suggested_weight={weight}")


if __name__ == "__main__":
    main()
