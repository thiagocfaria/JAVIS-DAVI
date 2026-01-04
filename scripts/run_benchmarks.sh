#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/Documentos/archive/benchmarks/$(date +%Y%m%d_%H%M%S)"

mkdir -p "${OUT_DIR}"

echo "Benchmark output: ${OUT_DIR}"

# System info (best effort)
{
  echo "=== uname ==="
  uname -a
  echo
  echo "=== lscpu ==="
  command -v lscpu >/dev/null 2>&1 && lscpu || echo "lscpu not available"
  echo
  echo "=== free ==="
  command -v free >/dev/null 2>&1 && free -h || echo "free not available"
} > "${OUT_DIR}/system_info.txt"

# Validator weight (cached / default)
python3 "${ROOT_DIR}/scripts/measure_validator_weight.py" --runs 5 \
  > "${OUT_DIR}/validator_weight_default.txt" 2>&1 || true

# Validator weight (no cache)
python3 "${ROOT_DIR}/scripts/measure_validator_weight.py" --runs 5 --no-cache \
  > "${OUT_DIR}/validator_weight_nocache.txt" 2>&1 || true

# Validator weight (full OCR worst-case)
JARVIS_OCR_FAST_MAX_DIM=0 python3 "${ROOT_DIR}/scripts/measure_validator_weight.py" --runs 5 --no-cache \
  > "${OUT_DIR}/validator_weight_full_ocr.txt" 2>&1 || true

# Local micro benchmarks (report format)
python3 "${ROOT_DIR}/scripts/measure_local_weights.py" --format report \
  > "${OUT_DIR}/local_weights_report.json" 2> "${OUT_DIR}/local_weights_report.err" || true

# Vision/automation benchmarks (auto backend)
python3 "${ROOT_DIR}/scripts/bench_vision_actions.py" --backend auto \
  > "${OUT_DIR}/vision_actions.json" 2> "${OUT_DIR}/vision_actions.err" || true

# Python vs Rust validator compare (text)
python3 "${ROOT_DIR}/scripts/compare_python_rust.py" \
  > "${OUT_DIR}/compare_python_rust.txt" 2>&1 || true

# Python vs Rust vision compare (json)
python3 "${ROOT_DIR}/scripts/compare_python_rust_vision.py" \
  > "${OUT_DIR}/compare_python_rust_vision.json" 2> "${OUT_DIR}/compare_python_rust_vision.err" || true

# Scenario tests (dry-run)
python3 "${ROOT_DIR}/scripts/run_scenarios.py" \
  > "${OUT_DIR}/scenario_results.json" 2> "${OUT_DIR}/scenario_results.err" || true

# Generate HTML/JSON reports (best effort)
python3 "${ROOT_DIR}/scripts/generate_report.py" "${OUT_DIR}/local_weights_report.json" \
  > "${OUT_DIR}/local_weights_report.log" 2>&1 || true
python3 "${ROOT_DIR}/scripts/generate_report.py" "${OUT_DIR}/vision_actions.json" \
  > "${OUT_DIR}/vision_actions_report.log" 2>&1 || true

# Compare with baseline (best effort)
python3 "${ROOT_DIR}/scripts/compare_baseline.py" "${OUT_DIR}/local_weights_report.json" \
  > "${OUT_DIR}/compare_baseline_local.txt" 2>&1 || true

echo "Done."
