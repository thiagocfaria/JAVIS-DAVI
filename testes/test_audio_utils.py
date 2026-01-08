from __future__ import annotations

from array import array

import pytest

from jarvis.entrada.audio_utils import coerce_pcm_bytes


def test_coerce_int_list_treated_as_int16() -> None:
    payload = [0, 1, 2, 3]
    result = coerce_pcm_bytes(payload)
    expected = array("h", payload).tobytes()
    assert result == expected
    assert len(result) == 8


def test_coerce_int_list_rejects_out_of_range() -> None:
    with pytest.raises(TypeError):
        coerce_pcm_bytes([40000])


def test_coerce_int_list_rejects_below_range() -> None:
    with pytest.raises(TypeError):
        coerce_pcm_bytes([-40000])


def test_coerce_int_list_accepts_int16_bounds() -> None:
    payload = [-32768, 32767]
    result = coerce_pcm_bytes(payload)
    assert len(result) == 4


def test_coerce_rejects_odd_length_bytes() -> None:
    with pytest.raises(TypeError):
        coerce_pcm_bytes(b"\x00")
