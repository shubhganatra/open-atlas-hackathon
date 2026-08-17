"""Demo personas. PRIYA and WEI are THE money-shot pair: same university, same
visa type, same arrival date — the only material difference is job-offer status
— so any difference in their resolved plans is attributable to that one variable.
This is deliberate: it's what makes the demo's "why is one blocked and the other
isn't" moment legible rather than a wall of unrelated differences.

Also doubles as the seed of the Phase 7 eval set.
"""

from datetime import date

from app.schemas.state import JobOfferType, StudentState, University, VisaType

PRIYA = StudentState(
    student_id="priya",
    university=University.TEXAS_AM,
    visa_type=VisaType.F1,
    arrival_date=date(2026, 8, 10),
    job_offer_type=JobOfferType.ON_CAMPUS,
    has_dependents=False,
)

WEI = StudentState(
    student_id="wei",
    university=University.TEXAS_AM,
    visa_type=VisaType.F1,
    arrival_date=date(2026, 8, 10),
    job_offer_type=JobOfferType.NONE,
    has_dependents=False,
)

# Edge cases for Phase 7 (kept minimal per NOT-DOING — not a general benchmark).
ALREADY_HAS_SSN = StudentState(
    student_id="ananya",
    university=University.TEXAS_AM,
    visa_type=VisaType.F1,
    arrival_date=date(2026, 8, 10),
    job_offer_type=JobOfferType.OFF_CAMPUS_CPT_OPT,
    has_dependents=False,
    has_isss_checkin=True,  # logically required to have gotten the letter below
    has_isss_eligibility_letter=True,
    has_ssn=True,
)

DEPENDENT_VISA_NO_JOB = StudentState(
    student_id="raj",
    university=University.TEXAS_AM,
    visa_type=VisaType.F1,
    arrival_date=date(2026, 8, 10),
    job_offer_type=JobOfferType.NONE,
    has_dependents=True,
)
