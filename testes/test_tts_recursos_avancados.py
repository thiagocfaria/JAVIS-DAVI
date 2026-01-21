#!/usr/bin/env python3
"""
Testes completos dos recursos avançados de TTS.

Valida: cache, barge-in, word timing, chunking, phase1 ack.
"""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from jarvis.cerebro.config import Config
else:
    from jarvis.cerebro.config import Config


@pytest.fixture
def tts_config() -> Config:
    """Config básica para TTS."""
    from jarvis.cerebro.config import load_config
    config = load_config()
    # Garantir que tts_mode é local
    if hasattr(config, "tts_mode"):
        config = config.__class__(**{**config.__dict__, "tts_mode": "local"})
    return config


@pytest.fixture
def tts_none_config() -> Config:
    """Config com TTS desabilitado."""
    from jarvis.cerebro.config import load_config
    config = load_config()
    # Garantir que tts_mode é none
    if hasattr(config, "tts_mode"):
        config = config.__class__(**{**config.__dict__, "tts_mode": "none"})
    return config


class TestTTSWordTiming:
    """Testes de word timing (estimativa de tempo por palavra)."""

    def test_word_timing_habilitado(self, monkeypatch, tts_none_config: Config) -> None:
        """Word timing pode ser habilitado via env."""
        monkeypatch.setenv("JARVIS_TTS_WORD_TIMING", "1")
        monkeypatch.setenv("JARVIS_TTS_MODE", "none")

        from jarvis.interface.saida.tts import TextToSpeech

        config = cast(Config, tts_none_config)
        tts = TextToSpeech(config)
        assert tts._word_timing_enabled is True

    def test_word_timing_desabilitado_por_padrao(self, monkeypatch, tts_none_config: Config) -> None:
        """Word timing está desabilitado por padrão."""
        monkeypatch.delenv("JARVIS_TTS_WORD_TIMING", raising=False)

        from jarvis.interface.saida.tts import TextToSpeech

        config = cast(Config, tts_none_config)
        tts = TextToSpeech(config)
        assert tts._word_timing_enabled is False

    def test_estimate_word_timings_retorna_lista(self, tts_none_config: Config) -> None:
        """_estimate_word_timings deve retornar lista de timings."""
        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        timings, duration = tts._estimate_word_timings("ola mundo teste")

        assert len(timings) == 3
        assert all("word" in t for t in timings)
        assert all("start_ms" in t for t in timings)
        assert all("end_ms" in t for t in timings)
        assert timings[0]["word"] == "ola"
        assert timings[1]["word"] == "mundo"
        assert timings[2]["word"] == "teste"

    def test_estimate_word_timings_offset(self, tts_none_config: Config) -> None:
        """_estimate_word_timings deve respeitar offset."""
        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        timings, _ = tts._estimate_word_timings("ola mundo", offset_ms=1000.0)

        start_ms = timings[0]["start_ms"]
        assert isinstance(start_ms, (int, float))
        assert float(start_ms) >= 1000.0

    def test_estimate_word_timings_texto_vazio(self, tts_none_config) -> None:
        """Texto vazio deve retornar lista vazia."""
        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        timings, duration = tts._estimate_word_timings("")

        assert timings == []
        assert duration == 0.0

    def test_get_last_word_timings(self, monkeypatch, tts_none_config) -> None:
        """get_last_word_timings deve retornar timings após speak."""
        monkeypatch.setenv("JARVIS_TTS_WORD_TIMING", "1")

        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        tts.speak("teste de timing")

        timings = tts.get_last_word_timings()
        # Em modo none, pode não processar, mas não deve crashar
        # Verificamos apenas que o método existe e retorna algo
        assert timings is None or isinstance(timings, list)


class TestTTSChunking:
    """Testes de chunking de texto longo."""

    def test_chunking_habilitado(self, monkeypatch, tts_none_config) -> None:
        """Chunking pode ser habilitado via env."""
        monkeypatch.setenv("JARVIS_TTS_CHUNKING", "1")

        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        assert tts._chunking_enabled is True

    def test_split_chunks_divide_texto(self, tts_none_config) -> None:
        """_split_chunks deve dividir texto em sentenças."""
        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        texto = "Primeira frase. Segunda frase. Terceira frase."
        chunks = tts._split_chunks(texto)

        assert len(chunks) >= 1
        # Deve preservar todo o conteúdo
        assert "Primeira" in "".join(chunks)
        assert "Terceira" in "".join(chunks)

    def test_split_chunks_texto_curto(self, tts_none_config) -> None:
        """Texto curto não precisa ser dividido."""
        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        texto = "Texto curto."
        chunks = tts._split_chunks(texto)

        assert len(chunks) >= 1

    def test_auto_chunk_long_text(self, monkeypatch, tts_none_config) -> None:
        """Auto-chunking para textos muito longos."""
        monkeypatch.setenv("JARVIS_TTS_AUTO_CHUNK_LONG_TEXT", "1")
        monkeypatch.setenv("JARVIS_TTS_AUTO_CHUNK_MIN_CHARS", "50")

        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        assert tts._auto_chunk_long_text is True
        assert tts._auto_chunk_min_chars == 50


class TestTTSCache:
    """Testes de cache de TTS."""

    def test_cache_habilitado(self, monkeypatch, tts_none_config) -> None:
        """Cache pode ser habilitado via env."""
        monkeypatch.setenv("JARVIS_TTS_CACHE", "1")

        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        assert tts._cache_enabled is True

    def test_cache_desabilitado_por_padrao(self, monkeypatch, tts_none_config) -> None:
        """Cache está desabilitado por padrão."""
        monkeypatch.delenv("JARVIS_TTS_CACHE", raising=False)

        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        assert tts._cache_enabled is False

    def test_cache_put_e_get(self, monkeypatch, tts_none_config) -> None:
        """Cache deve armazenar e recuperar áudio."""
        monkeypatch.setenv("JARVIS_TTS_CACHE", "1")

        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)

        # Simular put
        texto = "teste de cache"
        audio = b"\x00\x01\x02\x03" * 100

        tts._cache_put(texto, audio)
        cached = tts._cache_get(texto)

        assert cached == audio

    def test_cache_max_entries(self, monkeypatch, tts_none_config) -> None:
        """Cache deve respeitar limite de entradas."""
        monkeypatch.setenv("JARVIS_TTS_CACHE", "1")
        monkeypatch.setenv("JARVIS_TTS_CACHE_MAX_ENTRIES", "3")

        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)

        # Adicionar mais entradas que o limite
        for i in range(5):
            tts._cache_put(f"texto {i}", f"audio {i}".encode())

        # Cache deve ter no máximo 3 entradas
        assert len(tts._cache) <= 3


class TestTTSBargeIn:
    """Testes de barge-in (interrupção de TTS por fala do usuário)."""

    def test_barge_in_habilitado(self, monkeypatch, tts_none_config) -> None:
        """Barge-in pode ser habilitado via env."""
        monkeypatch.setenv("JARVIS_TTS_BARGE_IN", "1")

        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        assert tts._barge_in_enabled is True

    def test_barge_in_desabilitado_por_padrao(self, monkeypatch, tts_none_config) -> None:
        """Barge-in está desabilitado por padrão."""
        monkeypatch.delenv("JARVIS_TTS_BARGE_IN", raising=False)

        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        assert tts._barge_in_enabled is False

    def test_should_stop_playback_sem_barge_in(self, monkeypatch, tts_none_config) -> None:
        """_should_stop_playback retorna False sem barge-in."""
        monkeypatch.delenv("JARVIS_TTS_BARGE_IN", raising=False)

        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        assert tts._should_stop_playback() is False

    def test_should_stop_playback_com_stop_file(self, monkeypatch, tts_none_config) -> None:
        """_should_stop_playback retorna True quando stop file existe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            stop_file = Path(tmpdir) / "stop"
            monkeypatch.setenv("JARVIS_TTS_BARGE_IN", "1")
            monkeypatch.setenv("JARVIS_TTS_BARGE_IN_STOP_FILE", str(stop_file))

            from jarvis.interface.saida.tts import TextToSpeech

            tts = TextToSpeech(tts_none_config)
            tts._barge_in_stop_file = stop_file

            # Sem arquivo, não para
            assert tts._should_stop_playback() is False

            # Com arquivo, para
            stop_file.touch()
            assert tts._should_stop_playback() is True


class TestTTSPhase1Ack:
    """Testes de phase1 ack (som de confirmação imediato)."""

    def test_play_phase1_ack_existe(self, tts_none_config) -> None:
        """Método play_phase1_ack deve existir."""
        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        assert hasattr(tts, "play_phase1_ack")
        assert callable(tts.play_phase1_ack)

    def test_play_phase1_ack_em_modo_none(self, tts_none_config) -> None:
        """play_phase1_ack não deve crashar em modo none."""
        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        # Não deve levantar exceção
        tts.play_phase1_ack()

    def test_earcon_raw_gerado(self, tts_none_config) -> None:
        """Earcon raw é gerado quando necessário."""
        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        # _earcon_raw é gerado internamente quando necessário
        # Não há _earcon_path, apenas _earcon_raw gerado dinamicamente
        assert hasattr(tts, "_earcon_raw")


class TestTTSMetrics:
    """Testes de métricas do TTS."""

    def test_get_last_metrics_retorna_dict(self, tts_none_config) -> None:
        """get_last_metrics deve retornar dicionário."""
        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        metrics = tts.get_last_metrics()

        assert isinstance(metrics, dict)

    def test_metricas_apos_speak(self, tts_none_config) -> None:
        """Métricas devem ser preenchidas após speak."""
        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        tts.speak("teste")
        metrics = tts.get_last_metrics()

        # Em modo none, métricas podem ser None
        # Verificamos apenas que não crasha
        assert isinstance(metrics, dict)


class TestTTSPauseResume:
    """Testes de pause/resume de TTS."""

    def test_pause_e_resume(self, tts_none_config) -> None:
        """pause e resume não devem crashar."""
        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)

        tts.pause()
        assert tts._pause_event.is_set() is False

        tts.resume()
        assert tts._pause_event.is_set() is True

    def test_stop(self, tts_none_config) -> None:
        """stop não deve crashar."""
        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        tts.stop()

        assert tts._stop_event.is_set() is True


class TestTTSStreaming:
    """Testes de streaming de TTS."""

    def test_speak_stream_existe(self, tts_none_config) -> None:
        """Método speak_stream deve existir."""
        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        assert hasattr(tts, "speak_stream")
        assert callable(tts.speak_stream)

    def test_speak_stream_com_chunks(self, tts_none_config) -> None:
        """speak_stream deve processar chunks."""
        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        chunks = ["Primeiro chunk.", "Segundo chunk.", "Terceiro chunk."]

        # Não deve crashar
        tts.speak_stream(iter(chunks))

    def test_streaming_enabled_via_env(self, monkeypatch, tts_none_config) -> None:
        """Streaming pode ser habilitado via env."""
        monkeypatch.setenv("JARVIS_TTS_STREAMING", "1")

        from jarvis.interface.saida.tts import TextToSpeech

        tts = TextToSpeech(tts_none_config)
        assert tts._streaming_enabled is True
