"""FAISS vector store for MITRE ATT&CK RAG retrieval.

Index lifecycle:
- create: build IndexFlatIP from normalized embeddings + documents
- persist: write index.faiss + metadata.json
- load: read both back (lazy, cached in RagService)
The index is loaded once and reused, never rebuilt per request.
"""
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import faiss
import numpy as np

from app.core.logging import get_logger

logger = get_logger("vector_store")

INDEX_FILENAME = "index.faiss"
METADATA_FILENAME = "metadata.json"


@dataclass
class VectorStore:
    """In-memory vector index plus aligned document metadata."""

    index: faiss.Index
    documents: List[Dict[str, Any]]
    dimension: int
    embedding_model: str
    index_path: Path
    metadata_path: Path
    technique_count: int = 0
    subtechnique_count: int = 0

    def search(
        self, query_vector: np.ndarray, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Return top-k hits with metadata and similarity score."""
        if self.index.ntotal == 0:
            return []
        q = np.asarray(query_vector, dtype=np.float32).reshape(1, -1)
        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(q, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.documents):
                continue
            doc = self.documents[int(idx)]
            results.append(
                {
                    "technique_id": doc.get("technique_id"),
                    "technique_name": doc.get("technique_name"),
                    "type": doc.get("type"),
                    "score": round(float(score), 6),
                    "description": doc.get("description", ""),
                    "tactics": doc.get("tactics", []),
                    "detection": doc.get("detection"),
                    "mitigations": doc.get("mitigations", []),
                    "data_sources": doc.get("data_sources", []),
                    "platforms": doc.get("platforms", []),
                }
            )
        results.sort(key=lambda r: r["score"], reverse=True)
        return results

    def save(self) -> None:
        """Persist index + metadata to disk (atomic via temp files)."""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

        tmp_index = self.index_path.with_suffix(".faiss.tmp")
        tmp_meta = self.metadata_path.with_suffix(".json.tmp")

        faiss.write_index(self.index, str(tmp_index))
        payload = {
            "embedding_model": self.embedding_model,
            "dimension": self.dimension,
            "doc_count": len(self.documents),
            "technique_count": self.technique_count,
            "subtechnique_count": self.subtechnique_count,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "documents": self.documents,
        }
        with open(tmp_meta, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        os.replace(tmp_index, self.index_path)
        os.replace(tmp_meta, self.metadata_path)
        logger.info(
            f"Vector store saved: {len(self.documents)} docs, "
            f"dim={self.dimension} -> {self.index_path}"
        )

    @classmethod
    def create(
        cls,
        vectors: np.ndarray,
        documents: List[Dict[str, Any]],
        *,
        index_path: Path,
        metadata_path: Path,
        embedding_model: str,
        technique_count: int = 0,
        subtechnique_count: int = 0,
    ) -> "VectorStore":
        """Build an index from already-normalized embeddings."""
        array = np.asarray(vectors, dtype=np.float32)
        if len(array) != len(documents):
            raise ValueError(
                f"Vector count ({len(array)}) must match document count ({len(documents)})"
            )
        dimension = array.shape[1] if array.ndim == 2 else 0
        if dimension == 0:
            raise ValueError("Cannot build vector store with zero vectors")

        index = faiss.IndexFlatIP(dimension)
        if len(array) > 0:
            index.add(array)

        return cls(
            index=index,
            documents=documents,
            dimension=dimension,
            embedding_model=embedding_model,
            index_path=index_path,
            metadata_path=metadata_path,
            technique_count=technique_count,
            subtechnique_count=subtechnique_count,
        )

    @classmethod
    def load(cls, index_path: Path, metadata_path: Path) -> "VectorStore":
        """Load an existing index and its aligned metadata."""
        if not index_path.exists():
            raise FileNotFoundError(f"FAISS index not found: {index_path}")
        if not metadata_path.exists():
            raise FileNotFoundError(f"Index metadata not found: {metadata_path}")

        index = faiss.read_index(str(index_path))
        with open(metadata_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        documents = meta.get("documents", [])
        if len(documents) != index.ntotal:
            logger.warning(
                f"Metadata doc_count ({len(documents)}) differs from index rows ({index.ntotal})"
            )

        return cls(
            index=index,
            documents=documents,
            dimension=meta.get("dimension", index.d),
            embedding_model=meta.get("embedding_model", "unknown"),
            index_path=index_path,
            metadata_path=metadata_path,
            technique_count=meta.get("technique_count", 0),
            subtechnique_count=meta.get("subtechnique_count", 0),
        )