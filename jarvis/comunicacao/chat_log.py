from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional


class ChatLog:
    """Append-only chat log for user-visible explanations."""

    def __init__(
        self,
        path: Path,
        auto_open: bool = False,
        open_command: str | None = None,
        open_cooldown_s: int = 60,
    ) -> None:
        self.path = path
        self.auto_open = auto_open
        self.open_command = open_command
        self.open_cooldown_s = max(0, int(open_cooldown_s))
        self._last_open_ts = 0.0

    def append(self, role: str, message: str, meta: dict[str, object] | None = None) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        line = f"[{ts}] {role}: {message}"
        if meta:
            line += " | meta=" + json.dumps(meta, ensure_ascii=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

        if self.auto_open and self._can_open():
            self.open()

    def open(self) -> None:
        cmd = self._resolve_open_command()
        if not cmd:
            return
        self._last_open_ts = time.time()
        try:
            subprocess.Popen(cmd)
        except Exception:
            return

    def _can_open(self) -> bool:
        if self.open_cooldown_s <= 0:
            return True
        return (time.time() - self._last_open_ts) >= self.open_cooldown_s

    def _resolve_open_command(self) -> list | None:
        if self.open_command:
            try:
                return shlex.split(self.open_command) + [str(self.path)]
            except Exception:
                return None

        if sys.platform.startswith("linux"):
            return ["xdg-open", str(self.path)]
        if sys.platform == "darwin":
            return ["open", str(self.path)]
        if os.name == "nt":
            return ["cmd", "/c", "start", str(self.path)]
        return None
