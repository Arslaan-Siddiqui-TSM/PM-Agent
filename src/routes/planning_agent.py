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


class GenerateDiagramsRequest(BaseModel):
    session_id: str = Field(..., description="Session ID from upload response")
    plan_text: str = Field(..., description="The project plan text to generate diagrams from")


class DiagramData(BaseModel):
    type: str
    title: str
    description: str
    url: str
    source_code: str


class GenerateDiagramsResponse(BaseModel):
    session_id: str
    diagrams: List[DiagramData]
    diagrams_count: int
    status: str


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


# ============================================================================
# Endpoint 4: Generate Diagrams from Plan
# ============================================================================

@router.post("/generate-diagrams", response_model=GenerateDiagramsResponse)
async def generate_diagrams(request: GenerateDiagramsRequest):
    """
    Generate visual diagrams from a project plan.
    
    This endpoint uses the DiagramGenerator agent to analyze the plan and create
    visual representations (Gantt charts, WBS diagrams, etc.) using direct rendering services.
    """
    # Get session
    session = sessions.get(request.session_id)
    if not session:
        print(f"Session not found: {request.session_id}")
        raise HTTPException(
            status_code=404,
            detail="Session not found."
        )
    
    if session.is_expired():
        print(f"Session expired: {request.session_id}")
        raise HTTPException(
            status_code=410,
            detail="Session expired."
        )
    
    print(f"Generating diagrams for session: {request.session_id}")
    
    try:
        # Import DiagramGenerator
        from src.agents.diagram_generator import DiagramGenerator
        
        # Initialize the diagram generator
        diagram_gen = DiagramGenerator()
        
        # Generate diagrams from plan
        diagrams = await diagram_gen.generate_all_diagrams(
            plan_text=request.plan_text,
            diagram_types=None,  # Auto-detect
            format="svg",
            include_failed=True  # Include failed diagrams with source code for debugging
        )
        
        # Close the HTTP client
        await diagram_gen.close()
        
        # Convert to response format
        diagram_data_list = [
            DiagramData(
                type=d.type,
                title=d.title,
                description=d.description,
                url=d.url,
                source_code=d.source_code
            )
            for d in diagrams
        ]
        
        success_count = len(diagram_data_list)
        print(f"Successfully generated {success_count} diagrams")
        
        # Add a warning if no diagrams were generated
        status = "completed"
        if success_count == 0:
            status = "completed_with_errors"
            print("WARNING: No diagrams were successfully generated. This may be due to rendering service issues.")
        
        return GenerateDiagramsResponse(
            session_id=request.session_id,
            diagrams=diagram_data_list,
            diagrams_count=success_count,
            status=status
        )
        
    except Exception as e:
        print(f"Error during diagram generation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Diagram generation failed: {str(e)}"
        )
