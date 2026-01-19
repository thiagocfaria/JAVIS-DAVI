from jarvis.interface.entrada.turn_taking import analyze_turn


def test_turn_taking_incomplete() -> None:
    result = analyze_turn("fui na feira e")
    assert result["is_complete"] is False
    hold_ms = result.get("hold_ms")
    assert isinstance(hold_ms, int)
    assert hold_ms > 0


def test_turn_taking_complete() -> None:
    result = analyze_turn("fui na feira comprar pao.")
    assert result["is_complete"] is True
    assert result["hold_ms"] == 0
