"""
tests/conftest.py — Safe test-only embedding mock and global fixtures.

Eliminates unintended Hugging Face downloads during offline CI runs
without modifying production application behavior.
"""
import hashlib
import os
import sys

import numpy as np
import pytest
from unittest.mock import MagicMock


class MockEmbeddingService:
    """
    Test-only embedding service: stable, deterministic, unit-normalised vectors.

    Algorithm: SHA-256(text) → 8-byte big-endian seed → np.random.default_rng
    seed → standard_normal(dim) float32 → L2 normalise.

    Properties:
    - Cross-process stable (no Python hash randomisation).
    - Does NOT touch global np.random state.
    - Distinct texts produce distinct vectors with overwhelming probability.
    - Empty batch returns shape (0, 384) without error.
    """

    def __init__(self, model_name: str = "mock-offline-embedder", dimension: int = 384):
        self.model_name = model_name
        self._dimension = dimension
        self.model = MagicMock()
        self.model.get_sentence_embedding_dimension.return_value = dimension

    def _embed_single(self, text: str) -> np.ndarray:
        seed_int = int.from_bytes(
            hashlib.sha256(text.encode("utf-8")).digest()[:8], "big"
        )
        rng = np.random.default_rng(seed_int)
        raw = rng.standard_normal(self._dimension).astype(np.float32)
        norm = np.linalg.norm(raw)
        return raw / (norm if norm > 0 else 1.0)

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        if not texts:
            return np.empty((0, self._dimension), dtype=np.float32)
        return np.stack([self._embed_single(t) for t in texts]).astype(np.float32)

    def embed_text(self, text: str) -> np.ndarray:
        return self.embed_texts([text])

    @property
    def dimension(self) -> int:
        return self._dimension


@pytest.fixture(autouse=True)
def mock_offline_embeddings(monkeypatch):
    """
    When running in offline mode (TRANSFORMERS_OFFLINE=1 or HF_HUB_OFFLINE=1),
    intercept EmbeddingService instantiation in vector_store and main to prevent
    network requests to Hugging Face Hub during FastAPI lifespan startup.

    Fails loudly if the target module cannot be patched — never silently skips.
    """
    if os.getenv("TRANSFORMERS_OFFLINE") != "1" and os.getenv("HF_HUB_OFFLINE") != "1":
        return  # Online mode: let tests use real embeddings if they need to.

    import vector_store  # ImportError propagates — fail loudly
    monkeypatch.setattr(vector_store, "EmbeddingService", MockEmbeddingService)

    if "main" in sys.modules:
        monkeypatch.setattr(sys.modules["main"], "EmbeddingService", MockEmbeddingService)
