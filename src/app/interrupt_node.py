"""
Interrupt node for Human-in-the-Loop (HITL) workflow.

This node triggers an interrupt BETWEEN the reflect and human_review nodes.
It simply calls interrupt() and returns the human input when the graph resumes.

This is the CORRECT pattern for LangGraph interrupts:
- Generate data in one node (reflect)
- Interrupt in a separate node (this node)
- Process human response in the next node (human_review)

This ensures that reflect doesn't re-execute on resume, preventing UUID mismatches.
"""

from typing import Dict, Any
from langgraph.types import interrupt
from src.states.reflection_state import ReflectionState
from src.utils.helper import get_global_logger


def interrupt_for_review(state: ReflectionState, config: dict | None = None) -> Dict[str, Any]:
    """
    Trigger an interrupt to wait for human review.
    
    This node:
    1. Receives state from reflect (with request_id, pending review file already created)
    2. Calls interrupt() to pause the graph
    3. On resume, returns the human input to be processed by human_review node
    
    Args:
        state: ReflectionState with request_id set by reflect node
        config: LangGraph config with thread_id
    
    Returns:
        Dict with human_feedback when graph resumes
    """
    logger = get_global_logger()
    
    # Extract thread_id from config if available
    thread_id = None
    if config and isinstance(config, dict):
        thread_id = config.get("configurable", {}).get("thread_id")
    
    if logger:
        logger.logger.info(
            f"🛑 HITL: Interrupt node reached\n"
            f"   Request ID: {state.request_id}\n"
            f"   Thread ID: {thread_id or 'unknown'}\n"
            f"   Iteration: {len(state.iterations) if state.iterations else 0}\n"
            f"   About to call interrupt()..."
        )
    
    # Call interrupt() - this pauses the graph
    # On resume, human_input will contain the feedback from the API
    interrupt_payload = {
        "type": "human_review_required",
        "request_id": state.request_id,
        "iteration": len(state.iterations) if state.iterations else 0,
        "message": "Waiting for human review of the draft plan"
    }
    
    # Include thread_id in payload if available
    if thread_id:
        interrupt_payload["thread_id"] = thread_id
    
    human_input = interrupt(interrupt_payload)
    
    if logger:
        logger.logger.info(
            f"✅ HITL: Execution resumed\n"
            f"   Received action: {human_input.get('action') if isinstance(human_input, dict) else 'unknown'}\n"
            f"   Request ID from input: {human_input.get('request_id') if isinstance(human_input, dict) else 'unknown'}"
        )
    
    # When resumed, return the human input so human_review node can process it
    # Store the entire human_input dict in state.human_feedback
    return {
        "human_feedback": human_input
    }
