from __future__ import annotations

from jarvis.entrada.stt import apply_wake_word_filter


def test_wake_word_required_accepts():
    assert (
        apply_wake_word_filter(
            "jarvis, abrir navegador", wake_word="jarvis", require=True
        )
        == "abrir navegador"
    )


def test_wake_word_required_rejects():
    assert (
        apply_wake_word_filter("abrir navegador", wake_word="jarvis", require=True)
        == ""
    )


def test_wake_word_optional_allows_plain_text():
    assert (
        apply_wake_word_filter("abrir navegador", wake_word="jarvis", require=False)
        == "abrir navegador"
    )


def test_wake_word_normalization():
    assert (
        apply_wake_word_filter("Jarvis:  ligar luz", wake_word="jarvis", require=True)
        == "ligar luz"
    )


def test_wake_word_empty_input():
    assert apply_wake_word_filter("", wake_word="jarvis", require=True) == ""


def test_wake_word_boundary_rejects_suffix():
    assert (
        apply_wake_word_filter("jarvisinho abrir", wake_word="jarvis", require=True)
        == ""
    )
