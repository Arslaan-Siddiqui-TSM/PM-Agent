import os
import json
import time
from pathlib import Path
from src.config.llm_config import model
from rich.console import Console


console = Console()


# ============================================================================
# LLM Retry Configuration
# ============================================================================
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 5  # seconds
MAX_RETRY_DELAY = 60  # seconds


def _invoke_llm_with_retry(prompt: str, stage_name: str = "LLM") -> str:
    """
    Invoke LLM with exponential backoff retry logic.
    
    Args:
        prompt: The prompt to send to the LLM
        stage_name: Name of the stage for logging
    
    Returns:
        LLM response content as string
    
    Raises:
        Exception: If all retries fail
    """
    retry_delay = INITIAL_RETRY_DELAY
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            console.print(f"[bold yellow]DEBUG:[/bold yellow] {stage_name} attempt {attempt}/{MAX_RETRIES}")
            
            # Invoke LLM
            result = model.invoke(prompt)
            content = str(getattr(result, "content", result))
            
            console.print(f"[bold green]✓ {stage_name} SUCCESS:[/bold green] Received {len(content)} chars")
            return content
            
        except Exception as e:
            error_msg = str(e)
            console.print(f"[bold red]✗ {stage_name} ATTEMPT {attempt} FAILED:[/bold red] {error_msg}")
            
            # Check if it's a timeout or gateway error
            is_timeout = "timeout" in error_msg.lower() or "504" in error_msg or "502" in error_msg
            
            if attempt < MAX_RETRIES:
                # Calculate delay with exponential backoff
                delay = min(retry_delay * (2 ** (attempt - 1)), MAX_RETRY_DELAY)
                console.print(f"[bold yellow]⏳ Retrying in {delay} seconds...[/bold yellow]")
                time.sleep(delay)
            else:
                # All retries exhausted
                console.print(f"[bold red]✗ {stage_name} FAILED:[/bold red] All {MAX_RETRIES} attempts exhausted")
                raise Exception(f"{stage_name} failed after {MAX_RETRIES} attempts: {error_msg}")
    
    raise Exception(f"{stage_name} failed: Unknown error")


# ============================================================================
# Helper Functions for Two-Stage Feasibility Generation
# ============================================================================

def _extract_thinking_summary(content_str: str) -> str:
    """
    Extract thinking summary from Stage 1 LLM response.
    
    Handles:
    - Delimited format with ---THINKING_SUMMARY_START--- and ---THINKING_SUMMARY_END---
    - Code fences around delimited content
    - Fallback to entire content if delimiters not found
    """
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Extracting thinking summary from Stage 1 response")
    
    # Optional: strip surrounding code fences if present
    cs_strip = content_str.strip()
    if cs_strip.startswith("```") and cs_strip.endswith("```"):
        console.print("[bold yellow]DEBUG:[/bold yellow] Stripping surrounding code fences from response")
        cs_body = cs_strip[3:]
        nl = cs_body.find("\n")
        if nl != -1:
            cs_body = cs_body[nl+1:]
        cs_body = cs_body.rstrip("`")
        content_str = cs_body.strip()

    # Try robust regex-based extraction
    import re as _re
    think_pat = _re.compile(
        r"---THINKING_SUMMARY_START---\s*(.*?)\s*(?:---THINKING_SUMMARY_END---|\Z)",
        _re.DOTALL,
    )

    m_think = think_pat.search(content_str)
    if m_think:
        thinking_summary = m_think.group(1).strip()
        console.print(f"[bold green]DEBUG:[/bold green] Extracted thinking summary via regex (len={len(thinking_summary)})")
        return thinking_summary
    
    # Fallback: use entire content
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Delimiters not found, using entire response as thinking summary")
    return content_str.strip()


def _build_stage2_prompt(thinking_summary: str, user_payload: dict, session_id: str) -> str:
    """
    Build Stage 2 prompt for feasibility report generation.
    
    Combines:
    - Stage 2 template (feasibility_report.txt)
    - Thinking summary from Stage 1
    - Original development_context and documents
    """
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Building Stage 2 prompt")
    
    # Load Stage 2 template
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "feasibility_report.txt"
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Loading Stage 2 template from: {prompt_path}")
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            stage2_template = f.read()
        console.print(f"[bold green]DEBUG:[/bold green] Stage 2 template loaded, length: {len(stage2_template)} characters")
    except Exception as e:
        console.print(f"[bold red]ERROR:[/bold red] Failed to load Stage 2 template: {e}")
        raise
    
    # Build user message for Stage 2
    stage2_payload = {
        "thinking_summary": thinking_summary,
        "development_context": user_payload.get("development_context", {}),
        "unified_context": user_payload.get("unified_context", {}),
        "session_id": session_id
    }
    
    user_message_stage2 = json.dumps(stage2_payload, ensure_ascii=False, indent=2)
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Stage 2 user payload length: {len(user_message_stage2)} characters")
    
    # Combine template and payload
    full_prompt_stage2 = f"{stage2_template}\n\n---\n\nUSER PAYLOAD:\n\n{user_message_stage2}"
    
    console.print(f"[bold green]DEBUG:[/bold green] Stage 2 prompt built, total length: {len(full_prompt_stage2)} characters")
    
    return full_prompt_stage2


def _generate_revision(revision_context: dict, session_id: str) -> dict:
    """
    Generate revised feasibility report based on critique.
    
    Args:
        revision_context: Dict containing previous_report, critique, human_feedback, iteration
        session_id: Session ID for tracking
        
    Returns:
        dict: Dictionary with 'thinking_summary' and 'feasibility_report'
    """
    console.print(f"\n[bold magenta]{'='*60}[/bold magenta]")
    console.print(f"[bold magenta]REVISION MODE - Iteration {revision_context.get('iteration', '?')}[/bold magenta]")
    console.print(f"[bold magenta]{'='*60}[/bold magenta]\n")
    
    project_root = Path(__file__).parent.parent.parent
    revise_prompt_path = project_root / "prompts" / "feasibility_revise.txt"
    
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Loading revision prompt from: {revise_prompt_path}")
    
    try:
        with open(revise_prompt_path, "r", encoding="utf-8") as f:
            revise_template = f.read()
    except FileNotFoundError:
        console.print(f"[bold red]ERROR:[/bold red] Revision prompt not found at {revise_prompt_path}")
        return {
            "thinking_summary": "ERROR: Revision prompt template not found",
            "feasibility_report": "ERROR: Revision prompt template not found"
        }
    
    # Fill in the revision template
    revision_prompt = revise_template.format(
        iteration=revision_context.get('iteration', 0),
        original_report=revision_context.get('previous_report', ''),
        critique=revision_context.get('critique', '')
    )
    
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Revision prompt length: {len(revision_prompt)} characters")
    
    try:
        # Generate revised report (with retry)
        revised_report = _invoke_llm_with_retry(
            revision_prompt, 
            f"Revision Generation (Iteration {revision_context.get('iteration', 0)})"
        )
        
        console.print(f"[bold green]✓ REVISION COMPLETE:[/bold green] Revised report: {len(revised_report)} chars")
        
        # For revisions, thinking_summary is a brief note about the revision
        thinking_summary = f"REVISION {revision_context.get('iteration', 0)}: Addressed critique points - {len(revised_report)} chars generated"
        
        return {
            "thinking_summary": thinking_summary,
            "feasibility_report": revised_report
        }
        
    except Exception as e:
        console.print(f"[bold red]ERROR:[/bold red] Revision generation failed: {e}")
        return {
            "thinking_summary": f"Error generating revision: {e}",
            "feasibility_report": f"Error generating revision: {e}"
        }


def generate_feasibility_questions(
    context_file_path: str, 
    development_context: dict | None = None, 
    session_id: str = "unknown",
    revision_context: dict | None = None
) -> dict:
    """Generate feasibility questions for the Tech Lead review.

    Args:
        context_file_path (str): Path to the unified context file containing feasibility report and document content.
        development_context (dict, optional): Development process information from user.
        session_id (str, optional): Session ID for the assessment.
        revision_context (dict, optional): Context for revision iterations including previous report, critique, and feedback.

    Returns:
        dict: Dictionary with keys 'thinking_summary' and 'feasibility_report' containing markdown text.
    """    
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Starting feasibility question generation")
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Context file path: {context_file_path}")
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Development context provided: {development_context is not None}")
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Revision context provided: {revision_context is not None}")
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Session ID: {session_id}")
    
    # Check if this is a revision iteration
    is_revision = revision_context is not None
    
    if is_revision:
        console.print(f"[bold magenta]🔄 REVISION MODE:[/bold magenta] Iteration {revision_context.get('iteration', '?')}")
        console.print(f"[bold magenta]📝 Critique available:[/bold magenta] {len(revision_context.get('critique', ''))} chars")
        return _generate_revision(revision_context, session_id)
    
    # Original generation path (no revision)
    console.print(f"[bold green]✨ INITIAL GENERATION MODE[/bold green]")
    
    # Read the unified context file
    try:
        with open(context_file_path, 'r', encoding='utf-8') as f:
            unified_context = f.read()
        console.print(f"[bold green]DEBUG:[/bold green] Unified context file loaded, length: {len(unified_context)} characters")
    except Exception as e:
        console.print(f"[bold red]ERROR:[/bold red] Failed to read unified context file: {e}")
        return {
            "thinking_summary": f"Error reading context file: {e}",
            "feasibility_report": f"Error reading context file: {e}"
        }
    
    # Get project root directory (two levels up from this file)
    project_root = Path(__file__).parent.parent.parent
    
    # Load Stage 1 prompt (Thinking Summary)
    prompt_path = project_root / "prompts" / "thinking_summary.txt"
    
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Loading Stage 1 prompt from: {prompt_path}")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()
    
    console.print(f"[bold yellow]DEBUG:[/bold yellow] System prompt loaded, length: {len(system_prompt)} characters")
    
    # Truncate unified context if too long (keep reasonable limit for token budget)
    max_context_length = 150000  # Allows larger context for modern LLMs
    if len(unified_context) > max_context_length:
        console.print(f"[bold yellow]DEBUG:[/bold yellow] Truncating unified context to {max_context_length} characters")
        unified_context = unified_context[:max_context_length]
    
    # If development_context is None, provide an empty dict with "unknown" placeholder
    if development_context is None:
        development_context = {
            "note": "No development context provided by user",
            "teamSize": "unknown",
            "timeline": "unknown",
            "budget": "unknown",
            "methodology": "unknown",
            "techStack": "unknown",
            "constraints": "unknown"
        }
    
    # Build payload with unified context
    user_payload = {
        "development_context": development_context,
        "unified_context": {
            "session_id": session_id,
            "content": unified_context,
            "source": context_file_path
        }
    }
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Built user payload with unified context")
    
    # Build the full prompt with system instructions + JSON payload
    user_message = json.dumps(user_payload, ensure_ascii=False, indent=2)
    
    console.print(f"[bold yellow]DEBUG:[/bold yellow] User payload length: {len(user_message)} characters")
    
    # Combine system prompt and user message
    full_prompt = f"{system_prompt}\n\n---\n\nUSER PAYLOAD:\n\n{user_message}"
    
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Full prompt length: {len(full_prompt)} characters")
    
    # Show a preview of the prompt
    console.print("\n[bold magenta]DEBUG - PROMPT PREVIEW:[/bold magenta]")
    console.print("[dim]" + "="*80 + "[/dim]")
    console.print(f"[cyan]Total prompt characters: {len(full_prompt)}[/cyan]")
    console.print(f"[cyan]User payload preview:[/cyan]")
    console.print(user_message[:500] + "..." if len(user_message) > 500 else user_message)
    console.print("[dim]" + "="*80 + "[/dim]\n")
    
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Starting two-stage feasibility generation...")
    
    try:
        # ============================================================
        # STAGE 1: Generate thinking summary (with retry)
        # ============================================================
        console.print(f"\n[bold cyan]═══ STAGE 1: GENERATING THINKING SUMMARY ═══[/bold cyan]")
        
        content_stage1 = _invoke_llm_with_retry(full_prompt, "Stage 1 (Thinking Summary)")
        console.print(f"[bold yellow]DEBUG:[/bold yellow] Stage 1 content length: {len(content_stage1)} characters")
        
        # Extract thinking summary from Stage 1
        thinking_summary = _extract_thinking_summary(content_stage1)
        console.print(f"[bold green]✓ STAGE 1 COMPLETE:[/bold green] Thinking summary: {len(thinking_summary)} chars")
        
        # ============================================================
        # STAGE 2: Generate feasibility report from thinking summary (with retry)
        # ============================================================
        console.print(f"\n[bold cyan]═══ STAGE 2: GENERATING FEASIBILITY REPORT ═══[/bold cyan]")
        console.print(f"[bold yellow]DEBUG:[/bold yellow] Building Stage 2 prompt with thinking summary")
        
        stage2_prompt = _build_stage2_prompt(thinking_summary, user_payload, session_id)
        console.print(f"[bold yellow]DEBUG:[/bold yellow] Stage 2 prompt length: {len(stage2_prompt)} characters")
        
        content_stage2 = _invoke_llm_with_retry(stage2_prompt, "Stage 2 (Feasibility Report)")
        console.print(f"[bold yellow]DEBUG:[/bold yellow] Stage 2 content length: {len(content_stage2)} characters")
        
        # Extract feasibility report from Stage 2 (entire response is the report)
        feasibility_report = content_stage2.strip()
        console.print(f"[bold green]✓ STAGE 2 COMPLETE:[/bold green] Feasibility report: {len(feasibility_report)} chars")
        
        console.print(f"\n[bold green]═══ TWO-STAGE GENERATION COMPLETED SUCCESSFULLY ═══[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]DEBUG ERROR:[/bold red] LLM invocation failed: {e}")
        return {
            "thinking_summary": f"Error calling LLM: {e}",
            "feasibility_report": f"Error calling LLM: {e}"
        }

    return {
        "thinking_summary": thinking_summary,
        "feasibility_report": feasibility_report
    }


def save_development_context_to_json(
    development_context: dict,
    session_id: str,
    output_dir: str = "output/intermediate"
) -> str:
    """Save development context data to a JSON file (only once per session).
    
    Args:
        development_context (dict): Dictionary containing form data from frontend
            (methodology, teamSize, timeline, budget, techStack, constraints).
        session_id (str): Session ID associated with this context.
        output_dir (str, optional): Directory to save the JSON file. 
            Defaults to "output/intermediate".
    
    Returns:
        str: The path to the saved JSON file.
    """
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Checking for existing development context")
    console.print(f"[bold yellow]DEBUG:[/bold yellow] Session ID: {session_id}")
    
    import json
    from datetime import datetime
    from glob import glob
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if development context already exists for this session
    existing_files = glob(os.path.join(output_dir, f"development_context_{session_id[:8]}*.json"))
    
    if existing_files:
        # Reuse existing file
        json_file_path = existing_files[0]
        console.print(f"[bold green]✓ Reusing existing development context:[/bold green] {json_file_path}")
        return json_file_path
    
    # Create filename with session ID (no timestamp needed, one per session)
    json_filename = f"development_context_{session_id[:8]}.json"
    json_file_path = os.path.join(output_dir, json_filename)
    
    # Prepare the JSON data structure
    json_data = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "development_context": development_context,
    }
    
    # Save to JSON file
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    console.print(f"[bold green]✓ Development context saved to:[/bold green] {json_file_path}")
    return json_file_path


if __name__ == "__main__":
    console.print(f"[bold yellow]This module is not meant to be run directly.[/bold yellow]")
    console.print(f"[bold cyan]Use the API endpoints for feasibility generation.[/bold cyan]")