from __future__ import annotations

import os
from pathlib import Path

try:
    import fcntl  # type: ignore
except Exception:
    fcntl = None


def _env_int(key: str, default: int) -> int:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


class ChatInbox:
    """Tail a text file and return new lines as commands."""

    def __init__(self, path: Path, cursor_path: Path | None = None) -> None:
        self.path = path
        self._cursor_path = cursor_path or Path(str(path) + ".cursor")
        self._offset = self._load_cursor()
        self._max_lines = max(0, _env_int("JARVIS_CHAT_INBOX_MAX_LINES", 0))

    @staticmethod
    def _lock(handle, exclusive: bool) -> None:
        if fcntl is None:
            return
        try:
            mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            fcntl.flock(handle.fileno(), mode)
        except Exception:
            return

    def _load_cursor(self) -> int:
        try:
            if not self._cursor_path.exists():
                return 0
            raw = self._cursor_path.read_text(encoding="utf-8").strip()
            if not raw:
                return 0
            value = int(raw)
            return value if value >= 0 else 0
        except Exception:
            return 0

    def _store_cursor(self) -> None:
        try:
            self._cursor_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = Path(str(self._cursor_path) + ".tmp")
            tmp_path.write_text(str(self._offset), encoding="utf-8")
            tmp_path.replace(self._cursor_path)
        except Exception:
            return

    def drain(self) -> list[str]:
        if not self.path.exists():
            return []
        try:
            size = self.path.stat().st_size
        except Exception:
            return []
        if size < self._offset:
            self._offset = 0
            self._store_cursor()
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                self._lock(handle, exclusive=False)
                handle.seek(self._offset)
                lines = handle.readlines()
                self._offset = handle.tell()
            self._store_cursor()
        except Exception:
            return []
        if self._max_lines and len(lines) > self._max_lines:
            lines = lines[-self._max_lines :]
        return [line.strip() for line in lines if line.strip()]


def append_line(path: Path, line: str) -> bool:
    """Append one line to inbox with best-effort lock."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = line.strip()
        if not payload:
            return False
        with path.open("a", encoding="utf-8") as handle:
            ChatInbox._lock(handle, exclusive=True)
            handle.write(payload + "\n")
            handle.flush()
        return True
    except Exception:
        return False
