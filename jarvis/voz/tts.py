"""Compat: alias para o modulo TTS na nova interface."""

from __future__ import annotations

import sys as _sys
from importlib import import_module as _import_module
from typing import Any as _Any

_mod = _import_module("jarvis.interface.saida.tts")

TextToSpeech = getattr(_mod, "TextToSpeech")
check_tts_deps = getattr(_mod, "check_tts_deps")

# Usado em testes que fazem monkeypatch via `jarvis.voz.tts.shutil/subprocess`.
shutil = getattr(_mod, "shutil")
subprocess = getattr(_mod, "subprocess")

__all__ = ["TextToSpeech", "check_tts_deps", "shutil", "subprocess"]


def __getattr__(name: str) -> _Any:
    return getattr(_mod, name)


_sys.modules[__name__] = _mod
