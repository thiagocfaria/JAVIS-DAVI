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
PROTO_VERSION = 1


def agora_ms() -> int:
    return int(time.time() * 1000)


def novo_id() -> str:
    return str(uuid.uuid4())


@dataclass
class Mensagem:
    version: int
    tipo: str
    id: str
    ts: int
    session_id: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "type": self.tipo,
            "id": self.id,
            "ts": self.ts,
            "session_id": self.session_id,
            "payload": self.payload,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Mensagem:
        return Mensagem(
            version=int(data.get("version", PROTO_VERSION) or PROTO_VERSION),
            tipo=str(data.get("type", "")),
            id=str(data.get("id", "")),
            ts=int(data.get("ts", 0) or 0),
            session_id=str(data.get("session_id", "")),
            payload=dict(data.get("payload", {}) or {}),
        )


def criar_mensagem(tipo: str, session_id: str, payload: dict[str, Any] | None = None) -> Mensagem:
    return Mensagem(
        version=PROTO_VERSION,
        tipo=tipo,
        id=novo_id(),
        ts=agora_ms(),
        session_id=session_id,
        payload=payload or {},
    )


def validar_mensagem(data: dict[str, Any]) -> str | None:
    if "version" not in data:
        return "missing_version"
    version = data.get("version")
    if not isinstance(version, int) or version <= 0:
        return "invalid_version"
    if "type" not in data:
        return "missing_type"
    msg_type = data.get("type")
    if not isinstance(msg_type, str):
        return "invalid_type"
    if msg_type not in TIPOS_MENSAGEM:
        return "unknown_type"
    if "id" not in data:
        return "missing_id"
    msg_id = data.get("id")
    if not isinstance(msg_id, str) or not msg_id.strip():
        return "invalid_id"
    if "ts" not in data:
        return "missing_ts"
    ts = data.get("ts")
    if not isinstance(ts, int) or ts <= 0:
        return "invalid_ts"
    if "session_id" not in data:
        return "missing_session_id"
    session_id = data.get("session_id")
    if not isinstance(session_id, str) or not session_id.strip():
        return "invalid_session_id"
    if "payload" not in data:
        return "missing_payload"
    payload = data.get("payload")
    if not isinstance(payload, dict):
        return "invalid_payload"
    return None
