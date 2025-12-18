"""
Feasibility Graph

Simple graph for feasibility assessment generation with HITL support.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, Any

from langgraph.graph import END, StateGraph, START
from langgraph.checkpoint.memory import MemorySaver

from src.states.feasibility_state import FeasibilityState

# Global checkpointer instance for state persistence
_checkpointer = MemorySaver()


def _create_unified_context_file(md_file_paths: list[str], session_id: str) -> Dict[str, Any]:
    """
    Check if requirement_context.md already exists and reuse it, or create it if needed.
    
    Args:
        md_file_paths: List of paths to markdown files (parsed documents)
        session_id: Session ID for the assessment
        
    Returns:
        dict: {
            "file_path": str,
            "total_chars": int,
            "documents_processed": int,
            "documents_failed": int
        }
    """
    print(f"\n{'='*60}")
    print(f"Checking for existing context file for session {session_id[:8]}")
    print(f"{'='*60}\n")
    
    # Derive the session directory from the md_file_paths
    # md_file_paths are in: output/session_<id>_<date>/markdown/*.md
    # We need: output/session_<id>_<date>/context/
    if md_file_paths:
        first_md_path = Path(md_file_paths[0])
        session_base_dir = first_md_path.parent.parent  # Go up from markdown/ to session_*/
        output_dir = session_base_dir / "context"
    else:
        # Fallback if no MD files provided (shouldn't happen)
        output_dir = Path(f"output/session_{session_id[:8]}/context")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Use requirement_context.md (already created by docling_parser)
    unified_file_path = output_dir / "requirement_context.md"
    
    # If requirement_context.md already exists, reuse it
    if unified_file_path.exists():
        print(f"✅ Reusing existing requirement_context.md")
        with open(unified_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"📊 File size: {len(content):,} characters")
        print(f"{'='*60}\n")
        return {
            "file_path": str(unified_file_path.absolute()),
            "total_chars": len(content),
            "documents_processed": len(md_file_paths),
            "documents_failed": 0
        }
    
    print(f"📄 Creating requirement_context.md from {len(md_file_paths)} MD files\n")
    
    # Read and combine all MD files
    unified_content = []
    documents_processed = 0
    documents_failed = 0
    
    unified_content.append("# UNIFIED CONTEXT FILE")
    unified_content.append(f"Session ID: {session_id}\n")
    unified_content.append("---\n")
    
    # Add document content section
    unified_content.append("## PARSED DOCUMENTS\n")
    
    for idx, md_path_str in enumerate(md_file_paths, 1):
        md_path = Path(md_path_str)
        
        if not md_path.exists():
            print(f"⚠️  WARNING [{idx}/{len(md_file_paths)}]: File not found: {md_path}")
            documents_failed += 1
            continue
            
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                print(f"⚠️  WARNING [{idx}/{len(md_file_paths)}]: File is empty: {md_path.name}")
                documents_failed += 1
                continue
            
            # Add document header
            doc_name = md_path.name
            unified_content.append(f"\n### Document: {doc_name}\n")
            unified_content.append(content)
            unified_content.append("\n---\n")
            
            documents_processed += 1
            print(f"✅ SUCCESS [{idx}/{len(md_file_paths)}]: {doc_name} ({len(content):,} chars)")
            
        except Exception as e:
            print(f"❌ ERROR [{idx}/{len(md_file_paths)}]: Failed to read {md_path.name}: {e}")
            documents_failed += 1
    
    # Placeholder for feasibility report
    unified_content.append("\n## FEASIBILITY REPORT\n")
    unified_content.append("*(To be generated)*\n")
    
    # Write unified context file
    final_content = "\n".join(unified_content)
    total_chars = len(final_content)
    
    try:
        with open(unified_file_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        print(f"\n{'='*60}")
        print(f"✅ Unified context file created successfully!")
        print(f"{'='*60}")
        print(f"📁 File path: {unified_file_path}")
        print(f"📊 Total size: {total_chars:,} characters")
        print(f"✅ Documents processed: {documents_processed}")
        print(f"❌ Documents failed: {documents_failed}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Failed to write unified context file: {e}")
        raise
    
    return {
        "file_path": str(unified_file_path.absolute()),
        "total_chars": total_chars,
        "documents_processed": documents_processed,
        "documents_failed": documents_failed
    }


def _update_unified_context_with_report(unified_path: str, feasibility_report: str) -> bool:
    """
    Update the unified context file with the generated feasibility report.
    
    Args:
        unified_path: Path to the unified context file
        feasibility_report: Generated feasibility report content
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Updating unified context file with feasibility report")
    print(f"{'='*60}\n")
    
    try:
        # Read current content
        with open(unified_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verify placeholder exists
        placeholder = "## FEASIBILITY REPORT\n\n*(To be generated)*"
        if placeholder not in content:
            print(f"⚠️  WARNING: Placeholder not found in unified context file")
            print(f"   File may have been modified or report already added")
            return False
        
        # Replace placeholder with actual report
        updated_content = content.replace(
            placeholder,
            f"## FEASIBILITY REPORT\n\n{feasibility_report}"
        )
        
        # Write updated content
        with open(unified_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print(f"✅ Unified context file updated successfully!")
        print(f"📊 Report size: {len(feasibility_report):,} characters")
        print(f"📊 Total file size: {len(updated_content):,} characters")
        print(f"{'='*60}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Failed to update unified context file: {e}")
        return False


def _save_initial_thinking_summary(thinking_summary: str, session_id: str, unified_context_path: str) -> bool:
    """
    Save the initial thinking summary to a dedicated file before HITL begins.
    
    Args:
        thinking_summary: The initial detailed thinking summary
        session_id: Session ID for the assessment
        unified_context_path: Path to unified context file (used to derive correct directory)
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    try:
        # Derive the context directory from unified_context_path
        # unified_context_path is: output/session_<id>_<date>/context/requirement_context.md
        output_dir = Path(unified_context_path).parent
        
        thinking_file_path = output_dir / f"initial_thinking_summary_{session_id[:8]}.md"
        
        with open(thinking_file_path, 'w', encoding='utf-8') as f:
            f.write("# INITIAL THINKING SUMMARY\n")
            f.write(f"Session ID: {session_id}\n")
            f.write("Generated: Before HITL process\n\n")
            f.write("---\n\n")
            f.write(thinking_summary)
        
        print(f"💾 Saved initial thinking summary to: {thinking_file_path.name}")
        print(f"   Size: {len(thinking_summary):,} characters\n")
        return True
        
    except Exception as e:
        print(f"⚠️  WARNING: Failed to save initial thinking summary: {e}")
        return False

        
    except Exception as e:
        print(f"❌ ERROR: Failed to update unified context file: {e}")
        return False


def _validate_generation_result(result: dict, stage: str) -> Dict[str, Any]:
    """
    Validate the result from feasibility agent.
    
    Args:
        result: Result dictionary from generate_feasibility_questions
        stage: "thinking_summary" or "feasibility_report"
        
    Returns:
        dict: Validation report
    """
    validation = {
        "is_valid": False,
        "has_content": False,
        "content_length": 0,
        "warnings": []
    }
    
    content = result.get(stage, "")
    
    if not content:
        validation["warnings"].append(f"{stage} is empty")
        return validation
    
    validation["has_content"] = True
    validation["content_length"] = len(content)
    
    # Check for error messages
    if "Error" in content or "error" in content[:100]:
        validation["warnings"].append(f"{stage} may contain error message")
    
    # Check minimum length (thinking summary should be substantial)
    min_length = 100 if stage == "thinking_summary" else 500
    if len(content) < min_length:
        validation["warnings"].append(f"{stage} is suspiciously short ({len(content)} chars < {min_length})")
    
    # Check for delimiter issues (thinking summary)
    if stage == "thinking_summary":
        if "---THINKING_SUMMARY_START---" not in content:
            validation["warnings"].append("Thinking summary delimiters not found - fallback was used")
    
    # If no warnings, mark as valid
    validation["is_valid"] = len(validation["warnings"]) == 0
    
    return validation


def _generate_assessment(state: FeasibilityState) -> dict:
    """Generate feasibility assessment (thinking + report)."""
    from src.app.feasibility_agent import generate_feasibility_questions
    
    print(f"\n{'#'*60}")
    print(f"# FEASIBILITY GRAPH: GENERATE ASSESSMENT NODE")
    print(f"# Iteration: {state.iteration + 1}")
    print(f"{'#'*60}\n")
    
    # Track revision history if this is a revision
    if state.iteration > 0:
        print(f"🔄 Generating revision {state.iteration + 1}/{state.max_iterations}")
        print(f"📝 User feedback: {state.human_feedback[:100]}..." if state.human_feedback else "")
        print()
    
    # Create unified context file from MD files (only on first iteration)
    md_file_paths = state.md_file_paths or []
    session_id = state.session_id
    
    print(f"📋 Session ID: {session_id[:8]}...")
    
    # Use existing unified context if available, otherwise create new
    if state.unified_context_path and Path(state.unified_context_path).exists():
        unified_context_path = state.unified_context_path
        print(f"📄 Using existing unified context: {Path(unified_context_path).name}\n")
    else:
        print(f"📄 Processing {len(md_file_paths)} MD files\n")
        
        # Create unified context and get metadata
        context_result = _create_unified_context_file(md_file_paths, session_id)
        unified_context_path = context_result["file_path"]
        
        # Validate that documents were actually processed
        if context_result["documents_processed"] == 0:
            print(f"❌ CRITICAL: No documents were processed!")
            return {
                "thinking_summary": "ERROR: No documents were processed",
                "feasibility_report": "ERROR: No documents were processed",
                "unified_context_path": unified_context_path,
                "status": "failed"
            }
    
    print(f"🤖 Invoking feasibility agent...\n")
    
    # Prepare additional context for revisions
    revision_context = None
    if state.iteration > 0 and state.critique_md:
        revision_context = {
            "previous_report": state.feasibility_report,
            "critique": state.critique_md,
            "human_feedback": state.human_feedback,
            "iteration": state.iteration
        }
    
    # Generate feasibility questions
    result = generate_feasibility_questions(
        context_file_path=unified_context_path,
        development_context=state.development_context,
        session_id=session_id,
        revision_context=revision_context  # Pass revision context if available
    )
    
    # Validate thinking summary
    print(f"\n{'='*60}")
    print(f"Validating Stage 1: Thinking Summary")
    print(f"{'='*60}")
    thinking_validation = _validate_generation_result(result, "thinking_summary")
    print(f"Valid: {thinking_validation['is_valid']}")
    print(f"Has content: {thinking_validation['has_content']}")
    print(f"Content length: {thinking_validation['content_length']:,} chars")
    if thinking_validation['warnings']:
        for warning in thinking_validation['warnings']:
            print(f"⚠️  {warning}")
    print()
    
    # Validate feasibility report
    print(f"{'='*60}")
    print(f"Validating Stage 2: Feasibility Report")
    print(f"{'='*60}")
    report_validation = _validate_generation_result(result, "feasibility_report")
    print(f"Valid: {report_validation['is_valid']}")
    print(f"Has content: {report_validation['has_content']}")
    print(f"Content length: {report_validation['content_length']:,} chars")
    if report_validation['warnings']:
        for warning in report_validation['warnings']:
            print(f"⚠️  {warning}")
    print()
    
    # Update unified context file with feasibility report
    if report_validation['has_content']:
        update_success = _update_unified_context_with_report(
            unified_context_path,
            result.get("feasibility_report", "")
        )
        if not update_success:
            print(f"⚠️  WARNING: Failed to update unified context file with report")
    
    # Record this iteration in history
    revision_entry = {
        "iteration": state.iteration,
        "thinking_summary": result.get("thinking_summary", ""),
        "feasibility_report": result.get("feasibility_report", ""),
        "human_feedback": state.human_feedback if state.iteration > 0 else None,
        "critique": state.critique_md if state.iteration > 0 else None
    }
    
    # Build updated revision history
    updated_history = list(state.revision_history) if state.revision_history else []
    updated_history.append(revision_entry)
    
    # Save initial thinking summary if this is the first iteration
    initial_thinking = state.initial_thinking_summary
    if state.iteration == 0 and result.get("thinking_summary"):
        initial_thinking = result.get("thinking_summary", "")
        print(f"\n💾 Saving initial thinking summary ({len(initial_thinking):,} chars)")
        print(f"   This will be preserved throughout all revisions")
        
        # Save to file (pass unified_context_path to derive the correct directory)
        _save_initial_thinking_summary(initial_thinking, session_id, unified_context_path)
    
    # Note: Feasibility reports are saved by feasibility_handler.py with proper version control
    # No need to save here with timestamps
    
    print(f"\n{'#'*60}")
    print(f"# FEASIBILITY ASSESSMENT GENERATION COMPLETE")
    print(f"{'#'*60}\n")
    
    return {
        "thinking_summary": result.get("thinking_summary", ""),
        "feasibility_report": result.get("feasibility_report", ""),
        "unified_context_path": unified_context_path,
        "revision_history": updated_history,
        "initial_thinking_summary": initial_thinking,
        "status": "awaiting_human"  # After generation, wait for human review
    }


def _human_review_gate(state: FeasibilityState) -> dict:
    """
    Human review gate - pauses execution for human approval/feedback.
    
    This node uses interrupt() to pause the graph and wait for human input.
    Execution will resume when the API receives approval or feedback.
    """
    from langgraph.types import interrupt
    
    print(f"\n{'='*60}")
    print(f"🚦 HUMAN REVIEW GATE")
    print(f"Iteration: {state.iteration}")
    print(f"Status: {state.status}")
    print(f"{'='*60}\n")
    
    # Pause execution and wait for human decision
    # The interrupt will be resolved when the API endpoint receives:
    # - approved=True (continue to END)
    # - approved=False with human_feedback (continue to critique)
    human_decision = interrupt(
        {
            "type": "human_review_required",
            "session_id": state.session_id,
            "iteration": state.iteration,
            "feasibility_report": state.feasibility_report,
            "thinking_summary": state.thinking_summary,
            "message": "Awaiting human review of feasibility report"
        }
    )
    
    print(f"✅ Human decision received: {human_decision}")
    
    # Return empty dict - state updates will come from API
    return {}


def _generate_critique(state: FeasibilityState) -> dict:
    """
    Generate structured critique from human feedback.
    
    Converts natural language feedback into actionable critique using LLM.
    """
    from src.config.llm_config import model
    
    print(f"\n{'='*60}")
    print(f"📝 GENERATING CRITIQUE FROM FEEDBACK")
    print(f"Iteration: {state.iteration}")
    print(f"{'='*60}\n")
    
    if not state.human_feedback:
        print("⚠️  WARNING: No human feedback provided, skipping critique")
        return {"critique_md": "", "status": "revising"}
    
    print(f"Human feedback: {state.human_feedback[:200]}...\n")
    
    # Load critique prompt template
    prompt_path = Path("prompts/feasibility_critique.txt")
    
    if not prompt_path.exists():
        print(f"⚠️  WARNING: Critique prompt not found at {prompt_path}")
        # Fallback: use feedback directly as critique
        return {
            "critique_md": f"## User Feedback\n\n{state.human_feedback}",
            "status": "revising"
        }
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            critique_prompt_template = f.read()
        
        # Fill in the template
        critique_prompt = critique_prompt_template.format(
            feasibility_report=state.feasibility_report,
            human_feedback=state.human_feedback,
            iteration=state.iteration
        )
        
        # Generate critique using LLM
        critique_response = model.invoke(critique_prompt)
        critique_md = critique_response.content if hasattr(critique_response, 'content') else str(critique_response)
        
        print(f"✅ Critique generated ({len(critique_md)} chars)\n")
        
        return {
            "critique_md": critique_md,
            "status": "revising"
        }
        
    except Exception as e:
        print(f"❌ ERROR generating critique: {e}")
        # Fallback to using feedback directly
        return {
            "critique_md": f"## User Feedback\n\n{state.human_feedback}",
            "status": "revising"
        }


def _revise_assessment(state: FeasibilityState) -> dict:
    """
    Generate revised feasibility assessment based on critique.
    
    This node calls _generate_assessment again with revision context.
    """
    print(f"\n{'='*60}")
    print(f"🔄 REVISING ASSESSMENT")
    print(f"Iteration: {state.iteration} -> {state.iteration + 1}")
    print(f"{'='*60}\n")
    
    # Increment iteration counter
    new_iteration = state.iteration + 1
    
    # Check if max iterations reached
    if new_iteration >= state.max_iterations:
        print(f"⚠️  Max iterations ({state.max_iterations}) reached")
        return {
            "iteration": new_iteration,
            "status": "max_iterations_reached"
        }
    
    # Update iteration and status, then call generate_assessment
    print(f"Proceeding with revision {new_iteration}/{state.max_iterations}")
    
    return {
        "iteration": new_iteration,
        "status": "generating"
    }


def _should_continue_or_end(state: FeasibilityState) -> str:
    """
    Routing function to determine next step after human review gate.
    
    Returns:
        "approved" -> END (workflow complete)
        "needs_revision" -> critique node (generate critique from feedback)
        "max_iterations" -> END (max revisions reached)
    """
    print(f"\n{'='*60}")
    print(f"🔀 ROUTING DECISION")
    print(f"Status: {state.status}")
    print(f"Approved: {state.approved}")
    print(f"Iteration: {state.iteration}/{state.max_iterations}")
    print(f"{'='*60}\n")
    
    # Check if approved
    if state.approved is True:
        print("✅ Route: APPROVED -> END")
        return "approved"
    
    # Check if max iterations reached
    if state.iteration >= state.max_iterations:
        print("🛑 Route: MAX_ITERATIONS -> END")
        return "max_iterations"
    
    # Check if feedback provided for revision
    if state.approved is False and state.human_feedback:
        print("🔄 Route: NEEDS_REVISION -> critique")
        return "needs_revision"
    
    # Default: something went wrong, end workflow
    print("⚠️  Route: ERROR -> END (no valid decision)")
    return "approved"  # Default to ending


def get_feasibility_graph(state: FeasibilityState = None):
    """
    Build the feasibility assessment graph with HITL support.
    
    This is a singleton-like function that returns a compiled graph
    with persistent checkpointing for human-in-the-loop workflows.
    
    Args:
        state: Optional initial state (for backward compatibility)
        
    Returns:
        Compiled LangGraph with MemorySaver checkpointer
    """
    graph = StateGraph(FeasibilityState)
    
    # Add all nodes
    graph.add_node("generate_assessment", _generate_assessment)
    graph.add_node("human_review_gate", _human_review_gate)
    graph.add_node("generate_critique", _generate_critique)
    graph.add_node("revise_assessment", _revise_assessment)
    
    # Define workflow edges
    # START -> generate_assessment (initial generation or revision)
    graph.add_edge(START, "generate_assessment")
    
    # generate_assessment -> human_review_gate (always wait for human review)
    graph.add_edge("generate_assessment", "human_review_gate")
    
    # human_review_gate -> conditional routing based on approval
    graph.add_conditional_edges(
        "human_review_gate",
        _should_continue_or_end,
        {
            "approved": END,              # If approved, workflow complete
            "needs_revision": "generate_critique",  # If needs revision, generate critique
            "max_iterations": END          # If max iterations reached, end
        }
    )
    
    # generate_critique -> revise_assessment (convert feedback to critique)
    graph.add_edge("generate_critique", "revise_assessment")
    
    # revise_assessment -> generate_assessment (loop back for revision)
    graph.add_edge("revise_assessment", "generate_assessment")
    
    # Compile with checkpointer for state persistence
    return graph.compile(checkpointer=_checkpointer)


def get_checkpointer():
    """
    Get the global checkpointer instance.
    
    Returns:
        MemorySaver: The checkpointer used by the feasibility graph
    """
    return _checkpointer
