"""
Plan Generation Handler

Handles project plan generation using reflection loop (LangGraph).

Supports two modes:
1. Non-HITL (default): Automatic reflection without human review
2. HITL: Human-in-the-Loop with interrupts at draft_review and reflection_review stages
"""

from typing import Optional
from pathlib import Path
from datetime import datetime
import time
import json

from fastapi import HTTPException

from src.core.session import Session
from src.app.graph import get_graph, generate_thread_id, generate_request_id
from src.states.reflection_state import ReflectionState


# Directory for pending reviews (HITL mode)
PENDING_REVIEWS_DIR = Path("output/pending_reviews")


class PlanGenerationHandler:
    """
    Handles project plan generation using reflection loop.
    
    Workflow (Non-HITL):
    1. Get document context from MD files
    2. Combine with feasibility assessment
    3. Initialize reflection state
    4. Execute LangGraph workflow (Draft → Reflect → Revise)
    5. Save final plan
    6. Return results
    
    Workflow (HITL):
    1-3. Same as above
    4. Execute until first interrupt (draft_review)
    5. Return pending review info to client
    6. Client submits review via /resume-review
    7. Graph continues to next interrupt (reflection_review)
    8. Repeat until completion
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize plan generation handler.
        
        Args:
            verbose: Enable verbose console output
        """
        self.verbose = verbose
    
    def generate_plan(
        self,
        session: Session,
        max_iterations: int = 5,
        enable_hitl: bool = True
    ) -> dict:
        """
        Generate project plan using reflection loop.
        
        Args:
            session: Session object
            max_iterations: Maximum reflection iterations
            enable_hitl: Enable Human-in-the-Loop mode (default: False)
        
        Returns:
            Dictionary with plan, evidence, result, file_path, steps, execution_time, iterations_completed, status
            
            In HITL mode, may return partial result with interrupt info:
            {
                "status": "pending_review",
                "review_type": "draft_review" | "reflection_review",
                "request_id": "<uuid>",
                "thread_id": "<uuid>",
                ...
            }
        """
        print(f"Plan generation requested for session: {session.session_id} (HITL={'enabled' if enable_hitl else 'disabled'})")
        start_time = time.time()
        
        try:
            # Step 1: Get document context from MD files
            print("Step 1: Processing document context from MD files")
            document_context = self._get_intelligent_context(session)
            
            # Step 2: Combine document context with feasibility assessment
            print("Step 2: Combining document context with feasibility assessment")
            document_context = self._combine_with_feasibility(session, document_context)
            
            # Step 3: Initialize Reflection state with HITL tracking
            print(f"Step 3: Initializing Reflection state with max_iterations={max_iterations}")
            self._debug_context(document_context, session)
            
            # Generate unique IDs for HITL tracking
            thread_id = generate_thread_id()
            request_id = generate_request_id() if enable_hitl else None
            
            reflection_state = ReflectionState(
                task="Synthesize all provided project documents and feasibility notes into an executive-grade implementation plan.",
                document_context=document_context,
                feasibility_file_path=session.feasibility_file_path,
                max_iterations=max_iterations,
                thread_id=thread_id,
                request_id=request_id,
            )
            
            # Step 4: Execute the Reflection graph
            if enable_hitl:
                print("Step 4: Executing Reflection graph with HITL (may pause for human review)")
                return self._execute_graph_hitl(reflection_state, session, start_time)
            else:
                print("Step 4: Executing Reflection graph (non-HITL mode)")
                final_plan_text, iterations_count = self._execute_graph(reflection_state)
            
            execution_time = time.time() - start_time
            print(f"Plan generation completed in {execution_time:.2f}s with {iterations_count} iterations")
            
            # Legacy response format for API compatibility
            plan_dict = {
                "plan_string": f"Reflection-based plan generated in {iterations_count} iterations.",
                "steps": []
            }
            evidence_dict = {"iterations": iterations_count}
            
            # Persist the final result to a markdown file
            plan_filepath = self._save_plan_file(final_plan_text, session.session_id)
            
            return {
                "session_id": session.session_id,
                "plan": plan_dict,
                "evidence": evidence_dict,
                "result": final_plan_text,
                "file_path": str(plan_filepath) if plan_filepath else None,
                "steps": [],
                "execution_time": execution_time,
                "iterations_completed": iterations_count,
                "status": "completed"
            }
            
        except Exception as e:
            print(f"Error during plan generation for session {session.session_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error during plan generation: {str(e)}"
            )
    
    def _execute_graph_hitl(self, reflection_state: ReflectionState, session: Session, start_time: float) -> dict:
        """
        Execute LangGraph workflow with HITL (Human-in-the-Loop).
        
        This method handles the initial execution until the first interrupt.
        Returns pending review info for the client to process.
        """
        from src.services.graph_runner import get_graph_runner
        
        graph_runner = get_graph_runner()
        
        # Start execution with thread_id for checkpointing
        initial_state_dict = reflection_state.model_dump()
        
        try:
            result = graph_runner.start_execution(
                initial_state=initial_state_dict,
                thread_id=reflection_state.thread_id
            )
            
            # Check if we hit an interrupt
            if isinstance(result, dict) and "__interrupt__" in result:
                interrupt_data = result.get("__interrupt__", [])
                
                # Debug logging to understand interrupt structure
                print(f"DEBUG: interrupt_data type: {type(interrupt_data)}")
                print(f"DEBUG: interrupt_data length: {len(interrupt_data) if hasattr(interrupt_data, '__len__') else 'N/A'}")
                
                if interrupt_data:
                    # Get the first interrupt - it's a tuple (Interrupt object,)
                    first_interrupt = interrupt_data[0] if isinstance(interrupt_data, (list, tuple)) else interrupt_data
                    print(f"DEBUG: first_interrupt type: {type(first_interrupt)}")
                    print(f"DEBUG: first_interrupt dir: {[attr for attr in dir(first_interrupt) if not attr.startswith('_')]}")
                    
                    # LangGraph Interrupt objects have a 'value' attribute
                    if hasattr(first_interrupt, 'value'):
                        interrupt_value = first_interrupt.value
                        print("DEBUG: Got value from .value attribute")
                    elif isinstance(first_interrupt, dict):
                        interrupt_value = first_interrupt.get("value", first_interrupt)
                        print("DEBUG: Got value from dict")
                    else:
                        interrupt_value = {}
                        print("DEBUG: Using empty dict as fallback")
                    
                    print(f"DEBUG: interrupt_value type: {type(interrupt_value)}")
                    print(f"DEBUG: interrupt_value keys: {interrupt_value.keys() if isinstance(interrupt_value, dict) else 'N/A'}")
                    
                    review_type = interrupt_value.get("type", "unknown") if isinstance(interrupt_value, dict) else "unknown"
                    draft_content = interrupt_value.get("draft") if isinstance(interrupt_value, dict) else None
                    reflection_content = interrupt_value.get("reflection") if isinstance(interrupt_value, dict) else None
                    iteration = interrupt_value.get("iteration", 1) if isinstance(interrupt_value, dict) else 1
                    message = interrupt_value.get("message", "Human review required") if isinstance(interrupt_value, dict) else "Human review required"
                    
                    print(f"DEBUG: Extracted - type: {review_type}, draft len: {len(draft_content) if draft_content else 0}, iteration: {iteration}")
                    
                    # Persist pending review to file for the /pending-review endpoint
                    self._save_pending_review(
                        review_type=review_type,
                        request_id=reflection_state.request_id,
                        thread_id=reflection_state.thread_id,
                        iteration=iteration,
                        draft=draft_content,
                        reflection=reflection_content,
                        message=message,
                        session_id=session.session_id,
                    )
                    
                    execution_time = time.time() - start_time
                    
                    return {
                        "session_id": session.session_id,
                        "status": "pending_review",
                        "review_type": review_type,
                        "request_id": reflection_state.request_id,
                        "thread_id": reflection_state.thread_id,
                        "iteration": interrupt_value.get("iteration", 1),
                        "message": interrupt_value.get("message", "Human review required"),
                        "execution_time": execution_time,
                    }
            
            # No interrupt - execution completed
            final_plan = result.get("final_plan") if isinstance(result, dict) else None
            iterations = result.get("iterations", []) if isinstance(result, dict) else []
            
            execution_time = time.time() - start_time
            
            if final_plan:
                plan_filepath = self._save_plan_file(final_plan, session.session_id)
                
                return {
                    "session_id": session.session_id,
                    "status": "completed",
                    "result": final_plan,
                    "file_path": str(plan_filepath) if plan_filepath else None,
                    "iterations_completed": len(iterations),
                    "execution_time": execution_time,
                    "plan": {"plan_string": f"Plan generated in {len(iterations)} iterations.", "steps": []},
                    "evidence": {"iterations": len(iterations)},
                    "steps": [],
                }
            
            raise HTTPException(
                status_code=500,
                detail="Graph execution completed but no final plan was captured."
            )
            
        except HTTPException:
            raise
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Resource exhausted" in error_msg:
                raise HTTPException(
                    status_code=429,
                    detail="Google Gemini API rate limit exceeded. Please try again in a few minutes."
                )
            raise HTTPException(
                status_code=500,
                detail=f"Error during HITL graph execution: {str(e)}"
            )
    
    def _save_pending_review(
        self,
        review_type: str,
        request_id: str,
        thread_id: str,
        iteration: int,
        draft: Optional[str],
        reflection: Optional[str],
        message: str,
        session_id: str,
    ) -> None:
        """Save pending review data to file for the /pending-review/{request_id} endpoint."""
        PENDING_REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
        
        pending_data = {
            "type": review_type,
            "node": review_type,  # For backwards compatibility
            "request_id": request_id,
            "thread_id": thread_id,
            "iteration": iteration,
            "draft": draft,
            "reflection": reflection,
            "message": message,
            "metadata": {
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
            }
        }
        
        pending_file = PENDING_REVIEWS_DIR / f"{request_id}.json"
        with open(pending_file, "w", encoding="utf-8") as f:
            json.dump(pending_data, f, ensure_ascii=False, indent=2)
        
        print(f"Pending review saved: {pending_file}")
    
    def _get_intelligent_context(self, session: Session) -> str:
        """Get document context from MD files."""
        if not session.parsed_documents:
            raise ValueError("No parsed documents found. Please ensure documents are uploaded and parsed first.")
        
        print(f"Reading {len(session.parsed_documents)} MD files for plan generation...")
        md_content = []
        
        for parsed_doc in session.parsed_documents:
            md_path = Path(parsed_doc.output_md_path)
            if md_path.exists():
                print(f"  Reading: {md_path.name}")
                with open(md_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    md_content.append(content)
                    print(f"    Loaded {len(content)} characters")
            else:
                print(f"  Warning: MD file not found: {md_path}")
        
        if not md_content:
            raise ValueError("No MD files could be read. Please ensure parsing completed successfully.")
        
        document_context = "\n\n---\n\n".join(md_content)
        print(f"Combined MD content: {len(document_context)} characters from {len(md_content)} files")
        return document_context
    
    def _combine_with_feasibility(self, session: Session, document_context: str) -> str:
        """Combine document context with feasibility assessment."""
        if session.feasibility_assessment:
            print("Feasibility assessment found in session, appending to context")
            document_context = f"""{document_context}

---

## FEASIBILITY ASSESSMENT

{session.feasibility_assessment}
"""
            print(f"Combined context length: {len(document_context)} chars")
        else:
            print("WARNING: No feasibility assessment found in session. Proceeding with document context only.")
            print("Consider running /feasibility endpoint first for better results.")
        
        return document_context
    
    def _debug_context(self, document_context: str, session: Session):
        """Debug output for context being sent to LLM."""
        print("\n" + "="*80)
        print("DEBUG: CONTEXT BEING SENT TO LLM FOR PROJECT PLAN GENERATION")
        print("="*80)
        print(f"Total document context length: {len(document_context)} characters")
        print(f"Has feasibility assessment: {session.feasibility_assessment is not None}")
        print(f"Feasibility file path: {session.feasibility_file_path}")
        print("\nDocument context structure:")
        
        # Show section headers to understand structure
        lines = document_context.split('\n')
        section_headers = [line for line in lines if line.startswith('#')]
        print(f"Found {len(section_headers)} section headers:")
        for header in section_headers[:20]:  # Show first 20 headers
            print(f"  {header}")
        if len(section_headers) > 20:
            print(f"  ... and {len(section_headers) - 20} more sections")
        
        print(f"\nContext preview (first 3000 chars):\n{document_context[:3000]}")
        print("..." if len(document_context) > 3000 else "")
        print(f"\nContext preview (last 1500 chars):\n...{document_context[-1500:]}")
        print("="*80 + "\n")
    
    def _execute_graph(self, reflection_state: ReflectionState) -> tuple:
        """Execute LangGraph workflow without HITL (non-interactive mode)."""
        # Use the graph without HITL for automatic execution
        graph = get_graph(reflection_state, enable_hitl=False)
        final_plan_text = None
        iterations_count = 0
        node_count = 0
        
        # Create config with thread_id (required by checkpointer)
        config = {"configurable": {"thread_id": reflection_state.thread_id}}
        
        try:
            for s in graph.stream(reflection_state, config=config):
                node_name = next(iter(s))
                data = s[node_name]
                node_count += 1
                print(f"Completed node {node_count}: {node_name}")
                
                # Capture the final plan when the revise node sets it
                if node_name == "revise":
                    final_plan_text = data.get("final_plan")
                    iterations = data.get("iterations", [])
                    iterations_count = len(iterations)
                    if final_plan_text:
                        print(f"Final plan captured from revise node after {iterations_count} iterations")
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Resource exhausted" in error_msg:
                print(f"Rate limit error during graph execution: {error_msg}")
                raise HTTPException(
                    status_code=429,
                    detail="Google Gemini API rate limit exceeded. Please try again in a few minutes."
                )
            else:
                print(f"Error during graph execution: {error_msg}")
                raise
        
        if not final_plan_text:
            print("ERROR: No final plan was captured during execution")
            raise HTTPException(
                status_code=500,
                detail="Failed to generate final plan. Please check that max_iterations allows enough cycles."
            )
        
        return final_plan_text, iterations_count
    
    def _save_plan_file(self, final_plan_text: str, session_id: str) -> Optional[Path]:
        """Save plan to file."""
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        plan_filename = f"project_plan_{session_id[:8]}_{ts}.md"
        plan_filepath = output_dir / plan_filename
        
        try:
            with plan_filepath.open("w", encoding="utf-8") as f:
                f.write(str(final_plan_text).strip())
            print(f"Final project plan saved to: {plan_filepath}")
            return plan_filepath
        except Exception as e:
            print(f"WARNING: Failed to write project plan file: {e}")
            return None

