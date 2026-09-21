from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger, setup_logging
from app.dependencies import set_global_ml_service
from app.schemas.common import ErrorResponse
from app.services.ml_service import MLService
from app.services.rag_service import RagService

# Initialize structured logging
setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan context: initialize singleton services on startup."""
    logger.info("Initializing Log Anomaly Detection Backend...")
    ml_service = MLService()
    try:
        ml_service.load_artifacts()
        logger.info("MLService artifacts loaded successfully during lifespan startup.")
    except Exception as e:
        logger.error(f"Failed to load ML artifacts on startup: {str(e)}")
        # Allow app to start so health endpoint can accurately report degraded status

    set_global_ml_service(ml_service)

    # RAG initialization is BEST-EFFORT and never blocks the app:
    # if the MITRE index is missing, log a clear warning and keep going.
    rag_service = RagService(enabled=True)
    if rag_service.preload():
        logger.info("RAG vector store preloaded successfully (MITRE ATT&CK).")
    else:
        logger.warning(
            "RAG vector store is unavailable at startup. "
            "Run scripts/build_mitre_index.py to build the MITRE ATT&CK index. "
            "ML anomaly detection remains fully functional."
        )

    yield
    logger.info("Shutting down Log Anomaly Detection Backend.")


app = FastAPI(
    title="AI-Powered Log Anomaly Detection & Incident Intelligence Platform",
    description=(
        "Production-quality backend for cyber-attack log anomaly detection and incident intelligence. "
        "Serves the frozen E2 Isolation Forest detector (CICIDS2017, 60 features) with configurable operating points."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS if isinstance(settings.ALLOWED_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle custom application domain exceptions."""
    logger.warning(f"AppException [{exc.error_code}]: {exc.message}")
    error_payload = ErrorResponse(
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
        timestamp=datetime.now(timezone.utc).isoformat(),
        request_id=request.headers.get("X-Correlation-ID"),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload.model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic schema validation errors, ensuring clean structured responses."""
    logger.info(f"Validation error: {exc.errors()}")
    cleaned_errors = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        cleaned_errors.append({
            "field": loc,
            "message": err.get("msg", "Invalid value"),
            "type": err.get("type", "value_error"),
        })

    error_payload = ErrorResponse(
        error_code="INVALID_INPUT",
        message="Request validation failed. Verify input features and numeric constraints.",
        details={"validation_errors": cleaned_errors},
        timestamp=datetime.now(timezone.utc).isoformat(),
        request_id=request.headers.get("X-Correlation-ID"),
    )
    return JSONResponse(
        status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", status.HTTP_422_UNPROCESSABLE_ENTITY),
        content=error_payload.model_dump(),
    )



@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled server exceptions, preventing path/secret leakage."""
    logger.error(f"Unhandled exception on {request.method} {request.url}: {str(exc)}", exc_info=True)
    error_payload = ErrorResponse(
        error_code="INTERNAL_ERROR",
        message="An unexpected internal server error occurred.",
        details={},
        timestamp=datetime.now(timezone.utc).isoformat(),
        request_id=request.headers.get("X-Correlation-ID"),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload.model_dump(),
    )


# Mount API v1 router
app.include_router(api_router, prefix="/api/v1")
