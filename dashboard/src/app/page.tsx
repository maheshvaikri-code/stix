'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Shield,
  FileText,
  Activity,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Database,
  TrendingUp,
  TrendingDown,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { useDashboardStats, useDecisionTimeSeries, useAllServicesHealth, useApprovals } from '@/lib/hooks';
import { Card, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge, DecisionBadge, StatusBadge } from '@/components/ui/badge';
import { StatusIndicator, PulsingIndicator } from '@/components/ui/status-indicator';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

// =============================================================================
// DASHBOARD PAGE
// =============================================================================

export default function DashboardPage() {
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('24h');

  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useDashboardStats();
  const { data: timeSeries, isLoading: timeSeriesLoading } = useDecisionTimeSeries(timeRange);
  const { data: health, refetch: refetchHealth } = useAllServicesHealth();
  const { data: pendingApprovals } = useApprovals({ status: 'PENDING', page_size: 5 });

  const handleRefresh = () => {
    refetchStats();
    refetchHealth();
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            Real-time overview of STIX authorization activity
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-gray-100 rounded-lg p-1">
            {(['24h', '7d', '30d'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1 text-sm rounded ${
                  timeRange === range
                    ? 'bg-white shadow text-gray-900'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
          <Button variant="secondary" onClick={handleRefresh}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Service Status */}
      <div className="grid grid-cols-4 gap-4">
        {['enforcer', 'policy', 'evidence', 'approvals'].map((service) => {
          const serviceHealth = health?.[service as keyof typeof health];
          const status = serviceHealth?.status || 'unknown';
          const icons = {
            enforcer: Shield,
            policy: FileText,
            evidence: Database,
            approvals: CheckCircle,
          };
          const Icon = icons[service as keyof typeof icons];

          return (
            <Card key={service} className="!p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-gray-100 rounded-lg">
                    <Icon className="h-5 w-5 text-gray-600" />
                  </div>
                  <div>
                    <p className="font-medium capitalize">{service}</p>
                    <p className="text-xs text-gray-500">
                      {serviceHealth?.version || 'Unknown'}
                    </p>
                  </div>
                </div>
                <PulsingIndicator status={status === 'unknown' ? 'unhealthy' : status} />
              </div>
            </Card>
          );
        })}
      </div>

      {/* Stats Cards */}
      {statsLoading ? (
        <div className="py-8">
          <LoadingSpinner />
        </div>
      ) : stats && (
        <div className="grid grid-cols-4 gap-4">
          <StatsCard
            title="Total Decisions"
            value={stats.decisions.total}
            icon={<Activity className="h-6 w-6" />}
            change={stats.decisions.trend}
            changeLabel={`${stats.decisions.trend >= 0 ? '+' : ''}${stats.decisions.trend}% from previous`}
          />
          <StatsCard
            title="Allowed"
            value={stats.decisions.allowed}
            icon={<CheckCircle className="h-6 w-6" />}
            iconColor="text-green-600"
            iconBg="bg-green-50"
            subtitle={`${((stats.decisions.allowed / stats.decisions.total) * 100).toFixed(1)}% of total`}
          />
          <StatsCard
            title="Denied"
            value={stats.decisions.denied}
            icon={<XCircle className="h-6 w-6" />}
            iconColor="text-red-600"
            iconBg="bg-red-50"
            subtitle={`${((stats.decisions.denied / stats.decisions.total) * 100).toFixed(1)}% of total`}
          />
          <StatsCard
            title="Pending Approvals"
            value={stats.approvals.pending}
            icon={<Clock className="h-6 w-6" />}
            iconColor="text-yellow-600"
            iconBg="bg-yellow-50"
            alert={stats.approvals.pending > 0}
          />
        </div>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-6">
        {/* Decision Distribution */}
        <Card className="col-span-2">
          <CardHeader
            title="Decision Distribution"
            description={`Last ${timeRange}`}
          />
          {stats && <DecisionChart stats={stats} />}
        </Card>

        {/* Policy Summary */}
        <Card>
          <CardHeader
            title="Policies"
            action={
              <Link href="/policies" className="text-sm text-blue-600 hover:text-blue-800">
                View all
              </Link>
            }
          />
          {stats && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Active Policies</span>
                <span className="text-2xl font-bold">{stats.policies.active}</span>
              </div>
              <div className="text-sm text-gray-500">
                {stats.policies.total} total policies
              </div>
              <div className="space-y-2">
                {Object.entries(stats.policies.by_regulation).slice(0, 5).map(([reg, count]) => (
                  <div key={reg} className="flex items-center justify-between text-sm">
                    <Badge variant="info" size="sm">{reg}</Badge>
                    <span>{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* Bottom Section */}
      <div className="grid grid-cols-2 gap-6">
        {/* Pending Approvals */}
        <Card>
          <CardHeader
            title="Pending Approvals"
            action={
              <Link href="/approvals" className="text-sm text-blue-600 hover:text-blue-800">
                View all
              </Link>
            }
          />
          {pendingApprovals?.data.length ? (
            <div className="space-y-3">
              {pendingApprovals.data.map((approval) => (
                <div
                  key={approval.request_id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div>
                    <p className="font-medium text-sm">{approval.action}</p>
                    <p className="text-xs text-gray-500">
                      {approval.actor_id} | {approval.resource_type}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">
                      {formatTimeAgo(approval.created_at)}
                    </span>
                    <Link
                      href="/approvals"
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <CheckCircle className="h-12 w-12 mx-auto mb-2 text-green-500" />
              <p>No pending approvals</p>
            </div>
          )}
        </Card>

        {/* Evidence Summary */}
        <Card>
          <CardHeader
            title="Evidence Chain"
            action={
              <Link href="/evidence" className="text-sm text-blue-600 hover:text-blue-800">
                View details
              </Link>
            }
          />
          {stats && (
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <div
                  className={`p-3 rounded-lg ${
                    stats.evidence.chain_valid ? 'bg-green-50' : 'bg-red-50'
                  }`}
                >
                  {stats.evidence.chain_valid ? (
                    <CheckCircle className="h-6 w-6 text-green-600" />
                  ) : (
                    <AlertTriangle className="h-6 w-6 text-red-600" />
                  )}
                </div>
                <div>
                  <p className="font-medium">
                    Chain {stats.evidence.chain_valid ? 'Valid' : 'Invalid'}
                  </p>
                  <p className="text-sm text-gray-500">
                    Last verified: {formatTimeAgo(stats.evidence.last_verified)}
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <p className="text-sm text-gray-500">Total Records</p>
                  <p className="text-xl font-bold">
                    {stats.evidence.total_records.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Today</p>
                  <p className="text-xl font-bold">
                    {stats.evidence.today.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

// =============================================================================
// COMPONENTS
// =============================================================================

function StatsCard({
  title,
  value,
  icon,
  iconColor = 'text-blue-600',
  iconBg = 'bg-blue-50',
  change,
  changeLabel,
  subtitle,
  alert,
}: {
  title: string;
  value: number;
  icon: React.ReactNode;
  iconColor?: string;
  iconBg?: string;
  change?: number;
  changeLabel?: string;
  subtitle?: string;
  alert?: boolean;
}) {
  return (
    <Card className={alert ? 'border-yellow-300 bg-yellow-50' : ''}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold mt-1">{value.toLocaleString()}</p>
          {change !== undefined && (
            <p
              className={`text-sm mt-1 flex items-center gap-1 ${
                change >= 0 ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {change >= 0 ? (
                <TrendingUp className="h-3 w-3" />
              ) : (
                <TrendingDown className="h-3 w-3" />
              )}
              {changeLabel}
            </p>
          )}
          {subtitle && (
            <p className="text-xs text-gray-400 mt-1">{subtitle}</p>
          )}
        </div>
        <div className={`p-3 rounded-lg ${iconBg} ${iconColor}`}>{icon}</div>
      </div>
    </Card>
  );
}

function DecisionChart({ stats }: { stats: { decisions: { total: number; allowed: number; denied: number; quarantined: number } } }) {
  const total = stats.decisions.total;
  const allowedPercent = (stats.decisions.allowed / total) * 100;
  const deniedPercent = (stats.decisions.denied / total) * 100;
  const quarantinedPercent = (stats.decisions.quarantined / total) * 100;

  return (
    <div className="space-y-4">
      {/* Bar Chart */}
      <div className="h-4 flex rounded-full overflow-hidden">
        <div
          className="bg-green-500"
          style={{ width: `${allowedPercent}%` }}
          title={`Allowed: ${allowedPercent.toFixed(1)}%`}
        />
        <div
          className="bg-red-500"
          style={{ width: `${deniedPercent}%` }}
          title={`Denied: ${deniedPercent.toFixed(1)}%`}
        />
        <div
          className="bg-yellow-500"
          style={{ width: `${quarantinedPercent}%` }}
          title={`Quarantined: ${quarantinedPercent.toFixed(1)}%`}
        />
      </div>

      {/* Legend */}
      <div className="flex items-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span>Allowed ({allowedPercent.toFixed(1)}%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <span>Denied ({deniedPercent.toFixed(1)}%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-yellow-500" />
          <span>Quarantined ({quarantinedPercent.toFixed(1)}%)</span>
        </div>
      </div>

      {/* Details */}
      <div className="grid grid-cols-3 gap-4 pt-4 border-t">
        <div className="text-center">
          <p className="text-2xl font-bold text-green-600">
            {stats.decisions.allowed.toLocaleString()}
          </p>
          <p className="text-xs text-gray-500">Allowed</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-red-600">
            {stats.decisions.denied.toLocaleString()}
          </p>
          <p className="text-xs text-gray-500">Denied</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-yellow-600">
            {stats.decisions.quarantined.toLocaleString()}
          </p>
          <p className="text-xs text-gray-500">Quarantined</p>
        </div>
      </div>
    </div>
  );
}

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}
