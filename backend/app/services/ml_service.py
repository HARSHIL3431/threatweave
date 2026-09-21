import json
import math
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import numpy as np

from app.core.config import settings
from app.core.exceptions import (
    FeatureMismatchException,
    InferenceErrorException,
    ModelNotReadyException,
)
from app.core.logging import get_logger

logger = get_logger("ml_service")


@dataclass
class MLResult:
    """Internal structured ML inference output."""
    is_anomaly: bool
    anomaly_score: float
    threshold: float
    experiment_id: str
    model_version: str
    operating_point: str


class MLService:
    """Service responsible for loading frozen ML artifacts and executing inference."""

    # Authoritative operating points from validated experimentation
    KNOWN_OPERATING_POINTS = {
        "OP-A": 0.5219193851693676,
        "OP-B": 0.4878500998020172,
    }

    def __init__(
        self,
        model_path: Optional[str] = None,
        config_path: Optional[str] = None,
        operating_point: Optional[str] = None,
    ):
        self.model_path = model_path
        self.config_path = config_path
        self.operating_point = operating_point or settings.ACTIVE_OPERATING_POINT
        self.is_loaded: bool = False
        
        self.model = None
        self.params: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        self.train_samples: int = 0
        self.train_time: float = 0.0
        self.contamination: float = 0.1
        
        self.feature_names: List[str] = []
        self.log1p_features: Set[str] = set()
        self.signed_log_features: Set[str] = set()
        self.feature_count: int = 0
        
        self.model_version: str = "isolation_forest_v1"
        self.experiment_id: str = "with_port"
        self.active_threshold: float = self.KNOWN_OPERATING_POINTS.get(
            self.operating_point, 0.5219193851693676
        )

    def load_artifacts(self) -> None:
        """Load model pickle and preprocessing configuration, validating feature contract."""
        resolved_model = (
            Path(self.model_path).resolve()
            if self.model_path
            else settings.resolved_model_path
        )
        resolved_config = (
            Path(self.config_path).resolve()
            if self.config_path
            else settings.resolved_preprocessing_config_path
        )

        logger.info(f"Loading ML model artifact from: {resolved_model}")
        if not resolved_model.exists():
            msg = f"Model artifact not found at {resolved_model}"
            logger.error(msg)
            raise ModelNotReadyException(msg)

        try:
            with open(resolved_model, "rb") as f:
                artifact = pickle.load(f)
        except Exception as e:
            msg = f"Failed to deserialize model artifact: {str(e)}"
            logger.error(msg)
            raise ModelNotReadyException(msg)

        # Validate mandatory keys
        expected_keys = {"model", "params", "train_samples", "train_time", "contamination", "metadata"}
        missing_keys = expected_keys - set(artifact.keys())
        if missing_keys:
            msg = f"Model artifact is missing required keys: {missing_keys}"
            logger.error(msg)
            raise ModelNotReadyException(msg)

        self.model = artifact["model"]
        self.params = artifact["params"]
        self.train_samples = artifact["train_samples"]
        self.train_time = artifact["train_time"]
        self.contamination = artifact["contamination"]
        self.metadata = artifact.get("metadata", {})
        self.experiment_id = self.metadata.get("experiment_id", "with_port")

        logger.info(f"Loading preprocessing configuration from: {resolved_config}")
        if not resolved_config.exists():
            msg = f"Preprocessing configuration not found at {resolved_config}"
            logger.error(msg)
            raise ModelNotReadyException(msg)

        try:
            with open(resolved_config, "r") as f:
                prep_cfg = json.load(f)
        except Exception as e:
            msg = f"Failed to parse preprocessing configuration: {str(e)}"
            logger.error(msg)
            raise ModelNotReadyException(msg)

        self._validate_preprocessing_config(prep_cfg)

        # Validate threshold
        art_thresh = self.metadata.get("threshold")
        if art_thresh is not None:
            self.KNOWN_OPERATING_POINTS["OP-A"] = float(art_thresh)

        if self.operating_point not in self.KNOWN_OPERATING_POINTS:
            msg = f"Invalid operating point {self.operating_point}; valid options: {list(self.KNOWN_OPERATING_POINTS.keys())}"
            logger.error(msg)
            raise ModelNotReadyException(msg)

        self.active_threshold = self.KNOWN_OPERATING_POINTS[self.operating_point]
        self.is_loaded = True
        logger.info(
            f"MLService loaded successfully. Experiment='{self.experiment_id}', "
            f"OperatingPoint='{self.operating_point}', Threshold={self.active_threshold:.6f}"
        )

    def _validate_preprocessing_config(self, prep_cfg: Dict[str, Any]) -> None:
        """Validate the artifact-driven feature and transform contract."""
        required_sections = {"feature_names", "log1p_features", "signed_log_features"}
        missing_sections = required_sections - prep_cfg.keys()
        if missing_sections:
            raise FeatureMismatchException(
                "Preprocessing configuration is missing required sections",
                {"missing_sections": sorted(missing_sections)},
            )

        feature_names = prep_cfg["feature_names"]
        log1p_features = prep_cfg["log1p_features"]
        signed_log_features = prep_cfg["signed_log_features"]
        if not isinstance(feature_names, list) or not all(isinstance(name, str) for name in feature_names):
            raise FeatureMismatchException("preprocessing_config.feature_names must be a list of strings")
        if not isinstance(log1p_features, list) or not all(isinstance(name, str) for name in log1p_features):
            raise FeatureMismatchException("preprocessing_config.log1p_features must be a list of strings")
        if not isinstance(signed_log_features, list) or not all(isinstance(name, str) for name in signed_log_features):
            raise FeatureMismatchException("preprocessing_config.signed_log_features must be a list of strings")

        model_features = self.metadata.get("feature_list")
        metadata_count = self.metadata.get("feature_count")
        if not isinstance(metadata_count, int) or metadata_count <= 0:
            raise FeatureMismatchException("Model metadata must declare a positive integer feature_count")
        if not isinstance(model_features, list) or not model_features:
            raise FeatureMismatchException("Model metadata must declare the ordered feature_list")
        if metadata_count != len(model_features):
            raise FeatureMismatchException("Model metadata feature_count does not match feature_list length")
        if len(feature_names) != metadata_count:
            raise FeatureMismatchException(
                "Preprocessing feature count does not match model metadata",
                {"config_count": len(feature_names), "model_count": metadata_count},
            )
        if len(set(feature_names)) != len(feature_names):
            raise FeatureMismatchException("Preprocessing feature_names contains duplicate features")
        if feature_names != model_features:
            raise FeatureMismatchException(
                "Feature names/ordering mismatch between model metadata and preprocessing config"
            )

        feature_set = set(feature_names)
        unknown_log1p = sorted(set(log1p_features) - feature_set)
        unknown_signed = sorted(set(signed_log_features) - feature_set)
        if unknown_log1p or unknown_signed:
            raise FeatureMismatchException(
                "Preprocessing transform references unknown features",
                {"unknown_log1p": unknown_log1p, "unknown_signed_log": unknown_signed},
            )
        if len(set(log1p_features)) != len(log1p_features):
            raise FeatureMismatchException("preprocessing_config.log1p_features contains duplicates")
        if len(set(signed_log_features)) != len(signed_log_features):
            raise FeatureMismatchException("preprocessing_config.signed_log_features contains duplicates")
        overlap = sorted(set(log1p_features) & set(signed_log_features))
        if overlap:
            raise FeatureMismatchException(
                "A feature cannot have both log1p and signed_log transformations",
                {"overlap": overlap},
            )
        if prep_cfg.get("include_destination_port") is not True:
            raise FeatureMismatchException("E2 preprocessing configuration must include Destination Port")
        if "Is_Zero_Duration" not in feature_set:
            raise FeatureMismatchException("Preprocessing feature contract must include Is_Zero_Duration")

        self.feature_names = feature_names.copy()
        self.log1p_features = set(log1p_features)
        self.signed_log_features = set(signed_log_features)
        self.feature_count = metadata_count

    def preprocess_flow(self, raw_flow: Dict[str, Any]) -> np.ndarray:
        """Preprocess a single network flow into the model's expected 60-feature vector."""
        flow = dict(raw_flow)

        missing_features = [name for name in self.feature_names if name not in flow and name != "Is_Zero_Duration"]
        if missing_features:
            raise FeatureMismatchException(
                "Missing required raw features",
                {"missing_features": missing_features},
            )

        # Step 1: Zero-duration handling
        # Reproduce Stage 8 of preprocessing pipeline
        flow_dur = float(flow["Flow Duration"])
        is_zero_dur = 1.0 if flow_dur == 0.0 else 0.0
        
        # Clip duration to 1.0 us minimum
        clipped_dur = max(flow_dur, 1.0)
        flow["Flow Duration"] = clipped_dur
        flow["Is_Zero_Duration"] = is_zero_dur

        if is_zero_dur == 1.0:
            total_pkts = float(flow.get("Total Fwd Packets", 0.0)) + float(flow.get("Total Backward Packets", 0.0))
            total_bytes = float(flow.get("Total Length of Fwd Packets", 0.0)) + float(flow.get("Total Length of Bwd Packets", 0.0))
            dur_sec = clipped_dur * 1e-6
            flow["Flow Packets/s"] = total_pkts / dur_sec
            flow["Flow Bytes/s"] = total_bytes / dur_sec

        # Step 2: Log1p transforms
        for col in self.log1p_features:
            if col in flow:
                v = float(flow[col])
                flow[col] = float(np.log1p(v))

        # Step 3: Signed log transforms: sign(x) * log1p(|x|)
        for col in self.signed_log_features:
            if col in flow:
                v = float(flow[col])
                flow[col] = float(np.sign(v) * np.log1p(np.abs(v)))

        # Step 4: Feature ordering
        try:
            row = [float(flow[col]) for col in self.feature_names]
        except KeyError as e:
            raise FeatureMismatchException(f"Missing required feature during preprocessing: {e}")

        return np.array([row], dtype=np.float64)

    def preprocess_batch(self, raw_flows: List[Dict[str, Any]]) -> np.ndarray:
        """Preprocess a batch of flows into an (N, 60) numpy array."""
        rows = []
        for i, flow in enumerate(raw_flows):
            try:
                row_arr = self.preprocess_flow(flow)
                rows.append(row_arr[0])
            except Exception as e:
                raise InferenceErrorException(f"Failed preprocessing flow at index {i}: {str(e)}")
        
        return np.array(rows, dtype=np.float64)

    def predict(self, raw_flow: Dict[str, Any]) -> MLResult:
        """Execute inference on a single network flow."""
        if not self.is_loaded:
            raise ModelNotReadyException("Model has not been loaded")

        try:
            X = self.preprocess_flow(raw_flow)
            score = float(-self.model.score_samples(X)[0])
            is_anomaly = bool(score >= self.active_threshold)
            
            return MLResult(
                is_anomaly=is_anomaly,
                anomaly_score=score,
                threshold=self.active_threshold,
                experiment_id=self.experiment_id,
                model_version=self.model_version,
                operating_point=self.operating_point,
            )
        except (ModelNotReadyException, FeatureMismatchException):
            raise
        except Exception as e:
            logger.error(f"Inference error: {str(e)}")
            raise InferenceErrorException()

    def predict_batch(self, raw_flows: List[Dict[str, Any]]) -> List[MLResult]:
        """Execute inference on a batch of network flows."""
        if not self.is_loaded:
            raise ModelNotReadyException("Model has not been loaded")

        if not raw_flows:
            return []

        try:
            X = self.preprocess_batch(raw_flows)
            scores = -self.model.score_samples(X)
            
            results = []
            for score in scores:
                sc = float(score)
                results.append(
                    MLResult(
                        is_anomaly=bool(sc >= self.active_threshold),
                        anomaly_score=sc,
                        threshold=self.active_threshold,
                        experiment_id=self.experiment_id,
                        model_version=self.model_version,
                        operating_point=self.operating_point,
                    )
                )
            return results
        except (ModelNotReadyException, FeatureMismatchException, InferenceErrorException):
            raise
        except Exception as e:
            logger.error(f"Batch inference error: {str(e)}")
            raise InferenceErrorException()
