import tempfile
import time
import unittest
from pathlib import Path

from jarvis.memoria.embeddings import Embedder
from jarvis.memoria.memory import HybridMemoryStore, LocalMemoryCache, MemoryItem


class TestMemoriaLocal(unittest.TestCase):
    def test_fixar_e_esquecer_memoria(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.sqlite3"
            store = HybridMemoryStore(local_cache=LocalMemoryCache(db_path))
            first = store.add_fixed_knowledge("lembrar isso")
            second = store.add_fixed_knowledge("lembrar isso")
            self.assertEqual(first, second)

            deleted = store.forget("lembrar isso", kind="knowledge")
            self.assertGreaterEqual(deleted, 1)
            deleted_again = store.forget("lembrar isso", kind="knowledge")
            self.assertEqual(deleted_again, 0)

    def test_fts_search_recency(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.sqlite3"
            cache = LocalMemoryCache(db_path)
            old = MemoryItem(
                id="old",
                kind="knowledge",
                text="alpha item",
                metadata={},
                ts=1.0,
                layer="warm",
                access_count=0,
                last_accessed=1.0,
            )
            new = MemoryItem(
                id="new",
                kind="knowledge",
                text="alpha item",
                metadata={},
                ts=2.0,
                layer="warm",
                access_count=0,
                last_accessed=2.0,
            )
            cache.add(old)
            cache.add(new)
            results = cache.search("alpha", kind="knowledge", limit=2)
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].id, "new")

    def test_semantic_search_local_fallback(self) -> None:
        class DummyEmbedder(Embedder):
            def __init__(self) -> None:
                self._dimension = 2

            @property
            def dimension(self) -> int:
                return self._dimension

            def embed(self, text: str) -> list[float]:
                lowered = text.lower()
                if "alpha" in lowered:
                    return [1.0, 0.0]
                if "beta" in lowered:
                    return [0.0, 1.0]
                return [0.0, 0.0]

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.sqlite3"
            store = HybridMemoryStore(
                local_cache=LocalMemoryCache(db_path),
                cloud_store=None,
                embedder=DummyEmbedder(),
                embed_dim=2,
            )
            store.add_knowledge("alpha memory")
            store.add_knowledge("beta memory")

            results = store.search_semantic(
                "alpha", kind="knowledge", limit=2, threshold=0.0
            )
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].item.text, "alpha memory")

    def test_embedding_blob_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.sqlite3"
            cache = LocalMemoryCache(db_path)
            item = MemoryItem(
                id="emb",
                kind="knowledge",
                text="alpha",
                metadata={},
                ts=1.0,
                layer="warm",
                access_count=0,
                last_accessed=1.0,
                embedding=[0.1, 0.2, 0.3],
            )
            cache.add(item)
            fetched = cache.get("emb")
            self.assertIsNotNone(fetched)
            assert fetched is not None
            assert fetched.embedding is not None
            self.assertEqual(len(fetched.embedding), 3)
            self.assertAlmostEqual(fetched.embedding[0], 0.1, places=5)
            self.assertAlmostEqual(fetched.embedding[1], 0.2, places=5)
            self.assertAlmostEqual(fetched.embedding[2], 0.3, places=5)

    def test_access_updates_layer_and_decay(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "memory.sqlite3"
            cache = LocalMemoryCache(db_path)
            now = time.time()
            item = MemoryItem(
                id="hot",
                kind="knowledge",
                text="alpha",
                metadata={},
                ts=now,
                layer="warm",
                access_count=0,
                last_accessed=now,
            )
            cache.add(item)
            cache.update_access("hot")
            cache.update_access("hot")
            cache.update_access("hot")
            fetched = cache.get("hot")
            self.assertIsNotNone(fetched)
            assert fetched is not None
            self.assertEqual(fetched.layer, "hot")

            old_item = MemoryItem(
                id="old",
                kind="knowledge",
                text="beta",
                metadata={},
                ts=now - (40 * 86400),
                layer="warm",
                access_count=0,
                last_accessed=now - (40 * 86400),
            )
            cache.add(old_item)
            affected = cache.apply_decay(days_threshold=30, archive_days=60)
            self.assertGreaterEqual(affected, 1)
            decayed = cache.get("old")
            self.assertIsNotNone(decayed)
            assert decayed is not None
            self.assertEqual(decayed.layer, "cold")


if __name__ == "__main__":
    unittest.main()
