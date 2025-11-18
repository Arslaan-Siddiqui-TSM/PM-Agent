"""
FastAPI endpoints for Human-In-The-Loop review and resume functionality.

Provides:
- GET /pending-review/{request_id}: Fetch pending review data
- POST /resume-review: Resume graph execution with human input
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel, Field, validator

from src.utils.helper import get_global_logger
from src.services.graph_runner import get_graph_runner

router = APIRouter()

# Get HITL secret from environment (for local dev, default to 'changeme')
HITL_SECRET = os.getenv("HITL_SECRET", "changeme")

# Paths
PENDING_REVIEWS_DIR = Path("output/pending_reviews")
AUDIT_LOG_PATH = Path("output/review_audit.jsonl")


# ═══════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════

class ReviewPayload(BaseModel):
    """Request payload for resuming a review."""
    request_id: str = Field(..., description="UUID of the review request")
    action: str = Field(..., description="'approve' or 'feedback'")
    feedback_text: Optional[str] = Field(None, description="Reviewer feedback text")
    edited_text: Optional[str] = Field(None, description="Edited draft text")
    tags: Optional[List[str]] = Field(default_factory=list, description="Review tags")
    reviewer_id: Optional[str] = Field(None, description="Reviewer identifier")
    
    @validator("action")
    def validate_action(cls, v):
        if v not in ["approve", "feedback"]:
            raise ValueError("action must be 'approve' or 'feedback'")
        return v
    
    @validator("edited_text")
    def validate_edited_text_length(cls, v):
        if v and len(v) > 50_000:
            raise ValueError("edited_text must be ≤ 50,000 characters")
        return v


class PendingReviewResponse(BaseModel):
    """Response model for pending review data."""
    type: str
    node: str
    request_id: str
    iteration: int
    model_output: str
    reflection_notes: str
    metadata: dict


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
            logger.logger.info(f"Audit: Appended record for request_id={audit_data.get('request_id')}")
    
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
    description="Fetch the interrupt payload for a pending review by request_id"
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
            detail=f"Pending review not found for request_id: {request_id}"
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
            detail=f"Error reading pending review: {str(e)}"
        )


@router.post(
    "/resume-review",
    summary="Resume graph execution with human review",
    description="Submit reviewer decision and resume the LangGraph execution"
)
async def resume_review(
    payload: ReviewPayload,
    authorization: Optional[str] = Header(None)
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
            logger.logger.warning(f"Unauthorized resume attempt for {payload.request_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Authorization header"
        )
    
    # ═══════════════════════════════════════════════════════════
    # 2. CHECK PENDING FILE EXISTS
    # ═══════════════════════════════════════════════════════════
    pending_file = PENDING_REVIEWS_DIR / f"{payload.request_id}.json"
    
    if not pending_file.exists():
        if logger:
            logger.logger.warning(f"Resume attempted but pending file not found: {payload.request_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending review not found for request_id: {payload.request_id}"
        )
    
    # ═══════════════════════════════════════════════════════════
    # 3. ACQUIRE LOCK
    # ═══════════════════════════════════════════════════════════
    if not _acquire_lock(payload.request_id):
        if logger:
            logger.logger.warning(f"Resume lock already held for {payload.request_id}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resume already in progress for this request_id"
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
            
            model_output_snapshot = pending_data.get("model_output", "")
        
        except Exception as e:
            if logger:
                logger.logger.error(f"Error reading pending file for audit: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error reading pending review file: {str(e)}"
            )
        
        # ═══════════════════════════════════════════════════════
        # 5. BUILD AUDIT RECORD
        # ═══════════════════════════════════════════════════════
        audit_record = {
            "request_id": payload.request_id,
            "iteration": pending_data.get("iteration"),
            "action": payload.action,
            "feedback_text": payload.feedback_text,
            "edited_text": payload.edited_text,
            "tags": payload.tags or [],
            "reviewer_id": payload.reviewer_id,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "model_output_snapshot": model_output_snapshot,
        }
        
        # Append audit log
        try:
            _append_audit_record(audit_record)
        except Exception as e:
            if logger:
                logger.logger.error(f"Failed to append audit log: {e}")
            # Don't fail the request if audit fails, but log it
        
        # ═══════════════════════════════════════════════════════
        # 6. CALL LANGGRAPH RESUME
        # ═══════════════════════════════════════════════════════
        # Build the human_input dict that will be passed to Command(resume=...)
        human_input = {
            "request_id": payload.request_id,  # REQUIRED by graph
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
                logger.logger.error(f"No thread_id in pending file for {payload.request_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Pending review missing thread_id. Cannot resume execution."
            )
        
        # Log payload and pending data for diagnostics
        if logger:
            logger.logger.info(f"Resume request received: payload.request_id={payload.request_id}, action={payload.action}, reviewer={payload.reviewer_id}")
            logger.logger.info(f"Pending file data - request_id: {pending_data.get('request_id')}, thread_id: {pending_data.get('thread_id')}, iteration: {pending_data.get('iteration')}")
            logger.logger.debug(f"Pending file snapshot for {payload.request_id}: {json.dumps(pending_data, ensure_ascii=False)[:1000]}")
            logger.logger.debug(f"Human input to be passed: {json.dumps(human_input, ensure_ascii=False)}")

        # Get the singleton GraphRunner instance
        try:
            graph_runner = get_graph_runner()
        except Exception as e:
            if logger:
                logger.logger.error(f"Failed to get GraphRunner: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize graph runner: {str(e)}"
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
                request_id=payload.request_id
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
                detail=f"Graph resume operation failed: {str(e)}"
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
        
        # If the graph interrupted again (e.g., for iteration 2), include the new request_id
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
                response_data["interrupted_again"] = True
                response_data["new_request_id"] = result.get("request_id")
                
                if logger:
                    logger.logger.info(
                        f"HITL: Graph interrupted again for next iteration\n"
                        f"  old_request_id={payload.request_id}\n"
                        f"  new_request_id={result.get('request_id')}"
                    )
            else:
                # Graph completed (final_plan was set)
                response_data["interrupted_again"] = False
                response_data["completed"] = True
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
            logger.logger.error(f"Unexpected error in resume_review: {e}", exc_info=True)
        
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
            detail=f"Resume operation failed: {str(e)}"
        )
    
    finally:
        # Always release lock
        _release_lock(payload.request_id)
