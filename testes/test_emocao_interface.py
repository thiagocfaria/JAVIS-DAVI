import pytest

from jarvis.interface.entrada.emocao import detect_emotion


def test_emocao_heuristica_basica() -> None:
    np = pytest.importorskip("numpy")
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False)
    samples = (0.6 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    audio = (samples * 32767).astype(np.int16).tobytes()
    result = detect_emotion(audio, sr)
    assert result is not None
    assert result["label"] in {"neutro", "calmo", "agitado", "triste", "feliz"}
