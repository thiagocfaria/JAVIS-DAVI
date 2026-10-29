from __future__ import annotations

from collections import deque
from typing import Iterable


class RollingPercentiles:
    """Track rolling percentiles for stage latencies (ms)."""

    def __init__(self, max_samples: int = 200) -> None:
        self._max_samples = max(10, int(max_samples))
        self._samples: dict[str, deque[float]] = {}

    def record(self, stage: str, value_ms: float | None) -> float | None:
        if value_ms is None:
            return None
        try:
            value = float(value_ms)
        except (TypeError, ValueError):
            return None
        if value < 0:
            return None
        bucket = self._samples.setdefault(stage, deque(maxlen=self._max_samples))
        bucket.append(value)
        return self.p95(stage)

    def p95(self, stage: str) -> float | None:
        values = self._samples.get(stage)
        if not values:
            return None
        ordered = sorted(values)
        idx = int(round(0.95 * (len(ordered) - 1)))
        idx = max(0, min(idx, len(ordered) - 1))
        return ordered[idx]

    def snapshot(self, stages: Iterable[str]) -> dict[str, float | None]:
        return {stage: self.p95(stage) for stage in stages}
