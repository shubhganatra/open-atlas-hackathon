"use client";

import { useState } from "react";
import { calendarUrl, fetchIsssEmail, type EmailDraft, type PersonaSummary, type ResolvedPlan } from "@/lib/api";
import { useApp } from "@/lib/AppContext";
import StepCard from "./StepCard";

const JOB_OFFER_LABEL: Record<string, string> = {
  none: "no job offer",
  on_campus: "on-campus job offer",
  off_campus_cpt_opt: "off-campus (CPT/OPT) job offer",
};

function displayName(id: string): string {
  return id.charAt(0).toUpperCase() + id.slice(1);
}

// The single active account's plan — this is the whole page's content now,
// not one of several columns. Renamed from PersonaColumn (2026-08-15): same
// component, different role, after cutting the side-by-side dashboard view.
export default function AccountPanel({
  persona,
  plan,
  error,
  loading,
}: {
  persona: PersonaSummary;
  plan: ResolvedPlan | null;
  error: string | null;
  loading: boolean;
}) {
  const { completeStep, completingStepId, completeError, explanationsLoading } = useApp();
  const [email, setEmail] = useState<EmailDraft | null>(null);
  const [draftingEmail, setDraftingEmail] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);

  // Switching accounts must never leave a stale artifact drawn under the new
  // account's name. Pure state reset, no external API touched — done during
  // render (react.dev's "Adjusting state when a prop changes"), not in an
  // effect that would exist solely to call setState.
  const [resetFor, setResetFor] = useState(persona.id);
  if (persona.id !== resetFor) {
    setResetFor(persona.id);
    setEmail(null);
    setEmailError(null);
  }

  async function handleDraftEmail() {
    setDraftingEmail(true);
    setEmailError(null);
    try {
      setEmail(await fetchIsssEmail(persona.id));
    } catch (e) {
      setEmailError(e instanceof Error ? e.message : "Failed to draft email");
    } finally {
      setDraftingEmail(false);
    }
  }

  return (
    <section className="rounded-2xl border border-blue-100 bg-white p-5 shadow-sm">
      <header className="mb-4">
        <h2 className="text-xl font-semibold text-slate-900">{displayName(persona.id)}&apos;s plan</h2>
        <p className="text-sm text-slate-500">
          {persona.university.replace("_", " ")} · {persona.visa_type.toUpperCase()} ·{" "}
          {JOB_OFFER_LABEL[persona.job_offer_type] ?? persona.job_offer_type}
        </p>
      </header>

      {error && (
        <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {loading && !plan && <p className="text-sm text-slate-400">Loading plan…</p>}

      {completeError && (
        <p className="mb-2 rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {completeError}
        </p>
      )}

      {plan && (
        <ul className="space-y-3">
          {plan.steps.map((step) => (
            <StepCard
              key={step.id}
              step={step}
              onComplete={completeStep}
              completing={completingStepId === step.id}
              explanationsLoading={explanationsLoading}
            />
          ))}
        </ul>
      )}

      <div className="mt-5 border-t border-blue-100 pt-4">
        <p className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">
          Prepared artifacts
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleDraftEmail}
            disabled={draftingEmail}
            className="rounded-full border border-blue-200 px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors hover:bg-blue-50 disabled:opacity-50"
          >
            {draftingEmail ? "Drafting…" : "Draft ISSS email (if you can't find a portal option)"}
          </button>
          <a
            href={calendarUrl(persona.id)}
            className="rounded-full border border-blue-200 px-3 py-1.5 text-sm font-medium text-slate-700 transition-colors hover:bg-blue-50"
          >
            Download calendar (.ics)
          </a>
        </div>

        {emailError && <p className="mt-2 text-sm text-red-600">{emailError}</p>}

        {email && (
          <div className="mt-3 rounded-xl border border-blue-100 bg-blue-50/40 p-3 text-sm">
            <p className="font-medium text-slate-900">Subject: {email.subject}</p>
            <p className="mt-2 whitespace-pre-wrap text-slate-600">{email.body}</p>
            <p className="mt-2 text-xs text-slate-400">
              Drafted for you to review and send yourself — nothing is sent automatically.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
