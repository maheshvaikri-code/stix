'use client';

import { useEffect, useRef, useState } from 'react';
import {
  FileText,
  Plus,
  Search,
  Filter,
  Download,
  Upload,
  Eye,
  Edit,
  Trash2,
  CheckCircle,
  XCircle,
  Play,
} from 'lucide-react';
import {
  useAuthorizeAction,
  usePolicies,
  useTogglePolicy,
  useDeletePolicy,
  useCreatePolicy,
  useUpdatePolicy,
} from '@/lib/hooks';
import {
  type ActorType,
  type AuthorizationDecision,
  type AuthorizationResult,
  type DetectionSignals,
  type Environment,
  type Policy,
  type RiskTier,
} from '@/lib/api';
import { api } from '@/lib/api';
import { Card, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input, Textarea } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge, DecisionBadge } from '@/components/ui/badge';
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from '@/components/ui/table';
import { Pagination } from '@/components/ui/pagination';
import { Modal, ModalFooter } from '@/components/ui/modal';
import { EmptyState } from '@/components/ui/empty-state';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { CodeBlock, JsonViewer } from '@/components/ui/code-block';

// =============================================================================
// POLICIES PAGE
// =============================================================================

export default function PoliciesPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [regulation, setRegulation] = useState<string>('');
  const [decision, setDecision] = useState<string>('');
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null);
  const [editorPolicy, setEditorPolicy] = useState<Policy | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [showSimulator, setShowSimulator] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const { data, isLoading, error } = usePolicies({
    page,
    page_size: 20,
    search: search || undefined,
    regulation: regulation || undefined,
    decision: decision || undefined,
  });

  const togglePolicy = useTogglePolicy();
  const deletePolicy = useDeletePolicy();
  const createPolicy = useCreatePolicy();

  const handleToggle = (policyId: string, currentEnabled: boolean) => {
    togglePolicy.mutate({ policyId, enabled: !currentEnabled });
  };

  const handleDelete = (policyId: string) => {
    deletePolicy.mutate(policyId, {
      onSuccess: () => setShowDeleteConfirm(null),
    });
  };

  const handleExport = async () => {
    try {
      const blob = await api.exportPolicies();
      downloadBlob(blob, `stix-policies-${new Date().toISOString().slice(0, 10)}.json`);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Failed to export policies');
    }
  };

  const handleImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    try {
      const parsed = JSON.parse(await file.text()) as { policies?: unknown[] } | unknown[];
      const policies = Array.isArray(parsed) ? parsed : parsed.policies;
      if (!policies?.length) throw new Error('The import file must contain a non-empty policies array');

      for (const policy of policies) {
        await createPolicy.mutateAsync(policy as Omit<Policy, 'created_at' | 'updated_at'>);
      }
      setActionError(null);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Failed to import policies');
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Policies</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage authorization policies for AI agents
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" onClick={() => setShowSimulator(true)}>
            <Play className="h-4 w-4 mr-2" />
            Simulator
          </Button>
          <Button variant="secondary" onClick={() => importInputRef.current?.click()}>
            <Upload className="h-4 w-4 mr-2" />
            Import
          </Button>
          <input
            ref={importInputRef}
            type="file"
            accept="application/json,.json"
            onChange={handleImport}
            className="hidden"
          />
          <Button variant="secondary" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button onClick={() => { setEditorPolicy(null); setShowEditor(true); }}>
            <Plus className="h-4 w-4 mr-2" />
            New Policy
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <Input
              placeholder="Search policies..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="max-w-md"
            />
          </div>
          <Select
            value={regulation}
            onChange={(e) => setRegulation(e.target.value)}
            options={[
              { value: '', label: 'All Regulations' },
              { value: 'HIPAA', label: 'HIPAA' },
              { value: 'GDPR', label: 'GDPR' },
              { value: 'SOX', label: 'SOX' },
              { value: 'PCI', label: 'PCI-DSS' },
              { value: 'CCPA', label: 'CCPA' },
            ]}
          />
          <Select
            value={decision}
            onChange={(e) => setDecision(e.target.value)}
            options={[
              { value: '', label: 'All Decisions' },
              { value: 'ALLOW', label: 'Allow' },
              { value: 'DENY', label: 'Deny' },
              { value: 'QUARANTINE', label: 'Quarantine' },
            ]}
          />
        </div>
      </Card>

      {(actionError || togglePolicy.error || deletePolicy.error) && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          {actionError || (togglePolicy.error as Error | null)?.message || (deletePolicy.error as Error | null)?.message}
        </div>
      )}

      {/* Policies Table */}
      <Card padding="none">
        {isLoading ? (
          <div className="py-12">
            <LoadingSpinner />
          </div>
        ) : error ? (
          <EmptyState
            title="Error loading policies"
            description={error instanceof Error ? error.message : 'Unknown error'}
          />
        ) : !data?.data.length ? (
          <EmptyState
            icon={<FileText className="h-12 w-12" />}
            title="No policies found"
            description="Create your first policy to start securing AI agent actions."
            action={
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Policy
              </Button>
            }
          />
        ) : (
          <>
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeader>Policy ID</TableHeader>
                  <TableHeader>Scope</TableHeader>
                  <TableHeader>Decision</TableHeader>
                  <TableHeader>Regulation</TableHeader>
                  <TableHeader>Priority</TableHeader>
                  <TableHeader>Status</TableHeader>
                  <TableHeader>Actions</TableHeader>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.data.map((policy) => (
                  <TableRow key={policy.policy_id} clickable>
                    <TableCell>
                      <div>
                        <p className="font-medium text-gray-900">{policy.policy_id}</p>
                        <p className="text-xs text-gray-500">v{policy.version}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-xs space-y-1">
                        <p>
                          <span className="text-gray-500">Actor:</span> {policy.scope.actor_type}
                        </p>
                        <p>
                          <span className="text-gray-500">Action:</span> {policy.scope.action}
                        </p>
                        <p>
                          <span className="text-gray-500">Resource:</span> {policy.scope.resource_type}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <DecisionBadge decision={policy.decision} />
                    </TableCell>
                    <TableCell>
                      {policy.regulation ? (
                        <Badge variant="info">{policy.regulation}</Badge>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-sm">{policy.priority}</span>
                    </TableCell>
                    <TableCell>
                      <button
                        onClick={() => handleToggle(policy.policy_id, policy.enabled)}
                        className={`flex items-center gap-1 text-sm ${
                          policy.enabled ? 'text-green-600' : 'text-gray-400'
                        }`}
                      >
                        {policy.enabled ? (
                          <>
                            <CheckCircle className="h-4 w-4" /> Enabled
                          </>
                        ) : (
                          <>
                            <XCircle className="h-4 w-4" /> Disabled
                          </>
                        )}
                      </button>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setSelectedPolicy(policy)}
                          className="p-1 hover:bg-gray-100 rounded"
                        >
                          <Eye className="h-4 w-4 text-gray-500" />
                        </button>
                        <button
                          onClick={() => { setEditorPolicy(policy); setShowEditor(true); }}
                          className="p-1 hover:bg-gray-100 rounded"
                        >
                          <Edit className="h-4 w-4 text-gray-500" />
                        </button>
                        <button
                          onClick={() => setShowDeleteConfirm(policy.policy_id)}
                          className="p-1 hover:bg-gray-100 rounded"
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pagination
              page={page}
              pageSize={20}
              total={data.total}
              onPageChange={setPage}
            />
          </>
        )}
      </Card>

      {/* Policy Detail Modal */}
      <Modal
        isOpen={!!selectedPolicy}
        onClose={() => setSelectedPolicy(null)}
        title={`Policy: ${selectedPolicy?.policy_id}`}
        size="lg"
      >
        {selectedPolicy && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-500">Version</p>
                <p className="font-medium">{selectedPolicy.version}</p>
              </div>
              <div>
                <p className="text-gray-500">Priority</p>
                <p className="font-medium">{selectedPolicy.priority}</p>
              </div>
              <div>
                <p className="text-gray-500">Decision</p>
                <DecisionBadge decision={selectedPolicy.decision} />
              </div>
              <div>
                <p className="text-gray-500">Reason Code</p>
                <p className="font-medium">{selectedPolicy.reason_code}</p>
              </div>
              <div>
                <p className="text-gray-500">Created</p>
                <p className="font-medium">
                  {new Date(selectedPolicy.created_at).toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-gray-500">Updated</p>
                <p className="font-medium">
                  {new Date(selectedPolicy.updated_at).toLocaleString()}
                </p>
              </div>
            </div>

            <div>
              <p className="text-sm text-gray-500 mb-2">Scope</p>
              <JsonViewer data={selectedPolicy.scope} maxHeight="150px" />
            </div>

            {selectedPolicy.conditions && (
              <div>
                <p className="text-sm text-gray-500 mb-2">Conditions</p>
                <JsonViewer data={selectedPolicy.conditions} maxHeight="200px" />
              </div>
            )}

            {selectedPolicy.description && (
              <div>
                <p className="text-sm text-gray-500 mb-2">Description</p>
                <p className="text-sm">{selectedPolicy.description}</p>
              </div>
            )}
          </div>
        )}
      </Modal>

      <PolicyEditor
        isOpen={showEditor}
        policy={editorPolicy}
        onClose={() => setShowEditor(false)}
      />

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(null)}
        title="Delete Policy"
        size="sm"
      >
        <p className="text-gray-600">
          Are you sure you want to delete policy{' '}
          <span className="font-medium">{showDeleteConfirm}</span>? This action
          cannot be undone.
        </p>
        <ModalFooter>
          <Button variant="secondary" onClick={() => setShowDeleteConfirm(null)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={() => showDeleteConfirm && handleDelete(showDeleteConfirm)}
            loading={deletePolicy.isPending}
          >
            Delete
          </Button>
        </ModalFooter>
      </Modal>

      {/* Policy Simulator Modal */}
      <PolicySimulator
        isOpen={showSimulator}
        onClose={() => setShowSimulator(false)}
      />
    </div>
  );
}

// =============================================================================
// POLICY SIMULATOR
// =============================================================================

type CoreSignalKey = 'piiDetected' | 'phiDetected' | 'pciDetected' | 'secretsDetected';

type SignalState = Record<CoreSignalKey, boolean>;

interface PresetScenario {
  name: string;
  description: string;
  actorId: string;
  actorType: ActorType;
  action: string;
  resourceType: string;
  env: Environment;
  signals: Partial<SignalState>;
  riskTier?: RiskTier;
  expected: AuthorizationDecision;
}

const DEFAULT_SIGNALS: SignalState = {
  piiDetected: false,
  phiDetected: false,
  pciDetected: false,
  secretsDetected: false,
};

const SIGNAL_OPTIONS: Array<{
  key: CoreSignalKey;
  label: string;
  description: string;
}> = [
  {
    key: 'piiDetected',
    label: 'PII',
    description: 'Personally identifiable information detected',
  },
  {
    key: 'phiDetected',
    label: 'PHI',
    description: 'Protected health information detected',
  },
  {
    key: 'pciDetected',
    label: 'PCI',
    description: 'Payment card data detected',
  },
  {
    key: 'secretsDetected',
    label: 'Secrets',
    description: 'Credentials or keys detected',
  },
];

// Preset compliance scenarios for quick testing against the live Enforcer API.
const PRESET_SCENARIOS: PresetScenario[] = [
  {
    name: 'PHI Access Blocked',
    description: 'HIPAA: AI agent attempts to read patient data with PHI detected',
    actorId: 'healthcare-agent',
    actorType: 'AI_AGENT',
    action: 'read_patient_record',
    resourceType: 'patient_data',
    env: 'prod',
    signals: { phiDetected: true },
    expected: 'DENY',
  },
  {
    name: 'PII Read With Masking',
    description: 'Baseline: low-risk read with PII signal should allow with masking obligations',
    actorId: 'support-agent',
    actorType: 'AI_AGENT',
    action: 'read_customer_record',
    resourceType: 'customer_profile',
    env: 'prod',
    signals: { piiDetected: true },
    expected: 'ALLOW',
  },
  {
    name: 'High-Risk Tool Execution',
    description: 'Default guardrail: high-risk tool execution requires human approval',
    actorId: 'ops-agent',
    actorType: 'AI_AGENT',
    action: 'execute_shell',
    resourceType: 'tool',
    env: 'prod',
    signals: {},
    riskTier: 'HIGH',
    expected: 'QUARANTINE',
  },
  {
    name: 'Secret Access Blocked',
    description: 'Security: AI agent touches a secret with credential signal detected',
    actorId: 'gitlab:user:developer',
    actorType: 'AI_AGENT',
    action: 'read_secret',
    resourceType: 'secret',
    env: 'prod',
    signals: { secretsDetected: true },
    expected: 'DENY',
  },
  {
    name: 'Tokenized Payment Allowed',
    description: 'PCI: service processes tokenized payment data without card data exposure',
    actorId: 'payment-service',
    actorType: 'SERVICE',
    action: 'process_payment',
    resourceType: 'payment_token',
    env: 'prod',
    signals: {},
    expected: 'ALLOW',
  },
];

type SimulationResult = AuthorizationResult;

function activeSignals(signals: SignalState): DetectionSignals {
  return Object.fromEntries(
    Object.entries(signals).filter(([, enabled]) => enabled),
  ) as DetectionSignals;
}

function decodeJwtPart(value: string) {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
  const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4);
  return JSON.parse(atob(padded));
}

function PolicySimulator({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [actorId, setActorId] = useState('test-agent');
  const [actorType, setActorType] = useState<ActorType>('AI_AGENT');
  const [action, setAction] = useState('send_email');
  const [resourceType, setResourceType] = useState('email');
  const [env, setEnv] = useState<Environment>('prod');
  const [riskTier, setRiskTier] = useState<RiskTier | ''>('');
  const [signals, setSignals] = useState<SignalState>(DEFAULT_SIGNALS);
  const [expectedDecision, setExpectedDecision] = useState<AuthorizationDecision | null>(null);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showProofToken, setShowProofToken] = useState(false);
  const authorizeAction = useAuthorizeAction();

  const resetResult = () => {
    setResult(null);
    setError(null);
    setShowProofToken(false);
    authorizeAction.reset();
  };

  const applyPreset = (preset: PresetScenario) => {
    setActorId(preset.actorId);
    setActorType(preset.actorType);
    setAction(preset.action);
    setResourceType(preset.resourceType);
    setEnv(preset.env);
    setRiskTier(preset.riskTier ?? '');
    setSignals({ ...DEFAULT_SIGNALS, ...preset.signals });
    setExpectedDecision(preset.expected);
    resetResult();
  };

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    setShowProofToken(false);
    try {
      const resourceAttributes = riskTier ? { risk_tier: riskTier } : undefined;
      const data = await authorizeAction.mutateAsync({
        actor: { id: actorId, type: actorType },
        action,
        resource: {
          type: resourceType,
          ...(resourceAttributes ? { attributes: resourceAttributes } : {}),
        },
        context: {
          env,
          tags: ['dashboard:policy-simulator'],
          signals: activeSignals(signals),
        },
        ...(riskTier
          ? {
              tool_call: {
                tool: action,
                risk_tier: riskTier,
                args_summary: `Dashboard simulator request for ${resourceType}`,
              },
            }
          : {}),
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  const decodeProofToken = (token: string) => {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) return null;
      const header = decodeJwtPart(parts[0]);
      const payload = decodeJwtPart(parts[1]);
      return { header, payload, signature: parts[2].substring(0, 32) + '...' };
    } catch {
      return null;
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Policy Simulator" size="lg">
      <div className="space-y-4">
        <p className="text-sm text-gray-500">
          Test how policies evaluate authorization requests. Select a preset scenario or enter custom values.
        </p>

        {/* Preset Scenarios */}
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
            Preset Scenarios
          </p>
          <div className="grid grid-cols-1 gap-2">
            {PRESET_SCENARIOS.map((preset) => (
              <button
                key={preset.name}
                onClick={() => applyPreset(preset)}
                className="flex items-center justify-between p-3 text-left rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-colors"
              >
                <div>
                  <p className="text-sm font-medium">{preset.name}</p>
                  <p className="text-xs text-gray-500">{preset.description}</p>
                </div>
                <Badge
                  variant={
                    preset.expected === 'ALLOW' ? 'success' :
                    preset.expected === 'DENY' ? 'error' : 'warning'
                  }
                  size="sm"
                >
                  Expected: {preset.expected}
                </Badge>
              </button>
            ))}
          </div>
        </div>

        {/* Custom Input */}
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
            Request Parameters
          </p>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Actor ID"
              value={actorId}
              onChange={(e) => setActorId(e.target.value)}
            />
            <Select
              label="Actor Type"
              value={actorType}
              onChange={(e) => setActorType(e.target.value as ActorType)}
              options={[
                { value: 'AI_AGENT', label: 'AI Agent' },
                { value: 'SERVICE', label: 'Service' },
                { value: 'HUMAN', label: 'Human' },
                { value: 'JOB', label: 'Job / CI Runner' },
              ]}
            />
            <Input
              label="Action"
              value={action}
              onChange={(e) => setAction(e.target.value)}
            />
            <Input
              label="Resource Type"
              value={resourceType}
              onChange={(e) => setResourceType(e.target.value)}
            />
            <Select
              label="Environment"
              value={env}
              onChange={(e) => setEnv(e.target.value as Environment)}
              options={[
                { value: 'prod', label: 'Production' },
                { value: 'stage', label: 'Staging' },
                { value: 'dev', label: 'Development' },
                { value: 'test', label: 'Test' },
              ]}
            />
            <Select
              label="Risk Tier"
              value={riskTier}
              onChange={(e) => setRiskTier(e.target.value as RiskTier | '')}
              options={[
                { value: '', label: 'None' },
                { value: 'LOW', label: 'Low' },
                { value: 'MEDIUM', label: 'Medium' },
                { value: 'HIGH', label: 'High' },
                { value: 'CRITICAL', label: 'Critical' },
              ]}
            />
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-500">
            Detection Signals
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {SIGNAL_OPTIONS.map((signal) => {
              const enabled = signals[signal.key];
              return (
                <button
                  key={signal.key}
                  type="button"
                  onClick={() =>
                    setSignals((current) => ({
                      ...current,
                      [signal.key]: !current[signal.key],
                    }))
                  }
                  className={`rounded-lg border p-3 text-left transition-colors ${
                    enabled
                      ? 'border-blue-300 bg-blue-50 text-blue-950'
                      : 'border-gray-200 bg-white hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium">{signal.label}</span>
                    <Badge variant={enabled ? 'info' : 'default'} size="sm">
                      {enabled ? 'On' : 'Off'}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-gray-500">{signal.description}</p>
                </button>
              );
            })}
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-lg bg-red-50 border border-red-200">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {result && (
          <div className={`p-4 rounded-lg border ${
            result.decision === 'ALLOW' ? 'bg-green-50 border-green-200' :
            result.decision === 'DENY' ? 'bg-red-50 border-red-200' :
            'bg-yellow-50 border-yellow-200'
          }`}>
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-medium">Simulation Result</p>
                {expectedDecision && (
                  <Badge
                    variant={expectedDecision === result.decision ? 'success' : 'warning'}
                    size="sm"
                  >
                    {expectedDecision === result.decision ? 'Matched' : 'Expected'} {expectedDecision}
                  </Badge>
                )}
              </div>
              {result.trace_id && (
                <span className="text-xs text-gray-400 font-mono">
                  {result.trace_id.substring(0, 16)}...
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-500">Decision:</span>{' '}
                <DecisionBadge decision={result.decision} />
              </div>
              {result.reason_code && (
                <div>
                  <span className="text-gray-500">Reason:</span>{' '}
                  <span className="font-mono text-xs">{result.reason_code}</span>
                </div>
              )}
              {result.policy?.id && (
                <div>
                  <span className="text-gray-500">Policy:</span>{' '}
                  <span className="font-mono text-xs">{result.policy.id}</span>
                </div>
              )}
              {result.explanation && (
                <div className="col-span-2">
                  <span className="text-gray-500">Explanation:</span>{' '}
                  <span className="text-xs">{result.explanation}</span>
                </div>
              )}
            </div>

            {/* Controls & Regulations */}
            {((result.controls?.length ?? 0) > 0 || (result.regulations?.length ?? 0) > 0) && (
              <div className="mt-3 pt-3 border-t border-gray-200 flex flex-wrap gap-1">
                {result.controls?.map((c) => (
                  <Badge key={c} variant="info" size="sm">{c}</Badge>
                ))}
                {result.regulations?.map((r) => (
                  <Badge key={r} variant="default" size="sm">{r}</Badge>
                ))}
              </div>
            )}

            {/* Obligations */}
            {result.obligations && result.obligations.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200">
                <p className="text-xs font-medium text-gray-500 mb-1">Obligations:</p>
                {result.obligations.map((ob, i) => (
                  <span key={i} className="mr-1 mb-1 inline-block"><Badge variant="warning" size="sm">{ob.type}</Badge></span>
                ))}
              </div>
            )}

            {/* Approval Info */}
            {result.approval?.required && (
              <div className="mt-3 pt-3 border-t border-gray-200">
                <p className="text-xs font-medium text-yellow-700">
                  Approval Required: {result.approval.approver_role ?? 'Compliance Officer'}
                  {result.approval.ticket_id && ` (Ticket: ${result.approval.ticket_id})`}
                </p>
              </div>
            )}

            {/* Proof Token */}
            {result.proof_token && (
              <div className="mt-3 pt-3 border-t border-gray-200">
                <button
                  onClick={() => setShowProofToken(!showProofToken)}
                  className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                >
                  {showProofToken ? 'Hide' : 'Show'} Proof Token (Ed25519)
                </button>
                {showProofToken && (
                  <div className="mt-2">
                    {(() => {
                      const decoded = decodeProofToken(result.proof_token!);
                      if (!decoded) return <p className="text-xs text-gray-400">Unable to decode</p>;
                      return (
                        <div className="space-y-2">
                          <div>
                            <p className="text-xs font-medium text-gray-500">Header:</p>
                            <pre className="text-xs bg-white p-2 rounded border overflow-x-auto">
                              {JSON.stringify(decoded.header, null, 2)}
                            </pre>
                          </div>
                          <div>
                            <p className="text-xs font-medium text-gray-500">Claims:</p>
                            <pre className="text-xs bg-white p-2 rounded border overflow-x-auto">
                              {JSON.stringify(decoded.payload, null, 2)}
                            </pre>
                          </div>
                          <div>
                            <p className="text-xs font-medium text-gray-500">Signature:</p>
                            <pre className="text-xs bg-white p-2 rounded border font-mono">
                              {decoded.signature}
                            </pre>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <ModalFooter>
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
        <Button onClick={runSimulation} loading={loading}>
          <Play className="h-4 w-4 mr-2" />
          Run Simulation
        </Button>
      </ModalFooter>
    </Modal>
  );
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function PolicyEditor({
  isOpen,
  policy,
  onClose,
}: {
  isOpen: boolean;
  policy: Policy | null;
  onClose: () => void;
}) {
  const createPolicy = useCreatePolicy();
  const updatePolicy = useUpdatePolicy();
  const [policyId, setPolicyId] = useState('');
  const [version, setVersion] = useState('1.0.0');
  const [priority, setPriority] = useState('100');
  const [actorType, setActorType] = useState<ActorType>('AI_AGENT');
  const [action, setAction] = useState('*');
  const [resourceType, setResourceType] = useState('*');
  const [decision, setDecision] = useState<AuthorizationDecision>('ALLOW');
  const [reasonCode, setReasonCode] = useState('POLICY_ALLOW');
  const [regulation, setRegulation] = useState('');
  const [description, setDescription] = useState('');
  const [conditions, setConditions] = useState('');
  const [enabled, setEnabled] = useState(true);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setPolicyId(policy?.policy_id ?? '');
    setVersion(policy?.version ?? '1.0.0');
    setPriority(String(policy?.priority ?? 100));
    setActorType((policy?.scope.actor_type as ActorType | undefined) ?? 'AI_AGENT');
    setAction(policy?.scope.action ?? '*');
    setResourceType(policy?.scope.resource_type ?? '*');
    setDecision(policy?.decision ?? 'ALLOW');
    setReasonCode(policy?.reason_code ?? 'POLICY_ALLOW');
    setRegulation(policy?.regulation ?? '');
    setDescription(policy?.description ?? '');
    setConditions(policy?.conditions ? JSON.stringify(policy.conditions, null, 2) : '');
    setEnabled(policy?.enabled ?? true);
    setFormError(null);
  }, [isOpen, policy]);

  const submit = async () => {
    try {
      if (!policyId.trim()) throw new Error('Policy ID is required');
      let parsedConditions: Record<string, unknown> | undefined;
      if (conditions.trim()) {
        const parsed = JSON.parse(conditions) as unknown;
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
          throw new Error('Conditions must be a JSON object');
        }
        parsedConditions = parsed as Record<string, unknown>;
      }

      const payload = {
        policy_id: policyId.trim(),
        version: version.trim() || '1.0.0',
        priority: Number(priority) || 100,
        scope: {
          actor_type: actorType,
          action: action.trim() || '*',
          resource_type: resourceType.trim() || '*',
        },
        decision,
        reason_code: reasonCode.trim() || 'POLICY_ALLOW',
        regulation: regulation.trim() || undefined,
        description: description.trim() || undefined,
        conditions: parsedConditions,
        enabled,
      } satisfies Omit<Policy, 'created_at' | 'updated_at'>;

      if (policy) {
        await updatePolicy.mutateAsync({ policyId: policy.policy_id, updates: payload });
      } else {
        await createPolicy.mutateAsync(payload);
      }
      onClose();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Failed to save policy');
    }
  };

  const saving = createPolicy.isPending || updatePolicy.isPending;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={policy ? `Edit Policy: ${policy.policy_id}` : 'Create Policy'}
      size="xl"
    >
      <div className="space-y-5">
        {formError && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
            {formError}
          </div>
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Policy ID" value={policyId} onChange={(e) => setPolicyId(e.target.value)} disabled={Boolean(policy)} />
          <Input label="Version" value={version} onChange={(e) => setVersion(e.target.value)} />
          <Input label="Priority" type="number" value={priority} onChange={(e) => setPriority(e.target.value)} />
          <Input label="Reason Code" value={reasonCode} onChange={(e) => setReasonCode(e.target.value)} />
          <Select
            label="Actor Type"
            value={actorType}
            onChange={(e) => setActorType(e.target.value as ActorType)}
            options={['AI_AGENT', 'SERVICE', 'HUMAN', 'JOB', 'SYSTEM'].map((value) => ({ value, label: value }))}
          />
          <Select
            label="Decision"
            value={decision}
            onChange={(e) => setDecision(e.target.value as AuthorizationDecision)}
            options={[
              { value: 'ALLOW', label: 'Allow' },
              { value: 'DENY', label: 'Deny' },
              { value: 'QUARANTINE', label: 'Quarantine' },
            ]}
          />
          <Input label="Action" value={action} onChange={(e) => setAction(e.target.value)} />
          <Input label="Resource Type" value={resourceType} onChange={(e) => setResourceType(e.target.value)} />
          <Input label="Regulation" value={regulation} onChange={(e) => setRegulation(e.target.value)} placeholder="HIPAA, SOX, GDPR" />
          <label className="flex items-center gap-3 self-end rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium">
            <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} className="h-4 w-4 accent-cyan-600" />
            Policy enabled
          </label>
        </div>
        <Textarea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} placeholder="Explain the control intent and operator response." />
        <Textarea label="Conditions (JSON object, optional)" value={conditions} onChange={(e) => setConditions(e.target.value)} rows={6} placeholder={'{\n  "env": "prod"\n}'} className="font-mono text-xs" />
      </div>
      <ModalFooter>
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button onClick={submit} loading={saving}>{policy ? 'Save Changes' : 'Create Policy'}</Button>
      </ModalFooter>
    </Modal>
  );
}
