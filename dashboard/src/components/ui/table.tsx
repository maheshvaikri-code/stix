"use client";

import { type ReactNode } from "react";

interface TableProps {
  children: ReactNode;
  className?: string;
}

export function Table({ children, className = "" }: TableProps) {
  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="min-w-full divide-y divide-slate-200/70">
        {children}
      </table>
    </div>
  );
}

export function TableHead({ children }: { children: ReactNode }) {
  return <thead className="bg-slate-950/[0.03]">{children}</thead>;
}

export function TableBody({ children }: { children: ReactNode }) {
  return (
    <tbody className="divide-y divide-slate-200/70 bg-white/[0.58]">
      {children}
    </tbody>
  );
}

export function TableRow({
  children,
  onClick,
  clickable,
}: {
  children: ReactNode;
  onClick?: () => void;
  clickable?: boolean;
}) {
  return (
    <tr
      onClick={onClick}
      className={
        clickable
          ? "cursor-pointer transition-colors hover:bg-cyan-50/50"
          : "transition-colors"
      }
    >
      {children}
    </tr>
  );
}

export function TableHeader({
  children,
  className = "",
  sortable,
  sorted,
  onSort,
}: {
  children: ReactNode;
  className?: string;
  sortable?: boolean;
  sorted?: "asc" | "desc" | null;
  onSort?: () => void;
}) {
  return (
    <th
      scope="col"
      className={`
        px-6 py-3 text-left text-xs font-bold text-slate-500 uppercase tracking-[0.16em]
        ${sortable ? "cursor-pointer hover:bg-slate-100/70" : ""}
        ${className}
      `}
      onClick={sortable ? onSort : undefined}
    >
      <div className="flex items-center gap-1">
        {children}
        {sortable && (
          <span className="text-gray-400">
            {sorted === "asc" && "↑"}
            {sorted === "desc" && "↓"}
            {!sorted && "↕"}
          </span>
        )}
      </div>
    </th>
  );
}

export function TableCell({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <td
      className={`px-6 py-4 whitespace-nowrap text-sm text-slate-700 ${className}`}
    >
      {children}
    </td>
  );
}
