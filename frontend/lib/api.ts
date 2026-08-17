// Thin client for the FastAPI backend. No SWR/React Query — a couple of
// fetches on load doesn't need a caching library, and pulling one in would
// just be scope for scope's sake this close to the wire.

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export type StepStatusValue = "done" | "ready" | "blocked";

export interface PlanStep {
  id: string;
  title: string;
  description: string;
  status: StepStatusValue;
  blocked_reasons: string[];
  deadline: string | null;
  link_label: string | null;
  link_url: string | null;
  explanation: string | null;
}

export interface ResolvedPlan {
  student_id: string;
  steps: PlanStep[];
  recommended_step_id: string | null;
}

export interface PersonaSummary {
  id: string;
  university: string;
  visa_type: string;
  job_offer_type: string;
}

export interface EmailDraft {
  subject: string;
  body: string;
}

export interface DocumentMeta {
  id: string;
  filename: string;
  doc_type: string;
  size_bytes: number;
  uploaded_at: string;
}

async function asJson<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) {
    // FastAPI's error shape is {"detail": "..."} — surface that when present
    // (e.g. "Can't draft this yet — no job offer on file") instead of just a
    // status code, since the detail is usually the actually useful part.
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `${what} failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function fetchPersonas(): Promise<PersonaSummary[]> {
  return fetch(`${API_BASE}/personas`).then((r) => asJson(r, "Loading personas"));
}

// Fast path: deterministic only, no LLM wait — see backend/app/main.py's
// get_plan. This is what the Tracker renders headers/badges/links from
// immediately; explanation text arrives separately via fetchExplanations.
export function fetchPlan(personaId: string): Promise<ResolvedPlan> {
  return fetch(`${API_BASE}/personas/${personaId}/plan`).then((r) => asJson(r, `Loading ${personaId}'s plan`));
}

// Slow path: step_id -> explanation text (or null if generation failed).
// Fetched separately from fetchPlan so the deterministic plan never waits on
// the LLM round trip — see DESIGN.md "Async Load".
export function fetchExplanations(personaId: string): Promise<Record<string, string | null>> {
  return fetch(`${API_BASE}/personas/${personaId}/explanations`).then((r) =>
    asJson(r, `Loading ${personaId}'s explanations`)
  );
}

// Deterministic-only response (no explanation text) — the caller re-fetches
// via fetchExplanations afterward for LLM-explained text when available.
// See backend/app/main.py's complete_step for why.
export function completeStep(personaId: string, stepId: string): Promise<ResolvedPlan> {
  return fetch(`${API_BASE}/personas/${personaId}/steps/${stepId}/complete`, { method: "POST" }).then((r) =>
    asJson(r, "Marking step done")
  );
}

export function fetchIsssEmail(personaId: string): Promise<EmailDraft> {
  return fetch(`${API_BASE}/personas/${personaId}/artifacts/isss-email`).then((r) =>
    asJson(r, "Drafting ISSS email")
  );
}

export function calendarUrl(personaId: string): string {
  return `${API_BASE}/personas/${personaId}/artifacts/calendar.ics`;
}

// Kept in sync by hand with backend/app/documents.py's DOCUMENT_TYPES — small
// and static enough that a shared-schema round trip isn't worth the extra
// fetch on every page load.
export const DOCUMENT_TYPES: Record<string, string> = {
  admit_letter: "Admission letter",
  i20: "I-20",
  job_offer: "Job offer letter",
  isss_letter: "ISSS eligibility letter",
  passport: "Passport",
  other: "Other",
};

export function fetchDocuments(personaId: string): Promise<DocumentMeta[]> {
  return fetch(`${API_BASE}/personas/${personaId}/documents`).then((r) => asJson(r, "Loading documents"));
}

export async function uploadDocument(personaId: string, docType: string, file: File): Promise<DocumentMeta> {
  const form = new FormData();
  form.append("doc_type", docType);
  form.append("file", file);
  const res = await fetch(`${API_BASE}/personas/${personaId}/documents`, { method: "POST", body: form });
  return asJson(res, "Uploading document");
}

export function documentFileUrl(personaId: string, docId: string): string {
  return `${API_BASE}/personas/${personaId}/documents/${docId}/file`;
}
