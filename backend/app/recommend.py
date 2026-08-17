"""Deterministic "what should I do next" ranking over an already-resolved
plan. Zero LLM involved — this is a policy layered on top of the resolver's
output, not a new decision about status or eligibility (it never looks at
StudentState directly, only at PlanStep.status/deadline, which the resolver
already decided). LLM-flavored explanation text ("here's why this is your
best next move") can layer on top of this later, once FEATHERLESS_API_KEY is
live, without changing the ranking itself.

Ranking: among READY steps, prefer the one with the nearest deadline; if none
have a deadline, take the first in graph order. Deliberately simple — this is
a hackathon demo, not a scheduling engine.
"""

from __future__ import annotations

from app.schemas.plan_graph import ResolvedPlan, StepId, StepStatus


def recommend_next(plan: ResolvedPlan) -> StepId | None:
    ready = [s for s in plan.steps if s.status == StepStatus.READY]
    if not ready:
        return None
    with_deadline = [s for s in ready if s.deadline is not None]
    if with_deadline:
        return min(with_deadline, key=lambda s: s.deadline).id
    return ready[0].id
