from __future__ import annotations

import pytest

from jarvis.comunicacao import protocolo


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({}, "missing_version"),
        ({"version": 0}, "invalid_version"),
        ({"version": "1"}, "invalid_version"),
        ({"version": 1}, "missing_type"),
        ({"version": 1, "type": 123}, "invalid_type"),
        ({"version": 1, "type": "unknown"}, "unknown_type"),
        ({"version": 1, "type": "hello"}, "missing_id"),
        ({"version": 1, "type": "hello", "id": ""}, "invalid_id"),
        ({"version": 1, "type": "hello", "id": "1"}, "missing_ts"),
        ({"version": 1, "type": "hello", "id": "1", "ts": -1}, "invalid_ts"),
        (
            {"version": 1, "type": "hello", "id": "1", "ts": 123},
            "missing_session_id",
        ),
        (
            {"version": 1, "type": "hello", "id": "1", "ts": 123, "session_id": ""},
            "invalid_session_id",
        ),
        (
            {"version": 1, "type": "hello", "id": "1", "ts": 123, "session_id": "s"},
            "missing_payload",
        ),
        (
            {
                "version": 1,
                "type": "hello",
                "id": "1",
                "ts": 123,
                "session_id": "s",
                "payload": [],
            },
            "invalid_payload",
        ),
    ],
)
def test_validar_mensagem_errors(payload, expected):
    assert protocolo.validar_mensagem(payload) == expected


def test_validar_mensagem_ok():
    payload = {
        "version": 1,
        "type": "hello",
        "id": "1",
        "ts": 123,
        "session_id": "s",
        "payload": {},
    }
    assert protocolo.validar_mensagem(payload) is None
