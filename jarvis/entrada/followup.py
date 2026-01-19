"""Compat: alias para o modulo followup na nova interface."""

from __future__ import annotations

import sys as _sys
from importlib import import_module as _import_module
from typing import Any as _Any

_mod = _import_module("jarvis.interface.entrada.followup")

FollowUpSession = getattr(_mod, "FollowUpSession")

__all__ = ["FollowUpSession"]


def __getattr__(name: str) -> _Any:
    return getattr(_mod, name)


_sys.modules[__name__] = _mod
