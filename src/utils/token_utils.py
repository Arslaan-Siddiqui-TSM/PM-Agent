"""
Token tracking utilities for LLM calls.

This module provides convenient functions for tracking and displaying
token usage across LLM calls in your scripts.
"""

from src.config.llm_config import session_tracker
import atexit
import json
import time
from pathlib import Path


def enable_auto_summary():
    """
    Automatically display session summary when the script exits.
    
    Usage:
        from src.utils.token_utils import enable_auto_summary
        
        # Call this at the start of your script
        enable_auto_summary()
        
        # Make your LLM calls...
        # Session summary will be displayed automatically when script ends
    """
    atexit.register(session_tracker.print_summary)


def print_summary():
    """
    Manually display the current session summary.
    
    Usage:
        from src.utils.token_utils import print_summary
        
        # At any point in your script
        print_summary()
    """
    session_tracker.print_summary()


def reset_tracker():
    """
    Reset the session tracker to start fresh.
    
    Usage:
        from src.utils.token_utils import reset_tracker
        
        # After completing a workflow
        reset_tracker()
    """
    session_tracker.reset()


def get_session_stats():
    """
    Get current session statistics as a dictionary.
    
    Returns:
        dict: Session statistics including:
            - total_calls: Number of LLM calls made
            - total_input_tokens: Total input tokens used
            - total_output_tokens: Total output tokens generated
            - total_tokens: Combined token usage
            - session_duration: Time elapsed since first call
    
    Usage:
        from src.utils.token_utils import get_session_stats
        
        stats = get_session_stats()
        print(f"Used {stats['total_tokens']:,} tokens")
    """
    return {
        'total_calls': len(session_tracker.calls),
        'total_input_tokens': session_tracker.total_input,
        'total_output_tokens': session_tracker.total_output,
        'total_tokens': session_tracker.total_input + session_tracker.total_output,
        'session_duration': time.time() - session_tracker.session_start
    }


def snapshot():
    """Take a point-in-time snapshot of usage counters and calls."""
    return {
        'totals': get_session_stats(),
        'calls': list(session_tracker.calls),
    }


def diff(start_snapshot: dict) -> dict:
    """Compute delta between now and a prior snapshot."""
    current = snapshot()
    start_totals = start_snapshot.get('totals', {})
    current_totals = current.get('totals', {})
    return {
        'calls_delta': len(current.get('calls', [])) - len(start_snapshot.get('calls', [])),
        'input_tokens_delta': current_totals.get('total_input_tokens', 0) - start_totals.get('total_input_tokens', 0),
        'output_tokens_delta': current_totals.get('total_output_tokens', 0) - start_totals.get('total_output_tokens', 0),
        'total_tokens_delta': current_totals.get('total_tokens', 0) - start_totals.get('total_tokens', 0),
        'duration_delta': current_totals.get('session_duration', 0.0) - start_totals.get('session_duration', 0.0),
        'calls': current.get('calls', [])[len(start_snapshot.get('calls', [])):] if current.get('calls') else [],
    }


def export_stats(session_id: str, note: str | None = None, output_path: str | Path | None = None) -> str:
    """Persist session token stats (totals + per-call) to JSON and return the path."""
    output_path = Path(output_path) if output_path else Path(f"output/session_{session_id[:8]}/token_usage.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'session_id': session_id,
        'created_at': time.time(),
        'note': note,
        'totals': get_session_stats(),
        'calls': list(session_tracker.calls),
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return str(output_path)


# Convenience alias
show_summary = print_summary

