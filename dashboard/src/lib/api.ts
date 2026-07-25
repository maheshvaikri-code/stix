/**
 * STIX Dashboard - API Client
 */

import type {
  FabricAgent,
  FabricCollection,
  FabricEnforcementPoint,
  FabricGraphSummary,
  FabricInventory,
  FabricPolicyChannel,
  FabricRegistryStats,
  FabricReadinessReport,
  FabricToolAction,
} from '@stix/fabric-types';

// =============================================================================
// CONFIGURATION
// =============================================================================

export const API_CONFIG = {
  enforcer: process.env.NEXT_PUBLIC_ENFORCER_URL || 'http://localhost:3001',
  policy: process.env.NEXT_PUBLIC_POLICY_URL || 'http://localhost:3002',
  evidence: process.env.NEXT_PUBLIC_EVIDENCE_URL || 'http://localhost:3003',
  approvals: process.env.NEXT_PUBLIC_APPROVALS_URL || 'http://localhost:3004',
  fabric: process.env.NEXT_PUBLIC_FABRIC_URL || 'http://localhost:3005',
};

export type ApiService = keyof typeof API_CONFIG;

// =============================================================================
// TYPES
// =============================================================================

export interface ServiceHealth {
  name: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  uptime_ms: number;
  version: string;
  checks?: Record<string, { status: string; latency_ms: number }>;
}

interface RawServiceHealth {
  name?: string;
  service?: string;
  status?: 'healthy' | 'degraded' | 'unhealthy';
  uptime?: number;
  uptime_ms?: number;
  version?: string;
  checks?: Record<string, { status: string; latency_ms: number }>;
}

export interface Policy {
  policy_id: string;
  version: string;
  priority: number;
  scope: {
    actor_type: string;
    action: string;
    resource_type: string;
  };
  conditions?: Record<string, unknown>;
  decision: 'ALLOW' | 'DENY' | 'QUARANTINE';
  reason_code: string;
  regulation?: string;
  description?: string;
  created_at: string;
  updated_at: string;
  enabled: boolean;
}

export interface EvidenceRecord {
  event_id: string;
  trace_id: string;
  timestamp: string;
  decision: 'ALLOW' | 'DENY' | 'QUARANTINE';
  actor_id: string;
  actor_type: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  policy_id: string;
  reason_code: string;
  request_hash: string;
  chain_hash: string;
  metadata?: Record<string, unknown>;
}

export interface ApprovalRequest {
  request_id: string;
  trace_id: string;
  actor_id: string;
  actor_type: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  reason_code: string;
  context: Record<string, unknown>;
  created_at: string;
  expires_at: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';
  reviewed_by?: string;
  reviewed_at?: string;
  review_notes?: string;
}

export interface DashboardStats {
  decisions: {
    total: number;
    allowed: number;
    denied: number;
    quarantined: number;
    last_24h: number;
    trend: number; // Percentage change from previous period
  };
  approvals: {
    pending: number;
    approved_today: number;
    rejected_today: number;
    avg_response_time_ms: number;
  };
  policies: {
    total: number;
    active: number;
    by_regulation: Record<string, number>;
    by_decision: Record<string, number>;
  };
  evidence: {
    total_records: number;
    today: number;
    chain_valid: boolean;
    last_verified: string;
  };
  degraded_services?: DashboardStatsSourceStatus[];
}

export interface DashboardStatsSourceStatus {
  service: Extract<ApiService, 'enforcer' | 'policy' | 'evidence' | 'approvals'>;
  message: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface TimeSeriesPoint {
  timestamp: string;
  value: number;
}

export interface DecisionTimeSeries {
  allowed: TimeSeriesPoint[];
  denied: TimeSeriesPoint[];
  quarantined: TimeSeriesPoint[];
}

export type {
  FabricAgent,
  FabricEnforcementPoint,
  FabricGraphSummary,
  FabricInventory,
  FabricPolicyChannel,
  FabricRegistryStats,
  FabricReadinessReport,
  FabricToolAction,
};

const EMPTY_DASHBOARD_STATS: Omit<DashboardStats, 'degraded_services'> = {
  decisions: {
    total: 0,
    allowed: 0,
    denied: 0,
    quarantined: 0,
    last_24h: 0,
    trend: 0,
  },
  approvals: {
    pending: 0,
    approved_today: 0,
    rejected_today: 0,
    avg_response_time_ms: 0,
  },
  policies: {
    total: 0,
    active: 0,
    by_regulation: {},
    by_decision: {},
  },
  evidence: {
    total_records: 0,
    today: 0,
    chain_valid: false,
    last_verified: new Date(0).toISOString(),
  },
};

// =============================================================================
// API CLIENT
// =============================================================================

class ApiClient {
  private apiKey?: string;

  setApiKey(key: string) {
    this.apiKey = key;
  }

  private async fetch<T>(
    service: ApiService,
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_CONFIG[service]}${path}`;
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.apiKey) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${this.apiKey}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`API Error (${response.status}): ${error}`);
    }

    return response.json();
  }

  private async fetchWithFallback<T>(
    service: DashboardStatsSourceStatus['service'],
    path: string,
    fallback: T,
    degradedServices: DashboardStatsSourceStatus[]
  ): Promise<T> {
    try {
      return await this.fetch<T>(service, path);
    } catch (error) {
      degradedServices.push({
        service,
        message: error instanceof Error ? error.message : String(error),
      });
      return fallback;
    }
  }

  // ---------------------------------------------------------------------------
  // Health
  // ---------------------------------------------------------------------------

  async getServiceHealth(service: ApiService): Promise<ServiceHealth> {
    try {
      const health = await this.fetch<RawServiceHealth>(service, '/health');
      return {
        name: health.name ?? health.service ?? service,
        status: health.status ?? 'unhealthy',
        uptime_ms: health.uptime_ms ?? (health.uptime ?? 0) * 1000,
        version: health.version ?? 'unknown',
        checks: health.checks,
      };
    } catch {
      return {
        name: service,
        status: 'unhealthy',
        uptime_ms: 0,
        version: 'unknown',
      };
    }
  }

  async getAllServicesHealth(): Promise<Record<ApiService, ServiceHealth>> {
    const services = Object.keys(API_CONFIG) as ApiService[];
    const results = await Promise.all(
      services.map(async (service) => ({
        service,
        health: await this.getServiceHealth(service),
      }))
    );
    return Object.fromEntries(results.map((r) => [r.service, r.health])) as Record<
      ApiService,
      ServiceHealth
    >;
  }

  // ---------------------------------------------------------------------------
  // Dashboard Stats
  // ---------------------------------------------------------------------------

  async getDashboardStats(): Promise<DashboardStats> {
    const degradedServices: DashboardStatsSourceStatus[] = [];
    const [decisions, approvals, policies, evidence] = await Promise.all([
      this.fetchWithFallback<DashboardStats['decisions']>(
        'enforcer',
        '/api/v1/stats/decisions',
        EMPTY_DASHBOARD_STATS.decisions,
        degradedServices
      ),
      this.fetchWithFallback<DashboardStats['approvals']>(
        'approvals',
        '/api/v1/stats',
        EMPTY_DASHBOARD_STATS.approvals,
        degradedServices
      ),
      this.fetchWithFallback<DashboardStats['policies']>(
        'policy',
        '/api/v1/stats',
        EMPTY_DASHBOARD_STATS.policies,
        degradedServices
      ),
      this.fetchWithFallback<DashboardStats['evidence']>(
        'evidence',
        '/api/v1/stats',
        EMPTY_DASHBOARD_STATS.evidence,
        degradedServices
      ),
    ]);

    return {
      decisions,
      approvals,
      policies,
      evidence,
      degraded_services: degradedServices,
    };
  }

  async getDecisionTimeSeries(
    period: '24h' | '7d' | '30d' = '24h'
  ): Promise<DecisionTimeSeries> {
    return this.fetch<DecisionTimeSeries>('enforcer', `/api/v1/stats/timeseries?period=${period}`);
  }

  // ---------------------------------------------------------------------------
  // Policies
  // ---------------------------------------------------------------------------

  async listPolicies(params: {
    page?: number;
    page_size?: number;
    regulation?: string;
    decision?: string;
    enabled?: boolean;
    search?: string;
  } = {}): Promise<PaginatedResponse<Policy>> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', String(params.page));
    if (params.page_size) searchParams.set('page_size', String(params.page_size));
    if (params.regulation) searchParams.set('regulation', params.regulation);
    if (params.decision) searchParams.set('decision', params.decision);
    if (params.enabled !== undefined) searchParams.set('enabled', String(params.enabled));
    if (params.search) searchParams.set('search', params.search);

    return this.fetch<PaginatedResponse<Policy>>('policy', `/api/v1/policies?${searchParams}`);
  }

  async getPolicy(policyId: string): Promise<Policy> {
    return this.fetch<Policy>('policy', `/api/v1/policies/${policyId}`);
  }

  async createPolicy(policy: Omit<Policy, 'created_at' | 'updated_at'>): Promise<Policy> {
    return this.fetch<Policy>('policy', '/api/v1/policies', {
      method: 'POST',
      body: JSON.stringify(policy),
    });
  }

  async updatePolicy(policyId: string, updates: Partial<Policy>): Promise<Policy> {
    return this.fetch<Policy>('policy', `/api/v1/policies/${policyId}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  }

  async deletePolicy(policyId: string): Promise<void> {
    await this.fetch<void>('policy', `/api/v1/policies/${policyId}`, {
      method: 'DELETE',
    });
  }

  async togglePolicy(policyId: string, enabled: boolean): Promise<Policy> {
    return this.updatePolicy(policyId, { enabled });
  }

  async validatePolicy(policy: unknown): Promise<{ valid: boolean; errors?: string[] }> {
    return this.fetch<{ valid: boolean; errors?: string[] }>('policy', '/api/v1/policies/validate', {
      method: 'POST',
      body: JSON.stringify(policy),
    });
  }

  async simulatePolicy(
    policy: unknown,
    request: {
      actor: { id: string; type: string };
      action: string;
      resource: { type: string };
      context: Record<string, unknown>;
    }
  ): Promise<{ decision: string; matched_policy?: string }> {
    return this.fetch<{ decision: string; matched_policy?: string }>(
      'policy',
      '/api/v1/policies/simulate',
      {
        method: 'POST',
        body: JSON.stringify({ policy, request }),
      }
    );
  }

  // ---------------------------------------------------------------------------
  // Evidence
  // ---------------------------------------------------------------------------

  async queryEvidence(params: {
    page?: number;
    page_size?: number;
    trace_id?: string;
    actor_id?: string;
    action?: string;
    resource_type?: string;
    decision?: string;
    start_time?: string;
    end_time?: string;
  } = {}): Promise<PaginatedResponse<EvidenceRecord>> {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) searchParams.set(key, String(value));
    });

    return this.fetch<PaginatedResponse<EvidenceRecord>>('evidence', `/api/v1/evidence?${searchParams}`);
  }

  async getEvidenceByTrace(traceId: string): Promise<EvidenceRecord[]> {
    return this.fetch<EvidenceRecord[]>('evidence', `/api/v1/evidence/trace/${traceId}`);
  }

  async verifyEvidenceChain(params: {
    start_time?: string;
    end_time?: string;
  } = {}): Promise<{
    valid: boolean;
    records_verified: number;
    errors?: string[];
    first_invalid?: string;
  }> {
    const searchParams = new URLSearchParams();
    if (params.start_time) searchParams.set('start_time', params.start_time);
    if (params.end_time) searchParams.set('end_time', params.end_time);

    return this.fetch('evidence', `/api/v1/evidence/verify?${searchParams}`);
  }

  async getEvidenceStats(params: {
    start_time?: string;
    end_time?: string;
  } = {}): Promise<{
    total: number;
    by_decision: Record<string, number>;
    by_actor_type: Record<string, number>;
    by_action: Record<string, number>;
    unique_actors: number;
    unique_traces: number;
  }> {
    const searchParams = new URLSearchParams();
    if (params.start_time) searchParams.set('start_time', params.start_time);
    if (params.end_time) searchParams.set('end_time', params.end_time);

    return this.fetch('evidence', `/api/v1/evidence/stats?${searchParams}`);
  }

  async exportEvidence(params: {
    start_time?: string;
    end_time?: string;
    format?: 'json' | 'jsonl' | 'csv';
  }): Promise<Blob> {
    const searchParams = new URLSearchParams();
    if (params.start_time) searchParams.set('start_time', params.start_time);
    if (params.end_time) searchParams.set('end_time', params.end_time);
    if (params.format) searchParams.set('format', params.format);

    const response = await fetch(
      `${API_CONFIG.evidence}/api/v1/evidence/export?${searchParams}`,
      {
        headers: this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {},
      }
    );

    if (!response.ok) {
      throw new Error(`Export failed: ${response.status}`);
    }

    return response.blob();
  }

  // ---------------------------------------------------------------------------
  // Approvals
  // ---------------------------------------------------------------------------

  async listApprovals(params: {
    page?: number;
    page_size?: number;
    status?: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';
    actor_id?: string;
    action?: string;
  } = {}): Promise<PaginatedResponse<ApprovalRequest>> {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) searchParams.set(key, String(value));
    });

    return this.fetch<PaginatedResponse<ApprovalRequest>>('approvals', `/api/v1/approvals?${searchParams}`);
  }

  async getApproval(requestId: string): Promise<ApprovalRequest> {
    return this.fetch<ApprovalRequest>('approvals', `/api/v1/approvals/${requestId}`);
  }

  async approveRequest(
    requestId: string,
    notes?: string
  ): Promise<ApprovalRequest> {
    return this.fetch<ApprovalRequest>('approvals', `/api/v1/approvals/${requestId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
  }

  async rejectRequest(
    requestId: string,
    notes?: string
  ): Promise<ApprovalRequest> {
    return this.fetch<ApprovalRequest>('approvals', `/api/v1/approvals/${requestId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
  }

  async getApprovalsByTrace(traceId: string): Promise<ApprovalRequest[]> {
    return this.fetch<ApprovalRequest[]>('approvals', `/api/v1/approvals/trace/${traceId}`);
  }

  // ---------------------------------------------------------------------------
  // STIX Fabric
  // ---------------------------------------------------------------------------

  async listFabricAgents(): Promise<FabricCollection<FabricAgent>> {
    return this.fetch<FabricCollection<FabricAgent>>('fabric', '/api/v1/fabric/agents');
  }

  async listFabricEnforcementPoints(): Promise<FabricCollection<FabricEnforcementPoint>> {
    return this.fetch<FabricCollection<FabricEnforcementPoint>>(
      'fabric',
      '/api/v1/fabric/enforcement-points'
    );
  }

  async listFabricToolActions(): Promise<FabricCollection<FabricToolAction>> {
    return this.fetch<FabricCollection<FabricToolAction>>('fabric', '/api/v1/fabric/tool-actions');
  }

  async listFabricPolicyChannels(): Promise<FabricCollection<FabricPolicyChannel>> {
    return this.fetch<FabricCollection<FabricPolicyChannel>>(
      'fabric',
      '/api/v1/fabric/policy-channels'
    );
  }

  async getFabricStats(): Promise<FabricRegistryStats> {
    return this.fetch<FabricRegistryStats>('fabric', '/api/v1/fabric/stats');
  }

  async getFabricGraphSummary(): Promise<FabricGraphSummary> {
    return this.fetch<FabricGraphSummary>('fabric', '/api/v1/fabric/graph/summary');
  }

  async getFabricReadiness(): Promise<FabricReadinessReport> {
    return this.fetch<FabricReadinessReport>('fabric', '/api/v1/fabric/readiness');
  }

  async getFabricInventory(): Promise<FabricInventory> {
    const [agents, enforcementPoints, toolActions, policyChannels, stats, graph] = await Promise.all([
      this.listFabricAgents(),
      this.listFabricEnforcementPoints(),
      this.listFabricToolActions(),
      this.listFabricPolicyChannels(),
      this.getFabricStats(),
      this.getFabricGraphSummary(),
    ]);

    return {
      agents,
      enforcementPoints,
      toolActions,
      policyChannels,
      stats,
      graph,
    };
  }
}

// =============================================================================
// EXPORTS
// =============================================================================

export const api = new ApiClient();

export default api;
