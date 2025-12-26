"""
Human-in-the-Loop (HITL) Interrupt Nodes for Reflection Pattern.

This module implements the interrupt nodes for the HITL planning workflow:
- human_review_draft: Pauses after draft generation for human review
- human_review_reflection: Pauses after reflection for human review

Key Design Principles:
1. Human Authority: Humans can edit any generated text, override AI decisions, terminate execution
2. Synchronous Execution: Graph execution blocks until human responds
3. UX-First: Clear step labels, editable text areas, intermediate states visible

Workflow:
    START → Draft (LLM) → ⏸ Human Review Draft → Reflect (LLM) → ⏸ Human Review Reflection → Revise (LLM) → END or LOOP
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from langgraph.types import interrupt

from src.states.reflection_state import HumanReviewRecord, ReflectionState
from src.utils.helper import get_global_logger


def human_review_draft(state: ReflectionState) -> Dict[str, Any]:
    """
    Interrupt node for human review of the draft.

    This node:
    1. Pauses execution for human input
    2. Allows humans to edit the draft directly
    3. Supports: Approve, Provide Feedback, or Terminate
    4. Returns state updates based on human action

    Interrupt Payload (sent to UI):
    {
        "type": "draft_review",
        "iteration": <current_iteration>,
        "draft": <draft_text>,
        "message": "Please review the AI-generated draft plan"
    }

    Expected Human Response:
    {
        "draft": "<edited draft text or original>",
        "draft_approved": true/false,
        "draft_human_feedback": "Optional feedback text",
        "terminated_by_human": false
    }

    Routing:
    - Approved → reflect_node
    - Feedback → reflect_node (with feedback incorporated)
    - Terminate → END
    """
    logger = get_global_logger()

    # Build interrupt payload for UI
    interrupt_payload = {
        "type": "draft_review",
        "iteration": state.iteration_count,
        "draft": state.current_draft,
        "request_id": state.request_id,
        "thread_id": state.thread_id,
        "message": "Please review the AI-generated draft plan. You can edit the text, provide feedback, approve, or terminate.",
    }

    if logger:
        logger.logger.info(
            f"🛑 HITL: Draft Review Interrupt\n"
            f"   Request ID: {state.request_id}\n"
            f"   Iteration: {state.iteration_count}\n"
            f"   Draft length: {len(state.current_draft or '')} chars"
        )

    # Pause execution and wait for human input
    human_input = interrupt(interrupt_payload)

    # Process human response
    if not isinstance(human_input, dict):
        raise ValueError(
            f"human_review_draft: Expected dict response, got {type(human_input)}"
        )

    if logger:
        logger.logger.info(
            f"✅ HITL: Draft Review Resumed\n"
            f"   Action: {'Approved' if human_input.get('draft_approved') else 'Feedback'}\n"
            f"   Terminated: {human_input.get('terminated_by_human', False)}"
        )

    # Check for termination
    if human_input.get("terminated_by_human", False):
        # Record termination in review history
        review_record = HumanReviewRecord(
            review_type="draft_review",
            action="terminate",
            feedback_text=human_input.get("draft_human_feedback"),
            reviewer_id=human_input.get("reviewer_id"),
            timestamp=datetime.now(timezone.utc),
        )

        return {
            "terminated_by_human": True,
            "review_history": list(state.review_history) + [review_record],
            "final_plan": human_input.get("draft")
            or state.current_draft,  # Use current draft as final
        }

    # Get edited draft (human may have modified it)
    edited_draft = human_input.get("draft", state.current_draft)
    draft_approved = human_input.get("draft_approved", False)
    draft_human_feedback = human_input.get("draft_human_feedback")

    # Update the latest iteration with human edits if draft was modified
    iterations = list(state.iterations)
    if iterations and edited_draft != state.current_draft:
        latest_iteration = iterations[-1].model_copy()
        latest_iteration.draft_human_edited = edited_draft
        iterations[-1] = latest_iteration

    # Record review action
    review_record = HumanReviewRecord(
        review_type="draft_review",
        action="approve" if draft_approved else "feedback",
        feedback_text=draft_human_feedback,
        edited_text=edited_draft if edited_draft != state.current_draft else None,
        reviewer_id=human_input.get("reviewer_id"),
        timestamp=datetime.now(timezone.utc),
    )

    return {
        "draft": edited_draft,  # Use human-edited version
        "draft_approved": draft_approved,
        "draft_human_feedback": draft_human_feedback,
        "iterations": iterations,
        "review_history": list(state.review_history) + [review_record],
    }


def human_review_reflection(state: ReflectionState) -> Dict[str, Any]:
    """
    Interrupt node for human review of the reflection/critique.

    This node:
    1. Pauses execution for human input
    2. Displays draft (read-only) and reflection (editable)
    3. Prevents incorrect critiques, over-analysis, missed risks, hallucinations
    4. Supports: Approve Critique, Provide Feedback, or Terminate

    Interrupt Payload (sent to UI):
    {
        "type": "reflection_review",
        "iteration": <current_iteration>,
        "draft": <draft_text>,  # Read-only context
        "reflection": <reflection_text>,  # Editable
        "message": "Please review the AI critique"
    }

    Expected Human Response:
    {
        "reflection": "<edited reflection text or original>",
        "reflection_approved": true/false,
        "reflection_human_feedback": "Optional corrective feedback",
        "terminated_by_human": false
    }

    Routing:
    - Approved → revise_node
    - Feedback → revise_node (with corrected critique)
    - Terminate → END
    """
    logger = get_global_logger()

    # Build interrupt payload for UI
    interrupt_payload = {
        "type": "reflection_review",
        "iteration": state.iteration_count,
        "draft": state.current_draft,  # Read-only context
        "reflection": state.current_critique,  # Editable
        "request_id": state.request_id,
        "thread_id": state.thread_id,
        "message": "Please review the AI critique. You can edit the reflection, provide corrective feedback, approve, or terminate.",
    }

    if logger:
        logger.logger.info(
            f"🛑 HITL: Reflection Review Interrupt\n"
            f"   Request ID: {state.request_id}\n"
            f"   Iteration: {state.iteration_count}\n"
            f"   Reflection length: {len(state.current_critique or '')} chars"
        )

    # Pause execution and wait for human input
    human_input = interrupt(interrupt_payload)

    # Process human response
    if not isinstance(human_input, dict):
        raise ValueError(
            f"human_review_reflection: Expected dict response, got {type(human_input)}"
        )

    if logger:
        logger.logger.info(
            f"✅ HITL: Reflection Review Resumed\n"
            f"   Action: {'Approved' if human_input.get('reflection_approved') else 'Feedback'}\n"
            f"   Terminated: {human_input.get('terminated_by_human', False)}"
        )

    # Check for termination
    if human_input.get("terminated_by_human", False):
        # Record termination in review history
        review_record = HumanReviewRecord(
            review_type="reflection_review",
            action="terminate",
            feedback_text=human_input.get("reflection_human_feedback"),
            reviewer_id=human_input.get("reviewer_id"),
            timestamp=datetime.now(timezone.utc),
        )

        return {
            "terminated_by_human": True,
            "review_history": list(state.review_history) + [review_record],
            "final_plan": state.current_draft,  # Use current draft as final
        }

    # Get edited reflection (human may have modified it)
    edited_reflection = human_input.get("reflection", state.current_critique)
    reflection_approved = human_input.get("reflection_approved", False)
    reflection_human_feedback = human_input.get("reflection_human_feedback")

    # Update the latest iteration with human edits if reflection was modified
    iterations = list(state.iterations)
    if iterations and edited_reflection != state.current_critique:
        latest_iteration = iterations[-1].model_copy()
        latest_iteration.critique = (
            edited_reflection  # Update critique with human edits
        )
        latest_iteration.reflection_human_edited = edited_reflection
        iterations[-1] = latest_iteration

    # Record review action
    review_record = HumanReviewRecord(
        review_type="reflection_review",
        action="approve" if reflection_approved else "feedback",
        feedback_text=reflection_human_feedback,
        edited_text=edited_reflection
        if edited_reflection != state.current_critique
        else None,
        reviewer_id=human_input.get("reviewer_id"),
        timestamp=datetime.now(timezone.utc),
    )

    return {
        "reflection": edited_reflection,  # Use human-edited version
        "reflection_approved": reflection_approved,
        "reflection_human_feedback": reflection_human_feedback,
        "iterations": iterations,
        "review_history": list(state.review_history) + [review_record],
    }
