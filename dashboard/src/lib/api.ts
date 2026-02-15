/**
 * STIX Dashboard - API Client
 */

// =============================================================================
// CONFIGURATION
// =============================================================================

export const API_CONFIG = {
  enforcer: process.env.NEXT_PUBLIC_ENFORCER_URL || 'http://localhost:3001',
  policy: process.env.NEXT_PUBLIC_POLICY_URL || 'http://localhost:3002',
  evidence: process.env.NEXT_PUBLIC_EVIDENCE_URL || 'http://localhost:3003',
  approvals: process.env.NEXT_PUBLIC_APPROVALS_URL || 'http://localhost:3004',
};

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

// =============================================================================
// API CLIENT
// =============================================================================

class ApiClient {
  private apiKey?: string;

  setApiKey(key: string) {
    this.apiKey = key;
  }

  private async fetch<T>(
    service: keyof typeof API_CONFIG,
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

  // ---------------------------------------------------------------------------
  // Health
  // ---------------------------------------------------------------------------

  async getServiceHealth(service: keyof typeof API_CONFIG): Promise<ServiceHealth> {
    try {
      return await this.fetch<ServiceHealth>(service, '/health');
    } catch {
      return {
        name: service,
        status: 'unhealthy',
        uptime_ms: 0,
        version: 'unknown',
      };
    }
  }

  async getAllServicesHealth(): Promise<Record<string, ServiceHealth>> {
    const services = Object.keys(API_CONFIG) as (keyof typeof API_CONFIG)[];
    const results = await Promise.all(
      services.map(async (service) => ({
        service,
        health: await this.getServiceHealth(service),
      }))
    );
    return Object.fromEntries(results.map((r) => [r.service, r.health]));
  }

  // ---------------------------------------------------------------------------
  // Dashboard Stats
  // ---------------------------------------------------------------------------

  async getDashboardStats(): Promise<DashboardStats> {
    const [decisions, approvals, policies, evidence] = await Promise.all([
      this.fetch<DashboardStats['decisions']>('enforcer', '/api/v1/stats/decisions'),
      this.fetch<DashboardStats['approvals']>('approvals', '/api/v1/stats'),
      this.fetch<DashboardStats['policies']>('policy', '/api/v1/stats'),
      this.fetch<DashboardStats['evidence']>('evidence', '/api/v1/stats'),
    ]);

    return { decisions, approvals, policies, evidence };
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
}

// =============================================================================
// EXPORTS
// =============================================================================

export const api = new ApiClient();

export default api;
