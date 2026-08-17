"""Student state schema — the structured facts the intake loop extracts.

Kept intentionally narrow: only what the deterministic resolver (app/graph logic,
not this LangGraph orchestration module) needs to gate the money-shot personas plus
a couple of edge cases. Do not grow this file speculatively — see PLAN.md Phase 1
risk note (schema over-design is the time sink to avoid).
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class University(StrEnum):
    TEXAS_AM = "texas_am"
    PURDUE = "purdue"  # locked Phase 3 — matches app/data/corpus/purdue metadata tag


class VisaType(StrEnum):
    F1 = "f1"
    J1 = "j1"


class JobOfferType(StrEnum):
    NONE = "none"
    ON_CAMPUS = "on_campus"
    OFF_CAMPUS_CPT_OPT = "off_campus_cpt_opt"


class StudentState(BaseModel):
    """Structured situation for one student. This is what the intake loop fills in
    and what the resolver (Phase 2) consumes. Everything except student_id is
    Optional so the intake loop can represent "not yet known" and ask only for
    what's missing.
    """

    student_id: str

    university: University | None = None
    visa_type: VisaType | None = None
    arrival_date: date | None = None

    job_offer_type: JobOfferType | None = None
    has_dependents: bool | None = None

    has_ssn: bool = False
    has_bank_account: bool = False
    has_isss_eligibility_letter: bool = False
    has_paid_enrollment_fee: bool = False
    has_student_id_card: bool = False
    has_us_address: bool = False  # 2026-08-15: gates OPEN_BANK_ACCOUNT — see app/resolver.py
    has_isss_checkin: bool = False  # 2026-08-15: gates REQUEST_ISSS_ELIGIBILITY_LETTER

    def missing_fields(self) -> list[str]:
        """Fields the intake loop still needs to ask about. Boolean has_* fields
        default to False (assumed not-done-yet) rather than counting as missing —
        only the situational fields block progress until known.
        """
        required = ("university", "visa_type", "arrival_date", "job_offer_type", "has_dependents")
        return [f for f in required if getattr(self, f) is None]
