"""RAG (Retrieval-Augmented Generation) service over MITRE ATT&CK knowledge.

Retrieval only - no LLM, no generated narratives. All output is grounded in
the official MITRE ATT&CK STIX data that was indexed by
scripts/build_mitre_index.py.

The FAISS index is loaded lazily once and cached at module level so it is not
rebuilt or re-read on every API request. If the index is missing, RAG is
unavailable: ML anomaly detection continues to work and the RAG endpoint
returns a controlled 503 RAG_UNAVAILABLE error.
"""
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.exceptions import RagUnavailableException
from app.core.logging import get_logger
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore

logger = get_logger("rag_service")

# Shared lazy cache so every request reuses the loaded index.
_SHARED_STORES: Dict[str, VectorStore] = {}


def clear_rag_cache() -> None:
    """Drop cached vector stores (used by tests)."""
    _SHARED_STORES.clear()


@dataclass
class RetrievalResult:
    """A single grounded MITRE ATT&CK technique retrieved by RAG."""

    technique_id: str
    technique_name: str
    score: float
    description: str = ""
    tactics: List[str] = field(default_factory=list)
    detection: Optional[str] = None
    mitigations: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    platforms: List[str] = field(default_factory=list)
    type: str = "technique"


def build_query_from_flow(flow: Dict[str, Any]) -> str:
    """Convert flow characteristics into a deterministic descriptive query.

    Only the most informative features are described; the query is used to
    retrieve potentially relevant ATT&CK techniques. It never asserts that a
    technique was confirmed.
    """
    def fval(name: str, default: float = 0.0) -> float:
        try:
            return float(flow.get(name, default))
        except (TypeError, ValueError):
            return default

    dest_port = int(fval("Destination Port"))
    duration_us = int(fval("Flow Duration"))
    fwd_pkts = int(fval("Total Fwd Packets"))
    bwd_pkts = int(fval("Total Backward Packets"))
    fwd_bytes = int(fval("Total Length of Fwd Packets"))
    bwd_bytes = int(fval("Total Length of Bwd Packets"))
    fps = fval("Flow Packets/s")
    bps = fval("Flow Bytes/s")
    acks = int(fval("ACK Flag Count"))
    fins = int(fval("FIN Flag Count"))
    rst = int(fval("RST Flag Count"))
    psh = int(fval("PSH Flag Count"))
    urg = int(fval("URG Flag Count"))
    init_win_fwd = int(fval("Init_Win_bytes_forward"))

    parts = [
        "Suspicious network flow observed; investigating potential attack activity",
        f"destination port {dest_port}",
        f"flow duration {duration_us} microseconds",
    ]
    if fwd_pkts or bwd_pkts:
        parts.append(f"{fwd_pkts} forward packets and {bwd_pkts} backward packets")
    if fwd_bytes or bwd_bytes:
        parts.append(f"{fwd_bytes} forward bytes and {bwd_bytes} backward bytes")
    parts.append(f"flow rate {fps:.2f} packets/s and {bps:.2f} bytes/s")
    if acks or fins or rst or psh or urg:
        parts.append(
            f"flags: {acks} ACK, {fins} FIN, {rst} RST, {psh} PSH, {urg} URG"
        )
    if init_win_fwd > 0:
        parts.append(f"initial forward window {init_win_fwd} bytes")

    if fval("Is_Zero_Duration", -1.0) == 1.0:
        parts.append("suspicious zero-duration connection")

    return ". ".join(parts) + "."


class RagService:
    """Retrieve grounded MITRE ATT&CK context from a local FAISS index."""

    def __init__(
        self,
        enabled: Optional[bool] = None,
        index_path: Optional[Path] = None,
        metadata_path: Optional[Path] = None,
        embedder: Optional[EmbeddingService] = None,
        top_k: Optional[int] = None,
    ):
        self.enabled = settings.RAG_ENABLED if enabled is None else bool(enabled)
        self.index_path = index_path or settings.mitre_index_file
        self.metadata_path = metadata_path or settings.mitre_index_metadata_file
        self.embedder = embedder or EmbeddingService(settings.RAG_EMBEDDING_MODEL)
        self.top_k = top_k or settings.RAG_TOP_K
        self._store: Optional[VectorStore] = None
        self._load_error: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Index loading (lazy, once)
    # ------------------------------------------------------------------ #
    def _cache_key(self) -> str:
        try:
            return str(self.index_path.resolve())
        except Exception:
            return str(self.index_path)

    def _load_store(self) -> Optional[VectorStore]:
        if not self.enabled:
            return None
        key = self._cache_key()
        if key in _SHARED_STORES:
            self._store = _SHARED_STORES[key]
            return self._store

        if not self.index_path.exists():
            self._load_error = f"FAISS index not found at {self.index_path}"
            return None
        if not self.metadata_path.exists():
            self._load_error = f"Index metadata not found at {self.metadata_path}"
            return None

        try:
            store = VectorStore.load(self.index_path, self.metadata_path)
            _SHARED_STORES[key] = store
            self._store = store
            self._load_error = None
            logger.info(
                f"RAG vector store loaded: {store.index.ntotal} docs, "
                f"dim={store.dimension}"
            )
            return store
        except Exception as e:
            self._load_error = f"Failed to load RAG vector store: {str(e)}"
            logger.error(self._load_error)
            return None

    def preload(self) -> bool:
        """Attempt to load the index during startup. Never raises."""
        return self._load_store() is not None

    def is_available(self) -> bool:
        return self._load_store() is not None

    # ------------------------------------------------------------------ #
    # Public querying
    # ------------------------------------------------------------------ #
    def query(self, query: str, top_k: Optional[int] = None) -> List[RetrievalResult]:
        """Retrieve the most relevant MITRE ATT&CK techniques for a query."""
        store = self._load_store()
        if store is None:
            raise RagUnavailableException(
                self._load_error or "RAG knowledge index is unavailable"
            )
        if not query or not query.strip():
            raise ValueError("Query must be a non-empty string")

        k = self.top_k if top_k is None else max(1, int(top_k))
        query_vector = self.embedder.embed([query])[0]
        hits = store.search(query_vector, top_k=k)

        results = [
            RetrievalResult(
                technique_id=h["technique_id"],
                technique_name=h["technique_name"],
                score=h["score"],
                description=h["description"],
                tactics=h["tactics"],
                detection=h["detection"],
                mitigations=h["mitigations"],
                data_sources=h["data_sources"],
                platforms=h["platforms"],
                type=h["type"],
            )
            for h in hits
        ]
        logger.debug(
            f"RAG query returned {len(results)} results (top_k={k})"
        )
        return results

    def query_timed(
        self, query: str, top_k: Optional[int] = None
    ) -> tuple[float, List[RetrievalResult]]:
        """Run query and return (elapsed_ms, results)."""
        start = time.perf_counter()
        results = self.query(query, top_k=top_k)
        return (time.perf_counter() - start) * 1000.0, results

    # ------------------------------------------------------------------ #
    # Detection integration (backwards-compatible stub interface)
    # ------------------------------------------------------------------ #
    def retrieve_context(self, flow: Dict[str, Any], anomaly_score: float) -> List[str]:
        """Retrieve grounded context strings for an anomalous flow.

        Returns an empty list when RAG is disabled or the index is missing so
        that ML anomaly detection is never blocked by RAG availability.
        """
        _ = anomaly_score
        store = self._load_store()
        if store is None:
            logger.warning(
                "RAG retrieval skipped (disabled or index unavailable): "
                f"{self._load_error or 'not enabled'}"
            )
            return []

        try:
            query_str = build_query_from_flow(flow)
            results = self.query(query_str, top_k=self.top_k)
        except Exception as e:
            logger.warning(f"RAG retrieval failed, returning empty context: {e}")
            return []

        return [format_retrieval_result(r) for r in results]

    def retrieve_evidence(
        self, flow: Dict[str, Any], top_k: Optional[int] = None
    ) -> List[RetrievalResult]:
        """Retrieve structured RAG evidence for the LLM explanation layer.

        Never raises: returns [] when RAG is disabled or the index is missing so
        the explanation layer still works grounded on detection data alone.
        """
        store = self._load_store()
        if store is None:
            logger.warning(
                "RAG evidence retrieval skipped (disabled or index unavailable): "
                f"{self._load_error or 'not enabled'}"
            )
            return []
        try:
            query_str = build_query_from_flow(flow)
            return self.query(query_str, top_k=top_k or self.top_k)
        except Exception as e:
            logger.warning(f"RAG evidence retrieval failed, returning empty context: {e}")
            return []

    # ------------------------------------------------------------------ #
    # Status for health/API
    # ------------------------------------------------------------------ #
    def status(self) -> Dict[str, Any]:
        store = self._load_store()
        if store is None:
            return {
                "status": "unavailable",
                "detail": self._load_error
                or "RAG index not built. Run scripts/build_mitre_index.py first.",
                "index_path": str(self.index_path),
            }
        return {
            "status": "ready",
            "index_path": str(store.index_path),
            "embedding_model": store.embedding_model,
            "embedding_dim": store.dimension,
            "doc_count": len(store.documents),
            "technique_count": store.technique_count,
            "subtechnique_count": store.subtechnique_count,
        }


def format_retrieval_result(result: RetrievalResult) -> str:
    """Compact single-line rendering for detection response context lists."""
    tactics = ", ".join(result.tactics) if result.tactics else "unknown tactic"
    return (
        f"[retrieved-not-confirmed] {result.technique_id} "
        f"{result.technique_name} ({tactics}) score={result.score:.4f}"
    )