"""Remote memory client with graceful fallbacks.

This client uses only the Python standard library (urllib) so it can run in
lightweight environments without extra dependencies. It sends JSON payloads to
an HTTP endpoint that exposes two minimal routes:

- ``POST /memories``: ``{"kind": str, "text": str, "metadata": dict}``
  returns ``{"id": str, "ts": float}``
- ``POST /search``: ``{"query": str, "kind": Optional[str], "limit": int}``
  returns ``{"results": [{"id", "kind", "text", "metadata", "ts"}]}``

When the remote endpoint is unreachable, the client fails silently and returns
``None``/``[]`` so the local cache can continue to operate.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


log = logging.getLogger(__name__)


@dataclass
class RemoteMemoryItem:
    id: str
    kind: str
    text: str
    metadata: Dict[str, Any]
    ts: float


class RemoteMemoryClient:
    """HTTP client for a lightweight remote memory service."""

    def __init__(
        self, base_url: str, token: str | None = None, timeout: float = 3.0
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "jarvis-remote-memory/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode()
        request = urllib.request.Request(
            url, data=data, headers=self._headers(), method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
                return json.loads(body.decode())
        except (
            urllib.error.URLError,
            json.JSONDecodeError,
        ) as exc:  # pragma: no cover - defensive
            log.debug("Remote memory request failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    def add(
        self, kind: str, text: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str | None:
        """Send a memory item to the remote store.

        Returns the remote id when successful, otherwise ``None``.
        """

        payload = {
            "kind": kind,
            "text": text,
            "metadata": metadata or {},
        }
        result = self._post("/memories", payload)
        if not result:
            return None
        return result.get("id")

    def search(
        self, query: str, kind: str | None = None, limit: int = 5
    ) -> List[RemoteMemoryItem]:
        """Search remote memories.

        When the remote endpoint is unavailable, an empty list is returned.
        """

        payload = {"query": query, "kind": kind, "limit": limit}
        result = self._post("/search", payload)
        if not result:
            return []

        items: Iterable[dict[str, Any]] = result.get("results", [])
        parsed: list[RemoteMemoryItem] = []
        for item in items:
            try:
                parsed.append(
                    RemoteMemoryItem(
                        id=str(item.get("id", "")),
                        kind=str(item.get("kind", "")),
                        text=str(item.get("text", "")),
                        metadata=dict(item.get("metadata") or {}),
                        ts=float(item.get("ts", time.time())),
                    )
                )
            except Exception:
                continue
        return parsed
