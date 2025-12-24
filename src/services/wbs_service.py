"""
WBS Service - Main Business Logic for WBS Diagram Generation

Orchestrates the complete WBS diagram generation workflow including:
- LLM generation of PlantUML code
- PlantUML rendering to images
"""
from typing import Tuple, Literal
from datetime import datetime, timezone

from src.core.config import settings
from src.core.exceptions import DiagramGenerationError
from src.services.llm_service import LLMService
from src.services.plantuml_service import PlantUMLService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class WBSService:
    """
    Main service class orchestrating WBS diagram generation workflow.
    
    Coordinates between LLM and PlantUML rendering layers.
    """
    
    def __init__(self):
        """Initialize service."""
        self.llm_service = LLMService()
        self.plantuml_service = PlantUMLService()
    
    async def generate_wbs(
        self,
        prompt: str,
        format: Literal['svg', 'png'] = "svg"
    ) -> Tuple[bytes, str]:
        """
        Generate a WBS diagram from natural language prompt.
        
        Complete workflow:
        1. Call LLM to generate PlantUML WBS code
        2. Validate and render PlantUML code to image
        3. Return rendered image and PlantUML code
        
        Args:
            prompt: Natural language description
            format: Output format (svg or png)
            
        Returns:
            Tuple of (image_bytes, plantuml_code)
            
        Raises:
            DiagramGenerationError: If generation fails
        """
        start_time = datetime.now(timezone.utc)
        
        logger.info(f"Generating WBS: prompt='{prompt[:50]}...', format={format}")
        
        # Step 1: Generate PlantUML code via LLM
        try:
            plantuml_code, tokens_used, llm_latency_ms = await self.llm_service.generate_wbs_code(
                prompt=prompt,
                max_tokens=settings.MAX_TOKENS
            )
            
            logger.info(f"Generated PlantUML code ({len(plantuml_code)} characters)")
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise DiagramGenerationError(
                "Failed to generate WBS from prompt",
                detail=str(e)
            )
        
        # Step 2: Render PlantUML code to image
        try:
            image_bytes = await self.plantuml_service.render_wbs_to_bytes(
                plantuml_code=plantuml_code,
                fmt=format
            )
            
            logger.info(f"Rendered WBS diagram ({len(image_bytes)} bytes)")
            
        except Exception as e:
            logger.error(f"Rendering failed: {e}")
            raise DiagramGenerationError(
                "Failed to render WBS diagram",
                detail=str(e)
            )
        
        # Log success
        total_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        logger.info(
            f"Successfully generated WBS in {total_time_ms}ms "
            f"(LLM: {llm_latency_ms}ms, tokens: {tokens_used})"
        )
        
        return image_bytes, plantuml_code
    
    async def preview_wbs(
        self,
        plantuml_code: str,
        format: Literal['svg', 'png'] = "svg"
    ) -> bytes:
        """
        Preview/render PlantUML WBS code without LLM.
        
        Args:
            plantuml_code: PlantUML WBS code
            format: Output format
            
        Returns:
            Rendered image bytes
            
        Raises:
            DiagramGenerationError: If rendering fails
        """
        logger.info(f"Previewing WBS: format={format}")
        
        try:
            image_bytes = await self.plantuml_service.render_wbs_to_bytes(
                plantuml_code=plantuml_code,
                fmt=format
            )
            
            logger.info(f"Preview rendered ({len(image_bytes)} bytes)")
            return image_bytes
            
        except Exception as e:
            logger.error(f"Preview rendering failed: {e}")
            raise DiagramGenerationError(
                "Failed to preview WBS diagram",
                detail=str(e)
            )

