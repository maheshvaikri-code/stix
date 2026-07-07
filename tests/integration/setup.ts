/**
 * STIX Integration Tests - Setup
 */

export interface TestConfig {
  enforcerUrl: string;
  policyUrl: string;
  evidenceUrl: string;
  approvalsUrl: string;
  apiKey?: string;
  timeout: number;
}

export function getTestConfig(): TestConfig {
  return {
    enforcerUrl: process.env.STIX_ENFORCER_URL || 'http://localhost:3001',
    policyUrl: process.env.STIX_POLICY_URL || 'http://localhost:3002',
    evidenceUrl: process.env.STIX_EVIDENCE_URL || 'http://localhost:3003',
    approvalsUrl: process.env.STIX_APPROVALS_URL || 'http://localhost:3004',
    apiKey: process.env.STIX_API_KEY,
    timeout: parseInt(process.env.STIX_TEST_TIMEOUT || '30000', 10),
  };
}

export class TestClient {
  private baseUrl: string;
  private apiKey?: string;
  private timeout: number;

  constructor(baseUrl: string, apiKey?: string, timeout = 30000) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
    this.timeout = timeout;
  }

  async request<T>(
    path: string,
    options: {
      method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
      body?: unknown;
      headers?: Record<string, string>;
    } = {}
  ): Promise<{ status: number; data: T; headers: Headers }> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...options.headers,
      };

      if (this.apiKey) {
        headers['Authorization'] = `Bearer ${this.apiKey}`;
      }

      const response = await fetch(`${this.baseUrl}${path}`, {
        method: options.method || 'GET',
        headers,
        body: options.body ? JSON.stringify(options.body) : undefined,
        signal: controller.signal,
      });

      const text = await response.text();
      const data = (text ? JSON.parse(text) : {}) as T;

      return {
        status: response.status,
        data,
        headers: response.headers,
      };
    } finally {
      clearTimeout(timeoutId);
    }
  }

  async get<T>(path: string): Promise<{ status: number; data: T }> {
    return this.request<T>(path, { method: 'GET' });
  }

  async post<T>(path: string, body: unknown): Promise<{ status: number; data: T }> {
    return this.request<T>(path, { method: 'POST', body });
  }

  async healthCheck(): Promise<boolean> {
    try {
      const { status, data } = await this.get<{ status: string }>('/health');
      return status === 200 && data.status === 'healthy';
    } catch {
      return false;
    }
  }
}

export function createClients(config: TestConfig) {
  return {
    enforcer: new TestClient(config.enforcerUrl, config.apiKey, config.timeout),
    policy: new TestClient(config.policyUrl, config.apiKey, config.timeout),
    evidence: new TestClient(config.evidenceUrl, config.apiKey, config.timeout),
    approvals: new TestClient(config.approvalsUrl, config.apiKey, config.timeout),
  };
}

export interface AuthorizeRequest {
  actor: {
    id: string;
    type: 'AI_AGENT' | 'SERVICE' | 'HUMAN';
    tenant?: string;
    role?: string;
  };
  action: string;
  resource: {
    type: string;
    id?: string;
    classification?: string[];
  };
  context: {
    env: string;
    purpose?: string;
    signals?: Record<string, boolean>;
  };
}

export interface AuthorizeResponse {
  decision: 'ALLOW' | 'DENY' | 'QUARANTINE';
  trace_id: string;
  reason_code: string;
  proof_token?: string;
  approval_ticket_id?: string;
  policy_id?: string;
  controls?: string[];
}

export interface EvidenceRecord {
  event_id: string;
  trace_id: string;
  timestamp: string;
  decision: string;
  actor_id: string;
  actor_type: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  policy_id: string;
  reason_code: string;
  request_hash: string;
  chain_hash: string;
}

export interface ApprovalRequest {
  request_id: string;
  trace_id: string;
  actor_id: string;
  action: string;
  resource_type: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';
  created_at: string;
  expires_at: string;
}

// Test data generators
export function generateTestActor(overrides?: Partial<AuthorizeRequest['actor']>): AuthorizeRequest['actor'] {
  return {
    id: `test-agent-${Date.now()}`,
    type: 'AI_AGENT',
    ...overrides,
  };
}

export function generateTestRequest(overrides?: Partial<AuthorizeRequest>): AuthorizeRequest {
  return {
    actor: generateTestActor(overrides?.actor),
    action: overrides?.action || 'test_action',
    resource: {
      type: overrides?.resource?.type || 'test_resource',
      id: overrides?.resource?.id,
      classification: overrides?.resource?.classification,
    },
    context: {
      env: overrides?.context?.env || 'test',
      purpose: overrides?.context?.purpose || 'integration_testing',
      signals: overrides?.context?.signals,
    },
  };
}

// Wait utility
export function wait(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Retry utility
export async function retry<T>(
  fn: () => Promise<T>,
  options: { retries?: number; delay?: number; condition?: (result: T) => boolean } = {}
): Promise<T> {
  const { retries = 3, delay = 1000, condition } = options;

  for (let i = 0; i < retries; i++) {
    try {
      const result = await fn();
      if (!condition || condition(result)) {
        return result;
      }
    } catch (error) {
      if (i === retries - 1) throw error;
    }
    await wait(delay);
  }

  throw new Error('Retry exhausted');
}
