'use client';

import { useState } from 'react';
import {
  Database,
  Search,
  Download,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
  Hash,
  Clock,
} from 'lucide-react';
import {
  useEvidence,
  useEvidenceStats,
  useVerifyEvidenceChain,
  useExportEvidence,
  useEvidenceByTrace,
} from '@/lib/hooks';
import { type EvidenceRecord } from '@/lib/api';
import { Card, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge, DecisionBadge, StatusBadge } from '@/components/ui/badge';
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from '@/components/ui/table';
import { Pagination } from '@/components/ui/pagination';
import { Modal, ModalFooter } from '@/components/ui/modal';
import { EmptyState } from '@/components/ui/empty-state';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { DateRangePicker } from '@/components/ui/date-range-picker';
import { JsonViewer } from '@/components/ui/code-block';
import { Tabs, TabPanel } from '@/components/ui/tabs';

// =============================================================================
// EVIDENCE PAGE
// =============================================================================

export default function EvidencePage() {
  const [activeTab, setActiveTab] = useState('records');
  const [page, setPage] = useState(1);
  const [traceId, setTraceId] = useState('');
  const [actorId, setActorId] = useState('');
  const [decision, setDecision] = useState('');
  const [startDate, setStartDate] = useState(
    new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
  );
  const [endDate, setEndDate] = useState(new Date().toISOString());
  const [selectedRecord, setSelectedRecord] = useState<EvidenceRecord | null>(null);
  const [showExportModal, setShowExportModal] = useState(false);

  const { data: evidenceData, isLoading, error: evidenceError, refetch } = useEvidence({
    page,
    page_size: 20,
    trace_id: traceId || undefined,
    actor_id: actorId || undefined,
    decision: decision || undefined,
    start_time: startDate,
    end_time: endDate,
  });

  const { data: stats, error: statsError } = useEvidenceStats({
    start_time: startDate,
    end_time: endDate,
  });

  const { data: chainVerification, isLoading: verifying, error: chainError, refetch: verifyChain } = useVerifyEvidenceChain({
    start_time: startDate,
    end_time: endDate,
  });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Evidence</h1>
          <p className="text-sm text-gray-500 mt-1">
            Immutable audit trail for all authorization decisions
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="secondary" onClick={() => verifyChain()}>
            <RefreshCw className={`h-4 w-4 mr-2 ${verifying ? 'animate-spin' : ''}`} />
            Verify Chain
          </Button>
          <Button variant="secondary" onClick={() => setShowExportModal(true)}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {(evidenceError || statsError || chainError) && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          Evidence is partially unavailable. {([evidenceError, statsError, chainError].find(Boolean) as Error | undefined)?.message ?? 'Retry the request or check the Evidence service.'}
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 rounded-lg">
                <Database className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Records</p>
                <p className="text-xl font-bold">{(stats.total || 0).toLocaleString()}</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-50 rounded-lg">
                <CheckCircle className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Allowed</p>
                <p className="text-xl font-bold">
                  {(stats.by_decision?.ALLOW || 0).toLocaleString()}
                </p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-50 rounded-lg">
                <XCircle className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Denied</p>
                <p className="text-xl font-bold">
                  {(stats.by_decision?.DENY || 0).toLocaleString()}
                </p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <div
                className={`p-2 rounded-lg ${
                  chainVerification?.valid
                    ? 'bg-green-50'
                    : 'bg-red-50'
                }`}
              >
                <Hash
                  className={`h-5 w-5 ${
                    chainVerification?.valid
                      ? 'text-green-600'
                      : 'text-red-600'
                  }`}
                />
              </div>
              <div>
                <p className="text-sm text-gray-500">Chain Status</p>
                <p className="text-xl font-bold">
                  {verifying ? (
                    <LoadingSpinner size="sm" />
                  ) : chainVerification?.valid ? (
                    <span className="text-green-600">Valid</span>
                  ) : (
                    <span className="text-red-600">Invalid</span>
                  )}
                </p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Tabs */}
      <Tabs
        tabs={[
          { id: 'records', label: 'Records', icon: <Database className="h-4 w-4" /> },
          { id: 'analytics', label: 'Analytics', icon: <AlertTriangle className="h-4 w-4" /> },
        ]}
        activeTab={activeTab}
        onChange={setActiveTab}
      />

      <TabPanel active={activeTab === 'records'}>
        {/* Filters */}
        <Card className="mb-6">
          <div className="flex flex-wrap items-center gap-4">
            <Input
              placeholder="Trace ID"
              value={traceId}
              onChange={(e) => setTraceId(e.target.value)}
              className="w-48"
            />
            <Input
              placeholder="Actor ID"
              value={actorId}
              onChange={(e) => setActorId(e.target.value)}
              className="w-48"
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
            <DateRangePicker
              startDate={startDate}
              endDate={endDate}
              onChange={(start, end) => {
                setStartDate(start);
                setEndDate(end);
              }}
            />
            <Button variant="secondary" onClick={() => refetch()}>
              <Search className="h-4 w-4 mr-2" />
              Search
            </Button>
          </div>
        </Card>

        {/* Evidence Table */}
        <Card padding="none">
          {isLoading ? (
            <div className="py-12">
              <LoadingSpinner />
            </div>
          ) : evidenceError ? (
            <EmptyState
              icon={<AlertTriangle className="h-12 w-12 text-amber-500" />}
              title="Evidence records unavailable"
              description={evidenceError instanceof Error ? evidenceError.message : 'Retry the request.'}
            />
          ) : !evidenceData?.data.length ? (
            <EmptyState
              icon={<Database className="h-12 w-12" />}
              title="No evidence records found"
              description="Adjust your filters to find evidence records."
            />
          ) : (
            <>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeader>Timestamp</TableHeader>
                    <TableHeader>Trace ID</TableHeader>
                    <TableHeader>Actor</TableHeader>
                    <TableHeader>Action</TableHeader>
                    <TableHeader>Resource</TableHeader>
                    <TableHeader>Decision</TableHeader>
                    <TableHeader>Policy</TableHeader>
                    <TableHeader>Actions</TableHeader>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {evidenceData.data.map((record) => (
                    <TableRow
                      key={record.event_id}
                      clickable
                      onClick={() => setSelectedRecord(record)}
                    >
                      <TableCell className="text-gray-500">
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(record.timestamp).toLocaleString()}
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                          {record.trace_id.substring(0, 12)}...
                        </span>
                      </TableCell>
                      <TableCell>
                        <div>
                          <p className="font-medium text-sm">{record.actor_id}</p>
                          <p className="text-xs text-gray-500">{record.actor_type}</p>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {record.action}
                      </TableCell>
                      <TableCell>
                        <div>
                          <p className="text-sm">{record.resource_type}</p>
                          {record.resource_id && (
                            <p className="text-xs text-gray-500">{record.resource_id}</p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <DecisionBadge decision={record.decision} />
                      </TableCell>
                      <TableCell>
                        <span className="font-mono text-xs text-gray-600">
                          {record.policy_id}
                        </span>
                      </TableCell>
                      <TableCell>
                        <button className="p-1 hover:bg-gray-100 rounded">
                          <ExternalLink className="h-4 w-4 text-gray-400" />
                        </button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <Pagination
                page={page}
                pageSize={20}
                total={evidenceData.total}
                onPageChange={setPage}
              />
            </>
          )}
        </Card>
      </TabPanel>

      <TabPanel active={activeTab === 'analytics'}>
        <EvidenceAnalytics stats={stats} startDate={startDate} endDate={endDate} />
      </TabPanel>

      {/* Record Detail Modal */}
      <Modal
        isOpen={!!selectedRecord}
        onClose={() => setSelectedRecord(null)}
        title="Evidence Record"
        size="lg"
      >
        {selectedRecord && <EvidenceRecordDetail record={selectedRecord} />}
      </Modal>

      {/* Export Modal */}
      <ExportModal
        isOpen={showExportModal}
        onClose={() => setShowExportModal(false)}
        startDate={startDate}
        endDate={endDate}
      />
    </div>
  );
}

// =============================================================================
// EVIDENCE RECORD DETAIL
// =============================================================================

function EvidenceRecordDetail({ record }: { record: EvidenceRecord }) {
  const { data: relatedRecords, isLoading } = useEvidenceByTrace(record.trace_id);

  return (
    <div className="space-y-6">
      {/* Header Info */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-gray-500">Event ID</p>
          <p className="font-mono">{record.event_id}</p>
        </div>
        <div>
          <p className="text-gray-500">Trace ID</p>
          <p className="font-mono">{record.trace_id}</p>
        </div>
        <div>
          <p className="text-gray-500">Timestamp</p>
          <p>{new Date(record.timestamp).toLocaleString()}</p>
        </div>
        <div>
          <p className="text-gray-500">Decision</p>
          <DecisionBadge decision={record.decision} />
        </div>
      </div>

      {/* Actor & Action */}
      <div className="p-4 bg-gray-50 rounded-lg">
        <p className="text-sm font-medium mb-2">Authorization Request</p>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-500">Actor</p>
            <p className="font-medium">{record.actor_id}</p>
            <Badge variant="info" size="sm">{record.actor_type}</Badge>
          </div>
          <div>
            <p className="text-gray-500">Action</p>
            <p className="font-mono">{record.action}</p>
          </div>
          <div>
            <p className="text-gray-500">Resource</p>
            <p>{record.resource_type}</p>
            {record.resource_id && (
              <p className="text-xs text-gray-500">{record.resource_id}</p>
            )}
          </div>
          <div>
            <p className="text-gray-500">Policy</p>
            <p className="font-mono text-sm">{record.policy_id}</p>
            <p className="text-xs text-gray-500">{record.reason_code}</p>
          </div>
        </div>
      </div>

      {/* Chain Integrity */}
      <div className="p-4 border rounded-lg">
        <p className="text-sm font-medium mb-2 flex items-center gap-2">
          <Hash className="h-4 w-4" />
          Chain Integrity
        </p>
        <div className="space-y-2 text-sm">
          <div>
            <p className="text-gray-500">Request Hash</p>
            <p className="font-mono text-xs break-all bg-gray-50 p-2 rounded">
              {record.request_hash}
            </p>
          </div>
          <div>
            <p className="text-gray-500">Chain Hash</p>
            <p className="font-mono text-xs break-all bg-gray-50 p-2 rounded">
              {record.chain_hash}
            </p>
          </div>
        </div>
      </div>

      {/* Metadata */}
      {record.metadata && (
        <div>
          <p className="text-sm font-medium mb-2">Metadata</p>
          <JsonViewer data={record.metadata} maxHeight="200px" />
        </div>
      )}

      {/* Related Records in Trace */}
      <div>
        <p className="text-sm font-medium mb-2">Related Records in Trace</p>
        {isLoading ? (
          <LoadingSpinner size="sm" />
        ) : relatedRecords && relatedRecords.length > 1 ? (
          <div className="space-y-2">
            {relatedRecords.map((r) => (
              <div
                key={r.event_id}
                className={`p-2 text-sm rounded flex items-center justify-between ${
                  r.event_id === record.event_id ? 'bg-blue-50 border border-blue-200' : 'bg-gray-50'
                }`}
              >
                <div>
                  <span className="text-gray-500">
                    {new Date(r.timestamp).toLocaleTimeString()}
                  </span>
                  <span className="mx-2">{r.action}</span>
                </div>
                <DecisionBadge decision={r.decision} />
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">No other records in this trace</p>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// EVIDENCE ANALYTICS
// =============================================================================

function EvidenceAnalytics({
  stats,
  startDate,
  endDate,
}: {
  stats?: {
    total: number;
    by_decision: Record<string, number>;
    by_actor_type: Record<string, number>;
    by_action: Record<string, number>;
    unique_actors: number;
    unique_traces: number;
  };
  startDate: string;
  endDate: string;
}) {
  if (!stats) return <LoadingSpinner />;

  // Ensure we have safe defaults
  const byDecision = stats.by_decision || {};
  const byActorType = stats.by_actor_type || {};
  const byAction = stats.by_action || {};
  const total = stats.total || 0;
  const uniqueActors = stats.unique_actors || 0;
  const uniqueTraces = stats.unique_traces || 0;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* By Decision */}
      <Card>
        <CardHeader title="By Decision" />
        <div className="space-y-3">
          {Object.entries(byDecision).length === 0 ? (
            <p className="text-sm text-gray-500">No data available</p>
          ) : Object.entries(byDecision).map(([decision, count]) => {
            const pct = total > 0 ? (count / total) * 100 : 0;
            return (
              <div key={decision}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="flex items-center gap-2">
                    <DecisionBadge decision={decision} />
                  </span>
                  <span>{count.toLocaleString()} ({pct.toFixed(1)}%)</span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      decision === 'ALLOW'
                        ? 'bg-green-500'
                        : decision === 'DENY'
                        ? 'bg-red-500'
                        : 'bg-yellow-500'
                    }`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* By Actor Type */}
      <Card>
        <CardHeader title="By Actor Type" />
        <div className="space-y-3">
          {Object.entries(byActorType).length === 0 ? (
            <p className="text-sm text-gray-500">No data available</p>
          ) : Object.entries(byActorType).map(([type, count]) => {
            const pct = total > 0 ? (count / total) * 100 : 0;
            return (
              <div key={type}>
                <div className="flex justify-between text-sm mb-1">
                  <span>{type}</span>
                  <span>{count.toLocaleString()} ({pct.toFixed(1)}%)</span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Top Actions */}
      <Card>
        <CardHeader title="Top Actions" />
        <div className="space-y-2">
          {Object.entries(byAction).length === 0 ? (
            <p className="text-sm text-gray-500">No data available</p>
          ) : Object.entries(byAction)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 10)
            .map(([action, count]) => (
              <div key={action} className="flex justify-between text-sm">
                <span className="font-mono">{action}</span>
                <span className="text-gray-500">{count.toLocaleString()}</span>
              </div>
            ))}
        </div>
      </Card>

      {/* Summary Stats */}
      <Card>
        <CardHeader title="Summary" />
        <div className="space-y-4">
          <div className="flex justify-between">
            <span className="text-gray-500">Unique Actors</span>
            <span className="font-bold">{uniqueActors.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Unique Traces</span>
            <span className="font-bold">{uniqueTraces.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Total Records</span>
            <span className="font-bold">{total.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Time Period</span>
            <span className="text-sm">
              {new Date(startDate).toLocaleDateString()} -{' '}
              {new Date(endDate).toLocaleDateString()}
            </span>
          </div>
        </div>
      </Card>
    </div>
  );
}

// =============================================================================
// EXPORT MODAL
// =============================================================================

function ExportModal({
  isOpen,
  onClose,
  startDate,
  endDate,
}: {
  isOpen: boolean;
  onClose: () => void;
  startDate: string;
  endDate: string;
}) {
  const [format, setFormat] = useState<'json' | 'jsonl' | 'csv'>('jsonl');
  const exportEvidence = useExportEvidence();

  const handleExport = async () => {
    const blob = await exportEvidence.mutateAsync({
      start_time: startDate,
      end_time: endDate,
      format,
    });

    // Download the file
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `evidence-export-${new Date().toISOString().slice(0, 10)}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Export Evidence" size="sm">
      <div className="space-y-4">
        <p className="text-sm text-gray-500">
          Export evidence records for compliance or analysis.
        </p>

        <div>
          <p className="text-sm font-medium mb-2">Time Range</p>
          <p className="text-sm text-gray-600">
            {new Date(startDate).toLocaleString()} -{' '}
            {new Date(endDate).toLocaleString()}
          </p>
        </div>

        <Select
          label="Format"
          value={format}
          onChange={(e) => setFormat(e.target.value as 'json' | 'jsonl' | 'csv')}
          options={[
            { value: 'jsonl', label: 'JSON Lines (.jsonl)' },
            { value: 'json', label: 'JSON (.json)' },
            { value: 'csv', label: 'CSV (.csv)' },
          ]}
        />
      </div>

      <ModalFooter>
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={handleExport} loading={exportEvidence.isPending}>
          <Download className="h-4 w-4 mr-2" />
          Export
        </Button>
      </ModalFooter>
    </Modal>
  );
}
