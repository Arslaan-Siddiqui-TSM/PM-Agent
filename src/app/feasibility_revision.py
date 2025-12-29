"""
Feasibility Report Revision (HITL)

Core module for human-in-the-loop revision of feasibility reports.
Handles version management, LLM invocation, and output validation.
"""

import json
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from src.config.llm_config import model
from src.states.revision_state import RevisionState
from rich.console import Console


console = Console()


# ============================================================================
# Extraction & Parsing Helpers
# ============================================================================

def _extract_revision_report(content: str) -> str:
    """
    Extract revised feasibility report from LLM response.
    
    Looks for delimiters:
    ---REVISION_REPORT_START---
    [REVISED REPORT]
    ---REVISION_REPORT_END---
    
    Args:
        content: Raw LLM response string
        
    Returns:
        str: Extracted revised report markdown
    """
    console.print("[bold yellow]DEBUG:[/bold yellow] Extracting revised report from LLM response")
    
    # Strip code fences if present
    content_stripped = content.strip()
    if content_stripped.startswith("```") and content_stripped.endswith("```"):
        console.print("[bold yellow]DEBUG:[/bold yellow] Stripping surrounding code fences")
        content_body = content_stripped[3:]
        nl = content_body.find("\n")
        if nl != -1:
            content_body = content_body[nl+1:]
        content_stripped = content_body.rstrip("`").strip()
    
    # Extract via regex
    pattern = re.compile(
        r"---REVISION_REPORT_START---\s*(.*?)\s*---REVISION_REPORT_END---",
        re.DOTALL
    )
    
    match = pattern.search(content_stripped)
    if match:
        revised_report = match.group(1).strip()
        console.print(f"[bold green]DEBUG:[/bold green] Extracted revised report (len={len(revised_report)})")
        return revised_report
    
    # Fallback: use entire content
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Delimiters not found, using entire response as report")
    return content_stripped


def _extract_revision_summary(content: str) -> str:
    """
    Extract revision summary from LLM response.
    
    Looks for delimiters:
    ---REVISION_SUMMARY_START---
    [SUMMARY]
    ---REVISION_SUMMARY_END---
    
    Args:
        content: Raw LLM response string
        
    Returns:
        str: Extracted revision summary
    """
    console.print("[bold yellow]DEBUG:[/bold yellow] Extracting revision summary from LLM response")
    
    pattern = re.compile(
        r"---REVISION_SUMMARY_START---\s*(.*?)\s*---REVISION_SUMMARY_END---",
        re.DOTALL
    )
    
    match = pattern.search(content)
    if match:
        summary = match.group(1).strip()
        console.print(f"[bold green]DEBUG:[/bold green] Extracted revision summary (len={len(summary)})")
        return summary
    
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Revision summary delimiters not found, returning empty")
    return ""


# ============================================================================
# Validation Helpers
# ============================================================================

def _validate_revised_report(report: str) -> bool:
    """
    Validate that revised report is well-formed.
    
    Checks:
    - Not empty
    - Minimum length (≥ 3000 chars to ensure substantial content)
    - Valid Markdown (has headers)
    - Maximum length (≤ 8500 chars for safety)
    
    Args:
        report: Revised report markdown
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not report or not report.strip():
        console.print("[bold red]ERROR:[/bold red] Revised report is empty")
        return False
    
    report_len = len(report)
    if report_len < 3000:
        console.print(f"[bold red]ERROR:[/bold red] Revised report too short ({report_len} < 3000 chars)")
        return False
    
    if report_len > 8500:
        console.print(f"[bold red]ERROR:[/bold red] Revised report too long ({report_len} > 8500 chars)")
        return False
    
    # Check for markdown headers
    if not re.search(r'^#+\s', report, re.MULTILINE):
        console.print("[bold red]ERROR:[/bold red] Revised report missing markdown headers")
        return False
    
    console.print(f"[bold green]DEBUG:[/bold green] Revised report validation passed (len={report_len})")
    return True


def _preserve_verdict(previous_report: str, revised_report: str) -> bool:
    """
    Verify that verdict is preserved between versions.
    
    Simple heuristic: check if feasibility verdict keywords present in both.
    Keywords: "Feasible", "Not Feasible", "Conditionally Feasible"
    
    Args:
        previous_report: Previous version markdown
        revised_report: Revised version markdown
        
    Returns:
        bool: True if verdict preserved, False otherwise
    """
    verdicts = ["Feasible", "Not Feasible", "Conditionally Feasible"]
    
    previous_verdicts = [v for v in verdicts if v.lower() in previous_report.lower()]
    revised_verdicts = [v for v in verdicts if v.lower() in revised_report.lower()]
    
    if previous_verdicts and not revised_verdicts:
        console.print(f"[bold red]ERROR:[/bold red] Verdict lost in revision: {previous_verdicts} not found in revised")
        return False
    
    console.print(f"[bold green]DEBUG:[/bold green] Verdict preservation check passed")
    return True


# ============================================================================
# Version Management
# ============================================================================

def _get_next_version(current_version: int, max_revisions: int = 5) -> int:
    """
    Calculate next version number.
    
    Args:
        current_version: Current version (1, 2, 3...)
        max_revisions: Maximum allowed revisions (v1 → v2 → v3 → v4 → v5)
        
    Returns:
        int: Next version number
        
    Raises:
        ValueError: If max revisions reached
    """
    next_version = current_version + 1
    if next_version > max_revisions:
        raise ValueError(
            f"Maximum revision limit reached. "
            f"Current: v{current_version}, Max: v{max_revisions}. "
            f"Cannot create v{next_version}."
        )
    return next_version


def _get_report_path(session_id: str, version: int) -> Path:
    """
    Get standard path for feasibility_report_vN.md.
    
    Args:
        session_id: Session ID
        version: Report version number (1, 2, 3...)
        
    Returns:
        Path: Path to feasibility_report_vN.md
    """
    session_dir = Path(f"output/session_{session_id[:8]}/reports")
    return session_dir / f"feasibility_report_v{version}.md"


def _get_revision_dir(session_id: str) -> Path:
    """
    Get standard directory for revision artifacts.
    
    Args:
        session_id: Session ID
        
    Returns:
        Path: Path to revisions directory
    """
    revision_dir = Path(f"output/session_{session_id[:8]}/revisions")
    revision_dir.mkdir(parents=True, exist_ok=True)
    return revision_dir


# ============================================================================
# Prompt Building
# ============================================================================

def _build_revision_prompt(
    current_report: str,
    thinking_summary: str,
    human_critique: str,
    revision_instructions: Optional[str] = None
) -> str:
    """
    Build revision prompt for LLM.
    
    Combines revision template with actual artifacts.
    
    Args:
        current_report: Current feasibility_report_vN.md content
        thinking_summary: Original thinking_summary.md content
        human_critique: User feedback
        revision_instructions: Optional structured guidance
        
    Returns:
        str: Full prompt for LLM
    """
    console.print("[bold yellow]DEBUG:[/bold yellow] Building revision prompt")
    
    # Load revision template
    template_path = Path(__file__).parent.parent.parent / "prompts" / "feasibility_report_revise.txt"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        console.print(f"[bold green]DEBUG:[/bold green] Revision template loaded ({len(template)} chars)")
    except Exception as e:
        console.print(f"[bold red]ERROR:[/bold red] Failed to load revision template: {e}")
        raise
    
    # Build user message with all four sections
    sections = [
        f"SECTION 1: Current Feasibility Report",
        f"─" * 50,
        current_report,
        "",
        f"SECTION 2: Original Thinking Summary",
        f"─" * 50,
        thinking_summary,
        "",
        f"SECTION 3: Human Critique",
        f"─" * 50,
        human_critique,
    ]
    
    if revision_instructions:
        sections.extend([
            "",
            f"SECTION 4: Revision Instructions",
            f"─" * 50,
            revision_instructions,
        ])
    
    user_message = "\n\n".join(sections)
    
    # Combine template + user message
    full_prompt = f"{template}\n\n{'='*80}\n\nINPUT:\n\n{user_message}"
    
    prompt_len = len(full_prompt)
    console.print(f"[bold green]DEBUG:[/bold green] Revision prompt built ({prompt_len} chars)")
    console.print(f"[cyan]  - Template: {len(template)} chars")
    console.print(f"[cyan]  - User message: {len(user_message)} chars")
    
    return full_prompt


# ============================================================================
# LLM Invocation with Retry
# ============================================================================

def _invoke_revision_with_retry(
    prompt: str,
    max_retries: int = 3,
    initial_backoff: float = 1.0
) -> str:
    """
    Invoke revision LLM with exponential backoff retry.
    
    Args:
        prompt: Full revision prompt
        max_retries: Maximum number of attempts
        initial_backoff: Initial backoff delay (seconds)
        
    Returns:
        str: LLM response content
        
    Raises:
        Exception: If all retries fail
    """
    for attempt in range(max_retries):
        try:
            console.print(f"[bold cyan]Revision LLM invocation (attempt {attempt+1}/{max_retries})[/bold cyan]")
            result = model.invoke(prompt)
            content = str(getattr(result, "content", result))
            console.print(f"[bold green]✓ LLM invocation successful[/bold green]")
            return content
            
        except Exception as e:
            console.print(f"[bold red]✗ LLM invocation failed: {e}[/bold red]")
            
            if attempt == max_retries - 1:
                console.print(f"[bold red]ERROR:[/bold red] All {max_retries} retries failed")
                raise
            
            backoff = initial_backoff * (2 ** attempt)
            console.print(f"[bold yellow]Retrying in {backoff:.1f}s...[/bold yellow]")
            time.sleep(backoff)
    
    # Should not reach here
    raise RuntimeError("Unexpected: exhausted retries without exception")


# ============================================================================
# Main Revision Function
# ============================================================================

def revise_report(
    session_id: str,
    current_version: int,
    feasibility_report_current: str,
    thinking_summary: str,
    human_critique: str,
    revision_instructions: Optional[str] = None,
    max_revisions: int = 5
) -> Dict[str, Any]:
    """
    Revise an existing feasibility report based on human critique.
    
    Entry point for HITL revision workflow.
    
    Args:
        session_id: Session ID
        current_version: Version being critiqued (1, 2, 3...)
        feasibility_report_current: Current report markdown content
        thinking_summary: Original thinking summary markdown
        human_critique: User feedback (free-form text)
        revision_instructions: Optional structured guidance
        max_revisions: Maximum allowed versions (default: 5)
        
    Returns:
        dict: {
            "session_id": str,
            "new_version": int,
            "revised_report": str,
            "revision_summary": str,
            "file_path": str,
            "token_usage": int,
            "execution_time": float,
            "status": "completed" | "failed"
        }
        
    Raises:
        ValueError: If version limits exceeded or validation fails
    """
    start_time = time.time()
    
    console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
    console.print(f"[bold cyan]HITL FEASIBILITY REPORT REVISION[/bold cyan]")
    console.print(f"[bold cyan]{'='*80}[/bold cyan]\n")
    
    try:
        # Step 1: Validate inputs
        console.print("[bold yellow]STEP 1: Validating inputs[/bold yellow]")
        
        if not session_id or not session_id.strip():
            raise ValueError("session_id cannot be empty")
        
        if current_version < 1:
            raise ValueError(f"current_version must be ≥ 1, got {current_version}")
        
        if not feasibility_report_current or not feasibility_report_current.strip():
            raise ValueError("feasibility_report_current cannot be empty")
        
        if not thinking_summary or not thinking_summary.strip():
            raise ValueError("thinking_summary cannot be empty")
        
        if not human_critique or not human_critique.strip():
            raise ValueError("human_critique cannot be empty")
        
        console.print(f"[bold green]✓ Inputs validated[/bold green]")
        
        # Step 2: Calculate next version
        console.print(f"[bold yellow]STEP 2: Calculating next version[/bold yellow]")
        
        new_version = _get_next_version(current_version, max_revisions)
        console.print(f"[bold green]✓ Version: v{current_version} → v{new_version}[/bold green]")
        
        # Step 3: Build revision prompt
        console.print(f"[bold yellow]STEP 3: Building revision prompt[/bold yellow]")
        
        revision_prompt = _build_revision_prompt(
            current_report=feasibility_report_current,
            thinking_summary=thinking_summary,
            human_critique=human_critique,
            revision_instructions=revision_instructions
        )
        
        # Step 4: Invoke LLM with retry logic
        console.print(f"[bold yellow]STEP 4: Invoking revision LLM[/bold yellow]")
        
        llm_response = _invoke_revision_with_retry(revision_prompt, max_retries=3)
        
        # Step 5: Extract revised report and summary
        console.print(f"[bold yellow]STEP 5: Extracting revised report and summary[/bold yellow]")
        
        revised_report = _extract_revision_report(llm_response)
        revision_summary = _extract_revision_summary(llm_response)
        
        # Step 6: Validate revised report
        console.print(f"[bold yellow]STEP 6: Validating revised report[/bold yellow]")
        
        if not _validate_revised_report(revised_report):
            raise ValueError("Revised report failed validation (format/length check)")
        
        if not _preserve_verdict(feasibility_report_current, revised_report):
            raise ValueError("Revised report does not preserve feasibility verdict")
        
        console.print(f"[bold green]✓ Revised report validation passed[/bold green]")
        
        # Step 7: Save revised report to disk
        console.print(f"[bold yellow]STEP 7: Saving revised report to disk[/bold yellow]")
        
        report_path = _get_report_path(session_id, new_version)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(revised_report)
        
        console.print(f"[bold green]✓ Saved to: {report_path}[/bold green]")
        
        # Step 8: Save revision metadata
        console.print(f"[bold yellow]STEP 8: Saving revision metadata[/bold yellow]")
        
        revision_dir = _get_revision_dir(session_id)
        
        # Save critique
        critique_path = revision_dir / f"revision_{current_version}_critique.txt"
        with open(critique_path, 'w', encoding='utf-8') as f:
            f.write(human_critique)
        
        # Save summary
        summary_path = revision_dir / f"revision_{current_version}_summary.md"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(revision_summary)
        
        # Save instructions if provided
        if revision_instructions:
            instructions_path = revision_dir / f"revision_{current_version}_instructions.txt"
            with open(instructions_path, 'w', encoding='utf-8') as f:
                f.write(revision_instructions)
        
        console.print(f"[bold green]✓ Revision artifacts saved[/bold green]")
        
        # Step 9: Update or create revision log
        console.print(f"[bold yellow]STEP 9: Updating revision log[/bold yellow]")
        
        revision_log_path = Path(f"output/session_{session_id[:8]}/revisions/revision_log.json")
        revision_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing log or create new
        if revision_log_path.exists():
            with open(revision_log_path, 'r', encoding='utf-8') as f:
                revision_log = json.load(f)
        else:
            revision_log = {"session_id": session_id, "revisions": []}
        
        # Add new revision entry
        execution_time = time.time() - start_time
        revision_entry = {
            "version": new_version,
            "created_at": datetime.utcnow().isoformat(),
            "type": "hitl_revision",
            "previous_version": current_version,
            "critique_file": str(critique_path),
            "summary_file": str(summary_path),
            "file_path": str(report_path),
            "execution_time": execution_time
        }
        revision_log["revisions"].append(revision_entry)
        
        # Save updated log
        with open(revision_log_path, 'w', encoding='utf-8') as f:
            json.dump(revision_log, f, indent=2, ensure_ascii=False)
        
        console.print(f"[bold green]✓ Revision log updated[/bold green]")
        
        # Step 10: Return result
        console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
        console.print(f"[bold green]✓ REVISION COMPLETED SUCCESSFULLY[/bold green]")
        console.print(f"[bold cyan]{'='*80}[/bold cyan]\n")
        
        return {
            "session_id": session_id,
            "current_version": current_version,
            "new_version": new_version,
            "revised_report": revised_report,
            "revision_summary": revision_summary,
            "file_path": str(report_path),
            "execution_time": execution_time,
            "status": "completed"
        }
        
    except Exception as e:
        execution_time = time.time() - start_time
        console.print(f"\n[bold red]{'='*80}[/bold red]")
        console.print(f"[bold red]✗ REVISION FAILED[/bold red]")
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        console.print(f"[bold red]{'='*80}[/bold red]\n")
        
        return {
            "session_id": session_id,
            "current_version": current_version,
            "new_version": 0,
            "revised_report": "",
            "revision_summary": "",
            "file_path": "",
            "execution_time": execution_time,
            "status": "failed",
            "error_message": str(e)
        }
