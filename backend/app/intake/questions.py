"""Deterministic follow-up questions, one per missing field. Templated, not
LLM-generated — phrasing "what's your visa type?" doesn't need a model call,
and keeping it deterministic means the intake loop's question order is
predictable and testable. The LLM's job is parsing the *answer*, not writing
the question.
"""

_QUESTION_BY_FIELD = {
    "university": "Which university are you attending?",
    "visa_type": "What's your visa type — F-1 or J-1?",
    "arrival_date": "When do you arrive (or did you arrive) in the US?",
    "job_offer_type": (
        "Do you have a job offer lined up — on-campus, off-campus (CPT/OPT), or none yet?"
    ),
    "has_dependents": "Do you have any dependents (spouse/children) coming with you?",
}


def next_question(missing_fields: list[str]) -> str | None:
    if not missing_fields:
        return None
    return _QUESTION_BY_FIELD[missing_fields[0]]
