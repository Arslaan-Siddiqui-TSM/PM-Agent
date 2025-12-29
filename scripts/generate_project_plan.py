from src.states.reflection_state import ReflectionState

from src.app.graph import get_graph
from src.utils.helper import MarkdownLogger, set_global_logger
from src.core.document_intelligence_pipeline import DocumentIntelligencePipeline

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
import time
import os
import glob


REFLECTION_DEFAULT_TASK = (
    "Synthesize all provided project documents and feasibility notes into an "
    "executive-grade implementation plan."
)


def run_agent(
    use_document_intelligence: bool = True,
    enable_cache: bool = True,
    max_iterations: int = 2,
):
    """
    Run the ReWOO agent with all documents in the files directory.
    
    The agent will automatically load:
    - All PDF documents from the 'files/' directory
    - Optionally process through Document Intelligence Pipeline (recommended)
    - Feasibility question answers from 'outputs/feasibility_assessment.md'
    
    All execution steps will be saved to a markdown file in outputs/ directory.
    
    Args:
        task (str): Task description for the agent
        use_document_intelligence (bool): Use intelligent document processing (recommended)
        enable_cache (bool): Enable caching for faster repeated runs
    """
    start_time = time.time()
    
    # Get list of all PDF files in the files directory
    files_dir = os.path.join(os.path.dirname(__file__), "files")
    pdf_files = glob.glob(os.path.join(files_dir, "*.pdf"))
    
    # Initialize markdown logger
    md_logger = MarkdownLogger(output_dir="outputs")
    md_logger.start(
        "Reflection Agent Execution Started",
        pdf_files,
        "outputs/feasibility_assessment.md",
    )
    
    # Set as global logger so other modules can access it
    set_global_logger(md_logger)
    
    # Process documents with intelligence pipeline (NEW)
    document_context = None
    if use_document_intelligence:
        console = Console()
        console.print("\n[bold yellow]🧠 Using Document Intelligence Pipeline[/bold yellow]")
        console.print("[dim]This will automatically classify, extract, and analyze documents...[/dim]\n")
        
        pipeline = DocumentIntelligencePipeline(enable_cache=enable_cache, verbose=True)
        pipeline_result = pipeline.process_documents(pdf_files, output_dir="outputs/intermediate")
        
        # Generate comprehensive planning context
        document_context = pipeline.get_planning_context(pipeline_result)
        
        feasibility_file = "outputs/feasibility_assessment.md"
        if os.path.exists(feasibility_file):
            with open(feasibility_file, "r", encoding="utf-8") as f:
                feasibility_content = f.read()
            
            # Combine contexts
            document_context = f"""{document_context}

        ## FEASIBILITY ASSESSMENT:

        {feasibility_content}
        """
            console.print("[green]✓ Loaded feasibility assessment[/green]")
        else:
            console.print("[yellow]⚠️  No feasibility assessment found[/yellow]")

        console.print("\n[green]✓ Document Intelligence Pipeline completed[/green]")
        console.print(f"[dim]Analysis report saved to: outputs/intermediate/document_analysis_report.md[/dim]\n")
    else:
        console = Console()
        console.print("\n[yellow]⚠️  Document Intelligence Pipeline disabled - using legacy mode[/yellow]\n")
    
    console = Console()
    console.rule("[bold blue]🔍 Executing Reflection Reasoning Loop[/bold blue]")
    console.print(f"[bold cyan]🟡 Processing {len(pdf_files)} documents from files/ directory:[/bold cyan]")
    for pdf_file in sorted(pdf_files):
        console.print(f"   • {os.path.basename(pdf_file)}")
    console.print(f"[bold cyan]💡 Feasibility Context:[/bold cyan] outputs/feasibility_assessment.md")
    if use_document_intelligence:
        console.print(f"[bold cyan]🧠 Document Intelligence:[/bold cyan] ENABLED")
    console.print("\n")
    
    # Create initial state with document context
    initial_state = ReflectionState(
        task=REFLECTION_DEFAULT_TASK,
        document_context=document_context,
        feasibility_file_path="outputs/feasibility_assessment.md",
        max_iterations=max_iterations,
    )
    
    app = get_graph(initial_state)
    final_state = None
    final_plan_text = None  # Track the final plan when we see it

    for s in app.stream(initial_state):
        # Each s is a dict like {'plan': {...}} or {'tool': {...}} etc.
        node_name = next(iter(s))
        data = s[node_name]

        if node_name == "draft":
            iterations = data.get("iterations") or []
            iteration_index = len(iterations)
            latest_iteration = iterations[-1] if iterations else None

            if latest_iteration is None:
                console.print(Panel("Draft node returned no iteration.", border_style="red"))
            else:
                draft_text = getattr(latest_iteration, "draft", None) or latest_iteration.get("draft")  # type: ignore[attr-defined]
                revision_focus = getattr(latest_iteration, "reasoning", None) or (
                    latest_iteration.get("reasoning") if isinstance(latest_iteration, dict) else None  # type: ignore[attr-defined]
                )
                context_source = data.get("context_source")

                console.rule(f"[bold magenta]🧾 Iteration {iteration_index}: Draft[/bold magenta]")
                console.print(
                    Panel(
                        draft_text,
                        title=f"Draft Plan (Iteration {iteration_index})",
                        border_style="magenta",
                    )
                )

                md_logger.log_iteration_draft(
                    iteration_index,
                    draft_text,
                    revision_focus=revision_focus,
                    context_source=context_source,
                )

        elif node_name == "reflect":
            iterations = data.get("iterations") or []
            iteration_index = len(iterations)
            critique = data.get("current_critique", "No critique generated.")

            console.rule(f"[bold yellow]🔍 Iteration {iteration_index}: Reflection[/bold yellow]")
            console.print(
                Panel(
                    critique,
                    title="Critique",
                    border_style="yellow",
                )
            )

            md_logger.log_iteration_critique(iteration_index, critique)

        elif node_name == "revise":
            iterations = data.get("iterations") or []
            iteration_index = len(iterations)
            decision = data.get("decision", "revise")
            rationale = data.get("decision_rationale")
            required_actions = data.get("required_actions")
            final_plan = data.get("final_plan")

            console.rule(f"[bold cyan]♻️ Iteration {iteration_index}: Revision[/bold cyan]")
            decision_text = decision.replace("-", " ").title()
            panel_title = f"Decision: {decision_text}"
            body_lines = []
            if rationale:
                body_lines.append(f"Rationale: {rationale}")
            if required_actions:
                body_lines.append("Required Actions:")
                body_lines.extend([f"  - {line}" for line in required_actions.splitlines() if line.strip()])

            console.print(
                Panel(
                    "\n".join(body_lines) if body_lines else "No additional notes.",
                    title=panel_title,
                    border_style="cyan",
                )
            )

            md_logger.log_revision_decision(
                iteration_index,
                decision,
                rationale,
                required_actions,
            )

            if final_plan:
                final_plan_text = final_plan  # Capture the final plan for saving later
                console.print(
                    Panel(
                        final_plan,
                        title="Final Project Plan",
                        border_style="green",
                    )
                )
                md_logger.log_final_plan(final_plan)

        elif node_name == "finalize":
            # finalize node may return empty dict if plan already set
            pass
        else:
            console.print(Panel(f"Unknown state: {node_name}", border_style="red"))
        
        console.print("\n")
        final_state = s

    console.rule("[bold blue]✅ Finished Execution[/bold blue]")
    
    # Use the final plan we captured during the revise node
    if final_plan_text:
        console.print(
            Panel(
                Text(final_plan_text, justify="center", style="bold white on blue1"),
                title="Final Result",
                border_style="blue",
                expand=False,
            )
        )
    
    elapsed_time = time.time() - start_time
    console.print(f"\n[bold green]⏱️ Total execution time: {elapsed_time:.2f} seconds[/bold green]")
    
    # Save final plan to file
    if final_plan_text:
        output_dir = os.path.join(os.path.dirname(__file__), "outputs")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        plan_filename = f"project_plan_{timestamp}.md"
        plan_filepath = os.path.join(output_dir, plan_filename)
        
        try:
            with open(plan_filepath, "w", encoding="utf-8") as f:
                f.write(final_plan_text)
            console.print(f"[bold green]💾 Project plan saved to: {plan_filepath}[/bold green]")
        except Exception as e:
            console.print(f"[bold red]⚠️ Failed to save project plan: {e}[/bold red]")
    else:
        console.print("[bold yellow]⚠️ No final plan generated[/bold yellow]")
    
    # Finalize and save markdown log
    log_filepath = md_logger.finalize(elapsed_time)
    console.print(f"[bold yellow]📝 Execution log saved to: {log_filepath}[/bold yellow]")


if __name__ == "__main__":
    # The agent will automatically process all PDF files in the files/ directory
    # 
    # NEW: Document Intelligence Pipeline (Recommended)
    # - Automatically classifies documents by type (not based on filename)
    # - Extracts structured information from each document
    # - Analyzes for gaps, conflicts, and planning readiness
    # - Generates comprehensive planning context
    # - Uses caching for faster subsequent runs
    #
    # Set use_document_intelligence=False to use legacy raw document loading
    
    run_agent(
        use_document_intelligence=True,  # Use intelligent document processing
        enable_cache=True  # Enable caching for faster runs
    )