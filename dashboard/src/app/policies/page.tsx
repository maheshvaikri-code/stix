'use client';

import { useState } from 'react';
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
import { usePolicies, useTogglePolicy, useDeletePolicy } from '@/lib/hooks';
import { type Policy } from '@/lib/api';
import { Card, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
  const [showSimulator, setShowSimulator] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<string | null>(null);

  const { data, isLoading, error } = usePolicies({
    page,
    page_size: 20,
    search: search || undefined,
    regulation: regulation || undefined,
    decision: decision || undefined,
  });

  const togglePolicy = useTogglePolicy();
  const deletePolicy = useDeletePolicy();

  const handleToggle = (policyId: string, currentEnabled: boolean) => {
    togglePolicy.mutate({ policyId, enabled: !currentEnabled });
  };

  const handleDelete = (policyId: string) => {
    deletePolicy.mutate(policyId, {
      onSuccess: () => setShowDeleteConfirm(null),
    });
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
          <Button variant="secondary">
            <Upload className="h-4 w-4 mr-2" />
            Import
          </Button>
          <Button variant="secondary">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button>
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
                        <button className="p-1 hover:bg-gray-100 rounded">
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

function PolicySimulator({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [actorId, setActorId] = useState('test-agent');
  const [actorType, setActorType] = useState('AI_AGENT');
  const [action, setAction] = useState('send_email');
  const [resourceType, setResourceType] = useState('email');
  const [env, setEnv] = useState('prod');
  const [result, setResult] = useState<{ decision: string; reason_code?: string; policy?: { id: string } } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:3001/api/v1/authorize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          actor: { id: actorId, type: actorType },
          action,
          resource: { type: resourceType },
          context: { env },
        }),
      });
      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Policy Simulator" size="lg">
      <div className="space-y-4">
        <p className="text-sm text-gray-500">
          Test how policies would evaluate an authorization request.
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
            onChange={(e) => setActorType(e.target.value)}
            options={[
              { value: 'AI_AGENT', label: 'AI Agent' },
              { value: 'SERVICE', label: 'Service' },
              { value: 'USER', label: 'User' },
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
            onChange={(e) => setEnv(e.target.value)}
            options={[
              { value: 'production', label: 'Production' },
              { value: 'staging', label: 'Staging' },
              { value: 'development', label: 'Development' },
              { value: 'test', label: 'Test' },
            ]}
          />
        </div>

        {error && (
          <div className="p-4 rounded-lg bg-red-50 border border-red-200">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {result && (
          <div className="p-4 rounded-lg bg-gray-50 border">
            <p className="text-sm font-medium mb-2">Simulation Result</p>
            <div className="flex items-center gap-4">
              <div>
                <span className="text-gray-500 text-sm">Decision:</span>{' '}
                <DecisionBadge decision={result.decision} />
              </div>
              {result.reason_code && (
                <div>
                  <span className="text-gray-500 text-sm">Reason:</span>{' '}
                  <span className="font-mono text-sm">{result.reason_code}</span>
                </div>
              )}
              {result.policy?.id && (
                <div>
                  <span className="text-gray-500 text-sm">Policy:</span>{' '}
                  <span className="font-mono text-sm">{result.policy.id}</span>
                </div>
              )}
            </div>
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
