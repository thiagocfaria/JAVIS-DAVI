from __future__ import annotations

import importlib
import json
import sys
import types

import pytest


def _build_dummy_tk(entry_value: str = "hello"):
    module = types.SimpleNamespace()
    module._entry_value = entry_value
    module._last_button = None

    class DummyRoot:
        def __init__(self):
            self._exists = True

        def title(self, *args, **kwargs):
            return None

        def geometry(self, *args, **kwargs):
            return None

        def after(self, *args, **kwargs):
            return None

        def mainloop(self):
            if module._last_button is not None:
                module._last_button.command()

    class DummyWidget:
        def pack(self, *args, **kwargs):
            return None

    class DummyText(DummyWidget):
        def __init__(self, *args, **kwargs):
            self.value = ""

        def configure(self, *args, **kwargs):
            return None

        def delete(self, *args, **kwargs):
            self.value = ""

        def insert(self, *args, **kwargs):
            if len(args) >= 2:
                self.value += str(args[1])

        def see(self, *args, **kwargs):
            return None

    class DummyFrame(DummyWidget):
        def __init__(self, *args, **kwargs):
            return None

    class DummyEntry(DummyWidget):
        def __init__(self, *args, **kwargs):
            return None

        def get(self):
            return module._entry_value

        def delete(self, *args, **kwargs):
            module._entry_value = ""

        def bind(self, *args, **kwargs):
            return None

    class DummyLabel(DummyWidget):
        def __init__(self, *args, **kwargs):
            self.text = ""

        def config(self, *args, **kwargs):
            self.text = kwargs.get("text", self.text)

    class DummyButton(DummyWidget):
        def __init__(self, *args, **kwargs):
            self.command = kwargs.get("command")
            module._last_button = self

    module.Tk = DummyRoot
    module.Text = DummyText
    module.Frame = DummyFrame
    module.Entry = DummyEntry
    module.Label = DummyLabel
    module.Button = DummyButton

    return module


def test_tail_lines(tmp_path, monkeypatch):
    tk_dummy = _build_dummy_tk()
    monkeypatch.setitem(sys.modules, "tkinter", tk_dummy)
    chat_ui = importlib.import_module("jarvis.entrada.chat_ui")
    importlib.reload(chat_ui)

    path = tmp_path / "chat.log"
    path.write_text("a\nB\nc\n", encoding="utf-8")

    assert chat_ui._tail_lines(path, 2) == "B\nc"


def test_tail_lines_limit_zero(tmp_path, monkeypatch):
    tk_dummy = _build_dummy_tk()
    monkeypatch.setitem(sys.modules, "tkinter", tk_dummy)
    chat_ui = importlib.import_module("jarvis.entrada.chat_ui")
    importlib.reload(chat_ui)

    path = tmp_path / "chat.log"
    path.write_text("a\nb\nc\n", encoding="utf-8")

    assert chat_ui._tail_lines(path, 0) == ""


def test_format_log_with_timestamps(monkeypatch):
    tk_dummy = _build_dummy_tk()
    monkeypatch.setitem(sys.modules, "tkinter", tk_dummy)
    chat_ui = importlib.import_module("jarvis.entrada.chat_ui")
    importlib.reload(chat_ui)

    json_line = json.dumps(
        {"ts": "2024-01-01 10:00:00", "role": "jarvis", "message": "oi"},
        ensure_ascii=True,
    )
    content = f"{json_line}\nline2"
    formatted = chat_ui._format_log_with_timestamps(content)
    assert "jarvis: oi" in formatted
    assert "line2" in formatted
    assert formatted.count("[") >= 1


def test_chat_ui_main_writes_inbox(tmp_path, monkeypatch):
    tk_dummy = _build_dummy_tk(entry_value="hello")
    monkeypatch.setitem(sys.modules, "tkinter", tk_dummy)
    chat_ui = importlib.import_module("jarvis.entrada.chat_ui")
    importlib.reload(chat_ui)

    log_path = tmp_path / "chat.log"
    inbox_path = tmp_path / "chat_inbox.txt"
    log_path.write_text("log\n", encoding="utf-8")

    monkeypatch.setenv("JARVIS_CHAT_LOG_PATH", str(log_path))
    monkeypatch.setenv("JARVIS_CHAT_INBOX_PATH", str(inbox_path))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "chat_ui",
            "--log-path",
            str(log_path),
            "--inbox-path",
            str(inbox_path),
            "--tail",
            "1",
            "--poll-ms",
            "1000",
        ],
    )

    assert chat_ui.main() == 0
    assert inbox_path.read_text(encoding="utf-8").strip() == "hello"
