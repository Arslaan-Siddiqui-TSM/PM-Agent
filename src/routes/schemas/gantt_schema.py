"""
Gantt Schemas - Pydantic Models for Gantt Chart API Validation

Defines Pydantic schemas for Gantt chart diagram requests and responses
with proper validation and serialization.
"""
from typing import Literal
from pydantic import BaseModel, Field, field_validator


# Input Schemas (API requests)

class GenerateGanttRequest(BaseModel):
    """Request model for generating a Gantt chart from natural language."""
    
    prompt: str = Field(
        ..., 
        min_length=1, 
        max_length=2000,
        description="Natural language description of the project timeline and tasks"
    )
    format: Literal["svg", "png"] = Field(
        default="svg",
        description="Output format for the Gantt chart diagram"
    )
    
    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate prompt is not empty after stripping."""
        if not v.strip():
            raise ValueError("Prompt cannot be empty or whitespace only")
        return v.strip()


class PreviewGanttRequest(BaseModel):
    """Request model for previewing/rendering Mermaid Gantt code directly."""
    
    mermaid_code: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Mermaid Gantt chart code to render"
    )
    format: Literal["svg", "png"] = Field(
        default="svg",
        description="Output format for the Gantt chart diagram"
    )
    
    @field_validator("mermaid_code")
    @classmethod
    def validate_mermaid_code(cls, v: str) -> str:
        """Basic validation of Mermaid code."""
        if not v.strip():
            raise ValueError("Mermaid code cannot be empty")
        return v.strip()


# Output Schemas (API responses)

class GanttResponse(BaseModel):
    """Response model for JSON fallback with base64-encoded image."""
    
    mermaid_code: str = Field(
        ...,
        description="Generated Mermaid Gantt chart code"
    )
    image_base64: str = Field(
        ...,
        description="Base64-encoded Gantt chart diagram image"
    )
    format: str = Field(
        ...,
        description="Image format (svg or png)"
    )
