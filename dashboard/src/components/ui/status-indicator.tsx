'use client';

interface StatusIndicatorProps {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  showLabel?: boolean;
  size?: 'sm' | 'md';
}

const statusColors = {
  healthy: 'bg-green-500',
  degraded: 'bg-yellow-500',
  unhealthy: 'bg-red-500',
  unknown: 'bg-gray-400',
};

const statusLabels = {
  healthy: 'Healthy',
  degraded: 'Degraded',
  unhealthy: 'Unhealthy',
  unknown: 'Unknown',
};

const sizeStyles = {
  sm: 'h-2 w-2',
  md: 'h-3 w-3',
};

export function StatusIndicator({
  status,
  showLabel,
  size = 'md',
}: StatusIndicatorProps) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={`rounded-full ${statusColors[status]} ${sizeStyles[size]}`}
      />
      {showLabel && (
        <span className="text-sm text-gray-600">{statusLabels[status]}</span>
      )}
    </div>
  );
}

export function PulsingIndicator({ status }: { status: 'healthy' | 'degraded' | 'unhealthy' }) {
  return (
    <span className="relative flex h-3 w-3">
      <span
        className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${statusColors[status]}`}
      />
      <span
        className={`relative inline-flex rounded-full h-3 w-3 ${statusColors[status]}`}
      />
    </span>
  );
}
