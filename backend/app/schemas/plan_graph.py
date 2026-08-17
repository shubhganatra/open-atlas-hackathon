"""Dependency-graph schema for the sequenced plan. Steps are nodes; prerequisites
are edges. This module only defines the shape — the actual gating LOGIC (which
prerequisites are satisfied given a StudentState) is the deterministic resolver
built in Phase 2, deliberately kept out of this file so the schema stays inert
data and the resolver stays independently unit-testable.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class StepId(StrEnum):
    CONFIRM_US_ADDRESS = "confirm_us_address"  # 2026-08-15: added as a real prerequisite, not a UI nicety
    COMPLETE_ISSS_CHECKIN = "complete_isss_checkin"
    OPEN_BANK_ACCOUNT = "open_bank_account"
    REQUEST_ISSS_ELIGIBILITY_LETTER = "request_isss_eligibility_letter"
    APPLY_SSN = "apply_ssn"
    PAY_ENROLLMENT_FEE = "pay_enrollment_fee"
    GET_STUDENT_ID_CARD = "get_student_id_card"


class StepStatus(StrEnum):
    DONE = "done"
    READY = "ready"
    BLOCKED = "blocked"


class StepDefinition(BaseModel):
    """Static definition of a step: what it is and what it depends on. One fixed
    list of these constitutes "the graph" — resolver walks it against a
    StudentState to produce PlanStep results below.
    """

    id: StepId
    title: str
    description: str
    prerequisites: list[StepId] = []
    deadline: date | None = None
    # 2026-08-15: the real-world place to actually take this action — e.g. a
    # university portal, not "email the office" when they have a self-service
    # form. Static and school-specific (Texas A&M for now, same scope
    # limitation as the fee deadline above) rather than invented per-request.
    link_label: str | None = None
    link_url: str | None = None


class PlanStep(BaseModel):
    """A StepDefinition resolved against a specific StudentState."""

    id: StepId
    title: str
    description: str
    status: StepStatus
    blocked_reasons: list[str] = []
    deadline: date | None = None
    link_label: str | None = None
    link_url: str | None = None
    # Filled by app/planner.py (Phase 4), never by the resolver — keeps the
    # deterministic core (app/resolver.py) provably free of LLM output.
    explanation: str | None = None


class ResolvedPlan(BaseModel):
    student_id: str
    steps: list[PlanStep]
    # Filled by app/recommend.py — deterministic, zero LLM, computed from the
    # steps above (never decides status itself, same boundary as PlanStep.explanation).
    recommended_step_id: StepId | None = None
