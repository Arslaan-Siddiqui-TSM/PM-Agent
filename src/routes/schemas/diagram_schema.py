"""
Diagram Schemas - Pydantic Models for Diagram API Validation

Defines Pydantic schemas for diagram-related API requests
and responses with proper validation and serialization.
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


# Input Schemas (API requests)

class GenerateDiagramRequest(BaseModel):
    """Request model for generating a diagram from natural language."""
    
    prompt: str = Field(
        ..., 
        min_length=1, 
        max_length=2000,
        description="Natural language description of the diagram to generate"
    )
    format: Literal["svg", "png"] = Field(
        default="svg",
        description="Output format for the diagram"
    )
    layout: Optional[Literal["dot", "neato", "fdp", "sfdp", "twopi", "circo"]] = Field(
        default="dot",
        description="Graphviz layout engine to use"
    )
    
    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate prompt is not empty after stripping."""
        if not v.strip():
            raise ValueError("Prompt cannot be empty or whitespace only")
        return v.strip()


class PreviewDiagramRequest(BaseModel):
    """Request model for previewing/rendering DOT code directly."""
    
    dot: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Graphviz DOT code to render"
    )
    format: Literal["svg", "png"] = Field(
        default="svg",
        description="Output format for the diagram"
    )
    layout: Optional[Literal["dot", "neato", "fdp", "sfdp", "twopi", "circo"]] = Field(
        default="dot",
        description="Graphviz layout engine to use"
    )
    
    @field_validator("dot")
    @classmethod
    def validate_dot(cls, v: str) -> str:
        """Basic validation of DOT code."""
        if not v.strip():
            raise ValueError("DOT code cannot be empty")
        return v.strip()


# Output Schemas (API responses)

class DiagramResponse(BaseModel):
    """Response model for JSON fallback with base64-encoded image."""
    
    diagram_dot: str = Field(
        ...,
        description="Generated Graphviz DOT code"
    )
    image_base64: str = Field(
        ...,
        description="Base64-encoded diagram image"
    )
    format: str = Field(
        ...,
        description="Image format (svg or png)"
    )

