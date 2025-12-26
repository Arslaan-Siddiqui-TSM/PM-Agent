from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class HumanReviewRecord(BaseModel):
    """Record of a single human review action."""

    review_type: str = Field(
        description="Type of review: 'draft_review' or 'reflection_review'"
    )
    action: str = Field(
        description="Action taken: 'approve', 'feedback', or 'terminate'"
    )
    feedback_text: Optional[str] = Field(
        default=None, description="Feedback text provided by reviewer"
    )
    edited_text: Optional[str] = Field(
        default=None, description="Edited text if reviewer modified content"
    )
    reviewer_id: Optional[str] = Field(
        default=None, description="Identifier of the reviewer"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the review was submitted"
    )


class ReflectionIteration(BaseModel):
    """A single reflection cycle containing a draft and optional critique."""

    draft: str = Field(description="Draft produced during this iteration")
    critique: Optional[str] = Field(
        default=None, description="Critique or feedback generated for the draft"
    )
    accepted: bool = Field(
        default=False,
        description="Whether this iteration's draft was accepted as final output",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the iteration was recorded",
    )

    # HITL tracking for this iteration
    draft_human_edited: Optional[str] = Field(
        default=None, description="Human-edited version of the draft (if modified)"
    )
    reflection_human_edited: Optional[str] = Field(
        default=None, description="Human-edited version of the reflection (if modified)"
    )


class ReflectionState(BaseModel):
    """State container for the reflection-style planning agent."""

    # ═══════════════════════════════════════════════════════════
    # CORE INPUT FIELDS
    # ═══════════════════════════════════════════════════════════
    task: Optional[str] = Field(
        default=None, description="Original user task or problem statement"
    )
    document_context: Optional[str] = Field(
        default=None, description="Aggregated context derived from documents"
    )
    feasibility_file_path: Optional[str] = Field(
        default=None, description="Path to feasibility assessment notes"
    )

    # ═══════════════════════════════════════════════════════════
    # ITERATION CONTROL
    # ═══════════════════════════════════════════════════════════
    max_iterations: int = Field(
        default=5,
        description="Maximum number of draft→reflect→revise cycles before stopping (hard cap: 5)",
    )
    iterations: List[ReflectionIteration] = Field(
        default_factory=list,
        description="History of generated drafts and critiques",
    )

    # ═══════════════════════════════════════════════════════════
    # HUMAN-IN-THE-LOOP (HITL) FIELDS
    # ═══════════════════════════════════════════════════════════

    # Draft review stage
    draft: Optional[str] = Field(
        default=None, description="Current draft text (canonical plan text)"
    )
    draft_human_feedback: Optional[str] = Field(
        default=None, description="Human feedback/instructions for the draft"
    )
    draft_approved: Optional[bool] = Field(
        default=None, description="Whether the draft was approved by human reviewer"
    )

    # Reflection review stage
    reflection: Optional[str] = Field(
        default=None, description="Current reflection/critique text"
    )
    reflection_human_feedback: Optional[str] = Field(
        default=None, description="Human corrective feedback for the reflection"
    )
    reflection_approved: Optional[bool] = Field(
        default=None,
        description="Whether the reflection was approved by human reviewer",
    )

    # Revised plan
    revised_plan: Optional[str] = Field(
        default=None, description="Final revised plan after incorporating all feedback"
    )

    # Termination control
    terminated_by_human: bool = Field(
        default=False, description="Whether execution was terminated by human reviewer"
    )

    # Review tracking
    review_history: List[HumanReviewRecord] = Field(
        default_factory=list, description="History of all human review actions"
    )

    # Session/request tracking for HITL
    request_id: Optional[str] = Field(
        default=None, description="Unique request ID for HITL tracking"
    )
    thread_id: Optional[str] = Field(
        default=None, description="LangGraph thread ID for checkpointing"
    )

    # ═══════════════════════════════════════════════════════════
    # ENHANCED TRACKING (for iteration awareness)
    # ═══════════════════════════════════════════════════════════
    quality_scores: List[float] = Field(
        default_factory=list,
        description="Quality scores (0-10) for each iteration to track improvement trajectory",
    )
    improvement_areas: List[str] = Field(
        default_factory=list,
        description="Focus areas identified for each iteration to avoid redundant critiques",
    )
    iteration_summaries: List[str] = Field(
        default_factory=list,
        description="High-level summaries of what was addressed in each iteration",
    )
    addressed_issues: List[str] = Field(
        default_factory=list,
        description="Issues that have been resolved in previous iterations",
    )

    # ═══════════════════════════════════════════════════════════
    # OUTPUT
    # ═══════════════════════════════════════════════════════════
    final_plan: Optional[str] = Field(
        default=None, description="Accepted project plan Markdown"
    )

    def __getitem__(self, item: str):
        """Allow dict-style access for LangGraph compatibility"""
        return getattr(self, item)

    # ═══════════════════════════════════════════════════════════
    # CONVENIENCE PROPERTIES (derived from iterations)
    # ═══════════════════════════════════════════════════════════
    @property
    def current_draft(self) -> Optional[str]:
        """Get the most recent draft from iteration history or state.draft"""
        if self.draft:
            return self.draft
        return self.iterations[-1].draft if self.iterations else None

    @property
    def current_critique(self) -> Optional[str]:
        """Get the most recent critique from iteration history or state.reflection"""
        if self.reflection:
            return self.reflection
        return self.iterations[-1].critique if self.iterations else None

    @property
    def iteration_count(self) -> int:
        """Current iteration number (0-indexed)"""
        return len(self.iterations)
