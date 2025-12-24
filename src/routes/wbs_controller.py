"""
WBS Controller - API Endpoints for WBS Diagram Operations

Handles Work Breakdown Structure diagram generation and preview.
"""
import base64
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from src.services.wbs_service import WBSService
from src.services.plantuml_service import PlantUMLService
from src.schemas.wbs_schema import (
    GenerateWBSRequest,
    PreviewWBSRequest,
    WBSResponse
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/wbs", tags=["WBS"])


def get_wbs_service() -> WBSService:
    """Dependency injection for WBS service."""
    return WBSService()


@router.post("/generate", tags=["WBS"])
async def generate_wbs(
    request_data: GenerateWBSRequest,
    http_request: Request
):
    """
    Generate a WBS diagram from a natural language prompt.
    
    This endpoint:
    1. Sends the prompt to the LLM to generate PlantUML WBS code
    2. Validates the generated PlantUML code
    3. Renders the PlantUML to the requested format (SVG or PNG)
    4. Returns the image directly or as JSON (based on Accept header)
    
    Returns:
        - Image response (image/svg+xml or image/png) by default
        - JSON response with base64-encoded image if Accept: application/json
    """
    logger.info(
        f"Generate WBS request: format={request_data.format}, "
        f"prompt='{request_data.prompt[:50]}...'"
    )
    
    try:
        service = get_wbs_service()
        
        # Generate WBS diagram
        image_bytes, plantuml_code = await service.generate_wbs(
            prompt=request_data.prompt,
            format=request_data.format
        )
        
        # Return response based on Accept header
        accept_header = http_request.headers.get("accept", "")
        
        if "application/json" in accept_header:
            # Return JSON with base64-encoded image
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            return WBSResponse(
                plantuml_code=plantuml_code,
                image_base64=image_base64,
                format=request_data.format
            )
        else:
            # Return image directly
            mime_type = PlantUMLService.get_format_mime_type(request_data.format)
            return Response(
                content=image_bytes,
                media_type=mime_type
            )
            
    except Exception as e:
        logger.error(f"WBS generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate WBS diagram: {str(e)}"
        )


@router.post("/preview", tags=["WBS"])
async def preview_wbs(
    request_data: PreviewWBSRequest,
    http_request: Request
):
    """
    Preview/render a WBS diagram from PlantUML code directly (no LLM call).
    
    Useful for WYSIWYG editing or when you already have PlantUML code.
    
    Returns:
        - Image response (image/svg+xml or image/png) by default
        - JSON response with base64-encoded image if Accept: application/json
    """
    logger.info(f"Preview WBS request: format={request_data.format}")
    
    try:
        service = get_wbs_service()
        
        # Preview WBS diagram (no LLM, no DB save)
        image_bytes = await service.preview_wbs(
            plantuml_code=request_data.plantuml_code,
            format=request_data.format
        )
        
        # Return response based on Accept header
        accept_header = http_request.headers.get("accept", "")
        
        if "application/json" in accept_header:
            # Return JSON with base64-encoded image
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            return WBSResponse(
                plantuml_code=request_data.plantuml_code,
                image_base64=image_base64,
                format=request_data.format
            )
        else:
            # Return image directly
            mime_type = PlantUMLService.get_format_mime_type(request_data.format)
            return Response(
                content=image_bytes,
                media_type=mime_type
            )
            
    except Exception as e:
        logger.error(f"WBS preview failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to preview WBS diagram: {str(e)}"
        )

