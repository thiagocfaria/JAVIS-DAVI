from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Optional


def _env_bool(key: str, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _debug(message: str) -> None:
    if _env_bool("JARVIS_DEBUG", False):
        print(f"[chat_log] {message}")


def _env_int(key: str, default: int) -> int:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


class ChatLog:
    """Append-only chat log for user-visible explanations."""

    def __init__(
        self,
        path: Path,
        auto_open: bool = False,
        open_command: str | None = None,
        open_cooldown_s: int = 60,
        max_bytes: int | None = None,
        max_backups: int | None = None,
    ) -> None:
        self.path = path
        self.auto_open = auto_open
        self.open_command = open_command
        self.open_cooldown_s = max(0, int(open_cooldown_s))
        self.max_bytes = (
            max_bytes
            if max_bytes is not None
            else _env_int("JARVIS_CHAT_LOG_MAX_BYTES", 5 * 1024 * 1024)
        )
        self.max_backups = (
            max_backups
            if max_backups is not None
            else _env_int("JARVIS_CHAT_LOG_BACKUPS", 3)
        )
        self._last_open_ts = 0.0

    def append(self, role: str, message: str, meta: dict[str, object] | None = None) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        payload: dict[str, object] = {
            "ts": ts,
            "role": role,
            "message": message,
        }
        if meta:
            payload["meta"] = meta
        line = json.dumps(payload, ensure_ascii=True)
        self._rotate_if_needed(len(line) + 1)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

        if self.auto_open and self._can_open():
            self.open()

    def open(self) -> None:
        cmd = self._resolve_open_command()
        if not cmd:
            _debug("open command unavailable")
            return
        self._last_open_ts = time.time()
        try:
            subprocess.Popen(cmd)
        except Exception as exc:
            _debug(f"open failed: {exc}")
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

    def _rotate_if_needed(self, incoming_len: int) -> None:
        if self.max_bytes <= 0:
            return
        try:
            if not self.path.exists():
                return
            size = self.path.stat().st_size
        except Exception:
            return
        if size + incoming_len <= self.max_bytes:
            return
        self._rotate_log()

    def _rotate_log(self) -> None:
        try:
            if self.max_backups <= 0:
                if self.path.exists():
                    self.path.unlink()
                return

            oldest = Path(str(self.path) + f".{self.max_backups}")
            if oldest.exists():
                oldest.unlink()

            for idx in range(self.max_backups - 1, 0, -1):
                src = Path(str(self.path) + f".{idx}")
                dst = Path(str(self.path) + f".{idx + 1}")
                if src.exists():
                    src.replace(dst)

            if self.path.exists():
                self.path.replace(Path(str(self.path) + ".1"))
        except Exception:
            return
