"""
FastAPI endpoints for Human-In-The-Loop review and resume functionality.

Supports two interrupt points in the HITL Reflection Pattern:
- draft_review: Human reviews the AI-generated draft
- reflection_review: Human reviews the AI-generated critique

Provides:
- GET /pending-review/{request_id}: Fetch pending review data (both types)
- POST /resume-review: Resume graph execution with human input
- POST /terminate-review: Terminate the planning workflow
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field, validator

from src.services.graph_runner import get_graph_runner
from src.utils.helper import get_global_logger

router = APIRouter()

# Get HITL secret from environment (for local dev, default to 'changeme')
HITL_SECRET = os.getenv("HITL_SECRET", "changeme")

# Paths
PENDING_REVIEWS_DIR = Path("output/pending_reviews")
AUDIT_LOG_PATH = Path("output/review_audit.jsonl")


# ═══════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════


class DraftReviewPayload(BaseModel):
    """
    Request payload for submitting draft review.

    Actions:
    - approve: Accept the draft and proceed to reflection
    - feedback: Provide feedback/edits and proceed to reflection
    - terminate: Stop the workflow and finalize with current draft
    """

    request_id: str = Field(..., description="UUID of the review request")
    action: Literal["approve", "feedback", "terminate"] = Field(
        ..., description="Action: approve, feedback, or terminate"
    )
    draft: Optional[str] = Field(None, description="Edited draft text (if modified)")
    draft_human_feedback: Optional[str] = Field(
        None, description="Feedback text for the draft"
    )
    reviewer_id: Optional[str] = Field(None, description="Reviewer identifier")

    @validator("draft")
    def validate_draft_length(cls, v):
        if v and len(v) > 100_000:
            raise ValueError("draft must be ≤ 100,000 characters")
        return v


class ReflectionReviewPayload(BaseModel):
    """
    Request payload for submitting reflection review.

    Actions:
    - approve: Accept the critique and proceed to revision
    - feedback: Provide corrective feedback and proceed to revision
    - terminate: Stop the workflow and finalize with current draft
    """

    request_id: str = Field(..., description="UUID of the review request")
    action: Literal["approve", "feedback", "terminate"] = Field(
        ..., description="Action: approve, feedback, or terminate"
    )
    reflection: Optional[str] = Field(
        None, description="Edited reflection text (if modified)"
    )
    reflection_human_feedback: Optional[str] = Field(
        None, description="Corrective feedback for reflection"
    )
    reviewer_id: Optional[str] = Field(None, description="Reviewer identifier")

    @validator("reflection")
    def validate_reflection_length(cls, v):
        if v and len(v) > 50_000:
            raise ValueError("reflection must be ≤ 50,000 characters")
        return v


class ReviewPayload(BaseModel):
    """Legacy request payload for resuming a review (backwards compatible)."""

    request_id: str = Field(..., description="UUID of the review request")
    action: str = Field(..., description="'approve' or 'feedback'")
    feedback_text: Optional[str] = Field(None, description="Reviewer feedback text")
    edited_text: Optional[str] = Field(None, description="Edited draft text")
    tags: Optional[List[str]] = Field(default_factory=list, description="Review tags")
    reviewer_id: Optional[str] = Field(None, description="Reviewer identifier")

    @validator("action")
    def validate_action(cls, v):
        if v not in ["approve", "feedback", "terminate"]:
            raise ValueError("action must be 'approve', 'feedback', or 'terminate'")
        return v

    @validator("edited_text")
    def validate_edited_text_length(cls, v):
        if v and len(v) > 50_000:
            raise ValueError("edited_text must be ≤ 50,000 characters")
        return v


class PendingReviewResponse(BaseModel):
    """Response model for pending review data."""

    type: str  # "draft_review" or "reflection_review"
    node: str
    request_id: str
    thread_id: str
    iteration: int
    draft: Optional[str] = (
        None  # For draft_review: editable draft; for reflection_review: read-only context
    )
    reflection: Optional[str] = None  # For reflection_review: editable critique
    model_output: Optional[str] = None  # Legacy field
    reflection_notes: Optional[str] = None  # Legacy field
    metadata: dict
    message: str


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════


def _verify_auth(authorization: Optional[str]) -> bool:
    """Verify the Authorization header matches the expected Bearer token."""
    if not authorization:
        return False

    # Expected format: "Bearer <token>"
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0] != "Bearer":
        return False

    token = parts[1]
    return token == HITL_SECRET


def _append_audit_record(audit_data: dict) -> None:
    """Append a JSON record to the audit log file."""
    logger = get_global_logger()

    try:
        # Ensure output directory exists
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Append as JSON line
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(audit_data, ensure_ascii=False) + "\n")

        if logger:
            logger.logger.info(
                f"Audit: Appended record for request_id={audit_data.get('request_id')}"
            )

    except Exception as e:
        if logger:
            logger.logger.error(f"Audit: Failed to write audit log: {e}")
        raise


def _acquire_lock(request_id: str) -> bool:
    """
    Attempt to acquire a lock file for the given request_id.
    Returns True if lock acquired, False if already locked.
    """
    lock_file = PENDING_REVIEWS_DIR / f"{request_id}.lock"

    if lock_file.exists():
        return False

    try:
        # Create lock file
        lock_file.touch()
        return True
    except Exception:
        return False


def _release_lock(request_id: str) -> None:
    """Release the lock file for the given request_id."""
    lock_file = PENDING_REVIEWS_DIR / f"{request_id}.lock"

    try:
        if lock_file.exists():
            lock_file.unlink()
    except Exception as e:
        logger = get_global_logger()
        if logger:
            logger.logger.warning(f"Failed to release lock for {request_id}: {e}")


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════


@router.get(
    "/pending-review/{request_id}",
    response_model=PendingReviewResponse,
    summary="Get pending review data",
    description="Fetch the interrupt payload for a pending review by request_id",
)
async def get_pending_review(request_id: str):
    """
    Retrieve pending review data persisted by the reflect node.

    Args:
        request_id: UUID of the review request

    Returns:
        PendingReviewResponse: The interrupt payload

    Raises:
        404: If pending review file not found
    """
    logger = get_global_logger()

    pending_file = PENDING_REVIEWS_DIR / f"{request_id}.json"

    if not pending_file.exists():
        if logger:
            logger.logger.warning(f"Pending review not found: {request_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending review not found for request_id: {request_id}",
        )

    try:
        with open(pending_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if logger:
            logger.logger.info(f"Fetched pending review: {request_id}")

        return PendingReviewResponse(**data)

    except Exception as e:
        if logger:
            logger.logger.error(f"Error reading pending review {request_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading pending review: {str(e)}",
        )


@router.post(
    "/resume-review",
    summary="Resume graph execution with human review",
    description="Submit reviewer decision and resume the LangGraph execution",
)
async def resume_review(
    payload: ReviewPayload, authorization: Optional[str] = Header(None)
):
    """
    Resume a paused graph execution with human reviewer input.

    This endpoint:
    1. Validates authorization
    2. Acquires a lock to prevent concurrent resume
    3. Appends an audit record
    4. Calls LangGraph resume API/SDK
    5. Deletes the pending review file on success

    Args:
        payload: ReviewPayload containing reviewer decision
        authorization: Bearer token for authentication

    Returns:
        Success message with request_id and action

    Raises:
        401: If authorization invalid
        400: If validation fails
        404: If pending review not found
        409: If already locked (concurrent resume attempt)
        500: If resume operation fails
    """
    logger = get_global_logger()

    # ═══════════════════════════════════════════════════════════
    # 1. VALIDATE AUTHORIZATION
    # ═══════════════════════════════════════════════════════════
    if not _verify_auth(authorization):
        if logger:
            logger.logger.warning(
                f"Unauthorized resume attempt for {payload.request_id}"
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Authorization header",
        )

    # ═══════════════════════════════════════════════════════════
    # 2. CHECK PENDING FILE EXISTS
    # ═══════════════════════════════════════════════════════════
    pending_file = PENDING_REVIEWS_DIR / f"{payload.request_id}.json"

    if not pending_file.exists():
        if logger:
            logger.logger.warning(
                f"Resume attempted but pending file not found: {payload.request_id}"
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending review not found for request_id: {payload.request_id}",
        )

    # ═══════════════════════════════════════════════════════════
    # 3. ACQUIRE LOCK
    # ═══════════════════════════════════════════════════════════
    if not _acquire_lock(payload.request_id):
        if logger:
            logger.logger.warning(f"Resume lock already held for {payload.request_id}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resume already in progress for this request_id",
        )

    # Ensure audit_record is always defined so the outer exception handler can reference it safely
    audit_record: dict = {}

    try:
        # ═══════════════════════════════════════════════════════
        # 4. READ PENDING FILE FOR AUDIT
        # ═══════════════════════════════════════════════════════
        try:
            with open(pending_file, "r", encoding="utf-8") as f:
                pending_data = json.load(f)

        except Exception as e:
            if logger:
                logger.logger.error(f"Error reading pending file for audit: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error reading pending review file: {str(e)}",
            )

        # ═══════════════════════════════════════════════════════
        # 5. BUILD AUDIT RECORD
        # ═══════════════════════════════════════════════════════
        review_type = pending_data.get("type", "unknown")

        audit_record = {
            "request_id": payload.request_id,
            "review_type": review_type,
            "iteration": pending_data.get("iteration"),
            "action": payload.action,
            "feedback_text": payload.feedback_text,
            "edited_text": payload.edited_text,
            "tags": payload.tags or [],
            "reviewer_id": payload.reviewer_id,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "draft_snapshot": pending_data.get("draft", "")[:500]
            if pending_data.get("draft")
            else None,
            "reflection_snapshot": pending_data.get("reflection", "")[:500]
            if pending_data.get("reflection")
            else None,
        }

        # Append audit log
        try:
            _append_audit_record(audit_record)
        except Exception as e:
            if logger:
                logger.logger.error(f"Failed to append audit log: {e}")
            # Don't fail the request if audit fails, but log it

        # ═══════════════════════════════════════════════════════
        # 6. BUILD HUMAN INPUT BASED ON REVIEW TYPE
        # ═══════════════════════════════════════════════════════
        # Build human_input dict based on review type
        if review_type == "draft_review":
            # Draft review: human can edit draft, provide feedback, approve, or terminate
            human_input = {
                "draft": payload.edited_text or pending_data.get("draft"),
                "draft_approved": payload.action == "approve",
                "draft_human_feedback": payload.feedback_text,
                "terminated_by_human": payload.action == "terminate",
                "reviewer_id": payload.reviewer_id,
            }
        elif review_type == "reflection_review":
            # Reflection review: human can edit reflection, provide feedback, approve, or terminate
            human_input = {
                "reflection": payload.edited_text or pending_data.get("reflection"),
                "reflection_approved": payload.action == "approve",
                "reflection_human_feedback": payload.feedback_text,
                "terminated_by_human": payload.action == "terminate",
                "reviewer_id": payload.reviewer_id,
            }
        else:
            # Legacy/fallback format
            human_input = {
                "request_id": payload.request_id,
                "action": payload.action,
                "feedback_text": payload.feedback_text,
                "edited_text": payload.edited_text,
                "tags": payload.tags or [],
                "reviewer_id": payload.reviewer_id,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }

        # Extract thread_id from pending file
        thread_id = pending_data.get("thread_id")
        if not thread_id:
            if logger:
                logger.logger.error(
                    f"No thread_id in pending file for {payload.request_id}"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Pending review missing thread_id. Cannot resume execution.",
            )

        # Log payload and pending data for diagnostics
        if logger:
            logger.logger.info(
                f"Resume request received: payload.request_id={payload.request_id}, action={payload.action}, reviewer={payload.reviewer_id}"
            )
            logger.logger.info(
                f"Pending file data - request_id: {pending_data.get('request_id')}, thread_id: {pending_data.get('thread_id')}, iteration: {pending_data.get('iteration')}"
            )
            logger.logger.debug(
                f"Pending file snapshot for {payload.request_id}: {json.dumps(pending_data, ensure_ascii=False)[:1000]}"
            )
            logger.logger.debug(
                f"Human input to be passed: {json.dumps(human_input, ensure_ascii=False)}"
            )

        # Get the singleton GraphRunner instance
        try:
            graph_runner = get_graph_runner()
        except Exception as e:
            if logger:
                logger.logger.error(f"Failed to get GraphRunner: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize graph runner: {str(e)}",
            )

        # Resume the graph execution
        try:
            if logger:
                logger.logger.info(
                    f"HITL Resume: About to call graph_runner.resume_execution\n"
                    f"  request_id={payload.request_id}\n"
                    f"  thread_id={thread_id}\n"
                    f"  action={payload.action}\n"
                    f"  human_input.request_id={human_input.get('request_id')}"
                )

            # Call the GraphRunner to resume execution
            # This will call: graph.invoke(Command(resume=human_input), config={"configurable": {"thread_id": thread_id}})
            result = graph_runner.resume_execution(
                thread_id=thread_id,
                human_input=human_input,
                request_id=payload.request_id,
            )

            if logger:
                logger.logger.info(
                    f"HITL Resume: Graph execution resumed successfully for {payload.request_id}"
                )

                # Log result details for debugging
                if isinstance(result, dict):
                    logger.logger.info(
                        f"HITL Resume: Result details\n"
                        f"  has_final_plan={bool(result.get('final_plan'))}\n"
                        f"  result_request_id={result.get('request_id')}\n"
                        f"  iteration_count={result.get('iteration_count')}\n"
                        f"  has_interrupt={'__interrupt__' in result}"
                    )

        except Exception as e:
            if logger:
                logger.logger.error(f"Graph resume failed: {e}", exc_info=True)

            # Append failure to audit
            try:
                failure_record = audit_record.copy()
                failure_record["error"] = str(e)
                failure_record["status"] = "failed"
                _append_audit_record(failure_record)
            except Exception:
                pass

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Graph resume operation failed: {str(e)}",
            )

        # ═══════════════════════════════════════════════════════
        # 7. DELETE PENDING FILE ON SUCCESS
        # ═══════════════════════════════════════════════════════
        # Delete the old pending file since it was processed
        try:
            pending_file.unlink()
            if logger:
                logger.logger.info(f"Deleted pending file: {payload.request_id}")
        except Exception as e:
            if logger:
                logger.logger.error(f"Failed to delete pending file: {e}")

        # ═══════════════════════════════════════════════════════
        # 8. PREPARE RESPONSE WITH NEW REQUEST_ID (if graph interrupted again)
        # ═══════════════════════════════════════════════════════
        response_data = {
            "status": "success",
            "message": "Review processed and graph execution resumed successfully",
            "request_id": payload.request_id,
            "action": payload.action,
            "thread_id": thread_id,
        }

        # If the graph interrupted again (e.g., for reflection_review), extract and save new pending review
        if isinstance(result, dict):
            if logger:
                logger.logger.info(
                    f"HITL: Checking result for interrupt status\n"
                    f"  result keys: {list(result.keys())}\n"
                    f"  has __interrupt__: {'__interrupt__' in result}\n"
                    f"  request_id in result: {result.get('request_id')}\n"
                    f"  has final_plan: {bool(result.get('final_plan'))}"
                )

            # Check if graph has a new interrupt (indicated by __interrupt__ key)
            if "__interrupt__" in result:
                interrupt_data = result.get("__interrupt__", [])
                
                if interrupt_data:
                    # Extract interrupt value (same logic as plan_generation_handler)
                    first_interrupt = interrupt_data[0] if isinstance(interrupt_data, (list, tuple)) else interrupt_data
                    
                    if hasattr(first_interrupt, 'value'):
                        interrupt_value = first_interrupt.value
                    elif isinstance(first_interrupt, dict):
                        interrupt_value = first_interrupt.get("value", first_interrupt)
                    else:
                        interrupt_value = {}
                    
                    # Generate new request_id for this interrupt
                    new_request_id = str(uuid.uuid4())
                    
                    # Extract interrupt details
                    review_type = interrupt_value.get("type", "unknown") if isinstance(interrupt_value, dict) else "unknown"
                    draft_content = interrupt_value.get("draft") if isinstance(interrupt_value, dict) else None
                    reflection_content = interrupt_value.get("reflection") if isinstance(interrupt_value, dict) else None
                    iteration = interrupt_value.get("iteration", 1) if isinstance(interrupt_value, dict) else 1
                    message = interrupt_value.get("message", "Human review required") if isinstance(interrupt_value, dict) else "Human review required"
                    
                    if logger:
                        logger.logger.info(
                            f"HITL: Graph interrupted again\n"
                            f"  old_request_id={payload.request_id}\n"
                            f"  new_request_id={new_request_id}\n"
                            f"  review_type={review_type}\n"
                            f"  iteration={iteration}"
                        )
                    
                    # Save new pending review file
                    new_pending_data = {
                        "type": review_type,
                        "node": review_type,
                        "request_id": new_request_id,
                        "thread_id": thread_id,
                        "iteration": iteration,
                        "draft": draft_content,
                        "reflection": reflection_content,
                        "message": message,
                        "metadata": {
                            "session_id": pending_data.get("metadata", {}).get("session_id"),
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "previous_request_id": payload.request_id,
                        }
                    }
                    
                    new_pending_file = PENDING_REVIEWS_DIR / f"{new_request_id}.json"
                    with open(new_pending_file, "w", encoding="utf-8") as f:
                        json.dump(new_pending_data, f, ensure_ascii=False, indent=2)
                    
                    if logger:
                        logger.logger.info(f"Saved new pending review: {new_pending_file}")
                    
                    response_data["interrupted_again"] = True
                    response_data["new_request_id"] = new_request_id
                    response_data["review_type"] = review_type
                    response_data["iteration"] = iteration
                else:
                    response_data["interrupted_again"] = False
            else:
                # Graph completed (final_plan was set)
                response_data["interrupted_again"] = False
                response_data["completed"] = True
                response_data["final_plan"] = result.get("final_plan")
                response_data["has_final_plan"] = bool(result.get("final_plan"))

                if logger:
                    logger.logger.info(
                        f"HITL: Graph completed (no more interrupts)\n"
                        f"  has_final_plan={bool(result.get('final_plan'))}"
                    )

        return response_data

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        # Log unexpected errors
        if logger:
            logger.logger.error(
                f"Unexpected error in resume_review: {e}", exc_info=True
            )

        # Append failure to audit
        try:
            failure_record = audit_record.copy()
            failure_record["error"] = str(e)
            failure_record["status"] = "failed"
            _append_audit_record(failure_record)
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Resume operation failed: {str(e)}",
        )

    finally:
        # Always release lock
        _release_lock(payload.request_id)
