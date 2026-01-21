#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jarvis.cerebro.config import load_config
from jarvis.cerebro.orchestrator import Orchestrator


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
    parser = argparse.ArgumentParser(
        description="Run scenario tests (dry-run by default)"
    )
    parser.add_argument(
        "--file",
        default=str(ROOT / "Documentos" / "benchmarks" / "scenarios.json"),
        help="scenarios json file",
    )
    parser.add_argument("--real", action="store_true", help="execute real actions")
    parser.add_argument("--output", type=str, help="output JSON path (optional)")
    args = parser.parse_args()

    scenario_path = Path(args.file)
    data = json.loads(scenario_path.read_text(encoding="utf-8"))

    orchestrator = _build_orchestrator(dry_run=not args.real)
    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "dry_run": not args.real,
        "scenarios": [],
    }

    for scenario in data.get("scenarios", []):
        name = scenario.get("name", "unnamed")
        commands = scenario.get("commands", [])
        scenario_result = {"name": name, "commands": []}
        for command in commands:
            start = time.perf_counter()
            with redirect_stdout(io.StringIO()):
                orchestrator.handle_text(command)
            duration_ms = (time.perf_counter() - start) * 1000.0
            scenario_result["commands"].append(
                {
                    "command": command,
                    "duration_ms": round(duration_ms, 2),
                    "success": bool(orchestrator.last_success),
                    "error": orchestrator.last_error,
                }
            )
        results["scenarios"].append(scenario_result)

    output = json.dumps(results, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
