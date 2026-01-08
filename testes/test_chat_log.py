import tempfile
import unittest
from pathlib import Path

import json
import jarvis.comunicacao.chat_log as chat_log_module

from jarvis.comunicacao.chat_log import ChatLog


class TestChatLog(unittest.TestCase):
    def test_append_writes_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "chat.jsonl"
            chat = ChatLog(path, auto_open=False)
            chat.append("jarvis", "parou", {"reason": "test"})
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            payload = json.loads(lines[0])
            self.assertEqual(payload.get("role"), "jarvis")
            self.assertEqual(payload.get("message"), "parou")
            self.assertEqual(payload.get("meta", {}).get("reason"), "test")


if __name__ == "__main__":
    unittest.main()


def test_auto_open_disabled_does_not_call_popen(monkeypatch, tmp_path):
    calls = []

    def fake_popen(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(chat_log_module.subprocess, "Popen", fake_popen)

    chat = ChatLog(tmp_path / "chat.log", auto_open=False, open_cooldown_s=0)
    chat.append("jarvis", "ola")

    assert calls == []


def test_auto_open_respects_cooldown(monkeypatch, tmp_path):
    calls = []

    def fake_popen(*args, **kwargs):
        calls.append((args, kwargs))

    times = iter([100.0, 100.0, 120.0, 161.0, 161.0])

    def fake_time():
        return next(times)

    monkeypatch.setattr(chat_log_module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(chat_log_module.time, "time", fake_time)

    chat = ChatLog(tmp_path / "chat.log", auto_open=True, open_cooldown_s=60)
    chat.append("jarvis", "primeiro")
    chat.append("jarvis", "segundo")
    chat.append("jarvis", "terceiro")

    assert len(calls) == 2


def test_log_rotation_by_size(tmp_path):
    path = tmp_path / "chat.log"
    chat = ChatLog(path, auto_open=False, max_bytes=1, max_backups=1)

    chat.append("jarvis", "primeiro")
    assert path.exists()
    assert not (tmp_path / "chat.log.1").exists()

    chat.append("jarvis", "segundo")
    rotated = tmp_path / "chat.log.1"
    assert rotated.exists()
    assert "primeiro" in rotated.read_text(encoding="utf-8")
    assert "segundo" in path.read_text(encoding="utf-8")

    chat.append("jarvis", "terceiro")
    assert rotated.exists()
    assert "segundo" in rotated.read_text(encoding="utf-8")
    assert "terceiro" in path.read_text(encoding="utf-8")


def test_open_logs_when_popen_fails(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("JARVIS_DEBUG", "1")

    def fake_popen(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(chat_log_module.subprocess, "Popen", fake_popen)

    chat = ChatLog(tmp_path / "chat.log", auto_open=False)
    chat.open()

    output = capsys.readouterr().out
    assert "[chat_log]" in output
    assert "open failed" in output
