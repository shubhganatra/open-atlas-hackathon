"use client";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { PersonaSummary } from "@/lib/api";

const JOB_OFFER_LABEL: Record<string, string> = {
  none: "no job offer",
  on_campus: "on-campus job offer",
  off_campus_cpt_opt: "off-campus (CPT/OPT) job offer",
};

function displayName(id: string): string {
  return id.charAt(0).toUpperCase() + id.slice(1);
}

// Not real auth — a dev-facing "which demo account am I" selector standing in
// for login. Deliberately still framed as "signed in as", not "viewing", so
// the single-account product experience (you see your own plan, not a
// dashboard of everyone's) reads correctly even though the switch itself is
// a demo convenience. See DECISIONS.md, 2026-08-15.
export default function AccountSwitcher({
  personas,
  activeId,
  onChange,
}: {
  personas: PersonaSummary[];
  activeId: string | null;
  onChange: (id: string) => void;
}) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-600">
      <span className="text-slate-400">Signed in as</span>
      <Select value={activeId ?? undefined} onValueChange={(value) => value && onChange(value)}>
        <SelectTrigger className="rounded-full border-blue-200 bg-white font-medium text-slate-900">
          <SelectValue>
            {(value: string | null) => {
              const p = personas.find((p) => p.id === value);
              return p ? `${displayName(p.id)} — ${JOB_OFFER_LABEL[p.job_offer_type] ?? p.job_offer_type}` : "Choose an account";
            }}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {personas.map((p) => (
            <SelectItem key={p.id} value={p.id}>
              {displayName(p.id)} — {JOB_OFFER_LABEL[p.job_offer_type] ?? p.job_offer_type}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
