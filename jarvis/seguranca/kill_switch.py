from __future__ import annotations

from pathlib import Path


def stop_requested(stop_file: Path) -> bool:
    """Return True if the STOP file exists."""
    try:
        return stop_file.exists()
    except Exception:
        return False
