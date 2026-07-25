"use client";

import { type ReactNode } from "react";
import { InboxIcon } from "lucide-react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="mb-4 rounded-3xl border border-slate-200/70 bg-white/80 p-4 text-slate-400 shadow-lg shadow-slate-200/60">
        {icon || <InboxIcon className="h-12 w-12" />}
      </div>
      <h3 className="mb-1 text-lg font-semibold tracking-tight text-slate-950">
        {title}
      </h3>
      {description && (
        <p className="mb-4 max-w-md text-sm leading-6 text-slate-500">
          {description}
        </p>
      )}
      {action && <div>{action}</div>}
    </div>
  );
}
