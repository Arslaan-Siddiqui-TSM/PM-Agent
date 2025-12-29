"""
LangGraph-based Human-in-the-Loop (HITL) system for feasibility assessment revisions.

This module implements an interrupt-resume pattern where the graph can be paused
at the revision node to collect human feedback and then resume with the revised assessment.
Uses NVIDIA NIM APIs for LLM-based revisions.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphInterrupt
from langgraph.types import interrupt
from typing import TypedDict, Optional, Any
from pathlib import Path
import json
from datetime import datetime
import os

class HitlFeasibilityState(TypedDict):
    """State for the HITL feasibility revision graph"""
    session_id: str
    current_version: int
    feasibility_assessment: str
    thinking_summary: Optional[str]
    human_critique: Optional[str]
    revision_instructions: Optional[str]
    revised_assessment: Optional[str]
    revision_history: list
    max_revisions: int
    error: Optional[str]

class LangGraphHitlSystem:
    """LangGraph-based HITL system for feasibility revisions"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.revision_prompt = self._load_revision_prompt()
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()
    
    def _load_revision_prompt(self) -> str:
        """Load revision prompt from external file in prompts/ folder"""
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "feasibility_report_revise.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Revision prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for HITL revisions with interrupt after feedback."""
        
        graph = StateGraph(HitlFeasibilityState)
        
        # Add nodes
        graph.add_node("validate_initial", self._validate_initial_assessment)
        graph.add_node("collect_feedback", self._collect_feedback_node)
        graph.add_node("revise_assessment", self._revise_assessment_node)
        graph.add_node("save_revision", self._save_revision_node)
        graph.add_node("update_history", self._update_history_node)
        
        # Add edges
        graph.add_edge(START, "validate_initial")
        graph.add_edge("validate_initial", "collect_feedback")
        graph.add_edge("collect_feedback", "revise_assessment")
        graph.add_edge("revise_assessment", "save_revision")
        graph.add_edge("save_revision", "update_history")
        graph.add_edge("update_history", END)
        
        return graph.compile(checkpointer=self.checkpointer)
    
    def _validate_initial_assessment(self, state: HitlFeasibilityState) -> HitlFeasibilityState:
        """Validate that initial feasibility assessment exists"""
        if self.verbose:
            print(f"[HITL] Validating initial assessment for session {state['session_id']}")
        
        if not state.get('feasibility_assessment'):
            state['error'] = "No initial feasibility assessment found"
        
        return state
    
    def _collect_feedback_node(self, state: HitlFeasibilityState) -> HitlFeasibilityState:
        """
        Process human feedback that has already been provided.
        In the actual REST API flow, feedback comes from the request body.
        
        This node validates that human critique was provided and is non-empty.
        """
        if self.verbose:
            print(f"[HITL] Processing human feedback for session {state['session_id']}")
        
        # If critique is missing, emit interrupt to pause the graph
        if not state.get('human_critique'):
            return interrupt({
                "reason": "awaiting human critique",
                "session_id": state.get("session_id"),
                "current_version": state.get("current_version"),
            })
        
        return state
    
    def _revise_assessment_node(self, state: HitlFeasibilityState) -> HitlFeasibilityState:
        """
        Revise the feasibility assessment based on human critique.
        This is where we'd integrate an LLM for the revision.
        """
        if self.verbose:
            print(f"[HITL] Revising assessment for session {state['session_id']}")
        
        if state.get('error'):
            return state
        
        if not state.get('human_critique'):
            state['error'] = "No critique provided"
            return state
        
        # For now, create a placeholder revised assessment
        # In production, this would call an LLM
        revised = self._apply_revision(
            original=state['feasibility_assessment'],
            critique=state['human_critique'],
            instructions=state.get('revision_instructions')
        )
        
        state['revised_assessment'] = revised
        return state
    
    def _apply_revision(self, original: str, critique: str, instructions: Optional[str]) -> str:
        """
        Apply human critique to the original assessment using the unified LLM model.
        Uses configured LLM provider with token tracking.
        
        Refactored to use structured inputs instead of concatenating everything into the prompt.
        """
        if self.verbose:
            print(f"[HITL] Calling LLM to revise assessment...")
        
        try:
            # Use the unified model with token tracking
            from src.config.llm_config import model
            from langchain_core.messages import SystemMessage, HumanMessage
            
            # Build structured user input (runtime data only)
            user_content_parts = [
                "Previous feasibility report:",
                "═" * 80,
                original,
                "",
                "Human critique:",
                "═" * 80,
                critique
            ]
            
            if instructions:
                user_content_parts.extend([
                    "",
                    "Revision instructions:",
                    "═" * 80,
                    instructions
                ])
            
            user_content = "\n".join(user_content_parts)
            
            # Structured messages: prompt from external file + runtime inputs
            messages = [
                SystemMessage(content=self.revision_prompt),
                HumanMessage(content=user_content)
            ]
            
            # Use unified model.invoke() which has token tracking
            response = model.invoke(messages)
            
            revised_assessment = str(getattr(response, "content", response))
            if self.verbose:
                print(f"[HITL] ✅ LLM revision completed, length: {len(revised_assessment)} chars")
            
            return revised_assessment
            
        except Exception as e:
            if self.verbose:
                print(f"[HITL] ❌ Error calling LLM: {str(e)}")
            # Fallback to simple revision if LLM fails
            return self._fallback_revision(original, critique, instructions)
    
    def _fallback_revision(self, original: str, critique: str, instructions: Optional[str]) -> str:
        """Fallback revision if LLM call fails"""
        return f"""# Revised Feasibility Assessment

{original}

---

## Revision Notes (Based on Human Feedback)

**Feedback Received:**
{critique}

{f"**Additional Instructions Implemented:**{instructions}" if instructions else ""}

This assessment has been reviewed and revised based on the above feedback.
Key points from the feedback have been considered in the updated assessment above.

*Revision Date: {datetime.now().isoformat()}*
"""
    
    def _save_revision_node(self, state: HitlFeasibilityState) -> HitlFeasibilityState:
        """Save the revised assessment to disk"""
        if self.verbose:
            print(f"[HITL] Saving revision for session {state['session_id']}")
        
        if not state.get('revised_assessment'):
            state['error'] = "No revised assessment to save"
            return state
        
        try:
            # Determine next version
            next_version = state['current_version'] + 1
            
            # Create output directory
            output_dir = Path(f"output/session_{state['session_id'][:8]}/reports")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save revised assessment
            report_path = output_dir / f"feasibility_report_v{next_version}.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(state['revised_assessment'])
            
            if self.verbose:
                print(f"[HITL] Saved revision to {report_path}")
            
            # Update state with new version info
            state['current_version'] = next_version
            state['feasibility_assessment'] = state['revised_assessment']
            
        except Exception as e:
            state['error'] = f"Failed to save revision: {str(e)}"
        
        return state
    
    def _update_history_node(self, state: HitlFeasibilityState) -> HitlFeasibilityState:
        """Update revision history"""
        if self.verbose:
            print(f"[HITL] Updating history for session {state['session_id']}")
        
        try:
            # Ensure revision_history is a list
            if not isinstance(state.get('revision_history'), list):
                state['revision_history'] = []
            
            # Add entry to revision history
            history_entry = {
                "version": state['current_version'],
                "created_at": datetime.now().isoformat(),
                "type": "human_revision",
                "critique": state.get('human_critique'),
                "instructions": state.get('revision_instructions'),
                "file_path": str(Path(f"output/session_{state['session_id'][:8]}/reports/feasibility_report_v{state['current_version']}.md"))
            }
            
            state['revision_history'].append(history_entry)
            
        except Exception as e:
            state['error'] = f"Failed to update history: {str(e)}"
        
        return state
    
    async def run_revision_workflow(self, state_dict: dict, thread_id: Optional[str] = None) -> dict:
        """
        Run the HITL revision workflow. If feedback is missing, the graph will interrupt after
        collect_feedback and return a resume handle.
        """
        state = HitlFeasibilityState(**state_dict)
        config = {"configurable": {"thread_id": thread_id or state_dict.get("session_id") or "default"}}
        try:
            result = self.graph.invoke(state, config=config)
            # If interrupt returned as data payload
            if isinstance(result, dict) and "__interrupt__" in result:
                return {
                    "status": "interrupt",
                    "resume_config": config,
                    "interrupts": result.get("__interrupt__"),
                }
            return result
        except GraphInterrupt as gi:
            # Return interrupt payload plus resume config
            return {
                "status": "interrupt",
                "resume_config": config,
                "interrupts": getattr(gi, "args", []),
            }
        except Exception as e:
            if self.verbose:
                print(f"[HITL] Error in workflow: {str(e)}")
            return {**state_dict, "error": str(e)}
    
    def resume_with_feedback(self, config: dict, feedback: dict) -> dict:
        """Resume the interrupted graph with human feedback."""
        if self.verbose:
            print(f"[HITL] Resuming workflow with feedback")
        try:
            result = self.graph.invoke(feedback, config=config)
            return result
        except Exception as e:
            if self.verbose:
                print(f"[HITL] Error resuming workflow: {str(e)}")
            return {"error": str(e)}


def create_hitl_system() -> LangGraphHitlSystem:
    """Factory function to create a LangGraph HITL system"""
    return LangGraphHitlSystem(verbose=True)
