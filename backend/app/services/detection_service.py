import uuid
from typing import List, Optional
from app.core.logging import get_logger
from app.schemas.detection import (
    AttackContext,
    BatchDetectionRequest,
    BatchDetectionResponse,
    DetectionDetails,
    DetectionResponse,
    Explanation,
    Metadata,
    NetworkFlowRequest,
    SeverityDetails,
)
from app.services.llm_service import LLMService
from app.services.mitre_service import MitreService
from app.services.ml_service import MLService
from app.services.rag_service import RagService
from app.services.severity_service import SeverityService

logger = get_logger("detection_service")


class DetectionService:
    """Orchestration service coordinating ML inference, severity classification, and intelligence stubs."""

    def __init__(
        self,
        ml_service: MLService,
        severity_service: Optional[SeverityService] = None,
        mitre_service: Optional[MitreService] = None,
        rag_service: Optional[RagService] = None,
        llm_service: Optional[LLMService] = None,
    ):
        self.ml_service = ml_service
        self.severity_service = severity_service or SeverityService()
        self.mitre_service = mitre_service or MitreService()
        self.rag_service = rag_service or RagService()
        self.llm_service = llm_service or LLMService()

    def detect_single(
        self,
        flow_request: NetworkFlowRequest,
        correlation_id: Optional[str] = None,
    ) -> DetectionResponse:
        """Process single network flow end-to-end."""
        request_id = correlation_id or str(uuid.uuid4())
        logger.debug(f"Processing detection request {request_id}")

        flow_dict = flow_request.to_feature_dict()

        # 1. ML inference
        ml_result = self.ml_service.predict(flow_dict)

        # 2. Severity calculation
        sev_result = self.severity_service.calculate_severity(
            anomaly_score=ml_result.anomaly_score,
            threshold=ml_result.threshold,
        )

        # 3. Future service extension points
        mitre_techniques = self.mitre_service.map_techniques(
            flow=flow_dict,
            anomaly_score=ml_result.anomaly_score,
            is_anomaly=ml_result.is_anomaly,
        )
        retrieved_context = self.rag_service.retrieve_context(
            flow=flow_dict,
            anomaly_score=ml_result.anomaly_score,
        )
        llm_exp = self.llm_service.explain(
            flow=flow_dict,
            anomaly_score=ml_result.anomaly_score,
            is_anomaly=ml_result.is_anomaly,
            mitre_context=mitre_techniques,
            rag_context=retrieved_context,
        )

        logger.info(
            f"Detection completed for {request_id}: is_anomaly={ml_result.is_anomaly}, "
            f"score={ml_result.anomaly_score:.6f}, severity={sev_result.level}"
        )

        return DetectionResponse(
            request_id=request_id,
            detection=DetectionDetails(
                is_anomaly=ml_result.is_anomaly,
                anomaly_score=round(ml_result.anomaly_score, 6),
                threshold=round(ml_result.threshold, 6),
                experiment_id=ml_result.experiment_id,
                operating_point=ml_result.operating_point,
            ),
            severity=SeverityDetails(
                level=sev_result.level,
                risk_score=sev_result.risk_score,
                calibration_note=sev_result.calibration_note,
            ),
            attack_context=AttackContext(
                mitre_techniques=mitre_techniques,
                retrieved_context=retrieved_context,
            ),
            explanation=Explanation(
                summary=llm_exp.summary,
                reasoning=llm_exp.reasoning,
                recommendations=llm_exp.recommendations or [],
            ),
            metadata=Metadata(
                model_version=ml_result.model_version,
                source_dataset="CICIDS2017",
            ),
        )

    def detect_batch(
        self,
        batch_request: BatchDetectionRequest,
        correlation_id: Optional[str] = None,
    ) -> BatchDetectionResponse:
        """Process batch of network flows preserving input order."""
        batch_id = correlation_id or str(uuid.uuid4())
        flows = batch_request.flows
        logger.info(f"Processing batch detection {batch_id} with {len(flows)} flows")

        if not flows:
            return BatchDetectionResponse(
                batch_id=batch_id,
                count=0,
                results=[],
            )

        flow_dicts = [f.to_feature_dict() for f in flows]

        # Execute batch ML inference
        ml_results = self.ml_service.predict_batch(flow_dicts)

        results: List[DetectionResponse] = []
        for i, (flow_dict, ml_res) in enumerate(zip(flow_dicts, ml_results)):
            req_id = f"{batch_id}-{i}"
            sev_res = self.severity_service.calculate_severity(
                anomaly_score=ml_res.anomaly_score,
                threshold=ml_res.threshold,
            )
            mitre_techniques = self.mitre_service.map_techniques(
                flow=flow_dict,
                anomaly_score=ml_res.anomaly_score,
                is_anomaly=ml_res.is_anomaly,
            )
            retrieved_context = self.rag_service.retrieve_context(
                flow=flow_dict,
                anomaly_score=ml_res.anomaly_score,
            )
            llm_exp = self.llm_service.explain(
                flow=flow_dict,
                anomaly_score=ml_res.anomaly_score,
                is_anomaly=ml_res.is_anomaly,
                mitre_context=mitre_techniques,
                rag_context=retrieved_context,
            )

            results.append(
                DetectionResponse(
                    request_id=req_id,
                    detection=DetectionDetails(
                        is_anomaly=ml_res.is_anomaly,
                        anomaly_score=round(ml_res.anomaly_score, 6),
                        threshold=round(ml_res.threshold, 6),
                        experiment_id=ml_res.experiment_id,
                        operating_point=ml_res.operating_point,
                    ),
                    severity=SeverityDetails(
                        level=sev_res.level,
                        risk_score=sev_res.risk_score,
                        calibration_note=sev_res.calibration_note,
                    ),
                    attack_context=AttackContext(
                        mitre_techniques=mitre_techniques,
                        retrieved_context=retrieved_context,
                    ),
                    explanation=Explanation(
                        summary=llm_exp.summary,
                        reasoning=llm_exp.reasoning,
                        recommendations=llm_exp.recommendations or [],
                    ),
                    metadata=Metadata(
                        model_version=ml_res.model_version,
                        source_dataset="CICIDS2017",
                    ),
                )
            )

        return BatchDetectionResponse(
            batch_id=batch_id,
            count=len(results),
            results=results,
        )
