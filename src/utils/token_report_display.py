"""
Token usage report display utilities.

Provides formatted console output for token usage statistics across
feasibility generation and HITL revision iterations.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

console = Console()


def display_feasibility_token_summary(stats: Dict[str, Any], execution_time: float):
    """Display summary of tokens used in feasibility generation."""
    
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Metric", style="cyan", width=25)
    table.add_column("Value", style="green", justify="right", width=25)
    
    table.add_row("Total LLM Calls", f"{stats.get('total_calls', 0)}")
    table.add_row("Total Input Tokens", f"[bright_blue]{stats.get('total_input_tokens', 0):,}[/bright_blue]")
    table.add_row("Total Output Tokens", f"[bright_green]{stats.get('total_output_tokens', 0):,}[/bright_green]")
    table.add_row("Total Tokens", f"[bold bright_yellow]{stats.get('total_tokens', 0):,}[/bold bright_yellow]")
    table.add_row("Execution Time", f"{execution_time:.2f}s")
    
    if stats.get('total_tokens', 0) > 0:
        speed = stats.get('total_tokens', 0) / execution_time
        table.add_row("Speed", f"[dim]{speed:.2f} tok/s[/dim]")
    
    # Cost calculation (NVIDIA pricing)
    input_cost = (stats.get('total_input_tokens', 0) / 1_000_000) * 0.02
    output_cost = (stats.get('total_output_tokens', 0) / 1_000_000) * 0.06
    total_cost = input_cost + output_cost
    
    table.add_row("─" * 25, "─" * 25)
    table.add_row("Estimated Cost (NVIDIA)", f"${total_cost:.4f}")
    
    panel = Panel(
        table,
        title="📊 Feasibility Generation - Token Summary",
        border_style="blue",
        padding=(0, 1)
    )
    
    console.print(panel)


def display_revision_token_summary(stats: Dict[str, Any], execution_time: float, from_version: int, to_version: int):
    """Display summary of tokens used in HITL revision."""
    
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Metric", style="cyan", width=25)
    table.add_column("Value", style="green", justify="right", width=25)
    
    table.add_row("Revision", f"v{from_version} → v{to_version}")
    table.add_row("Total LLM Calls", f"{stats.get('total_calls', 0)}")
    table.add_row("Total Input Tokens", f"[bright_blue]{stats.get('total_input_tokens', 0):,}[/bright_blue]")
    table.add_row("Total Output Tokens", f"[bright_green]{stats.get('total_output_tokens', 0):,}[/bright_green]")
    table.add_row("Total Tokens", f"[bold bright_yellow]{stats.get('total_tokens', 0):,}[/bold bright_yellow]")
    table.add_row("Execution Time", f"{execution_time:.2f}s")
    
    if stats.get('total_tokens', 0) > 0:
        speed = stats.get('total_tokens', 0) / execution_time
        table.add_row("Speed", f"[dim]{speed:.2f} tok/s[/dim]")
    
    # Cost calculation
    input_cost = (stats.get('total_input_tokens', 0) / 1_000_000) * 0.02
    output_cost = (stats.get('total_output_tokens', 0) / 1_000_000) * 0.06
    total_cost = input_cost + output_cost
    
    table.add_row("─" * 25, "─" * 25)
    table.add_row("Estimated Cost (NVIDIA)", f"${total_cost:.4f}")
    
    panel = Panel(
        table,
        title="📊 HITL Revision - Token Summary",
        border_style="blue",
        padding=(0, 1)
    )
    
    console.print(panel)


def display_full_iteration_summary(
    session_id: str,
    feasibility_stats: Dict[str, Any],
    feasibility_time: float,
    revisions: Optional[List[Dict[str, Any]]] = None
):
    """Display comprehensive summary of all tokens used in full iteration."""
    
    # Calculate totals
    total_input = feasibility_stats.get('total_input_tokens', 0)
    total_output = feasibility_stats.get('total_output_tokens', 0)
    total_tokens = feasibility_stats.get('total_tokens', 0)
    total_cost = (total_input / 1_000_000) * 0.02 + (total_output / 1_000_000) * 0.06
    
    # Build main summary table
    summary_table = Table(show_header=True, header_style="bold magenta", box=None)
    summary_table.add_column("Phase", style="cyan")
    summary_table.add_column("Input", justify="right")
    summary_table.add_column("Output", justify="right")
    summary_table.add_column("Total", justify="right")
    summary_table.add_column("Time (s)", justify="right")
    summary_table.add_column("Cost ($)", justify="right")
    
    # Feasibility row
    feasibility_cost = (feasibility_stats.get('total_input_tokens', 0) / 1_000_000) * 0.02 + \
                      (feasibility_stats.get('total_output_tokens', 0) / 1_000_000) * 0.06
    summary_table.add_row(
        "Feasibility",
        f"{feasibility_stats.get('total_input_tokens', 0):,}",
        f"{feasibility_stats.get('total_output_tokens', 0):,}",
        f"{feasibility_stats.get('total_tokens', 0):,}",
        f"{feasibility_time:.2f}",
        f"{feasibility_cost:.4f}"
    )
    
    # Revision rows if present
    revision_total_cost = 0
    if revisions:
        for revision in revisions:
            rev_in = revision.get('input_tokens', 0)
            rev_out = revision.get('output_tokens', 0)
            rev_total = rev_in + rev_out
            rev_time = revision.get('duration', 0)
            rev_cost = (rev_in / 1_000_000) * 0.02 + (rev_out / 1_000_000) * 0.06
            revision_total_cost += rev_cost
            
            summary_table.add_row(
                f"Revision ({revision.get('version', '?')})",
                f"{rev_in:,}",
                f"{rev_out:,}",
                f"{rev_total:,}",
                f"{rev_time:.2f}",
                f"{rev_cost:.4f}"
            )
            
            total_input += rev_in
            total_output += rev_out
            total_tokens += rev_total
    
    # Totals row
    summary_table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{total_input:,}[/bold]",
        f"[bold]{total_output:,}[/bold]",
        f"[bold]{total_tokens:,}[/bold]",
        "[dim]-[/dim]",
        f"[bold ${feasibility_cost + revision_total_cost:.4f}[/bold]"
    )
    
    # Create metrics table
    metrics_table = Table(show_header=False, box=None, padding=(0, 1))
    metrics_table.add_column("Metric", style="cyan", width=25)
    metrics_table.add_column("Value", style="green", justify="right", width=25)
    
    total_time = feasibility_time + sum(r.get('duration', 0) for r in revisions or [])
    
    metrics_table.add_row("Session ID", session_id[:12])
    metrics_table.add_row("Phases Completed", f"Feasibility + {len(revisions or [])} revisions")
    metrics_table.add_row("Input:Output Ratio", f"{round(total_input/total_output if total_output > 0 else 0, 2)}:1")
    metrics_table.add_row("Avg Tokens/Second", f"{round(total_tokens/total_time if total_time > 0 else 0, 2)}")
    metrics_table.add_row("Cost per 1K Tokens", f"${round((feasibility_cost + revision_total_cost)/(total_tokens/1000) if total_tokens > 0 else 0, 6)}")
    
    # Display in columns
    columns = Columns(
        [summary_table, metrics_table],
        equal=False,
        expand=True
    )
    
    panel = Panel(
        columns,
        title="📈 Full Iteration - Comprehensive Token Analysis",
        border_style="magenta",
        padding=(0, 1)
    )
    
    console.print(panel)


def load_and_display_token_report(report_path: str):
    """Load a saved JSON token report and display it."""
    import json
    
    try:
        with open(report_path, 'r') as f:
            report = json.load(f)
        
        phase = report.get('phase', 'UNKNOWN')
        summary = report.get('summary', {})
        
        if phase == "FEASIBILITY_GENERATION":
            display_feasibility_token_summary(
                summary,
                summary.get('execution_time_seconds', 0)
            )
        elif phase == "HITL_REVISION":
            revision = report.get('revision', {})
            display_revision_token_summary(
                summary,
                summary.get('execution_time_seconds', 0),
                revision.get('from_version', 0),
                revision.get('to_version', 0)
            )
        
        return report
    
    except Exception as e:
        console.print(f"[red]Error loading token report: {e}[/red]")
        return None
