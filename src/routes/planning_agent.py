"""
Planning Agent Routes

FastAPI endpoints for document upload, feasibility checking, and plan generation.
All business logic is delegated to handler modules for maintainability.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import time

from src.core.session_storage import sessions

# Import handlers
from src.routes.upload_handler import UploadHandler
from src.routes.feasibility_handler import FeasibilityHandler
from src.routes.plan_generation_handler import PlanGenerationHandler

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
    development_context: Optional[Dict[str, str]] = Field(None, description="Development process information from user (methodology, team size, timeline, etc.)")


class FeasibilityReviewRequest(BaseModel):
    session_id: str = Field(..., description="Session ID from upload response")
    approved: bool = Field(..., description="True to approve report, False to request changes")
    feedback: Optional[str] = Field(None, description="Required when approved=False. Specific feedback for revision.")


class GeneratePlanRequest(BaseModel):
    session_id: str = Field(..., description="Session ID from upload response")
    use_intelligent_processing: bool = Field(True, description="Use Document Intelligence Pipeline for processing")
    max_iterations: int = Field(5, description="Maximum number of reflection iterations (default: 5)", ge=1, le=10)


class GeneratePlanResponse(BaseModel):
    session_id: str
    plan: Dict[str, Any]
    evidence: Dict[str, Any]
    result: str
    file_path: Optional[str] = Field(None, description="Path to the saved final project plan markdown file")
    steps: List[str]
    execution_time: float
    iterations_completed: int = Field(description="Number of reflection iterations completed")
    status: str = Field(description="Status of plan generation (completed/partial)")


# ============================================================================
# Endpoint 1: Upload Documents (Creates Session)
# ============================================================================

@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    use_default_files: bool = False,
    files: Optional[List[UploadFile]] = File(None, description="PDF files to upload (max 15 files)")
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
    result = await handler.handle_upload(use_default_files=use_default_files, files=files)
    
    return UploadResponse(
        session_id=result["session_id"],
        message=result["message"],
        uploaded_files=result["uploaded_files"],
        total_files=result["total_files"],
        status=result["status"]
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
            status_code=404,
            detail="Session not found. Please upload documents first."
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
            status_code=404,
            detail="Session not found. Please upload documents first."
        )
    
    if session.is_expired():
        print(f"Session expired: {request.session_id}")
        raise HTTPException(
            status_code=410,
            detail="Session expired. Please upload documents again."
        )
    
    # CRITICAL: Validate that all processing is complete before feasibility generation
    if session.processing_status != "completed":
        print(f"Processing not complete for session {request.session_id}: status={session.processing_status}")
        
        if session.processing_status == "processing":
            raise HTTPException(
                status_code=425,  # Too Early
                detail=(
                    "Document processing is still in progress. "
                    "Please wait for parsing and JSON conversion to complete. "
                    "Use /upload-status/{session_id} to check progress."
                )
            )
        elif session.processing_status == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"Document processing failed: {session.processing_error or 'Unknown error'}"
            )
        else:  # pending or other status
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Document processing has not started or is in invalid state: {session.processing_status}. "
                    "Please upload documents first."
                )
            )
    
    # Validate required session data is present
    # Check both parsed_documents and parsed_documents_dir for backwards compatibility
    if not session.parsed_documents and not session.parsed_documents_dir:
        print(f"Session {request.session_id} marked complete but missing required data")
        print(f"  - parsed_documents: {session.parsed_documents}")
        print(f"  - parsed_documents_dir: {session.parsed_documents_dir}")
        raise HTTPException(
            status_code=500,
            detail="Session processing incomplete: missing parsed documents. Please re-upload documents."
        )
    
    print(f"✅ All processing complete for session {request.session_id}, proceeding with feasibility generation")
    
    # Delegate to handler
    handler = FeasibilityHandler(verbose=False)
    result = handler.generate_feasibility(
        session=session,
        development_context=request.development_context
    )
    
    return result


# ============================================================================
# Endpoint 2a: Start Feasibility with HITL (New)
# ============================================================================

@router.post("/feasibility/start")
async def start_feasibility(request: FeasibilityRequest):
    """
    Start feasibility assessment with human-in-the-loop support.
    
    Generates initial feasibility report and pauses for human review.
    Supports iterative revision based on feedback.
    
    Workflow:
    1. Call /feasibility/start to generate initial report
    2. Call /feasibility/review with approval or feedback
    3. If feedback provided, report is revised and awaits review again
    4. Repeat until approved or max iterations reached
    
    Returns:
        - status: "awaiting_human" (waiting for review)
        - iteration: Current iteration number (0 = initial)
        - feasibility_report: Generated report content
        - message: Next steps
    """
    # Get session
    session = sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.is_expired():
        raise HTTPException(status_code=410, detail="Session expired")
    
    # Validate processing complete
    if session.processing_status != "completed":
        if session.processing_status == "processing":
            raise HTTPException(
                status_code=425,
                detail="Document processing still in progress. Use /upload-status/{session_id} to check."
            )
        elif session.processing_status == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"Document processing failed: {session.processing_error or 'Unknown error'}"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid processing state: {session.processing_status}"
            )
    
    if not session.parsed_documents and not session.parsed_documents_dir:
        raise HTTPException(
            status_code=500,
            detail="Missing parsed documents. Please re-upload."
        )
    
    # Delegate to handler
    handler = FeasibilityHandler(verbose=False)
    result = handler.start_feasibility(
        session=session,
        development_context=request.development_context
    )
    
    return result


@router.post("/feasibility/review")
async def review_feasibility(request: FeasibilityReviewRequest):
    """
    Submit human review decision for feasibility report.
    
    Args:
        - approved: True to approve and complete workflow, False to request changes
        - feedback: Required when approved=False. Specific feedback for improvements.
    
    Returns:
        - If approved: status="approved", workflow complete
        - If changes requested: status="awaiting_human", new iteration with revised report
        - If max iterations reached: status="max_iterations_reached"
    
    Example feedback:
        "The technical stack section needs more detail on database choices. 
         Also, the timeline seems too optimistic for a team of 3 developers."
    """
    # Get session
    session = sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.is_expired():
        raise HTTPException(status_code=410, detail="Session expired")
    
    # Delegate to handler
    handler = FeasibilityHandler(verbose=False)
    result = handler.review_feasibility(
        session=session,
        approved=request.approved,
        feedback=request.feedback
    )
    
    return result


@router.get("/feasibility/status/{session_id}")
async def get_feasibility_status(session_id: str):
    """
    Get current status of feasibility assessment workflow.
    
    Returns:
        - status: Current workflow state (not_started/generating/awaiting_human/approved/max_iterations_reached)
        - iteration: Current iteration number
        - max_iterations: Maximum allowed iterations
        - feasibility_report: Current report content
        - critique: Critique from last feedback (if available)
        - revision_history_count: Number of revisions completed
    """
    # Get session
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.is_expired():
        raise HTTPException(status_code=410, detail="Session expired")
    
    # Delegate to handler
    handler = FeasibilityHandler(verbose=False)
    result = handler.get_feasibility_status(session=session)
    
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
            status_code=404,
            detail="Session not found. Please upload documents first."
        )
    
    if session.is_expired():
        print(f"Session expired: {request.session_id}")
        raise HTTPException(
            status_code=410,
            detail="Session expired. Please upload documents again."
        )
    
    # CRITICAL: Validate that all processing is complete before plan generation
    if session.processing_status != "completed":
        print(f"Processing not complete for session {request.session_id}: status={session.processing_status}")
        
        if session.processing_status == "processing":
            raise HTTPException(
                status_code=425,  # Too Early
                detail=(
                    "Document processing is still in progress. "
                    "Please wait for parsing and JSON conversion to complete. "
                    "Use /upload-status/{session_id} to check progress."
                )
            )
        elif session.processing_status == "failed":
            raise HTTPException(
                status_code=500,
                detail=f"Document processing failed: {session.processing_error or 'Unknown error'}"
            )
        else:  # pending or other status
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Document processing has not started or is in invalid state: {session.processing_status}. "
                    "Please upload documents first."
                )
            )
    
    # Validate required session data is present
    # Check both parsed_documents and parsed_documents_dir for backwards compatibility
    if not session.parsed_documents and not session.parsed_documents_dir:
        print(f"Session {request.session_id} marked complete but missing required data")
        print(f"  - parsed_documents: {session.parsed_documents}")
        print(f"  - parsed_documents_dir: {session.parsed_documents_dir}")
        raise HTTPException(
            status_code=500,
            detail="Session processing incomplete: missing parsed documents. Please re-upload documents."
        )
    
    print(f"✅ All processing complete for session {request.session_id}, proceeding with plan generation")
    
    # Delegate to handler
    handler = PlanGenerationHandler(verbose=False)
    result = handler.generate_plan(
        session=session,
        max_iterations=request.max_iterations
    )
    
    return GeneratePlanResponse(
        session_id=result["session_id"],
        plan=result["plan"],
        evidence=result["evidence"],
        result=result["result"],
        file_path=result["file_path"],
        steps=result["steps"],
        execution_time=result["execution_time"],
        iterations_completed=result["iterations_completed"],
        status=result["status"]
    )
