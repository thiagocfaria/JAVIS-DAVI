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

    def __init__(
        self,
        followup_seconds: int | None = None,
        max_commands: int | None = None,
    ) -> None:
        if followup_seconds is None:
            followup_seconds = _env_int("JARVIS_FOLLOWUP_SECONDS", 20)
        if max_commands is None:
            max_commands = _env_int("JARVIS_FOLLOWUP_MAX_COMMANDS", 2)
        self.followup_seconds = max(0, int(followup_seconds))
        self.max_commands = max(0, int(max_commands))
        self.followup_until = 0.0
        self.remaining_commands = 0

    def is_active(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        return now < self.followup_until and self.remaining_commands > 0

    def should_require_wake_word(
        self, require_by_default: bool, now: float | None = None
    ) -> bool:
        if not require_by_default:
            return False
        return not self.is_active(now)

    def renew(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self.followup_until = now + self.followup_seconds
        self.remaining_commands = self.max_commands

    def reset(self) -> None:
        self.followup_until = 0.0
        self.remaining_commands = 0

    def on_command_accepted(self, accepted: bool, now: float | None = None) -> None:
        if not accepted:
            return
        if self.followup_seconds <= 0 or self.max_commands <= 0:
            self.reset()
            return

        now = time.monotonic() if now is None else now

        if not self.is_active(now):
            self.followup_until = now + self.followup_seconds
            self.remaining_commands = max(0, self.max_commands - 1)
            if self.remaining_commands == 0:
                self.followup_until = 0.0
            return

        self.remaining_commands = max(0, self.remaining_commands - 1)
        if self.remaining_commands == 0:
            self.followup_until = 0.0
            return
        self.followup_until = now + self.followup_seconds
