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
from typing import Any, Dict, List, Optional

import faiss
import numpy as np

from app.core.logging import get_logger

logger = get_logger("vector_store")

INDEX_FILENAME = "index.faiss"
METADATA_FILENAME = "metadata.json"

# Document types produced by the index builder (mitre_data.RagDocument).
KNOWN_DOCUMENT_TYPES = ("technique", "sub-technique")


class VectorStoreIntegrityError(ValueError):
    """Raised when a persisted index/metadata pair cannot be trusted.

    Covers unreadable files, malformed metadata, dimension mismatches,
    invalid records, duplicate identifiers, and index/metadata
    misalignment. Callers treat this as RAG-unavailable (fail closed) and
    never as a healthy index. Carries no secrets or filesystem contents
    beyond the invariant that failed.
    """


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
    # Source provenance for newly built indexes (P0-1). Older artifacts
    # lack this block and load with provenance=None (unknown).
    provenance: Optional[Dict[str, Any]] = None

    def search(
        self, query_vector: np.ndarray, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Return top-k hits with metadata and similarity score.

        FAISS row ``i`` maps positionally to ``documents[i]`` (IndexFlatIP
        carries no ID map). Positions without a valid grounded document are
        skipped so a hit can never resolve to an unrelated technique.
        """
        if self.index.ntotal == 0:
            return []
        q = np.asarray(query_vector, dtype=np.float32).reshape(1, -1)
        if q.shape[1] != self.index.d:
            raise ValueError(
                f"Query dimension {q.shape[1]} does not match index dimension {self.index.d}"
            )
        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(q, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.documents):
                continue
            doc = self.documents[int(idx)]
            if not isinstance(doc, dict) or not doc.get("technique_id"):
                continue
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
            # P0-1 provenance block; None for programmatic builds without
            # source info. Row alignment of "documents" is unchanged.
            "provenance": self.provenance,
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
        provenance: Optional[Dict[str, Any]] = None,
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
            provenance=provenance,
        )

    @classmethod
    def load(cls, index_path: Path, metadata_path: Path) -> "VectorStore":
        """Load an existing index and its aligned metadata.

        Fail-closed integrity validation: the on-disk pair is untrusted, so
        any structural defect, dimension mismatch, invalid record, duplicate
        identifier, or index/metadata misalignment raises
        ``VectorStoreIntegrityError`` (or ``FileNotFoundError`` for absent
        files) instead of returning a store that could misattribute
        techniques. A structurally valid empty pair (0 vectors, 0 documents)
        loads successfully and searches to ``[]``.
        """
        if not index_path.exists():
            raise FileNotFoundError(f"FAISS index not found: {index_path}")
        if not metadata_path.exists():
            raise FileNotFoundError(f"Index metadata not found: {metadata_path}")

        try:
            index = faiss.read_index(str(index_path))
        except FileNotFoundError:
            raise
        except Exception as e:
            raise VectorStoreIntegrityError(
                f"FAISS index unreadable or invalid ({e.__class__.__name__})"
            ) from e

        if not callable(getattr(index, "search", None)):
            raise VectorStoreIntegrityError(
                "FAISS index does not support vector search"
            )
        try:
            ntotal = int(index.ntotal)
            dim = int(index.d)
        except (TypeError, ValueError) as e:
            raise VectorStoreIntegrityError(
                "FAISS index exposes invalid vector count or dimension"
            ) from e
        if ntotal < 0 or dim <= 0:
            raise VectorStoreIntegrityError(
                "FAISS index has invalid vector count or dimension"
            )
        if not getattr(index, "is_trained", True):
            raise VectorStoreIntegrityError("FAISS index is not trained")

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise VectorStoreIntegrityError(
                f"Index metadata is not valid JSON ({e.__class__.__name__})"
            ) from e
        except OSError as e:
            raise VectorStoreIntegrityError(
                f"Index metadata unreadable ({e.__class__.__name__})"
            ) from e

        if not isinstance(meta, dict):
            raise VectorStoreIntegrityError(
                "Index metadata must be a JSON object"
            )
        documents = meta.get("documents", [])
        if not isinstance(documents, list):
            raise VectorStoreIntegrityError(
                "Index metadata 'documents' must be a list"
            )

        stored_dim = meta.get("dimension", dim)
        if type(stored_dim) is not int or stored_dim != dim:
            raise VectorStoreIntegrityError(
                "Metadata dimension does not match index dimension"
            )

        if len(documents) != ntotal:
            raise VectorStoreIntegrityError(
                f"Index/metadata misalignment: index holds {ntotal} vectors "
                f"but metadata has {len(documents)} documents"
            )

        _validate_documents(documents)

        for key in ("technique_count", "subtechnique_count"):
            count = meta.get(key, 0)
            if type(count) is not int or count < 0:
                raise VectorStoreIntegrityError(
                    f"Metadata {key!r} must be a non-negative integer"
                )
        embedding_model = meta.get("embedding_model", "unknown")
        if not isinstance(embedding_model, str) or not embedding_model.strip():
            raise VectorStoreIntegrityError(
                "Metadata 'embedding_model' must be a non-empty string"
            )

        # P0-1: older artifacts lack the provenance block; treat as unknown
        # rather than failing (backward compatible, no integrity change).
        provenance = meta.get("provenance")
        if not isinstance(provenance, dict):
            provenance = None

        return cls(
            index=index,
            documents=documents,
            dimension=dim,
            embedding_model=embedding_model,
            index_path=index_path,
            metadata_path=metadata_path,
            technique_count=meta.get("technique_count", 0),
            subtechnique_count=meta.get("subtechnique_count", 0),
            provenance=provenance,
        )


def _validate_documents(documents: List[Dict[str, Any]]) -> None:
    """Validate every metadata record needed for grounded retrieval.

    Each record must carry a non-empty ``technique_id``/``technique_name``
    and a known document ``type``; identifiers must be unique so a position
    can never be confused with another record. Records are never repaired
    or substituted here: any defect raises ``VectorStoreIntegrityError``.
    """
    seen_ids = set()
    for pos, doc in enumerate(documents):
        if not isinstance(doc, dict):
            raise VectorStoreIntegrityError(
                f"Metadata document at position {pos} is not an object"
            )
        technique_id = doc.get("technique_id")
        if not isinstance(technique_id, str) or not technique_id.strip():
            raise VectorStoreIntegrityError(
                f"Metadata document at position {pos} has no valid technique_id"
            )
        technique_name = doc.get("technique_name")
        if not isinstance(technique_name, str) or not technique_name.strip():
            raise VectorStoreIntegrityError(
                f"Metadata document at position {pos} has no valid technique_name"
            )
        if doc.get("type") not in KNOWN_DOCUMENT_TYPES:
            raise VectorStoreIntegrityError(
                f"Metadata document at position {pos} has an invalid type"
            )
        if technique_id in seen_ids:
            raise VectorStoreIntegrityError(
                f"Metadata contains duplicate technique_id {technique_id!r}"
            )
        seen_ids.add(technique_id)