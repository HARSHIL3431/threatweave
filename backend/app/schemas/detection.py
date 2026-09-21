import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class NetworkFlowRequest(BaseModel):
    """Network flow input matching the frozen E2 60-feature schema."""
    
    destination_port: float = Field(..., alias="Destination Port")
    flow_duration: float = Field(..., alias="Flow Duration")
    total_fwd_packets: float = Field(..., alias="Total Fwd Packets")
    total_backward_packets: float = Field(..., alias="Total Backward Packets")
    total_length_of_fwd_packets: float = Field(..., alias="Total Length of Fwd Packets")
    total_length_of_bwd_packets: float = Field(..., alias="Total Length of Bwd Packets")
    fwd_packet_length_max: float = Field(..., alias="Fwd Packet Length Max")
    fwd_packet_length_min: float = Field(..., alias="Fwd Packet Length Min")
    fwd_packet_length_mean: float = Field(..., alias="Fwd Packet Length Mean")
    fwd_packet_length_std: float = Field(..., alias="Fwd Packet Length Std")
    bwd_packet_length_max: float = Field(..., alias="Bwd Packet Length Max")
    bwd_packet_length_min: float = Field(..., alias="Bwd Packet Length Min")
    bwd_packet_length_mean: float = Field(..., alias="Bwd Packet Length Mean")
    bwd_packet_length_std: float = Field(..., alias="Bwd Packet Length Std")
    flow_bytes_per_s: float = Field(..., alias="Flow Bytes/s")
    flow_packets_per_s: float = Field(..., alias="Flow Packets/s")
    flow_iat_mean: float = Field(..., alias="Flow IAT Mean")
    flow_iat_std: float = Field(..., alias="Flow IAT Std")
    flow_iat_max: float = Field(..., alias="Flow IAT Max")
    flow_iat_min: float = Field(..., alias="Flow IAT Min")
    fwd_iat_total: float = Field(..., alias="Fwd IAT Total")
    fwd_iat_mean: float = Field(..., alias="Fwd IAT Mean")
    fwd_iat_std: float = Field(..., alias="Fwd IAT Std")
    fwd_iat_max: float = Field(..., alias="Fwd IAT Max")
    fwd_iat_min: float = Field(..., alias="Fwd IAT Min")
    bwd_iat_total: float = Field(..., alias="Bwd IAT Total")
    bwd_iat_mean: float = Field(..., alias="Bwd IAT Mean")
    bwd_iat_std: float = Field(..., alias="Bwd IAT Std")
    bwd_iat_max: float = Field(..., alias="Bwd IAT Max")
    bwd_iat_min: float = Field(..., alias="Bwd IAT Min")
    fwd_psh_flags: float = Field(..., alias="Fwd PSH Flags")
    fwd_urg_flags: float = Field(..., alias="Fwd URG Flags")
    fwd_header_length: float = Field(..., alias="Fwd Header Length")
    fwd_packets_per_s: float = Field(..., alias="Fwd Packets/s")
    bwd_packets_per_s: float = Field(..., alias="Bwd Packets/s")
    min_packet_length: float = Field(..., alias="Min Packet Length")
    max_packet_length: float = Field(..., alias="Max Packet Length")
    packet_length_mean: float = Field(..., alias="Packet Length Mean")
    packet_length_std: float = Field(..., alias="Packet Length Std")
    packet_length_variance: float = Field(..., alias="Packet Length Variance")
    fin_flag_count: float = Field(..., alias="FIN Flag Count")
    rst_flag_count: float = Field(..., alias="RST Flag Count")
    psh_flag_count: float = Field(..., alias="PSH Flag Count")
    ack_flag_count: float = Field(..., alias="ACK Flag Count")
    urg_flag_count: float = Field(..., alias="URG Flag Count")
    down_per_up_ratio: float = Field(..., alias="Down/Up Ratio")
    average_packet_size: float = Field(..., alias="Average Packet Size")
    init_win_bytes_forward: float = Field(..., alias="Init_Win_bytes_forward")
    init_win_bytes_backward: float = Field(..., alias="Init_Win_bytes_backward")
    act_data_pkt_fwd: float = Field(..., alias="act_data_pkt_fwd")
    min_seg_size_forward: float = Field(..., alias="min_seg_size_forward")
    active_mean: float = Field(..., alias="Active Mean")
    active_std: float = Field(..., alias="Active Std")
    active_max: float = Field(..., alias="Active Max")
    active_min: float = Field(..., alias="Active Min")
    idle_mean: float = Field(..., alias="Idle Mean")
    idle_std: float = Field(..., alias="Idle Std")
    idle_max: float = Field(..., alias="Idle Max")
    idle_min: float = Field(..., alias="Idle Min")
    is_zero_duration: Optional[float] = Field(default=None, alias="Is_Zero_Duration")

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )

    @field_validator("*", mode="after")
    @classmethod
    def validate_finite_numbers(cls, v: Any) -> Any:
        if v is not None and isinstance(v, (int, float)):
            if math.isnan(v):
                raise ValueError("NaN is not an acceptable numeric value")
            if math.isinf(v):
                raise ValueError("Infinity is not an acceptable numeric value")
        return v

    def to_feature_dict(self) -> Dict[str, float]:
        """Convert to dict with exact feature names as aliases."""
        data = self.model_dump(by_alias=True)
        return {k: float(v) if v is not None else None for k, v in data.items()}


class DetectionDetails(BaseModel):
    is_anomaly: bool
    anomaly_score: float
    threshold: float
    experiment_id: str
    operating_point: str


class SeverityDetails(BaseModel):
    level: str = Field(..., description="'info', 'low', 'medium', 'high', or 'critical'")
    risk_score: float
    calibration_note: str = "INITIAL PLACEHOLDER CALIBRATION"


class AttackContext(BaseModel):
    mitre_techniques: List[str] = Field(default_factory=list)
    retrieved_context: List[str] = Field(default_factory=list)


class Explanation(BaseModel):
    summary: Optional[str] = None
    reasoning: Optional[str] = None
    recommendations: List[str] = Field(default_factory=list)


class Metadata(BaseModel):
    model_version: str
    source_dataset: str = "CICIDS2017"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DetectionResponse(BaseModel):
    request_id: str
    detection: DetectionDetails
    severity: SeverityDetails
    attack_context: AttackContext
    explanation: Explanation
    metadata: Metadata


class BatchDetectionRequest(BaseModel):
    flows: List[NetworkFlowRequest] = Field(default_factory=list)


class BatchDetectionResponse(BaseModel):
    batch_id: str
    count: int
    results: List[DetectionResponse]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
