#!/usr/bin/env python3
"""
Testes completos de detecção de emoção/tonalidade.

Valida o módulo de detecção de emoção com diferentes cenários de áudio.
"""
from __future__ import annotations

import os
import pytest

from jarvis.interface.entrada.emocao import detect_emotion, detect_emotion_async


@pytest.fixture(autouse=True)
def enable_emotion():
    """Garante que detecção de emoção está habilitada."""
    old = os.environ.get("JARVIS_EMOTION_ENABLED")
    os.environ["JARVIS_EMOTION_ENABLED"] = "1"
    yield
    if old is None:
        os.environ.pop("JARVIS_EMOTION_ENABLED", None)
    else:
        os.environ["JARVIS_EMOTION_ENABLED"] = old


class TestEmocaoHeuristica:
    """Testes do backend heurístico de emoção."""

    def test_audio_vazio_retorna_none(self) -> None:
        """Áudio vazio deve retornar None."""
        result = detect_emotion(b"", 16000)
        assert result is None

    def test_audio_muito_curto_retorna_none(self) -> None:
        """Áudio menor que min_ms deve retornar None."""
        np = pytest.importorskip("numpy")
        # 100ms de áudio (menor que 800ms default)
        samples = np.zeros(1600, dtype=np.int16)
        result = detect_emotion(samples.tobytes(), 16000)
        assert result is None

    def test_audio_silencioso_retorna_neutro(self) -> None:
        """Áudio silencioso deve retornar neutro."""
        np = pytest.importorskip("numpy")
        # 1 segundo de silêncio (valores muito baixos)
        samples = (np.random.randn(16000) * 100).astype(np.int16)
        result = detect_emotion(samples.tobytes(), 16000)
        assert result is not None
        assert result["label"] == "neutro"
        assert result["backend"] == "heuristic"

    def test_audio_alto_e_agitado(self) -> None:
        """Áudio alto com muita variação deve detectar agitação."""
        np = pytest.importorskip("numpy")
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        # Sinal com alta amplitude e alta frequência (zcr alto)
        noise = np.random.randn(sr) * 0.3
        signal = (0.8 * np.sin(2 * np.pi * 300 * t) + noise)
        samples = (signal * 32767).astype(np.int16)
        result = detect_emotion(samples.tobytes(), sr)
        assert result is not None
        assert result["label"] in {"agitado", "feliz", "calmo"}
        assert "metrics" in result
        assert result["metrics"]["rms"] > 0.05

    def test_audio_baixo_e_grave(self) -> None:
        """Áudio baixo com frequência grave pode indicar tristeza."""
        np = pytest.importorskip("numpy")
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        # Sinal com baixa amplitude e frequência grave
        samples = (0.03 * np.sin(2 * np.pi * 100 * t) * 32767).astype(np.int16)
        result = detect_emotion(samples.tobytes(), sr)
        assert result is not None
        assert result["label"] in {"neutro", "triste", "calmo"}

    def test_audio_pitch_alto_amplitude_media(self) -> None:
        """Áudio com pitch alto e amplitude média pode indicar felicidade."""
        np = pytest.importorskip("numpy")
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        # Pitch alto (~200Hz) e amplitude média
        samples = (0.15 * np.sin(2 * np.pi * 200 * t) * 32767).astype(np.int16)
        result = detect_emotion(samples.tobytes(), sr)
        assert result is not None
        assert result["label"] in {"feliz", "calmo", "neutro"}

    def test_resultado_contem_metricas(self) -> None:
        """Resultado deve conter métricas de análise."""
        np = pytest.importorskip("numpy")
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        samples = (0.5 * np.sin(2 * np.pi * 220 * t) * 32767).astype(np.int16)
        result = detect_emotion(samples.tobytes(), sr)
        assert result is not None
        assert "metrics" in result
        metrics = result["metrics"]
        assert "rms" in metrics
        assert "zcr" in metrics
        assert "pitch_hz" in metrics
        assert isinstance(metrics["rms"], float)
        assert isinstance(metrics["zcr"], float)

    def test_confidence_entre_0_e_1(self) -> None:
        """Confidence deve estar entre 0 e 1."""
        np = pytest.importorskip("numpy")
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        samples = (0.5 * np.sin(2 * np.pi * 220 * t) * 32767).astype(np.int16)
        result = detect_emotion(samples.tobytes(), sr)
        assert result is not None
        assert 0.0 <= result["confidence"] <= 1.0


class TestEmocaoAsync:
    """Testes da detecção assíncrona de emoção."""

    def test_callback_eh_chamado(self) -> None:
        """Callback deve ser chamado com resultado."""
        np = pytest.importorskip("numpy")
        import threading

        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        samples = (0.5 * np.sin(2 * np.pi * 220 * t) * 32767).astype(np.int16)

        results = []
        event = threading.Event()

        def callback(result):
            results.append(result)
            event.set()

        detect_emotion_async(samples.tobytes(), sr, callback)
        event.wait(timeout=2.0)

        assert len(results) == 1
        assert results[0]["label"] in {"neutro", "calmo", "agitado", "triste", "feliz"}

    def test_callback_nao_chamado_para_audio_curto(self) -> None:
        """Callback não deve ser chamado para áudio muito curto."""
        np = pytest.importorskip("numpy")
        import threading
        import time

        samples = np.zeros(1600, dtype=np.int16)  # 100ms

        results = []

        def callback(result):
            results.append(result)

        detect_emotion_async(samples.tobytes(), 16000, callback)
        time.sleep(0.5)

        assert len(results) == 0


class TestEmocaoConfig:
    """Testes de configuração de emoção via env."""

    def test_desabilitado_via_env(self, monkeypatch) -> None:
        """Detecção pode ser desabilitada via env."""
        np = pytest.importorskip("numpy")
        monkeypatch.setenv("JARVIS_EMOTION_ENABLED", "0")

        sr = 16000
        samples = np.zeros(sr, dtype=np.int16)
        result = detect_emotion(samples.tobytes(), sr)
        assert result is None

    def test_min_ms_customizado(self, monkeypatch) -> None:
        """min_ms pode ser customizado via env."""
        np = pytest.importorskip("numpy")
        monkeypatch.setenv("JARVIS_EMOTION_MIN_MS", "100")

        # 200ms de áudio (maior que 100ms custom)
        samples = np.zeros(3200, dtype=np.int16)
        result = detect_emotion(samples.tobytes(), 16000)
        # Deve processar (não None por ser curto)
        assert result is not None
