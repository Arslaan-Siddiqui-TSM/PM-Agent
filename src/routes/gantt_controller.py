"""
Gantt Controller - API Endpoints for Gantt Chart Operations

Handles Gantt chart diagram generation and preview.
"""
import base64
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from src.services.gantt_service import GanttService
from src.services.mermaid_service import MermaidService
from src.schemas.gantt_schema import (
    GenerateGanttRequest,
    PreviewGanttRequest,
    GanttResponse
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/gantt", tags=["Gantt"])


def get_gantt_service() -> GanttService:
    """Dependency injection for Gantt service."""
    return GanttService()


@router.post("/generate", tags=["Gantt"])
async def generate_gantt(
    request_data: GenerateGanttRequest,
    http_request: Request
):
    """
    Generate a Gantt chart from a natural language prompt.
    
    This endpoint:
    1. Sends the prompt to the LLM to generate Mermaid Gantt code
    2. Validates the generated Mermaid code
    3. Renders the Mermaid code to the requested format (SVG or PNG)
    4. Returns the image directly or as JSON (based on Accept header)
    
    Returns:
        - Image response (image/svg+xml or image/png) by default
        - JSON response with base64-encoded image if Accept: application/json
    """
    logger.info(
        f"Generate Gantt request: format={request_data.format}, "
        f"prompt='{request_data.prompt[:50]}...'"
    )
    
    try:
        service = get_gantt_service()
        
        # Generate Gantt chart
        image_bytes, mermaid_code = await service.generate_gantt(
            prompt=request_data.prompt,
            format=request_data.format
        )
        
        # Return response based on Accept header
        accept_header = http_request.headers.get("accept", "")
        
        if "application/json" in accept_header:
            # Return JSON with base64-encoded image
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            return GanttResponse(
                mermaid_code=mermaid_code,
                image_base64=image_base64,
                format=request_data.format
            )
        else:
            # Return image directly
            mime_type = MermaidService.get_format_mime_type(request_data.format)
            return Response(
                content=image_bytes,
                media_type=mime_type
            )
            
    except Exception as e:
        logger.error(f"Gantt generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Gantt chart: {str(e)}"
        )


@router.post("/preview", tags=["Gantt"])
async def preview_gantt(
    request_data: PreviewGanttRequest,
    http_request: Request
):
    """
    Preview/render a Gantt chart from Mermaid code directly (no LLM call).
    
    Useful for WYSIWYG editing or when you already have Mermaid code.
    
    Returns:
        - Image response (image/svg+xml or image/png) by default
        - JSON response with base64-encoded image if Accept: application/json
    """
    logger.info(f"Preview Gantt request: format={request_data.format}")
    
    try:
        service = get_gantt_service()
        
        # Preview Gantt chart (no LLM, no DB save)
        image_bytes = await service.preview_gantt(
            mermaid_code=request_data.mermaid_code,
            format=request_data.format
        )
        
        # Return response based on Accept header
        accept_header = http_request.headers.get("accept", "")
        
        if "application/json" in accept_header:
            # Return JSON with base64-encoded image
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            return GanttResponse(
                mermaid_code=request_data.mermaid_code,
                image_base64=image_base64,
                format=request_data.format
            )
        else:
            # Return image directly
            mime_type = MermaidService.get_format_mime_type(request_data.format)
            return Response(
                content=image_bytes,
                media_type=mime_type
            )
            
    except Exception as e:
        logger.error(f"Gantt preview failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to preview Gantt chart: {str(e)}"
        )
