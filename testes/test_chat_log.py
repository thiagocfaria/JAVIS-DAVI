import tempfile
import unittest
from pathlib import Path

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
            self.assertIn("jarvis", lines[0])
            self.assertIn("parou", lines[0])
            self.assertIn("reason", lines[0])


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
