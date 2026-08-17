"""Phase 4 verification: scripted (non-interactive) end-to-end run of the real
pipeline — LLM extraction -> deterministic resolver -> LLM explanation — for
both money-shot personas, using natural-language descriptions instead of
structured StudentState objects (proving intake extraction actually works,
not just the resolver in isolation).

Requires FEATHERLESS_API_KEY set (backend/.env). This is the one script in the
repo that spends real API calls — free under the hackathon promo code, unlike
the Phase 2/3 scripts which are pure local logic and need no key at all.

    cd backend && .venv/bin/python scripts/verify_intake_e2e.py
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.graph.build import build_graph
from app.schemas.plan_graph import StepId, StepStatus
from app.schemas.state import StudentState

PRIYA_MESSAGE = (
    "I'm starting at Texas A&M this fall as an F-1 student, arriving August 10th. "
    "I already have an on-campus job lined up, and I don't have any dependents."
)
WEI_MESSAGE = (
    "I'll be attending Texas A&M on an F-1 visa, arriving August 10th. "
    "I don't have a job yet and no dependents."
)


def run_persona(label: str, message: str):
    graph = build_graph()
    state = {"student_state": StudentState(student_id=str(uuid.uuid4())[:8]), "latest_message": message}
    state = graph.invoke(state)

    if not state.get("resolved_plan"):
        # Extraction didn't get everything from one message — show what's still
        # missing rather than silently failing. (Expected to be rare given how
        # explicit the scripted messages are; if it happens, it's real signal
        # about extraction quality, not a bug in this script.)
        print(f"\n=== {label}: extraction incomplete ===")
        print("Still missing:", state["student_state"].missing_fields())
        print("Next question would be:", (state.get("pending_questions") or [None])[0])
        return None

    plan = state["resolved_plan"]
    print(f"\n=== {label} ({plan.student_id}) ===")
    for step in plan.steps:
        print(f"\n[{step.status.value.upper()}] {step.title}")
        print(f"  {step.explanation}")
    return plan


def main() -> None:
    priya_plan = run_persona("PRIYA", PRIYA_MESSAGE)
    wei_plan = run_persona("WEI", WEI_MESSAGE)

    if priya_plan and wei_plan:
        priya_ssn = next(s for s in priya_plan.steps if s.id == StepId.APPLY_SSN)
        wei_ssn = next(s for s in wei_plan.steps if s.id == StepId.APPLY_SSN)
        assert priya_ssn.status == StepStatus.BLOCKED
        assert wei_ssn.status == StepStatus.BLOCKED
        assert priya_ssn.explanation != wei_ssn.explanation, (
            "Priya and Wei are blocked for different reasons — their explanations should differ"
        )
        print("\nEnd-to-end pipeline verified for both personas.")


if __name__ == "__main__":
    main()
