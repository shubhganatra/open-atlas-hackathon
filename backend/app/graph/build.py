"""Compiles the LangGraph orchestration graph: intake -> (resolver -> planner
| back to caller for more input).

intake is single-turn (see nodes.py docstring) — the conditional edge routes
to END whenever fields are still missing, handing control back to whatever's
driving the conversation (chat endpoint, CLI script) rather than looping
inside the graph itself. Only once intake is complete does the graph continue
through the deterministic resolver into the LLM-grounded planner.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.graph.nodes import (
    OrchestrationState,
    intake_node,
    intake_still_pending,
    planner_node,
    resolver_node,
)


def build_graph():
    graph = StateGraph(OrchestrationState)

    graph.add_node("intake", intake_node)
    graph.add_node("resolver", resolver_node)
    graph.add_node("planner", planner_node)

    graph.set_entry_point("intake")
    graph.add_conditional_edges(
        "intake",
        intake_still_pending,
        {"ask_more": END, "proceed": "resolver"},
    )
    graph.add_edge("resolver", "planner")
    graph.add_edge("planner", END)

    return graph.compile()
