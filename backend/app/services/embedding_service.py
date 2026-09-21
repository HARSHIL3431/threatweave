"""Local sentence embedding generation for RAG.

Uses a CPU-compatible SentenceTransformer model with no API key required.
The model is loaded lazily and cached so the heavy download/init happens once.
"""
from typing import List, Optional
import numpy as np

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("embedding_service")

# Shared lazy cache: the model is heavy and must be loaded only once per process.
_MODEL_CACHE = {}


class EmbeddingService:
    """Wrapper around a local SentenceTransformer for batch text embedding."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.RAG_EMBEDDING_MODEL

    def _ensure_model(self):
        if self.model_name not in _MODEL_CACHE:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {self.model_name}")
            _MODEL_CACHE[self.model_name] = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded")
        return _MODEL_CACHE[self.model_name]

    @property
    def dimension(self) -> int:
        """Embedding vector dimensionality."""
        return int(self._ensure_model().get_sentence_embedding_dimension())

    def embed(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Embed a list of texts, returning an (N, D) float32 array.

        Embeddings are L2-normalized so cosine similarity reduces to an
        inner product (compatible with faiss IndexFlatIP).
        """
        if not texts:
            raise ValueError("No texts provided to embed")
        model = self._ensure_model()
        vectors = model.encode(
            list(texts),
            batch_size=batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return np.asarray(vectors, dtype=np.float32).reshape(len(texts), -1)

    def embed_single(self, text: str) -> np.ndarray:
        return self.embed([text])[0]