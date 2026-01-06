from __future__ import annotations

from jarvis.voz.vad import StreamingVAD


def _make_frame(label: int, frame_size: int = 4) -> bytes:
    """Create deterministic fake frame bytes for testing."""
    return bytes([label % 256]) * frame_size


def test_pre_roll_trims_initial_silence():
    frame_size = 4
    events: list[tuple[bytes, bool]] = []
    # initial silence (labels 1..4)
    for label in range(1, 5):
        events.append((_make_frame(label, frame_size), False))
    # speech (labels 5..6)
    for label in range(5, 7):
        events.append((_make_frame(label, frame_size), True))
    # trailing silence (labels 7..9)
    for label in range(7, 10):
        events.append((_make_frame(label, frame_size), False))

    result = StreamingVAD._assemble_frames(
        frame_events=events,
        pre_roll_frames=2,
        post_roll_frames=1,
        silence_frames=2,
    )

    expected_frames = [
        _make_frame(3, frame_size),
        _make_frame(4, frame_size),
        _make_frame(5, frame_size),
        _make_frame(6, frame_size),
        _make_frame(7, frame_size),
    ]
    assert result == b"".join(expected_frames)


def test_pre_roll_returns_recent_silence_when_no_voice():
    events: list[tuple[bytes, bool]] = [
        (_make_frame(label), False) for label in range(1, 7)
    ]

    result = StreamingVAD._assemble_frames(
        frame_events=events,
        pre_roll_frames=3,
        post_roll_frames=2,
        silence_frames=2,
    )

    expected_frames = [
        _make_frame(4),
        _make_frame(5),
        _make_frame(6),
    ]
    assert result == b"".join(expected_frames)
