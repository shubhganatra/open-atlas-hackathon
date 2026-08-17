"""LLM-at-the-edges, extraction half: turns a free-text answer into structured
StudentState fields via forced tool use. This is the one place natural
language becomes data — everything downstream (resolver, RAG retrieval) works
off the structured result, never off the raw text again.

Uses the OpenAI-compatible function-calling shape (Featherless — see
app/llm.py): `tools=[{"type": "function", "function": {...}}]` and
`tool_choice={"type": "function", "function": {"name": ...}}` to force the
call. Unlike Anthropic's tool_use blocks, the arguments come back as a JSON
*string* that must be parsed, not a pre-parsed dict.
"""

from __future__ import annotations

import json
from datetime import date

from app.llm import MODEL, client
from app.schemas.state import JobOfferType, StudentState, University, VisaType

_EXTRACT_TOOL = {
    "type": "function",
    "function": {
        "name": "record_student_facts",
        "description": (
            "Record facts about the student's situation found in their message. "
            "Only include fields you're confident about; omit anything not mentioned "
            "or genuinely ambiguous — a missing field just means we'll ask again."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "university": {"type": "string", "enum": [u.value for u in University]},
                "visa_type": {"type": "string", "enum": [v.value for v in VisaType]},
                "arrival_date": {"type": "string", "description": "ISO date, YYYY-MM-DD"},
                "job_offer_type": {"type": "string", "enum": [j.value for j in JobOfferType]},
                "has_dependents": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
    },
}


def extract_fields(message: str) -> dict:
    """Raw extraction — returns whatever fields the model was confident about,
    as a plain dict with StudentState-compatible keys. Caller merges it.
    """
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=512,
        tools=[_EXTRACT_TOOL],
        tool_choice={"type": "function", "function": {"name": "record_student_facts"}},
        messages=[{"role": "user", "content": message}],
    )
    tool_call = response.choices[0].message.tool_calls[0]
    return json.loads(tool_call.function.arguments)


def apply_extracted_fields(state: StudentState, message: str) -> StudentState:
    """Extract from `message` and merge into `state`, only filling fields that
    are still unset — an extraction never overwrites an already-known fact.
    """
    fields = extract_fields(message)
    updates: dict = {}

    if state.university is None and "university" in fields:
        updates["university"] = University(fields["university"])
    if state.visa_type is None and "visa_type" in fields:
        updates["visa_type"] = VisaType(fields["visa_type"])
    if state.arrival_date is None and "arrival_date" in fields:
        try:
            updates["arrival_date"] = date.fromisoformat(fields["arrival_date"])
        except ValueError:
            pass  # malformed date from the model — leave it missing, ask again
    if state.job_offer_type is None and "job_offer_type" in fields:
        updates["job_offer_type"] = JobOfferType(fields["job_offer_type"])
    if state.has_dependents is None and "has_dependents" in fields:
        updates["has_dependents"] = fields["has_dependents"]

    return state.model_copy(update=updates)
