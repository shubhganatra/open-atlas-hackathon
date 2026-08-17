"""Phase 4 verification: an interactive terminal chat that drives the real
LangGraph orchestration turn by turn — intake extraction (LLM) -> deterministic
resolver -> RAG-grounded explanations (LLM) — end to end, for real API calls.

Requires FEATHERLESS_API_KEY set (backend/.env, loaded via python-dotenv).

    cd backend && .venv/bin/python scripts/chat_intake.py
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.graph.build import build_graph
from app.schemas.state import StudentState


def main() -> None:
    graph = build_graph()
    state = {"student_state": StudentState(student_id=str(uuid.uuid4())[:8])}

    print("Tell me about your situation (school, visa, arrival date, job offer, dependents).")
    print("You can answer in one message or several — I'll ask about whatever's still missing.\n")

    while True:
        message = input("you> ").strip()
        if not message:
            continue
        state["latest_message"] = message
        state = graph.invoke(state)

        if state.get("resolved_plan"):
            plan = state["resolved_plan"]
            print(f"\n=== Resolved plan for {plan.student_id} ===")
            for step in plan.steps:
                print(f"\n[{step.status.value.upper()}] {step.title}")
                print(f"  {step.explanation}")
            break

        questions = state.get("pending_questions") or []
        if questions:
            print(f"copilot> {questions[0]}\n")


if __name__ == "__main__":
    main()
