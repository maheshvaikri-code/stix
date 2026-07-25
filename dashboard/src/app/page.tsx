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
  Leaf,
  Network,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
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
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {['enforcer', 'policy', 'evidence', 'approvals', 'fabric'].map((service) => {
          const serviceHealth = health?.[service as keyof typeof health];
          const status = serviceHealth?.status || 'unknown';
          const icons = {
            enforcer: Shield,
            policy: FileText,
            evidence: Database,
            approvals: CheckCircle,
            fabric: Network,
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

      {/* Decision Timeline (Recharts) */}
      <Card>
        <CardHeader
          title="Decision Timeline"
          description={`Authorization decisions over the last ${timeRange}`}
        />
        <div className="h-72 px-2">
          {timeSeriesLoading ? (
            <div className="flex items-center justify-center h-full">
              <LoadingSpinner />
            </div>
          ) : timeSeries && timeSeries.allowed?.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mergeTimeSeries(timeSeries)} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <defs>
                  <linearGradient id="colorAllowed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorDenied" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorQuarantined" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#eab308" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#eab308" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis
                  dataKey="timestamp"
                  tick={{ fontSize: 11, fill: '#94a3b8' }}
                  tickFormatter={(v: string) => {
                    const d = new Date(v);
                    return timeRange === '24h'
                      ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                      : d.toLocaleDateString([], { month: 'short', day: 'numeric' });
                  }}
                />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#f8fafc',
                    fontSize: '12px',
                  }}
                  labelFormatter={(v: string) => new Date(v).toLocaleString()}
                />
                <Legend
                  wrapperStyle={{ fontSize: '12px' }}
                  iconType="circle"
                />
                <Area
                  type="monotone"
                  dataKey="allowed"
                  name="Allowed"
                  stroke="#22c55e"
                  strokeWidth={2}
                  fill="url(#colorAllowed)"
                  stackId="1"
                />
                <Area
                  type="monotone"
                  dataKey="denied"
                  name="Denied"
                  stroke="#ef4444"
                  strokeWidth={2}
                  fill="url(#colorDenied)"
                  stackId="1"
                />
                <Area
                  type="monotone"
                  dataKey="quarantined"
                  name="Quarantined"
                  stroke="#eab308"
                  strokeWidth={2}
                  fill="url(#colorQuarantined)"
                  stackId="1"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">
              No time series data available
            </div>
          )}
        </div>
      </Card>

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

      {/* Sustainability Metrics (Green Agent Prize) */}
      <Card className="border-green-200 bg-gradient-to-r from-green-50 to-emerald-50">
        <CardHeader
          title="Sustainability Metrics"
          description="AI compute savings from local policy evaluation vs. LLM-based compliance checking"
        />
        {stats && (
          <div className="grid grid-cols-4 gap-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-green-700">
                {Math.round(((stats.decisions.total - (stats.decisions.quarantined || 0)) / Math.max(stats.decisions.total, 1)) * 100)}%
              </p>
              <p className="text-sm text-green-600 mt-1">Decisions Without LLM</p>
              <p className="text-xs text-gray-500 mt-1">
                Local policy engine evaluation
              </p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-green-700">
                {((stats.decisions.total - (stats.decisions.quarantined || 0)) * 1200).toLocaleString()}
              </p>
              <p className="text-sm text-green-600 mt-1">Tokens Saved</p>
              <p className="text-xs text-gray-500 mt-1">
                ~1,200 tokens/decision avoided
              </p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-green-700">
                {((stats.decisions.total - (stats.decisions.quarantined || 0)) * 0.003).toFixed(2)}
              </p>
              <p className="text-sm text-green-600 mt-1">USD Saved</p>
              <p className="text-xs text-gray-500 mt-1">
                vs. sending every diff to LLM
              </p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-green-700">
                {((stats.decisions.total - (stats.decisions.quarantined || 0)) * 0.8).toFixed(1)}s
              </p>
              <p className="text-sm text-green-600 mt-1">Compute Time Saved</p>
              <p className="text-xs text-gray-500 mt-1">
                ~0.8s per avoided LLM call
              </p>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

// =============================================================================
// HELPERS
// =============================================================================

interface TimeSeriesPoint {
  timestamp: string;
  value: number;
}

interface MergedTimeSeriesPoint {
  timestamp: string;
  allowed: number;
  denied: number;
  quarantined: number;
}

/**
 * Merge separate allowed/denied/quarantined time series arrays
 * into a single flat array for Recharts
 */
function mergeTimeSeries(data: {
  allowed: TimeSeriesPoint[];
  denied: TimeSeriesPoint[];
  quarantined: TimeSeriesPoint[];
}): MergedTimeSeriesPoint[] {
  const byTimestamp = new Map<string, MergedTimeSeriesPoint>();

  for (const point of data.allowed) {
    if (!byTimestamp.has(point.timestamp)) {
      byTimestamp.set(point.timestamp, { timestamp: point.timestamp, allowed: 0, denied: 0, quarantined: 0 });
    }
    byTimestamp.get(point.timestamp)!.allowed = point.value;
  }

  for (const point of data.denied) {
    if (!byTimestamp.has(point.timestamp)) {
      byTimestamp.set(point.timestamp, { timestamp: point.timestamp, allowed: 0, denied: 0, quarantined: 0 });
    }
    byTimestamp.get(point.timestamp)!.denied = point.value;
  }

  for (const point of data.quarantined) {
    if (!byTimestamp.has(point.timestamp)) {
      byTimestamp.set(point.timestamp, { timestamp: point.timestamp, allowed: 0, denied: 0, quarantined: 0 });
    }
    byTimestamp.get(point.timestamp)!.quarantined = point.value;
  }

  return Array.from(byTimestamp.values()).sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
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
