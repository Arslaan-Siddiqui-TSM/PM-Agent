"""
Feasibility Revision Handler

Orchestrates HITL revision workflow.
Loads artifacts, validates versions, delegates to revision module.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import time

from fastapi import HTTPException

from src.core.session import Session
from src.core.langgraph_hitl import create_hitl_system


class FeasibilityRevisionHandler:
    """
    Handles human-in-the-loop revision of feasibility reports.
    
    Workflow:
    1. Validate session and version exists
    2. Load current report (vN.md)
    3. Load thinking summary
    4. Invoke revision module
    5. Return revised report
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize revision handler.
        
        Args:
            verbose: Enable verbose console output
        """
        self.verbose = verbose
    
    def revise_feasibility(
        self,
        session: Session,
        current_version: int,
        human_critique: Optional[str] = None,
        revision_instructions: Optional[str] = None,
        max_revisions: int = 5
    ) -> dict:
        """
        Revise an existing feasibility report based on human critique.
        
        Args:
            session: Session object
            current_version: Version being critiqued (1, 2, 3...)
            human_critique: User feedback (free-form text)
            revision_instructions: Optional structured guidance
            max_revisions: Maximum allowed revisions (default: 5)
        
        Returns:
            Dictionary with session_id, new_version, file paths, execution_time
            
        Raises:
            HTTPException: If session invalid, version not found, or revision fails
        """
        print(f"Feasibility revision requested for session: {session.session_id}")
        print(f"  Current version: v{current_version}")
        print(f"  Max revisions: v{max_revisions}")
        start_time = time.time()
        
        try:
            # Step 1: Validate inputs
            print("Step 1: Validating inputs")
            
            if current_version < 1:
                raise ValueError(f"current_version must be ≥ 1, got {current_version}")
            
            # For interrupt-based HITL, critique may be missing on the initial call
            if human_critique is not None and not human_critique.strip():
                raise ValueError("human_critique cannot be empty")
            
            print("✓ Inputs validated")
            
            # Step 2: Load current feasibility report
            print(f"Step 2: Loading feasibility_report_v{current_version}.md")
            
            report_path = self._get_report_path(session.session_id, current_version)
            
            if not report_path.exists():
                raise FileNotFoundError(
                    f"Feasibility report version {current_version} not found at {report_path}. "
                    f"Please ensure the initial generation is complete."
                )
            
            with open(report_path, 'r', encoding='utf-8') as f:
                current_report = f.read()
            
            if not current_report or not current_report.strip():
                raise ValueError(f"Feasibility report v{current_version} is empty")
            
            print(f"✓ Loaded {report_path.name} ({len(current_report)} chars)")
            
            # Step 3: Load thinking summary
            print("Step 3: Loading thinking_summary.md")
            
            thinking_summary_path = self._get_thinking_summary_path(session.session_id)
            
            if not thinking_summary_path.exists():
                raise FileNotFoundError(
                    f"Thinking summary not found at {thinking_summary_path}. "
                    f"Please ensure the initial feasibility generation is complete."
                )
            
            with open(thinking_summary_path, 'r', encoding='utf-8') as f:
                thinking_summary = f.read()
            
            if not thinking_summary or not thinking_summary.strip():
                raise ValueError("Thinking summary is empty")
            
            print(f"✓ Loaded thinking_summary.md ({len(thinking_summary)} chars)")
            
            # Step 4: Invoke LangGraph HITL system (interrupt-aware)
            print("Step 4: Invoking LangGraph HITL system")
            hitl = create_hitl_system()

            state_dict = {
                "session_id": session.session_id,
                "current_version": current_version,
                "feasibility_assessment": current_report,
                "thinking_summary": thinking_summary,
                "human_critique": human_critique,
                "revision_instructions": revision_instructions,
                "revision_history": [],
                "max_revisions": max_revisions,
                "error": None,
            }

            result = hitl.run_revision_workflow(state_dict, thread_id=session.session_id)
            # run_revision_workflow is async, but internally does a sync invoke; handle both awaitable and dict
            if hasattr(result, "__await__"):
                import asyncio
                result = asyncio.run(result)

            # If interrupted (awaiting critique), return resume config
            if isinstance(result, dict) and result.get("status") == "interrupt":
                execution_time = time.time() - start_time
                return {
                    "session_id": session.session_id,
                    "current_version": current_version,
                    "status": "interrupt",
                    "message": "Awaiting human critique to resume revision",
                    "resume_config": result.get("resume_config"),
                    "execution_time": execution_time,
                }

            # Validate final state
            if not isinstance(result, dict):
                raise RuntimeError("Unexpected HITL result type")
            if result.get("error"):
                raise RuntimeError(result["error"])

            # Determine new version and file path from state
            new_version = result.get("current_version", current_version)
            file_path = None
            history = result.get("revision_history") or []
            if history:
                file_path = history[-1].get("file_path")

            # Step 5: Store in session and return
            print("Step 5: Storing revision metadata in session")
            session.current_feasibility_version = new_version

            print(f"✓ Session updated with new version v{new_version}")

            execution_time = time.time() - start_time
            print(f"Revision completed in {execution_time:.2f}s")

            return {
                "session_id": session.session_id,
                "current_version": current_version,
                "new_version": new_version,
                "message": f"Feasibility report revised successfully (v{current_version} → v{new_version})",
                "file_path": file_path,
                "execution_time": execution_time,
            }
            
        except FileNotFoundError as e:
            print(f"File not found: {str(e)}")
            raise HTTPException(
                status_code=404,
                detail=f"Required artifact not found: {str(e)}"
            )
        
        except ValueError as e:
            print(f"Validation error: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid request: {str(e)}"
            )
        
        except RuntimeError as e:
            print(f"Revision failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Revision failed: {str(e)}"
            )
        
        except Exception as e:
            print(f"Unexpected error during revision: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Unexpected error during revision: {str(e)}"
            )
    
    def _get_report_path(self, session_id: str, version: int) -> Path:
        """
        Get standard path for feasibility_report_vN.md.
        
        Args:
            session_id: Session ID
            version: Report version number (1, 2, 3...)
            
        Returns:
            Path: Path to feasibility_report_vN.md
        """
        return Path(f"output/session_{session_id[:8]}/reports/feasibility_report_v{version}.md")
    
    def _get_thinking_summary_path(self, session_id: str) -> Path:
        """
        Get path to thinking_summary.md.
        
        Searches for the most recent thinking_summary file in the session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Path: Path to thinking_summary.md
            
        Raises:
            FileNotFoundError: If no thinking summary found
        """
        report_dir = Path(f"output/session_{session_id[:8]}/reports")
        
        if not report_dir.exists():
            raise FileNotFoundError(f"Report directory not found: {report_dir}")
        
        # Find thinking_summary files (may have timestamp suffix)
        thinking_files = list(report_dir.glob("thinking_summary_*.md"))
        
        if not thinking_files:
            raise FileNotFoundError(
                f"No thinking_summary files found in {report_dir}. "
                f"Please ensure initial feasibility generation is complete."
            )
        
        # Return the most recent one (by modification time)
        return max(thinking_files, key=lambda p: p.stat().st_mtime)
    
    def get_revision_history(self, session_id: str) -> dict:
        """
        Get revision history for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            dict: Revision log with all versions and metadata
            
        Raises:
            HTTPException: If revision log not found
        """
        import json
        
        revision_log_path = Path(f"output/session_{session_id[:8]}/revisions/revision_log.json")
        
        if not revision_log_path.exists():
            # Return empty revision history if no revisions made yet
            return {
                "session_id": session_id,
                "revisions": []
            }
        
        try:
            with open(revision_log_path, 'r', encoding='utf-8') as f:
                revision_log = json.load(f)
            return revision_log
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to read revision log: {str(e)}"
            )
    
    def get_current_feasibility_version(self, session_id: str) -> int:
        """
        Get the current highest version number for feasibility report.
        
        Args:
            session_id: Session ID
            
        Returns:
            int: Current version number (1 if initial only, 2+ if revisions exist)
        """
        report_dir = Path(f"output/session_{session_id[:8]}/reports")
        
        if not report_dir.exists():
            return 1
        
        # Find all feasibility_report_vN.md files
        report_files = list(report_dir.glob("feasibility_report_v*.md"))
        
        if not report_files:
            return 1
        
        # Extract version numbers and return max
        versions = []
        for f in report_files:
            try:
                # Extract version from filename: feasibility_report_v{N}.md
                match_result = f.stem.replace("feasibility_report_v", "")
                version = int(match_result)
                versions.append(version)
            except ValueError:
                continue
        
        return max(versions) if versions else 1
