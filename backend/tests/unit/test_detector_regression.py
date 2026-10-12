"""P1-1 tests: frozen E2 detector regression guardrails.

All tests are deterministic and offline (frozen artifacts + fixtures only).
Nothing here retrains, recalibrates, or alters the detector: failures mean
the validated behavior changed and must be investigated.
"""
from unittest.mock import Mock

import numpy as np
import pytest

from app.core.config import settings
from app.core.exceptions import FeatureMismatchException, ModelNotReadyException
from app.services.ml_service import MLService

E2_THRESHOLD_OPA = 0.5219193851693676
E2_THRESHOLD_OPB = 0.4878500998020172


# 1. Correct primary model selection.
def test_default_artifact_paths_select_e2():
    assert "with_port" in settings.MODEL_PATH
    assert "with_port" in settings.PREPROCESSING_CONFIG_PATH
    assert "baseline_no_port" not in settings.MODEL_PATH
    assert "baseline_no_port" not in settings.PREPROCESSING_CONFIG_PATH
    assert settings.resolved_model_path.parent.name == "with_port"
    assert settings.ACTIVE_OPERATING_POINT == "OP-A"


def test_loaded_service_is_e2(loaded_ml_service):
    svc = loaded_ml_service
    assert svc.experiment_id == "with_port"
    assert svc.model_version == "isolation_forest_v1"
    assert svc.feature_count == 60
    assert svc.contamination == pytest.approx(0.10)
    assert svc.operating_point == "OP-A"
    assert svc.active_threshold == pytest.approx(E2_THRESHOLD_OPA, abs=1e-12)


# 2. Expected E2 feature count and ordering (cross-artifact agreement).
def test_feature_contract_agrees_across_artifacts(loaded_ml_service):
    svc = loaded_ml_service
    assert len(svc.feature_names) == 60
    assert svc.feature_names == svc.metadata["feature_list"]
    assert svc.metadata["feature_count"] == 60
    assert svc.feature_names[0] == "Destination Port"
    assert svc.feature_names[-1] == "Is_Zero_Duration"
    assert "Destination Port" in svc.feature_names  # E2, not the E1 ablation


# 3/9. Incompatible dimensions fail loudly; E1 can never silently replace E2.
def test_e1_config_rejected_against_e2_model():
    e1_config = (
        settings.resolved_preprocessing_config_path.parent.parent
        / "baseline_no_port"
        / "preprocessing_config.json"
    )
    assert e1_config.is_file()
    with pytest.raises(FeatureMismatchException):
        MLService(config_path=str(e1_config)).load_artifacts()


def test_e1_requires_explicit_selection(loaded_ml_service):
    # The production loader hard-requires the E2 port contract, so the E1
    # ablation artifact cannot be loaded through MLService at all -- there is
    # no code path by which E1 could silently replace E2 in production.
    e1_model = (
        settings.resolved_model_path.parent.parent
        / "baseline_no_port"
        / "model.pkl"
    )
    e1_config = e1_model.parent / "preprocessing_config.json"
    assert e1_model.is_file() and e1_config.is_file()
    with pytest.raises(FeatureMismatchException) as exc_info:
        MLService(model_path=str(e1_model), config_path=str(e1_config)).load_artifacts()
    assert "Destination Port" in str(exc_info.value)


# 5/6. Score direction and inclusive threshold boundaries (both operating points).
@pytest.mark.parametrize(
    "operating_point,threshold",
    [("OP-A", E2_THRESHOLD_OPA), ("OP-B", E2_THRESHOLD_OPB)],
)
def test_threshold_boundary_is_inclusive(sample_flows, operating_point, threshold):
    svc = MLService(operating_point=operating_point)
    svc.load_artifacts()
    flow = sample_flows["benign_flow"]["input"]
    original_score_samples = svc.model.score_samples

    def decide(returned):
        svc.model.score_samples = Mock(return_value=np.array([returned]))
        try:
            return svc.predict(flow)
        finally:
            svc.model.score_samples = original_score_samples

    # score_samples returns s => anomaly_score is -s; feed exact negations.
    assert decide(-threshold).is_anomaly is True  # score == threshold
    assert decide(-(threshold + 1e-6)).is_anomaly is True
    assert decide(-(threshold - 1e-6)).is_anomaly is False


def test_score_direction_and_sides(loaded_ml_service, sample_flows):
    benign = loaded_ml_service.predict(sample_flows["benign_flow"]["input"])
    anomalous = loaded_ml_service.predict(sample_flows["anomalous_flow"]["input"])
    assert anomalous.anomaly_score > benign.anomaly_score
    assert benign.anomaly_score < loaded_ml_service.active_threshold
    assert anomalous.anomaly_score >= loaded_ml_service.active_threshold
    assert benign.is_anomaly is False
    assert anomalous.is_anomaly is True


# 7. Repeated-inference reproducibility (including batch agreement).
def test_repeated_inference_identical(loaded_ml_service, sample_flows):
    for key in ("benign_flow", "anomalous_flow", "zero_duration_flow"):
        flow = sample_flows[key]["input"]
        first = loaded_ml_service.predict(flow)
        for _ in range(3):
            again = loaded_ml_service.predict(flow)
            assert again.anomaly_score == first.anomaly_score
            assert again.is_anomaly == first.is_anomaly
    flows = [sample_flows[k]["input"] for k in ("benign_flow", "anomalous_flow")]
    batch = loaded_ml_service.predict_batch(flows)
    assert [r.anomaly_score for r in batch] == [
        loaded_ml_service.predict(f).anomaly_score for f in flows
    ]


# B. Input dict order must not affect the inference vector.
def test_shuffled_input_order_identical_vector(loaded_ml_service, sample_flows):
    flow = sample_flows["anomalous_flow"]["input"]
    shuffled = dict(reversed(list(flow.items())))
    assert list(shuffled) != list(flow)
    np.testing.assert_array_equal(
        loaded_ml_service.preprocess_flow(flow),
        loaded_ml_service.preprocess_flow(shuffled),
    )


# 8/12. Unloaded or broken models raise; never a silent benign result.
def test_unloaded_service_never_predicts(sample_flows):
    svc = MLService()
    assert svc.is_loaded is False
    with pytest.raises(ModelNotReadyException):
        svc.predict(sample_flows["benign_flow"]["input"])
    with pytest.raises(ModelNotReadyException):
        svc.predict_batch([sample_flows["benign_flow"]["input"]])


# A. Artifact provenance completeness (structural manifest, no byte hashes:
# *.pkl artifacts are environment-local and git-ignored, so hashes would be
# brittle; required metadata fields are the stable contract instead).
def test_artifact_provenance_complete(loaded_ml_service):
    meta = loaded_ml_service.metadata
    for key in (
        "experiment_id", "feature_list", "feature_count",
        "contamination", "threshold", "model_params",
    ):
        assert key in meta, f"missing artifact metadata: {key}"
    assert meta["threshold"] == pytest.approx(E2_THRESHOLD_OPA, abs=1e-12)
    assert meta["contamination"] == pytest.approx(0.10)
    assert loaded_ml_service.train_samples > 0


# 10. RAG unavailability leaves ML fields byte-identical.
def test_rag_unavailable_preserves_ml_fields(
    loaded_ml_service, sample_flows, tmp_path, fake_embedder
):
    from fastapi.testclient import TestClient

    from app.dependencies import get_detection_service
    from app.main import app
    from app.services.detection_service import DetectionService
    from app.services.llm_service import LLMService
    from app.services.mitre_service import MitreService
    from app.services.rag_service import RagService

    broken = RagService(
        enabled=True,
        index_path=tmp_path / "missing" / "index.faiss",
        metadata_path=tmp_path / "missing" / "metadata.json",
        embedder=fake_embedder,
    )
    app.dependency_overrides[get_detection_service] = lambda: DetectionService(
        ml_service=loaded_ml_service,
        mitre_service=MitreService(enabled=True, rag_service=broken),
        rag_service=broken,
        llm_service=LLMService(),
    )
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/detect",
                json=sample_flows["anomalous_flow"]["input"],
            )
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 200
    direct = loaded_ml_service.predict(sample_flows["anomalous_flow"]["input"])
    data = resp.json()
    # API rounds to 6 decimals; the underlying ML value must be identical.
    assert data["detection"]["anomaly_score"] == pytest.approx(direct.anomaly_score, abs=1e-6)
    assert data["detection"]["is_anomaly"] == direct.is_anomaly
    assert data["detection"]["threshold"] == pytest.approx(direct.threshold, abs=1e-6)
    assert data["attack_context"]["mitre_techniques"] == []
    assert data["attack_context"]["retrieved_context"] == []


# 11. Detection response compatibility.
def test_detection_response_contract(client, sample_flows):
    resp = client.post("/api/v1/detect", json=sample_flows["benign_flow"]["input"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["detection"]["experiment_id"] == "with_port"
    assert data["detection"]["operating_point"] == "OP-A"
    assert data["detection"]["threshold"] == pytest.approx(0.521919, abs=1e-5)
    assert data["metadata"]["model_version"] == "isolation_forest_v1"
    assert set(data.keys()) >= {
        "request_id", "detection", "severity",
        "attack_context", "explanation", "metadata",
    }
