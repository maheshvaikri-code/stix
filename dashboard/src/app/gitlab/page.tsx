'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import {
  GitBranch,
  GitMerge,
  GitPullRequest,
  Shield,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Activity,
  Eye,
  RefreshCw,
} from 'lucide-react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge, DecisionBadge } from '@/components/ui/badge';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { useEvidence, useFabricAgents } from '@/lib/hooks';

// =============================================================================
// TYPES
// =============================================================================

interface MRComplianceEntry {
  traceId: string;
  mrIid: number;
  projectPath: string;
  title: string;
  targetBranch: string;
  decision: 'ALLOW' | 'DENY' | 'QUARANTINE';
  riskTier: string;
  findingsCount: number;
  timestamp: string;
  regulations: string[];
  author: string;
}

// =============================================================================
// GITLAB INTEGRATION PAGE
// =============================================================================

export default function GitLabPage() {
  const [filter, setFilter] = useState<'all' | 'ALLOW' | 'DENY' | 'QUARANTINE'>('all');

  // Fetch evidence records tagged with platform:gitlab
  const { data: evidenceData, isLoading, error: evidenceError, refetch } = useEvidence({
    page_size: 50,
    resource_type: 'merge_request',
  });
  const { data: fabricAgents } = useFabricAgents();

  const guardianAgent = useMemo(
    () => fabricAgents?.data.find((agent) =>
      agent.labels.some((label) => /gitlab|guardian/i.test(label)) ||
      /gitlab|guardian/i.test(agent.display_name),
    ),
    [fabricAgents],
  );
  const guardianPolicyPack = guardianAgent?.metadata?.policy_pack
    ?? (guardianAgent?.labels.length ? guardianAgent.labels.join(', ') : undefined)
    ?? 'Not configured';

  // Transform evidence records into MR compliance entries
  const mrEntries: MRComplianceEntry[] = (evidenceData?.data ?? []).map((record) => {
    const meta = (record.metadata ?? {}) as Record<string, unknown>;
    const resourceAttrs = (meta.resource_attributes ?? {}) as Record<string, unknown>;
    const contextAttrs = (meta.context_attributes ?? {}) as Record<string, unknown>;
    return {
      traceId: record.trace_id,
      mrIid: Number(resourceAttrs.mr_iid ?? 0),
      projectPath: String(resourceAttrs.project_path ?? record.resource_id ?? 'unknown/project'),
      title: String(resourceAttrs.title ?? record.action ?? 'Untitled MR'),
      targetBranch: String(resourceAttrs.target_branch ?? 'main'),
      decision: record.decision,
      riskTier: String(contextAttrs.risk_tier ?? 'LOW'),
      findingsCount: Number(contextAttrs.scan_findings_count ?? 0),
      timestamp: record.timestamp,
      regulations: Array.isArray(meta.regulations) ? meta.regulations as string[] : [],
      author: String(contextAttrs.gitlab_username ?? record.actor_id ?? 'unknown'),
    };
  });

  const filtered = filter === 'all' ? mrEntries : mrEntries.filter(e => e.decision === filter);

  // Stats
  const totalMRs = mrEntries.length;
  const allowedMRs = mrEntries.filter(e => e.decision === 'ALLOW').length;
  const deniedMRs = mrEntries.filter(e => e.decision === 'DENY').length;
  const quarantinedMRs = mrEntries.filter(e => e.decision === 'QUARANTINE').length;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <GitBranch className="h-7 w-7 text-orange-600" />
            GitLab Integration
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            STIX Guardian compliance monitoring for GitLab merge requests
          </p>
        </div>
        <Button variant="secondary" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 rounded-lg">
              <GitPullRequest className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{totalMRs}</p>
              <p className="text-xs text-gray-500">MRs Scanned</p>
            </div>
          </div>
        </Card>
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-50 rounded-lg">
              <CheckCircle className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-green-700">{allowedMRs}</p>
              <p className="text-xs text-gray-500">Compliant</p>
            </div>
          </div>
        </Card>
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-50 rounded-lg">
              <XCircle className="h-5 w-5 text-red-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-red-700">{deniedMRs}</p>
              <p className="text-xs text-gray-500">Violations</p>
            </div>
          </div>
        </Card>
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-50 rounded-lg">
              <Clock className="h-5 w-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-yellow-700">{quarantinedMRs}</p>
              <p className="text-xs text-gray-500">Pending Review</p>
            </div>
          </div>
        </Card>
      </div>

      {evidenceError && (
        <Card className="border-amber-200 bg-amber-50">
          <div className="flex items-center gap-3 p-4 text-sm text-amber-900">
            <AlertTriangle className="h-5 w-5 shrink-0" />
            GitLab evidence is unavailable: {evidenceError instanceof Error ? evidenceError.message : 'retry the request'}
          </div>
        </Card>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-6">
        {/* MR Compliance Table */}
        <div className="col-span-2">
          <Card>
            <CardHeader
              title="Merge Request Compliance Status"
              description="Recent MRs reviewed by STIX Guardian"
              action={
                <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
                  {(['all', 'ALLOW', 'DENY', 'QUARANTINE'] as const).map((f) => (
                    <button
                      key={f}
                      onClick={() => setFilter(f)}
                      className={`px-3 py-1 text-xs rounded ${
                        filter === f
                          ? 'bg-white shadow text-gray-900'
                          : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      {f === 'all' ? 'All' : f}
                    </button>
                  ))}
                </div>
              }
            />
            <CardContent>
              {isLoading ? (
                <div className="py-12 flex justify-center">
                  <LoadingSpinner />
                </div>
              ) : filtered.length === 0 ? (
                <div className="py-12 text-center text-gray-400">
                  <GitMerge className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                  <p className="font-medium">No merge requests found</p>
                  <p className="text-sm mt-1">
                    MRs reviewed by STIX Guardian will appear here
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {filtered.map((entry) => (
                    <div
                      key={entry.traceId}
                      className="px-6 py-4 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-sm truncate">
                              !{entry.mrIid}
                            </span>
                            <span className="text-gray-500 text-sm truncate">
                              {entry.title}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                            <span>{entry.projectPath}</span>
                            <span>→ {entry.targetBranch}</span>
                            <span>by {entry.author}</span>
                            {entry.findingsCount > 0 && (
                              <span className="text-orange-500">
                                {entry.findingsCount} finding{entry.findingsCount !== 1 ? 's' : ''}
                              </span>
                            )}
                          </div>
                          {entry.regulations.length > 0 && (
                            <div className="flex gap-1 mt-2">
                              {entry.regulations.map((reg) => (
                                <Badge key={reg} variant="info" size="sm">
                                  {reg}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-3 ml-4">
                          <Badge
                            variant={
                              entry.riskTier === 'CRITICAL' ? 'error' :
                              entry.riskTier === 'HIGH' ? 'error' :
                              entry.riskTier === 'MEDIUM' ? 'warning' : 'success'
                            }
                            size="sm"
                          >
                            {entry.riskTier}
                          </Badge>
                          <DecisionBadge decision={entry.decision} />
                        </div>
                      </div>
                      <div className="mt-2 text-xs text-gray-400">
                        Trace: {entry.traceId.substring(0, 16)}... | {formatTimeAgo(entry.timestamp)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Guardian Status */}
          <Card>
            <CardHeader title="STIX Guardian Agent" />
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-50 rounded-lg">
                  <Shield className="h-5 w-5 text-green-600" />
                </div>
                <div>
                <p className="font-medium text-sm">
                  {guardianAgent?.status === 'ACTIVE' ? 'Active' : guardianAgent ? guardianAgent.status : 'Not registered'}
                </p>
                <p className="text-xs text-gray-500">
                    {guardianAgent ? 'Registered in the live Fabric inventory' : 'No GitLab Guardian agent is registered in Fabric'}
                  </p>
                </div>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Agent Type</span>
                  <span className="font-medium">{guardianAgent?.runtime ?? 'Unregistered'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Owner</span>
                  <span className="font-medium">{guardianAgent?.owner ?? '-'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Triggers</span>
                  <span className="font-medium">{guardianAgent?.metadata?.triggers ? String(guardianAgent.metadata.triggers) : 'merge request evidence'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Policy Pack</span>
                  <Badge variant="info" size="sm">{String(guardianPolicyPack)}</Badge>
                </div>
              </div>
            </div>
          </Card>

          {/* Compliance Flow */}
          <Card>
            <CardHeader title="Compliance Gate Flow" />
            <div className="space-y-3">
              {[
                { step: 1, label: 'MR Created / Updated', icon: GitPullRequest, color: 'text-blue-600' },
                { step: 2, label: 'Diff Scanned for Signals', icon: Eye, color: 'text-purple-600' },
                { step: 3, label: 'STIX Policy Evaluation', icon: Shield, color: 'text-indigo-600' },
                { step: 4, label: 'Claude Analysis (if needed)', icon: Activity, color: 'text-cyan-600' },
                { step: 5, label: 'Decision + Proof Token', icon: CheckCircle, color: 'text-green-600' },
              ].map(({ step, label, icon: Icon, color }) => (
                <div key={step} className="flex items-center gap-3">
                  <div className={`w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-600`}>
                    {step}
                  </div>
                  <Icon className={`h-4 w-4 ${color}`} />
                  <span className="text-sm text-gray-700">{label}</span>
                </div>
              ))}
            </div>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader title="Quick Actions" />
            <div className="space-y-2">
              <Link href="/policies" className="block">
                <Button variant="secondary" className="w-full justify-start text-sm">
                <Eye className="h-4 w-4 mr-2" />
                View Policy Pack
                </Button>
              </Link>
              <Link href="/governance" className="block">
                <Button variant="secondary" className="w-full justify-start text-sm">
                <RefreshCw className="h-4 w-4 mr-2" />
                Run Policy Drift Check
                </Button>
              </Link>
              <Link href="/evidence" className="block">
                <Button variant="secondary" className="w-full justify-start text-sm">
                <AlertTriangle className="h-4 w-4 mr-2" />
                View Evidence Chain
                </Button>
              </Link>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// HELPERS
// =============================================================================

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
