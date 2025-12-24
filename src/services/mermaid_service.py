"""
Mermaid Service - Business Logic for Mermaid Gantt Chart Rendering

Handles Mermaid Gantt chart rendering to SVG/PNG images using mermaid.ink API
with validation and error handling.
"""
import base64
from typing import Literal
import httpx

from src.core.exceptions import RenderError, ValidationError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MermaidService:
    """Service class for rendering Mermaid Gantt charts to images via mermaid.ink API."""
    
    # Mermaid.ink API base URLs
    MERMAID_INK_SVG_URL = "https://mermaid.ink/svg/"
    MERMAID_INK_PNG_URL = "https://mermaid.ink/img/"
    
    @staticmethod
    def validate_mermaid_gantt_syntax(mermaid_code: str) -> None:
        """
        Perform basic validation on Mermaid Gantt syntax.
        
        Args:
            mermaid_code: Mermaid code string to validate
            
        Raises:
            ValidationError: If Mermaid code is invalid
        """
        mermaid_code = mermaid_code.strip()
        
        # Check minimum length
        if len(mermaid_code) < 10:
            raise ValidationError("Mermaid code too short")
        
        # Check for gantt declaration
        if "gantt" not in mermaid_code.lower():
            raise ValidationError("Mermaid code must contain 'gantt' declaration")
    
    @staticmethod
    async def render_gantt_to_bytes(
        mermaid_code: str,
        fmt: Literal["svg", "png"] = "svg"
    ) -> bytes:
        """
        Render Mermaid Gantt chart code to an image using mermaid.ink API.
        
        Args:
            mermaid_code: Mermaid Gantt chart code as string
            fmt: Output format - "svg" or "png"
            
        Returns:
            Rendered image as bytes
            
        Raises:
            ValidationError: If invalid format specified
            RenderError: If rendering fails
        """
        # Validate format
        if fmt not in ["svg", "png"]:
            raise ValidationError(f"Invalid format: {fmt}. Must be 'svg' or 'png'")
        
        # Validate Mermaid syntax
        MermaidService.validate_mermaid_gantt_syntax(mermaid_code)
        
        try:
            logger.info(f"Rendering Mermaid Gantt chart with format={fmt}")
            
            # Encode mermaid text to URL-safe base64 as mermaid.ink expects
            mermaid_bytes = mermaid_code.encode("utf-8")
            base64_encoded = base64.urlsafe_b64encode(mermaid_bytes).decode("ascii")
            
            # Choose the appropriate URL based on format
            base_url = MermaidService.MERMAID_INK_SVG_URL if fmt == "svg" else MermaidService.MERMAID_INK_PNG_URL
            url = base_url + base64_encoded
            
            logger.info(f"Fetching image from mermaid.ink: {url[:100]}...")
            
            # Make async HTTP request to mermaid.ink
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                output_bytes = response.content
            
            logger.info(f"Successfully rendered {len(output_bytes)} bytes")
            return output_bytes
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Mermaid.ink API error (HTTP {e.response.status_code}): {str(e)}"
            logger.error(error_msg)
            raise RenderError(error_msg) from e
        
        except httpx.TimeoutException as e:
            error_msg = "Timeout while connecting to mermaid.ink API"
            logger.error(error_msg)
            raise RenderError(error_msg) from e
        
        except httpx.RequestError as e:
            error_msg = f"Failed to connect to mermaid.ink API: {str(e)}"
            logger.error(error_msg)
            raise RenderError(error_msg) from e
        
        except Exception as e:
            error_msg = f"Failed to render Mermaid Gantt chart: {str(e)}"
            logger.error(error_msg)
            raise RenderError(error_msg) from e
    
    @staticmethod
    def get_format_mime_type(fmt: str) -> str:
        """
        Get the appropriate MIME type for a given format.
        
        Args:
            fmt: Format string ("svg" or "png")
            
        Returns:
            MIME type string
        """
        mime_types = {
            "svg": "image/svg+xml",
            "png": "image/png"
        }
        return mime_types.get(fmt, "application/octet-stream")
