"""
Revision State

State management for feasibility report revision (HITL) workflow.
"""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class RevisionState(BaseModel):
    """State for feasibility report revision (HITL) workflow."""
    
    # Session & version tracking
    session_id: str
    current_version: int                              # Version being critiqued (1, 2, 3...)
    new_version: int = 0                              # Will be set after revision
    
    # Core artifacts (inputs to revision LLM)
    feasibility_report_current: str = ""              # Current version content (vN.md)
    thinking_summary: str = ""                        # Original thinking summary (unchanged)
    human_critique: str                               # User feedback
    revision_instructions: Optional[str] = None       # Optional structured guidance
    
    # Configuration & constraints
    max_revisions: int = 5                            # Safety limit (v1 → v2 → v3 → v4 → v5)
    revision_number: int = 0                          # Counter for internal tracking
    
    # Process state
    status: str = "pending"                           # pending | revising | completed | failed
    revised_report: str = ""                          # Output from LLM
    revision_summary: Optional[str] = ""              # Change log
    
    # Metrics & tracking
    token_usage: int = 0                              # Tokens used in this revision
    execution_time: float = 0.0                       # Time taken (seconds)
    error_message: Optional[str] = None               # Error details if failed
    created_at: str = ""                              # ISO timestamp
    
    # File paths
    current_report_path: str = ""                     # Path to feasibility_report_vN.md
    thinking_summary_path: str = ""                   # Path to thinking_summary.md
    revised_report_path: str = ""                     # Path to feasibility_report_v(N+1).md
    
    class Config:
        arbitrary_types_allowed = True
