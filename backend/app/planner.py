"""LLM-at-the-edges, explanation half. Takes the deterministic resolver's
output (status + blocked_reasons — the "what" and "why", already correct) and
RAG-retrieved school-specific docs (the "how"), and asks the model to
synthesize one short, personalized explanation per step.

The model is explicitly told not to re-decide status or invent reasons — it
explains and grounds, it doesn't override. That boundary is what keeps this
"deterministic core + LLM at the edges" rather than an LLM quietly re-deciding
the plan.

One batched call, not one call per step: originally decided under
Featherless's per-plan concurrency limit (1 concurrent request on that
plan — firing 5 step calls in parallel would've just 429'd four of them),
now on Groq (see app/llm.py) mainly for latency (1 round trip instead of up
to 5). Kept as-is after the provider swap — still the right call.
"""

from __future__ import annotations

import json

from app.llm import MODEL, client
from app.rag.retrieve import retrieve
from app.schemas.plan_graph import PlanStep, ResolvedPlan, StepId, StepStatus
from app.schemas.state import StudentState

# Which corpus topic grounds each step. None = no matching corpus doc — skip
# retrieval, rely on the step's own description (e.g. student ID pickup isn't
# covered by any scraped/hand-written doc).
#
# CONFIRM_US_ADDRESS / COMPLETE_ISSS_CHECKIN added 2026-08-15 alongside the
# resolver graph expansion (see app/resolver.py) — missed at the time since
# there was no live key yet to catch the resulting KeyError. Check this dict
# whenever StepId grows.
_STEP_TOPIC: dict[StepId, str | None] = {
    StepId.CONFIRM_US_ADDRESS: None,  # no dedicated corpus doc on housing/address specifically
    StepId.COMPLETE_ISSS_CHECKIN: "ssn",  # covered by the same texas_am SSN-process doc
    StepId.OPEN_BANK_ACCOUNT: "banking",
    StepId.PAY_ENROLLMENT_FEE: "fees",
    StepId.REQUEST_ISSS_ELIGIBILITY_LETTER: "ssn",
    StepId.APPLY_SSN: "ssn",
    StepId.GET_STUDENT_ID_CARD: None,
}

_DONE_EXPLANATION = "Already done — nothing further needed here."

_EXPLAIN_TOOL = {
    "type": "function",
    "function": {
        "name": "record_step_explanations",
        "description": "Record one short explanation per step, in the same order given.",
        "parameters": {
            "type": "object",
            "properties": {
                "explanations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step_id": {"type": "string"},
                            "explanation": {"type": "string"},
                        },
                        "required": ["step_id", "explanation"],
                    },
                }
            },
            "required": ["explanations"],
            "additionalProperties": False,
        },
    },
}


def _grounding_context(step: PlanStep, state: StudentState) -> str:
    topic = _STEP_TOPIC[step.id]
    if not (topic and state.university):
        return ""
    docs = retrieve(
        query=f"{step.title}: {step.description}",
        university=state.university.value,
        visa_type=(state.visa_type.value if state.visa_type else "f1"),
        topic=topic,
        n_results=2,
    )
    return "\n\n".join(f"[{d.source}]\n{d.text}" for d in docs) if docs else ""


def attach_explanations(plan: ResolvedPlan, state: StudentState) -> ResolvedPlan:
    pending = [s for s in plan.steps if s.status != StepStatus.DONE]
    if not pending:
        steps = [s.model_copy(update={"explanation": _DONE_EXPLANATION}) for s in plan.steps]
        return plan.model_copy(update={"steps": steps})

    blocks = []
    for step in pending:
        reasons_block = "\n".join(f"  - {r}" for r in step.blocked_reasons) or "  (none — ready now)"
        context = _grounding_context(step, state)
        blocks.append(
            f"### {step.id.value}: {step.title}\n"
            f"Status: {step.status.value}\n"
            f"Blocking reasons from our rules engine (do not contradict or add to these):\n{reasons_block}\n"
            f"Grounding material:\n{context or '(no school-specific doc — stay generic, do not invent details)'}"
        )

    prompt = (
        f"A student is working through their US financial-onboarding plan. Write one short "
        f"(2-4 sentence) explanation per step below, in English. If a step is blocked, state "
        f"the ROOT cause plainly. If ready, say what to do next. Don't restate the raw reasons "
        f"list verbatim — synthesize it into prose.\n\n"
        + "\n\n".join(blocks)
        + "\n\nCall record_step_explanations with one entry per step above, using the exact "
        "step_id shown in each heading."
    )

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=1200,
        tools=[_EXPLAIN_TOOL],
        tool_choice={"type": "function", "function": {"name": "record_step_explanations"}},
        messages=[{"role": "user", "content": prompt}],
    )
    tool_call = response.choices[0].message.tool_calls[0]
    parsed = json.loads(tool_call.function.arguments)
    by_id = {e["step_id"]: e["explanation"] for e in parsed.get("explanations", [])}

    explained_steps = [
        step.model_copy(
            update={
                "explanation": _DONE_EXPLANATION
                if step.status == StepStatus.DONE
                else by_id.get(step.id.value, "(explanation unavailable — model didn't return one for this step)")
            }
        )
        for step in plan.steps
    ]
    return plan.model_copy(update={"steps": explained_steps})
