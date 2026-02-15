/**
 * STIX Target Email - HTTP Routes
 *
 * @module @stix/target-email
 */

import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { z } from 'zod';
import { createVerifier, type TargetVerifier, type ProtectedContext } from '@stix/target-verifier';
import { isoTimestamp, type Logger } from '@stix/shared';
import { EmailService, SendEmailRequestSchema, type SendEmailRequest } from './email.js';
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
  emailService: EmailService;
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
  const { config, logger, emailService, verifier, startTime } = opts;

  // ===========================================================================
  // HEALTH ROUTES
  // ===========================================================================

  fastify.get('/health', async (_request, reply) => {
    const emailHealth = await emailService.healthCheck();

    const health = {
      status: emailHealth.healthy ? 'healthy' : 'degraded',
      service: config.service.name,
      version: config.service.version,
      uptime_ms: Date.now() - startTime,
      timestamp: isoTimestamp(),
      checks: {
        email: emailHealth,
      },
    };

    return reply.code(emailHealth.healthy ? 200 : 503).send(health);
  });

  fastify.get('/ready', async (_request, reply) => {
    const emailHealth = await emailService.healthCheck();

    if (!emailHealth.healthy) {
      return reply.code(503).send({
        ready: false,
        message: 'Email service not ready',
      });
    }

    return reply.send({ ready: true });
  });

  // ===========================================================================
  // PROTECTED EMAIL ROUTE
  // ===========================================================================

  fastify.post<{
    Body: SendEmailRequest;
  }>(
    '/send',
    {
      preHandler: async (request: FastifyRequest, reply: FastifyReply) => {
        // Verify STIX proof token
        const result = await verifier.verifyFromHeaders(
          request.headers as Record<string, string>,
          'send_email',
          'email'
        );

        if (!result.valid) {
          logger.warn('Email send blocked - verification failed', {
            errors: result.errors,
            ip: request.ip,
          });

          return reply.code(403).send({
            error: 'STIX_VERIFICATION_FAILED',
            message: 'Authorization verification failed',
            errors: result.errors,
          });
        }

        // Attach STIX context to request
        request.stix = {
          verification: result,
          traceId: result.traceId!,
          claims: result.claims!,
          obligations: result.obligations || [],
          reportOutcome: async () => {},
        };
      },
      schema: {
        body: {
          type: 'object',
          required: ['to', 'subject', 'body'],
          properties: {
            to: { oneOf: [{ type: 'string' }, { type: 'array', items: { type: 'string' } }] },
            cc: { oneOf: [{ type: 'string' }, { type: 'array', items: { type: 'string' } }] },
            bcc: { oneOf: [{ type: 'string' }, { type: 'array', items: { type: 'string' } }] },
            subject: { type: 'string' },
            body: {
              type: 'object',
              properties: {
                text: { type: 'string' },
                html: { type: 'string' },
              },
            },
            replyTo: { type: 'string' },
            priority: { type: 'string', enum: ['high', 'normal', 'low'] },
          },
        },
      },
    },
    async (request, reply) => {
      const stix = request.stix!;

      // Validate request body
      const parseResult = SendEmailRequestSchema.safeParse(request.body);
      if (!parseResult.success) {
        return reply.code(400).send({
          error: 'INVALID_REQUEST',
          message: 'Invalid email request',
          details: parseResult.error.format(),
        });
      }

      const emailRequest = parseResult.data;

      // Check for data masking obligations
      const maskingObligation = stix.obligations.find(
        (o) => o.type === 'DATA_MASK' || o.type === 'REDACT_FIELDS'
      );

      if (maskingObligation) {
        logger.info('Applying data masking obligation', {
          trace_id: stix.traceId,
          obligation: maskingObligation.type,
        });
        // In a real implementation, apply masking to email content
      }

      // Check for logging obligations
      const logObligation = stix.obligations.find(
        (o) => o.type === 'LOG_LEVEL' || o.type === 'AUDIT_LOG'
      );

      if (logObligation) {
        logger.info('Protected email send attempt', {
          trace_id: stix.traceId,
          actor: stix.claims.actor_id,
          to: emailRequest.to,
          subject: emailRequest.subject,
          policy_id: stix.claims.policy_id,
        });
      }

      // Send the email
      const result = await emailService.send(emailRequest, stix.traceId);

      // Log result
      logger.info('Email send completed', {
        trace_id: stix.traceId,
        success: result.success,
        message_id: result.messageId,
        duration_ms: result.duration_ms,
      });

      if (result.success) {
        return reply.code(200).send({
          success: true,
          trace_id: stix.traceId,
          message_id: result.messageId,
          recipients: result.recipients,
          timestamp: result.timestamp,
        });
      } else {
        return reply.code(500).send({
          success: false,
          trace_id: stix.traceId,
          error: result.error,
          timestamp: result.timestamp,
        });
      }
    }
  );

  // ===========================================================================
  // BATCH SEND (requires higher authorization level)
  // ===========================================================================

  fastify.post<{
    Body: { emails: SendEmailRequest[] };
  }>(
    '/send/batch',
    {
      preHandler: async (request: FastifyRequest, reply: FastifyReply) => {
        // Verify STIX proof token with batch action
        const result = await verifier.verifyFromHeaders(
          request.headers as Record<string, string>,
          'send_email_batch',
          'email_batch'
        );

        if (!result.valid) {
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
      const { emails } = request.body;

      // Validate batch size
      if (!emails || emails.length === 0) {
        return reply.code(400).send({
          error: 'INVALID_REQUEST',
          message: 'No emails provided',
        });
      }

      if (emails.length > 100) {
        return reply.code(400).send({
          error: 'BATCH_TOO_LARGE',
          message: 'Maximum 100 emails per batch',
        });
      }

      // Send emails
      const results = await Promise.all(
        emails.map(async (email, index) => {
          const parseResult = SendEmailRequestSchema.safeParse(email);
          if (!parseResult.success) {
            return {
              index,
              success: false,
              error: {
                code: 'INVALID_REQUEST',
                message: 'Invalid email request',
              },
            };
          }

          const result = await emailService.send(
            parseResult.data,
            `${stix.traceId}-${index}`
          );

          return {
            index,
            success: result.success,
            messageId: result.messageId,
            error: result.error,
          };
        })
      );

      const successCount = results.filter((r) => r.success).length;

      return reply.code(200).send({
        trace_id: stix.traceId,
        total: emails.length,
        success_count: successCount,
        failure_count: emails.length - successCount,
        results,
      });
    }
  );

  // ===========================================================================
  // TEMPLATE SEND
  // ===========================================================================

  fastify.post<{
    Body: {
      template_id: string;
      to: string | string[];
      variables: Record<string, string>;
    };
  }>(
    '/send/template',
    {
      preHandler: async (request: FastifyRequest, reply: FastifyReply) => {
        const result = await verifier.verifyFromHeaders(
          request.headers as Record<string, string>,
          'send_email_template',
          'email_template'
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
      const { template_id, to, variables } = request.body;

      // In a real implementation, load template from database
      // For now, use a simple placeholder replacement

      logger.info('Template email requested', {
        trace_id: stix.traceId,
        template_id,
        to,
      });

      // Placeholder: generate email from template
      const emailRequest: SendEmailRequest = {
        to,
        subject: `Template: ${template_id}`,
        body: {
          text: `Template ${template_id} with variables: ${JSON.stringify(variables)}`,
        },
      };

      const result = await emailService.send(emailRequest, stix.traceId);

      return reply.code(result.success ? 200 : 500).send({
        trace_id: stix.traceId,
        template_id,
        success: result.success,
        message_id: result.messageId,
        error: result.error,
      });
    }
  );
}
