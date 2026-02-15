/**
 * Health Routes
 * Health check and readiness endpoints
 */

import type { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import type { Config } from '../config/index.js';
import type { PolicyClient } from '../services/policy-client.js';
import type { EvidenceClient } from '../services/evidence-client.js';
import type { ApprovalsClient } from '../services/approvals-client.js';
import type { CacheService } from '../services/cache.js';

// =============================================================================
// ROUTE OPTIONS
// =============================================================================

interface HealthRouteOptions {
  config: Config;
  policyClient: PolicyClient;
  evidenceClient: EvidenceClient;
  approvalsClient: ApprovalsClient;
  cache: CacheService | null;
  startTime: number;
}

// =============================================================================
// ROUTES
// =============================================================================

export async function healthRoutes(
  fastify: FastifyInstance,
  options: HealthRouteOptions
): Promise<void> {
  const { config, policyClient, evidenceClient, approvalsClient, cache, startTime } = options;

  /**
   * GET /health
   * Basic health check (for load balancers)
   */
  fastify.get('/health', {
    schema: {
      description: 'Health check',
      tags: ['health'],
      response: {
        200: {
          type: 'object',
          properties: {
            ready: { type: 'boolean' },
            status: { type: 'string' },
            service: { type: 'string' },
            version: { type: 'string' },
            uptime: { type: 'number' },
            timestamp: { type: 'string' },
          },
        },
      },
    },
  }, async (_request: FastifyRequest, reply: FastifyReply) => {
    return reply.code(200).send({
      status: 'healthy',
      service: config.service.name,
      version: config.service.version,
      uptime: Math.floor((Date.now() - startTime) / 1000),
      timestamp: new Date().toISOString(),
    });
  });

  /**
   * GET /ready
   * Readiness check with dependency health
   */
  fastify.get('/ready', {
    schema: {
      description: 'Readiness check with dependencies',
      tags: ['health'],
      response: {
        200: {
          type: 'object',
          properties: {
            status: { type: 'string' },
            service: { type: 'string' },
            version: { type: 'string' },
            uptime: { type: 'number' },
            timestamp: { type: 'string' },
            checks: { type: 'object' },
          },
        },
        503: {
          type: 'object',
          properties: {
            ready: { type: 'boolean' },
            status: { type: 'string' },
            checks: { type: 'object' },
          },
        },
      },
    },
  }, async (_request: FastifyRequest, reply: FastifyReply) => {
    const checks: Record<string, { status: 'pass' | 'fail' | 'warn'; message?: string; duration_ms?: number }> = {};
    let healthy = true;

    // Check Policy Service
    const policyStart = Date.now();
    try {
      const policyHealth = await policyClient.health();
      checks['policy-service'] = {
        status: policyHealth ? 'pass' : 'fail',
        duration_ms: Date.now() - policyStart,
      };
      if (!policyHealth) healthy = false;
    } catch (error) {
      checks['policy-service'] = {
        status: 'fail',
        message: (error as Error).message,
        duration_ms: Date.now() - policyStart,
      };
      healthy = false;
    }

    // Check Evidence Service
    const evidenceStart = Date.now();
    try {
      const evidenceHealth = await evidenceClient.health();
      const evidenceStatus = evidenceHealth
        ? 'pass'
        : (config.evidence.writeMode === 'strict' ? 'fail' : 'warn');
      checks['evidence-service'] = {
        status: evidenceStatus,
        duration_ms: Date.now() - evidenceStart,
      };
      if (!evidenceHealth && config.evidence.writeMode === 'strict') {
        healthy = false;
      }
    } catch (error) {
      const evidenceStatus = config.evidence.writeMode === 'strict' ? 'fail' : 'warn';
      checks['evidence-service'] = {
        status: evidenceStatus,
        message: (error as Error).message,
        duration_ms: Date.now() - evidenceStart,
      };
      if (config.evidence.writeMode === 'strict') {
        healthy = false;
      }
    }

    // Check Approvals Service
    const approvalsStart = Date.now();
    try {
      const approvalsHealth = await approvalsClient.health();
      checks['approvals-service'] = {
        status: approvalsHealth ? 'pass' : 'warn',
        duration_ms: Date.now() - approvalsStart,
      };
    } catch (error) {
      checks['approvals-service'] = {
        status: 'warn',
        message: (error as Error).message,
        duration_ms: Date.now() - approvalsStart,
      };
    }

    // Check Cache
    if (cache) {
      const cacheStart = Date.now();
      try {
        const cacheHealth = await cache.health();
        checks['cache'] = {
          status: cacheHealth ? 'pass' : 'warn',
          duration_ms: Date.now() - cacheStart,
        };
      } catch (error) {
        checks['cache'] = {
          status: 'warn',
          message: (error as Error).message,
          duration_ms: Date.now() - cacheStart,
        };
      }
    }

    const response = {
      ready: healthy,
      status: healthy ? 'healthy' : 'unhealthy',
      service: config.service.name,
      version: config.service.version,
      uptime: Math.floor((Date.now() - startTime) / 1000),
      timestamp: new Date().toISOString(),
      checks,
    };

    return reply.code(healthy ? 200 : 503).send(response);
  });

  /**
   * GET /metrics
   * Prometheus metrics endpoint
   */
  fastify.get('/metrics', {
    schema: {
    },
  }, async (_request: FastifyRequest, reply: FastifyReply) => {
    // Placeholder for Prometheus metrics
    // In production, integrate with prom-client
    const metrics = `
# HELP stix_enforcer_uptime_seconds Service uptime in seconds
# TYPE stix_enforcer_uptime_seconds gauge
stix_enforcer_uptime_seconds ${Math.floor((Date.now() - startTime) / 1000)}

# HELP stix_enforcer_info Service information
# TYPE stix_enforcer_info gauge
stix_enforcer_info{version="${config.service.version}",env="${config.service.env}"} 1
`;

    reply.header('Content-Type', 'text/plain; version=0.0.4');
    return reply.send(metrics.trim());
  });
}
