"""FastAPI entrypoint. Phase 5: the real routes the frontend calls — persona
plans (resolver + planner) and their two prepared artifacts.

Deliberately NOT a general chat/intake endpoint here — the live intake loop
(app/graph) exists and is tested (scripts/chat_intake.py), but per the
2026-08-15 scope cut the UI's primary surface is the precomputed money-shot
personas, not a conversational flow. See PLAN.md Phase 5 / DECISIONS.md.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import documents as docstore
from app.artifacts import build_ics, draft_isss_email
from app.data.personas import PRIYA, WEI
from app.planner import attach_explanations
from app.recommend import recommend_next
from app.resolver import done_flag_for, resolve_plan
from app.schemas.plan_graph import ResolvedPlan, StepId, StepStatus
from app.schemas.state import StudentState

logger = logging.getLogger(__name__)

app = FastAPI(title="Financial Onboarding Copilot")

# Local dev origins always allowed; the deployed Vercel frontend is covered by
# regex (preview + production URLs are both *.vercel.app unless a custom
# domain is attached) rather than a hardcoded string, since the exact preview
# URL changes per-deploy and isn't known in advance. ALLOWED_ORIGINS is an
# escape hatch for a custom domain, set via Render's env vars — comma-separated,
# unset by default, never committed. See DECISIONS.md "Deployment".
_extra_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", *_extra_origins],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

# The money-shot pair, keyed by id. Deliberately not a general persona CRUD
# API — see NOT-DOING. The Phase 7 edge-case personas live in app/data/personas.py
# for the eval script but aren't exposed here; the UI's story is Priya vs Wei.
#
# This dict holds the actual StudentState objects (not copies) — 2026-08-15:
# it doubles as the in-memory "mark step done" session store. Mutating a
# persona's has_* flag via /steps/{id}/complete persists for the life of this
# server process, same as everything else here (no DB — proportionate to a
# hackathon demo, resets on restart, see DECISIONS.md "Mark done").
_PERSONAS: dict[str, StudentState] = {PRIYA.student_id: PRIYA, WEI.student_id: WEI}

# Pre-populate each persona's Docs page with their mock official documents
# (admission letter; job offer letter for Priya only) — see app/documents.py.
docstore.ensure_seed_documents()


def _get_persona(persona_id: str) -> StudentState:
    persona = _PERSONAS.get(persona_id)
    if persona is None:
        raise HTTPException(status_code=404, detail=f"Unknown persona: {persona_id}")
    return persona


def _resolve_with_recommendation(state: StudentState) -> ResolvedPlan:
    plan = resolve_plan(state)
    return plan.model_copy(update={"recommended_step_id": recommend_next(plan)})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/personas")
def list_personas() -> list[dict]:
    return [
        {
            "id": p.student_id,
            "university": p.university,
            "visa_type": p.visa_type,
            "job_offer_type": p.job_offer_type,
        }
        for p in _PERSONAS.values()
    ]


@app.get("/personas/{persona_id}/plan", response_model=ResolvedPlan)
def get_plan(persona_id: str) -> ResolvedPlan:
    """Fast path: deterministic only, zero LLM involvement, so the Tracker can
    render headers/badges/blocked-reasons/links/mark-done the instant this
    resolves — never blocked on a Groq round trip. See DESIGN.md "Async Load":
    explanation text is a separate, slower fetch (get_explanations below).
    """
    state = _get_persona(persona_id)
    return _resolve_with_recommendation(state)


@app.get("/personas/{persona_id}/explanations")
def get_explanations(persona_id: str) -> dict[str, str | None]:
    """Slow path: the LLM-generated explanation per step, fetched separately
    from GET /plan so the frontend can show the deterministic plan instantly
    and fade explanations in once they arrive (or show them missing, gracefully,
    if the LLM call fails) — 2026-08-15, see DESIGN.md.
    """
    state = _get_persona(persona_id)
    plan = _resolve_with_recommendation(state)
    try:
        explained = attach_explanations(plan, state)
    except Exception as e:
        # Same graceful-degradation principle as before the split: a failed
        # LLM call means every step just has no explanation, not an error the
        # frontend has to handle specially — it already treats missing
        # explanation text as "not available yet."
        logger.warning("Explanation generation failed for %s: %s", persona_id, e)
        return {s.id.value: None for s in plan.steps}
    return {s.id.value: s.explanation for s in explained.steps}


@app.post("/personas/{persona_id}/steps/{step_id}/complete", response_model=ResolvedPlan)
def complete_step(persona_id: str, step_id: StepId) -> ResolvedPlan:
    """Mark a step done. Deliberately deterministic-only (no attach_explanations
    call) — this endpoint needs to work reliably without FEATHERLESS_API_KEY,
    since "mark done -> see what's next" is exactly the loop we want demoable
    right now. The frontend re-fetches the full (LLM-explained, when available)
    plan afterward via GET /plan.
    """
    state = _get_persona(persona_id)
    flag = done_flag_for(step_id)
    if flag is None:
        raise HTTPException(status_code=400, detail=f"Unknown step: {step_id}")

    # Only a currently-READY step can be completed — the resolver is the only
    # source of truth for what's actually actionable right now. This also
    # guards against completing an already-DONE step (a no-op that would be
    # confusing to allow) or a BLOCKED one (which would be lying about how the
    # real process works).
    current = next(s for s in resolve_plan(state).steps if s.id == step_id)
    if current.status != StepStatus.READY:
        raise HTTPException(
            status_code=409,
            detail=f'"{current.title}" is {current.status.value}, not ready — can\'t be marked done yet.',
        )

    setattr(state, flag, True)
    return _resolve_with_recommendation(state)


@app.get("/personas/{persona_id}/artifacts/isss-email")
def get_isss_email(persona_id: str) -> dict:
    state = _get_persona(persona_id)  # 404s before the try — a bad id shouldn't read as an LLM failure

    # Gated the same way "mark done" is gated: drafting a letter-request email
    # only makes sense once the step is actually READY (or already DONE, for
    # a copy). Found live 2026-08-15 — without this, the model would draft a
    # confident email for a student who's actually blocked (e.g. no job offer
    # yet), silently fabricating "I have a job offer" / "check-in is done" to
    # fill the gap. The fix isn't a better prompt, it's not asking the model
    # to write something that isn't true yet.
    letter_step = next(s for s in resolve_plan(state).steps if s.id == StepId.REQUEST_ISSS_ELIGIBILITY_LETTER)
    if letter_step.status == StepStatus.BLOCKED:
        reasons = "; ".join(letter_step.blocked_reasons)
        raise HTTPException(status_code=409, detail=f"Can't draft this yet — {reasons}")

    try:
        return draft_isss_email(state)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Email drafting failed: {e}") from e


@app.get("/personas/{persona_id}/artifacts/calendar.ics")
def get_calendar(persona_id: str) -> Response:
    state = _get_persona(persona_id)
    plan = resolve_plan(state)  # no attach_explanations call — the ICS artifact stays fully
    # deterministic end-to-end, doesn't need or wait on an LLM round trip.
    return Response(
        content=build_ics(plan),
        media_type="text/calendar",
        headers={"Content-Disposition": f"attachment; filename={persona_id}-deadlines.ics"},
    )


@app.get("/document-types")
def get_document_types() -> dict[str, str]:
    return docstore.DOCUMENT_TYPES


@app.get("/personas/{persona_id}/documents")
def list_documents(persona_id: str) -> list[dict]:
    _get_persona(persona_id)
    return [d.to_dict() for d in docstore.list_documents(persona_id)]


@app.post("/personas/{persona_id}/documents")
async def upload_document(persona_id: str, doc_type: str = Form(...), file: UploadFile = File(...)) -> dict:
    _get_persona(persona_id)
    content = await file.read()
    try:
        meta = docstore.save_document(persona_id, doc_type, file.filename or "upload", content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return meta.to_dict()


@app.get("/personas/{persona_id}/documents/{doc_id}/file")
def get_document_file(persona_id: str, doc_id: str) -> FileResponse:
    _get_persona(persona_id)
    path = docstore.get_document_path(persona_id, doc_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(path)
