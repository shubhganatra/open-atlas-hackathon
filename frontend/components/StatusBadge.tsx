import type { StepStatusValue } from "@/lib/api";

// Colors per DESIGN.md "Status Indicators" — blocked reads as muted/inactive
// (slate), not alarming; the amber "Blocked by" note on the card carries the
// attention instead. See StepCard.
const STYLES: Record<StepStatusValue, string> = {
  done: "bg-emerald-50 text-emerald-700",
  ready: "bg-blue-50 text-blue-700",
  blocked: "bg-slate-100 text-slate-500",
};

const LABELS: Record<StepStatusValue, string> = {
  done: "Done",
  ready: "Ready",
  blocked: "Blocked",
};

export default function StatusBadge({ status }: { status: StepStatusValue }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[status]}`}
    >
      {LABELS[status]}
    </span>
  );
}
