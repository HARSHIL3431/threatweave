import json
from pathlib import Path
from typing import Any, Dict
import hashlib

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.ml_service import MLService
from app.services.vector_store import VectorStore


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Path to test fixtures."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def sample_flows(fixtures_dir: Path) -> Dict[str, Any]:
    """Load curated sample flows with verified baseline scores."""
    with open(fixtures_dir / "sample_flows.json", "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def loaded_ml_service() -> MLService:
    """Pre-loaded MLService instance for unit testing."""
    svc = MLService()
    svc.load_artifacts()
    return svc


@pytest.fixture(scope="module")
def client() -> TestClient:
    """FastAPI TestClient with initialized lifespan."""
    with TestClient(app) as test_client:
        yield test_client


class FakeEmbedder:
    """Deterministic tiny embedder so tests never load the real model.

    Two identical texts always map to the same normalized vector, and
    different texts map to different vectors - enough to exercise retrieval.
    """

    DIM = 8

    def embed(self, texts, batch_size: int = 32) -> np.ndarray:
        vectors = []
        for text in texts:
            digest = hashlib.md5(text.encode("utf-8")).digest()
            v = np.frombuffer(digest, dtype=np.uint8).astype(np.float32)[: self.DIM]
            v = np.pad(v, (0, self.DIM - len(v))) / 255.0
            norm = np.linalg.norm(v)
            vectors.append(v / norm if norm > 0 else v)
        return np.asarray(vectors, dtype=np.float32).reshape(len(texts), self.DIM)

    @property
    def dimension(self) -> int:
        return self.DIM


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def make_store(tmp_path: Path):
    """Factory building a real FAISS store (with FakeEmbedder) in a tmp dir.

    Returns a callable: make_store(documents) -> (index_path, metadata_path)
    where each document is {"text": str, "meta": dict} (meta carries at least
    technique_id / technique_name / type and optional extra fields).
    """

    def _make(documents) -> "tuple[Path, Path]":
        index_dir = tmp_path / "vectorstore"
        index_dir.mkdir(parents=True, exist_ok=True)
        index_path = index_dir / "index.faiss"
        metadata_path = index_dir / "metadata.json"
        embedder = FakeEmbedder()
        vectors = embedder.embed([d["text"] for d in documents])
        store = VectorStore.create(
            vectors=vectors,
            documents=[d["meta"] for d in documents],
            index_path=index_path,
            metadata_path=metadata_path,
            embedding_model="fake-model",
            technique_count=1,
            subtechnique_count=1,
        )
        store.save()
        return index_path, metadata_path

    return _make
