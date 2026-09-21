"""MITRE ATT&CK mapping (safe, retrieval-based).

The frozen ML model only produces an anomaly flag + score; it has no
behavioral semantics sufficient to CONFIRM a specific ATT&CK technique.
Therefore this service never claims a technique was detected. Instead, for
anomalous flows it builds a descriptive query from flow characteristics and
retrieves potentially *relevant* techniques from the grounded MITRE knowledge
base. Every technique returned is labeled retrieved-not-confirmed.
"""
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ml_service import MLService
from app.services.rag_service import RagService, build_query_from_flow

logger = get_logger("mitre_service")


class MitreService:
    """Map anomalous flows to potentially relevant MITRE ATT&CK techniques."""

    def __init__(
        self,
        enabled: Optional[bool] = None,
        rag_service: Optional[RagService] = None,
        anomaly_threshold: Optional[float] = None,
        top_k: int = 5,
    ):
        self.enabled = settings.MITRE_ENABLED if enabled is None else bool(enabled)
        self.rag_service = rag_service or RagService(enabled=self.enabled)
        self.anomaly_threshold = anomaly_threshold or MLService.KNOWN_OPERATING_POINTS["OP-A"]
        self.top_k = top_k

    def map_techniques(
        self,
        flow: Dict[str, Any],
        anomaly_score: float,
        is_anomaly: Optional[bool] = None,
    ) -> List[str]:
        """Retrieve potentially relevant technique IDs for an anomalous flow.

        Returns an empty list when disabled, when the flow is not anomalous,
        or when the RAG knowledge base is unavailable. Technique IDs are only
        ever taken from the grounded index - never invented.
        """
        if not self.enabled:
            return []

        flagged = (
            anomaly_score >= self.anomaly_threshold
            if is_anomaly is None
            else bool(is_anomaly)
        )
        if not flagged:
            return []

        try:
            query_str = build_query_from_flow(flow)
            results = self.rag_service.query(query_str, top_k=self.top_k)
        except Exception as e:
            logger.warning(f"MITRE mapping skipped (RAG unavailable): {e}")
            return []

        return [r.technique_id for r in results]