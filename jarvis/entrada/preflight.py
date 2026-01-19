"""Compat: alias para o modulo preflight na nova interface."""

from __future__ import annotations

import sys as _sys
from importlib import import_module as _import_module
from typing import Any as _Any

_mod = _import_module("jarvis.interface.entrada.preflight")

CheckResult = getattr(_mod, "CheckResult")
PreflightReport = getattr(_mod, "PreflightReport")
run_preflight = getattr(_mod, "run_preflight")
format_report = getattr(_mod, "format_report")

# Funcoes internas usadas por testes
_check_stt = getattr(_mod, "_check_stt")
_check_tts = getattr(_mod, "_check_tts")
_check_chat_ui = getattr(_mod, "_check_chat_ui")
_check_chat_shortcut = getattr(_mod, "_check_chat_shortcut")
_check_wake_word_audio = getattr(_mod, "_check_wake_word_audio")

__all__ = [
    "CheckResult",
    "PreflightReport",
    "run_preflight",
    "format_report",
    "_check_stt",
    "_check_tts",
    "_check_chat_ui",
    "_check_chat_shortcut",
    "_check_wake_word_audio",
]


def __getattr__(name: str) -> _Any:
    return getattr(_mod, name)


_sys.modules[__name__] = _mod
