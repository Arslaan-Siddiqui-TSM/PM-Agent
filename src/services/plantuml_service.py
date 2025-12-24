"""
PlantUML Service - Business Logic for PlantUML Rendering

Handles PlantUML WBS code rendering to SVG/PNG images via remote server
with validation and error handling.
"""
import zlib
from typing import Literal
import httpx

from src.core.config import settings
from src.core.exceptions import RenderError, ValidationError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PlantUMLService:
    """Service class for rendering PlantUML WBS code to images via remote server."""
    
    @staticmethod
    def validate_plantuml_syntax(code: str) -> None:
        """
        Perform basic validation on PlantUML WBS syntax.
        
        Args:
            code: PlantUML code string to validate
            
        Raises:
            ValidationError: If PlantUML code is invalid
        """
        code = code.strip()
        
        # Check minimum length
        if len(code) < 10:
            raise ValidationError("PlantUML code too short")
        
        # Check for @startwbs or @startuml tags
        if not (code.startswith("@startwbs") or code.startswith("@startuml")):
            raise ValidationError("PlantUML code must start with '@startwbs' or '@startuml'")
        
        # Check for @endwbs or @enduml tags
        if not (code.endswith("@endwbs") or code.endswith("@enduml")):
            raise ValidationError("PlantUML code must end with '@endwbs' or '@enduml'")
    
    @staticmethod
    def _encode_plantuml(plantuml_text: str) -> str:
        """
        Encode PlantUML text using PlantUML's encoding scheme.
        
        PlantUML uses deflate compression + custom base64 encoding.
        Reference: https://plantuml.com/text-encoding
        
        Args:
            plantuml_text: PlantUML source code
            
        Returns:
            Encoded string suitable for PlantUML URL
        """
        # PlantUML uses a custom base64 alphabet
        plantuml_alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_'
        
        def encode3bytes(b1, b2, b3):
            """Encode 3 bytes into 4 characters using PlantUML alphabet."""
            c1 = b1 >> 2
            c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
            c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
            c4 = b3 & 0x3F
            return (plantuml_alphabet[c1 & 0x3F] +
                    plantuml_alphabet[c2 & 0x3F] +
                    plantuml_alphabet[c3 & 0x3F] +
                    plantuml_alphabet[c4 & 0x3F])
        
        # Compress using deflate
        compressed = zlib.compress(plantuml_text.encode('utf-8'))[2:-4]  # Remove zlib header/footer
        
        # Encode compressed data
        result = []
        for i in range(0, len(compressed), 3):
            if i + 2 < len(compressed):
                result.append(encode3bytes(compressed[i], compressed[i + 1], compressed[i + 2]))
            elif i + 1 < len(compressed):
                result.append(encode3bytes(compressed[i], compressed[i + 1], 0))
            else:
                result.append(encode3bytes(compressed[i], 0, 0))
        
        return ''.join(result)
    
    @staticmethod
    async def render_wbs_to_bytes(
        plantuml_code: str,
        fmt: Literal["svg", "png"] = "svg"
    ) -> bytes:
        """
        Render PlantUML WBS code to an image using remote server.
        
        Args:
            plantuml_code: PlantUML WBS code as string
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
        
        # Validate PlantUML syntax
        PlantUMLService.validate_plantuml_syntax(plantuml_code)
        
        try:
            logger.info(f"Rendering PlantUML WBS with format={fmt}")
            
            # Encode PlantUML code
            encoded = PlantUMLService._encode_plantuml(plantuml_code)
            
            # Build URL for PlantUML server
            base_url = settings.PLANTUML_SERVER_URL.rstrip('/')
            format_path = "svg" if fmt == "svg" else "png"
            url = f"{base_url}/{format_path}/{encoded}"
            
            logger.info(f"PlantUML server URL: {url}")
            logger.info(f"Requesting PlantUML rendering from: {base_url}")
            
            # Fetch the rendered image from PlantUML server
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                output_bytes = response.content
            
            logger.info(f"Successfully rendered {len(output_bytes)} bytes")
            return output_bytes
            
        except httpx.HTTPStatusError as e:
            error_msg = f"PlantUML server returned error {e.response.status_code}: {e.response.text[:200]}"
            logger.error(error_msg)
            raise RenderError(error_msg) from e
        
        except httpx.RequestError as e:
            error_msg = f"Failed to connect to PlantUML server: {str(e)}"
            logger.error(error_msg)
            raise RenderError(error_msg) from e
        
        except Exception as e:
            error_msg = f"Failed to render PlantUML code: {str(e)}"
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

