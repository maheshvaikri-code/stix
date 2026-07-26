/**
 * STIX Evidence Service Routes
 */

import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import {
  isStixError,
  type StixError,
  createErrorResponse,
  EvidenceNotFoundError,
} from '@stix/shared';
import type { EvidenceStore, DecisionEventData, OutcomeEventData } from '../store/index.js';

// =============================================================================
// EVIDENCE ROUTES
// =============================================================================

interface EvidenceRouteOptions {
  store: EvidenceStore;
}

export async function evidenceRoutes(
  fastify: FastifyInstance,
  options: EvidenceRouteOptions
): Promise<void> {
  const { store } = options;

  /**
   * GET /api/v1/evidence
   * List evidence records
   */
  fastify.get<{ Querystring: { page?: string; page_size?: string; limit?: string; decision?: string; trace_id?: string; actor_id?: string; start_time?: string; end_time?: string } }>('/api/v1/evidence', {
    schema: {
    },
  }, async (request, reply) => {
    const parsePositiveInt = (value: string | undefined, fallback: number): number => {
      const parsed = Number.parseInt(value ?? '', 10);
      return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
    };

    const page = parsePositiveInt(request.query.page, 1);
    const pageSize = parsePositiveInt(request.query.page_size ?? request.query.limit, 20);
    let events = await store.getAll();

    // Filter by decision
    if (request.query.decision) {
      events = events.filter(e => e.decision === request.query.decision);
    }

    // Filter by trace_id
    if (request.query.trace_id) {
      events = events.filter(e => e.trace_id === request.query.trace_id);
    }

    // Filter by actor_id
    if (request.query.actor_id) {
      events = events.filter(e => {
        const actorId = (e.actor as any)?.id;
        return actorId === request.query.actor_id;
      });
    }

    // Filter by date range
    if (request.query.start_time || request.query.end_time) {
      const start = request.query.start_time ? new Date(request.query.start_time) : null;
      const end = request.query.end_time ? new Date(request.query.end_time) : null;

      if (start && Number.isNaN(start.getTime())) {
        return reply.code(400).send({ error: 'Invalid start_time' });
      }
      if (end && Number.isNaN(end.getTime())) {
        return reply.code(400).send({ error: 'Invalid end_time' });
      }

      events = events.filter(e => {
        const ts = new Date(e.timestamp).getTime();
        if (start && ts < start.getTime()) return false;
        if (end && ts > end.getTime()) return false;
        return true;
      });
    }

    // Trace lookups and offset pagination should be append-stable so concurrent
    // writes do not shift records from page 1 into page 2.
    const sortAscending = Boolean(request.query.trace_id || request.query.page || request.query.page_size);
    events.sort((a, b) => {
      const timeA = new Date(a.timestamp).getTime();
      const timeB = new Date(b.timestamp).getTime();
      const timeDelta = sortAscending ? timeA - timeB : timeB - timeA;
      return timeDelta || a.event_id.localeCompare(b.event_id);
    });

    const total = events.length;
    const start = (page - 1) * pageSize;
    const paginatedEvents = events.slice(start, start + pageSize);

    // Transform to dashboard format
    const data = paginatedEvents.map(e => ({
      event_id: e.event_id,
      trace_id: e.trace_id,
      timestamp: e.timestamp,
      decision: e.decision,
      actor_id: (e.actor as any)?.id || '',
      actor_type: (e.actor as any)?.type || '',
      action: (e.action as any)?.name || (e.action as any) || '',
      resource_type: (e.resource as any)?.type || '',
      resource_id: (e.resource as any)?.id,
      policy_id: (e as any).policy?.id || '',
      reason_code: e.reason_code || '',
      request_hash: e.integrity?.event_hash || '',
      chain_hash: e.integrity?.prev_hash || '',
      metadata: (e as any).metadata,
    }));

    return reply.code(200).send({
      records: data,
      data,
      total,
      page,
      page_size: pageSize,
      has_more: start + pageSize < total,
    });
  });

  /**
   * POST /api/v1/evidence/decision
   * Record a decision event
   */
  fastify.post<{ Body: DecisionEventData }>('/api/v1/evidence/decision', {
    schema: {
      body: {
        type: 'object',
        required: ['trace_id', 'decision', 'reason_code', 'actor', 'action', 'resource', 'context', 'policy'],
      },
    },
  }, async (request: FastifyRequest<{ Body: DecisionEventData }>, reply: FastifyReply) => {
    try {
      const event = await store.recordDecision(request.body);
      return reply.code(201).send({
        success: true,
        data: {
          event_id: event.event_id,
          trace_id: event.trace_id,
          event_hash: event.integrity.event_hash,
        },
      });
    } catch (error) {
      if (isStixError(error)) {
        const stixError = error as StixError;
        return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
      }
      request.log.error({ err: error }, 'Failed to record decision');
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to record decision' },
      });
    }
  });

  /**
   * POST /api/v1/evidence/outcome
   * Record an outcome event
   */
  fastify.post<{ Body: OutcomeEventData }>('/api/v1/evidence/outcome', {
    schema: {
      body: {
        type: 'object',
        required: ['trace_id', 'status'],
      },
    },
  }, async (request: FastifyRequest<{ Body: OutcomeEventData }>, reply: FastifyReply) => {
    try {
      const event = await store.recordOutcome(request.body);
      return reply.code(201).send({
        success: true,
        data: {
          event_id: event.event_id,
          trace_id: event.trace_id,
          event_hash: event.integrity.event_hash,
        },
      });
    } catch (error) {
      if (isStixError(error)) {
        const stixError = error as StixError;
        return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
      }
      request.log.error({ err: error }, 'Failed to record outcome');
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to record outcome' },
      });
    }
  });

  /**
   * GET /api/v1/evidence/:eventId
   * Get a single event by ID
   */
  fastify.get<{ Params: { eventId: string } }>('/api/v1/evidence/:eventId', {
    schema: {
      params: {
        type: 'object',
        properties: {
          eventId: { type: 'string' },
        },
      },
    },
  }, async (request: FastifyRequest<{ Params: { eventId: string } }>, reply: FastifyReply) => {
    try {
      const event = await store.getEvent(request.params.eventId);
      
      if (!event) {
        throw new EvidenceNotFoundError(request.params.eventId);
      }

      return reply.code(200).send({
        success: true,
        data: event,
      });
    } catch (error) {
      if (isStixError(error)) {
        const stixError = error as StixError;
        return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
      }
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to get event' },
      });
    }
  });

  /**
   * GET /api/v1/evidence/trace/:traceId
   * Get all events for a trace
   */
  fastify.get<{ Params: { traceId: string } }>('/api/v1/evidence/trace/:traceId', {
    schema: {
      params: {
        type: 'object',
        properties: {
          traceId: { type: 'string' },
        },
      },
    },
  }, async (request: FastifyRequest<{ Params: { traceId: string } }>, reply: FastifyReply) => {
    try {
      const events = await store.getEventsByTrace(request.params.traceId);

      // Transform to dashboard format
      const data = events.map(e => ({
        event_id: e.event_id,
        trace_id: e.trace_id,
        timestamp: e.timestamp,
        decision: e.decision,
        actor_id: (e.actor as any)?.id || '',
        actor_type: (e.actor as any)?.type || '',
        action: (e.action as any)?.name || (e.action as any) || '',
        resource_type: (e.resource as any)?.type || '',
        resource_id: (e.resource as any)?.id,
        policy_id: (e as any).policy?.id || '',
        reason_code: e.reason_code || '',
        request_hash: e.integrity?.event_hash || '',
        chain_hash: e.integrity?.prev_hash || '',
        metadata: (e as any).metadata,
      }));

      // Return as array directly (dashboard expects EvidenceRecord[])
      return reply.code(200).send(data);
    } catch (error) {
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to get events' },
      });
    }
  });

  /**
   * GET /api/v1/evidence/verify
   * Verify hash chain integrity (dashboard format)
   */
  fastify.get<{ Querystring: { start_time?: string; end_time?: string } }>('/api/v1/evidence/verify', {
    schema: {
    },
  }, async (request: FastifyRequest<{ Querystring: { start_time?: string; end_time?: string } }>, reply: FastifyReply) => {
    try {
      let eventsInScope = await store.getAll();

      if (request.query.start_time || request.query.end_time) {
        const start = request.query.start_time ? new Date(request.query.start_time) : null;
        const end = request.query.end_time ? new Date(request.query.end_time) : null;

        if (start && Number.isNaN(start.getTime())) {
          return reply.code(400).send({ error: 'Invalid start_time' });
        }
        if (end && Number.isNaN(end.getTime())) {
          return reply.code(400).send({ error: 'Invalid end_time' });
        }

        eventsInScope = eventsInScope.filter(e => {
          const ts = new Date(e.timestamp).getTime();
          if (start && ts < start.getTime()) return false;
          if (end && ts > end.getTime()) return false;
          return true;
        });
      }

      const traceIds = Array.from(new Set(eventsInScope.map(e => e.trace_id)));
      const errors: string[] = [];
      let firstInvalid: string | undefined;
      let recordsVerified = 0;

      for (const traceId of traceIds) {
        const result = await store.verifyChain(traceId);
        recordsVerified += result.eventCount;

        if (!result.valid) {
          const reason = result.errors[0] ?? 'Hash chain verification failed';
          errors.push(`trace ${traceId}: ${reason}`);
          if (!firstInvalid) {
            firstInvalid = result.brokenAtEventId ?? result.firstEventId ?? traceId;
          }
        }
      }

      return reply.code(200).send({
        valid: errors.length === 0,
        records_verified: recordsVerified,
        traces_verified: traceIds.length,
        errors: errors.length > 0 ? errors : undefined,
        first_invalid: firstInvalid,
      });
    } catch (error) {
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to verify chain' },
      });
    }
  });

  /**
   * GET /api/v1/evidence/verify/:traceId
   * Verify hash chain integrity for a trace
   */
  fastify.get<{ Params: { traceId: string } }>('/api/v1/evidence/verify/:traceId', {
    schema: {
      params: {
        type: 'object',
        properties: {
          traceId: { type: 'string' },
        },
      },
    },
  }, async (request: FastifyRequest<{ Params: { traceId: string } }>, reply: FastifyReply) => {
    try {
      const result = await store.verifyChain(request.params.traceId);

      return reply.code(200).send({
        valid: result.valid,
        records_verified: result.eventCount,
        errors: result.errors.length > 0 ? result.errors : undefined,
        first_invalid: result.brokenAtEventId,
      });
    } catch (error) {
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to verify chain' },
      });
    }
  });

  /**
   * GET /api/v1/evidence/actor/:actorId
   * Get events by actor ID
   */
  fastify.get<{
    Params: { actorId: string };
    Querystring: { limit?: number; offset?: number; startDate?: string; endDate?: string };
  }>('/api/v1/evidence/actor/:actorId', {
    schema: {
    },
  }, async (request, reply) => {
    try {
      const events = await store.getEventsByActor(request.params.actorId, {
        limit: request.query.limit,
        offset: request.query.offset,
        startDate: request.query.startDate,
        endDate: request.query.endDate,
      });

      return reply.code(200).send({
        success: true,
        data: events,
        meta: {
          actor_id: request.params.actorId,
          event_count: events.length,
        },
      });
    } catch (error) {
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to get events' },
      });
    }
  });

  /**
   * GET /api/v1/evidence/resource/:resourceType/:resourceId?
   * Get events by resource
   */
  fastify.get<{
    Params: { resourceType: string; resourceId?: string };
    Querystring: { limit?: number; offset?: number };
  }>('/api/v1/evidence/resource/:resourceType/:resourceId?', {
    schema: {
    },
  }, async (request, reply) => {
    try {
      const events = await store.getEventsByResource(
        request.params.resourceType,
        request.params.resourceId,
        {
          limit: request.query.limit,
          offset: request.query.offset,
        }
      );

      return reply.code(200).send({
        success: true,
        data: events,
        meta: {
          resource_type: request.params.resourceType,
          resource_id: request.params.resourceId,
          event_count: events.length,
        },
      });
    } catch (error) {
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to get events' },
      });
    }
  });

  /**
   * GET /api/v1/evidence/stats
   * Get evidence statistics
   */
  fastify.get('/api/v1/evidence/stats', {
    schema: {
    },
  }, async (_request, reply) => {
    try {
      const stats = await store.getStats();

      // Return stats directly (dashboard expects this format)
      return reply.code(200).send(stats);
    } catch (error) {
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to get stats' },
      });
    }
  });

  /**
   * GET /api/v1/evidence/export
   * Export the filtered evidence ledger for dashboard and compliance use.
   */
  fastify.get<{
    Querystring: {
      start_time?: string;
      end_time?: string;
      format?: 'json' | 'jsonl' | 'csv';
    };
  }>('/api/v1/evidence/export', async (request, reply) => {
    try {
      const start = request.query.start_time ? new Date(request.query.start_time) : undefined;
      const end = request.query.end_time ? new Date(request.query.end_time) : undefined;

      if (start && Number.isNaN(start.getTime())) {
        return reply.code(400).send({ error: 'Invalid start_time' });
      }
      if (end && Number.isNaN(end.getTime())) {
        return reply.code(400).send({ error: 'Invalid end_time' });
      }

      const events = (await store.getAll())
        .filter(event => {
          const timestamp = new Date(event.timestamp).getTime();
          if (start && timestamp < start.getTime()) return false;
          if (end && timestamp > end.getTime()) return false;
          return true;
        })
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

      const format = request.query.format ?? 'json';
      if (format === 'csv') {
        return reply
          .code(200)
          .header('Content-Type', 'text/csv')
          .header('Content-Disposition', 'attachment; filename="stix-evidence.csv"')
          .send(eventsToCSV(events));
      }

      if (format === 'jsonl') {
        return reply
          .code(200)
          .header('Content-Type', 'application/x-ndjson')
          .header('Content-Disposition', 'attachment; filename="stix-evidence.jsonl"')
          .send(events.map(event => JSON.stringify(event)).join('\n'));
      }

      return reply
        .code(200)
        .header('Content-Type', 'application/json')
        .header('Content-Disposition', 'attachment; filename="stix-evidence.json"')
        .send({ records: events, exported_at: new Date().toISOString() });
    } catch (error) {
      request.log.error({ err: error }, 'Failed to export evidence');
      return reply.code(500).send({
        success: false,
        error: { code: 'EXPORT_FAILED', message: 'Failed to export evidence' },
      });
    }
  });

  /**
   * GET /api/v1/evidence/export/:traceId
   * Export trace events
   */
  fastify.get<{
    Params: { traceId: string };
    Querystring: { format?: 'json' | 'csv' };
  }>('/api/v1/evidence/export/:traceId', {
    schema: {
    },
  }, async (request, reply) => {
    try {
      const events = await store.getEventsByTrace(request.params.traceId);
      const format = request.query.format ?? 'json';

      if (format === 'csv') {
        const csv = eventsToCSV(events);
        return reply
          .code(200)
          .header('Content-Type', 'text/csv')
          .header('Content-Disposition', `attachment; filename="trace_${request.params.traceId}.csv"`)
          .send(csv);
      }

      return reply.code(200).send({
        success: true,
        data: events,
        meta: {
          trace_id: request.params.traceId,
          event_count: events.length,
          exported_at: new Date().toISOString(),
        },
      });
    } catch (error) {
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to export trace' },
      });
    }
  });
}

/**
 * Convert events to CSV format
 */
function eventsToCSV(events: any[]): string {
  if (events.length === 0) return '';

  const headers = [
    'event_id',
    'trace_id',
    'event_type',
    'timestamp',
    'decision',
    'reason_code',
    'actor_id',
    'actor_type',
    'action',
    'resource_type',
    'resource_id',
    'event_hash',
  ];

  const rows = events.map(e => [
    e.event_id,
    e.trace_id,
    e.event_type,
    e.timestamp,
    e.decision ?? '',
    e.reason_code ?? '',
    e.actor?.id ?? '',
    e.actor?.type ?? '',
    e.action?.name ?? '',
    e.resource?.type ?? '',
    e.resource?.id ?? '',
    e.integrity?.event_hash ?? '',
  ].map(v => `"${String(v).replace(/"/g, '""')}"`).join(','));

  return [headers.join(','), ...rows].join('\n');
}

// =============================================================================
// HEALTH ROUTES
// =============================================================================

interface HealthRouteOptions {
  store: EvidenceStore;
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
      service: 'stix-evidence',
      version,
      uptime: Math.floor((Date.now() - startTime) / 1000),
      timestamp: new Date().toISOString(),
    });
  });

  fastify.get('/ready', async (_request, reply) => {
    const storeHealthy = await store.health();

    return reply.code(storeHealthy ? 200 : 503).send({
      status: storeHealthy ? 'healthy' : 'unhealthy',
      service: 'stix-evidence',
      version,
      checks: {
        store: { status: storeHealthy ? 'pass' : 'fail' },
      },
    });
  });
}
