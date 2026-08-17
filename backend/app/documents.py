"""Phase 5b: a lightweight local document store — students upload their I-20,
job offer letter, ISSS eligibility letter, etc. and can see what they've
already uploaded.

Deliberately NOT wired into the resolver: uploading a document never changes
any step's status. That would be a genuinely useful feature (e.g. an
uploaded I-20 could satisfy a resolver precondition) but it's a real change
to the deterministic core's inputs, not a UI-layer add — worth a proper
design pass later, not something to bolt on under time pressure. Noted in
NOT-DOING.

Storage: plain local disk under DATA_DIR, one folder per persona (gitignored
— see .gitignore). No cloud storage, no virus scanning, no MIME sniffing
beyond an extension allow-list — proportionate to a hackathon demo, not a
real document vault.

2026-08-15: also seeds mock official documents (admission letter, job offer
letter) a student would realistically already have when they start using the
app, rather than making the demo upload them live. See ensure_seed_documents().
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data" / "uploads"
SEED_DIR = Path(__file__).resolve().parent / "data" / "seed_documents"

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".heic", ".doc", ".docx", ".html"}

# Single source of truth for doc types — the frontend's dropdown mirrors this
# list; keep them in sync by hand (small/static enough that a shared-schema
# round trip isn't worth the extra endpoint).
DOCUMENT_TYPES = {
    "admit_letter": "Admission letter",
    "i20": "I-20",
    "job_offer": "Job offer letter",
    "isss_letter": "ISSS eligibility letter",
    "passport": "Passport",
    "other": "Other",
}


@dataclass
class DocumentMeta:
    id: str
    filename: str
    doc_type: str
    size_bytes: int
    uploaded_at: str

    def to_dict(self) -> dict:
        return asdict(self)


def _persona_dir(persona_id: str) -> Path:
    d = DATA_DIR / persona_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_name(filename: str) -> str:
    # User-supplied and lands directly in a filesystem path — strip any path
    # components and anything outside a conservative allow-list.
    name = Path(filename).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "upload"


def save_document(persona_id: str, doc_type: str, filename: str, content: bytes) -> DocumentMeta:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext or '(none)'}")
    if doc_type not in DOCUMENT_TYPES:
        doc_type = "other"

    doc_id = uuid.uuid4().hex[:8]
    safe = _safe_name(filename)
    stored_name = f"{doc_id}__{doc_type}__{safe}"
    (_persona_dir(persona_id) / stored_name).write_bytes(content)

    return DocumentMeta(id=doc_id, filename=safe, doc_type=doc_type, size_bytes=len(content),
                         uploaded_at=datetime.now(timezone.utc).isoformat())


def list_documents(persona_id: str) -> list[DocumentMeta]:
    docs = []
    for path in sorted(_persona_dir(persona_id).iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not path.is_file():
            continue
        parts = path.name.split("__", 2)
        if len(parts) != 3:
            continue  # not one of ours — ignore rather than error on a stray file
        doc_id, doc_type, filename = parts
        stat = path.stat()
        docs.append(DocumentMeta(id=doc_id, filename=filename, doc_type=doc_type, size_bytes=stat.st_size,
                                  uploaded_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()))
    return docs


def get_document_path(persona_id: str, doc_id: str) -> Path | None:
    for path in _persona_dir(persona_id).iterdir():
        if path.name.startswith(f"{doc_id}__"):
            return path
    return None


def ensure_seed_documents() -> None:
    """Pre-populate each persona's document list with the mock official
    documents they'd realistically already have (admission letter; a job
    offer letter for Priya only, since Wei doesn't have one) — not something
    the demo has to fake-upload live. Layout: data/seed_documents/{persona_id}/{doc_type}.html.

    Idempotent — skips a persona/doc_type pair that's already present, so
    calling this again (e.g. on every server restart) never creates
    duplicates. Called once at import time in app/main.py.
    """
    if not SEED_DIR.exists():
        return
    for persona_dir in SEED_DIR.iterdir():
        if not persona_dir.is_dir():
            continue
        persona_id = persona_dir.name
        already_have = {d.doc_type for d in list_documents(persona_id)}
        for seed_file in persona_dir.iterdir():
            doc_type = seed_file.stem  # filename (minus extension) IS the doc_type by convention
            if doc_type in already_have:
                continue
            save_document(persona_id, doc_type, seed_file.name, seed_file.read_bytes())
