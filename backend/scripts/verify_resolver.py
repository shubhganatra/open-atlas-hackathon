"""Phase 2 verification: does the deterministic resolver produce the correct
money-shot result? Run standalone, no server needed — that's the point.

    cd backend && .venv/bin/python scripts/verify_resolver.py

Asserts hard on the money-shot pair (PRIYA vs WEI); prints a readable table for
every persona so it's easy to eyeball. This script is also the seed of the
Phase 7 eval harness — expected-status assertions here should carry forward
almost unchanged into that script's persona table.

Updated 2026-08-15 for the 7-step graph (CONFIRM_US_ADDRESS,
COMPLETE_ISSS_CHECKIN added — see app/resolver.py) and to walk through the
new "mark done -> recommend next" loop, which is the actual live-demo flow
now (see DECISIONS.md, "Mark done" / "Recommend logic").
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.data.personas import ALREADY_HAS_SSN, DEPENDENT_VISA_NO_JOB, PRIYA, WEI
from app.recommend import recommend_next
from app.resolver import resolve_plan
from app.schemas.plan_graph import StepId, StepStatus


def _print_plan(label: str, plan) -> None:
    print(f"\n=== {label} ({plan.student_id}) ===")
    for step in plan.steps:
        line = f"  [{step.status.value.upper():7}] {step.title}"
        print(line)
        for reason in step.blocked_reasons:
            print(f"            - {reason}")
    rec = next((s for s in plan.steps if s.id == plan.recommended_step_id), None)
    print(f"  -> recommended next: {rec.title if rec else '(none)'}")


def _status(plan, step_id: StepId) -> StepStatus:
    return next(s.status for s in plan.steps if s.id == step_id)


def main() -> None:
    priya_plan = resolve_plan(PRIYA)
    wei_plan = resolve_plan(WEI)
    ssn_plan = resolve_plan(ALREADY_HAS_SSN)
    dependent_plan = resolve_plan(DEPENDENT_VISA_NO_JOB)

    for plan in (priya_plan, wei_plan, ssn_plan, dependent_plan):
        plan_with_rec = plan.model_copy(update={"recommended_step_id": recommend_next(plan)})
        _print_plan(
            {"priya": "PRIYA — has on-campus job offer", "wei": "WEI — no job offer",
             "ananya": "ANANYA — already has SSN (edge case)", "raj": "RAJ — dependents, no job offer (edge case)"}[plan.student_id],
            plan_with_rec,
        )

    # --- The money-shot assertion: same university, different job status,
    # different SSN gating, with the reason legible in blocked_reasons. -------
    assert _status(priya_plan, StepId.REQUEST_ISSS_ELIGIBILITY_LETTER) == StepStatus.BLOCKED, \
        "Priya hasn't completed ISSS Check-In yet — should be BLOCKED on that alone"
    priya_letter_reasons = next(s for s in priya_plan.steps if s.id == StepId.REQUEST_ISSS_ELIGIBILITY_LETTER).blocked_reasons
    assert not any("job offer" in r.lower() for r in priya_letter_reasons), \
        "Priya HAS a job offer — her block reason should be check-in only, never job-offer"

    assert _status(wei_plan, StepId.REQUEST_ISSS_ELIGIBILITY_LETTER) == StepStatus.BLOCKED
    wei_letter_reasons = next(s for s in wei_plan.steps if s.id == StepId.REQUEST_ISSS_ELIGIBILITY_LETTER).blocked_reasons
    assert any("job offer" in r.lower() for r in wei_letter_reasons), \
        "Wei has no job offer — that root cause must appear in her block reasons"
    assert len(wei_letter_reasons) > len(priya_letter_reasons), \
        "Wei is blocked by strictly more things than Priya (checkin AND job offer vs. checkin alone)"

    # Both start with the same top recommendation: the fee deadline dominates
    # since neither has completed anything yet.
    assert priya_plan.model_copy(update={"recommended_step_id": recommend_next(priya_plan)}).recommended_step_id == StepId.PAY_ENROLLMENT_FEE
    assert wei_plan.model_copy(update={"recommended_step_id": recommend_next(wei_plan)}).recommended_step_id == StepId.PAY_ENROLLMENT_FEE

    assert _status(ssn_plan, StepId.APPLY_SSN) == StepStatus.DONE, "Ananya already has an SSN — should show DONE"
    assert _status(dependent_plan, StepId.REQUEST_ISSS_ELIGIBILITY_LETTER) == StepStatus.BLOCKED, \
        "Raj has no job offer regardless of dependents — should still be BLOCKED"

    # --- Walkthrough: the actual live-demo loop -------------------------------
    # Complete Priya's fee, address, and check-in one at a time and watch both
    # her status and the recommendation shift — this is exactly what
    # POST /personas/{id}/steps/{step_id}/complete does in the running app.
    print("\n=== WALKTHROUGH: Priya completes steps one at a time ===")
    state = PRIYA.model_copy()
    for flag, label in [
        ("has_paid_enrollment_fee", "pays enrollment fee"),
        ("has_us_address", "confirms US address"),
        ("has_isss_checkin", "completes ISSS Check-In"),
    ]:
        state = state.model_copy(update={flag: True})
        plan = resolve_plan(state)
        rec = next((s for s in plan.steps if s.id == recommend_next(plan)), None)
        print(f"  after Priya {label}: recommended next -> {rec.title if rec else '(none)'}")
    final_letter_status = _status(resolve_plan(state), StepId.REQUEST_ISSS_ELIGIBILITY_LETTER)
    assert final_letter_status == StepStatus.READY, \
        "Once check-in is done (and she already has a job offer), the letter step should flip to READY"
    print(f"  -> Request ISSS letter is now: {final_letter_status.value.upper()} (job offer + check-in both satisfied)")

    print("\nAll resolver assertions passed.")


if __name__ == "__main__":
    main()
