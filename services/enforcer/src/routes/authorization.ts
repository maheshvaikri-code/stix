/**
 * Authorization Routes
 * API endpoints for STIX authorization
 */

import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import {
  type AuthorizeRequest,
  type StixError,
  AuthorizeRequestSchema,
  OutcomeRequestSchema,
  formatZodErrors,
  isStixError,
  createErrorResponse,
  HEADERS,
} from '@stix/shared';
import type { AuthorizationEngine } from '../core/engine.js';
import type { EvidenceClient } from '../services/evidence-client.js';

// =============================================================================
// ROUTE OPTIONS
// =============================================================================

interface AuthorizeRouteOptions {
  engine: AuthorizationEngine;
  evidenceClient: EvidenceClient;
}

// =============================================================================
// ROUTES
// =============================================================================

export async function authorizationRoutes(
  fastify: FastifyInstance,
  options: AuthorizeRouteOptions
): Promise<void> {
  const { engine, evidenceClient } = options;

  /**
   * POST /api/v1/authorize
   * Main authorization endpoint
   */
  fastify.post<{
    Body: AuthorizeRequest;
  }>('/api/v1/authorize', {
    schema: {
      body: {
        type: 'object',
        required: ['actor', 'action', 'resource', 'context'],
        properties: {
          actor: {
            type: 'object',
            required: ['id', 'type'],
            properties: {
              id: { type: 'string' },
              type: { type: 'string', enum: ['HUMAN', 'SERVICE', 'AI_AGENT', 'JOB', 'SYSTEM'] },
              role: { type: 'string' },
              tenant: { type: 'string' },
              attributes: { type: 'object' },
            },
          },
          action: { type: 'string' },
          resource: {
            type: 'object',
            required: ['type'],
            properties: {
              type: { type: 'string' },
              id: { type: 'string' },
              classification: { type: 'array', items: { type: 'string' } },
              attributes: { type: 'object' },
            },
          },
          context: {
            type: 'object',
            required: ['env'],
            properties: {
              env: { type: 'string', enum: ['dev', 'test', 'stage', 'prod', 'production'] },
              purpose: { type: 'string' },
              run_id: { type: 'string' },
              session_id: { type: 'string' },
              ticket_id: { type: 'string' },
              jurisdiction: { type: 'string' },
              tags: { type: 'array', items: { type: 'string' } },
              signals: { type: 'object' },
              attributes: { type: 'object' },
            },
          },
          tool_call: {
            type: 'object',
            properties: {
              tool: { type: 'string' },
              risk_tier: { type: 'string', enum: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] },
              args_summary: { type: 'string' },
            },
          },
        },
      },
      response: {
        200: {
          description: 'Authorization decision',
          type: 'object',
          properties: {
            decision: { type: 'string', enum: ['ALLOW', 'DENY', 'QUARANTINE'] },
            reason_code: { type: 'string' },
            trace_id: { type: 'string' },
            explanation: { type: 'string' },
            policy_id: { type: 'string' },
            policy: {
              type: 'object',
              properties: {
                id: { type: 'string' },
                version: { type: 'string' },
                hash: { type: 'string' },
              },
            },
            obligations: { type: 'array' },
            approval: { type: 'object', nullable: true },
            approval_ticket_id: { type: 'string' },
            proof_token: { type: 'string' },
            controls: { type: 'array', items: { type: 'string' } },
            regulations: { type: 'array', items: { type: 'string' } },
          },
        },
        400: { type: 'object', description: 'Validation error' },
        500: { type: 'object', description: 'Internal server error' },
      },
    },
  }, async (request: FastifyRequest<{ Body: AuthorizeRequest }>, reply: FastifyReply) => {
    try {
      // Validate request
      const parsed = AuthorizeRequestSchema.safeParse(request.body);
      if (!parsed.success) {
        const details = formatZodErrors(parsed.error);
        return reply.code(400).send({
          error: `Validation failed: ${details.map((d: { field: string; message: string }) => `${d.field}: ${d.message}`).join('; ')}`,
          details,
        });
      }
      const validatedRequest = parsed.data;

      // Process authorization
      const result = await engine.authorize(validatedRequest);

      // Set trace header
      reply.header(HEADERS.STIX_TRACE, result.response.trace_id);

      // Set proof token header if present
      if (result.response.proof_token) {
        reply.header(HEADERS.STIX_PROOF, result.response.proof_token);
      }

      const response = {
        ...result.response,
        approval_ticket_id: result.response.approval?.ticket_id,
        policy_id: result.response.policy?.id,
      };

      return reply.code(200).send(response);
    } catch (error) {
      if (isStixError(error)) {
        const stixError = error as StixError;
        return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
      }
      
      request.log.error({ err: error }, 'Authorization failed');
      return reply.code(500).send({
        success: false,
        error: {
          code: 'INTERNAL_ERROR',
          message: 'An unexpected error occurred',
        },
      });
    }
  });

  /**
   * POST /api/v1/outcome
   * Record execution outcome
   */
  fastify.post('/api/v1/outcome', {
    schema: {
      description: 'Record execution outcome',
      tags: ['authorization'],
      body: {
        type: 'object',
        required: ['trace_id', 'status'],
        properties: {
          trace_id: { type: 'string' },
          status: { type: 'string', enum: ['SUCCESS', 'FAILED', 'SKIPPED', 'PENDING'] },
          result_summary: { type: 'string' },
          error_class: { type: 'string' },
          obligations_applied: { type: 'object' },
        },
      },
      response: {
        200: {
          description: 'Outcome recorded',
          type: 'object',
          properties: {
            success: { type: 'boolean' },
            recorded: { type: 'boolean' },
          },
        },
      },
    },
  }, async (request: FastifyRequest, reply: FastifyReply) => {
    try {
      const parsed = OutcomeRequestSchema.safeParse(request.body);
      if (!parsed.success) {
        const details = formatZodErrors(parsed.error);
        return reply.code(400).send({
          error: `Validation failed: ${details.map((d: { field: string; message: string }) => `${d.field}: ${d.message}`).join('; ')}`,
          details,
        });
      }
      const validatedRequest = parsed.data;

      await evidenceClient.recordOutcome({
        trace_id: validatedRequest.trace_id,
        status: validatedRequest.status,
        result_summary: validatedRequest.result_summary,
        error_class: validatedRequest.error_class,
        obligations_applied: validatedRequest.obligations_applied,
      });

      return reply.code(200).send({ success: true, recorded: true });
    } catch (error) {
      if (isStixError(error)) {
        const stixError = error as StixError;
        return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
      }
      
      request.log.error({ err: error }, 'Failed to record outcome');
      return reply.code(500).send({
        success: false,
        error: {
          code: 'INTERNAL_ERROR',
          message: 'Failed to record outcome',
        },
      });
    }
  });

  /**
   * GET /api/v1/authorize/:trace_id
   * Get authorization by trace ID
   */
  fastify.get<{
    Params: { trace_id: string };
  }>('/api/v1/authorize/:trace_id', {
    schema: {
      params: {
        type: 'object',
        properties: {
          trace_id: { type: 'string' },
        },
      },
    },
  }, async (request: FastifyRequest<{ Params: { trace_id: string } }>, reply: FastifyReply) => {
    try {
      const events = await evidenceClient.getTraceEvents(request.params.trace_id);
      if (events.length === 0) {
        return reply.code(404).send({
          success: false,
          error: {
            code: 'TRACE_NOT_FOUND',
            message: `No evidence found for trace_id=${request.params.trace_id}`,
          },
        });
      }

      const latestWithDecision = [...events]
        .reverse()
        .find((event) => typeof event.decision === 'string');

      return reply.code(200).send({
        success: true,
        trace_id: request.params.trace_id,
        event_count: events.length,
        latest_decision: latestWithDecision?.decision,
        latest_reason_code: latestWithDecision?.reason_code,
        events,
      });
    } catch (error) {
      if (isStixError(error)) {
        const stixError = error as StixError;
        return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
      }

      return reply.code(500).send({
        success: false,
        error: {
          code: 'INTERNAL_ERROR',
          message: 'Failed to retrieve trace evidence',
        },
      });
    }
  });
}
