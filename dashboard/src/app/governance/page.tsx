'use client';

import { useMemo } from 'react';
import { Download, RefreshCw } from 'lucide-react';
import { Card, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { useApprovals, useEvidenceStats, usePolicies } from '@/lib/hooks';
import type { ApprovalRequest, Policy } from '@/lib/api';

type LifecycleState = 'DRAFT' | 'REVIEW' | 'APPROVED' | 'DEPLOYED';

interface PolicyLifecycleItem {
  policyId: string;
  title: string;
  owner: string;
  updatedAt: string;
  state: LifecycleState;
}

interface DelegationRow {
  actionClass: string;
  requiredRole: string;
  requestCount: number;
  pendingCount: number;
  nextExpiry?: string;
}

const states: LifecycleState[] = ['DRAFT', 'REVIEW', 'APPROVED', 'DEPLOYED'];

const stateVariant: Record<LifecycleState, 'default' | 'warning' | 'info' | 'success'> = {
  DRAFT: 'default',
  REVIEW: 'warning',
  APPROVED: 'info',
  DEPLOYED: 'success',
};

function fmtIso(iso: string): string {
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? 'Unknown time' : parsed.toLocaleString();
}

function deriveLifecycleState(policy: Policy): LifecycleState {
  if (!policy.enabled) {
    return policy.updated_at === policy.created_at ? 'DRAFT' : 'REVIEW';
  }

  const updatedAt = Date.parse(policy.updated_at);
  if (!Number.isNaN(updatedAt)) {
    const daysSinceUpdate = (Date.now() - updatedAt) / (1000 * 60 * 60 * 24);
    if (daysSinceUpdate <= 7) {
      return 'APPROVED';
    }
  }

  return 'DEPLOYED';
}

function policyToLifecycleItem(policy: Policy): PolicyLifecycleItem {
  const title = policy.description?.trim()
    ? policy.description
    : `${policy.scope.action} -> ${policy.scope.resource_type}`;

  return {
    policyId: policy.policy_id,
    title,
    owner: policy.regulation || 'Policy Team',
    updatedAt: policy.updated_at || policy.created_at || new Date().toISOString(),
    state: deriveLifecycleState(policy),
  };
}

function downloadText(filename: string, content: string): void {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export default function GovernancePage() {
  const { data: policyData, isLoading: policyLoading, error: policyError, refetch: refetchPolicies } = usePolicies({
    page: 1,
    page_size: 200,
  });
  const { data: approvalData, error: approvalError, refetch: refetchApprovals } = useApprovals({
    page: 1,
    page_size: 200,
  });
  const { data: evidenceStats, error: evidenceError, refetch: refetchEvidenceStats } = useEvidenceStats();

  const delegationRows = useMemo(
    () => buildDelegationRows(approvalData?.data ?? []),
    [approvalData],
  );

  const items = useMemo(
    () => (policyData?.data ?? []).map(policyToLifecycleItem),
    [policyData]
  );

  const grouped = useMemo(() => {
    return states.map((state) => ({
      state,
      items: items
        .filter((item) => item.state === state)
        .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
    }));
  }, [items]);

  const governanceSnapshot = useMemo(() => {
    const pendingApprovals = approvalData?.data?.filter((approval) => approval.status === 'PENDING').length ?? 0;
    const byDecision = evidenceStats?.by_decision ?? {};

    return {
      policyTotal: items.length,
      pendingApprovals,
      evidenceTotal: evidenceStats?.total ?? 0,
      denied: byDecision.DENY ?? 0,
      quarantined: byDecision.QUARANTINE ?? 0,
      updatedAt: new Date().toISOString(),
    };
  }, [approvalData, evidenceStats, items.length]);

  const exportGovernanceReport = () => {
    const lines = [
      `# STIX Governance Snapshot`,
      ``,
      `Generated: ${governanceSnapshot.updatedAt}`,
      ``,
      `## Summary`,
      ``,
      `- Policies tracked: ${governanceSnapshot.policyTotal}`,
      `- Pending approvals: ${governanceSnapshot.pendingApprovals}`,
      `- Evidence records observed: ${governanceSnapshot.evidenceTotal}`,
      `- DENY decisions: ${governanceSnapshot.denied}`,
      `- QUARANTINE decisions: ${governanceSnapshot.quarantined}`,
      ``,
      `## Lifecycle Distribution`,
      ``,
      ...grouped.map((group) => `- ${group.state}: ${group.items.length}`),
      ``,
      `## Recent Policies`,
      ``,
      ...items.slice(0, 20).map((item) => `- ${item.policyId} | ${item.state} | ${item.owner} | ${item.updatedAt}`),
      '',
    ];

    const stamp = governanceSnapshot.updatedAt.slice(0, 10);
    downloadText(`stix-governance-snapshot-${stamp}.md`, lines.join('\n'));
  };

  if (policyLoading) {
    return (
      <div className="p-6">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Governance</h1>
          <p className="text-sm text-gray-500 mt-1">
            Policy lifecycle, approval delegation, and reporting cadence.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={() => {
              void refetchPolicies();
              void refetchApprovals();
              void refetchEvidenceStats();
            }}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button variant="secondary" onClick={exportGovernanceReport}>
            <Download className="mr-2 h-4 w-4" />
            Export Snapshot
          </Button>
        </div>
      </div>

      {(policyError || approvalError || evidenceError) && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Governance data is partially unavailable: {(policyError ?? approvalError ?? evidenceError) instanceof Error ? (policyError ?? approvalError ?? evidenceError)?.message : 'Unknown error'}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {grouped.map((group) => (
          <Card key={group.state} className="!p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold">{group.state}</h2>
              <Badge variant={stateVariant[group.state]}>{group.items.length}</Badge>
            </div>
            <div className="space-y-3">
              {group.items.map((item) => (
                <div key={item.policyId} className="rounded-lg border border-gray-200 p-3 bg-white">
                  <div className="flex items-center justify-between">
                    <p className="font-medium text-sm">{item.policyId}</p>
                    <Badge variant={stateVariant[item.state]}>{item.state}</Badge>
                  </div>
                  <p className="text-sm text-gray-700 mt-1">{item.title}</p>
                  <p className="text-xs text-gray-500 mt-2">
                    {item.owner} | {fmtIso(item.updatedAt)}
                  </p>
                </div>
              ))}
              {group.items.length === 0 && (
                <p className="text-xs text-gray-500">No policies in this state.</p>
              )}
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader
            title="Approval Delegation Matrix"
            description="Required roles and expiry windows observed in the live approval service"
          />
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="py-2 pr-4">Action Class</th>
                  <th className="py-2 pr-4">Required Role</th>
                  <th className="py-2 pr-4">Requests</th>
                  <th className="py-2">Next Expiry</th>
                </tr>
              </thead>
              <tbody>
                {delegationRows.map((row) => (
                  <tr key={`${row.actionClass}-${row.requiredRole}`} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-mono text-xs">{row.actionClass}</td>
                    <td className="py-2 pr-4">
                      <Badge variant={row.requiredRole === 'Any configured approver' ? 'default' : 'info'} size="sm">
                        {row.requiredRole}
                      </Badge>
                    </td>
                    <td className="py-2 pr-4">
                      {row.pendingCount > 0 ? `${row.pendingCount} pending / ` : ''}{row.requestCount} total
                    </td>
                    <td className="py-2 text-gray-600">
                      {row.nextExpiry ? fmtIso(row.nextExpiry) : 'No pending request'}
                    </td>
                  </tr>
                ))}
                {!delegationRows.length && (
                  <tr>
                    <td className="py-4 text-sm text-gray-500" colSpan={4}>
                      No approval delegation records returned by the service.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <Card>
          <CardHeader title="Reporting Cadence" />
          <div className="space-y-3 text-sm">
            <div className="rounded-lg border border-gray-200 p-3">
              <p className="font-medium">Daily</p>
              <p className="text-gray-600">
                Evidence volume: {governanceSnapshot.evidenceTotal}, denies: {governanceSnapshot.denied}, quarantines: {governanceSnapshot.quarantined}, pending approvals: {governanceSnapshot.pendingApprovals}.
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 p-3">
              <p className="font-medium">Weekly</p>
              <p className="text-gray-600">Run replay and verification cadence workflow and review drift report artifacts.</p>
            </div>
            <div className="rounded-lg border border-gray-200 p-3">
              <p className="font-medium">Monthly</p>
              <p className="text-gray-600">Generate SLO sign-off packet and attach DR, attestation, and capacity evidence.</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

function buildDelegationRows(approvals: ApprovalRequest[]): DelegationRow[] {
  const grouped = new Map<string, ApprovalRequest[]>();

  for (const approval of approvals) {
    const actionClass = `${approval.action} -> ${approval.resource_type}`;
    const requiredRole = approval.required_role || 'Any configured approver';
    const key = `${actionClass}::${requiredRole}`;
    const existing = grouped.get(key) ?? [];
    existing.push(approval);
    grouped.set(key, existing);
  }

  return [...grouped.entries()]
    .map(([key, requests]) => {
      const [actionClass, requiredRole] = key.split('::');
      const pending = requests
        .filter((request) => request.status === 'PENDING')
        .sort((a, b) => Date.parse(a.expires_at) - Date.parse(b.expires_at));

      return {
        actionClass,
        requiredRole,
        requestCount: requests.length,
        pendingCount: pending.length,
        nextExpiry: pending[0]?.expires_at,
      };
    })
    .sort((a, b) => b.pendingCount - a.pendingCount || b.requestCount - a.requestCount)
    .slice(0, 8);
}
