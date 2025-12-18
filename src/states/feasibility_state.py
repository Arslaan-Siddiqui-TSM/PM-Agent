"""
Feasibility State

State management for feasibility assessment graph.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Literal
from pydantic import BaseModel, Field


class FeasibilityState(BaseModel):
    """State for feasibility assessment graph execution."""
    
    # Inputs
    session_id: str
    md_file_paths: Optional[List[str]] = None
    development_context: Optional[Dict[str, str]] = None
    
    # Intermediate
    unified_context_path: str = ""
    
    # Outputs
    thinking_summary: str = ""
    feasibility_report: str = ""
    
    # Human-in-the-Loop fields
    initial_thinking_summary: str = ""  # Preserve the first detailed thinking summary before HITL
    approved: Optional[bool] = None  # None=not reviewed, True=approved, False=needs revision
    human_feedback: Optional[str] = None  # User's revision request text
    critique_md: Optional[str] = None  # Structured critique generated from feedback
    revision_history: List[Dict] = Field(default_factory=list)  # Track all iterations with metadata
    iteration: int = 0  # Current iteration (0 = initial generation)
    max_iterations: int = 3  # Maximum revisions allowed
    status: Literal[
        "generating",
        "awaiting_human", 
        "revising",
        "approved",
        "max_iterations_reached",
        "failed"
    ] = "generating"
    
    class Config:
        arbitrary_types_allowed = True
