"""
Health Controller - API Endpoints for Health Checks

Provides health check and status endpoints for monitoring.
"""
from fastapi import APIRouter
from src.schemas.common_schema import HealthResponse
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns basic application health status.
    """
    return HealthResponse(
        status="ok",
        version="1.0.0"
    )

