from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

TIPOS_MENSAGEM = {
    "hello",
    "heartbeat",
    "plan_request",
    "plan_response",
    "action_result",
    "telemetry_event",
    "error",
}


def agora_ms() -> int:
    return int(time.time() * 1000)


def novo_id() -> str:
    return str(uuid.uuid4())


@dataclass
class Mensagem:
    tipo: str
    id: str
    ts: int
    session_id: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.tipo,
            "id": self.id,
            "ts": self.ts,
            "session_id": self.session_id,
            "payload": self.payload,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Mensagem:
        return Mensagem(
            tipo=str(data.get("type", "")),
            id=str(data.get("id", "")),
            ts=int(data.get("ts", 0) or 0),
            session_id=str(data.get("session_id", "")),
            payload=dict(data.get("payload", {}) or {}),
        )


def criar_mensagem(tipo: str, session_id: str, payload: dict[str, Any] | None = None) -> Mensagem:
    return Mensagem(
        tipo=tipo,
        id=novo_id(),
        ts=agora_ms(),
        session_id=session_id,
        payload=payload or {},
    )


def validar_mensagem(data: dict[str, Any]) -> str | None:
    if "type" not in data:
        return "missing_type"
    if data.get("type") not in TIPOS_MENSAGEM:
        return "unknown_type"
    if "id" not in data:
        return "missing_id"
    if "ts" not in data:
        return "missing_ts"
    if "session_id" not in data:
        return "missing_session_id"
    if "payload" not in data:
        return "missing_payload"
    return None
