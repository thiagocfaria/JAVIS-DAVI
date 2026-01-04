from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass
class LocalEnvController:
    workdir: Path

    def run_bash_script(self, code: str, timeout: int = 30) -> Dict:
        result = subprocess.run(
            code,
            shell=True,
            cwd=str(self.workdir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "status": "ok" if result.returncode == 0 else "error",
            "returncode": result.returncode,
            "output": (result.stdout or "") + (result.stderr or ""),
            "error": "",
        }

    def run_python_script(self, code: str, timeout: int = 30) -> Dict:
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(self.workdir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "status": "ok" if result.returncode == 0 else "error",
            "returncode": result.returncode,
            "output": result.stdout or "",
            "error": result.stderr or "",
        }


def build_env_controller(workdir: str | None) -> LocalEnvController:
    base = Path(workdir or os.getcwd())
    return LocalEnvController(workdir=base)
