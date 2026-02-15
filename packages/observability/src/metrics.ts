/**
 * STIX Metrics Module
 * Prometheus-compatible metrics for STIX services
 */

import {
  Registry,
  Counter,
  Histogram,
  Gauge,
  collectDefaultMetrics,
  register as defaultRegister,
} from 'prom-client';

/**
 * Metrics configuration
 */
export interface MetricsConfig {
  /** Service name for labels */
  serviceName: string;

  /** Whether to collect default Node.js metrics */
  collectDefaultMetrics?: boolean;

  /** Default labels to add to all metrics */
  defaultLabels?: Record<string, string>;

  /** Metric prefix */
  prefix?: string;

  /** Custom registry (uses default if not provided) */
  registry?: Registry;
}

/**
 * STIX Metrics - Pre-defined metrics for STIX services
 */
export class StixMetrics {
  public readonly registry: Registry;
  private readonly prefix: string;

  // Authorization metrics
  public readonly authorizationTotal: Counter;
  public readonly authorizationDuration: Histogram;
  public readonly authorizationErrors: Counter;

  // Evidence metrics
  public readonly evidenceWriteTotal: Counter;
  public readonly evidenceWriteDuration: Histogram;
  public readonly evidenceWriteErrors: Counter;
  public readonly evidenceBatchSize: Histogram;

  // Approval metrics
  public readonly approvalsCreated: Counter;
  public readonly approvalsResolved: Counter;
  public readonly approvalsPending: Gauge;
  public readonly approvalResolutionTime: Histogram;

  // Policy metrics
  public readonly policyEvaluations: Counter;
  public readonly policyEvaluationDuration: Histogram;
  public readonly policiesLoaded: Gauge;
  public readonly policyCacheHits: Counter;
  public readonly policyCacheMisses: Counter;

  // Rate limiting metrics
  public readonly rateLimitHits: Counter;
  public readonly rateLimitAllowed: Counter;

  // Service health metrics
  public readonly healthCheckTotal: Counter;
  public readonly healthCheckDuration: Histogram;
  public readonly serviceUp: Gauge;

  // HTTP metrics
  public readonly httpRequestTotal: Counter;
  public readonly httpRequestDuration: Histogram;
  public readonly httpRequestSize: Histogram;
  public readonly httpResponseSize: Histogram;

  constructor(config: MetricsConfig) {
    this.prefix = config.prefix ?? 'stix';
    this.registry = config.registry ?? defaultRegister;

    // Set default labels
    if (config.defaultLabels) {
      this.registry.setDefaultLabels({
        service: config.serviceName,
        ...config.defaultLabels,
      });
    } else {
      this.registry.setDefaultLabels({ service: config.serviceName });
    }

    // Collect default Node.js metrics
    if (config.collectDefaultMetrics !== false) {
      collectDefaultMetrics({
        register: this.registry,
        prefix: `${this.prefix}_`,
      });
    }

    // Initialize authorization metrics
    this.authorizationTotal = new Counter({
      name: `${this.prefix}_authorization_total`,
      help: 'Total number of authorization requests',
      labelNames: ['decision', 'actor_type', 'action', 'resource_type', 'env'],
      registers: [this.registry],
    });

    this.authorizationDuration = new Histogram({
      name: `${this.prefix}_authorization_duration_seconds`,
      help: 'Duration of authorization requests in seconds',
      labelNames: ['decision', 'actor_type'],
      buckets: [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
      registers: [this.registry],
    });

    this.authorizationErrors = new Counter({
      name: `${this.prefix}_authorization_errors_total`,
      help: 'Total number of authorization errors',
      labelNames: ['error_type'],
      registers: [this.registry],
    });

    // Initialize evidence metrics
    this.evidenceWriteTotal = new Counter({
      name: `${this.prefix}_evidence_write_total`,
      help: 'Total number of evidence records written',
      labelNames: ['decision', 'env'],
      registers: [this.registry],
    });

    this.evidenceWriteDuration = new Histogram({
      name: `${this.prefix}_evidence_write_duration_seconds`,
      help: 'Duration of evidence writes in seconds',
      buckets: [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1],
      registers: [this.registry],
    });

    this.evidenceWriteErrors = new Counter({
      name: `${this.prefix}_evidence_write_errors_total`,
      help: 'Total number of evidence write errors',
      labelNames: ['error_type'],
      registers: [this.registry],
    });

    this.evidenceBatchSize = new Histogram({
      name: `${this.prefix}_evidence_batch_size`,
      help: 'Size of evidence write batches',
      buckets: [1, 5, 10, 25, 50, 100, 250, 500, 1000],
      registers: [this.registry],
    });

    // Initialize approval metrics
    this.approvalsCreated = new Counter({
      name: `${this.prefix}_approvals_created_total`,
      help: 'Total number of approvals created',
      labelNames: ['env', 'approver_role'],
      registers: [this.registry],
    });

    this.approvalsResolved = new Counter({
      name: `${this.prefix}_approvals_resolved_total`,
      help: 'Total number of approvals resolved',
      labelNames: ['status', 'env'],
      registers: [this.registry],
    });

    this.approvalsPending = new Gauge({
      name: `${this.prefix}_approvals_pending`,
      help: 'Current number of pending approvals',
      labelNames: ['env'],
      registers: [this.registry],
    });

    this.approvalResolutionTime = new Histogram({
      name: `${this.prefix}_approval_resolution_seconds`,
      help: 'Time to resolve approvals in seconds',
      labelNames: ['status'],
      buckets: [60, 300, 600, 1800, 3600, 7200, 14400, 28800, 43200, 86400],
      registers: [this.registry],
    });

    // Initialize policy metrics
    this.policyEvaluations = new Counter({
      name: `${this.prefix}_policy_evaluations_total`,
      help: 'Total number of policy evaluations',
      labelNames: ['policy_id', 'decision'],
      registers: [this.registry],
    });

    this.policyEvaluationDuration = new Histogram({
      name: `${this.prefix}_policy_evaluation_duration_seconds`,
      help: 'Duration of policy evaluations in seconds',
      buckets: [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
      registers: [this.registry],
    });

    this.policiesLoaded = new Gauge({
      name: `${this.prefix}_policies_loaded`,
      help: 'Number of policies currently loaded',
      labelNames: ['active'],
      registers: [this.registry],
    });

    this.policyCacheHits = new Counter({
      name: `${this.prefix}_policy_cache_hits_total`,
      help: 'Total number of policy cache hits',
      registers: [this.registry],
    });

    this.policyCacheMisses = new Counter({
      name: `${this.prefix}_policy_cache_misses_total`,
      help: 'Total number of policy cache misses',
      registers: [this.registry],
    });

    // Initialize rate limiting metrics
    this.rateLimitHits = new Counter({
      name: `${this.prefix}_rate_limit_hits_total`,
      help: 'Total number of rate limit hits',
      labelNames: ['actor_id', 'action'],
      registers: [this.registry],
    });

    this.rateLimitAllowed = new Counter({
      name: `${this.prefix}_rate_limit_allowed_total`,
      help: 'Total number of requests allowed by rate limiter',
      registers: [this.registry],
    });

    // Initialize health metrics
    this.healthCheckTotal = new Counter({
      name: `${this.prefix}_health_check_total`,
      help: 'Total number of health checks',
      labelNames: ['status'],
      registers: [this.registry],
    });

    this.healthCheckDuration = new Histogram({
      name: `${this.prefix}_health_check_duration_seconds`,
      help: 'Duration of health checks in seconds',
      buckets: [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1],
      registers: [this.registry],
    });

    this.serviceUp = new Gauge({
      name: `${this.prefix}_service_up`,
      help: 'Whether the service is up (1) or down (0)',
      labelNames: ['component'],
      registers: [this.registry],
    });

    // Initialize HTTP metrics
    this.httpRequestTotal = new Counter({
      name: `${this.prefix}_http_requests_total`,
      help: 'Total number of HTTP requests',
      labelNames: ['method', 'route', 'status_code'],
      registers: [this.registry],
    });

    this.httpRequestDuration = new Histogram({
      name: `${this.prefix}_http_request_duration_seconds`,
      help: 'Duration of HTTP requests in seconds',
      labelNames: ['method', 'route', 'status_code'],
      buckets: [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
      registers: [this.registry],
    });

    this.httpRequestSize = new Histogram({
      name: `${this.prefix}_http_request_size_bytes`,
      help: 'Size of HTTP requests in bytes',
      labelNames: ['method', 'route'],
      buckets: [100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000],
      registers: [this.registry],
    });

    this.httpResponseSize = new Histogram({
      name: `${this.prefix}_http_response_size_bytes`,
      help: 'Size of HTTP responses in bytes',
      labelNames: ['method', 'route'],
      buckets: [100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000],
      registers: [this.registry],
    });
  }

  /**
   * Get metrics in Prometheus format
   */
  async getMetrics(): Promise<string> {
    return this.registry.metrics();
  }

  /**
   * Get metrics content type
   */
  getContentType(): string {
    return this.registry.contentType;
  }

  /**
   * Reset all metrics
   */
  reset(): void {
    this.registry.resetMetrics();
  }

  /**
   * Record an authorization request
   */
  recordAuthorization(params: {
    decision: string;
    actorType: string;
    action: string;
    resourceType: string;
    env: string;
    durationSeconds: number;
  }): void {
    this.authorizationTotal.inc({
      decision: params.decision,
      actor_type: params.actorType,
      action: params.action,
      resource_type: params.resourceType,
      env: params.env,
    });

    this.authorizationDuration.observe(
      { decision: params.decision, actor_type: params.actorType },
      params.durationSeconds
    );
  }

  /**
   * Record an evidence write
   */
  recordEvidenceWrite(params: {
    decision: string;
    env: string;
    durationSeconds: number;
    batchSize?: number;
  }): void {
    this.evidenceWriteTotal.inc({
      decision: params.decision,
      env: params.env,
    });

    this.evidenceWriteDuration.observe(params.durationSeconds);

    if (params.batchSize) {
      this.evidenceBatchSize.observe(params.batchSize);
    }
  }

  /**
   * Record an HTTP request
   */
  recordHttpRequest(params: {
    method: string;
    route: string;
    statusCode: number;
    durationSeconds: number;
    requestSize?: number;
    responseSize?: number;
  }): void {
    const labels = {
      method: params.method,
      route: params.route,
      status_code: String(params.statusCode),
    };

    this.httpRequestTotal.inc(labels);
    this.httpRequestDuration.observe(labels, params.durationSeconds);

    if (params.requestSize) {
      this.httpRequestSize.observe(
        { method: params.method, route: params.route },
        params.requestSize
      );
    }

    if (params.responseSize) {
      this.httpResponseSize.observe(
        { method: params.method, route: params.route },
        params.responseSize
      );
    }
  }
}

/**
 * Create metrics endpoint for Fastify
 */
export function createMetricsPlugin(metrics: StixMetrics) {
  return async function metricsPlugin(
    fastify: { get: (path: string, handler: (request: unknown, reply: { header: (name: string, value: string) => void; send: (body: string) => void }) => Promise<void>) => void },
  ): Promise<void> {
    fastify.get('/metrics', async (_request, reply) => {
      reply.header('Content-Type', metrics.getContentType());
      reply.send(await metrics.getMetrics());
    });
  };
}

/**
 * Create HTTP request timing middleware for Fastify
 */
export function createHttpMetricsHook(metrics: StixMetrics) {
  return {
    onRequest: async (request: { method: string; routerPath?: string; headers: Record<string, string> }, _reply: unknown) => {
      (request as { startTime?: bigint }).startTime = process.hrtime.bigint();
    },
    onResponse: async (request: { method: string; routerPath?: string; headers: Record<string, string>; startTime?: bigint }, reply: { statusCode: number; getHeader: (name: string) => string | undefined }) => {
      const startTime = (request as { startTime?: bigint }).startTime;
      if (!startTime) return;

      const endTime = process.hrtime.bigint();
      const durationNs = Number(endTime - startTime);
      const durationSeconds = durationNs / 1e9;

      metrics.recordHttpRequest({
        method: request.method,
        route: request.routerPath ?? 'unknown',
        statusCode: reply.statusCode,
        durationSeconds,
        requestSize: parseInt(request.headers['content-length'] ?? '0', 10),
        responseSize: parseInt(reply.getHeader('content-length') ?? '0', 10),
      });
    },
  };
}
