from fastapi import APIRouter, Depends, Header
from typing import Optional
from app.dependencies import get_detection_service
from app.schemas.detection import (
    BatchDetectionRequest,
    BatchDetectionResponse,
    DetectionResponse,
    NetworkFlowRequest,
)
from app.services.detection_service import DetectionService

router = APIRouter(tags=["Detection"])


@router.post(
    "/detect",
    response_model=DetectionResponse,
    summary="Analyze a single network flow for anomalies",
    description="Scores a single 60-feature network flow using the frozen E2 Isolation Forest detector."
)
def detect_single_flow(
    flow: NetworkFlowRequest,
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-ID"),
    detection_service: DetectionService = Depends(get_detection_service),
) -> DetectionResponse:
    """Analyze single network flow and return anomaly detection with risk severity."""
    return detection_service.detect_single(flow, correlation_id=x_correlation_id)


@router.post(
    "/detect/batch",
    response_model=BatchDetectionResponse,
    summary="Analyze a batch of network flows for anomalies",
    description="Scores a batch of network flows in order. An empty batch returns an empty result set."
)
def detect_batch_flows(
    batch: BatchDetectionRequest,
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-ID"),
    detection_service: DetectionService = Depends(get_detection_service),
) -> BatchDetectionResponse:
    """Analyze batch of network flows preserving input ordering."""
    return detection_service.detect_batch(batch, correlation_id=x_correlation_id)
