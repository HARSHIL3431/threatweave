import pytest
from pydantic import ValidationError
from app.schemas.detection import NetworkFlowRequest


def test_valid_network_flow_request(sample_flows):
    """Verify standard valid network flow passes validation."""
    flow_data = sample_flows["benign_flow"]["input"]
    req = NetworkFlowRequest(**flow_data)
    assert req.destination_port == flow_data["Destination Port"]
    assert req.flow_duration == flow_data["Flow Duration"]


def test_missing_required_feature(sample_flows):
    """Verify missing required feature fails with ValidationError."""
    flow_data = dict(sample_flows["benign_flow"]["input"])
    del flow_data["Destination Port"]
    with pytest.raises(ValidationError) as exc_info:
        NetworkFlowRequest(**flow_data)
    assert "Destination Port" in str(exc_info.value)


def test_invalid_type_feature(sample_flows):
    """Verify string/non-numeric feature fails validation."""
    flow_data = dict(sample_flows["benign_flow"]["input"])
    flow_data["Flow Duration"] = "non-a-number"
    with pytest.raises(ValidationError):
        NetworkFlowRequest(**flow_data)


def test_reject_nan_value(sample_flows):
    """Verify NaN numeric values are strictly rejected."""
    flow_data = dict(sample_flows["benign_flow"]["input"])
    flow_data["Flow Duration"] = float("nan")
    with pytest.raises(ValidationError) as exc_info:
        NetworkFlowRequest(**flow_data)
    assert "NaN is not an acceptable numeric value" in str(exc_info.value)


def test_reject_infinity_value(sample_flows):
    """Verify Infinity numeric values are strictly rejected."""
    flow_data = dict(sample_flows["benign_flow"]["input"])
    flow_data["Flow Bytes/s"] = float("inf")
    with pytest.raises(ValidationError) as exc_info:
        NetworkFlowRequest(**flow_data)
    assert "Infinity is not an acceptable numeric value" in str(exc_info.value)


def test_reject_extra_fields(sample_flows):
    """Verify extra unexpected fields are rejected (extra='forbid')."""
    flow_data = dict(sample_flows["benign_flow"]["input"])
    flow_data["unexpected_injected_column"] = 123.45
    with pytest.raises(ValidationError):
        NetworkFlowRequest(**flow_data)
