"""Minimal remote memory service for local/VPS use.

This module provides a tiny HTTP server (standard library only) that stores
memories in-process. It is intended for:

- quick local/VPS deployments where FastAPI/Flask would be overkill
- integration tests that validate the remote memory client

Usage:

```python
from jarvis.memoria.remote_service import start_background_server

server, store, thread = start_background_server()
# server.server_address -> (host, port)
```
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List, Optional, Tuple


@dataclass
class _MemoryRecord:
    id: str
    kind: str
    text: str
    metadata: Dict
    ts: float


@dataclass
class InMemoryRemoteStore:
    """In-memory storage used by the HTTP server."""

    records: List[_MemoryRecord] = field(default_factory=list)
    _counter: int = 0

    def add(
        self, kind: str, text: str, metadata: Optional[Dict] = None
    ) -> _MemoryRecord:
        self._counter += 1
        record = _MemoryRecord(
            id=str(self._counter),
            kind=kind,
            text=text,
            metadata=metadata or {},
            ts=time.time(),
        )
        self.records.append(record)
        return record

    def search(
        self, query: str, kind: Optional[str], limit: int
    ) -> List[_MemoryRecord]:
        query_norm = query.lower()
        results: list[_MemoryRecord] = []
        for rec in reversed(self.records):  # newest first
            if kind and rec.kind != kind:
                continue
            if query_norm and query_norm not in rec.text.lower():
                continue
            results.append(rec)
            if len(results) >= limit:
                break
        return results


def _build_handler(store: InMemoryRemoteStore):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, payload: Dict) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            try:
                body = self.rfile.read(length)
                payload = json.loads(body.decode()) if body else {}
            except Exception:
                self._send(400, {"error": "invalid json"})
                return

            if self.path == "/memories":
                kind = str(payload.get("kind", ""))
                text = str(payload.get("text", ""))
                metadata = (
                    payload.get("metadata")
                    if isinstance(payload.get("metadata"), dict)
                    else {}
                )
                record = store.add(kind=kind, text=text, metadata=metadata)
                self._send(200, {"id": record.id, "ts": record.ts})
                return

            if self.path == "/search":
                query = str(payload.get("query", ""))
                kind = payload.get("kind")
                kind = str(kind) if kind is not None else None
                limit = int(payload.get("limit", 5)) or 5
                results = store.search(query=query, kind=kind, limit=limit)
                payload_results = [
                    {
                        "id": rec.id,
                        "kind": rec.kind,
                        "text": rec.text,
                        "metadata": rec.metadata,
                        "ts": rec.ts,
                    }
                    for rec in results
                ]
                self._send(200, {"results": payload_results})
                return

            self._send(404, {"error": "not found"})

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            # Silence noisy output in tests
            return

    return Handler


def start_background_server(
    host: str = "127.0.0.1", port: int = 0
) -> Tuple[ThreadingHTTPServer, InMemoryRemoteStore, threading.Thread]:
    """Start the minimal HTTP server in a background thread."""

    store = InMemoryRemoteStore()
    handler = _build_handler(store)
    server = ThreadingHTTPServer((host, port), handler)

    def _run() -> None:
        server.serve_forever()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return server, store, thread


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Lightweight remote memory server")
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host/IP to bind (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind (default: 8000, use 0 for random)",
    )
    args = parser.parse_args(argv)

    server, _store, thread = start_background_server(host=args.host, port=args.port)
    server_addr = server.server_address
    host = server_addr[0]
    port = server_addr[1] if len(server_addr) > 1 else args.port
    print(f"Remote memory server running on http://{host}:{port}", flush=True)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down remote memory server...", flush=True)
    finally:
        server.shutdown()
        thread.join(timeout=2)


if __name__ == "__main__":  # pragma: no cover - manual/CLI entrypoint
    main()
