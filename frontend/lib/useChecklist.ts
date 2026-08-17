"use client";

import { useEffect, useState } from "react";

export interface ChecklistItem {
  id: string;
  text: string;
  done: boolean;
}

function storageKey(personaId: string): string {
  return `copilot:checklist:${personaId}`;
}

// Client-side only, per persona — deliberately NOT sent to the backend and
// never touched by the resolver. These are personal reminders a student adds
// themselves (e.g. "buy a SIM card"), not steps in the deterministic plan;
// keeping them local avoids any confusion about which list is the source of
// truth for plan correctness. See DECISIONS.md, "Add a new task", 2026-08-15.
export function useChecklist(personaId: string | null) {
  const [items, setItems] = useState<ChecklistItem[]>([]);

  // Reading localStorage genuinely needs an Effect, not render-phase state
  // adjustment: it's a browser-only API that would crash during SSR if
  // touched at render time. This is exactly the "read an external store on a
  // dependency change" case Effects exist for, so the whole callback is
  // exempted from react-hooks/set-state-in-effect rather than fought around.
  /* eslint-disable react-hooks/set-state-in-effect -- localStorage is the external system being synchronized; see comment above. */
  useEffect(() => {
    if (!personaId) {
      setItems([]);
      return;
    }
    try {
      const raw = localStorage.getItem(storageKey(personaId));
      setItems(raw ? JSON.parse(raw) : []);
    } catch {
      setItems([]);
    }
  }, [personaId]);
  /* eslint-enable react-hooks/set-state-in-effect */

  function persist(next: ChecklistItem[]) {
    setItems(next);
    if (personaId) localStorage.setItem(storageKey(personaId), JSON.stringify(next));
  }

  function addItem(text: string) {
    if (!text.trim()) return;
    persist([...items, { id: crypto.randomUUID(), text: text.trim(), done: false }]);
  }

  function toggleItem(id: string) {
    persist(items.map((i) => (i.id === id ? { ...i, done: !i.done } : i)));
  }

  function removeItem(id: string) {
    persist(items.filter((i) => i.id !== id));
  }

  return { items, addItem, toggleItem, removeItem };
}
