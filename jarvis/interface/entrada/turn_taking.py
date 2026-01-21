"""
Heuristicas leves de turn-taking para decidir se a fala terminou.

Este modulo nao depende de ML. Ele estima se a frase parece completa e sugere
um pequeno tempo de espera extra quando a frase aparenta estar incompleta.
"""

from __future__ import annotations

import os


def _env_int(key: str, default: int) -> int:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


_INCOMPLETE_TOKENS = {
    "e",
    "mas",
    "ou",
    "porque",
    "que",
    "pra",
    "para",
    "de",
    "do",
    "da",
    "das",
    "dos",
    "com",
    "se",
    "quando",
    "entao",
    "então",
    "como",
    "por",
    "em",
}


def analyze_turn(text: str, endpoint_ms: float | None = None) -> dict[str, bool | int | str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return {
            "is_complete": True,
            "hold_ms": 0,
            "reason": "empty",
            "last_token": "",
        }

    last_char = cleaned[-1]
    last_token = cleaned.split()[-1].lower()
    min_words = max(1, _env_int("JARVIS_TURN_TAKING_MIN_WORDS", 3))
    base_hold = max(0, _env_int("JARVIS_TURN_TAKING_HOLD_MS", 600))
    short_silence_ms = max(0, _env_int("JARVIS_TURN_TAKING_SHORT_SILENCE_MS", 300))

    is_complete = False
    reason = "unknown"

    if last_char in ".?!":
        is_complete = True
        reason = "terminal_punctuation"
    elif cleaned.endswith("...") or last_char in ",;:":
        is_complete = False
        reason = "open_punctuation"
    elif last_token in _INCOMPLETE_TOKENS:
        is_complete = False
        reason = "incomplete_token"
    elif len(cleaned.split()) < min_words:
        is_complete = False
        reason = "short_phrase"
    else:
        is_complete = True
        reason = "default_complete"

    hold_ms = 0
    if not is_complete:
        hold_ms = base_hold
        if endpoint_ms is not None and endpoint_ms < short_silence_ms:
            hold_ms += max(0, int(short_silence_ms - endpoint_ms))

    return {
        "is_complete": bool(is_complete),
        "hold_ms": int(hold_ms),
        "reason": reason,
        "last_token": last_token,
    }
