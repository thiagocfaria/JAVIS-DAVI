"""Remote memory integration tests."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from jarvis.memoria.memory import HybridMemoryStore, LocalMemoryCache
from jarvis.memoria.remote_client import RemoteMemoryClient
from jarvis.memoria.remote_service import start_background_server


def _build_store(tmp_path: Path, base_url: str) -> HybridMemoryStore:
    local = LocalMemoryCache(tmp_path / "local.db")
    remote = RemoteMemoryClient(base_url=base_url)
    return HybridMemoryStore(local_cache=local, remote_client=remote, embedder=None, embed_dim=None)


def test_add_pushes_to_remote(tmp_path):
    server, store, thread = start_background_server()
    host, port = server.server_address
    base_url = f"http://{host}:{port}"

    memory = _build_store(tmp_path, base_url)
    memory.add_episode("Teste remoto", metadata={"source": "pytest"})

    # Allow small propagation window
    time.sleep(0.05)
    server.shutdown()
    thread.join(timeout=1)

    assert len(store.records) == 1
    record = store.records[0]
    assert record.text == "Teste remoto"
    assert record.metadata.get("source") == "pytest"


def test_search_merges_local_and_remote(tmp_path):
    server, store, thread = start_background_server()
    host, port = server.server_address
    base_url = f"http://{host}:{port}"

    memory = _build_store(tmp_path, base_url)
    # Local only
    memory.add_procedure("Procedimento local", metadata={"priority": 1})
    # Remote only
    client = RemoteMemoryClient(base_url=base_url)
    client.add(kind="procedure", text="Procedimento remoto", metadata={"priority": 2})

    results = memory.search("Procedimento", kind="procedure", limit=5)

    server.shutdown()
    thread.join(timeout=1)

    texts = {r.text for r in results}
    assert "Procedimento local" in texts
    assert "Procedimento remoto" in texts
    # Deduplication should keep size at most 2
    assert len(results) == 2


def test_cli_entrypoint_starts_server(tmp_path):
    proc = subprocess.Popen(
        [sys.executable, "-m", "jarvis.memoria.remote_service", "--host", "127.0.0.1", "--port", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    line = ""
    start = time.time()
    while time.time() - start < 5 and not line:
        line = proc.stdout.readline().strip()  # type: ignore[union-attr]

    assert "Remote memory server running on" in line
    base_url = line.split(" on ")[-1].strip()
    client = RemoteMemoryClient(base_url=base_url)
    remote_id = client.add("episode", "cli smoke test", metadata={"source": "pytest"})
    results = client.search("cli smoke test", limit=1)

    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:  # pragma: no cover - defensive
        proc.kill()

    assert remote_id is not None
    assert any(r.text == "cli smoke test" for r in results)

