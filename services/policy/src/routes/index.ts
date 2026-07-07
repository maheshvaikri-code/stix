/**
 * STIX Policy Service Routes
 */

import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import {
  type PolicyArtifact,
  type StixError,
  PolicyArtifactSchema,
  formatZodErrors,
  isStixError,
  createErrorResponse,
  PolicyNotFoundError,
} from '@stix/shared';
import type { PolicyEngine, EvaluationRequest } from '../core/engine.js';
import type { PolicyStore } from '../store/index.js';

// =============================================================================
// HELPERS
// =============================================================================

type PolicyInput = PolicyArtifact & { enabled?: boolean };

function normalizePolicyInput(input: Record<string, unknown>): Record<string, unknown> {
  const policyInput = input as unknown as PolicyInput;
  if (typeof policyInput.enabled === 'boolean') {
    const { enabled, ...rest } = policyInput;
    return { ...rest, active: enabled };
  }
  return input;
}

function toPolicyResponse(policy: PolicyArtifact): Record<string, unknown> {
  const createdAt =
    (policy as any).metadata?.created_at ?? policy.created_at ?? new Date().toISOString();
  const updatedAt =
    (policy as any).metadata?.updated_at ?? policy.updated_at ?? new Date().toISOString();

  return {
    policy_id: policy.policy_id,
    version: policy.version,
    priority: policy.priority ?? 100,
    scope: policy.scope,
    conditions: policy.conditions,
    decision: policy.decision,
    reason_code: policy.reason_code,
    regulation: policy.regulation ?? policy.regulations?.[0],
    description: policy.description,
    created_at: createdAt,
    updated_at: updatedAt,
    enabled: policy.active ?? true,
  };
}

// =============================================================================
// EVALUATE ROUTES
// =============================================================================

interface EvaluateRouteOptions {
  engine: PolicyEngine;
}

export async function evaluateRoutes(
  fastify: FastifyInstance,
  options: EvaluateRouteOptions
): Promise<void> {
  const { engine } = options;

  /**
   * POST /api/v1/evaluate
   * Evaluate policy for a request
   */
  fastify.post<{ Body: EvaluationRequest }>('/api/v1/evaluate', {
    schema: {
      body: {
        type: 'object',
        required: ['actor', 'action', 'resource', 'context'],
      },
    },
  }, async (request: FastifyRequest<{ Body: EvaluationRequest }>, reply: FastifyReply) => {
    try {
      const decision = await engine.evaluate(request.body);
      return reply.code(200).send(decision);
    } catch (error) {
      if (isStixError(error)) {
        const stixError = error as StixError;
        return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
      }
      request.log.error({ err: error }, 'Policy evaluation failed');
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Policy evaluation failed' },
      });
    }
  });
}

// =============================================================================
// POLICY MANAGEMENT ROUTES
// =============================================================================

interface PolicyRouteOptions {
  store: PolicyStore;
  engine: PolicyEngine;
}

export async function policyRoutes(
  fastify: FastifyInstance,
  options: PolicyRouteOptions
): Promise<void> {
  const { store, engine } = options;

  /**
   * GET /api/v1/policies
   * List all policies
   */
  fastify.get('/api/v1/policies', {
    schema: {
      querystring: {
        type: 'object',
        properties: {
          page: { type: 'integer', minimum: 1 },
          page_size: { type: 'integer', minimum: 1, maximum: 100 },
          regulation: { type: 'string' },
          decision: { type: 'string' },
          enabled: { type: 'boolean' },
          search: { type: 'string' },
        },
      },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    try {
      const query = request.query as {
        page?: number;
        page_size?: number;
        regulation?: string;
        decision?: string;
        enabled?: boolean;
        search?: string;
      };

      const page = query.page ?? 1;
      const pageSize = query.page_size ?? 20;

      // Get all policies first
      let policies = await store.listPolicies({ limit: 10000 });

      // Filter by regulation
      if (query.regulation) {
        policies = policies.filter((p) =>
          (p.regulation ?? p.regulations?.[0]) === query.regulation
        );
      }

      // Filter by decision
      if (query.decision) {
        policies = policies.filter(p => p.decision === query.decision);
      }

      // Filter by enabled status
      if (query.enabled !== undefined) {
        policies = policies.filter(p => (p.active ?? true) === query.enabled);
      }

      // Filter by search term
      if (query.search) {
        const searchLower = query.search.toLowerCase();
        policies = policies.filter(p =>
          p.policy_id.toLowerCase().includes(searchLower) ||
          p.description?.toLowerCase().includes(searchLower) ||
          p.scope.action.toLowerCase().includes(searchLower)
        );
      }

      const total = policies.length;
      const start = (page - 1) * pageSize;
      const paginatedPolicies = policies.slice(start, start + pageSize);

      // Transform to dashboard format
      const data = paginatedPolicies.map(toPolicyResponse);

      return reply.code(200).send({
        data,
        total,
        page,
        page_size: pageSize,
        has_more: start + pageSize < total,
      });
    } catch (error) {
      request.log.error({ err: error }, 'Failed to list policies');
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to list policies' },
      });
    }
  });

  /**
   * GET /api/v1/policies/:policyId
   * Get a policy by ID
   */
  fastify.get<{ Params: { policyId: string } }>('/api/v1/policies/:policyId', {
    schema: {
      params: {
        type: 'object',
        properties: {
          policyId: { type: 'string' },
        },
      },
    },
  }, async (request: FastifyRequest<{ Params: { policyId: string } }>, reply: FastifyReply) => {
    try {
      const policy = await store.getPolicy(request.params.policyId);
      
      if (!policy) {
        throw new PolicyNotFoundError(request.params.policyId);
      }

      return reply.code(200).send(toPolicyResponse(policy));
    } catch (error) {
      if (isStixError(error)) {
        const stixError = error as StixError;
        return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
      }
      request.log.error({ err: error }, 'Failed to get policy');
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to get policy' },
      });
    }
  });

  /**
   * POST /api/v1/policies
   * Create a new policy
   */
  fastify.post<{ Body: PolicyArtifact }>('/api/v1/policies', {
    schema: {},
  }, async (request: FastifyRequest<{ Body: PolicyArtifact }>, reply: FastifyReply) => {
    try {
      const normalized = normalizePolicyInput(request.body as unknown as Record<string, unknown>);
      const parsed = PolicyArtifactSchema.safeParse(normalized);
      if (!parsed.success) {
        const details = formatZodErrors(parsed.error);
        return reply.code(400).send({
          error: `Validation failed: ${details.map((d: { field: string; message: string }) => `${d.field}: ${d.message}`).join('; ')}`,
          details,
        });
      }
      const validated = parsed.data;
      const now = new Date().toISOString();
      validated.created_at = validated.created_at ?? now;
      validated.updated_at = now;
      
      // Check if policy already exists
      const existing = await store.getPolicy(validated.policy_id);
      if (existing) {
        return reply.code(409).send({
          success: false,
          error: { code: 'POLICY_EXISTS', message: 'Policy already exists' },
        });
      }

      await store.upsertPolicy(validated);

      return reply.code(201).send(toPolicyResponse(validated));
    } catch (error) {
      if (isStixError(error)) {
        const stixError = error as StixError;
        return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
      }
      request.log.error({ err: error }, 'Failed to create policy');
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to create policy' },
      });
    }
  });

  /**
   * PUT /api/v1/policies/:policyId
   * Update a policy
   */
  fastify.put<{ Params: { policyId: string }; Body: PolicyArtifact }>(
    '/api/v1/policies/:policyId',
    {
      schema: {},
    },
    async (request: FastifyRequest<{ Params: { policyId: string }; Body: PolicyArtifact }>, reply: FastifyReply) => {
      try {
        const normalized = normalizePolicyInput({
          ...(request.body as unknown as Record<string, unknown>),
          policy_id: request.params.policyId,
        });
        const parsed = PolicyArtifactSchema.safeParse(normalized);
        if (!parsed.success) {
          const details = formatZodErrors(parsed.error);
          return reply.code(400).send({
            error: `Validation failed: ${details.map((d: { field: string; message: string }) => `${d.field}: ${d.message}`).join('; ')}`,
            details,
          });
        }
        const validated = parsed.data;
        const now = new Date().toISOString();
        validated.created_at = validated.created_at ?? now;
        validated.updated_at = now;

        await store.upsertPolicy(validated);

        return reply.code(200).send(toPolicyResponse(validated));
      } catch (error) {
        if (isStixError(error)) {
          const stixError = error as StixError;
          return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
        }
        request.log.error({ err: error }, 'Failed to update policy');
        return reply.code(500).send({
          success: false,
          error: { code: 'INTERNAL_ERROR', message: 'Failed to update policy' },
        });
      }
    }
  );

  /**
   * PATCH /api/v1/policies/:policyId
   * Partially update a policy
   */
  fastify.patch<{ Params: { policyId: string }; Body: Partial<PolicyArtifact> }>(
    '/api/v1/policies/:policyId',
    {
      schema: {},
    },
    async (request: FastifyRequest<{ Params: { policyId: string }; Body: Partial<PolicyArtifact> }>, reply: FastifyReply) => {
      try {
        const existing = await store.getPolicy(request.params.policyId);
        if (!existing) {
          throw new PolicyNotFoundError(request.params.policyId);
        }

        const updates = normalizePolicyInput(request.body as Record<string, unknown>);

        // Merge updates with existing policy
        const updated: PolicyArtifact = {
          ...existing,
          ...updates,
          policy_id: request.params.policyId, // Ensure ID doesn't change
          updated_at: new Date().toISOString(),
        };

        if (!updated.created_at) {
          updated.created_at = new Date().toISOString();
        }

        const parsed = PolicyArtifactSchema.safeParse(updated);
        if (!parsed.success) {
          const details = formatZodErrors(parsed.error);
          return reply.code(400).send({
            error: `Validation failed: ${details.map((d: { field: string; message: string }) => `${d.field}: ${d.message}`).join('; ')}`,
            details,
          });
        }
        const validated = parsed.data;
        await store.upsertPolicy(validated);

        // Return in dashboard format
        return reply.code(200).send(toPolicyResponse(validated));
      } catch (error) {
        if (isStixError(error)) {
          const stixError = error as StixError;
          return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
        }
        request.log.error({ err: error }, 'Failed to update policy');
        return reply.code(500).send({
          success: false,
          error: { code: 'INTERNAL_ERROR', message: 'Failed to update policy' },
        });
      }
    }
  );

  /**
   * DELETE /api/v1/policies/:policyId
   * Delete a policy
   */
  fastify.delete<{ Params: { policyId: string } }>('/api/v1/policies/:policyId', {
    schema: {},
  }, async (request: FastifyRequest<{ Params: { policyId: string } }>, reply: FastifyReply) => {
    try {
      const policy = await store.getPolicy(request.params.policyId);
      
      if (!policy) {
        throw new PolicyNotFoundError(request.params.policyId);
      }

      await store.deletePolicy(request.params.policyId);

      return reply.code(204).send();
    } catch (error) {
      if (isStixError(error)) {
        const stixError = error as StixError;
        return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
      }
      request.log.error({ err: error }, 'Failed to delete policy');
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to delete policy' },
      });
    }
  });

  /**
   * POST /api/v1/policies/simulate
   * Simulate policy evaluation against a request
   */
  fastify.post<{
    Body: {
      policy?: PolicyArtifact;
      request: {
        actor: { id: string; type: string };
        action: string;
        resource: { type: string };
        context: Record<string, unknown>;
      };
    };
  }>('/api/v1/policies/simulate', {
    schema: {
      body: {
        type: 'object',
        required: ['request'],
        properties: {
          policy: { type: 'object' },
          request: { type: 'object' },
        },
      },
      response: {
        200: {
          type: 'object',
          properties: {
            decision: { type: 'string' },
            matched_policy: { type: 'string' },
            reason_code: { type: 'string' },
            scope_match: { type: 'boolean' },
          },
        },
      },
    },
  }, async (request: FastifyRequest<{ Body: { policy?: PolicyArtifact; request: { actor: { id: string; type: string }; action: string; resource: { type: string }; context: Record<string, unknown> } } }>, reply: FastifyReply) => {
    try {
      const { policy, request: simRequest } = request.body;

      if (!simRequest) {
        return reply.code(400).send({
          error: 'Request is required',
        });
      }

      // If no policy provided, evaluate against current policy set
      if (!policy) {
        const evalRequest: EvaluationRequest = {
          actor: simRequest.actor as EvaluationRequest['actor'],
          action: simRequest.action,
          resource: simRequest.resource as EvaluationRequest['resource'],
          context: {
            ...(simRequest.context ?? {}),
            env: ((simRequest.context?.env as string | undefined) ?? 'dev') as EvaluationRequest['context']['env'],
          } as EvaluationRequest['context'],
        };

        const decision = await engine.evaluate(evalRequest);
        return reply.code(200).send({
          decision: decision.decision,
          matched_policy: decision.policy.id,
          reason_code: decision.reason_code,
        });
      }

      // Simple simulation - check if the policy scope matches the request
      const scopeMatches = (
        (policy.scope.actor_type === '*' || policy.scope.actor_type === simRequest.actor.type) &&
        (policy.scope.action === '*' || policy.scope.action === simRequest.action ||
         (policy.scope.action.includes('*') && simRequest.action.match(new RegExp('^' + policy.scope.action.replace(/\*/g, '.*') + '$')))) &&
        (policy.scope.resource_type === '*' || policy.scope.resource_type === simRequest.resource.type)
      );

      const decision = scopeMatches ? policy.decision : 'NO_MATCH';

      return reply.code(200).send({
        decision,
        matched_policy: scopeMatches ? policy.policy_id : undefined,
        scope_match: scopeMatches,
      });
    } catch (error) {
      return reply.code(500).send({
        success: false,
        error: { code: 'SIMULATION_ERROR', message: 'Failed to simulate policy' },
      });
    }
  });

  /**
   * POST /api/v1/policies/reload
   * Reload policies from disk
   */
  fastify.post('/api/v1/policies/reload', {
    schema: {},
  }, async (_request: FastifyRequest, reply: FastifyReply) => {
    try {
      await store.reload();
      
      return reply.code(200).send({
        success: true,
        message: 'Policies reloaded',
      });
    } catch (error) {
      return reply.code(500).send({
        success: false,
        error: { code: 'RELOAD_FAILED', message: 'Failed to reload policies' },
      });
    }
  });
}

// =============================================================================
// STATS ROUTES
// =============================================================================

interface StatsRouteOptions {
  store: PolicyStore;
}

export async function statsRoutes(
  fastify: FastifyInstance,
  options: StatsRouteOptions
): Promise<void> {
  const { store } = options;

  /**
   * GET /api/v1/stats
   * Get policy statistics
   */
  fastify.get('/api/v1/stats', {
    schema: {},
  }, async (_request: FastifyRequest, reply: FastifyReply) => {
    try {
      const policies = await store.listPolicies({ limit: 10000 });

      // Count by regulation
      const byRegulation: Record<string, number> = {};
      // Count by decision
      const byDecision: Record<string, number> = {};
      // Count active
      let active = 0;

      for (const policy of policies) {
        // By regulation
        const reg = policy.regulation ?? policy.regulations?.[0] ?? 'none';
        byRegulation[reg] = (byRegulation[reg] || 0) + 1;

        // By decision
        byDecision[policy.decision] = (byDecision[policy.decision] || 0) + 1;

        // Active count
        if (policy.active !== false) {
          active++;
        }
      }

      return reply.code(200).send({
        total: policies.length,
        active,
        by_regulation: byRegulation,
        by_decision: byDecision,
      });
    } catch (error) {
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to get stats' },
      });
    }
  });
}

// =============================================================================
// HEALTH ROUTES
// =============================================================================

interface HealthRouteOptions {
  store: PolicyStore;
  startTime: number;
  version: string;
}

export async function healthRoutes(
  fastify: FastifyInstance,
  options: HealthRouteOptions
): Promise<void> {
  const { store, startTime, version } = options;

  fastify.get('/health', async (_request, reply) => {
    return reply.code(200).send({
      status: 'healthy',
      service: 'stix-policy',
      version,
      uptime: Math.floor((Date.now() - startTime) / 1000),
      timestamp: new Date().toISOString(),
    });
  });

  fastify.get('/ready', async (_request, reply) => {
    const storeHealthy = await store.health();
    
    return reply.code(storeHealthy ? 200 : 503).send({
      status: storeHealthy ? 'healthy' : 'unhealthy',
      service: 'stix-policy',
      version,
      checks: {
        store: { status: storeHealthy ? 'pass' : 'fail' },
      },
    });
  });
}
