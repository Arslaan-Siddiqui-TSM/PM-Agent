from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pathlib import Path
import os

from src.core.session_storage import sessions
from src.utils.constants import UPLOAD_DIR

router = APIRouter()


# Get supported document types
@router.get("/document-types")
async def get_document_types():
    """Return list of supported document types"""
    return {
        "supported_types": [
            "functional_specification",
            "technical_specification",
            "user_stories",
            "api_documentation",
            "architecture_design",
            "requirements_document",
            "other"
        ]
    }


# Get session info
@router.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a session"""
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )
    
    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "total_documents": len(session.document_paths),
        "has_development_context": session.development_context is not None,
        "development_context": session.development_context,
        "has_feasibility_assessment": session.feasibility_assessment is not None,
        "feasibility_file_path": session.feasibility_file_path,
        "has_pipeline_results": session.pipeline_result is not None,
        "use_intelligent_processing": session.use_intelligent_processing,
        "is_expired": session.is_expired()
    }


# Delete session
@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its uploaded files"""
    print(f"Delete session requested: {session_id}")
    
    session = sessions.get(session_id)
    if not session:
        # 1a829677-f3b3-4949-ba38-64e53fd58246
        print(f"Session not found for deletion: {session_id}")
        print(f"Current Sessions: {sessions}")
        try:
            # Clean up orphaned files for this session
            for file in os.listdir(str(UPLOAD_DIR)):
                if file.startswith(session_id):
                    os.remove(os.path.join(str(UPLOAD_DIR), file))
                    print(f"Deleted file: {file}")
        except Exception as e:
            print(f"Warning: Could not clean up files: {e}")
        raise HTTPException(
            status_code=404,
            detail="Session not found"
        )
    
    # Delete uploaded files
    for doc_path in session.document_paths:
        file_path = Path(doc_path)
        if file_path.exists():
            file_path.unlink()
            print(f"Deleted file: {file_path}")
    
    # Remove session
    del sessions[session_id]
    print(f"Session {session_id} deleted successfully")
    
    return {"message": f"Session {session_id} deleted successfully"}


# Get file content
@router.get("/file-content", response_class=PlainTextResponse)
async def get_file_content(file_path: str = Query(..., description="Path to the file to read")):
    """Read and return the content of a file (e.g., feasibility assessment or project plan)"""
    try:
        path = Path(file_path)
        
        # Security check: ensure the file is within allowed directories
        allowed_dirs = [
            Path("output").resolve(),  # Session output files
            Path("outputs").resolve(),
            Path("uploads").resolve(),
            Path("data").resolve(),  # Hardcoded files
        ]
        file_resolved = path.resolve()
        
        # Check if file is within any allowed directory
        is_allowed = False
        for allowed_dir in allowed_dirs:
            try:
                file_resolved.relative_to(allowed_dir)
                is_allowed = True
                break
            except ValueError:
                continue
        
        if not is_allowed:
            raise HTTPException(
                status_code=403,
                detail="Access to this file is not allowed"
            )
        
        if not path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {file_path}"
            )
        
        # Read and return file content
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading file: {str(e)}"
        )


# Get upload/processing status (for frontend polling)
@router.get("/upload-status/{session_id}")
async def get_upload_status(session_id: str):
    """
    Get the upload and processing status for a session.
    Used by frontend for polling during async document processing.
    
    Returns:
        - status: "processing" | "completed" | "failed"
        - message: Human-readable status message
        - parsed_documents: Number of documents parsed (if available)
    """
    # Debug logging
    print(f"[DEBUG] Status check for session: {session_id}")
    print(f"[DEBUG] Available sessions: {list(sessions.keys())}")
    
    session = sessions.get(session_id)
    if not session:
        print(f"[DEBUG] Session {session_id} not found!")
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please upload documents first."
        )
    
    # Get status from session
    status = session.processing_status or "unknown"
    message = session.status_message or "Processing..."
    
    # Build response
    response = {
        "status": status,
        "message": message,
        "session_id": session_id,
    }
    
    # Add optional details if available
    if session.parsed_documents:
        response["parsed_documents"] = len(session.parsed_documents)
    
    return response