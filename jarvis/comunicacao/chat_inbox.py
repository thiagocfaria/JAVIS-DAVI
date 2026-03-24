"""Compat: alias para o modulo chat_inbox na nova interface."""

from __future__ import annotations

import sys as _sys
from importlib import import_module as _import_module
from typing import Any as _Any

_mod = _import_module("jarvis.interface.infra.chat_inbox")

ChatInbox = getattr(_mod, "ChatInbox")
append_line = getattr(_mod, "append_line")

__all__ = ["ChatInbox", "append_line"]


def __getattr__(name: str) -> _Any:
    return getattr(_mod, name)


_sys.modules[__name__] = _mod
