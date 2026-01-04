#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from contextlib import contextmanager, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jarvis.cerebro.actions import Action, ActionPlan
from jarvis.cerebro.config import load_config
from jarvis.cerebro.orchestrator import Orchestrator
from jarvis.validacao.validator import Validator

try:
    from PIL import Image, ImageDraw  # type: ignore
except ImportError:
    Image = None
    ImageDraw = None


def _read_rss_mb() -> float:
    try:
        with open("/proc/self/status", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        kb = int(parts[1])
                        return kb / 1024.0
    except Exception:
        return 0.0
    return 0.0


@dataclass
class Metric:
    latency_ms: float
    cpu_pct: float
    rss_mb: float

    def to_dict(self) -> dict[str, float]:
        return {
            "latency_ms": self.latency_ms,
            "cpu_pct": self.cpu_pct,
            "rss_mb": self.rss_mb,
        }


def _measure(func, runs: int = 5, iterations: int = 1) -> Metric:
    latencies: list[float] = []
    cpu_pcts: list[float] = []
    rss_vals: list[float] = []
    for _ in range(runs):
        start_rss = _read_rss_mb()
        start_wall = time.perf_counter()
        start_cpu = time.process_time()
        for _ in range(iterations):
            func()
        end_cpu = time.process_time()
        end_wall = time.perf_counter()
        end_rss = _read_rss_mb()
        wall = max(end_wall - start_wall, 1e-6)
        cpu = max(end_cpu - start_cpu, 0.0)
        latencies.append(wall * 1000.0)
        cpu_pcts.append((cpu / wall) * 100.0)
        rss_vals.append(max(end_rss, start_rss))
        time.sleep(0.05)
    return Metric(
        latency_ms=median(latencies),
        cpu_pct=median(cpu_pcts),
        rss_mb=median(rss_vals),
    )


@contextmanager
def _temp_env(overrides: dict[str, str | None]):
    original = {}
    for key, value in overrides.items():
        original[key] = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    try:
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _build_sample_image() -> Image.Image | None:
    if Image is None or ImageDraw is None:
        return None
    img = Image.new("RGB", (1920, 1080), color="white")
    draw = ImageDraw.Draw(img)
    lines = [
        "Jarvis QA Benchmark",
        "Linha 1: O rapido rapaz marrom salta sobre o cao preguicoso.",
        "Linha 2: 0123456789 - ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "Linha 3: lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    ]
    y = 50
    for line in lines:
        draw.text((50, y), line, fill="black")
        y += 60
    return img


def _apply_backend(backend: str) -> None:
    if backend == "python":
        os.environ["JARVIS_DISABLE_RUST_VISION"] = "1"
        os.environ.pop("JARVIS_FORCE_RUST_VISION", None)
    elif backend == "rust":
        os.environ.pop("JARVIS_DISABLE_RUST_VISION", None)
        os.environ["JARVIS_FORCE_RUST_VISION"] = "1"
    else:
        os.environ.pop("JARVIS_FORCE_RUST_VISION", None)


def _build_orchestrator(dry_run: bool) -> Orchestrator:
    os.environ["JARVIS_LOCAL_LLM_BASE_URL"] = ""
    os.environ["JARVIS_BROWSER_AI_ENABLED"] = "false"
    os.environ["JARVIS_MAX_GUIDANCE_ATTEMPTS"] = "0"
    os.environ["JARVIS_REQUIRE_APPROVAL"] = "false"
    os.environ["JARVIS_CHAT_AUTO_OPEN"] = "false"
    os.environ["JARVIS_STT_MODE"] = "none"
    os.environ["JARVIS_TTS_MODE"] = "none"
    os.environ["JARVIS_DRY_RUN"] = "true" if dry_run else "false"
    config = load_config()
    return Orchestrator(config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark OCR/screenshot/automation (QA)")
    parser.add_argument("--runs", type=int, default=5, help="number of runs per metric")
    parser.add_argument(
        "--backend",
        choices=("auto", "python", "rust"),
        default="auto",
        help="vision backend to use",
    )
    parser.add_argument(
        "--real-actions",
        action="store_true",
        help="execute real automation actions (WARNING: will interact with the desktop)",
    )
    parser.add_argument("--output", type=str, help="output JSON path (optional)")
    args = parser.parse_args()

    _apply_backend(args.backend)

    results: dict[str, object] = {
        "latency": {},
        "cpu": {},
        "memory": {},
        "meta": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "backend": args.backend,
            "dry_run_actions": not args.real_actions,
        },
        "skipped": {},
        "checks": {},
    }

    def record_metric(name: str, metric: Metric) -> None:
        results["latency"][name] = metric.latency_ms
        results["cpu"][name] = metric.cpu_pct
        results["memory"][name] = metric.rss_mb

    # Screenshot benchmark
    validator = None
    try:
        validator = Validator(enable_ocr=True, save_screenshots=False, mask_screenshots=True)
    except Exception as exc:
        results["skipped"]["validator_init"] = f"validator_init_failed:{exc}"
    else:
        backend = "none"
        if getattr(validator, "_rust_validator", None) is not None:
            backend = "rust"
        elif validator.enable_ocr:
            backend = "pytesseract"
        results["meta"]["vision_backend"] = backend

    screenshot = None
    if validator is not None:
        screenshot = validator.take_screenshot()
        if screenshot is None:
            results["skipped"]["screenshot_capture"] = "screenshot_unavailable"
        else:
            record_metric(
                "screenshot_capture",
                _measure(lambda: validator.take_screenshot() or True, runs=args.runs),
            )

    # OCR benchmarks (fast vs full)
    sample_image = _build_sample_image()
    ocr_image = screenshot or sample_image
    if ocr_image is None:
        results["skipped"]["ocr_fast"] = "no_image_available"
        results["skipped"]["ocr_full"] = "no_image_available"
    else:
        with _temp_env({"JARVIS_OCR_DISABLE_CACHE": "1", "JARVIS_OCR_FAST_MAX_DIM": "540"}):
            try:
                fast_validator = Validator(enable_ocr=True, save_screenshots=False, mask_screenshots=True)
            except Exception as exc:
                results["skipped"]["ocr_fast"] = f"validator_init_failed:{exc}"
            else:
                if not fast_validator.enable_ocr:
                    results["skipped"]["ocr_fast"] = "ocr_backend_unavailable"
                else:
                    record_metric(
                        "ocr_fast",
                        _measure(lambda: fast_validator.extract_text_ocr(ocr_image), runs=args.runs),
                    )
                    fast_text = fast_validator.extract_text_ocr(ocr_image)

        with _temp_env({"JARVIS_OCR_DISABLE_CACHE": "1", "JARVIS_OCR_FAST_MAX_DIM": "0"}):
            try:
                full_validator = Validator(enable_ocr=True, save_screenshots=False, mask_screenshots=True)
            except Exception as exc:
                results["skipped"]["ocr_full"] = f"validator_init_failed:{exc}"
            else:
                if not full_validator.enable_ocr:
                    results["skipped"]["ocr_full"] = "ocr_backend_unavailable"
                else:
                    record_metric(
                        "ocr_full",
                        _measure(lambda: full_validator.extract_text_ocr(ocr_image), runs=args.runs),
                    )
                    full_text = full_validator.extract_text_ocr(ocr_image)

        # OCR regression check
        if "fast_text" in locals() and "full_text" in locals():
            try:
                import difflib

                ratio = difflib.SequenceMatcher(None, fast_text, full_text).ratio()
                results["checks"]["ocr_fast_vs_full_similarity"] = {
                    "ratio": round(ratio, 4),
                    "fast_len": len(fast_text),
                    "full_len": len(full_text),
                }
            except Exception as exc:
                results["skipped"]["ocr_regression"] = f"diff_failed:{exc}"

    # Validator full check (worst-case OCR)
    with _temp_env({"JARVIS_OCR_DISABLE_CACHE": "1", "JARVIS_OCR_FAST_MAX_DIM": "0"}):
        try:
            full_validator = Validator(enable_ocr=True, save_screenshots=False, mask_screenshots=True)
        except Exception as exc:
            results["skipped"]["validator_full_ocr"] = f"validator_init_failed:{exc}"
        else:
            if not full_validator.enable_ocr:
                results["skipped"]["validator_full_ocr"] = "ocr_backend_unavailable"
            else:
                action = Action("open_url", {"url": "https://example.com"})
                record_metric(
                    "validator_full_ocr",
                    _measure(lambda: full_validator.validate(action), runs=args.runs),
                )

    # Automation (dry-run by default)
    orchestrator = _build_orchestrator(dry_run=not args.real_actions)
    actions = {
        "automation_click": Action("click", {"x": 10, "y": 10}),
        "automation_type_text": Action("type_text", {"text": "teste"}),
        "automation_open_url": Action("open_url", {"url": "https://example.com"}),
        "automation_open_app": Action("open_app", {"app": "xterm"}),
    }
    for label, action in actions.items():
        plan = ActionPlan(actions=[action], risk_level="low", notes="bench")
        def run_action() -> None:
            with redirect_stdout(io.StringIO()):
                orchestrator._execute_plan(plan)
        record_metric(label, _measure(run_action, runs=args.runs))

    output = json.dumps(results, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
