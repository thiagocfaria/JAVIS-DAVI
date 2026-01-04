"""
Embeddings module for semantic memory search (local only).
"""
from __future__ import annotations

import hashlib
import os
from typing import Optional

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except ImportError:
    SentenceTransformer = None


# ============================================================================
# EMBEDDING CACHE
# ============================================================================

class EmbeddingCache:
    """Simple in-memory cache for embeddings."""

    def __init__(self, max_size: int = 500) -> None:
        self._cache: dict[str, list[float]] = {}
        self._max_size = max_size

    def get(self, text: str) -> list[float] | None:
        """Get cached embedding."""
        key = self._make_key(text)
        return self._cache.get(key)

    def set(self, text: str, embedding: list[float]) -> None:
        """Cache embedding."""
        if len(self._cache) >= self._max_size:
            # Evict random entry
            self._cache.pop(next(iter(self._cache)))

        key = self._make_key(text)
        self._cache[key] = embedding

    def _make_key(self, text: str) -> str:
        """Create cache key."""
        return hashlib.md5(text.encode()).hexdigest()


# ============================================================================
# BASE EMBEDDER
# ============================================================================

class Embedder:
    """Base class for embedding providers."""

    def embed(self, text: str) -> list[float]:
        """Get embedding for text."""
        raise NotImplementedError

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts."""
        return [self.embed(text) for text in texts]

    def is_available(self) -> bool:
        """Check if embedder is available."""
        return True

    @property
    def dimension(self) -> int:
        """Embedding dimension."""
        return 384  # Default for all-MiniLM-L6-v2


# ============================================================================
# LOCAL EMBEDDER (sentence-transformers)
# ============================================================================

class LocalEmbedder(Embedder):
    """
    Local embedding using sentence-transformers.
    
    Local embeddings via sentence-transformers.
    Requires: pip install sentence-transformers
    """
    
    def __init__(self, model_name: Optional[str] = None) -> None:
        default_model = os.environ.get("JARVIS_EMBED_MODEL", "intfloat/multilingual-e5-small")
        self.model_name = model_name or default_model
        self._model = None
        dim_env = os.environ.get("JARVIS_EMBED_DIM", "384")
        self._dimension = int(dim_env) if dim_env.isdigit() else 384

    def is_available(self) -> bool:
        return SentenceTransformer is not None

    @property
    def dimension(self) -> int:
        return self._dimension

    def _load_model(self) -> SentenceTransformer:
        if self._model is None:
            if SentenceTransformer is None:
                raise RuntimeError("sentence-transformers not installed")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, text: str) -> list[float]:
        model = self._load_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = self._load_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return [e.tolist() for e in embeddings]


# ============================================================================
# EMBEDDING ROUTER (local only)
# ============================================================================

class EmbeddingRouter(Embedder):
    """
    Embedding router (local only).
    """

    def __init__(
        self,
        enable_cache: bool = True,
        required_dim: int | None = None,
        provider: str = "local",
    ) -> None:
        self._embedders: list[Embedder] = []
        self._cache = EmbeddingCache() if enable_cache else None
        self._active_embedder: Embedder | None = None
        self._required_dim = required_dim
        self._provider = provider.lower()

        local = LocalEmbedder()
        if local.is_available():
            self._embedders.append(local)

        # Enforce dimension if requested
        if self._required_dim is not None:
            self._embedders = [
                embedder for embedder in self._embedders
                if embedder.dimension == self._required_dim
            ]

    def is_available(self) -> bool:
        return len(self._embedders) > 0

    @property
    def dimension(self) -> int:
        if self._active_embedder:
            return self._active_embedder.dimension
        if self._embedders:
            return self._embedders[0].dimension
        return 384

    def embed(self, text: str) -> list[float]:
        # Check cache
        if self._cache:
            cached = self._cache.get(text)
            if cached:
                return cached

        # Try each embedder
        last_error = None
        for embedder in self._embedders:
            try:
                embedding = embedder.embed(text)
                self._active_embedder = embedder

                # Cache result
                if self._cache:
                    self._cache.set(text, embedding)

                return embedding
            except Exception as e:
                last_error = e
                continue

        if last_error:
            raise RuntimeError(f"All embedders failed: {last_error}")

        raise RuntimeError("No embedders available")

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Check cache for each text
        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []

        if self._cache:
            for i, text in enumerate(texts):
                cached = self._cache.get(text)
                if cached:
                    results[i] = cached
                else:
                    uncached_indices.append(i)
                    uncached_texts.append(text)
        else:
            uncached_indices = list(range(len(texts)))
            uncached_texts = texts

        # Embed uncached texts
        if uncached_texts:
            for embedder in self._embedders:
                try:
                    embeddings = embedder.embed_batch(uncached_texts)
                    self._active_embedder = embedder

                    # Fill in results and cache
                    for i, idx in enumerate(uncached_indices):
                        results[idx] = embeddings[i]
                        if self._cache:
                            self._cache.set(uncached_texts[i], embeddings[i])

                    break
                except Exception:
                    continue

        return results

    def get_active_provider(self) -> str | None:
        """Get name of active embedding provider."""
        if self._active_embedder is None:
            return None
        return type(self._active_embedder).__name__


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def build_embedder(
    enable_cache: bool = True,
) -> Embedder:
    """Build embedder (local only)."""
    provider = os.environ.get("JARVIS_EMBED_PROVIDER", "local").strip().lower()
    required_dim_env = os.environ.get("JARVIS_EMBED_DIM")
    required_dim = int(required_dim_env) if required_dim_env and required_dim_env.isdigit() else 384

    router = EmbeddingRouter(
        enable_cache=enable_cache,
        required_dim=required_dim,
        provider=provider,
    )

    if not router.is_available():
        raise RuntimeError(
            "No local embedding provider available. "
            "Install sentence-transformers and ensure JARVIS_EMBED_DIM matches."
        )

    return router


def check_embedding_deps() -> dict:
    """Check embedding dependencies."""
    return {
        "sentence_transformers": SentenceTransformer is not None,
    }
