"use client";

import { type ReactNode } from "react";

interface BadgeProps {
  children: ReactNode;
  variant?: "default" | "success" | "warning" | "error" | "info";
  size?: "sm" | "md";
}

const variantStyles = {
  default: "border-slate-200/80 bg-white/70 text-slate-700",
  success: "border-emerald-200 bg-emerald-50/90 text-emerald-700",
  warning: "border-amber-200 bg-amber-50/90 text-amber-800",
  error: "border-rose-200 bg-rose-50/90 text-rose-700",
  info: "border-cyan-200 bg-cyan-50/90 text-cyan-700",
};

const sizeStyles = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
};

export function Badge({
  children,
  variant = "default",
  size = "md",
}: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border font-semibold ${variantStyles[variant]} ${sizeStyles[size]}`}
    >
      {children}
    </span>
  );
}

// Decision-specific badges
export function DecisionBadge({ decision }: { decision: string }) {
  const variants: Record<string, BadgeProps["variant"]> = {
    ALLOW: "success",
    DENY: "error",
    QUARANTINE: "warning",
  };
  return <Badge variant={variants[decision] || "default"}>{decision}</Badge>;
}

export function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, BadgeProps["variant"]> = {
    PENDING: "warning",
    APPROVED: "success",
    REJECTED: "error",
    EXPIRED: "default",
    healthy: "success",
    degraded: "warning",
    unhealthy: "error",
  };
  return <Badge variant={variants[status] || "default"}>{status}</Badge>;
}
