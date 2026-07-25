/**
 * STIX Dashboard - React Query Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type ApiService, type Policy, type EvidenceRecord, type ApprovalRequest } from './api';

// =============================================================================
// QUERY KEYS
// =============================================================================

export const queryKeys = {
  health: (service: string) => ['health', service] as const,
  allHealth: ['health', 'all'] as const,
  dashboardStats: ['dashboard', 'stats'] as const,
  decisionTimeSeries: (period: string) => ['dashboard', 'timeseries', period] as const,

  policies: (params: Record<string, unknown>) => ['policies', params] as const,
  policy: (id: string) => ['policies', 'detail', id] as const,

  evidence: (params: Record<string, unknown>) => ['evidence', params] as const,
  evidenceByTrace: (traceId: string) => ['evidence', 'trace', traceId] as const,
  evidenceStats: (params: Record<string, unknown>) => ['evidence', 'stats', params] as const,
  evidenceChainVerify: (params: Record<string, unknown>) => ['evidence', 'verify', params] as const,

  approvals: (params: Record<string, unknown>) => ['approvals', params] as const,
  approval: (id: string) => ['approvals', 'detail', id] as const,
  approvalsByTrace: (traceId: string) => ['approvals', 'trace', traceId] as const,

  fabricInventory: ['fabric', 'inventory'] as const,
  fabricReadiness: ['fabric', 'readiness'] as const,
  fabricStats: ['fabric', 'stats'] as const,
  fabricGraph: ['fabric', 'graph', 'summary'] as const,
  fabricAgents: ['fabric', 'agents'] as const,
  fabricEnforcementPoints: ['fabric', 'enforcement-points'] as const,
  fabricToolActions: ['fabric', 'tool-actions'] as const,
  fabricPolicyChannels: ['fabric', 'policy-channels'] as const,
};

// =============================================================================
// HEALTH HOOKS
// =============================================================================

export function useServiceHealth(service: string) {
  return useQuery({
    queryKey: queryKeys.health(service),
    queryFn: () => api.getServiceHealth(service as ApiService),
    refetchInterval: 30000,
    staleTime: 10000,
  });
}

export function useAllServicesHealth() {
  return useQuery({
    queryKey: queryKeys.allHealth,
    queryFn: () => api.getAllServicesHealth(),
    refetchInterval: 30000,
    staleTime: 10000,
  });
}

// =============================================================================
// DASHBOARD HOOKS
// =============================================================================

export function useDashboardStats() {
  return useQuery({
    queryKey: queryKeys.dashboardStats,
    queryFn: () => api.getDashboardStats(),
    refetchInterval: 60000,
    staleTime: 30000,
  });
}

export function useDecisionTimeSeries(period: '24h' | '7d' | '30d' = '24h') {
  return useQuery({
    queryKey: queryKeys.decisionTimeSeries(period),
    queryFn: () => api.getDecisionTimeSeries(period),
    refetchInterval: 60000,
    staleTime: 30000,
  });
}

// =============================================================================
// POLICY HOOKS
// =============================================================================

export function usePolicies(params: {
  page?: number;
  page_size?: number;
  regulation?: string;
  decision?: string;
  enabled?: boolean;
  search?: string;
} = {}) {
  return useQuery({
    queryKey: queryKeys.policies(params),
    queryFn: () => api.listPolicies(params),
    staleTime: 30000,
  });
}

export function usePolicy(policyId: string) {
  return useQuery({
    queryKey: queryKeys.policy(policyId),
    queryFn: () => api.getPolicy(policyId),
    enabled: !!policyId,
  });
}

export function useCreatePolicy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (policy: Omit<Policy, 'created_at' | 'updated_at'>) =>
      api.createPolicy(policy),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] });
    },
  });
}

export function useUpdatePolicy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ policyId, updates }: { policyId: string; updates: Partial<Policy> }) =>
      api.updatePolicy(policyId, updates),
    onSuccess: (_, { policyId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.policy(policyId) });
      queryClient.invalidateQueries({ queryKey: ['policies'] });
    },
  });
}

export function useDeletePolicy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (policyId: string) => api.deletePolicy(policyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] });
    },
  });
}

export function useTogglePolicy() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ policyId, enabled }: { policyId: string; enabled: boolean }) =>
      api.togglePolicy(policyId, enabled),
    onSuccess: (_, { policyId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.policy(policyId) });
      queryClient.invalidateQueries({ queryKey: ['policies'] });
    },
  });
}

export function useValidatePolicy() {
  return useMutation({
    mutationFn: (policy: unknown) => api.validatePolicy(policy),
  });
}

export function useSimulatePolicy() {
  return useMutation({
    mutationFn: ({
      policy,
      request,
    }: {
      policy: unknown;
      request: {
        actor: { id: string; type: string };
        action: string;
        resource: { type: string };
        context: Record<string, unknown>;
      };
    }) => api.simulatePolicy(policy, request),
  });
}

// =============================================================================
// EVIDENCE HOOKS
// =============================================================================

export function useEvidence(params: {
  page?: number;
  page_size?: number;
  trace_id?: string;
  actor_id?: string;
  action?: string;
  resource_type?: string;
  decision?: string;
  start_time?: string;
  end_time?: string;
} = {}) {
  return useQuery({
    queryKey: queryKeys.evidence(params),
    queryFn: () => api.queryEvidence(params),
    staleTime: 30000,
  });
}

export function useEvidenceByTrace(traceId: string) {
  return useQuery({
    queryKey: queryKeys.evidenceByTrace(traceId),
    queryFn: () => api.getEvidenceByTrace(traceId),
    enabled: !!traceId,
  });
}

export function useEvidenceStats(params: {
  start_time?: string;
  end_time?: string;
} = {}) {
  return useQuery({
    queryKey: queryKeys.evidenceStats(params),
    queryFn: () => api.getEvidenceStats(params),
    staleTime: 60000,
  });
}

export function useVerifyEvidenceChain(params: {
  start_time?: string;
  end_time?: string;
} = {}) {
  return useQuery({
    queryKey: queryKeys.evidenceChainVerify(params),
    queryFn: () => api.verifyEvidenceChain(params),
    staleTime: 300000, // 5 minutes - verification is expensive
  });
}

export function useExportEvidence() {
  return useMutation({
    mutationFn: (params: {
      start_time?: string;
      end_time?: string;
      format?: 'json' | 'jsonl' | 'csv';
    }) => api.exportEvidence(params),
  });
}

// =============================================================================
// APPROVAL HOOKS
// =============================================================================

export function useApprovals(params: {
  page?: number;
  page_size?: number;
  status?: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';
  actor_id?: string;
  action?: string;
} = {}) {
  return useQuery({
    queryKey: queryKeys.approvals(params),
    queryFn: () => api.listApprovals(params),
    staleTime: 10000, // Refresh more often for pending approvals
    refetchInterval: params.status === 'PENDING' ? 10000 : 30000,
  });
}

export function useApproval(requestId: string) {
  return useQuery({
    queryKey: queryKeys.approval(requestId),
    queryFn: () => api.getApproval(requestId),
    enabled: !!requestId,
  });
}

export function useApprovalsByTrace(traceId: string) {
  return useQuery({
    queryKey: queryKeys.approvalsByTrace(traceId),
    queryFn: () => api.getApprovalsByTrace(traceId),
    enabled: !!traceId,
  });
}

export function useApproveRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ requestId, notes }: { requestId: string; notes?: string }) =>
      api.approveRequest(requestId, notes),
    onSuccess: (_, { requestId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.approval(requestId) });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats });
    },
  });
}

export function useRejectRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ requestId, notes }: { requestId: string; notes?: string }) =>
      api.rejectRequest(requestId, notes),
    onSuccess: (_, { requestId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.approval(requestId) });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats });
    },
  });
}

// =============================================================================
// FABRIC HOOKS
// =============================================================================

export function useFabricInventory() {
  return useQuery({
    queryKey: queryKeys.fabricInventory,
    queryFn: () => api.getFabricInventory(),
    staleTime: 30000,
    refetchInterval: 60000,
  });
}

export function useFabricReadiness() {
  return useQuery({
    queryKey: queryKeys.fabricReadiness,
    queryFn: () => api.getFabricReadiness(),
    staleTime: 30000,
    refetchInterval: 60000,
  });
}

export function useFabricStats() {
  return useQuery({
    queryKey: queryKeys.fabricStats,
    queryFn: () => api.getFabricStats(),
    staleTime: 30000,
    refetchInterval: 60000,
  });
}

export function useFabricGraphSummary() {
  return useQuery({
    queryKey: queryKeys.fabricGraph,
    queryFn: () => api.getFabricGraphSummary(),
    staleTime: 30000,
    refetchInterval: 60000,
  });
}

export function useFabricAgents() {
  return useQuery({
    queryKey: queryKeys.fabricAgents,
    queryFn: () => api.listFabricAgents(),
    staleTime: 30000,
  });
}

export function useFabricEnforcementPoints() {
  return useQuery({
    queryKey: queryKeys.fabricEnforcementPoints,
    queryFn: () => api.listFabricEnforcementPoints(),
    staleTime: 30000,
  });
}

export function useFabricToolActions() {
  return useQuery({
    queryKey: queryKeys.fabricToolActions,
    queryFn: () => api.listFabricToolActions(),
    staleTime: 30000,
  });
}

export function useFabricPolicyChannels() {
  return useQuery({
    queryKey: queryKeys.fabricPolicyChannels,
    queryFn: () => api.listFabricPolicyChannels(),
    staleTime: 30000,
  });
}
