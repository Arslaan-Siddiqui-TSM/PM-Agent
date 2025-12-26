"""
Centralized service for managing LangGraph execution and resume operations.

This singleton service manages the graph lifecycle, checkpointing, and provides
methods for starting new executions and resuming paused ones.

Uses MemorySaver for in-memory checkpointing, which keeps state only during
the application runtime. For persistent checkpoints across restarts, consider
switching to SqliteSaver.

Updated for HITL Reflection Pattern with two interrupt points:
- draft_review: After draft generation
- reflection_review: After reflection generation
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.app.graph import get_graph
from src.states.reflection_state import ReflectionState
from src.utils.helper import get_global_logger


class GraphRunner:
    """
    Singleton service for managing LangGraph execution.

    Handles:
    - Graph initialization with in-memory checkpointer (MemorySaver)
    - Starting new graph executions with thread management
    - Resuming paused executions via Command(resume=...)
    
    Note: Uses MemorySaver for checkpointing. State is stored in-memory
    and will be lost when the application restarts.
    """

    _instance: Optional["GraphRunner"] = None
    _graph: Any = None  # CompiledGraph type
    _checkpointer: Any = None  # MemorySaver type

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the graph runner with in-memory checkpointer."""
        if self._graph is None:
            self._initialize_graph()

    def _initialize_graph(self, enable_hitl: bool = True):
        """
        Initialize the compiled graph with MemorySaver checkpointer.

        Args:
            enable_hitl: Whether to enable HITL interrupt nodes (default: True)
        """
        logger = get_global_logger()

        try:
            # Use MemorySaver for in-memory checkpointing
            self._checkpointer = MemorySaver()

            if logger:
                logger.logger.info("Checkpointer initialized: MemorySaver (in-memory)")
        except Exception as e:
            if logger:
                logger.logger.error(f"Failed to initialize checkpointer: {e}")
            raise

        # Create a dummy state to get the compiled graph
        # The get_graph function expects a state parameter
        dummy_state = ReflectionState()

        # Get graph with our in-memory checkpointer
        self._graph = get_graph(
            dummy_state, enable_hitl=enable_hitl, checkpointer=self._checkpointer
        )

        if logger:
            logger.logger.info(
                f"GraphRunner initialized with compiled graph (HITL={'enabled' if enable_hitl else 'disabled'})"
            )

    def get_graph(self):
        """Get the compiled graph instance."""
        if self._graph is None:
            self._initialize_graph()
        return self._graph

    def get_checkpointer(self) -> Any:
        """Get the checkpointer instance."""
        if self._checkpointer is None:
            self._initialize_graph()
        return self._checkpointer

    def resume_execution(
        self, thread_id: str, human_input: Dict[str, Any], request_id: str
    ) -> Dict[str, Any]:
        """
        Resume a paused graph execution with human input.

        This method uses Command(resume=...) to inject the human reviewer's
        decision back into the paused graph. The interrupt() call in the
        reflect node will return this human_input value.

        Args:
            thread_id: The thread/conversation ID from the original run
            human_input: The reviewer's decision payload (approve/feedback)
            request_id: UUID of the review request (for logging)

        Returns:
            Final state after resume (dict with final_plan, iterations, etc.)

        Raises:
            Exception: If resume fails (checkpoint not found, graph error, etc.)
        """
        logger = get_global_logger()

        try:
            if logger:
                logger.logger.info(
                    f"HITL Resume: Resuming graph execution | request_id={request_id} | thread_id={thread_id} | action={human_input.get('action')}"
                )
                logger.logger.debug(
                    f"HITL Resume: Full human_input payload: {json.dumps(human_input, ensure_ascii=False, default=str)}"
                )

            # Create config with thread_id for checkpoint retrieval
            # This tells LangGraph which execution to resume
            config: Dict[str, Any] = {"configurable": {"thread_id": thread_id}}

            # Resume the graph with Command
            # Command(resume=...) signals LangGraph to continue from the interrupt
            # The value passed to resume becomes the return value of interrupt()
            if logger:
                logger.logger.info(
                    f"HITL Resume: Calling graph.invoke with Command(resume=...) for thread_id={thread_id}"
                )

            result = self._graph.invoke(  # type: ignore
                Command(resume=human_input), config=config
            )

            if logger:
                logger.logger.info(
                    f"HITL Resume: Graph resumed successfully\n"
                    f"  thread_id={thread_id}\n"
                    f"  request_id={request_id}\n"
                    f"  result type: {type(result)}\n"
                    f"  result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}\n"
                    f"  has_final_plan={bool(result.get('final_plan')) if isinstance(result, dict) else 'N/A'}\n"
                    f"  result_request_id={result.get('request_id') if isinstance(result, dict) else 'N/A'}\n"
                    f"  has___interrupt__={'__interrupt__' in result if isinstance(result, dict) else 'N/A'}"
                )

                # If there's an interrupt, log its details
                if isinstance(result, dict) and "__interrupt__" in result:
                    interrupt_data = result.get("__interrupt__")
                    logger.logger.info(
                        f"HITL Resume: GRAPH INTERRUPTED AGAIN!\n"
                        f"  Interrupt data: {interrupt_data}"
                    )

                logger.logger.debug(
                    f"HITL Resume: Full result keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}"
                )

            return result

        except Exception as e:
            if logger:
                logger.logger.error(
                    f"HITL Resume: Failed to resume graph\n"
                    f"  thread_id={thread_id}\n"
                    f"  request_id={request_id}\n"
                    f"  error={e}",
                    exc_info=True,
                )
            raise

    def start_execution(
        self, initial_state: Dict[str, Any], thread_id: str
    ) -> Dict[str, Any]:
        """
        Start a new graph execution.

        Args:
            initial_state: Initial state for the graph (ReflectionState dict)
            thread_id: Thread ID for this execution (used for checkpointing)

        Returns:
            Final state or interrupt payload if graph pauses

        Raises:
            Exception: If graph execution fails
        """
        logger = get_global_logger()

        try:
            config: Dict[str, Any] = {"configurable": {"thread_id": thread_id}}

            if logger:
                logger.logger.info(
                    f"HITL: Starting new graph execution\n  thread_id={thread_id}"
                )

            result = self._graph.invoke(initial_state, config=config)  # type: ignore

            if logger:
                # Check if execution paused (has __interrupt__ key)
                if isinstance(result, dict) and "__interrupt__" in result:
                    logger.logger.info(
                        f"HITL: Graph paused at interrupt\n"
                        f"  thread_id={thread_id}\n"
                        f"  interrupt_count={len(result['__interrupt__'])}"
                    )
                else:
                    logger.logger.info(
                        f"HITL: Graph execution completed\n  thread_id={thread_id}"
                    )

            return result

        except Exception as e:
            if logger:
                logger.logger.error(
                    f"HITL: Failed to start graph\n"
                    f"  thread_id={thread_id}\n"
                    f"  error={e}",
                    exc_info=True,
                )
            raise


# Global singleton instance
_graph_runner: Optional[GraphRunner] = None


def get_graph_runner() -> GraphRunner:
    """
    Get the global GraphRunner singleton instance.

    This ensures a single graph instance is shared across all API requests,
    with a shared in-memory checkpointer for state management.

    Returns:
        GraphRunner: The singleton instance
    """
    global _graph_runner

    if _graph_runner is None:
        _graph_runner = GraphRunner()

    return _graph_runner


def cleanup_graph_runner():
    """
    Cleanup the GraphRunner singleton.

    Call this when shutting down the application.
    Note: MemorySaver doesn't require connection cleanup.
    """
    global _graph_runner

    if _graph_runner is not None:
        logger = get_global_logger()
        if logger:
            logger.logger.info("GraphRunner cleaned up (MemorySaver - no connection to close)")
        _graph_runner = None
