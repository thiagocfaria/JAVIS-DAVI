#!/usr/bin/env python3
"""
Testes com gravações reais de áudio.

Usa os arquivos WAV pré-gravados para validar STT, VAD e pipeline completo.
Estes testes requerem os modelos carregados e são mais lentos.
"""
from __future__ import annotations

import wave
from pathlib import Path

import pytest


# Diretório de áudios de teste
TEST_AUDIO_DIR = Path("Documentos/DOC_INTERFACE/test_audio")
BENCH_AUDIO_DIR = Path("Documentos/DOC_INTERFACE/bench_audio")

# Textos esperados para cada áudio
EXPECTED_TEXT = {
    "oi_jarvis_clean.wav": "oi jarvis",
    "oi_jarvis_tv.wav": "oi jarvis",
    "oi_jarvis_tv_alta.wav": "oi jarvis",
    "comando_longo.wav": "jarvis, este é um teste longo de comando de voz para benchmark",
    "comando_longo_tv.wav": "jarvis, este é um teste longo de comando de voz para benchmark",
    "ruido_puro.wav": "",
    "sussurro.wav": "jarvis",
}


def _load_wav(path: Path) -> tuple[bytes, int]:
    """Carrega arquivo WAV e retorna bytes e sample rate."""
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        samplerate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    if channels != 1:
        raise ValueError(f"{path} precisa ser mono (1 canal)")
    return frames, samplerate


def _similarity(a: str, b: str) -> float:
    """Calcula similaridade entre duas strings."""
    import difflib
    return difflib.SequenceMatcher(a=a.lower().strip(), b=b.lower().strip()).ratio()


@pytest.fixture(scope="module")
def stt():
    """Fixture que carrega o STT uma vez por módulo."""
    from jarvis.cerebro.config import load_config
    from jarvis.interface.entrada.stt import SpeechToText

    config = load_config()
    return SpeechToText(config)


@pytest.fixture(scope="module")
def vad():
    """Fixture que carrega o VAD uma vez por módulo."""
    from jarvis.interface.entrada.vad import VoiceActivityDetector

    return VoiceActivityDetector(aggressiveness=2, sample_rate=16000)


def _skip_if_no_audio():
    """Pula teste se áudios não existem."""
    if not TEST_AUDIO_DIR.exists():
        pytest.skip(f"Diretório {TEST_AUDIO_DIR} não encontrado")


class TestAudioFilesExist:
    """Verifica que os arquivos de áudio de teste existem."""

    def test_test_audio_dir_exists(self) -> None:
        """Diretório de áudios de teste deve existir."""
        if not TEST_AUDIO_DIR.exists():
            pytest.skip("Diretório de áudios não encontrado")
        assert TEST_AUDIO_DIR.is_dir()

    @pytest.mark.parametrize("audio_name", list(EXPECTED_TEXT.keys()))
    def test_audio_file_exists(self, audio_name: str) -> None:
        """Cada arquivo de áudio esperado deve existir."""
        _skip_if_no_audio()
        path = TEST_AUDIO_DIR / audio_name
        assert path.exists(), f"Arquivo {path} não encontrado"

    @pytest.mark.parametrize("audio_name", list(EXPECTED_TEXT.keys()))
    def test_audio_is_valid_wav(self, audio_name: str) -> None:
        """Cada arquivo deve ser um WAV válido."""
        _skip_if_no_audio()
        path = TEST_AUDIO_DIR / audio_name
        frames, sr = _load_wav(path)
        assert sr == 16000, f"{audio_name} deve ser 16kHz"
        assert len(frames) > 0, f"{audio_name} não pode estar vazio"


@pytest.mark.slow
class TestSTTComGravacoes:
    """Testes de STT com gravações reais."""

    @pytest.mark.parametrize(
        "audio_name,expected",
        [
            ("oi_jarvis_clean.wav", "oi jarvis"),
            ("comando_longo.wav", "jarvis, este é um teste longo de comando de voz para benchmark"),
        ],
    )
    def test_transcricao_audio_limpo(self, stt, audio_name: str, expected: str) -> None:
        """STT deve transcrever corretamente áudio limpo."""
        _skip_if_no_audio()
        path = TEST_AUDIO_DIR / audio_name
        frames, sr = _load_wav(path)

        stt._reset_last_metrics()
        result = stt._transcribe_audio_bytes(
            frames,
            require_wake_word=False,
            skip_speech_check=True,
            allow_short_audio=True,
            skip_rust_trim=True,
        )

        text = result[0] if isinstance(result, tuple) else result
        text = (text or "").strip()

        sim = _similarity(text, expected)
        assert sim >= 0.7, f"Similaridade {sim:.2f} < 0.7 para {audio_name}: '{text}' vs '{expected}'"

    @pytest.mark.parametrize(
        "audio_name,expected",
        [
            ("oi_jarvis_tv.wav", "oi jarvis"),
            ("oi_jarvis_tv_alta.wav", "oi jarvis"),
        ],
    )
    def test_transcricao_audio_com_ruido(self, stt, audio_name: str, expected: str) -> None:
        """STT deve transcrever razoavelmente áudio com ruído."""
        _skip_if_no_audio()
        path = TEST_AUDIO_DIR / audio_name
        frames, sr = _load_wav(path)

        stt._reset_last_metrics()
        result = stt._transcribe_audio_bytes(
            frames,
            require_wake_word=False,
            skip_speech_check=True,
            allow_short_audio=True,
            skip_rust_trim=True,
        )

        text = result[0] if isinstance(result, tuple) else result
        text = (text or "").strip()

        sim = _similarity(text, expected)
        # Tolerância maior para áudio com ruído
        assert sim >= 0.5, f"Similaridade {sim:.2f} < 0.5 para {audio_name}: '{text}' vs '{expected}'"

    def test_ruido_puro_nao_gera_texto(self, stt) -> None:
        """Ruído puro não deve gerar transcrição significativa."""
        _skip_if_no_audio()
        path = TEST_AUDIO_DIR / "ruido_puro.wav"
        frames, sr = _load_wav(path)

        stt._reset_last_metrics()
        result = stt._transcribe_audio_bytes(
            frames,
            require_wake_word=False,
            skip_speech_check=False,  # Verificar fala
            allow_short_audio=True,
            skip_rust_trim=True,
        )

        text = result[0] if isinstance(result, tuple) else result
        text = (text or "").strip()

        # Ruído puro deve gerar texto vazio ou muito curto
        assert len(text) < 20, f"Ruído gerou texto demais: '{text}'"


@pytest.mark.slow
class TestVADComGravacoes:
    """Testes de VAD com gravações reais."""

    @pytest.mark.parametrize(
        "audio_name",
        ["oi_jarvis_clean.wav", "comando_longo.wav"],
    )
    def test_vad_detecta_fala(self, vad, audio_name: str) -> None:
        """VAD deve detectar fala em áudios com voz."""
        _skip_if_no_audio()
        path = TEST_AUDIO_DIR / audio_name
        frames, sr = _load_wav(path)

        speech_frames = 0
        total_frames = 0

        for frame in vad.frames_from_audio(frames):
            total_frames += 1
            processed = vad.preprocess_frame(frame)
            if vad.is_speech_preprocessed(processed):
                speech_frames += 1

        speech_ratio = speech_frames / total_frames if total_frames > 0 else 0
        assert speech_ratio > 0.1, f"VAD detectou muito pouca fala: {speech_ratio:.2%}"

    def test_vad_detecta_silencio(self, vad) -> None:
        """VAD deve detectar silêncio em áudio de ruído puro."""
        _skip_if_no_audio()
        path = TEST_AUDIO_DIR / "ruido_puro.wav"
        frames, sr = _load_wav(path)

        speech_frames = 0
        total_frames = 0

        for frame in vad.frames_from_audio(frames):
            total_frames += 1
            processed = vad.preprocess_frame(frame)
            if vad.is_speech_preprocessed(processed):
                speech_frames += 1

        speech_ratio = speech_frames / total_frames if total_frames > 0 else 0
        # Ruído pode ter alguns frames detectados como fala, mas não muitos
        assert speech_ratio < 0.5, f"VAD detectou muita 'fala' no ruído: {speech_ratio:.2%}"


@pytest.mark.slow
class TestEndpointingComGravacoes:
    """Testes de endpointing com gravações reais."""

    @pytest.mark.parametrize(
        "audio_name",
        ["oi_jarvis_clean.wav", "comando_longo.wav"],
    )
    def test_endpoint_detectado(self, vad, audio_name: str) -> None:
        """Endpointing deve detectar fim de fala."""
        _skip_if_no_audio()
        path = TEST_AUDIO_DIR / audio_name
        frames, sr = _load_wav(path)

        silence_ms = 400
        frame_ms = 30
        silence_frames_needed = max(1, int(silence_ms / frame_ms))

        speech_detected = False
        silence_count = 0
        endpoint_reached = False

        for frame in vad.frames_from_audio(frames):
            processed = vad.preprocess_frame(frame)
            is_speech = vad.is_speech_preprocessed(processed)

            if is_speech:
                speech_detected = True
                silence_count = 0
            elif speech_detected:
                silence_count += 1
                if silence_count >= silence_frames_needed:
                    endpoint_reached = True
                    break

        assert speech_detected, f"Nenhuma fala detectada em {audio_name}"
        assert endpoint_reached, f"Endpoint não detectado em {audio_name}"


@pytest.mark.slow
class TestEmocaoComGravacoes:
    """Testes de detecção de emoção com gravações reais."""

    @pytest.mark.parametrize(
        "audio_name",
        ["oi_jarvis_clean.wav", "comando_longo.wav"],
    )
    def test_emocao_detectada(self, audio_name: str) -> None:
        """Detecção de emoção deve retornar resultado para áudio com fala."""
        _skip_if_no_audio()
        from jarvis.interface.entrada.emocao import detect_emotion

        path = TEST_AUDIO_DIR / audio_name
        frames, sr = _load_wav(path)

        result = detect_emotion(frames, sr)

        assert result is not None, f"Emoção não detectada para {audio_name}"
        assert "label" in result
        assert "confidence" in result
        assert result["label"] in {"neutro", "calmo", "agitado", "triste", "feliz"}


@pytest.mark.slow
class TestMetricasComGravacoes:
    """Testes de métricas com gravações reais."""

    def test_stt_metrics_preenchidas(self, stt) -> None:
        """Métricas de STT devem ser preenchidas após transcrição."""
        _skip_if_no_audio()
        path = TEST_AUDIO_DIR / "oi_jarvis_clean.wav"
        frames, sr = _load_wav(path)

        stt._reset_last_metrics()
        stt._transcribe_audio_bytes(
            frames,
            require_wake_word=False,
            skip_speech_check=True,
            allow_short_audio=True,
            skip_rust_trim=True,
        )

        metrics = stt.get_last_metrics()
        assert isinstance(metrics, dict)
        # Pelo menos alguma métrica deve estar presente
        assert len(metrics) > 0


class TestBenchAudioFiles:
    """Testes com arquivos de benchmark."""

    def test_bench_audio_dir_exists(self) -> None:
        """Diretório de benchmark deve existir."""
        if not BENCH_AUDIO_DIR.exists():
            pytest.skip("Diretório de benchmark não encontrado")
        assert BENCH_AUDIO_DIR.is_dir()

    @pytest.mark.parametrize(
        "audio_name",
        ["voice_clean.wav", "voice_noise.wav"],
    )
    def test_bench_audio_exists(self, audio_name: str) -> None:
        """Arquivos de benchmark devem existir."""
        if not BENCH_AUDIO_DIR.exists():
            pytest.skip("Diretório de benchmark não encontrado")

        path = BENCH_AUDIO_DIR / audio_name
        assert path.exists(), f"Arquivo {path} não encontrado"
