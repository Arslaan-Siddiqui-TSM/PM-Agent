"""
LangGraph workflow for Human-in-the-Loop (HITL) Reflection Pattern.

Workflow:
    START → Draft (LLM) → Draft Review (Interrupt) → Reflect (LLM) → Reflection Review (Interrupt) → Revise (LLM) → END or LOOP

Key Features:
- Human reviewers can edit AI outputs directly
- Supports approve, feedback, or terminate actions
- Max 5 iterations with human-enforced termination
- State persisted via checkpointer for interrupt/resume
"""

from __future__ import annotations

from typing import Literal
import uuid

from langgraph.graph import END, StateGraph, START
from langgraph.checkpoint.memory import MemorySaver

from src.app.draft import generate_draft
from src.app.reflect import generate_reflection
from src.app.revise import apply_revision
from src.app.hitl_nodes import human_review_draft, human_review_reflection
from src.states.reflection_state import ReflectionState


def _route_after_draft_review(state: ReflectionState) -> Literal["reflect", "finalize"]:
    """
    Route after human reviews the draft.
    
    - If human terminated → finalize
    - Otherwise → reflect (with or without edits/feedback)
    """
    if state.terminated_by_human:
        return "finalize"
    return "reflect"


def _route_after_reflection_review(state: ReflectionState) -> Literal["revise", "finalize"]:
    """
    Route after human reviews the reflection.
    
    - If human terminated → finalize
    - Otherwise → revise (with approved or edited critique)
    """
    if state.terminated_by_human:
        return "finalize"
    return "revise"


def _route_after_revision(state: ReflectionState) -> Literal["draft", "finalize"]:
    """
    Route after revision decision.
    
    - If final_plan is set (accept or forced-accept) → finalize
    - Otherwise → draft (another iteration)
    """
    if state.final_plan is not None:
        return "finalize"
    return "draft"


def _finalize_node(state: ReflectionState) -> dict:
    """
    Finalize the plan generation.
    
    This node ensures final_plan is always set before ending:
    - If terminated_by_human, use current_draft
    - If final_plan not set, use current_draft as fallback
    """
    if state.final_plan is None and state.current_draft is not None:
        # Safeguard: if we reach finalize without explicitly setting final_plan,
        # return the latest draft as the final result.
        return {"final_plan": state.current_draft}
    return {}


def get_graph(state: ReflectionState, enable_hitl: bool = True, checkpointer=None):
    """
    Build the reflection-style reasoning graph with optional HITL.
    
    Args:
        state: Initial ReflectionState
        enable_hitl: If True, includes human review interrupt nodes (default: True)
        checkpointer: Optional external checkpointer for state persistence.
                     If None, uses MemorySaver (in-memory only).
    
    Returns:
        Compiled StateGraph with checkpointer for interrupt/resume support
    
    Graph Topology (with HITL):
        START → draft → draft_review → reflect → reflection_review → revise → [draft or finalize] → END
    
    Graph Topology (without HITL):
        START → draft → reflect → revise → [draft or finalize] → END
    """

    if not state:
        return None

    graph = StateGraph(ReflectionState)

    # Add LLM nodes
    graph.add_node("draft", generate_draft)
    graph.add_node("reflect", generate_reflection)
    graph.add_node("revise", apply_revision)
    graph.add_node("finalize", _finalize_node)
    
    if enable_hitl:
        # Add HITL interrupt nodes
        graph.add_node("draft_review", human_review_draft)
        graph.add_node("reflection_review", human_review_reflection)
        
        # Build HITL workflow:
        # START → draft → draft_review → reflect → reflection_review → revise → [draft or finalize]
        graph.add_edge(START, "draft")
        graph.add_edge("draft", "draft_review")
        graph.add_conditional_edges("draft_review", _route_after_draft_review)
        graph.add_edge("reflect", "reflection_review")
        graph.add_conditional_edges("reflection_review", _route_after_reflection_review)
        graph.add_conditional_edges("revise", _route_after_revision)
        graph.add_edge("finalize", END)
    else:
        # Build non-HITL workflow (original):
        # START → draft → reflect → revise → [draft or finalize]
        graph.add_edge(START, "draft")
        graph.add_edge("draft", "reflect")
        graph.add_edge("reflect", "revise")
        graph.add_conditional_edges("revise", _route_after_revision)
        graph.add_edge("finalize", END)

    # Compile with provided checkpointer or default MemorySaver
    if checkpointer is None:
        checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


def get_graph_without_hitl(state: ReflectionState, checkpointer=None):
    """
    Build the reflection-style reasoning graph WITHOUT HITL.
    
    Use this for batch processing or when human review is not needed.
    
    Args:
        state: Initial ReflectionState
        checkpointer: Optional external checkpointer
    
    Returns:
        Compiled StateGraph without interrupt nodes
    """
    return get_graph(state, enable_hitl=False, checkpointer=checkpointer)


def generate_thread_id() -> str:
    """Generate a unique thread ID for checkpointing."""
    return str(uuid.uuid4())


def generate_request_id() -> str:
    """Generate a unique request ID for HITL tracking."""
    return str(uuid.uuid4())
