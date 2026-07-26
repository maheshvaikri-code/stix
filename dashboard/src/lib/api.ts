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
  required_role?: string;
  require_justification?: boolean;
  security_binding?: {
    request_hash: string;
    arguments_hash: string;
    action_id: string;
    actor_id: string;
    actor_type: string;
    actor_role?: string;
    actor_tenant?: string;
    action: string;
    resource_type: string;
    resource_id?: string;
  };
}

export interface DashboardOperator {
  id: string;
  role: string;
}

export const DEFAULT_DASHBOARD_OPERATOR: DashboardOperator = {
  id: 'dashboard-user',
  role: 'security_admin',
};

export const DASHBOARD_SESSION_KEYS = {
  apiKey: 'stix_api_key',
  operator: 'stix_operator_identity',
} as const;

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

export interface EvidenceStats {
  total: number;
  by_decision: Record<string, number>;
  by_actor_type: Record<string, number>;
  by_action: Record<string, number>;
  unique_actors: number;
  unique_traces: number;
}

export interface EvidenceChainVerification {
  valid: boolean;
  records_verified: number;
  traces_verified?: number;
  errors?: string[];
  first_invalid?: string;
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

export type ActorType = 'HUMAN' | 'SERVICE' | 'AI_AGENT' | 'JOB' | 'SYSTEM';
export type Environment = 'dev' | 'test' | 'stage' | 'prod' | 'production';
export type AuthorizationDecision = 'ALLOW' | 'DENY' | 'QUARANTINE';
export type RiskTier = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface DetectionSignals {
  piiDetected?: boolean;
  phiDetected?: boolean;
  pciDetected?: boolean;
  secretsDetected?: boolean;
  custom?: Record<string, boolean>;
}

export interface AuthorizeActionRequest {
  actor: {
    id: string;
    type: ActorType;
    role?: string;
    tenant?: string;
    attributes?: Record<string, unknown>;
  };
  action: string;
  resource: {
    type: string;
    id?: string;
    classification?: string[];
    attributes?: Record<string, unknown>;
  };
  context: {
    env: Environment;
    purpose?: string;
    run_id?: string;
    session_id?: string;
    ticket_id?: string;
    jurisdiction?: string;
    tags?: string[];
    signals?: DetectionSignals;
    attributes?: Record<string, unknown>;
  };
  tool_call?: {
    tool: string;
    risk_tier?: RiskTier;
    args_summary?: string;
  };
}

export interface AuthorizationResult {
  decision: AuthorizationDecision;
  reason_code?: string;
  trace_id?: string;
  explanation?: string;
  policy_id?: string;
  policy?: { id: string; version: string; hash: string };
  obligations?: Array<{ type: string; params?: Record<string, unknown> }>;
  controls?: string[];
  regulations?: string[];
  proof_token?: string;
  approval?: { required: boolean; ticket_id?: string; approver_role?: string } | null;
  approval_ticket_id?: string;
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
  private operator: DashboardOperator = DEFAULT_DASHBOARD_OPERATOR;

  setApiKey(key?: string) {
    this.apiKey = key?.trim() || undefined;
  }

  setOperatorIdentity(operator: DashboardOperator) {
    this.operator = {
      id: operator.id.trim() || DEFAULT_DASHBOARD_OPERATOR.id,
      role: operator.role.trim() || DEFAULT_DASHBOARD_OPERATOR.role,
    };
  }

  getOperatorIdentity(): DashboardOperator {
    return this.operator;
  }

  restoreSession() {
    if (typeof window === 'undefined') return;

    this.setApiKey(window.localStorage.getItem(DASHBOARD_SESSION_KEYS.apiKey) ?? undefined);

    const rawOperator = window.localStorage.getItem(DASHBOARD_SESSION_KEYS.operator);
    if (!rawOperator) return;

    try {
      const parsed = JSON.parse(rawOperator) as Partial<DashboardOperator>;
      if (typeof parsed.id === 'string' && typeof parsed.role === 'string') {
        this.setOperatorIdentity({ id: parsed.id, role: parsed.role });
      }
    } catch {
      window.localStorage.removeItem(DASHBOARD_SESSION_KEYS.operator);
    }
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

    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 15000);

    let response: Response;
    try {
      response = await fetch(url, {
        ...options,
        headers,
        signal: options.signal ?? controller.signal,
      });
    } finally {
      window.clearTimeout(timeoutId);
    }

    if (!response.ok) {
      const rawError = await response.text();
      let message = rawError;
      try {
        const parsed = JSON.parse(rawError) as {
          error?: { message?: string } | string;
          message?: string;
        };
        message = typeof parsed.error === 'string'
          ? parsed.error
          : parsed.error?.message ?? parsed.message ?? rawError;
      } catch {
        // Keep the raw response when the service did not return JSON.
      }
      throw new Error(`API Error (${response.status}): ${message || response.statusText}`);
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
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const emptyEvidenceStats: EvidenceStats = {
      total: 0,
      by_decision: {},
      by_actor_type: {},
      by_action: {},
      unique_actors: 0,
      unique_traces: 0,
    };
    const emptyEvidencePage: PaginatedResponse<EvidenceRecord> = {
      data: [],
      total: 0,
      page: 1,
      page_size: 1,
      has_more: false,
    };
    const emptyChain: EvidenceChainVerification = {
      valid: false,
      records_verified: 0,
    };

    const [decisions, approvals, policies, evidenceStats, todayEvidence, evidenceChain] = await Promise.all([
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
      this.fetchWithFallback<EvidenceStats>(
        'evidence',
        '/api/v1/evidence/stats',
        emptyEvidenceStats,
        degradedServices
      ),
      this.fetchWithFallback<PaginatedResponse<EvidenceRecord>>(
        'evidence',
        `/api/v1/evidence?page=1&page_size=1&start_time=${encodeURIComponent(today.toISOString())}`,
        emptyEvidencePage,
        degradedServices
      ),
      this.fetchWithFallback<EvidenceChainVerification>(
        'evidence',
        '/api/v1/evidence/verify',
        emptyChain,
        degradedServices
      ),
    ]);

    return {
      decisions,
      approvals,
      policies,
      evidence: {
        total_records: evidenceStats.total,
        today: todayEvidence.total,
        chain_valid: evidenceChain.valid,
        last_verified: new Date().toISOString(),
      },
      degraded_services: degradedServices,
    };
  }

  async getDecisionTimeSeries(
    period: '24h' | '7d' | '30d' = '24h'
  ): Promise<DecisionTimeSeries> {
    return this.fetch<DecisionTimeSeries>('enforcer', `/api/v1/stats/timeseries?period=${period}`);
  }

  // ---------------------------------------------------------------------------
  // Authorization
  // ---------------------------------------------------------------------------

  async authorize(request: AuthorizeActionRequest): Promise<AuthorizationResult> {
    return this.fetch<AuthorizationResult>('enforcer', '/api/v1/authorize', {
      method: 'POST',
      body: JSON.stringify(request),
    });
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

  async exportPolicies(): Promise<Blob> {
    const response = await this.listPolicies({ page: 1, page_size: 10000 });
    return new Blob([JSON.stringify({ policies: response.data }, null, 2)], {
      type: 'application/json',
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
  } = {}): Promise<EvidenceChainVerification> {
    const searchParams = new URLSearchParams();
    if (params.start_time) searchParams.set('start_time', params.start_time);
    if (params.end_time) searchParams.set('end_time', params.end_time);

    return this.fetch<EvidenceChainVerification>('evidence', `/api/v1/evidence/verify?${searchParams}`);
  }

  async getEvidenceStats(params: {
    start_time?: string;
    end_time?: string;
  } = {}): Promise<EvidenceStats> {
    const searchParams = new URLSearchParams();
    if (params.start_time) searchParams.set('start_time', params.start_time);
    if (params.end_time) searchParams.set('end_time', params.end_time);

    return this.fetch<EvidenceStats>('evidence', `/api/v1/evidence/stats?${searchParams}`);
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

  async approveRequest(requestId: string, notes?: string): Promise<ApprovalRequest> {
    return this.fetch<ApprovalRequest>('approvals', `/api/v1/approvals/${requestId}/approve`, {
      method: 'POST',
      body: JSON.stringify({
        approver_id: this.operator.id,
        approver_role: this.operator.role,
        justification: notes,
      }),
    });
  }

  async rejectRequest(requestId: string, notes?: string): Promise<ApprovalRequest> {
    return this.fetch<ApprovalRequest>('approvals', `/api/v1/approvals/${requestId}/reject`, {
      method: 'POST',
      body: JSON.stringify({
        approver_id: this.operator.id,
        approver_role: this.operator.role,
        justification: notes,
      }),
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
