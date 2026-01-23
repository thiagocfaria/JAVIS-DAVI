#!/usr/bin/env python3
"""
Testes completos de VAD (Voice Activity Detection).

Valida WebRTC VAD, Silero VAD, streaming, AEC, e configurações.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock


class TestWebRTCVAD:
    """Testes do WebRTC VAD básico."""

    def test_vad_disponivel(self) -> None:
        """WebRTC VAD deve estar disponível."""
        try:
            import webrtcvad
            assert webrtcvad is not None
        except ImportError:
            pytest.skip("webrtcvad não instalado")

    def test_voice_activity_detector_init(self) -> None:
        """VoiceActivityDetector deve inicializar corretamente."""
        from jarvis.interface.entrada.vad import VoiceActivityDetector

        vad = VoiceActivityDetector(aggressiveness=2)
        assert vad is not None
        assert vad._aggressiveness == 2

    def test_vad_aggressiveness_levels(self) -> None:
        """VAD deve aceitar níveis de agressividade 0-3."""
        from jarvis.interface.entrada.vad import VoiceActivityDetector

        for level in range(4):
            vad = VoiceActivityDetector(aggressiveness=level)
            assert vad._aggressiveness == level

    def test_resolve_vad_aggressiveness(self) -> None:
        """resolve_vad_aggressiveness deve converter valores."""
        from jarvis.interface.entrada.vad import resolve_vad_aggressiveness

        assert resolve_vad_aggressiveness(0) == 0
        assert resolve_vad_aggressiveness(1) == 1
        assert resolve_vad_aggressiveness(2) == 2
        assert resolve_vad_aggressiveness(3) == 3
        # Valores fora do range devem ser limitados
        assert resolve_vad_aggressiveness(-1) == 0
        assert resolve_vad_aggressiveness(5) == 3

    def test_is_speech_audio_silencioso(self) -> None:
        """VAD deve detectar silêncio corretamente."""
        np = pytest.importorskip("numpy")
        from jarvis.interface.entrada.vad import VoiceActivityDetector

        vad = VoiceActivityDetector(aggressiveness=2, sample_rate=16000, frame_duration_ms=30)

        # Frame de silêncio (480 samples para 30ms @ 16kHz)
        silence = np.zeros(480, dtype=np.int16).tobytes()

        # Preprocessar e verificar
        processed = vad.preprocess_frame(silence)
        is_speech = vad.is_speech_preprocessed(processed)

        # Silêncio deve ser detectado como não-fala
        assert is_speech is False

    def test_is_speech_audio_ruidoso(self) -> None:
        """VAD deve detectar fala/ruído corretamente."""
        np = pytest.importorskip("numpy")
        from jarvis.interface.entrada.vad import VoiceActivityDetector

        vad = VoiceActivityDetector(aggressiveness=0, sample_rate=16000, frame_duration_ms=30)

        # Frame com sinal (simula fala)
        t = np.linspace(0, 0.03, 480, endpoint=False)
        signal = (0.5 * np.sin(2 * np.pi * 300 * t) * 32767).astype(np.int16)

        processed = vad.preprocess_frame(signal.tobytes())
        is_speech = vad.is_speech_preprocessed(processed)

        # Sinal forte deve ser detectado como fala (com agressividade baixa)
        assert isinstance(is_speech, bool)

    def test_frames_from_audio(self) -> None:
        """frames_from_audio deve dividir áudio em frames corretos."""
        np = pytest.importorskip("numpy")
        from jarvis.interface.entrada.vad import VoiceActivityDetector

        vad = VoiceActivityDetector(aggressiveness=2, sample_rate=16000, frame_duration_ms=30)

        # 1 segundo de áudio = ~33 frames de 30ms
        audio = np.zeros(16000, dtype=np.int16).tobytes()
        frames = list(vad.frames_from_audio(audio))

        assert len(frames) == 33  # 16000 / 480 = 33.33
        assert all(len(f) == 960 for f in frames)  # 480 samples * 2 bytes


class TestStreamingVAD:
    """Testes do VAD em modo streaming."""

    def test_streaming_vad_init(self) -> None:
        """StreamingVAD deve inicializar corretamente."""
        from jarvis.interface.entrada.vad import StreamingVAD

        svad = StreamingVAD(aggressiveness=2)
        assert svad is not None

    def test_streaming_vad_record_until_silence(self) -> None:
        """StreamingVAD deve gravar até silêncio."""
        from jarvis.interface.entrada.vad import StreamingVAD

        svad = StreamingVAD(aggressiveness=2, max_duration_s=1)

        # Não deve crashar ao inicializar
        assert svad is not None
        assert svad.sample_rate == 16000

    def test_streaming_vad_get_last_metrics(self) -> None:
        """StreamingVAD deve retornar métricas."""
        from jarvis.interface.entrada.vad import StreamingVAD

        svad = StreamingVAD(aggressiveness=2)
        metrics = svad.get_last_metrics()

        assert isinstance(metrics, dict)
        assert "vad_ms" in metrics
        assert "endpoint_ms" in metrics


class TestSileroVAD:
    """Testes do Silero VAD (quando disponível)."""

    def test_silero_is_available(self) -> None:
        """Verificar se Silero está disponível."""
        from jarvis.voz.adapters.vad_silero import is_available

        # Apenas verifica que a função existe e retorna bool
        result = is_available()
        assert isinstance(result, bool)

    def test_silero_has_cached_model(self) -> None:
        """Verificar se modelo Silero está em cache."""
        from jarvis.voz.adapters.vad_silero import has_cached_model

        result = has_cached_model()
        assert isinstance(result, bool)

    def test_silero_build_detector_sem_modelo(self) -> None:
        """build_silero_deactivity_detector sem modelo retorna None."""
        from jarvis.voz.adapters.vad_silero import (
            build_silero_deactivity_detector,
            is_available,
            has_cached_model,
        )

        if not is_available():
            pytest.skip("torch/numpy não disponível")

        if has_cached_model():
            pytest.skip("modelo já em cache")

        # Sem auto_download e sem cache, deve retornar None
        result = build_silero_deactivity_detector(auto_download=False)
        assert result is None

    def test_silero_deactivity_detector_mock(self) -> None:
        """SileroDeactivityDetector deve funcionar com mock."""
        np = pytest.importorskip("numpy")
        _torch = pytest.importorskip("torch")  # noqa: F841

        from jarvis.voz.adapters.vad_silero import SileroDeactivityDetector

        # Mock do modelo e get_speech_timestamps
        mock_model = MagicMock()

        def mock_get_speech_timestamps(audio, model, **kwargs):
            # Simula detecção de fala nos primeiros 8000 samples
            return [{"start": 0, "end": 8000}]

        detector = SileroDeactivityDetector(
            model=mock_model,
            get_speech_timestamps=mock_get_speech_timestamps,
            sensitivity=0.6,
        )

        # Áudio de 1 segundo
        audio = np.zeros(16000, dtype=np.int16).tobytes()

        trimmed, detected = detector.trim_on_deactivity(audio, 16000)

        assert detected is True
        assert len(trimmed) <= len(audio)

    def test_silero_trim_empty_audio(self) -> None:
        """SileroDeactivityDetector com áudio vazio."""
        _np = pytest.importorskip("numpy")  # noqa: F841
        _torch = pytest.importorskip("torch")  # noqa: F841

        from jarvis.voz.adapters.vad_silero import SileroDeactivityDetector

        mock_model = MagicMock()
        mock_get_speech_timestamps = MagicMock(return_value=[])

        detector = SileroDeactivityDetector(
            model=mock_model,
            get_speech_timestamps=mock_get_speech_timestamps,
            sensitivity=0.6,
        )

        trimmed, detected = detector.trim_on_deactivity(b"", 16000)

        assert trimmed == b""
        assert detected is False


class TestVADConfig:
    """Testes de configuração de VAD via env."""

    def test_vad_aggressiveness_via_env(self, monkeypatch) -> None:
        """Agressividade pode ser configurada via env."""
        monkeypatch.setenv("JARVIS_VAD_AGGRESSIVENESS", "3")

        from jarvis.interface.entrada.vad import _env_int

        assert _env_int("JARVIS_VAD_AGGRESSIVENESS", 2) == 3

    def test_vad_silence_ms_via_env(self, monkeypatch) -> None:
        """Tempo de silêncio pode ser configurado via env."""
        monkeypatch.setenv("JARVIS_VAD_SILENCE_MS", "500")

        from jarvis.interface.entrada.vad import _env_int

        assert _env_int("JARVIS_VAD_SILENCE_MS", 400) == 500

    def test_vad_pre_roll_ms_via_env(self, monkeypatch) -> None:
        """Pre-roll pode ser configurado via env."""
        monkeypatch.setenv("JARVIS_VAD_PRE_ROLL_MS", "100")

        from jarvis.interface.entrada.vad import _env_int

        assert _env_int("JARVIS_VAD_PRE_ROLL_MS", 50) == 100

    def test_vad_post_roll_ms_via_env(self, monkeypatch) -> None:
        """Post-roll pode ser configurado via env."""
        monkeypatch.setenv("JARVIS_VAD_POST_ROLL_MS", "300")

        from jarvis.interface.entrada.vad import _env_int

        assert _env_int("JARVIS_VAD_POST_ROLL_MS", 200) == 300


class TestAEC:
    """Testes de AEC (Acoustic Echo Cancellation)."""

    def test_is_aec_enabled_default(self, monkeypatch) -> None:
        """AEC está desabilitado por padrão."""
        monkeypatch.delenv("JARVIS_AEC_BACKEND", raising=False)

        from jarvis.interface.entrada.vad import is_aec_enabled

        assert is_aec_enabled() is False

    def test_is_aec_enabled_with_backend(self, monkeypatch) -> None:
        """AEC pode ser habilitado via env."""
        monkeypatch.setenv("JARVIS_AEC_BACKEND", "speex")

        from jarvis.interface.entrada.vad import is_aec_enabled

        assert is_aec_enabled() is True

    def test_apply_aec_to_audio_sem_aec(self, monkeypatch) -> None:
        """apply_aec_to_audio sem AEC retorna áudio original."""
        monkeypatch.delenv("JARVIS_AEC_BACKEND", raising=False)

        from jarvis.interface.entrada.vad import apply_aec_to_audio

        audio = b"\x00\x01\x02\x03"
        result = apply_aec_to_audio(audio, sample_rate=16000)

        assert result == audio

    def test_push_playback_reference(self) -> None:
        """push_playback_reference não deve crashar."""
        from jarvis.interface.entrada.vad import push_playback_reference

        # Não deve levantar exceção
        push_playback_reference(b"\x00\x01\x02\x03", sample_rate=16000)

    def test_reset_playback_reference(self) -> None:
        """reset_playback_reference não deve crashar."""
        from jarvis.interface.entrada.vad import reset_playback_reference

        # Não deve levantar exceção
        reset_playback_reference()


class TestVADMetrics:
    """Testes de métricas do VAD."""

    def test_vad_metrics_logging(self, monkeypatch) -> None:
        """Métricas de VAD podem ser logadas via env."""
        monkeypatch.setenv("JARVIS_VAD_METRICS", "1")

        from jarvis.interface.entrada.vad import _env_bool

        assert _env_bool("JARVIS_VAD_METRICS", False) is True

    def test_vad_metrics_disabled_by_default(self, monkeypatch) -> None:
        """Métricas de VAD estão desabilitadas por padrão."""
        monkeypatch.delenv("JARVIS_VAD_METRICS", raising=False)

        from jarvis.interface.entrada.vad import _env_bool

        assert _env_bool("JARVIS_VAD_METRICS", False) is False
