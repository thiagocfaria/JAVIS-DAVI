"""Tests for jarvis.memoria.embeddings — mocked where sentence-transformers needed."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from jarvis.memoria.embeddings import (
    EmbeddingCache,
    EmbeddingRouter,
    Embedder,
    check_embedding_deps,
)


# ---------------------------------------------------------------------------
# EmbeddingCache
# ---------------------------------------------------------------------------

class TestEmbeddingCache(unittest.TestCase):
    def test_get_miss(self) -> None:
        cache = EmbeddingCache()
        self.assertIsNone(cache.get("never seen"))

    def test_set_and_get(self) -> None:
        cache = EmbeddingCache()
        cache.set("hello", [0.1, 0.2, 0.3])
        result = cache.get("hello")
        self.assertEqual(result, [0.1, 0.2, 0.3])

    def test_same_text_same_key(self) -> None:
        cache = EmbeddingCache()
        cache.set("text", [1.0])
        self.assertEqual(cache.get("text"), [1.0])

    def test_different_text_different_key(self) -> None:
        cache = EmbeddingCache()
        cache.set("a", [1.0])
        cache.set("b", [2.0])
        self.assertEqual(cache.get("a"), [1.0])
        self.assertEqual(cache.get("b"), [2.0])

    def test_eviction_when_full(self) -> None:
        cache = EmbeddingCache(max_size=2)
        cache.set("first", [1.0])
        cache.set("second", [2.0])
        # Adding third evicts one entry
        cache.set("third", [3.0])
        self.assertEqual(len(cache._cache), 2)
        self.assertEqual(cache.get("third"), [3.0])

    def test_max_size_respected(self) -> None:
        cache = EmbeddingCache(max_size=3)
        for i in range(10):
            cache.set(f"text_{i}", [float(i)])
        self.assertLessEqual(len(cache._cache), 3)


# ---------------------------------------------------------------------------
# Embedder (base class)
# ---------------------------------------------------------------------------

class TestBaseEmbedder(unittest.TestCase):
    def test_embed_raises_not_implemented(self) -> None:
        e = Embedder()
        with self.assertRaises(NotImplementedError):
            e.embed("hello")

    def test_embed_batch_calls_embed(self) -> None:
        e = Embedder()
        e.embed = MagicMock(return_value=[0.1, 0.2])
        result = e.embed_batch(["a", "b", "c"])
        self.assertEqual(len(result), 3)
        self.assertEqual(e.embed.call_count, 3)

    def test_is_available_default_true(self) -> None:
        self.assertTrue(Embedder().is_available())

    def test_dimension_default(self) -> None:
        self.assertEqual(Embedder().dimension, 384)


# ---------------------------------------------------------------------------
# EmbeddingRouter
# ---------------------------------------------------------------------------

class TestEmbeddingRouterNoModel(unittest.TestCase):
    """Test router behaviour when no local model is available."""

    def _make_router_no_model(self) -> EmbeddingRouter:
        with patch("jarvis.memoria.embeddings.LocalEmbedder") as MockLocal:
            MockLocal.return_value.is_available.return_value = False
            router = EmbeddingRouter()
        return router

    def test_is_not_available_when_no_embedder(self) -> None:
        router = self._make_router_no_model()
        self.assertFalse(router.is_available())

    def test_embed_raises_when_no_embedder(self) -> None:
        router = self._make_router_no_model()
        with self.assertRaises(RuntimeError):
            router.embed("hello")

    def test_dimension_default_when_no_embedder(self) -> None:
        router = self._make_router_no_model()
        self.assertEqual(router.dimension, 384)

    def test_no_cache_when_disabled(self) -> None:
        with patch("jarvis.memoria.embeddings.LocalEmbedder") as MockLocal:
            MockLocal.return_value.is_available.return_value = False
            router = EmbeddingRouter(enable_cache=False)
        self.assertIsNone(router._cache)


class TestEmbeddingRouterWithMockedEmbedder(unittest.TestCase):
    """Test router with a mocked local embedder."""

    def _make_router(self) -> EmbeddingRouter:
        mock_embedder = MagicMock()
        mock_embedder.is_available.return_value = True
        mock_embedder.embed.return_value = [0.1, 0.2, 0.3]
        mock_embedder.dimension = 384

        with patch("jarvis.memoria.embeddings.LocalEmbedder", return_value=mock_embedder):
            router = EmbeddingRouter()
        return router

    def test_is_available(self) -> None:
        router = self._make_router()
        self.assertTrue(router.is_available())

    def test_embed_returns_embedding(self) -> None:
        router = self._make_router()
        result = router.embed("hello world")
        self.assertEqual(result, [0.1, 0.2, 0.3])

    def test_embed_caches_result(self) -> None:
        router = self._make_router()
        router.embed("hello")
        router.embed("hello")  # second call should hit cache
        # The underlying embedder should only be called once
        self.assertEqual(router._embedders[0].embed.call_count, 1)

    def test_embed_batch_returns_list(self) -> None:
        router = self._make_router()
        results = router.embed_batch(["a", "b"])
        self.assertEqual(len(results), 2)

    def test_embed_batch_uses_cache(self) -> None:
        router = self._make_router()
        # Pre-cache "a"
        if router._cache:
            router._cache.set("a", [9.9])
        results = router.embed_batch(["a", "b"])
        # "a" should come from cache
        self.assertEqual(results[0], [9.9])

    def test_dimension_from_active_embedder(self) -> None:
        router = self._make_router()
        router.embed("trigger active")
        self.assertEqual(router.dimension, 384)

    def test_get_active_provider(self) -> None:
        router = self._make_router()
        router.embed("trigger")
        provider = router.get_active_provider()
        self.assertIsNotNone(provider)

    def test_required_dim_filters_embedders(self) -> None:
        mock_embedder = MagicMock()
        mock_embedder.is_available.return_value = True
        mock_embedder.dimension = 128  # Different from required 384

        with patch("jarvis.memoria.embeddings.LocalEmbedder", return_value=mock_embedder):
            router = EmbeddingRouter(required_dim=384)
        # Embedder with wrong dim should be filtered out
        self.assertFalse(router.is_available())

    def test_embed_error_propagates(self) -> None:
        mock_embedder = MagicMock()
        mock_embedder.is_available.return_value = True
        mock_embedder.embed.side_effect = RuntimeError("model error")
        mock_embedder.dimension = 384

        with patch("jarvis.memoria.embeddings.LocalEmbedder", return_value=mock_embedder):
            router = EmbeddingRouter()

        with self.assertRaises(RuntimeError):
            router.embed("will fail")


class TestCheckEmbeddingDeps(unittest.TestCase):
    def test_returns_dict(self) -> None:
        deps = check_embedding_deps()
        self.assertIn("sentence_transformers", deps)
        self.assertIsInstance(deps["sentence_transformers"], bool)


if __name__ == "__main__":
    unittest.main()
