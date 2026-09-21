import json
from pathlib import Path

import pytest
import numpy as np
from app.core.exceptions import FeatureMismatchException, ModelNotReadyException
from app.core.config import settings
from app.services.ml_service import MLService


def test_ml_service_artifact_loading(loaded_ml_service):
    """Verify artifact loads with expected metadata and structure."""
    svc = loaded_ml_service
    assert svc.is_loaded is True
    assert svc.model is not None
    assert len(svc.feature_names) == 60
    assert svc.experiment_id == "with_port"
    assert svc.model_version == "isolation_forest_v1"
    assert svc.active_threshold == pytest.approx(0.521919385, abs=1e-5)


def test_ml_service_invalid_artifact_path():
    """Verify clean exception when model file does not exist."""
    svc = MLService(model_path="non_existent_model.pkl")
    with pytest.raises(ModelNotReadyException):
        svc.load_artifacts()


def test_ml_service_feature_ordering(loaded_ml_service):
    """Verify exact 60-feature ordering matches the frozen specification."""
    svc = loaded_ml_service
    assert svc.feature_names[0] == "Destination Port"
    assert svc.feature_names[1] == "Flow Duration"
    assert svc.feature_names[-1] == "Is_Zero_Duration"


def test_zero_duration_handling(loaded_ml_service, sample_flows):
    """Verify zero-duration flows have duration clipped and rate features recomputed."""
    svc = loaded_ml_service
    zero_flow = dict(sample_flows["zero_duration_flow"]["input"])
    assert zero_flow["Flow Duration"] == 0.0

    processed_arr = svc.preprocess_flow(zero_flow)
    assert processed_arr.shape == (1, 60)
    
    # Check Is_Zero_Duration index (last column)
    is_zero_idx = svc.feature_names.index("Is_Zero_Duration")
    assert processed_arr[0, is_zero_idx] == 1.0


def test_score_calculation_and_classification(loaded_ml_service, sample_flows):
    """Verify score calculation and anomaly classification for benign and anomaly flows."""
    svc = loaded_ml_service
    
    # Benign sample
    benign_dict = sample_flows["benign_flow"]["input"]
    res_benign = svc.predict(benign_dict)
    assert res_benign.is_anomaly is False
    assert res_benign.anomaly_score < svc.active_threshold
    assert res_benign.anomaly_score == pytest.approx(sample_flows["benign_flow"]["expected_score"], abs=1e-6)

    # Anomaly sample
    anom_dict = sample_flows["anomalous_flow"]["input"]
    res_anom = svc.predict(anom_dict)
    assert res_anom.is_anomaly is True
    assert res_anom.anomaly_score >= svc.active_threshold
    assert res_anom.anomaly_score == pytest.approx(sample_flows["anomalous_flow"]["expected_score"], abs=1e-6)


def test_operating_point_selection():
    """Verify OP-A and OP-B selection sets exact validated thresholds."""
    svcA = MLService(operating_point="OP-A")
    svcA.load_artifacts()
    assert svcA.operating_point == "OP-A"
    assert svcA.active_threshold == pytest.approx(0.5219193851693676, abs=1e-8)

    svcB = MLService(operating_point="OP-B")
    svcB.load_artifacts()
    assert svcB.operating_point == "OP-B"
    assert svcB.active_threshold == pytest.approx(0.4878500998020172, abs=1e-8)


def test_missing_feature_error(loaded_ml_service):
    """Verify FeatureMismatchException when a mandatory feature is missing."""
    svc = loaded_ml_service
    incomplete_flow = {"Destination Port": 80.0}
    with pytest.raises(FeatureMismatchException):
        svc.preprocess_flow(incomplete_flow)


def test_transform_lists_and_order_are_loaded_from_authoritative_config(loaded_ml_service):
    """Verify the service uses the frozen config lists and model ordering."""
    with open(settings.resolved_preprocessing_config_path, "r") as config_file:
        config = json.load(config_file)

    assert loaded_ml_service.feature_names == config["feature_names"]
    assert loaded_ml_service.log1p_features == set(config["log1p_features"])
    assert loaded_ml_service.signed_log_features == set(config["signed_log_features"])
    assert loaded_ml_service.feature_count == 60


def test_configured_transforms_are_applied_and_unconfigured_values_are_not(sample_flows, loaded_ml_service):
    """Verify configured log transforms, signed-log behavior, and untouched fields."""
    flow = dict(sample_flows["benign_flow"]["input"])
    flow["Flow Duration"] = 10.0
    flow["Total Fwd Packets"] = 3.0
    flow["Fwd Packet Length Max"] = 7.0
    flow["Fwd Header Length"] = -4.0

    processed = loaded_ml_service.preprocess_flow(flow)[0]
    assert processed[loaded_ml_service.feature_names.index("Total Fwd Packets")] == pytest.approx(np.log1p(3.0))
    assert processed[loaded_ml_service.feature_names.index("Flow Duration")] == pytest.approx(np.log1p(10.0))
    assert processed[loaded_ml_service.feature_names.index("Fwd Header Length")] == pytest.approx(-np.log1p(4.0))
    assert processed[loaded_ml_service.feature_names.index("Fwd Packet Length Max")] == pytest.approx(7.0)


def test_zero_duration_recomputes_rates_with_zero_and_nonzero_counts(sample_flows, loaded_ml_service):
    """Verify the training pipeline's 1us convention for both rate cases."""
    zero_flow = dict(sample_flows["zero_duration_flow"]["input"])
    zero_flow["Total Fwd Packets"] = 0.0
    zero_flow["Total Backward Packets"] = 0.0
    zero_flow["Total Length of Fwd Packets"] = 0.0
    zero_flow["Total Length of Bwd Packets"] = 0.0
    processed_zero = loaded_ml_service.preprocess_flow(zero_flow)[0]
    assert np.isfinite(processed_zero).all()
    assert processed_zero[loaded_ml_service.feature_names.index("Flow Packets/s")] == 0.0
    assert processed_zero[loaded_ml_service.feature_names.index("Flow Bytes/s")] == 0.0

    nonzero_flow = dict(zero_flow)
    nonzero_flow["Total Fwd Packets"] = 2.0
    nonzero_flow["Total Backward Packets"] = 3.0
    nonzero_flow["Total Length of Fwd Packets"] = 7.0
    nonzero_flow["Total Length of Bwd Packets"] = 11.0
    processed_nonzero = loaded_ml_service.preprocess_flow(nonzero_flow)[0]
    assert processed_nonzero[loaded_ml_service.feature_names.index("Flow Packets/s")] == pytest.approx(
        np.log1p(5.0 / 1e-6)
    )
    assert processed_nonzero[loaded_ml_service.feature_names.index("Flow Bytes/s")] == pytest.approx(
        np.log1p(18.0 / 1e-6)
    )


def test_invalid_preprocessing_config_fails_feature_validation(tmp_path: Path):
    """Malformed frozen configuration must fail before the service becomes ready."""
    with open(settings.resolved_preprocessing_config_path, "r") as config_file:
        config = json.load(config_file)

    config["feature_names"] = config["feature_names"] + ["Duplicate?"]
    config_path = tmp_path / "invalid_preprocessing_config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    service = MLService(config_path=str(config_path))
    with pytest.raises(FeatureMismatchException):
        service.load_artifacts()


def test_unknown_transform_feature_fails_feature_validation(tmp_path: Path):
    """Transformation lists may not reference fields outside the model contract."""
    with open(settings.resolved_preprocessing_config_path, "r") as config_file:
        config = json.load(config_file)

    config["log1p_features"].append("Not A Frozen Feature")
    config_path = tmp_path / "invalid_transform_config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    service = MLService(config_path=str(config_path))
    with pytest.raises(FeatureMismatchException):
        service.load_artifacts()


def test_duplicate_feature_and_missing_section_fail_feature_validation(tmp_path: Path):
    """Duplicate contract entries and missing transform sections are rejected."""
    with open(settings.resolved_preprocessing_config_path, "r") as config_file:
        config = json.load(config_file)

    config["feature_names"][1] = config["feature_names"][0]
    duplicate_path = tmp_path / "duplicate_feature_config.json"
    duplicate_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(FeatureMismatchException):
        MLService(config_path=str(duplicate_path)).load_artifacts()

    with open(settings.resolved_preprocessing_config_path, "r") as config_file:
        missing_section_config = json.load(config_file)
    del missing_section_config["signed_log_features"]
    missing_section_path = tmp_path / "missing_section_config.json"
    missing_section_path.write_text(json.dumps(missing_section_config), encoding="utf-8")
    with pytest.raises(FeatureMismatchException):
        MLService(config_path=str(missing_section_path)).load_artifacts()


def test_invalid_pickle_artifact_fails_without_deserialization_leak(tmp_path: Path):
    """Unreadable model bytes are converted to the controlled readiness error."""
    model_path = tmp_path / "invalid_model.pkl"
    model_path.write_bytes(b"not a pickle")

    with pytest.raises(ModelNotReadyException) as exc_info:
        MLService(model_path=str(model_path)).load_artifacts()

    assert "not a pickle" not in str(exc_info.value)


def test_structurally_invalid_pickle_artifact_fails_cleanly(tmp_path: Path):
    """A deserializable but incomplete artifact must not become service-ready."""
    model_path = tmp_path / "incomplete_model.pkl"
    with model_path.open("wb") as model_file:
        json_artifact = {"model": object()}
        import pickle
        pickle.dump(json_artifact, model_file)

    with pytest.raises(ModelNotReadyException) as exc_info:
        MLService(model_path=str(model_path)).load_artifacts()

    assert "model" in str(exc_info.value).lower()


def test_malformed_preprocessing_configurations_fail_early(tmp_path: Path):
    """Malformed JSON, invalid list types, overlap, and missing zero flag are rejected."""
    with open(settings.resolved_preprocessing_config_path, "r") as config_file:
        base_config = json.load(config_file)

    cases = []
    cases.append(("invalid_json", b"{not-json"))

    invalid_list_config = dict(base_config)
    invalid_list_config["log1p_features"] = "not-a-list"
    cases.append(("invalid_list", json.dumps(invalid_list_config).encode()))

    overlap_config = json.loads(json.dumps(base_config))
    overlap_config["signed_log_features"].append(overlap_config["log1p_features"][0])
    cases.append(("overlap", json.dumps(overlap_config).encode()))

    missing_flag_config = json.loads(json.dumps(base_config))
    missing_flag_config["feature_names"].remove("Is_Zero_Duration")
    cases.append(("missing_zero_duration_flag", json.dumps(missing_flag_config).encode()))

    for name, contents in cases:
        config_path = tmp_path / f"{name}.json"
        config_path.write_bytes(contents)
        with pytest.raises((FeatureMismatchException, ModelNotReadyException)):
            MLService(config_path=str(config_path)).load_artifacts()
