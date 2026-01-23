#!/usr/bin/env python3
"""
Testes completos de turn-taking (análise de turnos de fala).

Valida a heurística que decide se uma frase está completa ou incompleta.
"""
from __future__ import annotations

import pytest

from jarvis.interface.entrada.turn_taking import analyze_turn


class TestTurnTakingPontuacao:
    """Testes baseados em pontuação terminal."""

    def test_ponto_final_eh_completo(self) -> None:
        """Frase com ponto final é completa."""
        result = analyze_turn("Eu fui ao mercado.")
        assert result["is_complete"] is True
        assert result["reason"] == "terminal_punctuation"
        assert result["hold_ms"] == 0

    def test_interrogacao_eh_completo(self) -> None:
        """Frase com interrogação é completa."""
        result = analyze_turn("Você vai ao mercado?")
        assert result["is_complete"] is True
        assert result["reason"] == "terminal_punctuation"

    def test_exclamacao_eh_completo(self) -> None:
        """Frase com exclamação é completa."""
        result = analyze_turn("Que legal!")
        assert result["is_complete"] is True
        assert result["reason"] == "terminal_punctuation"

    def test_virgula_eh_incompleto(self) -> None:
        """Frase terminando em vírgula é incompleta."""
        result = analyze_turn("Eu fui ao mercado,")
        assert result["is_complete"] is False
        assert result["reason"] == "open_punctuation"
        hold_ms = result["hold_ms"]
        assert isinstance(hold_ms, int)
        assert hold_ms > 0

    def test_dois_pontos_eh_incompleto(self) -> None:
        """Frase terminando em dois pontos é incompleta."""
        result = analyze_turn("Olha isso:")
        assert result["is_complete"] is False
        assert result["reason"] == "open_punctuation"

    def test_ponto_virgula_eh_incompleto(self) -> None:
        """Frase terminando em ponto e vírgula é incompleta."""
        result = analyze_turn("Primeiro passo;")
        assert result["is_complete"] is False
        assert result["reason"] == "open_punctuation"

    @pytest.mark.xfail(reason="Detecção de reticências (...) não implementada")
    def test_reticencias_eh_incompleto(self) -> None:
        """Frase terminando em reticências é incompleta."""
        result = analyze_turn("Eu estava pensando...")
        assert result["is_complete"] is False
        assert result["reason"] == "open_punctuation"


class TestTurnTakingTokensIncompletos:
    """Testes de tokens que indicam frase incompleta."""

    @pytest.mark.parametrize(
        "token",
        ["e", "mas", "ou", "porque", "que", "pra", "para", "de", "do", "da", "com", "se", "quando", "então", "como", "por", "em"],
    )
    def test_tokens_incompletos(self, token: str) -> None:
        """Frases terminando em conectivos são incompletas."""
        result = analyze_turn(f"Eu quero ir {token}")
        assert result["is_complete"] is False
        assert result["reason"] == "incomplete_token"
        assert result["last_token"] == token
        hold_ms = result["hold_ms"]
        assert isinstance(hold_ms, int)
        assert hold_ms > 0

    def test_token_no_meio_nao_afeta(self) -> None:
        """Token incompleto no meio da frase não afeta resultado."""
        result = analyze_turn("Eu e você vamos ao parque.")
        assert result["is_complete"] is True


class TestTurnTakingFrasesCurtas:
    """Testes de frases curtas."""

    def test_uma_palavra_eh_incompleto(self) -> None:
        """Frase de uma palavra é incompleta."""
        result = analyze_turn("Jarvis")
        assert result["is_complete"] is False
        assert result["reason"] == "short_phrase"

    def test_duas_palavras_eh_incompleto(self) -> None:
        """Frase de duas palavras é incompleta (default min_words=3)."""
        result = analyze_turn("Oi Jarvis")
        assert result["is_complete"] is False
        assert result["reason"] == "short_phrase"

    def test_tres_palavras_eh_completo(self) -> None:
        """Frase de três palavras é completa por padrão."""
        result = analyze_turn("Liga a luz")
        assert result["is_complete"] is True
        assert result["reason"] == "default_complete"

    def test_frase_vazia_eh_completo(self) -> None:
        """Frase vazia é tratada como completa (nada a esperar)."""
        result = analyze_turn("")
        assert result["is_complete"] is True
        assert result["reason"] == "empty"
        assert result["hold_ms"] == 0

    def test_apenas_espacos_eh_completo(self) -> None:
        """Frase apenas com espaços é tratada como completa."""
        result = analyze_turn("   ")
        assert result["is_complete"] is True
        assert result["reason"] == "empty"


class TestTurnTakingHoldMs:
    """Testes do cálculo de hold_ms."""

    def test_frase_incompleta_tem_hold(self) -> None:
        """Frase incompleta deve ter hold_ms > 0."""
        result = analyze_turn("Eu quero e")
        hold_ms = result["hold_ms"]
        assert isinstance(hold_ms, int)
        assert hold_ms > 0

    def test_frase_completa_nao_tem_hold(self) -> None:
        """Frase completa deve ter hold_ms = 0."""
        result = analyze_turn("Eu quero isso.")
        assert result["hold_ms"] == 0

    def test_endpoint_ms_afeta_hold(self) -> None:
        """endpoint_ms baixo deve aumentar hold."""
        result_sem = analyze_turn("Eu quero e")
        result_com = analyze_turn("Eu quero e", endpoint_ms=100)
        # Com endpoint_ms curto, hold pode ser maior
        hold_com = result_com["hold_ms"]
        hold_sem = result_sem["hold_ms"]
        assert isinstance(hold_com, int) and isinstance(hold_sem, int)
        assert hold_com >= hold_sem


class TestTurnTakingConfig:
    """Testes de configuração via env."""

    def test_min_words_customizado(self, monkeypatch) -> None:
        """min_words pode ser customizado via env."""
        monkeypatch.setenv("JARVIS_TURN_TAKING_MIN_WORDS", "5")
        result = analyze_turn("Uma dois tres quatro")
        assert result["is_complete"] is False
        assert result["reason"] == "short_phrase"

        result = analyze_turn("Uma dois tres quatro cinco")
        assert result["is_complete"] is True

    def test_hold_ms_customizado(self, monkeypatch) -> None:
        """hold_ms base pode ser customizado via env."""
        monkeypatch.setenv("JARVIS_TURN_TAKING_HOLD_MS", "1000")
        result = analyze_turn("Eu quero e")
        hold_ms = result["hold_ms"]
        assert isinstance(hold_ms, int)
        assert hold_ms >= 1000


class TestTurnTakingCasosReais:
    """Testes com frases reais típicas de comandos de voz."""

    def test_comando_ligar_luz(self) -> None:
        """Comando típico de automação."""
        result = analyze_turn("Jarvis liga a luz da sala")
        assert result["is_complete"] is True

    @pytest.mark.xfail(reason="Detecção de artigo final não implementada (feature avançada)")
    def test_comando_incompleto(self) -> None:
        """Comando interrompido."""
        result = analyze_turn("Jarvis liga a")
        assert result["is_complete"] is False

    def test_pergunta_completa(self) -> None:
        """Pergunta completa."""
        result = analyze_turn("Qual é a previsão do tempo?")
        assert result["is_complete"] is True

    def test_pergunta_incompleta(self) -> None:
        """Pergunta sem pontuação mas com estrutura completa."""
        result = analyze_turn("Qual é a previsão do tempo")
        assert result["is_complete"] is True
        assert result["reason"] == "default_complete"

    def test_frase_com_numeros(self) -> None:
        """Frase com números."""
        result = analyze_turn("Define o timer para 5 minutos.")
        assert result["is_complete"] is True

    def test_comando_continuo(self) -> None:
        """Comando com indicação de continuação."""
        result = analyze_turn("Primeiro desliga a luz e")
        assert result["is_complete"] is False
        assert result["reason"] == "incomplete_token"
