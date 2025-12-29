#!/usr/bin/env python3
"""CLI helper to run feasibility generation (and optional HITL revision) with token logging.

Example:
    python scripts/run_feasibility_token_report.py \
        --md-dir output/sample_session/parsed_md \
        --development-context docs/dev_context.json \
        --critique docs/sample_critique.txt \
        --revision-instructions docs/revision_instructions.txt

This script does not mock LLM calls; you must have valid API keys configured.
"""
import argparse
import json
import time
import uuid
from pathlib import Path

from src.app.feasibility_revision import revise_report
from src.core.session import Session
from src.routes.feasibility_handler import FeasibilityHandler
from src.utils.token_utils import diff, get_session_stats, reset_tracker, snapshot


def _read_optional_json(path_str: str | None):
    if not path_str:
        return None
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"Development context file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_text(path_str: str) -> str:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write_report(session_id: str, payload: dict) -> str:
    out_path = Path(f"output/session_{session_id[:8]}/token_report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return str(out_path)


def _run_feasibility(session: Session, development_context: dict | None) -> tuple[dict, dict]:
    handler = FeasibilityHandler(verbose=True)
    before = snapshot()
    result = handler.generate_feasibility(session=session, development_context=development_context)
    usage = diff(before)
    return result, usage


def _run_revision(session_id: str, feasibility_paths: dict, critique_path: str, instructions_path: str | None, max_revisions: int) -> tuple[dict, dict]:
    report_text = _read_text(feasibility_paths["feasibility_report_file"])
    thinking_text = _read_text(feasibility_paths["thinking_summary_file"])
    critique_text = _read_text(critique_path)
    instructions_text = _read_text(instructions_path) if instructions_path else None

    before = snapshot()
    revision_result = revise_report(
        session_id=session_id,
        current_version=1,
        feasibility_report_current=report_text,
        thinking_summary=thinking_text,
        human_critique=critique_text,
        revision_instructions=instructions_text,
        max_revisions=max_revisions,
    )
    usage = diff(before)
    return revision_result, usage


def main():
    parser = argparse.ArgumentParser(description="Run feasibility + optional revision with token logging")
    parser.add_argument("--md-dir", required=True, help="Directory containing parsed .md files for the session")
    parser.add_argument("--development-context", help="Path to JSON with development context (optional)")
    parser.add_argument("--critique", help="Path to human critique text file to trigger a revision run")
    parser.add_argument("--revision-instructions", help="Optional path to extra revision instructions")
    parser.add_argument("--session-id", help="Session ID to reuse; defaults to random")
    parser.add_argument("--max-revisions", type=int, default=5, help="Max revisions allowed (default 5)")
    parser.add_argument("--note", help="Optional note to include in token report")
    args = parser.parse_args()

    session_id = args.session_id or uuid.uuid4().hex[:12]
    print(f"Using session ID: {session_id}")

    session = Session(session_id=session_id)
    session.parsed_documents_dir = args.md_dir

    development_context = _read_optional_json(args.development_context)

    reset_tracker()
    run_started = time.time()

    feasibility_result, feasibility_usage = _run_feasibility(session, development_context)

    revision_result = None
    revision_usage = None
    if args.critique:
        revision_result, revision_usage = _run_revision(
            session_id=session_id,
            feasibility_paths=feasibility_result,
            critique_path=args.critique,
            instructions_path=args.revision_instructions,
            max_revisions=args.max_revisions,
        )

    totals = get_session_stats()
    full_snapshot = snapshot()

    payload = {
        "session_id": session_id,
        "note": args.note,
        "created_at": time.time(),
        "run_duration": time.time() - run_started,
        "feasibility": {
            "result": feasibility_result,
            "usage": feasibility_usage,
        },
        "revision": {
            "result": revision_result,
            "usage": revision_usage,
        } if args.critique else None,
        "totals": totals,
        "calls": full_snapshot.get("calls", []),
    }

    report_path = _write_report(session_id, payload)
    print("\nToken report saved to:")
    print(f"  {report_path}")
    print("\nTotals:")
    print(f"  Calls: {totals['total_calls']}\n  Input tokens: {totals['total_input_tokens']}\n  Output tokens: {totals['total_output_tokens']}\n  Total tokens: {totals['total_tokens']}")


if __name__ == "__main__":
    main()
