"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import {
  completeStep as apiCompleteStep,
  fetchExplanations,
  fetchPersonas,
  fetchPlan,
  type PersonaSummary,
  type PlanStep,
  type ResolvedPlan,
} from "@/lib/api";

// Lifted out of page.tsx (2026-08-15) once the app grew multiple routes
// (Home / Tracker / FAQs / Docs) — "signed in as X" has to be one piece of
// state shared across all of them, not re-fetched independently per page.
interface AppContextValue {
  personas: PersonaSummary[];
  personasError: string | null;
  activeId: string | null;
  setActiveId: (id: string) => void;
  activePersona: PersonaSummary | null;
  plan: ResolvedPlan | null;
  planError: string | null;
  loadingPlan: boolean;
  explanationsLoading: boolean;
  recommendedStep: PlanStep | null;
  completeStep: (stepId: string) => Promise<void>;
  completingStepId: string | null;
  completeError: string | null;
}

const AppContext = createContext<AppContextValue | null>(null);

// Merge explanation text into an existing plan's steps without touching
// anything else (status/reasons/links are already correct and settled by the
// time this runs — this only ever fills in the one field the slow LLM path
// owns). Shared by the initial load and by completeStep's refresh.
function mergeExplanations(plan: ResolvedPlan, explanations: Record<string, string | null>): ResolvedPlan {
  return {
    ...plan,
    steps: plan.steps.map((s) => ({ ...s, explanation: explanations[s.id] ?? s.explanation })),
  };
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [personas, setPersonas] = useState<PersonaSummary[]>([]);
  const [personasError, setPersonasError] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [plan, setPlan] = useState<ResolvedPlan | null>(null);
  const [planError, setPlanError] = useState<string | null>(null);
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [explanationsLoading, setExplanationsLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchPersonas()
      .then((list) => {
        if (cancelled) return;
        setPersonas(list);
        if (list.length > 0) setActiveId(list[0].id);
      })
      .catch((e) => {
        if (!cancelled) setPersonasError(e instanceof Error ? e.message : "Failed to load accounts");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Reset is pure state (no external API touched) — safe and correct to do
  // during render rather than in an effect, per react.dev's "Adjusting state
  // when a prop changes". This is what guarantees switching accounts never
  // leaves the previous plan on screen under the new label while a fresh
  // fetch is still in flight.
  const [handledId, setHandledId] = useState<string | null | undefined>(undefined);
  if (activeId !== handledId) {
    setHandledId(activeId);
    setPlan(null);
    setPlanError(null);
    setLoadingPlan(activeId !== null);
    setExplanationsLoading(false);
  }

  useEffect(() => {
    if (!activeId) return;
    let cancelled = false;
    // Phase 1: fast deterministic plan — statuses, reasons, links, the
    // recommendation. Renders the whole Tracker immediately.
    fetchPlan(activeId)
      .then((p) => {
        if (cancelled) return;
        setPlan(p);
        setLoadingPlan(false);
        // Phase 2: slow LLM explanations, fetched separately and merged in
        // once they land — see DESIGN.md "Async Load".
        setExplanationsLoading(true);
        fetchExplanations(activeId)
          .then((explanations) => {
            if (cancelled) return;
            setPlan((prev) => (prev ? mergeExplanations(prev, explanations) : prev));
          })
          .catch(() => {
            // Explanations staying null is already a handled UI state (see
            // StepCard) — no need to surface a separate error for this.
          })
          .finally(() => {
            if (!cancelled) setExplanationsLoading(false);
          });
      })
      .catch((e) => {
        if (cancelled) return;
        setPlanError(e instanceof Error ? e.message : "Failed to load plan");
        setLoadingPlan(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeId]);

  const activePersona = personas.find((p) => p.id === activeId) ?? null;
  const recommendedStep = plan?.steps.find((s) => s.id === plan.recommended_step_id) ?? null;

  const [completingStepId, setCompletingStepId] = useState<string | null>(null);
  const [completeError, setCompleteError] = useState<string | null>(null);

  async function completeStep(stepId: string) {
    if (!activeId) return;
    setCompletingStepId(stepId);
    setCompleteError(null);
    try {
      // Deterministic response — reliable, correct statuses/recommendation
      // with zero LLM dependency. Applied immediately so "mark done -> see
      // what's next" always works, key or no key.
      const deterministic = await apiCompleteStep(activeId, stepId);
      setPlan(deterministic);
      setPlanError(null);
      // Best-effort enrichment with LLM explanation text; a failure here must
      // never undo the completion that already succeeded above.
      setExplanationsLoading(true);
      fetchExplanations(activeId)
        .then((explanations) => {
          setPlan((prev) => (prev ? mergeExplanations(prev, explanations) : prev));
        })
        .catch(() => {})
        .finally(() => setExplanationsLoading(false));
    } catch (e) {
      setCompleteError(e instanceof Error ? e.message : "Failed to mark step done");
    } finally {
      setCompletingStepId(null);
    }
  }

  return (
    <AppContext.Provider
      value={{
        personas,
        personasError,
        activeId,
        setActiveId,
        activePersona,
        plan,
        planError,
        loadingPlan,
        explanationsLoading,
        recommendedStep,
        completeStep,
        completingStepId,
        completeError,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within <AppProvider>");
  return ctx;
}
