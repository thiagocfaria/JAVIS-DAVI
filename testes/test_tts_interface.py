from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import threading
import time
import audioop
import struct

import pytest

from jarvis.voz import tts as tts_module
from jarvis.voz.tts import TextToSpeech


def _config(tts_mode: str = "local"):
    return SimpleNamespace(tts_mode=tts_mode)


def test_speak_skips_when_tts_mode_none(monkeypatch):
    tts = TextToSpeech(_config("none"))
    called = {"piper": 0, "espeak": 0}

    monkeypatch.setattr(tts, "_try_piper", lambda text: called.__setitem__("piper", 1))
    monkeypatch.setattr(tts, "_speak_espeak", lambda text: called.__setitem__("espeak", 1))

    tts.speak("hello")
    assert called["piper"] == 0
    assert called["espeak"] == 0


def test_speak_fallbacks_to_espeak(monkeypatch):
    tts = TextToSpeech(_config("local"))
    called = {"espeak": 0}

    monkeypatch.setattr(tts, "_try_piper", lambda text: False)
    monkeypatch.setattr(tts, "_speak_espeak", lambda text: called.__setitem__("espeak", 1))

    tts.speak("hello")
    assert called["espeak"] == 1


def test_try_piper_returns_false_when_missing_binary(monkeypatch):
    tts = TextToSpeech(_config("local"))

    monkeypatch.setattr(tts_module.shutil, "which", lambda name: None)

    assert tts._try_piper("hello") is False


def test_find_piper_model_uses_env_dir(tmp_path, monkeypatch):
    model_path = tmp_path / "pt_BR-faber-medium.onnx"
    model_path.write_text("dummy", encoding="utf-8")

    monkeypatch.setenv("JARVIS_PIPER_MODELS_DIR", str(tmp_path))
    tts = TextToSpeech(_config("local"))

    assert tts._find_piper_model() == model_path


def test_get_available_engines_lists_piper_and_espeak(monkeypatch, tmp_path):
    tts = TextToSpeech(_config("local"))

    monkeypatch.setattr(tts_module.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(tts, "_find_piper_model", lambda: Path(str(tmp_path / "voice.onnx")))

    engines = tts.get_available_engines()
    assert "piper" in engines
    assert "espeak-ng" in engines


def test_try_piper_success_pipeline(monkeypatch, tmp_path):
    tts = TextToSpeech(_config("local"))
    model_path = tmp_path / "voice.onnx"
    model_path.write_text("dummy", encoding="utf-8")

    monkeypatch.setattr(tts, "_find_piper_model", lambda: model_path)
    monkeypatch.setattr(tts_module.shutil, "which", lambda name: f"/bin/{name}")

    calls = []

    class DummyStdin:
        def __init__(self):
            self.data = b""
            self.closed = False

        def write(self, data: bytes) -> None:
            self.data += data

        def close(self) -> None:
            self.closed = True

    class DummyProc:
        def __init__(self, cmd):
            self.cmd = cmd
            self.stdin = DummyStdin()
            self.stdout = object()

        def wait(self, timeout=None) -> int:
            return 0

    def fake_popen(cmd, stdin=None, stdout=None, stderr=None, **kwargs):
        proc = DummyProc(cmd)
        calls.append({"cmd": cmd, "stdin": stdin, "proc": proc})
        return proc

    monkeypatch.setattr(tts_module.subprocess, "Popen", fake_popen)

    assert tts._try_piper("ola") is True
    assert calls[0]["cmd"][0] == "piper"
    assert calls[1]["cmd"][0] == "aplay"
    assert calls[1]["stdin"] is calls[0]["proc"].stdout
    assert calls[0]["proc"].stdin.data == b"ola"


def test_speak_async_starts_thread(monkeypatch):
    import threading

    tts = TextToSpeech(_config("local"))
    called = {"started": False}

    class DummyThread:
        def __init__(self, target=None, args=(), daemon=False):
            self._target = target
            self._args = args
            self._daemon = daemon

        def start(self) -> None:
            called["started"] = True

    monkeypatch.setattr(threading, "Thread", DummyThread)
    tts.speak_async("hello")
    assert called["started"] is True


def test_try_piper_logs_failure_when_debug(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("JARVIS_DEBUG", "1")
    tts = TextToSpeech(_config("local"))
    model_path = tmp_path / "voice.onnx"
    model_path.write_text("dummy", encoding="utf-8")

    monkeypatch.setattr(tts, "_find_piper_model", lambda: model_path)
    monkeypatch.setattr(tts_module.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(tts_module.subprocess, "Popen", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail")))

    assert tts._try_piper("ola") is False
    captured = capsys.readouterr()
    assert "[tts]" in captured.out
    assert "piper falhou" in captured.out


def test_speak_espeak_logs_failure_when_debug(monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_DEBUG", "1")
    tts = TextToSpeech(_config("local"))

    monkeypatch.setattr(tts_module.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(tts_module.subprocess, "Popen", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail")))

    tts._speak_espeak("ola")
    captured = capsys.readouterr()
    assert "[tts]" in captured.out
    assert "espeak falhou" in captured.out


def test_speak_espeak_uses_volume_env(monkeypatch):
    monkeypatch.setenv("JARVIS_TTS_VOLUME", "0.5")
    tts = TextToSpeech(_config("local"))

    monkeypatch.setattr(tts_module.shutil, "which", lambda name: f"/bin/{name}")
    calls = []

    def fake_popen(cmd, *args, **kwargs):
        calls.append(cmd)
        class DummyProc:
            pass
        return DummyProc()

    monkeypatch.setattr(tts_module.subprocess, "Popen", fake_popen)

    tts._speak_espeak("ola")
    assert calls
    assert "-a" in calls[0]
    amp_index = calls[0].index("-a") + 1
    assert calls[0][amp_index] == "50"


def test_speak_logs_fallback_when_piper_unavailable(monkeypatch, capsys):
    monkeypatch.setenv("JARVIS_DEBUG", "1")
    tts = TextToSpeech(_config("local"))
    monkeypatch.setattr(tts, "_try_piper", lambda text: False)
    monkeypatch.setattr(tts, "_speak_espeak", lambda text: None)

    tts.speak("ola")
    captured = capsys.readouterr()
    assert "piper indisponivel" in captured.out


def test_try_piper_scales_audio_when_volume_env(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_TTS_VOLUME", "0.5")
    tts = TextToSpeech(_config("local"))
    model_path = tmp_path / "voice.onnx"
    model_path.write_text("dummy", encoding="utf-8")

    monkeypatch.setattr(tts, "_find_piper_model", lambda: model_path)
    monkeypatch.setattr(tts_module.shutil, "which", lambda name: f"/bin/{name}")

    raw_audio = struct.pack("<h", 1000) * 4
    expected = audioop.mul(raw_audio, 2, 0.5)
    calls = []

    class DummyStdin:
        def __init__(self):
            self.data = b""
            self.closed = False

        def write(self, data: bytes) -> None:
            self.data += data

        def close(self) -> None:
            self.closed = True

    class DummyStdout:
        def __init__(self, data: bytes):
            self._data = data

        def read(self) -> bytes:
            return self._data

    class DummyProc:
        def __init__(self, cmd, stdout_data: bytes | None = None):
            self.cmd = cmd
            self.stdin = DummyStdin()
            self.stdout = DummyStdout(stdout_data) if stdout_data is not None else None

        def wait(self, timeout=None) -> int:
            return 0

    def fake_popen(cmd, stdin=None, stdout=None, stderr=None, **kwargs):
        if cmd[0] == "piper":
            proc = DummyProc(cmd, stdout_data=raw_audio)
        else:
            proc = DummyProc(cmd)
        calls.append({"cmd": cmd, "stdin": stdin, "proc": proc})
        return proc

    monkeypatch.setattr(tts_module.subprocess, "Popen", fake_popen)

    assert tts._try_piper("ola") is True
    assert calls[0]["cmd"][0] == "piper"
    assert calls[1]["cmd"][0] == "aplay"
    assert calls[1]["proc"].stdin.data == expected


def test_speak_serializes_calls(monkeypatch):
    tts = TextToSpeech(_config("local"))
    calls: list[str] = []
    started = threading.Event()
    finish = threading.Event()

    def fake_try_piper(text: str) -> bool:
        calls.append(text)
        if text == "first":
            started.set()
            finish.wait(0.5)
        return True

    monkeypatch.setattr(tts, "_try_piper", fake_try_piper)
    monkeypatch.setattr(tts, "_speak_espeak", lambda text: None)

    t1 = threading.Thread(target=tts.speak, args=("first",))
    t2 = threading.Thread(target=tts.speak, args=("second",))

    t1.start()
    assert started.wait(0.5)
    t2.start()

    time.sleep(0.05)
    assert calls == ["first"]

    finish.set()
    t1.join(1)
    t2.join(1)
    assert calls == ["first", "second"]
