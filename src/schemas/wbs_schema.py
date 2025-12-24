"""
WBS Schemas - Pydantic Models for WBS API Validation

Defines Pydantic schemas for WBS (Work Breakdown Structure) diagram
requests and responses with proper validation and serialization.
"""
from typing import Literal
from pydantic import BaseModel, Field, field_validator


# Input Schemas (API requests)

class GenerateWBSRequest(BaseModel):
    """Request model for generating a WBS diagram from natural language."""
    
    prompt: str = Field(
        ..., 
        min_length=1, 
        max_length=2000,
        description="Natural language description of the work breakdown structure"
    )
    format: Literal["svg", "png"] = Field(
        default="svg",
        description="Output format for the WBS diagram"
    )
    
    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Validate prompt is not empty after stripping."""
        if not v.strip():
            raise ValueError("Prompt cannot be empty or whitespace only")
        return v.strip()


class PreviewWBSRequest(BaseModel):
    """Request model for previewing/rendering PlantUML WBS code directly."""
    
    plantuml_code: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="PlantUML WBS code to render"
    )
    format: Literal["svg", "png"] = Field(
        default="svg",
        description="Output format for the WBS diagram"
    )
    
    @field_validator("plantuml_code")
    @classmethod
    def validate_plantuml_code(cls, v: str) -> str:
        """Basic validation of PlantUML code."""
        if not v.strip():
            raise ValueError("PlantUML code cannot be empty")
        return v.strip()


# Output Schemas (API responses)

class WBSResponse(BaseModel):
    """Response model for JSON fallback with base64-encoded image."""
    
    plantuml_code: str = Field(
        ...,
        description="Generated PlantUML WBS code"
    )
    image_base64: str = Field(
        ...,
        description="Base64-encoded WBS diagram image"
    )
    format: str = Field(
        ...,
        description="Image format (svg or png)"
    )

