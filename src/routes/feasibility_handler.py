"""
Feasibility Handler

Handles feasibility assessment generation using LLM with HITL support.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import time

from fastapi import HTTPException

from src.core.session import Session


class FeasibilityHandler:
    """
    Handles feasibility assessment generation.
    
    Workflow:
    1. Read MD files from parsed documents
    2. Process development context (Q&A from questionnaire)
    3. Generate feasibility assessment with LLM
    4. Save reports (thinking summary + feasibility report)
    5. Return results
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize feasibility handler.
        
        Args:
            verbose: Enable verbose console output
        """
        self.verbose = verbose
    
    def start_feasibility(
        self,
        session: Session,
        development_context: Optional[Dict[str, str]] = None
    ) -> dict:
        """
        Start feasibility assessment with HITL support.
        
        Initiates graph execution and pauses at human review gate.
        
        Args:
            session: Session object
            development_context: Development process information
        
        Returns:
            Dictionary with status, report, and metadata
        """
        print(f"\n{'='*60}")
        print(f"🚀 STARTING FEASIBILITY ASSESSMENT (HITL Mode)")
        print(f"Session: {session.session_id[:8]}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        try:
            from src.app.feasibility_agent import save_development_context_to_json
            from src.states.feasibility_state import FeasibilityState
            from src.app.feasibility_graph import get_feasibility_graph
            
            # Step 1: Get MD file paths
            print("Step 1: Preparing document input")
            md_file_paths = self._get_md_file_paths(session)
            print(f"✅ Prepared {len(md_file_paths)} MD files\n")
            
            # Step 2: Save development context if provided
            dev_context_json_path = None
            if development_context:
                print("Step 2: Saving development context")
                dev_context_json_path = save_development_context_to_json(
                    development_context=development_context,
                    session_id=session.session_id,
                    output_dir="output/intermediate"
                )
                print(f"✅ Context saved: {dev_context_json_path}\n")
            
            # Step 3: Initialize state
            print("Step 3: Initializing feasibility state")
            initial_state = FeasibilityState(
                session_id=session.session_id,
                md_file_paths=md_file_paths,
                development_context=development_context,
                iteration=0,
                max_iterations=3,
                status="generating"
            )
            print(f"✅ State initialized\n")
            
            # Step 4: Execute graph until interrupt
            print("Step 4: Starting graph execution")
            graph = get_feasibility_graph()
            
            # Create thread config for checkpointing
            thread_config = {
                "configurable": {
                    "thread_id": session.session_id
                }
            }
            
            # Stream execution until interrupt (human review gate)
            final_state = None
            for event in graph.stream(initial_state, thread_config, stream_mode="values"):
                final_state = event
                print(f"  Current status: {event.get('status', 'unknown')}")
            
            print(f"✅ Graph paused at human review gate\n")
            
            # Save initial outputs
            if final_state:
                thinking_path, report_path = self._save_feasibility_files(
                    {
                        "thinking_summary": final_state.get("thinking_summary", ""),
                        "feasibility_report": final_state.get("feasibility_report", "")
                    },
                    session.session_id
                )
                
                # Store in session
                session.feasibility_assessment = final_state.get("feasibility_report", "")
                session.feasibility_file_path = str(report_path)
            
            execution_time = time.time() - start_time
            
            print(f"\n{'='*60}")
            print(f"✅ FEASIBILITY GENERATION COMPLETE")
            print(f"⏱️  Execution time: {execution_time:.2f}s")
            print(f"🚦 Status: awaiting_human")
            print(f"{'='*60}\n")
            
            return {
                "session_id": session.session_id,
                "status": "awaiting_human",
                "iteration": final_state.get("iteration", 0) if final_state else 0,
                "max_iterations": final_state.get("max_iterations", 3) if final_state else 3,
                "feasibility_report": final_state.get("feasibility_report", "") if final_state else "",
                "thinking_summary": final_state.get("thinking_summary", "") if final_state else "",
                "message": "Feasibility report generated. Awaiting human review.",
                "execution_time": execution_time
            }
            
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}\n")
            raise HTTPException(
                status_code=500,
                detail=f"Error starting feasibility assessment: {str(e)}"
            )
    
    def review_feasibility(
        self,
        session: Session,
        approved: bool,
        feedback: Optional[str] = None
    ) -> dict:
        """
        Resume feasibility graph with human review decision.
        
        Args:
            session: Session object
            approved: True to approve, False to request changes
            feedback: Required if approved=False, optional critique/feedback text
        
        Returns:
            Dictionary with updated status and report
        """
        print(f"\n{'='*60}")
        print(f"📝 PROCESSING HUMAN REVIEW")
        print(f"Session: {session.session_id[:8]}")
        print(f"Decision: {'✅ APPROVED' if approved else '🔄 REQUEST CHANGES'}")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        try:
            from src.app.feasibility_graph import get_feasibility_graph
            from langgraph.checkpoint.base import CheckpointTuple
            
            # Validate feedback if requesting changes
            if not approved and not feedback:
                raise HTTPException(
                    status_code=400,
                    detail="Feedback is required when requesting changes (approved=False)"
                )
            
            # Get graph and checkpointer
            graph = get_feasibility_graph()
            
            # Thread config for resuming
            thread_config = {
                "configurable": {
                    "thread_id": session.session_id
                }
            }
            
            # Get current state from checkpoint
            state_snapshot = graph.get_state(thread_config)
            current_state = state_snapshot.values
            
            print(f"Current iteration: {current_state.get('iteration', 0)}")
            print(f"Current status: {current_state.get('status', 'unknown')}\n")
            
            if approved:
                # Approved - update state and end workflow
                print("✅ Report approved - completing workflow\n")
                
                updated_state = {
                    **current_state,
                    "approved": True,
                    "status": "approved"
                }
                
                # Update state and resume (will go to END)
                graph.update_state(thread_config, updated_state)
                
                execution_time = time.time() - start_time
                
                return {
                    "session_id": session.session_id,
                    "status": "approved",
                    "message": "Feasibility report approved successfully.",
                    "feasibility_report": current_state.get("feasibility_report", ""),
                    "execution_time": execution_time
                }
                
            else:
                # Changes requested - proceed with critique and revision
                print(f"🔄 Changes requested\n")
                print(f"Feedback ({len(feedback)} chars): {feedback[:100]}...\n")
                
                # Check if max iterations reached
                current_iteration = current_state.get("iteration", 0)
                max_iterations = current_state.get("max_iterations", 3)
                
                if current_iteration >= max_iterations:
                    print(f"⚠️  Max iterations ({max_iterations}) reached\n")
                    return {
                        "session_id": session.session_id,
                        "status": "max_iterations_reached",
                        "message": f"Maximum iterations ({max_iterations}) reached. Cannot revise further.",
                        "feasibility_report": current_state.get("feasibility_report", ""),
                        "iteration": current_iteration,
                        "execution_time": time.time() - start_time
                    }
                
                # Update state with feedback
                updated_state = {
                    **current_state,
                    "approved": False,
                    "human_feedback": feedback,
                    "status": "revising"
                }
                
                # Update state to trigger revision workflow
                graph.update_state(thread_config, updated_state)
                
                print("Step 1: Generating critique from feedback")
                print("Step 2: Revising assessment")
                print("Step 3: Re-generating report\n")
                
                # Resume execution - will go through critique → revise → generate → human_review_gate
                final_state = None
                for event in graph.stream(None, thread_config, stream_mode="values"):
                    final_state = event
                    print(f"  Status: {event.get('status', 'unknown')}, Iteration: {event.get('iteration', 0)}")
                
                # Save revised report
                if final_state:
                    thinking_path, report_path = self._save_feasibility_files(
                        {
                            "thinking_summary": final_state.get("thinking_summary", ""),
                            "feasibility_report": final_state.get("feasibility_report", "")
                        },
                        session.session_id,
                        iteration=final_state.get("iteration", 0)
                    )
                    
                    # Update session
                    session.feasibility_assessment = final_state.get("feasibility_report", "")
                    session.feasibility_file_path = str(report_path)
                
                execution_time = time.time() - start_time
                
                print(f"\n{'='*60}")
                print(f"✅ REVISION COMPLETE")
                print(f"⏱️  Execution time: {execution_time:.2f}s")
                print(f"🔄 New iteration: {final_state.get('iteration', 'unknown') if final_state else 'unknown'}")
                print(f"🚦 Status: awaiting_human")
                print(f"{'='*60}\n")
                
                return {
                    "session_id": session.session_id,
                    "status": "awaiting_human",
                    "iteration": final_state.get("iteration", current_iteration + 1) if final_state else current_iteration + 1,
                    "max_iterations": max_iterations,
                    "feasibility_report": final_state.get("feasibility_report", "") if final_state else "",
                    "critique": final_state.get("critique_md", "") if final_state else "",
                    "message": f"Revision {final_state.get('iteration', '?') if final_state else '?'} complete. Awaiting review.",
                    "execution_time": execution_time
                }
                
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}\n")
            raise HTTPException(
                status_code=500,
                detail=f"Error processing review: {str(e)}"
            )
    
    def get_feasibility_status(self, session: Session) -> dict:
        """
        Get current status of feasibility assessment workflow.
        
        Args:
            session: Session object
        
        Returns:
            Dictionary with current state information
        """
        print(f"Checking feasibility status for session: {session.session_id[:8]}")
        
        try:
            from src.app.feasibility_graph import get_feasibility_graph
            
            graph = get_feasibility_graph()
            
            thread_config = {
                "configurable": {
                    "thread_id": session.session_id
                }
            }
            
            # Get state snapshot
            state_snapshot = graph.get_state(thread_config)
            
            if not state_snapshot or not state_snapshot.values:
                return {
                    "session_id": session.session_id,
                    "status": "not_started",
                    "message": "No feasibility assessment in progress"
                }
            
            current_state = state_snapshot.values
            
            return {
                "session_id": session.session_id,
                "status": current_state.get("status", "unknown"),
                "iteration": current_state.get("iteration", 0),
                "max_iterations": current_state.get("max_iterations", 3),
                "approved": current_state.get("approved"),
                "feasibility_report": current_state.get("feasibility_report", ""),
                "thinking_summary": current_state.get("thinking_summary", ""),
                "critique": current_state.get("critique_md", ""),
                "revision_history_count": len(current_state.get("revision_history", [])),
                "message": f"Current status: {current_state.get('status', 'unknown')}"
            }
            
        except Exception as e:
            print(f"Error getting feasibility status: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting status: {str(e)}"
            )
    
    def generate_feasibility(
        self,
        session: Session,
        development_context: Optional[Dict[str, str]] = None
    ) -> dict:
        """
        Generate feasibility assessment using graph execution.
        
        Args:
            session: Session object
            development_context: Development process information (Q&A from questionnaire)
        
        Returns:
            Dictionary with session_id, message, file paths, execution_time
        """
        print(f"Feasibility check requested for session: {session.session_id}")
        start_time = time.time()
        
        try:
            from src.app.feasibility_agent import save_development_context_to_json
            
            # Step 1: Get MD file paths
            print("Step 1: Preparing document input for feasibility analysis")
            md_file_paths = self._get_md_file_paths(session)
            print(f"Prepared {len(md_file_paths)} MD file paths")
            
            # Step 1.5: Save development context if provided
            dev_context_json_path = None
            if development_context:
                print("Development context provided, saving to JSON")
                dev_context_json_path = save_development_context_to_json(
                    development_context=development_context,
                    session_id=session.session_id,
                    output_dir="output/intermediate"
                )
                print(f"Development context saved to JSON: {dev_context_json_path}")
            else:
                print("No development context provided.")
            
            # Step 2: Generate feasibility assessment using graph
            from src.config.feature_flags import feature_flags
            
            if feature_flags.use_hardcoded_feasibility:
                print("\n" + "="*80)
                print("HARDCODED FEASIBILITY MODE: Loading from static files")
                print("Skipping LLM calls to save costs during development/testing")
                print("="*80 + "\n")
                feasibility_result = self._load_hardcoded_feasibility()
            else:
                print("Step 2: Initializing Feasibility graph state")
                from src.states.feasibility_state import FeasibilityState
                
                feasibility_state = FeasibilityState(
                    session_id=session.session_id,
                    md_file_paths=md_file_paths,
                    development_context=development_context
                )
                
                print("Step 3: Executing Feasibility graph")
                thinking_summary, feasibility_report = self._execute_graph(feasibility_state)
                
                feasibility_result: Dict[str, str] = {
                    "thinking_summary": thinking_summary or "",
                    "feasibility_report": feasibility_report or ""
                }
            
            # Validate outputs
            self._validate_outputs(feasibility_result)
            
            # Step 4: Save both markdown files
            print("Step 4: Saving feasibility documents to files")
            thinking_path, report_path = self._save_feasibility_files(
                feasibility_result,
                session.session_id
            )
            
            # Step 5: Store in session
            print("Step 5: Storing feasibility assessment in session")
            session.feasibility_assessment = feasibility_result["feasibility_report"]
            session.feasibility_file_path = str(report_path)
            print(f"Feasibility documents stored in session")
            
            execution_time = time.time() - start_time
            print(f"Feasibility check completed in {execution_time:.2f}s")
            
            return {
                "session_id": session.session_id,
                "message": f"Feasibility assessment generated successfully. Two files created: {thinking_path.name} and {report_path.name}",
                "thinking_summary_file": str(thinking_path),
                "feasibility_report_file": str(report_path),
                "development_context_json_path": dev_context_json_path,
                "execution_time": execution_time
            }
            
        except Exception as e:
            print(f"Error during feasibility check for session {session.session_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error during feasibility check: {str(e)}"
            )
    
    def _get_md_file_paths(self, session: Session) -> list[str]:
        """
        Get list of MD file paths from the session's parsed documents directory.
        
        Used for v3 JSON conversion.
        """
        if not session.parsed_documents_dir:
            raise ValueError("No parsed documents directory found. Please ensure documents are uploaded and parsed first.")
        
        md_dir = Path(session.parsed_documents_dir)
        if not md_dir.exists():
            raise ValueError(f"MD directory not found: {md_dir}")
        
        # Find all .md files in the directory
        md_files = list(md_dir.glob("*.md"))
        
        if not md_files:
            raise ValueError(f"No MD files found in {md_dir}")
        
        print(f"Found {len(md_files)} MD files in {md_dir.name}")
        md_file_paths = [str(md_path.absolute()) for md_path in sorted(md_files)]
        
        for path in md_file_paths:
            print(f"  - {Path(path).name}")
        
        return md_file_paths
    
    def _execute_graph(self, state):
        """Execute the feasibility graph and return results (legacy method)."""
        from src.app.feasibility_graph import get_feasibility_graph
        
        graph = get_feasibility_graph()
        
        # Create thread config for checkpointer (required)
        thread_config = {
            "configurable": {
                "thread_id": state.session_id
            }
        }
        
        thinking_summary = None
        feasibility_report = None
        
        for s in graph.stream(state, thread_config):
            node_name = next(iter(s))
            data = s[node_name]
            print(f"Completed graph node: {node_name}")
            
            # Skip interrupt node (HITL gate) - just continue for legacy mode
            if node_name == "__interrupt__":
                print("Skipping HITL interrupt for legacy mode")
                continue
            
            # Handle both dict and tuple responses
            if isinstance(data, dict):
                thinking_summary = data.get("thinking_summary")
                feasibility_report = data.get("feasibility_report")
            elif isinstance(data, tuple):
                # Tuple format from some LangGraph versions
                print(f"Received tuple data, skipping...")
                continue
        
        return thinking_summary, feasibility_report
    
    def _validate_outputs(self, feasibility_result: Dict[str, str]):
        """Validate feasibility outputs are not empty."""
        def _too_short(s: str) -> bool:
            return (not s) or (len(s.strip()) < 50)
        
        if _too_short(feasibility_result.get("feasibility_report", "")) or _too_short(feasibility_result.get("thinking_summary", "")):
            print("WARNING: Feasibility outputs too short; attempting one retry generation...")
            raise HTTPException(
                status_code=502,
                detail="LLM returned insufficient content for feasibility outputs. Please try again."
            )
    
    def _load_hardcoded_feasibility(self) -> Dict[str, str]:
        """
        Load hardcoded feasibility files instead of generating with LLM.
        
        This is used for fast development/testing to avoid expensive LLM calls.
        Enable with USE_HARDCODED_FEASIBILITY=true in .env
        
        Returns:
            Dictionary with 'thinking_summary' and 'feasibility_report' keys
        """
        from src.config.feature_flags import feature_flags
        from pathlib import Path
        
        thinking_file = Path(feature_flags.hardcoded_feasibility_thinking_file)
        report_file = Path(feature_flags.hardcoded_feasibility_report_file)
        
        print(f"Loading hardcoded thinking summary from: {thinking_file}")
        if not thinking_file.exists():
            raise FileNotFoundError(
                f"Hardcoded thinking summary file not found: {thinking_file}\n"
                f"Please ensure the file exists or disable USE_HARDCODED_FEASIBILITY"
            )
        
        print(f"Loading hardcoded feasibility report from: {report_file}")
        if not report_file.exists():
            raise FileNotFoundError(
                f"Hardcoded feasibility report file not found: {report_file}\n"
                f"Please ensure the file exists or disable USE_HARDCODED_FEASIBILITY"
            )
        
        # Read files
        with open(thinking_file, 'r', encoding='utf-8') as f:
            thinking_summary = f.read()
        
        with open(report_file, 'r', encoding='utf-8') as f:
            feasibility_report = f.read()
        
        print(f"Loaded thinking summary: {len(thinking_summary)} chars")
        print(f"Loaded feasibility report: {len(feasibility_report)} chars")
        
        return {
            "thinking_summary": thinking_summary,
            "feasibility_report": feasibility_report
        }
    
    def _save_feasibility_files(
        self,
        feasibility_result: Dict[str, str],
        session_id: str,
        iteration: int = 0
    ) -> tuple:
        """Save feasibility files to session reports folder with version numbers (no timestamps)."""
        # Use session-specific reports directory
        session_id_short = session_id[:8]
        output_dir = Path(f"output/session_{session_id_short}/reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Use version suffix instead of timestamp
        version_suffix = f"_v{iteration}"
        
        # Validate content before saving
        thinking_summary = feasibility_result.get("thinking_summary", "")
        feasibility_report = feasibility_result.get("feasibility_report", "")
        
        # Check if content is empty or contains error messages
        if not thinking_summary or len(thinking_summary) < 100 or "error" in thinking_summary.lower()[:200]:
            print(f"⚠️  WARNING: Thinking summary appears invalid or empty ({len(thinking_summary)} chars)")
            thinking_summary = "# ERROR\n\nThinking summary generation failed or returned invalid content."
        
        if not feasibility_report or len(feasibility_report) < 500 or "error" in feasibility_report.lower()[:200]:
            print(f"⚠️  WARNING: Feasibility report appears invalid or empty ({len(feasibility_report)} chars)")
            feasibility_report = "# ERROR\n\nFeasibility report generation failed or returned invalid content.\n\nPlease check the server logs for details."
        
        # Save thinking summary
        thinking_filename = f"thinking_summary_{session_id[:8]}{version_suffix}.md"
        thinking_path = output_dir / thinking_filename
        with open(thinking_path, "w", encoding="utf-8") as f:
            f.write(thinking_summary)
        print(f"Thinking summary saved to: {thinking_path}")
        
        # Save feasibility report
        report_filename = f"feasibility_report_{session_id[:8]}{version_suffix}.md"
        report_path = output_dir / report_filename
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(feasibility_report)
        print(f"Feasibility report saved to: {report_path}")
        
        return thinking_path, report_path

