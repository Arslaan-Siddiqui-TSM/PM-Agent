"""
Common Schemas - Shared Pydantic Models

Contains common schemas used across the application including
health checks and error responses.
"""
from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    
    status: str = Field(
        default="ok",
        description="Overall health status"
    )
    version: str = Field(
        default="1.0.0",
        description="Application version"
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(
        ...,
        description="Error type or message"
    )
    detail: Optional[str] = Field(
        None,
        description="Additional error details"
    )
    request_id: Optional[str] = Field(
        None,
        description="Request ID for tracking"
    )

