"""
Follow-up session manager for voice commands.

Tracks a short active window after a valid command to avoid repeating wake word.
"""

from __future__ import annotations

import os
import time


def _env_int(key: str, default: int) -> int:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


class FollowUpSession:
    """Simple follow-up session window for voice commands."""

    def __init__(self, followup_seconds: int | None = None) -> None:
        if followup_seconds is None:
            followup_seconds = _env_int("JARVIS_FOLLOWUP_SECONDS", 20)
        self.followup_seconds = max(0, int(followup_seconds))
        self.followup_until = 0.0

    def is_active(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        return now < self.followup_until

    def should_require_wake_word(
        self, require_by_default: bool, now: float | None = None
    ) -> bool:
        if not require_by_default:
            return False
        return not self.is_active(now)

    def renew(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self.followup_until = now + self.followup_seconds

    def reset(self) -> None:
        self.followup_until = 0.0

    def on_command_accepted(self, accepted: bool, now: float | None = None) -> None:
        if accepted:
            self.renew(now)
