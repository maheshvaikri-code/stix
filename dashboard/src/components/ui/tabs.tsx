"use client";

import { type ReactNode } from "react";

interface TabsProps {
  tabs: { id: string; label: string; icon?: ReactNode }[];
  activeTab: string;
  onChange: (tabId: string) => void;
}

export function Tabs({ tabs, activeTab, onChange }: TabsProps) {
  return (
    <div className="rounded-3xl border border-white/70 bg-white/70 p-1 shadow-lg shadow-slate-200/60 backdrop-blur-xl">
      <nav className="flex flex-wrap gap-1" aria-label="Tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`
              flex items-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold transition-all
              ${
                activeTab === tab.id
                  ? "bg-slate-950 text-white shadow-lg shadow-slate-900/15"
                  : "text-slate-500 hover:bg-white/80 hover:text-slate-950"
              }
            `}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </nav>
    </div>
  );
}

export function TabPanel({
  children,
  active,
}: {
  children: ReactNode;
  active: boolean;
}) {
  if (!active) return null;
  return <div className="pt-6">{children}</div>;
}
