"""
Human-In-The-Loop Review Node

This node processes human reviewer input stored in state.human_feedback after the reflect node interrupts and resumes.
It handles approve/feedback actions and manages iteration limits.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any

from src.states.reflection_state import ReflectionState
from src.utils.helper import get_global_logger


def human_review_node(state: ReflectionState) -> Dict[str, Any]:
    """
    Process human reviewer input from state.human_feedback and update state accordingly.
    
    This node is called after the reflect node resumes from interrupt.
    The human_feedback field should contain the reviewer's decision.
    
    Args:
        state: Current ReflectionState with human_feedback populated
    
    Returns:
        State updates dictionary with routing information
    """
    logger = get_global_logger()
    
    # Validate that human_feedback exists
    if not state.human_feedback:
        raise ValueError("human_review_node called but state.human_feedback is None")
    
    human_input = state.human_feedback
    
    # Validate human_input structure
    if not isinstance(human_input, dict):
        raise ValueError(f"human_feedback must be a dict, got {type(human_input)}")
    
    action = human_input.get("action")
    request_id = human_input.get("request_id")
    
    if logger:
        logger.logger.info(
            f"HITL: human_review_node called\n"
            f"  state.request_id={state.request_id}\n"
            f"  human_input.request_id={request_id}\n"
            f"  action={action}\n"
            f"  iteration={state.iteration_count}"
        )
    
    if not action:
        raise ValueError("human_feedback must contain 'action' field")
    
    if not request_id:
        raise ValueError("human_feedback must contain 'request_id' field")
    
    if action not in ["approve", "feedback"]:
        raise ValueError(f"action must be 'approve' or 'feedback', got '{action}'")
    
    # Validate request_id matches state
    if state.request_id and state.request_id != request_id:
        raise ValueError(
            f"request_id mismatch: expected {state.request_id}, got {request_id}"
        )
    
    # Build review record
    review_record = {
        "action": action,
        "request_id": request_id,
        "iteration": state.iteration_count,
        "feedback_text": human_input.get("feedback_text"),
        "edited_text": human_input.get("edited_text"),
        "tags": human_input.get("tags", []),
        "reviewer_id": human_input.get("reviewer_id"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Update review history
    review_history = list(state.review_history)
    review_history.append(review_record)
    
    # Initialize return dict
    # NOTE: Do NOT include request_id - let reflect node manage it exclusively
    updates: Dict[str, Any] = {
        "review_history": review_history,
        "human_feedback": None,  # Clear after processing
    }
    
    # ═══════════════════════════════════════════════════════════
    # HANDLE APPROVE ACTION
    # ═══════════════════════════════════════════════════════════
    if action == "approve":
        # Set final_plan to current draft
        updates["final_plan"] = state.current_draft
        
        # Mark the latest iteration as accepted
        if state.iterations:
            iterations = list(state.iterations)
            latest = iterations[-1].model_copy()
            latest.accepted = True
            iterations[-1] = latest
            updates["iterations"] = iterations
        
        if logger:
            logger.logger.info(
                f"HITL: Approved by {review_record['reviewer_id'] or 'unknown'} "
                f"at iteration {state.iteration_count}"
            )
        
        return updates
    
    # ═══════════════════════════════════════════════════════════
    # HANDLE FEEDBACK ACTION
    # ═══════════════════════════════════════════════════════════
    elif action == "feedback":
        feedback_text = human_input.get("feedback_text")
        edited_text = human_input.get("edited_text")
        tags = human_input.get("tags", [])
        reviewer_id = human_input.get("reviewer_id")
        
        # Check if we've reached max_iterations
        current_iteration = state.iteration_count
        if current_iteration >= state.max_iterations:
            if logger:
                logger.logger.warning(
                    f"HITL: Max iterations ({state.max_iterations}) reached. "
                    f"Attempting to finalize with edited_text or last draft."
                )
            
            updates["max_iterations_reached"] = True
            
            # If reviewer provided edited_text, use it as final
            if edited_text and edited_text.strip():
                updates["final_plan"] = edited_text
                
                # Mark as accepted
                if state.iterations:
                    iterations = list(state.iterations)
                    latest = iterations[-1].model_copy()
                    latest.accepted = True
                    latest.draft = edited_text  # Update with edited version
                    iterations[-1] = latest
                    updates["iterations"] = iterations
                
                if logger:
                    logger.logger.info(
                        "HITL: Finalized with edited_text from reviewer"
                    )
            else:
                # No edited_text, finalize with last model output
                updates["final_plan"] = state.current_draft
                
                if state.iterations:
                    iterations = list(state.iterations)
                    latest = iterations[-1].model_copy()
                    latest.accepted = True
                    iterations[-1] = latest
                    updates["iterations"] = iterations
                
                if logger:
                    logger.logger.info(
                        "HITL: Max iterations reached, finalized with last model output"
                    )
            
            # Return with final_plan set - graph will route to finalize
            return updates
        
        # Not at max_iterations yet, prepare feedback for draft node
        # Store it back in human_feedback for the draft node to consume
        updates["human_feedback"] = {
            "text": feedback_text,
            "edited_text": edited_text,
            "tags": tags,
            "reviewer": reviewer_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if logger:
            logger.logger.info(
                f"HITL: Feedback received from {reviewer_id or 'unknown'}. "
                f"Iteration {current_iteration}/{state.max_iterations}. "
                f"Will generate new draft incorporating feedback."
            )
        
        # Return without final_plan - graph will route to draft
        return updates
    
    # Should never reach here due to validation above
    raise ValueError(f"Unhandled action: {action}")
