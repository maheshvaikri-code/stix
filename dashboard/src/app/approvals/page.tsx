'use client';

import { useState } from 'react';
import {
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  User,
  MessageSquare,
  History,
  Filter,
} from 'lucide-react';
import {
  useApprovals,
  useApproval,
  useApproveRequest,
  useRejectRequest,
} from '@/lib/hooks';
import { type ApprovalRequest } from '@/lib/api';
import { Card, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input, Textarea } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge, StatusBadge, DecisionBadge } from '@/components/ui/badge';
import { Table, TableHead, TableBody, TableRow, TableHeader, TableCell } from '@/components/ui/table';
import { Pagination } from '@/components/ui/pagination';
import { Modal, ModalFooter } from '@/components/ui/modal';
import { EmptyState } from '@/components/ui/empty-state';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { Tabs, TabPanel } from '@/components/ui/tabs';
import { JsonViewer } from '@/components/ui/code-block';

// =============================================================================
// APPROVALS PAGE
// =============================================================================

export default function ApprovalsPage() {
  const [activeTab, setActiveTab] = useState('pending');
  const [page, setPage] = useState(1);
  const [actorId, setActorId] = useState('');
  const [action, setAction] = useState('');
  const [selectedRequest, setSelectedRequest] = useState<ApprovalRequest | null>(null);

  const statusFilter =
    activeTab === 'pending'
      ? 'PENDING'
      : activeTab === 'history'
      ? undefined
      : (activeTab.toUpperCase() as 'APPROVED' | 'REJECTED');

  const { data, isLoading, refetch } = useApprovals({
    page,
    page_size: 20,
    status: statusFilter as 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED' | undefined,
    actor_id: actorId || undefined,
    action: action || undefined,
  });

  // Count pending for badge
  const { data: pendingData } = useApprovals({ status: 'PENDING', page_size: 1 });
  const pendingCount = pendingData?.total || 0;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Approvals</h1>
          <p className="text-sm text-gray-500 mt-1">
            Human-in-the-loop approval workflow for quarantined actions
          </p>
        </div>
        {pendingCount > 0 && (
          <div className="flex items-center gap-2 bg-yellow-50 text-yellow-800 px-4 py-2 rounded-lg">
            <AlertTriangle className="h-5 w-5" />
            <span className="font-medium">{pendingCount} pending approvals</span>
          </div>
        )}
      </div>

      {/* Tabs */}
      <Tabs
        tabs={[
          {
            id: 'pending',
            label: `Pending${pendingCount > 0 ? ` (${pendingCount})` : ''}`,
            icon: <Clock className="h-4 w-4" />,
          },
          { id: 'approved', label: 'Approved', icon: <CheckCircle className="h-4 w-4" /> },
          { id: 'rejected', label: 'Rejected', icon: <XCircle className="h-4 w-4" /> },
          { id: 'history', label: 'All History', icon: <History className="h-4 w-4" /> },
        ]}
        activeTab={activeTab}
        onChange={(tab) => {
          setActiveTab(tab);
          setPage(1);
        }}
      />

      {/* Filters */}
      <Card>
        <div className="flex items-center gap-4">
          <Input
            placeholder="Actor ID"
            value={actorId}
            onChange={(e) => setActorId(e.target.value)}
            className="w-48"
          />
          <Input
            placeholder="Action"
            value={action}
            onChange={(e) => setAction(e.target.value)}
            className="w-48"
          />
          <Button variant="secondary" onClick={() => refetch()}>
            <Filter className="h-4 w-4 mr-2" />
            Apply Filters
          </Button>
        </div>
      </Card>

      {/* Approvals Table/Cards */}
      {activeTab === 'pending' ? (
        <PendingApprovalsList
          approvals={data?.data || []}
          isLoading={isLoading}
          onSelect={setSelectedRequest}
          onAction={refetch}
        />
      ) : (
        <Card padding="none">
          {isLoading ? (
            <div className="py-12">
              <LoadingSpinner />
            </div>
          ) : !data?.data.length ? (
            <EmptyState
              icon={<CheckCircle className="h-12 w-12" />}
              title={`No ${activeTab} approvals`}
              description={
                activeTab === 'history'
                  ? 'No approval requests have been processed yet.'
                  : `No ${activeTab} requests in this time period.`
              }
            />
          ) : (
            <>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeader>Request ID</TableHeader>
                    <TableHeader>Actor</TableHeader>
                    <TableHeader>Action</TableHeader>
                    <TableHeader>Resource</TableHeader>
                    <TableHeader>Status</TableHeader>
                    <TableHeader>Created</TableHeader>
                    <TableHeader>Reviewed</TableHeader>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.data.map((approval) => (
                    <TableRow
                      key={approval.request_id}
                      clickable
                      onClick={() => setSelectedRequest(approval)}
                    >
                      <TableCell>
                        <span className="font-mono text-xs">
                          {approval.request_id.substring(0, 12)}...
                        </span>
                      </TableCell>
                      <TableCell>
                        <div>
                          <p className="font-medium text-sm">{approval.actor_id}</p>
                          <p className="text-xs text-gray-500">{approval.actor_type}</p>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {approval.action}
                      </TableCell>
                      <TableCell>
                        <div>
                          <p className="text-sm">{approval.resource_type}</p>
                          {approval.resource_id && (
                            <p className="text-xs text-gray-500">{approval.resource_id}</p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={approval.status} />
                      </TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {new Date(approval.created_at).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {approval.reviewed_at
                          ? new Date(approval.reviewed_at).toLocaleString()
                          : '-'}
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
      )}

      {/* Approval Detail Modal */}
      <Modal
        isOpen={!!selectedRequest}
        onClose={() => setSelectedRequest(null)}
        title="Approval Request"
        size="lg"
      >
        {selectedRequest && (
          <ApprovalDetail
            approval={selectedRequest}
            onClose={() => setSelectedRequest(null)}
            onAction={refetch}
          />
        )}
      </Modal>
    </div>
  );
}

// =============================================================================
// PENDING APPROVALS LIST (CARD VIEW)
// =============================================================================

function PendingApprovalsList({
  approvals,
  isLoading,
  onSelect,
  onAction,
}: {
  approvals: ApprovalRequest[];
  isLoading: boolean;
  onSelect: (approval: ApprovalRequest) => void;
  onAction: () => void;
}) {
  const approveRequest = useApproveRequest();
  const rejectRequest = useRejectRequest();

  if (isLoading) {
    return (
      <div className="py-12">
        <LoadingSpinner />
      </div>
    );
  }

  if (!approvals.length) {
    return (
      <Card>
        <EmptyState
          icon={<CheckCircle className="h-12 w-12 text-green-500" />}
          title="No pending approvals"
          description="All approval requests have been processed. Check back later or view the history tab."
        />
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {approvals.map((approval) => {
        const expiresIn = new Date(approval.expires_at).getTime() - Date.now();
        const expiresHours = Math.floor(expiresIn / (1000 * 60 * 60));
        const isUrgent = expiresHours < 4;

        return (
          <Card key={approval.request_id} className="hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-3">
                  <Badge variant={isUrgent ? 'warning' : 'info'}>
                    <Clock className="h-3 w-3 mr-1" />
                    Expires in {expiresHours}h
                  </Badge>
                  <span className="font-mono text-xs text-gray-500">
                    {approval.request_id}
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div>
                    <p className="text-xs text-gray-500">Actor</p>
                    <p className="font-medium">{approval.actor_id}</p>
                    <p className="text-xs text-gray-400">{approval.actor_type}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Action</p>
                    <p className="font-mono text-sm">{approval.action}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Resource</p>
                    <p>{approval.resource_type}</p>
                    {approval.resource_id && (
                      <p className="text-xs text-gray-400">{approval.resource_id}</p>
                    )}
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Reason</p>
                    <p className="text-sm">{approval.reason_code}</p>
                  </div>
                </div>

                <button
                  onClick={() => onSelect(approval)}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  View full details →
                </button>
              </div>

              <div className="flex gap-2 ml-4">
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() =>
                    rejectRequest.mutate(
                      { requestId: approval.request_id },
                      { onSuccess: onAction }
                    )
                  }
                  loading={rejectRequest.isPending}
                >
                  <XCircle className="h-4 w-4 mr-1" />
                  Reject
                </Button>
                <Button
                  size="sm"
                  onClick={() =>
                    approveRequest.mutate(
                      { requestId: approval.request_id },
                      { onSuccess: onAction }
                    )
                  }
                  loading={approveRequest.isPending}
                >
                  <CheckCircle className="h-4 w-4 mr-1" />
                  Approve
                </Button>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

// =============================================================================
// APPROVAL DETAIL
// =============================================================================

function ApprovalDetail({
  approval,
  onClose,
  onAction,
}: {
  approval: ApprovalRequest;
  onClose: () => void;
  onAction: () => void;
}) {
  const [notes, setNotes] = useState('');
  const approveRequest = useApproveRequest();
  const rejectRequest = useRejectRequest();

  const isPending = approval.status === 'PENDING';

  const handleApprove = () => {
    approveRequest.mutate(
      { requestId: approval.request_id, notes: notes || undefined },
      {
        onSuccess: () => {
          onAction();
          onClose();
        },
      }
    );
  };

  const handleReject = () => {
    rejectRequest.mutate(
      { requestId: approval.request_id, notes: notes || undefined },
      {
        onSuccess: () => {
          onAction();
          onClose();
        },
      }
    );
  };

  return (
    <div className="space-y-6">
      {/* Status Banner */}
      {!isPending && (
        <div
          className={`p-4 rounded-lg flex items-center gap-3 ${
            approval.status === 'APPROVED'
              ? 'bg-green-50 text-green-800'
              : approval.status === 'REJECTED'
              ? 'bg-red-50 text-red-800'
              : 'bg-gray-50 text-gray-800'
          }`}
        >
          {approval.status === 'APPROVED' ? (
            <CheckCircle className="h-5 w-5" />
          ) : approval.status === 'REJECTED' ? (
            <XCircle className="h-5 w-5" />
          ) : (
            <Clock className="h-5 w-5" />
          )}
          <div>
            <p className="font-medium">{approval.status}</p>
            {approval.reviewed_by && (
              <p className="text-sm">
                by {approval.reviewed_by} on{' '}
                {new Date(approval.reviewed_at!).toLocaleString()}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Request Details */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-gray-500">Request ID</p>
          <p className="font-mono">{approval.request_id}</p>
        </div>
        <div>
          <p className="text-gray-500">Trace ID</p>
          <p className="font-mono">{approval.trace_id}</p>
        </div>
        <div>
          <p className="text-gray-500">Created</p>
          <p>{new Date(approval.created_at).toLocaleString()}</p>
        </div>
        <div>
          <p className="text-gray-500">Expires</p>
          <p>{new Date(approval.expires_at).toLocaleString()}</p>
        </div>
      </div>

      {/* Actor & Action */}
      <div className="p-4 bg-gray-50 rounded-lg">
        <p className="text-sm font-medium mb-3">Request Details</p>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-500 flex items-center gap-1">
              <User className="h-3 w-3" /> Actor
            </p>
            <p className="font-medium">{approval.actor_id}</p>
            <Badge variant="info" size="sm">{approval.actor_type}</Badge>
          </div>
          <div>
            <p className="text-gray-500">Action</p>
            <p className="font-mono">{approval.action}</p>
          </div>
          <div>
            <p className="text-gray-500">Resource</p>
            <p>{approval.resource_type}</p>
            {approval.resource_id && (
              <p className="text-xs text-gray-500">{approval.resource_id}</p>
            )}
          </div>
          <div>
            <p className="text-gray-500">Reason Code</p>
            <p className="font-mono text-sm">{approval.reason_code}</p>
          </div>
        </div>
      </div>

      {/* Context */}
      <div>
        <p className="text-sm font-medium mb-2">Request Context</p>
        <JsonViewer data={approval.context} maxHeight="200px" />
      </div>

      {/* Review Notes */}
      {approval.review_notes && (
        <div>
          <p className="text-sm font-medium mb-2 flex items-center gap-1">
            <MessageSquare className="h-4 w-4" /> Review Notes
          </p>
          <div className="p-3 bg-gray-50 rounded-lg text-sm">
            {approval.review_notes}
          </div>
        </div>
      )}

      {/* Action Section */}
      {isPending && (
        <>
          <div>
            <Textarea
              label="Notes (optional)"
              placeholder="Add notes for this decision..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
            />
          </div>

          <ModalFooter>
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleReject}
              loading={rejectRequest.isPending}
            >
              <XCircle className="h-4 w-4 mr-2" />
              Reject
            </Button>
            <Button onClick={handleApprove} loading={approveRequest.isPending}>
              <CheckCircle className="h-4 w-4 mr-2" />
              Approve
            </Button>
          </ModalFooter>
        </>
      )}
    </div>
  );
}
