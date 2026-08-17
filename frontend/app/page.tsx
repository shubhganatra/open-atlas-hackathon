"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import ProgressRing from "@/components/ProgressRing";
import { useApp } from "@/lib/AppContext";
import { useChecklist } from "@/lib/useChecklist";

function displayName(id: string): string {
  return id.charAt(0).toUpperCase() + id.slice(1);
}

export default function Home() {
  const {
    activePersona,
    plan,
    planError,
    loadingPlan,
    personasError,
    recommendedStep,
    completeStep,
    completingStepId,
    completeError,
  } = useApp();
  const { items, addItem, toggleItem, removeItem } = useChecklist(activePersona?.id ?? null);
  const [showAddTask, setShowAddTask] = useState(false);
  const [taskText, setTaskText] = useState("");
  const [justCompleted, setJustCompleted] = useState<string | null>(null);

  const steps = plan?.steps ?? [];
  const doneCount = steps.filter((s) => s.status === "done").length;
  const total = steps.length;
  const pct = total > 0 ? Math.round((doneCount / total) * 100) : 0;

  const upcomingDeadline = [...steps]
    .filter((s) => s.deadline && s.status !== "done")
    .sort((a, b) => (a.deadline! < b.deadline! ? -1 : 1))[0];

  async function handleMarkDone(stepId: string, title: string) {
    await completeStep(stepId);
    setJustCompleted(title);
    window.setTimeout(() => setJustCompleted(null), 5000);
  }

  function handleAddTask(e: FormEvent) {
    e.preventDefault();
    addItem(taskText);
    setTaskText("");
    setShowAddTask(false);
  }

  return (
    <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-10">
      <h1 className="text-2xl font-semibold text-slate-900">
        Welcome back{activePersona ? `, ${displayName(activePersona.id)}` : ""} 👋
      </h1>
      <p className="mt-1 text-sm text-slate-500">
        Here&apos;s where your US financial setup stands today.
      </p>

      {(personasError || planError || completeError) && (
        <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">
          {personasError ?? planError ?? completeError}
        </p>
      )}

      {justCompleted && (
        <p className="mt-4 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          Nice! &ldquo;{justCompleted}&rdquo; is done.
          {recommendedStep && ` Next up: ${recommendedStep.title}.`}
        </p>
      )}

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        {/* Left column — the deterministic engine: progress, what's next, deadlines. */}
        <div className="space-y-4">
          <section className="rounded-2xl border border-blue-100 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-5">
              <ProgressRing value={doneCount} total={total} />
              <div>
                <p className="font-medium text-slate-900">
                  {loadingPlan
                    ? "Loading your plan…"
                    : total > 0
                      ? `${pct}% of your plan is done`
                      : "No plan loaded yet"}
                </p>
                <Link href="/tracker" className="text-sm font-medium text-blue-800 hover:underline">
                  View full tracker →
                </Link>
              </div>
            </div>
          </section>

          {recommendedStep && (
            <div className="rounded-2xl border border-blue-100 bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold tracking-wide text-blue-700 uppercase">Next up</p>
              <p className="mt-1 font-medium text-slate-900">{recommendedStep.title}</p>
              <p className="mt-1 text-sm text-slate-500">Ready to go — see the tracker for details.</p>
              <button
                onClick={() => handleMarkDone(recommendedStep.id, recommendedStep.title)}
                disabled={completingStepId === recommendedStep.id}
                className="mt-2 rounded-full bg-blue-700 px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-blue-800 disabled:opacity-50"
              >
                {completingStepId === recommendedStep.id ? "Marking done…" : "Mark done"}
              </button>
            </div>
          )}

          {upcomingDeadline && (
            <div className="rounded-2xl border border-blue-100 bg-white p-4 shadow-sm">
              <p className="text-xs font-semibold tracking-wide text-blue-700 uppercase">Upcoming deadline</p>
              <p className="mt-1 font-medium text-slate-900">{upcomingDeadline.title}</p>
              <p className="mt-1 text-sm text-slate-500">{upcomingDeadline.deadline}</p>
            </div>
          )}
        </div>

        {/* Right column — the sandbox: freeform personal reminders, explicitly
            not wired into the resolver, kept visually distinct from the plan. */}
        <section className="h-fit rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="font-medium text-slate-900">Your checklist</h2>
            <button
              onClick={() => setShowAddTask((v) => !v)}
              className="rounded-full bg-blue-700 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-blue-800"
            >
              + Add a new task
            </button>
          </div>

          {showAddTask && (
            <div className="mt-3 space-y-3">
              {recommendedStep && (
                <div className="flex items-center justify-between gap-3 rounded-xl border border-blue-200 bg-blue-50/60 px-3 py-2">
                  <div>
                    <p className="text-xs font-semibold tracking-wide text-blue-800 uppercase">
                      Suggested, based on your plan
                    </p>
                    <p className="text-sm font-medium text-slate-900">{recommendedStep.title}</p>
                  </div>
                  <button
                    onClick={() => handleMarkDone(recommendedStep.id, recommendedStep.title)}
                    disabled={completingStepId === recommendedStep.id}
                    className="shrink-0 rounded-full bg-blue-700 px-3 py-1 text-xs font-medium whitespace-nowrap text-white transition-colors hover:bg-blue-800 disabled:opacity-50"
                  >
                    {completingStepId === recommendedStep.id ? "Marking…" : "Mark done"}
                  </button>
                </div>
              )}

              <form onSubmit={handleAddTask} className="flex gap-2">
                <input
                  autoFocus
                  value={taskText}
                  onChange={(e) => setTaskText(e.target.value)}
                  placeholder="Or add your own reminder, e.g. Buy a SIM card"
                  className="flex-1 rounded-full border border-slate-300 px-4 py-1.5 text-sm"
                />
                <button
                  type="submit"
                  className="rounded-full bg-slate-900 px-4 py-1.5 text-sm font-medium text-white"
                >
                  Add
                </button>
              </form>
            </div>
          )}

          <p className="mt-2 text-xs text-slate-400">
            Personal reminders you add yourself — separate from your official plan.
          </p>

          {items.length > 0 && (
            <ul className="mt-3 space-y-1.5">
              {items.map((item) => (
                <li key={item.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={item.done}
                    onChange={() => toggleItem(item.id)}
                    className="accent-blue-700"
                  />
                  <span
                    className={item.done ? "flex-1 text-slate-400 line-through" : "flex-1 text-slate-700"}
                  >
                    {item.text}
                  </span>
                  <button
                    onClick={() => removeItem(item.id)}
                    className="text-slate-300 hover:text-red-500"
                    aria-label="Remove task"
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
