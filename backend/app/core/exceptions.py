from typing import Any, Dict, Optional
from fastapi import status

class AppException(Exception):
    """Base exception for all application errors."""
    
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class InvalidInputException(AppException):
    """Raised when request payload or features are invalid (NaN, Inf, bad values)."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="INVALID_INPUT",
            message=message,
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", status.HTTP_422_UNPROCESSABLE_ENTITY),
            details=details,
        )


class FeatureMismatchException(AppException):
    """Raised when input feature set does not match the expected 60-feature contract."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="FEATURE_MISMATCH",
            message=message,
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", status.HTTP_422_UNPROCESSABLE_ENTITY),
            details=details,
        )



class ModelNotReadyException(AppException):
    """Raised when the ML model or preprocessing pipeline has not loaded or failed."""
    
    def __init__(self, message: str = "Detection model is currently unavailable"):
        super().__init__(
            error_code="MODEL_NOT_READY",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={},
        )


class InferenceErrorException(AppException):
    """Raised when model inference or transformation calculation fails."""
    
    def __init__(self, message: str = "An error occurred during anomaly inference"):
        super().__init__(
            error_code="INFERENCE_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={},
        )


class InternalErrorException(AppException):
    """Raised for unexpected server errors."""
    
    def __init__(self, message: str = "An unexpected error occurred"):
        super().__init__(
            error_code="INTERNAL_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={},
        )


class RagUnavailableException(AppException):
    """Raised when the RAG knowledge index is missing or cannot be loaded.

    This is a controlled, recoverable state: ML detection keeps working and the
    RAG index can be built offline via scripts/build_mitre_index.py.
    """

    def __init__(self, message: str = "RAG knowledge index is unavailable"):
        super().__init__(
            error_code="RAG_UNAVAILABLE",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={},
        )


class LLMUnavailableException(AppException):
    """Raised when the LLM explanation layer is disabled or misconfigured.

    This is a controlled state: detection never depends on the LLM, and
    /explain responds with a structured error instead of a fabricated answer.
    """

    def __init__(self, message: str = "LLM explanation is not available"):
        super().__init__(
            error_code="LLM_UNAVAILABLE",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={},
        )


class LLMProviderErrorException(AppException):
    """Raised when the LLM provider returns an error response."""

    def __init__(self, message: str = "LLM provider returned an error", details=None):
        super().__init__(
            error_code="LLM_PROVIDER_ERROR",
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details or {},
        )


class LLMTimeoutException(AppException):
    """Raised when the LLM provider call exceeds the configured timeout."""

    def __init__(self, message: str = "LLM provider call timed out"):
        super().__init__(
            error_code="LLM_TIMEOUT",
            message=message,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details={},
        )


class LLMValidationErrorException(AppException):
    """Raised when the LLM output fails strict schema / technique grounding checks.

    The output is never silently accepted: it must be schema-valid, use only
    technique IDs supplied by RAG, and never introduce ungrounded evidence.
    """

    def __init__(self, message: str = "LLM output failed validation", details=None):
        super().__init__(
            error_code="LLM_VALIDATION_ERROR",
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details or {},
        )


class ReportGenerationException(AppException):
    """Raised when a PDF report cannot be generated or written safely."""

    def __init__(self, message: str = "Report generation failed", details=None):
        super().__init__(
            error_code="REPORT_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details or {},
        )


class ReportNotFoundException(AppException):
    """Raised when a requested generated report does not exist."""

    def __init__(self, message: str = "Report not found"):
        super().__init__(
            error_code="REPORT_NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details={},
        )
