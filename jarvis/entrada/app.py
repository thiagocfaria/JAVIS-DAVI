"""Compat: alias para o modulo app de entrada na nova interface.

Este wrapper existe para manter imports antigos (`jarvis.entrada.*`) funcionando
sem quebrar o type-checker (Pylance/Pyright).
"""

from __future__ import annotations

import sys as _sys
from importlib import import_module as _import_module
from typing import Any as _Any

_mod = _import_module("jarvis.interface.entrada.app")

main = getattr(_mod, "main")

__all__ = ["main"]


def __getattr__(name: str) -> _Any:
    return getattr(_mod, name)


_sys.modules[__name__] = _mod
