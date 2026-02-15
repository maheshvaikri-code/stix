'use client';

import { useMemo, useState } from 'react';
import { Card, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

type LifecycleState = 'DRAFT' | 'REVIEW' | 'APPROVED' | 'DEPLOYED';

interface PolicyLifecycleItem {
  policyId: string;
  title: string;
  owner: string;
  updatedAt: string;
  state: LifecycleState;
}

const initialItems: PolicyLifecycleItem[] = [
  { policyId: 'HIPAA-021', title: 'PHI outbound masking', owner: 'Policy Team', updatedAt: '2026-02-14T10:00:00Z', state: 'DRAFT' },
  { policyId: 'HIPAA-042', title: 'External recipient quarantine', owner: 'Compliance', updatedAt: '2026-02-14T09:30:00Z', state: 'REVIEW' },
  { policyId: 'SOC2-007', title: 'Service token strict auth', owner: 'Security', updatedAt: '2026-02-13T19:00:00Z', state: 'APPROVED' },
  { policyId: 'HIPAA-000', title: 'Default deny baseline', owner: 'Platform', updatedAt: '2026-02-13T16:45:00Z', state: 'DEPLOYED' },
];

const states: LifecycleState[] = ['DRAFT', 'REVIEW', 'APPROVED', 'DEPLOYED'];

const stateVariant: Record<LifecycleState, 'default' | 'warning' | 'info' | 'success'> = {
  DRAFT: 'default',
  REVIEW: 'warning',
  APPROVED: 'info',
  DEPLOYED: 'success',
};

function fmtIso(iso: string): string {
  return new Date(iso).toLocaleString();
}

export default function GovernancePage() {
  const [items, setItems] = useState<PolicyLifecycleItem[]>(initialItems);

  const grouped = useMemo(() => {
    return states.map((state) => ({
      state,
      items: items.filter(i => i.state === state).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
    }));
  }, [items]);

  const advance = (policyId: string) => {
    setItems(prev =>
      prev.map(item => {
        if (item.policyId !== policyId) return item;
        const idx = states.indexOf(item.state);
        const next = idx < states.length - 1 ? states[idx + 1] : item.state;
        return { ...item, state: next, updatedAt: new Date().toISOString() };
      })
    );
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Governance</h1>
        <p className="text-sm text-gray-500 mt-1">
          Policy lifecycle, approval delegation, and reporting cadence.
        </p>
      </div>

      <div className="grid grid-cols-4 gap-4">
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
                    {item.owner} • {fmtIso(item.updatedAt)}
                  </p>
                  <Button
                    className="mt-3 w-full"
                    variant="secondary"
                    disabled={item.state === 'DEPLOYED'}
                    onClick={() => advance(item.policyId)}
                  >
                    {item.state === 'DEPLOYED' ? 'Final State' : 'Advance State'}
                  </Button>
                </div>
              ))}
              {group.items.length === 0 && (
                <p className="text-xs text-gray-500">No policies in this state.</p>
              )}
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Approval Delegation Matrix" />
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="py-2 pr-4">Action Class</th>
                  <th className="py-2 pr-4">Primary Approver</th>
                  <th className="py-2 pr-4">Backup Approver</th>
                  <th className="py-2">SLA</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b">
                  <td className="py-2 pr-4">PHI External Send</td>
                  <td className="py-2 pr-4">Privacy Officer</td>
                  <td className="py-2 pr-4">Security Officer</td>
                  <td className="py-2">30m</td>
                </tr>
                <tr className="border-b">
                  <td className="py-2 pr-4">Policy Promotion</td>
                  <td className="py-2 pr-4">Compliance Lead</td>
                  <td className="py-2 pr-4">Platform Lead</td>
                  <td className="py-2">4h</td>
                </tr>
                <tr>
                  <td className="py-2 pr-4">Emergency Override</td>
                  <td className="py-2 pr-4">Security On-Call</td>
                  <td className="py-2 pr-4">Engineering Director</td>
                  <td className="py-2">15m</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>

        <Card>
          <CardHeader title="Reporting Cadence" />
          <div className="space-y-3 text-sm">
            <div className="rounded-lg border border-gray-200 p-3">
              <p className="font-medium">Daily</p>
              <p className="text-gray-600">Decision volume, denies, quarantines, pending approvals.</p>
            </div>
            <div className="rounded-lg border border-gray-200 p-3">
              <p className="font-medium">Weekly</p>
              <p className="text-gray-600">Policy drift/replay checks, key usage by `key_id`, evidence integrity summary.</p>
            </div>
            <div className="rounded-lg border border-gray-200 p-3">
              <p className="font-medium">Monthly</p>
              <p className="text-gray-600">RTO/RPO drill outcomes, control attestations, capacity envelope review.</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
