"""
Diagram Controller - API Endpoints for Diagram Operations

Handles diagram generation and preview.
"""
import base64
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from src.services.diagram_service import DiagramService
from src.services.render_service import RenderService
from src.schemas.diagram_schema import (
    GenerateDiagramRequest,
    PreviewDiagramRequest,
    DiagramResponse
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/diagram", tags=["Diagrams"])


def get_diagram_service() -> DiagramService:
    """Dependency injection for diagram service."""
    return DiagramService()


@router.post("/generate", tags=["Diagrams"])
async def generate_diagram(
    request_data: GenerateDiagramRequest,
    http_request: Request
):
    """
    Generate a diagram from a natural language prompt.
    
    This endpoint:
    1. Sends the prompt to the LLM to generate Graphviz DOT code
    2. Validates the generated DOT code
    3. Renders the DOT to the requested format (SVG or PNG)
    4. Returns the image directly or as JSON (based on Accept header)
    
    Returns:
        - Image response (image/svg+xml or image/png) by default
        - JSON response with base64-encoded image if Accept: application/json
    """
    logger.info(
        f"Generate diagram request: format={request_data.format}, "
        f"layout={request_data.layout}, prompt='{request_data.prompt[:50]}...'"
    )
    
    try:
        service = get_diagram_service()
        
        # Generate diagram
        image_bytes, dot_code = await service.generate_diagram(
            prompt=request_data.prompt,
            format=request_data.format,
            layout=request_data.layout or "dot"
        )
        
        # Return response based on Accept header
        accept_header = http_request.headers.get("accept", "")
        
        if "application/json" in accept_header:
            # Return JSON with base64-encoded image
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            return DiagramResponse(
                diagram_dot=dot_code,
                image_base64=image_base64,
                format=request_data.format
            )
        else:
            # Return image directly
            mime_type = RenderService.get_format_mime_type(request_data.format)
            return Response(
                content=image_bytes,
                media_type=mime_type
            )
            
    except Exception as e:
        logger.error(f"Diagram generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate diagram: {str(e)}"
        )


@router.post("/preview", tags=["Diagrams"])
async def preview_diagram(
    request_data: PreviewDiagramRequest,
    http_request: Request
):
    """
    Preview/render a diagram from Graphviz DOT code directly (no LLM call).
    
    Useful for WYSIWYG editing or when you already have DOT code.
    
    Returns:
        - Image response (image/svg+xml or image/png) by default
        - JSON response with base64-encoded image if Accept: application/json
    """
    logger.info(f"Preview diagram request: format={request_data.format}, layout={request_data.layout}")
    
    try:
        service = get_diagram_service()
        
        # Preview diagram (no LLM, no DB save)
        image_bytes = await service.preview_diagram(
            dot_code=request_data.dot,
            format=request_data.format,
            layout=request_data.layout or "dot"
        )
        
        # Return response based on Accept header
        accept_header = http_request.headers.get("accept", "")
        
        if "application/json" in accept_header:
            # Return JSON with base64-encoded image
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            return DiagramResponse(
                diagram_dot=request_data.dot,
                image_base64=image_base64,
                format=request_data.format
            )
        else:
            # Return image directly
            mime_type = RenderService.get_format_mime_type(request_data.format)
            return Response(
                content=image_bytes,
                media_type=mime_type
            )
            
    except Exception as e:
        logger.error(f"Diagram preview failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to preview diagram: {str(e)}"
        )

