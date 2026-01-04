"""
Memory module with local-first architecture.

Local: SQLite cache for offline fallback

Memory types:
- Episodic: What happened (task logs)
- Semantic: What it knows (knowledge + preferences)
- Procedural: How to do things (validated steps)

Memory layers:
- Hot: Recent, frequently used (in-memory cache)
- Warm: Less recent (local SQLite)
- Cold: Old, rarely used (archived)
- Fixed: Never expires (user-defined important memories)
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import threading
import time
from array import array
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from .embeddings import Embedder, build_embedder
except ImportError:
    build_embedder = None
    Embedder = None

try:
    from .remote_client import RemoteMemoryClient, RemoteMemoryItem
except ImportError:  # pragma: no cover - defensive
    RemoteMemoryClient = None  # type: ignore
    RemoteMemoryItem = None  # type: ignore


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class MemoryItem:
    """A memory item."""
    id: str | None = None
    kind: str = "episode"  # episode, knowledge, procedure, preference
    text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    ts: float = field(default_factory=time.time)
    layer: str = "warm"  # hot, warm, cold, fixed
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    expires_at: float | None = None


@dataclass
class SearchResult:
    """Search result with similarity score."""
    item: MemoryItem
    score: float


# ============================================================================
# HELPERS
# ============================================================================

def _normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def _hash_text(text: str) -> str:
    normalized = _normalize_text(text)
    return hashlib.sha256(normalized.encode()).hexdigest()


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for i in range(len(a)):
        dot += a[i] * b[i]
        norm_a += a[i] * a[i]
        norm_b += b[i] * b[i]
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def _recency_score(ts: float, now: float) -> float:
    age_days = max((now - ts) / 86400.0, 0.0)
    return 1.0 / (1.0 + age_days)


def _success_score(access_count: int) -> float:
    if access_count <= 0:
        return 0.0
    return min(access_count / 5.0, 1.0)


def _hybrid_score(similarity: float, ts: float, access_count: int, now: float) -> float:
    return (similarity * 0.6) + (_recency_score(ts, now) * 0.2) + (_success_score(access_count) * 0.2)


class LRUCache:
    def __init__(self, max_size: int = 128) -> None:
        self._max_size = max_size
        self._items: OrderedDict[str, object] = OrderedDict()

    def get(self, key: str) -> Optional[object]:
        if key not in self._items:
            return None
        value = self._items.pop(key)
        self._items[key] = value
        return value

    def set(self, key: str, value: object) -> None:
        if key in self._items:
            self._items.pop(key)
        self._items[key] = value
        if len(self._items) > self._max_size:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()


# ============================================================================
# LOCAL SQLITE CACHE (Minimal)
# ============================================================================

class LocalMemoryCache:
    """
    Local SQLite cache for offline fallback.

    Stores essential data locally (procedures + fixed knowledge).
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._fts_enabled = False
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        self._apply_pragmas(conn)
        return conn

    @staticmethod
    def _apply_pragmas(conn: sqlite3.Connection) -> None:
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA temp_store=MEMORY")
        except Exception:
            pass

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._connect()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    text TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    ts REAL NOT NULL,
                    layer TEXT DEFAULT 'warm',
                    access_count INTEGER DEFAULT 0,
                    last_accessed REAL,
                    text_hash TEXT,
                    embedding_blob BLOB,
                    embedding TEXT,
                    embedding_dim INTEGER
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_layer ON memories(layer)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_ts ON memories(ts DESC)
            """)
            self._ensure_column(conn, "memories", "text_hash", "TEXT")
            self._ensure_column(conn, "memories", "embedding_blob", "BLOB")
            self._ensure_column(conn, "memories", "embedding", "TEXT")
            self._ensure_column(conn, "memories", "embedding_dim", "INTEGER")
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_text_hash ON memories(text_hash)
            """)
            self._fts_enabled = self._init_fts(conn)
            self._maybe_migrate_embeddings(conn)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, col_type: str) -> None:
        try:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
            existing = {row[1] for row in rows}
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except Exception:
            pass

    def _maybe_migrate_embeddings(self, conn: sqlite3.Connection) -> None:
        try:
            rows = conn.execute(
                "SELECT id, embedding FROM memories "
                "WHERE embedding IS NOT NULL AND embedding_blob IS NULL "
                "LIMIT 200"
            ).fetchall()
            for item_id, embedding_json in rows:
                embedding = self._parse_embedding_json(embedding_json)
                blob = self._serialize_embedding_blob(embedding)
                if blob is None:
                    continue
                dim = len(embedding) if embedding else None
                conn.execute(
                    "UPDATE memories SET embedding_blob = ?, embedding_dim = ?, embedding = NULL "
                    "WHERE id = ?",
                    (blob, dim, item_id),
                )
        except Exception:
            pass

    def _init_fts(self, conn: sqlite3.Connection) -> bool:
        try:
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts "
                "USING fts5(id UNINDEXED, kind UNINDEXED, text, layer UNINDEXED, metadata UNINDEXED)"
            )
            mem_count = conn.execute("SELECT COUNT(1) FROM memories").fetchone()[0]
            fts_count = conn.execute("SELECT COUNT(1) FROM memories_fts").fetchone()[0]
            if mem_count and fts_count == 0:
                self._rebuild_fts(conn)
            return True
        except sqlite3.OperationalError:
            return False

    def _rebuild_fts(self, conn: sqlite3.Connection) -> None:
        conn.execute("DELETE FROM memories_fts")
        conn.execute(
            "INSERT INTO memories_fts (id, kind, text, layer, metadata) "
            "SELECT id, kind, text, layer, metadata FROM memories"
        )

    def _upsert_fts(self, conn: sqlite3.Connection, item: MemoryItem, metadata_json: str) -> None:
        if not self._fts_enabled:
            return
        conn.execute("DELETE FROM memories_fts WHERE id = ?", (item.id,))
        conn.execute(
            "INSERT INTO memories_fts (id, kind, text, layer, metadata) VALUES (?, ?, ?, ?, ?)",
            (item.id, item.kind, item.text, item.layer, metadata_json),
        )

    @property
    def fts_enabled(self) -> bool:
        return self._fts_enabled

    @staticmethod
    def _fts_query(query: str) -> Optional[str]:
        tokens = re.findall(r"[\w]+", query, flags=re.UNICODE)
        if not tokens:
            return None
        return " ".join([f"\"{token}\"" for token in tokens])

    @staticmethod
    def _parse_embedding_blob(value: Optional[bytes]) -> Optional[List[float]]:
        if value is None:
            return None
        try:
            buf = value if isinstance(value, (bytes, bytearray)) else bytes(value)
            arr = array("f")
            arr.frombytes(buf)
            return arr.tolist()
        except Exception:
            return None

    @staticmethod
    def _parse_embedding_json(value: Optional[str]) -> Optional[List[float]]:
        if not value:
            return None
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [float(x) for x in parsed]
        except Exception:
            return None
        return None

    @staticmethod
    def _serialize_embedding_blob(embedding: Optional[List[float]]) -> Optional[bytes]:
        if not embedding:
            return None
        try:
            arr = array("f", embedding)
            return arr.tobytes()
        except Exception:
            return None

    @classmethod
    def _row_to_item(cls, row: tuple) -> MemoryItem:
        embedding_blob = row[8] if len(row) > 8 else None
        embedding_json = row[9] if len(row) > 9 else None
        embedding = cls._parse_embedding_blob(embedding_blob)
        if embedding is None:
            embedding = cls._parse_embedding_json(embedding_json)
        return MemoryItem(
            id=row[0],
            kind=row[1],
            text=row[2],
            metadata=json.loads(row[3]),
            ts=row[4],
            layer=row[5],
            access_count=row[6],
            last_accessed=row[7],
            embedding=embedding,
        )

    def add(self, item: MemoryItem) -> str:
        """Add item to local cache."""
        item_id = item.id or self._generate_id(item.text)

        conn = self._connect()
        try:
            item.id = item_id
            metadata_json = json.dumps(item.metadata)
            text_hash = item.metadata.get("text_hash") or _hash_text(item.text)
            embedding_blob = self._serialize_embedding_blob(item.embedding)
            embedding_json = None
            if embedding_blob is None and item.embedding is not None:
                embedding_json = json.dumps(item.embedding)
            embedding_dim = len(item.embedding) if item.embedding else None
            conn.execute("""
                INSERT INTO memories
                (id, kind, text, metadata, ts, layer, access_count, last_accessed, text_hash, embedding_blob, embedding, embedding_dim)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    kind=excluded.kind,
                    text=excluded.text,
                    metadata=excluded.metadata,
                    ts=excluded.ts,
                    layer=excluded.layer,
                    access_count=excluded.access_count,
                    last_accessed=excluded.last_accessed,
                    text_hash=excluded.text_hash,
                    embedding_blob=excluded.embedding_blob,
                    embedding=excluded.embedding,
                    embedding_dim=excluded.embedding_dim
            """, (
                item_id,
                item.kind,
                item.text,
                metadata_json,
                item.ts,
                item.layer,
                item.access_count,
                item.last_accessed,
                text_hash,
                embedding_blob,
                embedding_json,
                embedding_dim,
            ))
            self._upsert_fts(conn, item, metadata_json)
            conn.commit()
            return item_id
        finally:
            conn.close()

    def get(self, item_id: str) -> MemoryItem | None:
        """Get item by ID."""
        conn = self._connect()
        try:
            cursor = conn.execute(
                "SELECT id, kind, text, metadata, ts, layer, access_count, last_accessed, "
                "embedding_blob, embedding FROM memories WHERE id = ?",
                (item_id,),
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_item(row)
            return None
        finally:
            conn.close()

    def search(self, query: str, kind: str | None = None, limit: int = 5) -> list[MemoryItem]:
        """Text search (FTS when available, otherwise LIKE)."""
        conn = self._connect()
        try:
            if query and self._fts_enabled:
                fts_query = self._fts_query(query)
                if fts_query:
                    sql = (
                        "SELECT m.id, m.kind, m.text, m.metadata, m.ts, m.layer, "
                        "m.access_count, m.last_accessed, m.embedding_blob, m.embedding "
                        "FROM memories_fts f JOIN memories m ON m.id = f.id "
                        "WHERE f MATCH ?"
                    )
                    params = [fts_query]
                    if kind:
                        sql += " AND m.kind = ?"
                        params.append(kind)
                    sql += " ORDER BY bm25(f), m.ts DESC LIMIT ?"
                    params.append(limit)
                    try:
                        cursor = conn.execute(sql, params)
                        return [self._row_to_item(row) for row in cursor.fetchall()]
                    except sqlite3.OperationalError:
                        pass

            sql = (
                "SELECT id, kind, text, metadata, ts, layer, access_count, last_accessed, "
                "embedding_blob, embedding FROM memories"
            )
            params = []
            conditions = []
            if query:
                conditions.append("text LIKE ?")
                params.append(f"%{query}%")
            if kind:
                conditions.append("kind = ?")
                params.append(kind)

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

            sql += " ORDER BY ts DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            return [self._row_to_item(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_procedures(self) -> list[MemoryItem]:
        """Get all procedures (for cache)."""
        return self.search("", kind="procedure", limit=100)

    def find_exact(self, kind: str, text: str) -> MemoryItem | None:
        """Find an exact memory match."""
        if not text:
            return None
        conn = self._connect()
        try:
            cursor = conn.execute(
                "SELECT id, kind, text, metadata, ts, layer, access_count, last_accessed, "
                "embedding_blob, embedding FROM memories WHERE kind = ? AND text = ? LIMIT 1",
                (kind, text),
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_item(row)
            return None
        finally:
            conn.close()

    def find_by_hash(self, kind: str, text_hash: str) -> MemoryItem | None:
        """Find a memory match by text hash."""
        if not text_hash:
            return None
        conn = self._connect()
        try:
            cursor = conn.execute(
                "SELECT id, kind, text, metadata, ts, layer, access_count, last_accessed, "
                "embedding_blob, embedding FROM memories WHERE kind = ? AND text_hash = ? LIMIT 1",
                (kind, text_hash),
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_item(row)
            return None
        finally:
            conn.close()

    def delete_by_id(self, item_id: str) -> bool:
        """Delete item by ID."""
        if not item_id:
            return False
        conn = self._connect()
        try:
            if self._fts_enabled:
                conn.execute("DELETE FROM memories_fts WHERE id = ?", (item_id,))
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (item_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_by_text(self, text: str, kind: str | None = None) -> int:
        """Delete items by text (LIKE match)."""
        if not text:
            return 0
        conn = self._connect()
        try:
            sql = "DELETE FROM memories WHERE text LIKE ?"
            params = [f"%{text}%"]
            if kind:
                sql += " AND kind = ?"
                params.append(kind)
            if self._fts_enabled:
                conn.execute(
                    "DELETE FROM memories_fts WHERE id IN "
                    "(SELECT id FROM memories WHERE text LIKE ?"
                    + (" AND kind = ?" if kind else "")
                    + ")",
                    params,
                )
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def update_access(self, item_id: str) -> None:
        """Update access metadata and adjust layer."""
        if not item_id:
            return
        now = time.time()
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT access_count, layer FROM memories WHERE id = ?",
                (item_id,),
            ).fetchone()
            if not row:
                return
            access_count = (row[0] or 0) + 1
            layer = row[1] or "warm"
            if layer not in {"fixed", "archive"}:
                if access_count >= 3:
                    layer = "hot"
                elif layer == "cold" and access_count >= 2:
                    layer = "warm"
            conn.execute(
                "UPDATE memories SET access_count = ?, last_accessed = ?, layer = ? WHERE id = ?",
                (access_count, now, layer, item_id),
            )
            conn.commit()
        finally:
            conn.close()

    def apply_decay(self, days_threshold: int = 30, archive_days: int = 180) -> int:
        """Move old memories across layers (warm/hot -> cold -> archive)."""
        if days_threshold <= 0:
            return 0
        if archive_days < days_threshold:
            archive_days = days_threshold * 2
        now = time.time()
        cutoff_cold = now - (days_threshold * 86400)
        cutoff_archive = now - (archive_days * 86400)
        conn = self._connect()
        try:
            cursor = conn.execute(
                "UPDATE memories SET layer = 'cold' "
                "WHERE layer IN ('hot', 'warm') "
                "AND last_accessed < ? "
                "AND layer != 'fixed'",
                (cutoff_cold,),
            )
            affected = cursor.rowcount
            cursor = conn.execute(
                "UPDATE memories SET layer = 'archive' "
                "WHERE layer = 'cold' "
                "AND last_accessed < ?",
                (cutoff_archive,),
            )
            affected += cursor.rowcount
            conn.commit()
            return affected
        finally:
            conn.close()

    def search_vector(
        self,
        embedding: List[float],
        kind: str | None = None,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> List[SearchResult]:
        """Local vector similarity search (brute force)."""
        if not embedding:
            return []
        conn = self._connect()
        try:
            sql = (
                "SELECT id, kind, text, metadata, ts, layer, access_count, last_accessed, "
                "embedding_blob, embedding "
                "FROM memories WHERE embedding_blob IS NOT NULL OR embedding IS NOT NULL"
            )
            params = []
            if kind:
                sql += " AND kind = ?"
                params.append(kind)
            cursor = conn.execute(sql, params)
            results: List[SearchResult] = []
            for row in cursor.fetchall():
                item = self._row_to_item(row)
                if not item.embedding:
                    continue
                if len(item.embedding) != len(embedding):
                    continue
                similarity = _cosine_similarity(embedding, item.embedding)
                if similarity < threshold:
                    continue
                results.append(SearchResult(item=item, score=similarity))
            results.sort(key=lambda r: r.score, reverse=True)
            return results[:limit]
        finally:
            conn.close()

    def _generate_id(self, text: str) -> str:
        """Generate ID from text."""
        return hashlib.md5(f"{text}{time.time()}".encode()).hexdigest()[:16]


# ============================================================================
# LOCAL MEMORY STORE (SQLite + optional embeddings)
# ============================================================================

class HybridMemoryStore:
    """
    Local memory with optional embeddings and cloud fallback.

    - Writes go to local cache
    - Reads use local cache (light) and optional Supabase cloud
    """

    def __init__(
        self,
        local_cache: LocalMemoryCache,
        cloud_store: SupabaseMemoryStore | None = None,
        remote_client: RemoteMemoryClient | None = None,
        embedder: Embedder | None = None,
        embed_dim: int | None = None,
        embed_episodes: bool = False,
    ) -> None:
        self.local = local_cache
        self.cloud = cloud_store
        self.remote = remote_client
        self.embedder = embedder
        self.embed_dim = embed_dim
        self.embed_episodes = embed_episodes
        self._hot_cache: dict[str, MemoryItem] = {}  # In-memory hot cache
        self._hot_cache_max = 50
        self._query_cache = LRUCache(max_size=128)
        self._vector_cache = LRUCache(max_size=64)

    def add(
        self,
        kind: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        layer: str = "warm",
        dedup: bool = False,
        ) -> str:
        """Add a memory item."""
        meta = dict(metadata or {})
        text_hash = _hash_text(text) if text else ""
        if text_hash:
            meta.setdefault("text_hash", text_hash)
        if dedup and text_hash:
            existing = self.local.find_by_hash(kind, text_hash)
            if existing and existing.id:
                return existing.id

        embedding = self._maybe_embed(kind, text)
        item = MemoryItem(
            kind=kind,
            text=text,
            metadata=meta,
            ts=time.time(),
            layer=layer,
            last_accessed=time.time(),
            embedding=embedding,
        )

        # Always add to local cache
        item_id = self.local.add(item)

        # Opportunistically push to remote store
        if self.remote:
            try:
                self.remote.add(kind=kind, text=text, metadata=meta)
            except Exception:
                pass

        # Add to hot cache if procedure
        if kind == "procedure":
            self._add_to_hot_cache(item)

        self._query_cache.clear()
        self._vector_cache.clear()

        return item_id

    def search(
        self,
        query: str,
        kind: str | None = None,
        limit: int = 5,
    ) -> list[MemoryItem]:
        """Search memories (text-based)."""
        cache_key = f"text|{kind or '*'}|{limit}|{query}"
        cached = self._query_cache.get(cache_key)
        if cached is not None:
            results = list(cached)
            self._record_access(results)
            return results

        results = self.local.search(query, kind, limit)
        remote_results: list[MemoryItem] = []
        if self.remote:
            try:
                remote_items = self.remote.search(query, kind=kind, limit=limit)
                remote_results = [
                    MemoryItem(
                        id=item.id,
                        kind=item.kind,
                        text=item.text,
                        metadata=item.metadata,
                        ts=item.ts,
                        layer="warm",
                    )
                    for item in remote_items
                ]
            except Exception:
                remote_results = []

        results = self._merge_results(results, remote_results, limit)
        self._record_access(results)
        self._query_cache.set(cache_key, results)
        return results

    def get_procedures(self) -> list[MemoryItem]:
        """Get all procedures (cached locally)."""
        # Check hot cache first
        procedures = [
            item for item in self._hot_cache.values()
            if item.kind == "procedure"
        ]
        if procedures:
            return procedures

        # Load from local cache
        return self.local.get_procedures()

    def add_episode(self, text: str, metadata: dict[str, Any] | None = None) -> str:
        """Add an episode (task log)."""
        return self.add("episode", text, metadata)

    def add_procedure(self, text: str, metadata: dict[str, Any] | None = None) -> str:
        """Add a procedure (validated steps)."""
        return self.add("procedure", text, metadata, layer="fixed")

    def add_knowledge(self, text: str, metadata: dict[str, Any] | None = None) -> str:
        """Add knowledge/preference."""
        return self.add("knowledge", text, metadata)

    def add_fixed_knowledge(self, text: str, metadata: dict[str, Any] | None = None) -> str:
        """Add fixed knowledge (never expires)."""
        return self.add("knowledge", text, metadata, layer="fixed", dedup=True)

    def search_semantic(
        self,
        query: str,
        kind: str | None = None,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> list[SearchResult]:
        """Search memories using vector similarity (local only)."""
        if not self.embedder:
            return []
        cache_key = f"vector|{kind or '*'}|{limit}|{threshold}|{query}"
        cached = self._vector_cache.get(cache_key)
        if cached is not None:
            results = list(cached)
            self._record_access([result.item for result in results])
            return results
        try:
            embedding = self.embedder.embed(query)
            if self.embed_dim and len(embedding) != self.embed_dim:
                return []
            results = self.local.search_vector(
                embedding=embedding,
                kind=kind,
                limit=limit,
                threshold=threshold,
            )
            now = time.time()
            for result in results:
                similarity = result.score
                result.score = _hybrid_score(similarity, result.item.ts, result.item.access_count, now)
            results.sort(key=lambda r: r.score, reverse=True)
            results = results[:limit]
            self._record_access([result.item for result in results])
            self._vector_cache.set(cache_key, results)
            return results
        except Exception:
            return []

    def _maybe_embed(self, kind: str, text: str) -> list[float] | None:
        """Generate embedding when enabled and supported."""
        if not self.embedder or not text.strip():
            return None
        if kind == "episode" and not self.embed_episodes:
            return None
        try:
            embedding = self.embedder.embed(text)
            if self.embed_dim and len(embedding) != self.embed_dim:
                return None
            return embedding
        except Exception:
            return None

    def _add_to_hot_cache(self, item: MemoryItem) -> None:
        """Add item to in-memory hot cache."""
        if len(self._hot_cache) >= self._hot_cache_max:
            # Evict oldest
            oldest = min(self._hot_cache.values(), key=lambda x: x.last_accessed)
            if oldest.id:
                del self._hot_cache[oldest.id]

        if item.id:
            self._hot_cache[item.id] = item

    def _record_access(self, items: list[MemoryItem]) -> None:
        for item in items:
            if not item.id:
                continue
            self.local.update_access(item.id)

    def apply_decay(self, days_threshold: int = 30, archive_days: int = 180) -> int:
        """Apply decay rules across local store."""
        return self.local.apply_decay(days_threshold=days_threshold, archive_days=archive_days)

    def forget(self, text: str, kind: str | None = None) -> int:
        """Forget memories matching text."""
        if not text:
            return 0
        deleted_local = 0
        exact = self.local.find_exact(kind, text) if kind else None
        if exact and exact.id:
            deleted_local = 1 if self.local.delete_by_id(exact.id) else 0
        else:
            deleted_local = self.local.delete_by_text(text, kind=kind)

        self._query_cache.clear()
        self._vector_cache.clear()

        return deleted_local

    @staticmethod
    def _merge_results(
        local_results: list[MemoryItem], remote_results: list[MemoryItem], limit: int
    ) -> list[MemoryItem]:
        """Merge and deduplicate results preferring local freshness."""

        seen = set()
        merged: list[MemoryItem] = []
        for item in local_results + remote_results:
            key = (item.kind, _normalize_text(item.text))
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
            if len(merged) >= limit:
                break
        return merged


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def build_memory_store(
    db_path: Path,
) -> HybridMemoryStore:
    """Build local memory store."""
    local = LocalMemoryCache(db_path)

    remote_client = None
    remote_url = os.environ.get("JARVIS_REMOTE_MEMORY_URL")
    remote_token = os.environ.get("JARVIS_REMOTE_MEMORY_TOKEN")
    if remote_url and RemoteMemoryClient:
        try:
            remote_client = RemoteMemoryClient(base_url=remote_url, token=remote_token)
        except Exception:
            remote_client = None

    embed_dim_env = os.environ.get("JARVIS_EMBED_DIM")
    embed_dim = int(embed_dim_env) if embed_dim_env and embed_dim_env.isdigit() else 384
    enable_embeddings = os.environ.get("JARVIS_ENABLE_EMBEDDINGS", "true").lower() in {
        "1", "true", "yes", "on"
    }
    embed_episodes = os.environ.get("JARVIS_EMBED_EPISODES", "false").lower() in {
        "1", "true", "yes", "on"
    }
    embedder = None
    if enable_embeddings and build_embedder:
        try:
            embedder = build_embedder(enable_cache=True)
        except Exception:
            embedder = None

    if embed_dim is None and embedder is not None:
        embed_dim = embedder.dimension

    return HybridMemoryStore(
        local_cache=local,
        remote_client=remote_client,
        embedder=embedder,
        embed_dim=embed_dim,
        embed_episodes=embed_episodes,
    )
