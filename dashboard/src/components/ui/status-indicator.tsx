"use client";

interface StatusIndicatorProps {
  status: "healthy" | "degraded" | "unhealthy" | "unknown";
  showLabel?: boolean;
  size?: "sm" | "md";
}

const statusColors = {
  healthy: "bg-emerald-400 shadow-[0_0_16px_rgba(52,211,153,0.65)]",
  degraded: "bg-amber-400 shadow-[0_0_16px_rgba(251,191,36,0.65)]",
  unhealthy: "bg-rose-500 shadow-[0_0_16px_rgba(244,63,94,0.65)]",
  unknown: "bg-slate-400 shadow-[0_0_16px_rgba(148,163,184,0.5)]",
};

const statusLabels = {
  healthy: "Healthy",
  degraded: "Degraded",
  unhealthy: "Unhealthy",
  unknown: "Unknown",
};

const sizeStyles = {
  sm: "h-2 w-2",
  md: "h-3 w-3",
};

export function StatusIndicator({
  status,
  showLabel,
  size = "md",
}: StatusIndicatorProps) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={`rounded-full ring-2 ring-white ${statusColors[status]} ${sizeStyles[size]}`}
      />
      {showLabel && (
        <span className="text-sm font-medium text-slate-600">
          {statusLabels[status]}
        </span>
      )}
    </div>
  );
}

export function PulsingIndicator({
  status,
}: {
  status: "healthy" | "degraded" | "unhealthy";
}) {
  return (
    <span className="relative flex h-3 w-3">
      <span
        className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${statusColors[status]}`}
      />
      <span
        className={`relative inline-flex h-3 w-3 rounded-full ring-2 ring-white ${statusColors[status]}`}
      />
    </span>
  );
}
