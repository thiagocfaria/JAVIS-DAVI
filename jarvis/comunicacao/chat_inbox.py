from __future__ import annotations

from pathlib import Path
from typing import List


class ChatInbox:
    """Tail a text file and return new lines as commands."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._offset = 0

    def drain(self) -> list[str]:
        if not self.path.exists():
            return []
        try:
            size = self.path.stat().st_size
        except Exception:
            return []
        if size < self._offset:
            self._offset = 0
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                handle.seek(self._offset)
                lines = handle.readlines()
                self._offset = handle.tell()
        except Exception:
            return []
        return [line.strip() for line in lines if line.strip()]
