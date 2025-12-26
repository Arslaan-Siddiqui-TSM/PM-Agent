from __future__ import annotations

import os
from typing import Dict

from src.config.llm_config import model
from src.states.reflection_state import ReflectionState
from src.utils.helper import (
    get_global_logger,
    load_feasibility_answers,
    load_prompt_template,
)


def _extract_quality_metrics(
    critique_text: str, current_draft: str
) -> tuple[float, list[str]]:
    """Extract quality score and improvement areas from critique or evaluate the draft."""

    # Try to parse quality assessment from critique if it contains structured feedback
    quality_score = 5.0  # Default mid-range score
    improvement_areas = []

    # Simple heuristic: Look for quality indicators in critique
    critique_lower = critique_text.lower()

    # Positive indicators
    positive_count = sum(
        [
            critique_lower.count("good"),
            critique_lower.count("strong"),
            critique_lower.count("comprehensive"),
            critique_lower.count("well"),
            critique_lower.count("excellent"),
        ]
    )

    # Negative indicators
    negative_count = sum(
        [
            critique_lower.count("missing"),
            critique_lower.count("weak"),
            critique_lower.count("insufficient"),
            critique_lower.count("unclear"),
            critique_lower.count("incomplete"),
            critique_lower.count("lacks"),
        ]
    )

    # Calculate score based on sentiment
    if negative_count > positive_count:
        quality_score = max(3.0, 7.0 - (negative_count - positive_count) * 0.5)
    else:
        quality_score = min(9.0, 6.0 + (positive_count - negative_count) * 0.3)

    # Extract improvement areas from critique
    # Look for common critique patterns
    lines = critique_text.split("\n")
    for line in lines:
        line_lower = line.lower()
        if any(
            keyword in line_lower
            for keyword in ["missing", "needs", "should", "lacks", "improve", "unclear"]
        ):
            # Extract the area being critiqued
            if "timeline" in line_lower or "schedule" in line_lower:
                improvement_areas.append("Timeline/Schedule clarity")
            elif "budget" in line_lower or "cost" in line_lower:
                improvement_areas.append("Budget/Cost estimation")
            elif "resource" in line_lower or "team" in line_lower:
                improvement_areas.append("Resource allocation")
            elif "risk" in line_lower:
                improvement_areas.append("Risk assessment")
            elif "scope" in line_lower or "requirement" in line_lower:
                improvement_areas.append("Scope definition")
            elif "dependency" in line_lower or "dependencies" in line_lower:
                improvement_areas.append("Dependency management")

    # Remove duplicates while preserving order
    improvement_areas = list(dict.fromkeys(improvement_areas))

    return quality_score, improvement_areas[:3]  # Max 3 focus areas


def generate_reflection(state: ReflectionState) -> Dict[str, object]:
    """
    Critique the current draft and capture feedback for revisions.
    
    This node now incorporates human feedback from the draft review stage:
    - Uses the human-edited draft if available
    - Includes human feedback in the critique prompt
    - Addresses specific concerns raised by the human reviewer
    """

    if not state.iterations or not state.current_draft:
        raise ValueError("Cannot reflect without an existing draft.")

    prompt_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "prompts", "project_plan_reflect.txt"
        )
    )
    prompt_template = load_prompt_template(prompt_path)

    feasibility_context = (
        load_feasibility_answers(state.feasibility_file_path)
        if state.feasibility_file_path
        else None
    ) or "No feasibility notes supplied. Flag missing governance details."

    # Use human-edited draft if available (HITL integration)
    draft_to_critique = state.draft if state.draft else state.current_draft
    
    # Build human feedback section for the prompt
    human_feedback_section = ""
    if state.draft_human_feedback:
        human_feedback_section = f"""
## HUMAN REVIEWER FEEDBACK (CRITICAL - MUST ADDRESS)

The human reviewer has provided the following feedback on the draft:

{state.draft_human_feedback}

**IMPORTANT**: Your critique MUST specifically address each point raised in the human feedback above.
Prioritize the human reviewer's concerns over other critique points.
"""

    # Build the prompt with human feedback incorporated
    base_prompt = prompt_template.format(
        pm_inputs=state.task or "Create a comprehensive software project plan.",
        feasibility_report=feasibility_context,
        initial_documents=state.document_context or "Document context unavailable.",
        draft_project_plan=draft_to_critique,
    )
    
    # Insert human feedback section if available
    if human_feedback_section:
        # Find a good insertion point (before the draft or at the end of context)
        formatted_prompt = f"{base_prompt}\n\n{human_feedback_section}"
    else:
        formatted_prompt = base_prompt

    result = model.invoke(formatted_prompt)
    critique_text = str(getattr(result, "content", result)).strip()

    # Extract quality metrics from critique
    quality_score, improvement_areas = _extract_quality_metrics(
        critique_text, draft_to_critique
    )

    # Build iteration summary
    iteration_number = len(state.iterations)
    human_feedback_note = " (with human feedback)" if state.draft_human_feedback else ""
    iteration_summary = f"Iteration {iteration_number}{human_feedback_note}: Quality {quality_score:.1f}/10. Focus: {', '.join(improvement_areas) if improvement_areas else 'General improvements'}"

    # Update the latest iteration with critique
    iterations = list(state.iterations)
    latest_iteration = iterations[-1].model_copy()
    latest_iteration.critique = critique_text
    iterations[-1] = latest_iteration

    # Accumulate quality scores and improvement areas
    quality_scores = list(state.quality_scores)
    quality_scores.append(quality_score)

    all_improvement_areas = list(state.improvement_areas)
    all_improvement_areas.extend(improvement_areas)

    iteration_summaries = list(state.iteration_summaries)
    iteration_summaries.append(iteration_summary)

    logger = get_global_logger()
    if logger:
        logger.log_llm_interaction(
            stage="Reflection Agent - Critique",
            prompt=formatted_prompt,
            response=critique_text,
            additional_context={
                "Iteration": len(iterations),
                "Quality Score": f"{quality_score:.1f}/10",
                "Improvement Areas": ", ".join(improvement_areas)
                if improvement_areas
                else "None",
                "Human Feedback Included": "Yes" if state.draft_human_feedback else "No",
            },
        )

    return {
        "iterations": iterations,
        "reflection": critique_text,  # Store in new HITL field
        "quality_scores": quality_scores,
        "improvement_areas": all_improvement_areas,
        "iteration_summaries": iteration_summaries,
    }
