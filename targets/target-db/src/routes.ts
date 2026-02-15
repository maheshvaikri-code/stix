/**
 * STIX Target DB - HTTP Routes
 *
 * @module @stix/target-db
 */

import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { type TargetVerifier, type ProtectedContext } from '@stix/target-verifier';
import { isoTimestamp, type Logger } from '@stix/shared';
import { DatabaseService, QueryRequestSchema, type QueryRequest } from './database.js';
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
  database: DatabaseService;
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
  const { config, logger, database, verifier, startTime } = opts;

  // ===========================================================================
  // HEALTH ROUTES
  // ===========================================================================

  fastify.get('/health', async (_request, reply) => {
    const dbHealth = await database.healthCheck();

    const health = {
      status: dbHealth.healthy ? 'healthy' : 'degraded',
      service: config.service.name,
      version: config.service.version,
      uptime_ms: Date.now() - startTime,
      timestamp: isoTimestamp(),
      checks: {
        database: dbHealth,
      },
    };

    return reply.code(dbHealth.healthy ? 200 : 503).send(health);
  });

  fastify.get('/ready', async (_request, reply) => {
    const dbHealth = await database.healthCheck();

    if (!dbHealth.healthy) {
      return reply.code(503).send({
        ready: false,
        message: 'Database not ready',
      });
    }

    return reply.send({ ready: true });
  });

  // ===========================================================================
  // PROTECTED QUERY ROUTE
  // ===========================================================================

  fastify.post<{
    Body: QueryRequest;
  }>(
    '/query',
    {
      preHandler: async (request: FastifyRequest, reply: FastifyReply) => {
        // Determine action from query type
        const body = request.body as QueryRequest;
        const sql = body?.sql?.trim().toUpperCase() || '';
        let action = 'db_query';

        if (sql.startsWith('SELECT')) action = 'db_read';
        else if (sql.startsWith('INSERT')) action = 'db_write';
        else if (sql.startsWith('UPDATE')) action = 'db_write';
        else if (sql.startsWith('DELETE')) action = 'db_delete';
        else if (sql.startsWith('CREATE') || sql.startsWith('ALTER') || sql.startsWith('DROP')) {
          action = 'db_ddl';
        }

        const result = await verifier.verifyFromHeaders(
          request.headers as Record<string, string>,
          action,
          'database'
        );

        if (!result.valid) {
          logger.warn('Database query blocked - verification failed', {
            action,
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
      const parseResult = QueryRequestSchema.safeParse(request.body);
      if (!parseResult.success) {
        return reply.code(400).send({
          error: 'INVALID_REQUEST',
          message: 'Invalid query request',
          details: parseResult.error.format(),
        });
      }

      const queryRequest = parseResult.data;

      // Check for audit obligations
      const auditObligation = stix.obligations.find((o) => o.type === 'AUDIT_LOG');
      if (auditObligation) {
        logger.info('Protected database query', {
          trace_id: stix.traceId,
          actor: stix.claims.actor_id,
          sql_preview: queryRequest.sql.substring(0, 100),
          policy_id: stix.claims.policy_id,
        });
      }

      // Execute the query
      const result = await database.execute(queryRequest, stix.traceId);

      // Check for data masking obligations
      const maskObligation = stix.obligations.find((o) => o.type === 'DATA_MASK');
      if (maskObligation && result.rows) {
        // Apply masking to sensitive fields
        // In a real implementation, mask fields based on obligation params
        logger.debug('Data masking obligation present', {
          trace_id: stix.traceId,
        });
      }

      // Log result
      logger.info('Query executed', {
        trace_id: stix.traceId,
        success: result.success,
        operation: result.operation,
        row_count: result.rowCount,
        duration_ms: result.duration_ms,
      });

      if (result.success) {
        return reply.code(200).send({
          trace_id: stix.traceId,
          operation: result.operation,
          rows: result.rows,
          row_count: result.rowCount,
          affected_rows: result.affectedRows,
          insert_id: result.insertId,
          fields: result.fields,
          timestamp: result.timestamp,
          duration_ms: result.duration_ms,
        });
      } else {
        return reply.code(400).send({
          trace_id: stix.traceId,
          error: result.error,
          timestamp: result.timestamp,
          duration_ms: result.duration_ms,
        });
      }
    }
  );

  // ===========================================================================
  // BATCH QUERY ROUTE
  // ===========================================================================

  fastify.post<{
    Body: { queries: QueryRequest[] };
  }>(
    '/query/batch',
    {
      preHandler: async (request: FastifyRequest, reply: FastifyReply) => {
        const result = await verifier.verifyFromHeaders(
          request.headers as Record<string, string>,
          'db_batch',
          'database'
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
      const { queries } = request.body;

      if (!queries || queries.length === 0) {
        return reply.code(400).send({
          error: 'INVALID_REQUEST',
          message: 'No queries provided',
        });
      }

      if (queries.length > 10) {
        return reply.code(400).send({
          error: 'BATCH_TOO_LARGE',
          message: 'Maximum 10 queries per batch',
        });
      }

      // Execute queries sequentially
      const results = [];
      for (let i = 0; i < queries.length; i++) {
        const parseResult = QueryRequestSchema.safeParse(queries[i]);
        if (!parseResult.success) {
          results.push({
            index: i,
            success: false,
            error: { code: 'INVALID_REQUEST', message: 'Invalid query' },
          });
          continue;
        }

        const result = await database.execute(
          parseResult.data,
          `${stix.traceId}-${i}`
        );

        results.push({
          index: i,
          success: result.success,
          operation: result.operation,
          rowCount: result.rowCount,
          affectedRows: result.affectedRows,
          error: result.error,
          duration_ms: result.duration_ms,
        });
      }

      const successCount = results.filter((r) => r.success).length;

      return reply.code(200).send({
        trace_id: stix.traceId,
        total: queries.length,
        success_count: successCount,
        failure_count: queries.length - successCount,
        results,
      });
    }
  );

  // ===========================================================================
  // TRANSACTION ROUTE
  // ===========================================================================

  fastify.post<{
    Body: { queries: QueryRequest[]; rollbackOnError?: boolean };
  }>(
    '/transaction',
    {
      preHandler: async (request: FastifyRequest, reply: FastifyReply) => {
        const result = await verifier.verifyFromHeaders(
          request.headers as Record<string, string>,
          'db_transaction',
          'database'
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
      const { queries, rollbackOnError = true } = request.body;

      if (!queries || queries.length === 0) {
        return reply.code(400).send({
          error: 'INVALID_REQUEST',
          message: 'No queries provided',
        });
      }

      logger.info('Starting transaction', {
        trace_id: stix.traceId,
        query_count: queries.length,
        rollback_on_error: rollbackOnError,
      });

      // Begin transaction
      await database.execute({ sql: 'BEGIN' }, `${stix.traceId}-begin`);

      const results = [];
      let success = true;

      try {
        for (let i = 0; i < queries.length; i++) {
          const parseResult = QueryRequestSchema.safeParse(queries[i]);
          if (!parseResult.success) {
            throw new Error(`Invalid query at index ${i}`);
          }

          const result = await database.execute(
            parseResult.data,
            `${stix.traceId}-${i}`
          );

          if (!result.success) {
            if (rollbackOnError) {
              throw new Error(result.error?.message || 'Query failed');
            }
          }

          results.push({
            index: i,
            success: result.success,
            operation: result.operation,
            affectedRows: result.affectedRows,
            error: result.error,
          });
        }

        // Commit transaction
        await database.execute({ sql: 'COMMIT' }, `${stix.traceId}-commit`);

        logger.info('Transaction committed', {
          trace_id: stix.traceId,
          query_count: queries.length,
        });
      } catch (error) {
        success = false;

        // Rollback transaction
        await database.execute({ sql: 'ROLLBACK' }, `${stix.traceId}-rollback`);

        logger.warn('Transaction rolled back', {
          trace_id: stix.traceId,
          error: (error as Error).message,
        });
      }

      return reply.code(success ? 200 : 400).send({
        trace_id: stix.traceId,
        success,
        committed: success,
        results,
      });
    }
  );
}
