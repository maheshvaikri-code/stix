'use client';

import { type ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  size?: 'sm' | 'md';
}

const variantStyles = {
  default: 'bg-gray-100 text-gray-800',
  success: 'bg-green-100 text-green-800',
  warning: 'bg-yellow-100 text-yellow-800',
  error: 'bg-red-100 text-red-800',
  info: 'bg-blue-100 text-blue-800',
};

const sizeStyles = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
};

export function Badge({ children, variant = 'default', size = 'md' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center font-medium rounded-full ${variantStyles[variant]} ${sizeStyles[size]}`}
    >
      {children}
    </span>
  );
}

// Decision-specific badges
export function DecisionBadge({ decision }: { decision: string }) {
  const variants: Record<string, BadgeProps['variant']> = {
    ALLOW: 'success',
    DENY: 'error',
    QUARANTINE: 'warning',
  };
  return <Badge variant={variants[decision] || 'default'}>{decision}</Badge>;
}

export function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, BadgeProps['variant']> = {
    PENDING: 'warning',
    APPROVED: 'success',
    REJECTED: 'error',
    EXPIRED: 'default',
    healthy: 'success',
    degraded: 'warning',
    unhealthy: 'error',
  };
  return <Badge variant={variants[status] || 'default'}>{status}</Badge>;
}
