"""
Diagram Service - Main Business Logic for Diagram Generation

Orchestrates the complete diagram generation workflow including:
- LLM generation
- Graphviz rendering
"""
from typing import Tuple, Literal
from datetime import datetime, timezone

from src.services.exceptions import DiagramGenerationError
from src.services.llm_service import LLMService
from src.services.render_service import RenderService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DiagramService:
    """
    Main service class orchestrating diagram generation workflow.
    
    Coordinates between LLM and rendering layers.
    """
    
    def __init__(self):
        """Initialize service."""
        self.llm_service = LLMService()
        self.render_service = RenderService()
    
    async def generate_diagram(
        self,
        prompt: str,
        format: Literal["svg", "png"] = "svg",
        layout: str = "dot"
    ) -> Tuple[bytes, str]:
        """
        Generate a diagram from natural language prompt.
        
        Complete workflow:
        1. Call LLM to generate DOT code
        2. Validate and render DOT code to image
        3. Return rendered image and DOT code
        
        Args:
            prompt: Natural language description
            format: Output format (svg or png)
            layout: Graphviz layout engine
            
        Returns:
            Tuple of (image_bytes, dot_code)
            
        Raises:
            DiagramGenerationError: If generation fails
        """
        start_time = datetime.now(timezone.utc)
        
        logger.info(f"Generating diagram: prompt='{prompt[:50]}...', format={format}, layout={layout}")
        
        # Step 1: Generate DOT code via LLM
        try:
            dot_code, tokens_used, llm_latency_ms = await self.llm_service.generate_dot_code(
                prompt=prompt,
                max_tokens=1024
            )
            
            logger.info(f"Generated DOT code ({len(dot_code)} characters)")
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise DiagramGenerationError(
                "Failed to generate diagram from prompt",
                detail=str(e)
            )
 
        # Step 2: Render DOT code to image
        try:
            image_bytes = await self.render_service.render_to_bytes(
                dot=dot_code,
                fmt=format,
                engine=layout
            )
            
            logger.info(f"Rendered diagram ({len(image_bytes)} bytes)")
            
        except Exception as e:
            logger.error(f"Rendering failed: {e}")
            raise DiagramGenerationError(
                "Failed to render diagram",
                detail=str(e)
            )
        
        # Log success
        total_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        logger.info(
            f"Successfully generated diagram in {total_time_ms}ms "
            f"(LLM: {llm_latency_ms}ms, tokens: {tokens_used})"
        )
        
        return image_bytes, dot_code
    
    async def preview_diagram(
        self,
        dot_code: str,
        format: Literal["svg", "png"] = "svg",
        layout: str = "dot"
    ) -> bytes:
        """
        Preview/render DOT code without LLM.
        
        Args:
            dot_code: Graphviz DOT code
            format: Output format
            layout: Layout engine
            
        Returns:
            Rendered image bytes
            
        Raises:
            DiagramGenerationError: If rendering fails
        """
        logger.info(f"Previewing diagram: format={format}, layout={layout}")
        
        try:
            image_bytes = await self.render_service.render_to_bytes(
                dot=dot_code,
                fmt=format,
                engine=layout
            )
            
            logger.info(f"Preview rendered ({len(image_bytes)} bytes)")
            return image_bytes
            
        except Exception as e:
            logger.error(f"Preview rendering failed: {e}")
            raise DiagramGenerationError(
                "Failed to preview diagram",
                detail=str(e)
            )

