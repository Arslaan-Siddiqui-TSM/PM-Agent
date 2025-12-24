"""
Gantt Service - Main Business Logic for Gantt Chart Generation

Orchestrates the complete Gantt chart generation workflow including:
- LLM generation of Mermaid Gantt code
- Mermaid rendering to images
"""
from typing import Tuple, Literal
from datetime import datetime, timezone

from src.services.exceptions import DiagramGenerationError
from src.services.llm_service import LLMService
from src.services.mermaid_service import MermaidService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GanttService:
    """
    Main service class orchestrating Gantt chart generation workflow.
    
    Coordinates between LLM and Mermaid rendering layers.
    """
    
    def __init__(self):
        """Initialize service."""
        self.llm_service = LLMService()
        self.mermaid_service = MermaidService()
    
    async def generate_gantt(
        self,
        prompt: str,
        format: Literal['svg', 'png'] = "svg"
    ) -> Tuple[bytes, str]:
        """
        Generate a Gantt chart from natural language prompt.
        
        Complete workflow:
        1. Call LLM to generate Mermaid Gantt code
        2. Validate and render Mermaid code to image
        3. Return rendered image and Mermaid code
        
        Args:
            prompt: Natural language description
            format: Output format (svg or png)
            
        Returns:
            Tuple of (image_bytes, mermaid_code)
            
        Raises:
            DiagramGenerationError: If generation fails
        """
        start_time = datetime.now(timezone.utc)
        
        logger.info(f"Generating Gantt chart: prompt='{prompt[:50]}...', format={format}")
        
        # Step 1: Generate Mermaid code via LLM
        try:
            mermaid_code, tokens_used, llm_latency_ms = await self.llm_service.generate_gantt_code(
                prompt=prompt,
                max_tokens=1024
            )
            
            logger.info(f"Generated Mermaid code ({len(mermaid_code)} characters)")
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise DiagramGenerationError(
                "Failed to generate Gantt chart from prompt",
                detail=str(e)
            )
 
        # Step 2: Render Mermaid code to image
        try:
            image_bytes = await self.mermaid_service.render_gantt_to_bytes(
                mermaid_code=mermaid_code,
                fmt=format
            )
            
            logger.info(f"Rendered Gantt chart ({len(image_bytes)} bytes)")
            
        except Exception as e:
            logger.error(f"Rendering failed: {e}")
            raise DiagramGenerationError(
                "Failed to render Gantt chart",
                detail=str(e)
            )
        
        # Log success
        total_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        logger.info(
            f"Successfully generated Gantt chart in {total_time_ms}ms "
            f"(LLM: {llm_latency_ms}ms, tokens: {tokens_used})"
        )
        
        return image_bytes, mermaid_code
    
    async def preview_gantt(
        self,
        mermaid_code: str,
        format: Literal['svg', 'png'] = "svg"
    ) -> bytes:
        """
        Preview/render Mermaid Gantt code without LLM.
        
        Args:
            mermaid_code: Mermaid Gantt chart code
            format: Output format
            
        Returns:
            Rendered image bytes
            
        Raises:
            DiagramGenerationError: If rendering fails
        """
        logger.info(f"Previewing Gantt chart: format={format}")
        
        try:
            image_bytes = await self.mermaid_service.render_gantt_to_bytes(
                mermaid_code=mermaid_code,
                fmt=format
            )
            
            logger.info(f"Preview rendered ({len(image_bytes)} bytes)")
            return image_bytes
            
        except Exception as e:
            logger.error(f"Preview rendering failed: {e}")
            raise DiagramGenerationError(
                "Failed to preview Gantt chart",
                detail=str(e)
            )
