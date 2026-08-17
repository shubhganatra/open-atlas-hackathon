"use client";

import AccountPanel from "@/components/AccountPanel";
import { useApp } from "@/lib/AppContext";

export default function TrackerPage() {
  const { activePersona, plan, planError, loadingPlan, personasError } = useApp();

  return (
    <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-10">
      <h1 className="text-2xl font-semibold text-slate-900">Tracker</h1>
      <p className="mt-1 mb-6 text-sm text-slate-500">
        Your full, step-by-step plan — statuses and deadlines update as you go.
      </p>

      {personasError && (
        <p className="mb-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">
          Couldn&apos;t reach the backend: {personasError}. Is it running on port 8000?
        </p>
      )}

      {activePersona ? (
        <AccountPanel persona={activePersona} plan={plan} error={planError} loading={loadingPlan} />
      ) : (
        !personasError && <p className="text-sm text-slate-400">Loading…</p>
      )}
    </main>
  );
}
