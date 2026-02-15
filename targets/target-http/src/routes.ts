/**
 * STIX Target HTTP - HTTP Routes
 *
 * @module @stix/target-http
 */

import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { type TargetVerifier, type ProtectedContext } from '@stix/target-verifier';
import { isoTimestamp, type Logger } from '@stix/shared';
import { HttpClientService, HttpRequestSchema, type HttpRequest } from './http-client.js';
import type { Config } from './config.js';

// =============================================================================
// AUGMENT FASTIFY TYPES
// =============================================================================

declare module 'fastify' {
  interface FastifyRequest {
    stix?: ProtectedContext;
  }
}

// =============================================================================
// ROUTE OPTIONS
// =============================================================================

interface RouteOptions {
  config: Config;
  logger: Logger;
  httpClient: HttpClientService;
  verifier: TargetVerifier;
  startTime: number;
}

// =============================================================================
// ROUTES
// =============================================================================

export async function registerRoutes(
  fastify: FastifyInstance,
  opts: RouteOptions
): Promise<void> {
  const { config, logger, httpClient, verifier, startTime } = opts;

  // ===========================================================================
  // HEALTH ROUTES
  // ===========================================================================

  fastify.get('/health', async (_request, reply) => {
    const health = {
      status: 'healthy',
      service: config.service.name,
      version: config.service.version,
      uptime_ms: Date.now() - startTime,
      timestamp: isoTimestamp(),
    };

    return reply.send(health);
  });

  fastify.get('/ready', async (_request, reply) => {
    return reply.send({ ready: true });
  });

  // ===========================================================================
  // PROTECTED HTTP PROXY ROUTE
  // ===========================================================================

  fastify.post<{
    Body: HttpRequest;
  }>(
    '/request',
    {
      preHandler: async (request: FastifyRequest, reply: FastifyReply) => {
        const result = await verifier.verifyFromHeaders(
          request.headers as Record<string, string>,
          'http_request',
          'external_api'
        );

        if (!result.valid) {
          logger.warn('HTTP request blocked - verification failed', {
            errors: result.errors,
            ip: request.ip,
          });

          return reply.code(403).send({
            error: 'STIX_VERIFICATION_FAILED',
            message: 'Authorization verification failed',
            errors: result.errors,
          });
        }

        request.stix = {
          verification: result,
          traceId: result.traceId!,
          claims: result.claims!,
          obligations: result.obligations || [],
          reportOutcome: async () => {},
        };
      },
    },
    async (request, reply) => {
      const stix = request.stix!;

      // Validate request body
      const parseResult = HttpRequestSchema.safeParse(request.body);
      if (!parseResult.success) {
        return reply.code(400).send({
          error: 'INVALID_REQUEST',
          message: 'Invalid HTTP request',
          details: parseResult.error.format(),
        });
      }

      const httpRequest = parseResult.data;

      // Log with audit obligation if required
      const auditObligation = stix.obligations.find((o) => o.type === 'AUDIT_LOG');
      if (auditObligation) {
        logger.info('Protected HTTP request', {
          trace_id: stix.traceId,
          actor: stix.claims.actor_id,
          method: httpRequest.method,
          url: httpRequest.url,
          policy_id: stix.claims.policy_id,
        });
      }

      // Execute the HTTP request
      const response = await httpClient.execute(httpRequest, stix.traceId);

      // Log result
      logger.info('HTTP request completed', {
        trace_id: stix.traceId,
        method: httpRequest.method,
        url: httpRequest.url,
        success: response.success,
        status_code: response.statusCode,
        duration_ms: response.duration_ms,
      });

      if (response.success) {
        return reply.code(200).send({
          trace_id: stix.traceId,
          response: {
            statusCode: response.statusCode,
            headers: response.headers,
            body: response.body,
            contentType: response.contentType,
            contentLength: response.contentLength,
          },
          timestamp: response.timestamp,
          duration_ms: response.duration_ms,
        });
      } else {
        return reply.code(502).send({
          trace_id: stix.traceId,
          error: response.error,
          response: response.statusCode > 0
            ? {
                statusCode: response.statusCode,
                headers: response.headers,
                body: response.body,
              }
            : undefined,
          timestamp: response.timestamp,
          duration_ms: response.duration_ms,
        });
      }
    }
  );

  // ===========================================================================
  // BATCH REQUEST
  // ===========================================================================

  fastify.post<{
    Body: { requests: HttpRequest[] };
  }>(
    '/request/batch',
    {
      preHandler: async (request: FastifyRequest, reply: FastifyReply) => {
        const result = await verifier.verifyFromHeaders(
          request.headers as Record<string, string>,
          'http_request_batch',
          'external_api_batch'
        );

        if (!result.valid) {
          return reply.code(403).send({
            error: 'STIX_VERIFICATION_FAILED',
            errors: result.errors,
          });
        }

        request.stix = {
          verification: result,
          traceId: result.traceId!,
          claims: result.claims!,
          obligations: result.obligations || [],
          reportOutcome: async () => {},
        };
      },
    },
    async (request, reply) => {
      const stix = request.stix!;
      const { requests } = request.body;

      if (!requests || requests.length === 0) {
        return reply.code(400).send({
          error: 'INVALID_REQUEST',
          message: 'No requests provided',
        });
      }

      if (requests.length > 10) {
        return reply.code(400).send({
          error: 'BATCH_TOO_LARGE',
          message: 'Maximum 10 requests per batch',
        });
      }

      // Validate all requests
      const validated: HttpRequest[] = [];
      for (const req of requests) {
        const parseResult = HttpRequestSchema.safeParse(req);
        if (!parseResult.success) {
          return reply.code(400).send({
            error: 'INVALID_REQUEST',
            message: 'Invalid request in batch',
            details: parseResult.error.format(),
          });
        }
        validated.push(parseResult.data);
      }

      // Execute all requests
      const responses = await httpClient.executeBatch(validated, stix.traceId);

      const successCount = responses.filter((r) => r.success).length;

      return reply.code(200).send({
        trace_id: stix.traceId,
        total: requests.length,
        success_count: successCount,
        failure_count: requests.length - successCount,
        responses: responses.map((r, i) => ({
          index: i,
          success: r.success,
          statusCode: r.statusCode,
          error: r.error,
          duration_ms: r.duration_ms,
        })),
      });
    }
  );

  // ===========================================================================
  // WEBHOOK FORWARD
  // ===========================================================================

  fastify.post<{
    Body: {
      webhook_url: string;
      payload: Record<string, unknown>;
      headers?: Record<string, string>;
    };
  }>(
    '/webhook',
    {
      preHandler: async (request: FastifyRequest, reply: FastifyReply) => {
        const result = await verifier.verifyFromHeaders(
          request.headers as Record<string, string>,
          'send_webhook',
          'webhook'
        );

        if (!result.valid) {
          return reply.code(403).send({
            error: 'STIX_VERIFICATION_FAILED',
            errors: result.errors,
          });
        }

        request.stix = {
          verification: result,
          traceId: result.traceId!,
          claims: result.claims!,
          obligations: result.obligations || [],
          reportOutcome: async () => {},
        };
      },
    },
    async (request, reply) => {
      const stix = request.stix!;
      const { webhook_url, payload, headers } = request.body;

      // Validate URL
      try {
        new URL(webhook_url);
      } catch {
        return reply.code(400).send({
          error: 'INVALID_URL',
          message: 'Invalid webhook URL',
        });
      }

      // Execute webhook POST
      const response = await httpClient.execute(
        {
          method: 'POST',
          url: webhook_url,
          headers: {
            'Content-Type': 'application/json',
            ...headers,
          },
          body: payload,
        },
        stix.traceId
      );

      logger.info('Webhook delivered', {
        trace_id: stix.traceId,
        webhook_url,
        success: response.success,
        status_code: response.statusCode,
      });

      return reply.code(response.success ? 200 : 502).send({
        trace_id: stix.traceId,
        success: response.success,
        statusCode: response.statusCode,
        error: response.error,
        duration_ms: response.duration_ms,
      });
    }
  );

  // ===========================================================================
  // API CALL WITH RETRY
  // ===========================================================================

  fastify.post<{
    Body: HttpRequest & { retries?: number; retryDelay?: number };
  }>(
    '/request/retry',
    {
      preHandler: async (request: FastifyRequest, reply: FastifyReply) => {
        const result = await verifier.verifyFromHeaders(
          request.headers as Record<string, string>,
          'http_request_retry',
          'external_api'
        );

        if (!result.valid) {
          return reply.code(403).send({
            error: 'STIX_VERIFICATION_FAILED',
            errors: result.errors,
          });
        }

        request.stix = {
          verification: result,
          traceId: result.traceId!,
          claims: result.claims!,
          obligations: result.obligations || [],
          reportOutcome: async () => {},
        };
      },
    },
    async (request, reply) => {
      const stix = request.stix!;
      const { retries = 3, retryDelay = 1000, ...httpRequest } = request.body;

      // Validate request
      const parseResult = HttpRequestSchema.safeParse(httpRequest);
      if (!parseResult.success) {
        return reply.code(400).send({
          error: 'INVALID_REQUEST',
          details: parseResult.error.format(),
        });
      }

      const maxRetries = Math.min(retries, config.http.retries);
      let lastResponse;
      let attempt = 0;

      while (attempt <= maxRetries) {
        lastResponse = await httpClient.execute(
          parseResult.data,
          `${stix.traceId}-attempt-${attempt}`
        );

        if (lastResponse.success) {
          break;
        }

        // Only retry on connection/server errors
        if (lastResponse.statusCode >= 400 && lastResponse.statusCode < 500) {
          break; // Don't retry client errors
        }

        attempt++;
        if (attempt <= maxRetries) {
          await new Promise((r) => setTimeout(r, retryDelay * attempt));
        }
      }

      return reply.code(lastResponse!.success ? 200 : 502).send({
        trace_id: stix.traceId,
        attempts: attempt + 1,
        success: lastResponse!.success,
        response: lastResponse!.success
          ? {
              statusCode: lastResponse!.statusCode,
              headers: lastResponse!.headers,
              body: lastResponse!.body,
            }
          : undefined,
        error: lastResponse!.error,
        duration_ms: lastResponse!.duration_ms,
      });
    }
  );
}
