"""LangGraph nodes: intake -> resolver -> planner.

Kept as three separate nodes on purpose: it's the visible proof, on the graph
itself, of "deterministic core + LLM at the edges" — resolver_node has no
model call wired into it, ever; intake_node and planner_node are the only
places an Anthropic API call happens.

intake_node is single-turn: it extracts whatever it can from
`latest_message` (if provided this turn), then reports whether anything's
still missing via `pending_questions`. The graph conditionally routes back to
the caller (not back to itself — LangGraph nodes aren't loops) when a
question is pending, and only proceeds to resolver -> planner once
StudentState.missing_fields() is empty. The caller (a chat endpoint or the
CLI script in scripts/chat_intake.py) is what actually loops turn to turn.
"""

from __future__ import annotations

from typing import TypedDict

from app.intake.extractor import apply_extracted_fields
from app.intake.questions import next_question
from app.planner import attach_explanations
from app.resolver import resolve_plan
from app.schemas.plan_graph import ResolvedPlan
from app.schemas.state import StudentState


class OrchestrationState(TypedDict, total=False):
    student_state: StudentState
    latest_message: str | None  # this turn's free-text answer, if any
    pending_questions: list[str]
    resolved_plan: ResolvedPlan | None


def intake_node(state: OrchestrationState) -> OrchestrationState:
    student_state = state["student_state"]
    latest_message = state.get("latest_message")
    if latest_message:
        student_state = apply_extracted_fields(student_state, latest_message)

    question = next_question(student_state.missing_fields())
    return {
        **state,
        "student_state": student_state,
        "latest_message": None,  # consumed
        "pending_questions": [question] if question else [],
    }


def resolver_node(state: OrchestrationState) -> OrchestrationState:
    """Phase 2: the deterministic resolver, wired for real. No LLM call here —
    this node's whole point is that it doesn't need one.
    """
    plan = resolve_plan(state["student_state"])
    return {**state, "resolved_plan": plan}


def planner_node(state: OrchestrationState) -> OrchestrationState:
    """Phase 4: attach RAG-grounded, personalized explanations to each
    resolved step.
    """
    plan = attach_explanations(state["resolved_plan"], state["student_state"])
    return {**state, "resolved_plan": plan}


def intake_still_pending(state: OrchestrationState) -> str:
    """Conditional-edge router: more questions to ask, or ready to resolve?"""
    return "ask_more" if state["student_state"].missing_fields() else "proceed"
