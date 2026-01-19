"""Compat: alias para o modulo shortcut na nova interface."""

from __future__ import annotations

import sys as _sys
from importlib import import_module as _import_module
from typing import Any as _Any

_mod = _import_module("jarvis.interface.entrada.shortcut")

ChatShortcut = getattr(_mod, "ChatShortcut")
check_shortcut_deps = getattr(_mod, "check_shortcut_deps")

# Usado em testes que fazem monkeypatch de `jarvis.entrada.shortcut.threading/subprocess`.
threading = getattr(_mod, "threading")
subprocess = getattr(_mod, "subprocess")

__all__ = ["ChatShortcut", "check_shortcut_deps", "threading", "subprocess"]


def __getattr__(name: str) -> _Any:
    return getattr(_mod, name)


_sys.modules[__name__] = _mod
