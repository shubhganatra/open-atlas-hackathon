"""Phase 5 per-step artifacts. The two are built deliberately differently:

- build_ics: fully deterministic, no LLM call. This is "the one genuinely
  automated real action" from the brief, and it has to be reliable on stage —
  not dependent on a model call succeeding. Pure function over a ResolvedPlan.
- draft_isss_email: LLM-at-the-edges, grounded via the same RAG retrieval as
  the planner. Still just a *draft* — the student reviews and sends it
  themselves. We never contact ISSS, a bank, or SSA on the student's behalf;
  see DECISIONS.md's "no real system integrations, human executes the
  irreversible click" call. This module is where that principle becomes a
  concrete artifact rather than just a design note.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from icalendar import Calendar, Event

from app.llm import MODEL, client
from app.rag.retrieve import retrieve
from app.schemas.plan_graph import ResolvedPlan
from app.schemas.state import StudentState


def build_ics(plan: ResolvedPlan) -> bytes:
    cal = Calendar()
    cal.add("prodid", "-//Financial Onboarding Copilot//onboarding-copilot//")
    cal.add("version", "2.0")

    for step in plan.steps:
        if step.deadline is None:
            continue
        event = Event()
        event.add("summary", f"Deadline: {step.title}")
        event.add("description", step.explanation or step.description)
        event.add("dtstart", step.deadline)
        event.add("dtstamp", datetime.now(timezone.utc))
        event.add("uid", f"{plan.student_id}-{step.id.value}@onboarding-copilot")
        cal.add_component(event)

    # A student with no fixed-date steps yet just gets a valid empty calendar,
    # not an error — deadlines only exist once a step's StepDefinition has one.
    return cal.to_ical()


_EMAIL_TOOL = {
    "type": "function",
    "function": {
        "name": "record_email_draft",
        "description": "Record a drafted email requesting the ISSS SSN eligibility letter.",
        "parameters": {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["subject", "body"],
            "additionalProperties": False,
        },
    },
}


def draft_isss_email(state: StudentState) -> dict:
    context = ""
    if state.university:
        docs = retrieve(
            query="ISSS SSN eligibility letter request process",
            university=state.university.value,
            visa_type=(state.visa_type.value if state.visa_type else "f1"),
            topic="ssn",
            n_results=2,
        )
        context = "\n\n".join(f"[{d.source}]\n{d.text}" for d in docs)

    job_offer = (state.job_offer_type.value if state.job_offer_type else "on_campus").replace("_", " ")
    visa = state.visa_type.value.upper() if state.visa_type else "F-1"

    prompt = (
        "Draft a short, polite email from an international student to their university's "
        "International Student & Scholar Services (ISSS) office, requesting the SSN eligibility "
        f"letter.\n\nStudent's situation: {job_offer} job offer, visa type {visa}.\n\n"
        f"Grounding material on this school's actual process (reference it naturally if relevant):\n"
        f"{context or '(no school-specific doc — keep it generic)'}\n\n"
        "Call record_email_draft with a subject and body. Keep the body under 150 words, "
        "professional, and specific to the student's situation."
    )

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=500,
        tools=[_EMAIL_TOOL],
        tool_choice={"type": "function", "function": {"name": "record_email_draft"}},
        messages=[{"role": "user", "content": prompt}],
    )
    tool_call = response.choices[0].message.tool_calls[0]
    return json.loads(tool_call.function.arguments)
