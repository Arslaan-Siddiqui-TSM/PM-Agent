"""
Plan Generation Handler

Handles project plan generation using reflection loop (LangGraph).
"""

from typing import Optional
from pathlib import Path
from datetime import datetime
import time

from fastapi import HTTPException

from src.core.session import Session
from src.app.graph import get_graph
from src.states.reflection_state import ReflectionState


class PlanGenerationHandler:
    """
    Handles project plan generation using reflection loop.
    
    Workflow:
    1. Get document context from MD files
    2. Combine with feasibility assessment
    3. Initialize reflection state
    4. Execute LangGraph workflow (Draft → Reflect → Revise)
    5. Save final plan
    6. Return results
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
        max_iterations: int = 1
    ) -> dict:
        """
        Generate project plan using reflection loop.
        
        Args:
            session: Session object
            max_iterations: Maximum reflection iterations
        
        Returns:
            Dictionary with plan, evidence, result, file_path, steps, execution_time, iterations_completed, status
        """
        print(f"Plan generation requested for session: {session.session_id}")
        start_time = time.time()
        
        try:
            # Step 1: Get document context from MD files
            print(f"Step 1: Processing document context from MD files")
            document_context = self._get_intelligent_context(session)
            
            # Step 2: Combine document context with feasibility assessment
            print("Step 2: Combining document context with feasibility assessment")
            document_context = self._combine_with_feasibility(session, document_context)
            
            # Step 3: Initialize Reflection state
            print(f"Step 3: Initializing Reflection state with max_iterations={max_iterations}")
            self._debug_context(document_context, session)
            
            reflection_state = ReflectionState(
                task="Synthesize all provided project documents and feasibility notes into an executive-grade implementation plan.",
                document_context=document_context,
                feasibility_file_path=session.feasibility_file_path,
                max_iterations=max_iterations,
            )
            
            # Step 4: Execute the Reflection graph with streaming
            print("Step 4: Executing Reflection graph with streaming")
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
        print(f"\nDocument context structure:")
        
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
        """Execute LangGraph workflow."""
        graph = get_graph(reflection_state)
        final_plan_text = None
        iterations_count = 0
        node_count = 0
        
        try:
            for s in graph.stream(reflection_state):
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
                    detail=f"Google Gemini API rate limit exceeded. Please try again in a few minutes."
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

