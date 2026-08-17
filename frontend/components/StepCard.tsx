import { Loader2 } from "lucide-react";
import type { PlanStep } from "@/lib/api";
import StatusBadge from "./StatusBadge";

// Card chrome by status, per DESIGN.md: READY is the one that should draw the
// eye (white + shadow), BLOCKED recedes (dashed, muted, no shadow) since it's
// not actionable right now — the amber "Blocked by" note below carries the
// attention instead of the card border.
const CARD_STYLE: Record<string, string> = {
  done: "border-emerald-200 bg-emerald-50",
  ready: "border-blue-200 bg-white shadow-sm",
  blocked: "border-dashed border-slate-200 bg-slate-50 opacity-75",
};

// Deliberately shows two distinct things, not one merged blurb: the resolver's
// raw reasons (deterministic, zero LLM involved) and the model's synthesized
// explanation (LLM-at-the-edges). Keeping them visually separate is the point
// — it's "deterministic core + LLM at the edges" made visible on screen, not
// just an implementation detail buried in the backend.
export default function StepCard({
  step,
  onComplete,
  completing,
  explanationsLoading,
}: {
  step: PlanStep;
  onComplete?: (stepId: string) => void;
  completing?: boolean;
  explanationsLoading?: boolean;
}) {
  return (
    <li className={`rounded-2xl border p-4 ${CARD_STYLE[step.status]}`}>
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-medium text-slate-900">{step.title}</h3>
        <StatusBadge status={step.status} />
      </div>

      {step.deadline && (
        <p className="mt-1 text-xs font-medium text-amber-700">
          Deadline: {step.deadline}
        </p>
      )}

      {step.blocked_reasons.length > 0 && (
        <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          <p className="font-medium">Blocked by:</p>
          <ul className="mt-1 list-inside list-disc">
            {step.blocked_reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {step.explanation ? (
        <p className="fade-in mt-2 text-sm leading-relaxed text-slate-600">{step.explanation}</p>
      ) : explanationsLoading ? (
        <p className="mt-2 flex items-center gap-1.5 text-sm text-slate-400">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Fetching details…
        </p>
      ) : (
        // A resolved plan with no explanation and nothing in flight isn't an
        // error — most often the backend gracefully degraded because the LLM
        // call failed (e.g. no API key). Status/reasons above are correct either way.
        <p className="mt-2 text-sm text-slate-400 italic">
          Explanation not available yet — status and reasons above are still accurate.
        </p>
      )}

      {step.link_url && (
        <a
          href={step.link_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-blue-700 hover:underline"
        >
          {step.link_label ?? "Take this action"} ↗
        </a>
      )}

      {step.status === "ready" && onComplete && (
        <div>
          <button
            onClick={() => onComplete(step.id)}
            disabled={completing}
            className="mt-3 rounded-full bg-blue-700 px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-blue-800 disabled:opacity-50"
          >
            {completing ? "Marking done…" : "Mark done"}
          </button>
        </div>
      )}
    </li>
  );
}
