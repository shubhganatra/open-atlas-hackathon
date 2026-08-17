"""Phase 7 — minimal eval harness. Checks the deterministic resolver's output
against hand-verified expected status for every step, across the money-shot
pair + 2 edge cases (per NOT-DOING: capped at this set, not a general
benchmark). This is the "small eval set (N student personas -> is the
sequence + eligibility gate correct?)" from the original brief — cheap to
build, and it's genuinely pitch material: the summary line at the bottom is
screenshot-able on its own.

Updated 2026-08-15 for the 7-step graph (added CONFIRM_US_ADDRESS,
COMPLETE_ISSS_CHECKIN) and to cover recommend_next().

No LLM involved (this evaluates the deterministic resolver + recommender,
not the LLM-generated explanations) — runs standalone, no API key needed.

    cd backend && .venv/bin/python scripts/eval_personas.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.personas import ALREADY_HAS_SSN, DEPENDENT_VISA_NO_JOB, PRIYA, WEI
from app.recommend import recommend_next
from app.resolver import resolve_plan
from app.schemas.plan_graph import StepId, StepStatus
from app.schemas.state import StudentState

Expected = dict[StepId, StepStatus]

# Hand-verified expected status per step, per persona. This table IS the eval
# spec: it should only ever change on a deliberate rules update, never to
# make a run pass — that would be evaluating the code against itself.
CASES: list[tuple[StudentState, str, Expected, StepId | None]] = [
    (
        PRIYA,
        "Priya (on-campus job offer)",
        {
            StepId.CONFIRM_US_ADDRESS: StepStatus.READY,
            StepId.COMPLETE_ISSS_CHECKIN: StepStatus.READY,
            StepId.OPEN_BANK_ACCOUNT: StepStatus.BLOCKED,
            StepId.PAY_ENROLLMENT_FEE: StepStatus.READY,
            StepId.REQUEST_ISSS_ELIGIBILITY_LETTER: StepStatus.BLOCKED,
            StepId.APPLY_SSN: StepStatus.BLOCKED,
            StepId.GET_STUDENT_ID_CARD: StepStatus.BLOCKED,
        },
        StepId.PAY_ENROLLMENT_FEE,  # only READY step with a deadline
    ),
    (
        WEI,
        "Wei (no job offer)",
        {
            StepId.CONFIRM_US_ADDRESS: StepStatus.READY,
            StepId.COMPLETE_ISSS_CHECKIN: StepStatus.READY,
            StepId.OPEN_BANK_ACCOUNT: StepStatus.BLOCKED,
            StepId.PAY_ENROLLMENT_FEE: StepStatus.READY,
            StepId.REQUEST_ISSS_ELIGIBILITY_LETTER: StepStatus.BLOCKED,
            StepId.APPLY_SSN: StepStatus.BLOCKED,
            StepId.GET_STUDENT_ID_CARD: StepStatus.BLOCKED,
        },
        StepId.PAY_ENROLLMENT_FEE,
    ),
    (
        ALREADY_HAS_SSN,
        "Ananya (edge case: already has SSN + letter + checkin)",
        {
            StepId.CONFIRM_US_ADDRESS: StepStatus.READY,
            StepId.COMPLETE_ISSS_CHECKIN: StepStatus.DONE,
            StepId.OPEN_BANK_ACCOUNT: StepStatus.BLOCKED,
            StepId.PAY_ENROLLMENT_FEE: StepStatus.READY,
            StepId.REQUEST_ISSS_ELIGIBILITY_LETTER: StepStatus.DONE,
            StepId.APPLY_SSN: StepStatus.DONE,
            StepId.GET_STUDENT_ID_CARD: StepStatus.BLOCKED,
        },
        StepId.PAY_ENROLLMENT_FEE,
    ),
    (
        DEPENDENT_VISA_NO_JOB,
        "Raj (edge case: dependents, no job offer)",
        {
            StepId.CONFIRM_US_ADDRESS: StepStatus.READY,
            StepId.COMPLETE_ISSS_CHECKIN: StepStatus.READY,
            StepId.OPEN_BANK_ACCOUNT: StepStatus.BLOCKED,
            StepId.PAY_ENROLLMENT_FEE: StepStatus.READY,
            StepId.REQUEST_ISSS_ELIGIBILITY_LETTER: StepStatus.BLOCKED,
            StepId.APPLY_SSN: StepStatus.BLOCKED,
            StepId.GET_STUDENT_ID_CARD: StepStatus.BLOCKED,
        },
        StepId.PAY_ENROLLMENT_FEE,
    ),
]


def main() -> None:
    rows: list[tuple[str, str, str, str, bool]] = []
    for state, label, expected, expected_recommendation in CASES:
        plan = resolve_plan(state)
        actual_by_id = {s.id: s.status for s in plan.steps}
        for step_id, expected_status in expected.items():
            actual_status = actual_by_id[step_id]
            rows.append((label, step_id.value, expected_status.value, actual_status.value, actual_status == expected_status))

        actual_recommendation = recommend_next(plan)
        rec_expected_s = expected_recommendation.value if expected_recommendation else "(none)"
        rec_actual_s = actual_recommendation.value if actual_recommendation else "(none)"
        rows.append((label, "[recommend_next]", rec_expected_s, rec_actual_s, actual_recommendation == expected_recommendation))

    name_w = max(len(r[0]) for r in rows)
    step_w = max(len(r[1]) for r in rows)
    header = f"{'persona':<{name_w}}  {'step':<{step_w}}  {'expected':<8}  {'actual':<8}  result"
    print(header)
    print("-" * len(header))
    for label, step, expected_s, actual_s, passed in rows:
        print(f"{label:<{name_w}}  {step:<{step_w}}  {expected_s:<8}  {actual_s:<8}  {'PASS' if passed else 'FAIL'}")

    total = len(rows)
    passed_count = sum(1 for r in rows if r[4])
    print()
    print(f"{passed_count}/{total} checks passed" + ("" if passed_count == total else " — FAILURES ABOVE"))
    if passed_count != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
