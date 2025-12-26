"""
Planning Agent Routes

FastAPI endpoints for document upload, feasibility checking, and plan generation.
All business logic is delegated to handler modules for maintainability.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.core.session_storage import sessions
from src.routes.feasibility_handler import FeasibilityHandler
from src.routes.plan_generation_handler import PlanGenerationHandler

# Import handlers
from src.routes.upload_handler import UploadHandler

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class UploadResponse(BaseModel):
    session_id: str
    message: str
    uploaded_files: List[str]
    total_files: int
    status: str


class FeasibilityRequest(BaseModel):
    session_id: str = Field(..., description="Session ID from upload response")
    development_context: Optional[Dict[str, str]] = Field(
        None,
        description="Development process information from user (methodology, team size, timeline, etc.)",
    )


class GeneratePlanRequest(BaseModel):
    session_id: str = Field(..., description="Session ID from upload response")
    use_intelligent_processing: bool = Field(
        True, description="Use Document Intelligence Pipeline for processing"
    )
    max_iterations: int = Field(
        5,
        description="Maximum number of reflection iterations (default: 5)",
        ge=1,
        le=10,
    )
    enable_hitl: bool = Field(
        False, description="Enable Human-in-the-Loop mode with review interrupts"
    )


class GeneratePlanResponse(BaseModel):
    session_id: str
    plan: Optional[Dict[str, Any]] = Field(
        None, description="Plan object (None if pending review)"
    )
    evidence: Optional[Dict[str, Any]] = Field(
        None, description="Evidence object (None if pending review)"
    )
    result: Optional[str] = Field(
        None, description="Final plan text (None if pending review)"
    )
    file_path: Optional[str] = Field(
        None, description="Path to the saved final project plan markdown file"
    )
    steps: List[str] = Field(default_factory=list)
    execution_time: float = Field(default=0.0)
    iterations_completed: Optional[int] = Field(
        None, description="Number of reflection iterations completed"
    )
    status: str = Field(description="Status: completed, pending_review, or error")
    # HITL-specific fields
    review_type: Optional[str] = Field(
        None, description="Type of pending review: draft_review or reflection_review"
    )
    request_id: Optional[str] = Field(
        None,
        description="Request ID for pending review (use with /pending-review/{request_id})",
    )
    thread_id: Optional[str] = Field(None, description="Thread ID for checkpointing")
    message: Optional[str] = Field(None, description="Status message")


# ============================================================================
# Endpoint 1: Upload Documents (Creates Session)
# ============================================================================


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    use_default_files: bool = False,
    files: Optional[List[UploadFile]] = File(
        None, description="PDF files to upload (max 15 files)"
    ),
):
    """
    Upload PDF documents and create a session.
    Returns a session_id to use for subsequent requests.

    Options:
    1. Set use_default_files=true to automatically use all PDFs from the data/files/ directory
    2. Upload your own files (if use_default_files=false)

    No need to manage file paths - just use the session_id!

    Note: Processing happens in background. Use /upload-status/{session_id} to check progress.
    """
    handler = UploadHandler(verbose=False)
    result = await handler.handle_upload(
        use_default_files=use_default_files, files=files
    )

    return UploadResponse(
        session_id=result["session_id"],
        message=result["message"],
        uploaded_files=result["uploaded_files"],
        total_files=result["total_files"],
        status=result["status"],
    )


@router.get("/upload-status/{session_id}")
async def check_upload_status(session_id: str):
    """
    Check the processing status of uploaded documents.

    Returns:
        - status: pending/processing/completed/failed
        - message: Status message with details
        - parsed_documents: Number of documents parsed (if completed)
    """
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404, detail="Session not found. Please upload documents first."
        )

    response = {
        "session_id": session_id,
        "status": session.processing_status,
        "message": session.status_message,
        "created_at": session.created_at.isoformat(),
    }

    # Add detailed info if processing is completed
    if session.processing_status == "completed" and session.parsed_documents:
        response["parsed_documents"] = len(session.parsed_documents)

    # Add error details if processing failed
    if session.processing_status == "failed" and session.processing_error:
        response["error"] = session.processing_error

    return response


# ============================================================================
# Endpoint 2: Feasibility Check
# ============================================================================


@router.post("/feasibility")
async def check_feasibility(request: FeasibilityRequest):
    """
    Generate feasibility assessment using LLM based on uploaded documents.
    Just provide the session_id from upload - no file paths needed!
    Returns the feasibility assessment in markdown format.

    IMPORTANT: This endpoint requires that document processing (parsing and JSON conversion)
    is fully complete before feasibility generation can proceed.
    """
    # Get session
    session = sessions.get(request.session_id)
    if not session:
        print(f"Session not found: {request.session_id}")
        raise HTTPException(
            status_code=404, detail="Session not found. Please upload documents first."
        )

    if session.is_expired():
        print(f"Session expired: {request.session_id}")
        raise HTTPException(
            status_code=410, detail="Session expired. Please upload documents again."
        )

    # CRITICAL: Validate that all processing is complete before feasibility generation
    if session.processing_status != "completed":
        print(
            f"Processing not complete for session {request.session_id}: status={session.processing_status}"
        )

        if session.processing_status == "processing":
            raise HTTPException(
                status_code=425,  # Too Early
                detail=(
                    "Document processing is still in progress. "
                    "Please wait for parsing and JSON conversion to complete. "
                    "Use /upload-status/{session_id} to check progress."
                ),
            )
        elif session.processing_status == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"Document processing failed: {session.processing_error or 'Unknown error'}",
            )
        else:  # pending or other status
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Document processing has not started or is in invalid state: {session.processing_status}. "
                    "Please upload documents first."
                ),
            )

    # Validate required session data is present
    # Check both parsed_documents and parsed_documents_dir for backwards compatibility
    if not session.parsed_documents and not session.parsed_documents_dir:
        print(f"Session {request.session_id} marked complete but missing required data")
        print(f"  - parsed_documents: {session.parsed_documents}")
        print(f"  - parsed_documents_dir: {session.parsed_documents_dir}")
        raise HTTPException(
            status_code=500,
            detail="Session processing incomplete: missing parsed documents. Please re-upload documents.",
        )

    print(
        f"✅ All processing complete for session {request.session_id}, proceeding with feasibility generation"
    )

    # Delegate to handler
    handler = FeasibilityHandler(verbose=False)
    result = handler.generate_feasibility(
        session=session, development_context=request.development_context
    )

    return result


# ============================================================================
# Endpoint 3: Generate Full Plan
# ============================================================================


@router.post("/generate-plan", response_model=GeneratePlanResponse)
async def generate_plan(request: GeneratePlanRequest):
    """
    Generate a complete project plan based on the uploaded documents.
    Just provide the session_id - the system remembers your documents!

    IMPORTANT: This endpoint requires that document processing (parsing and JSON conversion)
    is fully complete before plan generation can proceed.
    """
    # Get session
    session = sessions.get(request.session_id)
    if not session:
        print(f"Session not found: {request.session_id}")
        raise HTTPException(
            status_code=404, detail="Session not found. Please upload documents first."
        )

    if session.is_expired():
        print(f"Session expired: {request.session_id}")
        raise HTTPException(
            status_code=410, detail="Session expired. Please upload documents again."
        )

    # CRITICAL: Validate that all processing is complete before plan generation
    if session.processing_status != "completed":
        print(
            f"Processing not complete for session {request.session_id}: status={session.processing_status}"
        )

        if session.processing_status == "processing":
            raise HTTPException(
                status_code=425,  # Too Early
                detail=(
                    "Document processing is still in progress. "
                    "Please wait for parsing and JSON conversion to complete. "
                    "Use /upload-status/{session_id} to check progress."
                ),
            )
        elif session.processing_status == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"Document processing failed: {session.processing_error or 'Unknown error'}",
            )
        else:  # pending or other status
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Document processing has not started or is in invalid state: {session.processing_status}. "
                    "Please upload documents first."
                ),
            )

    # Validate required session data is present
    # Check both parsed_documents and parsed_documents_dir for backwards compatibility
    if not session.parsed_documents and not session.parsed_documents_dir:
        print(f"Session {request.session_id} marked complete but missing required data")
        print(f"  - parsed_documents: {session.parsed_documents}")
        print(f"  - parsed_documents_dir: {session.parsed_documents_dir}")
        raise HTTPException(
            status_code=500,
            detail="Session processing incomplete: missing parsed documents. Please re-upload documents.",
        )

    print(
        f"✅ All processing complete for session {request.session_id}, proceeding with plan generation"
    )

    # Delegate to handler
    handler = PlanGenerationHandler(verbose=False)
    result = handler.generate_plan(
        session=session,
        max_iterations=request.max_iterations,
        enable_hitl=request.enable_hitl,
    )

    # Build response based on status
    if result.get("status") == "pending_review":
        # HITL mode: waiting for human review
        return GeneratePlanResponse(
            session_id=result["session_id"],
            status=result["status"],
            review_type=result.get("review_type"),
            request_id=result.get("request_id"),
            thread_id=result.get("thread_id"),
            message=result.get("message"),
            execution_time=result.get("execution_time", 0.0),
            iterations_completed=result.get("iteration"),
        )
    else:
        # Completed (either HITL or non-HITL)
        return GeneratePlanResponse(
            session_id=result["session_id"],
            plan=result.get("plan"),
            evidence=result.get("evidence"),
            result=result.get("result"),
            file_path=result.get("file_path"),
            steps=result.get("steps", []),
            execution_time=result.get("execution_time", 0.0),
            iterations_completed=result.get("iterations_completed"),
            status=result["status"],
        )
