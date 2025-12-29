"""
Planning Agent Routes

FastAPI endpoints for document upload, feasibility checking, and plan generation.
All business logic is delegated to handler modules for maintainability.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from src.core.session_storage import sessions
from src.utils.token_utils import get_session_stats, reset_tracker

# Import handlers
from src.routes.upload_handler import UploadHandler
from src.routes.feasibility_handler import FeasibilityHandler
from src.routes.feasibility_revision_handler import FeasibilityRevisionHandler
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


class ReviseReportRequest(BaseModel):
    session_id: str = Field(..., description="Session ID from upload response")
    current_version: int = Field(..., description="Version being critiqued (1, 2, 3...)", ge=1)
    human_critique: Optional[str] = Field(None, description="Free-form user feedback on the report; optional on initial HITL start")
    revision_instructions: Optional[str] = Field(None, description="Optional structured guidance for revisions")
    max_revisions: int = Field(5, description="Maximum allowed revisions (default: 5)", ge=2, le=10)


class ReviseReportResponse(BaseModel):
    session_id: str
    current_version: Optional[int] = Field(None, description="Version critiqued or paused")
    new_version: Optional[int] = Field(None, description="New version after revision if completed")
    message: Optional[str] = Field(None, description="Status message")
    file_path: Optional[str] = Field(None, description="Path to revised report if completed")
    execution_time: Optional[float] = Field(None, description="Execution time for this revision step")
    status: Optional[str] = Field(None, description="Status of the revision request: interrupt|completed")
    resume_config: Optional[Dict[str, Any]] = Field(None, description="LangGraph resume config for interrupted workflows")
    token_usage: Optional[Dict[str, Any]] = Field(None, description="Token usage statistics for the revision")


class RevisionHistoryResponse(BaseModel):
    session_id: str
    revisions: List[Dict[str, Any]]


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

    # Check if hardcoded feasibility should be used (for testing/development)
    from pathlib import Path
    import os

    use_hardcoded = os.getenv("USE_HARDCODED_FEASIBILITY", "false").lower() == "true"

    if use_hardcoded:
        print("⚠️  Using HARDCODED feasibility report (USE_HARDCODED_FEASIBILITY=true)")
        hardcoded_path = Path("data/hardcoded_feasibility.md")
        hardcoded_thinking_path = Path("data/hardcoded_thinking_summary.md")

        if hardcoded_path.exists():
            with open(hardcoded_path, 'r', encoding='utf-8') as f:
                hardcoded_content = f.read()

            # Save it to the expected location for consistency
            output_dir = Path(f"output/session_{session.session_id[:8]}/reports")
            output_dir.mkdir(parents=True, exist_ok=True)
            report_path = output_dir / "feasibility_report_v1.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(hardcoded_content)

            # Also save thinking summary if it exists
            thinking_content = None
            thinking_path = None
            if hardcoded_thinking_path.exists():
                with open(hardcoded_thinking_path, 'r', encoding='utf-8') as f:
                    thinking_content = f.read()
                thinking_path = output_dir / "thinking_summary_v1.md"
                with open(thinking_path, 'w', encoding='utf-8') as f:
                    f.write(thinking_content)

            print(f"✓ Hardcoded report saved to {report_path}")
            if thinking_path:
                print(f"✓ Thinking summary saved to {thinking_path}")

            # IMPORTANT: Set session properties so revisions can be requested later
            session.feasibility_assessment = hardcoded_content
            session.feasibility_file_path = str(report_path)
            session.feasibility_thinking_summary = thinking_content

            print(
                "✅ Session properties set - "
                f"feasibility_assessment={bool(session.feasibility_assessment)}, "
                f"feasibility_file_path={session.feasibility_file_path}"
            )

            return {
                "file_path": str(report_path),
                "development_context_json_path": None,
                "message": "Hardcoded feasibility report loaded (testing mode)",
            }
        else:
            print(f"❌ Hardcoded feasibility file not found at {hardcoded_path}")
            raise HTTPException(
                status_code=500,
                detail=f"Hardcoded feasibility file not found at {hardcoded_path}",
            )

    # Delegate to handler for real LLM generation
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

# ============================================================================
# Endpoint 4: Revise Feasibility Report (HITL)
# ============================================================================

@router.post("/revise-feasibility", response_model=ReviseReportResponse)
async def revise_feasibility(request: ReviseReportRequest):
    """
    Revise an existing feasibility report based on human critique.
    
    Human-in-the-Loop (HITL) workflow using LangGraph:
    - Accepts user feedback on feasibility report
    - Generates an improved version without re-running initial analysis
    - Preserves feasibility verdict and core findings
    - Supports up to 5 versions per session (v1 → v2 → v3 → v4 → v5)
    
    Uses LangGraph's interrupt-resume pattern for robust workflow management.
    
    No re-ingestion or re-analysis required. Just provide:
    - session_id: your existing session
    - current_version: version being critiqued (1, 2, 3...)
    - human_critique: your feedback (free-form text)
    
    IMPORTANT: You must have already completed initial feasibility generation
    (/feasibility endpoint) before requesting revisions.
    """
    from src.core.langgraph_hitl import create_hitl_system
    from src.config.llm_config import session_tracker
    
    # Reset token tracker for this revision request
    reset_tracker()
    revision_start_time = time.time()
    
    # Get session
    session = sessions.get(request.session_id)
    if not session:
        print(f"Session not found: {request.session_id}")
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please upload documents and generate initial feasibility assessment first."
        )
    
    if session.is_expired():
        print(f"Session expired: {request.session_id}")
        raise HTTPException(
            status_code=410,
            detail="Session expired. Please start over by uploading documents."
        )
    
    # Validate that initial feasibility assessment exists
    if not session.feasibility_assessment or not session.feasibility_file_path:
        print(f"❌ Initial feasibility assessment not found for session {request.session_id}")
        print(f"  - session.feasibility_assessment: {bool(session.feasibility_assessment)}")
        print(f"  - session.feasibility_file_path: {session.feasibility_file_path}")
        raise HTTPException(
            status_code=400,
            detail=(
                "Initial feasibility assessment not found. "
                "Please complete feasibility generation (/feasibility) before requesting revisions."
            )
        )
    
    print(f"✅ Initial feasibility assessment found, proceeding with LangGraph HITL revision")
    
    # Use LangGraph HITL system for revision
    hitl_system = create_hitl_system()
    
    # Prepare state for the graph
    state_dict = {
        "session_id": request.session_id,
        "current_version": request.current_version,
        "feasibility_assessment": session.feasibility_assessment,
        "thinking_summary": getattr(session, 'feasibility_thinking_summary', None),
        "human_critique": request.human_critique,
        "revision_instructions": request.revision_instructions,
        "revised_assessment": None,
        "revision_history": [],
        "max_revisions": request.max_revisions,
        "error": None
    }
    
    # Run the HITL workflow
    result = await hitl_system.run_revision_workflow(state_dict)
    
    if result.get("status") == "interrupt":
        revision_end_time = time.time()
        revision_execution_time = revision_end_time - revision_start_time
        return ReviseReportResponse(
            session_id=request.session_id,
            current_version=request.current_version,
            new_version=None,
            message="Awaiting human critique to resume revision",
            file_path=None,
            execution_time=revision_execution_time,
            status="interrupt",
            resume_config=result.get("resume_config"),
            token_usage=None,
        )

    if result.get("error"):
        print(f"❌ HITL workflow error: {result['error']}")
        raise HTTPException(
            status_code=500,
            detail=f"Revision workflow failed: {result['error']}"
        )
    
    # Update session with new version
    session.feasibility_assessment = result.get("feasibility_assessment")
    session.feasibility_file_path = f"output/session_{request.session_id[:8]}/reports/feasibility_report_v{result.get('current_version')}.md"
    
    revision_end_time = time.time()
    revision_execution_time = revision_end_time - revision_start_time
    
    print(f"✅ LangGraph HITL revision completed, new version: {result.get('current_version')}")
    
    # Capture token usage stats for revision
    token_stats = get_session_stats()
    
    print("\n" + "="*80)
    print("📊 HITL REVISION - TOKEN USAGE SUMMARY")
    print("="*80)
    print(f"Total LLM Calls:         {token_stats['total_calls']}")
    print(f"Total Input Tokens:      {token_stats['total_input_tokens']:,}")
    print(f"Total Output Tokens:     {token_stats['total_output_tokens']:,}")
    print(f"Total Tokens:            {token_stats['total_tokens']:,}")
    print(f"Execution Time:          {revision_execution_time:.2f}s")
    if token_stats['total_tokens'] > 0 and revision_execution_time > 0:
        print(f"Avg Speed:               {token_stats['total_tokens']/revision_execution_time:.2f} tok/s")
    
    # Cost estimation (NVIDIA pricing)
    input_cost = (token_stats['total_input_tokens'] / 1_000_000) * 0.02
    output_cost = (token_stats['total_output_tokens'] / 1_000_000) * 0.06
    total_cost = input_cost + output_cost
    print(f"Est. Cost (NVIDIA):      ${total_cost:.4f}")
    print("="*80 + "\n")
    
    # Save token report
    try:
        token_report_path = _save_revision_token_report(
            session_id=request.session_id,
            current_version=request.current_version,
            new_version=result.get('current_version'),
            token_stats=token_stats,
            execution_time=revision_execution_time
        )
        print(f"✅ Token usage report saved: {token_report_path}\n")
    except Exception as e:
        print(f"⚠️  Warning: Failed to save token report: {e}\n")
    
    return ReviseReportResponse(
        session_id=request.session_id,
        current_version=request.current_version,
        new_version=result["current_version"],
        message=f"Feasibility report revised based on human feedback - now at v{result['current_version']}",
        file_path=session.feasibility_file_path,
        execution_time=revision_execution_time,
        token_usage=token_stats  # Include token stats in response
    )


# ============================================================================
# Endpoint 5: Get Revision History
# ============================================================================

@router.get("/revision-history/{session_id}", response_model=RevisionHistoryResponse)
async def get_revision_history(session_id: str):
    """
    Get the revision history for a session.
    
    Returns all versions of the feasibility report by scanning the output directory
    and reading the revision metadata from saved files.
    
    Returns:
        - session_id: The session ID
        - revisions: List of revision entries with version, timestamp, file paths, etc.
    """
    from pathlib import Path
    import os
    
    # Validate session exists
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found."
        )
    
    # Get revision history from disk
    revisions = []
    
    # Look for all feasibility report versions in the session output directory
    session_prefix = session_id[:8]
    reports_dir = Path(f"output/session_{session_prefix}/reports")
    
    if reports_dir.exists():
        # Find all feasibility_report_v*.md files
        report_files = sorted(reports_dir.glob("feasibility_report_v*.md"))
        
        for i, report_file in enumerate(report_files):
            version_num = int(report_file.stem.split('v')[1])
            
            # Get file modification time
            mod_time = os.path.getmtime(report_file)
            from datetime import datetime as dt
            created_at = dt.fromtimestamp(mod_time).isoformat()
            
            # Determine revision type
            revision_type = "initial" if version_num == 1 else "human_revision"
            
            revisions.append({
                "version": version_num,
                "created_at": created_at,
                "type": revision_type,
                "file_path": str(report_file)
            })
    
    if not revisions and session.feasibility_assessment:
        # If no files found but session has assessment, it hasn't been saved yet
        revisions.append({
            "version": 1,
            "created_at": datetime.now().isoformat(),
            "type": "initial",
            "file_path": session.feasibility_file_path or "not yet saved"
        })
    
    print(f"✅ Found {len(revisions)} revisions for session {session_id}")
    
    return RevisionHistoryResponse(
        session_id=session_id,
        revisions=revisions
    )


# ============================================================================
# Helper: Save Revision Token Report
# ============================================================================

def _save_revision_token_report(
    session_id: str,
    current_version: int,
    new_version: int,
    token_stats: Dict[str, Any],
    execution_time: float
) -> Path:
    """Save token usage statistics for revision to JSON file."""
    from src.config.llm_config import session_tracker
    
    session_id_short = session_id[:8]
    output_dir = Path(f"output/session_{session_id_short}/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"token_stats_revision_v{current_version}_to_v{new_version}_{timestamp}.json"
    
    payload = {
        "session_id": session_id,
        "phase": "HITL_REVISION",
        "revision": {
            "from_version": current_version,
            "to_version": new_version
        },
        "created_at": datetime.now().isoformat(),
        "summary": {
            "total_calls": token_stats.get('total_calls', 0),
            "total_input_tokens": token_stats.get('total_input_tokens', 0),
            "total_output_tokens": token_stats.get('total_output_tokens', 0),
            "total_tokens": token_stats.get('total_tokens', 0),
            "execution_time_seconds": execution_time,
            "session_duration_seconds": token_stats.get('session_duration', 0)
        },
        "cost_estimate": {
            "provider": "NVIDIA",
            "input_cost": round((token_stats.get('total_input_tokens', 0) / 1_000_000) * 0.02, 4),
            "output_cost": round((token_stats.get('total_output_tokens', 0) / 1_000_000) * 0.06, 4),
            "total_cost_usd": round(
                (token_stats.get('total_input_tokens', 0) / 1_000_000) * 0.02 +
                (token_stats.get('total_output_tokens', 0) / 1_000_000) * 0.06,
                4
            )
        },
        "per_call_details": [
            {
                "call_index": i,
                "provider": call.get('provider', 'NVIDIA'),
                "model": call.get('model', 'unknown'),
                "input_tokens": call.get('input_tokens', 0),
                "output_tokens": call.get('output_tokens', 0),
                "total_tokens": call.get('total_tokens', 0),
                "duration_seconds": call.get('duration', 0),
                "tokens_per_second": call.get('tokens_per_sec', 0),
                "timestamp": call.get('timestamp', 0),
                "estimated": call.get('estimated', False)
            }
            for i, call in enumerate(session_tracker.calls)
        ]
    }
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    
    return report_path


# ============================================================================
# Endpoint 6: Get Revision History
# ============================================================================

@router.get("/current-feasibility-version/{session_id}")
async def get_current_feasibility_version(session_id: str):
    """
    Get the current version number of the feasibility report.
    
    Returns:
        - session_id: The session ID
        - current_version: Latest version number (1 if initial only, 2+ if revisions exist)
    """
    # Validate session exists
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found."
        )
    
    # Get current version
    handler = FeasibilityRevisionHandler(verbose=False)
    current_version = handler.get_current_feasibility_version(session_id)
    
    return {
        "session_id": session_id,
        "current_version": current_version
    }


