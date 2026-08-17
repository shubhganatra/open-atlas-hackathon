"""The deterministic core — Phase 2, THE differentiator.

Pure Python. No LLM calls, no network calls, no randomness. Given a StudentState,
walks a fixed step graph and returns each step's status (done/ready/blocked) plus
human-readable blocking reasons. This module must be understandable and correct
on its own, independent of everything else in the system — the LLM only explains
and personalizes what this module decides, it never overrides it.

Locked rule (DECISIONS.md, 2026-08-15): applying for an SSN realistically
requires BOTH a job offer AND the ISSS eligibility letter. Modeled as a two-hop
chain rather than a flat AND: a job offer gates *requesting* the letter, and
having the letter gates the SSN application itself. This mirrors the real
process (SSA won't accept an SSN application without the ISSS letter; ISSS won't
issue the letter without a qualifying job offer) and is what lets the resolver
produce a clear causal chain of "why" rather than a single flat reason.
"""

from __future__ import annotations

from datetime import date

from app.schemas.plan_graph import PlanStep, ResolvedPlan, StepDefinition, StepId, StepStatus
from app.schemas.state import JobOfferType, StudentState

# --- Fixed step graph --------------------------------------------------------
# NOTE: deadline below is Texas A&M's real Fall 2026 full-payment due date
# (confirmed via Phase 3 scrape of sbs.tamu.edu/billing-payments/due-dates —
# see app/data/corpus/texas_am/fee_deadlines.md), replacing the Phase 2
# placeholder. Not yet school-parameterized — still hardcoded to A&M's date
# regardless of which university a student is at; fine for the money-shot demo
# (both personas are A&M), a real gap if Purdue personas need this later.
#
# CONFIRM_US_ADDRESS and COMPLETE_ISSS_CHECKIN added 2026-08-15 after a full
# review pass across all 5 original steps for missing real-world
# preconditions — both are grounded in our own corpus docs, not invented:
# app/data/corpus/general/bank_account_without_ssn.md already lists proof of
# address as a requirement, and app/data/corpus/texas_am/ssn_on_campus_employment.md
# already says ISSS Check-In must be complete before the eligibility letter.
# The other 3 steps were reviewed and left as-is — no similarly-grounded gap found.
#
# link_label/link_url added 2026-08-15: real, verified URLs (either already
# scraped in Phase 3's corpus, or looked up the same way) for where to
# actually take the action — e.g. request_isss_eligibility_letter points at
# the ISSS Portal, not "email ISSS", since A&M has a self-service form for
# exactly this. See DECISIONS.md "Per-step action links".
STEP_DEFINITIONS: list[StepDefinition] = [
    StepDefinition(
        id=StepId.CONFIRM_US_ADDRESS,
        title="Confirm your US address",
        description="Provide proof of your local address (a signed housing/dorm agreement is usually accepted before a permanent lease exists).",
        prerequisites=[],
        link_label="Texas A&M Residence Life",
        link_url="https://reslife.tamu.edu/",
    ),
    StepDefinition(
        id=StepId.COMPLETE_ISSS_CHECKIN,
        title="Complete ISSS Check-In",
        description="Confirm your international student office check-in is complete — required before requesting the SSN eligibility letter.",
        prerequisites=[],
        link_label="Check in on the ISSS Portal",
        link_url="https://isssportal.tamu.edu/",
    ),
    StepDefinition(
        id=StepId.OPEN_BANK_ACCOUNT,
        title="Open a US bank account",
        description="Open a checking account using your passport + I-20 — no SSN required to start.",
        prerequisites=[StepId.CONFIRM_US_ADDRESS],
        link_label="A&M's bank partnerships",
        link_url="https://sbs.tamu.edu/info-for/banking-relationships/index.html",
    ),
    StepDefinition(
        id=StepId.PAY_ENROLLMENT_FEE,
        title="Pay enrollment / confirmation fee",
        description="Pay the fixed-deadline enrollment fee to confirm your seat.",
        prerequisites=[],
        deadline=date(2026, 8, 21),
        link_label="Pay on the Student Business Services portal",
        link_url="https://sbs.tamu.edu/billing-payments/due-dates/index.html",
    ),
    StepDefinition(
        id=StepId.REQUEST_ISSS_ELIGIBILITY_LETTER,
        title="Request ISSS SSN eligibility letter",
        description=(
            "Request the letter confirming your job qualifies you to apply for an SSN — "
            "A&M's ISSS Portal handles this request directly, no email needed."
        ),
        prerequisites=[StepId.COMPLETE_ISSS_CHECKIN],
        link_label="Request on the ISSS Portal",
        link_url="https://isssportal.tamu.edu/",
    ),
    StepDefinition(
        id=StepId.APPLY_SSN,
        title="Apply for a Social Security Number",
        description="Apply at the SSA office with your ISSS eligibility letter, I-20, passport, and I-94.",
        prerequisites=[StepId.REQUEST_ISSS_ELIGIBILITY_LETTER],
        link_label="Find your nearest SSA office",
        link_url="https://www.ssa.gov/locator/",
    ),
    StepDefinition(
        id=StepId.GET_STUDENT_ID_CARD,
        title="Get your student ID card",
        description="Pick up your student ID once your enrollment fee has cleared.",
        prerequisites=[StepId.PAY_ENROLLMENT_FEE],
        link_label="Aggie Card Office",
        link_url="https://aggiecard.tamu.edu/",
    ),
]

_STEP_DEFS_BY_ID: dict[StepId, StepDefinition] = {d.id: d for d in STEP_DEFINITIONS}

# Which StudentState boolean flag marks each step DONE.
_DONE_FLAG: dict[StepId, str] = {
    StepId.CONFIRM_US_ADDRESS: "has_us_address",
    StepId.COMPLETE_ISSS_CHECKIN: "has_isss_checkin",
    StepId.OPEN_BANK_ACCOUNT: "has_bank_account",
    StepId.PAY_ENROLLMENT_FEE: "has_paid_enrollment_fee",
    StepId.REQUEST_ISSS_ELIGIBILITY_LETTER: "has_isss_eligibility_letter",
    StepId.APPLY_SSN: "has_ssn",
    StepId.GET_STUDENT_ID_CARD: "has_student_id_card",
}

# Exposed for main.py's "mark step done" endpoint — resolves a StepId to the
# StudentState flag it sets. Kept here (not duplicated) since this mapping is
# the resolver's, and the endpoint must never invent its own notion of what
# "done" means for a step.
def done_flag_for(step_id: StepId) -> str | None:
    return _DONE_FLAG.get(step_id)


def _is_done(step_id: StepId, state: StudentState) -> bool:
    return bool(getattr(state, _DONE_FLAG[step_id]))


def _state_level_block_reasons(step_id: StepId, state: StudentState) -> list[str]:
    """Blocking reasons rooted in a fact about the student rather than another
    step being incomplete. Currently the only one: no job offer blocks
    requesting the ISSS letter in the first place.
    """
    if step_id == StepId.REQUEST_ISSS_ELIGIBILITY_LETTER:
        if state.job_offer_type in (None, JobOfferType.NONE):
            return ["No job offer on file — ISSS will not issue the letter without one (on-campus or CPT/OPT)."]
    return []


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def resolve_plan(state: StudentState) -> ResolvedPlan:
    """Resolve every step's status for a given student. Order-independent:
    resolves each step's prerequisites recursively (memoized) rather than
    assuming STEP_DEFINITIONS is declared in dependency order, so the graph
    stays correct even as steps are added/reordered later.
    """
    resolved: dict[StepId, PlanStep] = {}

    def resolve_step(step_id: StepId) -> PlanStep:
        if step_id in resolved:
            return resolved[step_id]
        defn = _STEP_DEFS_BY_ID[step_id]

        if _is_done(step_id, state):
            step = PlanStep(
                id=step_id, title=defn.title, description=defn.description,
                status=StepStatus.DONE, blocked_reasons=[], deadline=defn.deadline,
                link_label=defn.link_label, link_url=defn.link_url,
            )
            resolved[step_id] = step
            return step

        reasons: list[str] = []
        for prereq_id in defn.prerequisites:
            prereq_step = resolve_step(prereq_id)
            if prereq_step.status != StepStatus.DONE:
                reasons.append(f'Requires "{prereq_step.title}" to be completed first.')
                # Bubble up the prereq's own root-cause reasons so the final message
                # explains the *ultimate* blocker, not just "a prereq isn't done."
                reasons.extend(prereq_step.blocked_reasons)

        reasons.extend(_state_level_block_reasons(step_id, state))
        reasons = _dedupe(reasons)

        step = PlanStep(
            id=step_id, title=defn.title, description=defn.description,
            status=StepStatus.BLOCKED if reasons else StepStatus.READY,
            blocked_reasons=reasons, deadline=defn.deadline,
            link_label=defn.link_label, link_url=defn.link_url,
        )
        resolved[step_id] = step
        return step

    for step_id in _STEP_DEFS_BY_ID:
        resolve_step(step_id)

    return ResolvedPlan(student_id=state.student_id, steps=[resolved[d.id] for d in STEP_DEFINITIONS])
