"""
Render Service - Business Logic for Graphviz Rendering

Handles Graphviz DOT code rendering to SVG/PNG images with validation
and error handling.
"""
from typing import Literal
import graphviz
from graphviz import ExecutableNotFound

from src.core.exceptions import RenderError, ValidationError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RenderService:
    """Service class for rendering Graphviz DOT code to images."""
    
    @staticmethod
    def validate_dot_syntax(dot: str) -> None:
        """
        Perform basic validation on DOT syntax.
        
        Args:
            dot: DOT code string to validate
            
        Raises:
            ValidationError: If DOT code is invalid
        """
        dot = dot.strip()
        
        # Check minimum length
        if len(dot) < 10:
            raise ValidationError("DOT code too short")
        
        # Check for graph declaration
        if not (dot.startswith("graph") or dot.startswith("digraph") or 
                dot.startswith("strict graph") or dot.startswith("strict digraph")):
            raise ValidationError("DOT code must start with 'graph' or 'digraph'")
        
        # Check for balanced braces
        if dot.count("{") != dot.count("}"):
            raise ValidationError("Unbalanced braces in DOT code")
        
        # Check that there's at least one opening and closing brace
        if "{" not in dot or "}" not in dot:
            raise ValidationError("DOT code must contain graph body in braces")
    
    @staticmethod
    async def render_to_bytes(
        dot: str,
        fmt: Literal["svg", "png"] = "svg",
        engine: str = "dot"
    ) -> bytes:
        """
        Render Graphviz DOT code to an image.
        
        Args:
            dot: Graphviz DOT code as string
            fmt: Output format - "svg" or "png"
            engine: Graphviz layout engine (dot, neato, fdp, sfdp, twopi, circo)
            
        Returns:
            Rendered image as bytes (UTF-8 encoded text for SVG, binary for PNG)
            
        Raises:
            ValidationError: If invalid format or engine specified
            RenderError: If rendering fails
        """
        # Validate format
        if fmt not in ["svg", "png"]:
            raise ValidationError(f"Invalid format: {fmt}. Must be 'svg' or 'png'")
        
        # Validate engine
        valid_engines = ["dot", "neato", "fdp", "sfdp", "twopi", "circo"]
        if engine not in valid_engines:
            raise ValidationError(
                f"Invalid engine: {engine}. Must be one of {valid_engines}"
            )
        
        # Validate DOT syntax
        RenderService.validate_dot_syntax(dot)
        
        try:
            # Create Source object from DOT code
            src = graphviz.Source(
                source=dot,
                engine=engine,
                format=fmt
            )
            
            logger.info(f"Rendering DOT with engine={engine}, format={fmt}")
            
            # Use pipe() method to get bytes directly without file I/O
            output_bytes = src.pipe(format=fmt, encoding=None)
            
            logger.info(f"Successfully rendered {len(output_bytes)} bytes")
            return output_bytes
            
        except ExecutableNotFound as e:
            error_msg = (
                "Graphviz executable not found. "
                "Please install Graphviz system package. "
                "See: https://graphviz.org/download/"
            )
            logger.error(error_msg)
            raise RenderError(error_msg) from e
        
        except Exception as e:
            error_msg = f"Failed to render DOT code: {str(e)}"
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

