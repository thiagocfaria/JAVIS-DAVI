#!/usr/bin/env python
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ARTIFACTS = Path("artifacts")
ARTIFACTS.mkdir(parents=True, exist_ok=True)
LOG_PATH = ARTIFACTS / "smoke.log"
RESULT_PATH = ARTIFACTS / "smoke_result.json"


def main() -> int:
    env = os.environ.copy()
    env.setdefault("JARVIS_LOCAL_LLM_BASE_URL", "")
    env.setdefault("JARVIS_STT_MODE", "none")
    env.setdefault("JARVIS_TTS_MODE", "none")
    env.setdefault("JARVIS_DISABLE_DOTENV", "1")

    cmd = [
        sys.executable,
        "-m",
        "jarvis.app",
        "--text",
        "ping",
        "--dry-run",
    ]

    started = time.time()
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    duration = time.time() - started

    LOG_PATH.write_text(proc.stdout + proc.stderr, encoding="utf-8")

    result = {
        "exit_code": proc.returncode,
        "status": "ok" if proc.returncode == 0 else "fail",
        "duration_s": round(duration, 3),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "command": " ".join(cmd),
    }
    RESULT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"Smoke status: {result['status']} (exit={proc.returncode}, {duration:.2f}s)")
    print(f"Log: {LOG_PATH}")
    print(f"Result: {RESULT_PATH}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
