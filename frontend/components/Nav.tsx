"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useApp } from "@/lib/AppContext";
import AccountSwitcher from "./AccountSwitcher";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/tracker", label: "Tracker" },
  { href: "/faqs", label: "FAQs" },
  { href: "/docs", label: "Docs" },
];

export default function Nav() {
  const pathname = usePathname();
  const { personas, activeId, setActiveId } = useApp();

  return (
    <header className="border-b border-blue-100 bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-2xl flex-wrap items-center justify-between gap-3 px-6 py-4">
        <div className="flex flex-wrap items-center gap-4">
          <Link href="/" className="flex items-baseline gap-2">
            <span className="text-lg font-semibold text-slate-900">FinanceOne</span>
            <span className="hidden text-xs text-slate-400 sm:inline">all things finance in your new home</span>
          </Link>
          <nav className="flex flex-wrap gap-1">
            {LINKS.map((l) => {
              const active = pathname === l.href;
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
                    active ? "bg-blue-700 text-white" : "text-slate-600 hover:bg-blue-50"
                  }`}
                >
                  {l.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {personas.length > 0 && <AccountSwitcher personas={personas} activeId={activeId} onChange={setActiveId} />}
      </div>
    </header>
  );
}
