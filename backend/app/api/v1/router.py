from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.detection import router as detection_router
from app.api.v1.rag import router as rag_router
from app.api.v1.explain import router as explain_router
from app.api.v1.reports import router as reports_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(detection_router)
api_router.include_router(rag_router)
api_router.include_router(explain_router)
api_router.include_router(reports_router)
