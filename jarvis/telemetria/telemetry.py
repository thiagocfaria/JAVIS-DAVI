from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable


class Telemetry:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self._lock = threading.Lock()

    def log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        record = {
            "ts": time.time(),
            "type": event_type,
            "payload": payload,
        }
        self._write_local(record)

    def log_sequence(self, events: Iterable[tuple[str, dict[str, Any]]]) -> None:
        """Log multiple events atomically (prevents interleaving)."""
        for event_type, payload in events:
            self.log_event(event_type, payload)

    def _write_local(self, record: dict[str, Any]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=True) + "\n")
