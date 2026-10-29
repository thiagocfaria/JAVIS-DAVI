"""
Utilitários e contratos comuns para áudio de entrada.

Mantém constantes de formato e normalização para evitar tipos inesperados.
"""
from __future__ import annotations

from array import array
from typing import Any

# Formato padrão de áudio: PCM int16 mono a 16 kHz.
SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2


def coerce_pcm_bytes(payload: Any) -> bytes:
    """
    Normaliza contêineres PCM para bytes (int16 little-endian mono).
    Aceita bytes/bytearray/memoryview, objetos com tobytes(), listas de ints ou listas de frames em bytes.
    """
    if payload is None:
        raise TypeError("audio payload is None")
    if isinstance(payload, (bytes, bytearray)):
        return bytes(payload)
    if isinstance(payload, memoryview):
        return payload.tobytes()
    if hasattr(payload, "tobytes"):
        try:
            return payload.tobytes()
        except Exception:
            pass
    if isinstance(payload, (list, tuple)):
        if len(payload) == 0:
            return b""
        if all(isinstance(item, (bytes, bytearray, memoryview)) for item in payload):
            return b"".join(bytes(item) for item in payload)
        if all(isinstance(item, int) for item in payload):
            ints = list(payload)
            if any(item < -32768 or item > 32767 for item in ints):
                raise TypeError("int values out of int16 range")
            if any(item < 0 or item > 255 for item in ints):
                return array("h", ints).tobytes()
            return bytes(ints)
    raise TypeError(f"unsupported audio payload type: {type(payload)}")
