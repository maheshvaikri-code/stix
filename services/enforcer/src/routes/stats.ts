/**
 * Stats Routes
 * Dashboard statistics endpoints backed by Evidence Service data
 */

import type { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import type { EvidenceClient } from '../services/evidence-client.js';

// =============================================================================
// TYPES
// =============================================================================

interface StatsRouteOptions {
  evidenceClient: EvidenceClient;
}

// Backwards-compat shim. Stats are now sourced from evidence service.
export function recordDecisionStat(decision: string): void {
  void decision;
}

// =============================================================================
// ROUTES
// =============================================================================

export async function statsRoutes(
  fastify: FastifyInstance,
  options: StatsRouteOptions
): Promise<void> {
  const { evidenceClient } = options;

  const fetchEventsInRange = async (
    startIso: string,
    endIso: string,
    maxPages = 20
  ) => {
    const all: Array<{ timestamp: string; decision?: string }> = [];
    let page = 1;
    const pageSize = 1000;

    while (page <= maxPages) {
      const result = await evidenceClient.queryEvents({
        page,
        pageSize,
        startTime: startIso,
        endTime: endIso,
      });

      const rows = (result.data ?? result.records ?? [])
        .filter((r) => typeof r.timestamp === 'string')
        .map((r) => ({ timestamp: r.timestamp, decision: r.decision }));

      all.push(...rows);

      const total = result.total ?? all.length;
      if (all.length >= total || rows.length === 0 || result.has_more === false) {
        break;
      }
      page++;
    }

    return all;
  };

  /**
   * GET /api/v1/stats/decisions
   * Get decision statistics
   */
  fastify.get('/api/v1/stats/decisions', {
    schema: {
    },
  }, async (_request: FastifyRequest, reply: FastifyReply) => {
    try {
      const now = Date.now();
      const last48hStartIso = new Date(now - 48 * 60 * 60 * 1000).toISOString();
      const nowIso = new Date(now).toISOString();

      const [stats, last48hEvents] = await Promise.all([
        evidenceClient.getStats(),
        fetchEventsInRange(last48hStartIso, nowIso),
      ]);

      const last24hStart = now - 24 * 60 * 60 * 1000;
      const last24h = last48hEvents.filter(
        (h) => new Date(h.timestamp).getTime() > last24hStart
      ).length;

      const prev24h = last48hEvents.filter((h) => {
        const t = new Date(h.timestamp).getTime();
        return t > now - 48 * 60 * 60 * 1000 && t <= last24hStart;
      }).length;

      const trend = prev24h > 0 ? ((last24h - prev24h) / prev24h) * 100 : 0;
      const byDecision = stats.by_decision ?? {};

      return reply.code(200).send({
        total: stats.total ?? 0,
        allowed: byDecision.ALLOW ?? 0,
        denied: byDecision.DENY ?? 0,
        quarantined: byDecision.QUARANTINE ?? 0,
        last_24h: last24h,
        trend: Math.round(trend * 100) / 100,
      });
    } catch (error) {
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to get stats' },
      });
    }
  });

  /**
   * GET /api/v1/stats/timeseries
   * Get decision time series
   */
  fastify.get<{ Querystring: { period?: string } }>('/api/v1/stats/timeseries', {
    schema: {
      querystring: {
        type: 'object',
        properties: {
          period: { type: 'string', enum: ['24h', '7d', '30d'] },
        },
      },
    },
  }, async (request: FastifyRequest<{ Querystring: { period?: string } }>, reply: FastifyReply) => {
    try {
      const period = request.query.period || '24h';
      const now = Date.now();

      let windowMs: number;
      let bucketMs: number;
      let bucketCount: number;

      switch (period) {
        case '7d':
          windowMs = 7 * 24 * 60 * 60 * 1000;
          bucketMs = 6 * 60 * 60 * 1000; // 6-hour buckets
          bucketCount = 28;
          break;
        case '30d':
          windowMs = 30 * 24 * 60 * 60 * 1000;
          bucketMs = 24 * 60 * 60 * 1000; // 1-day buckets
          bucketCount = 30;
          break;
        default: // 24h
          windowMs = 24 * 60 * 60 * 1000;
          bucketMs = 60 * 60 * 1000; // 1-hour buckets
          bucketCount = 24;
      }

      const windowStartIso = new Date(now - windowMs).toISOString();
      const nowIso = new Date(now).toISOString();
      const events = await fetchEventsInRange(windowStartIso, nowIso);

      // Initialize buckets
      const allowed: { timestamp: string; value: number }[] = [];
      const denied: { timestamp: string; value: number }[] = [];
      const quarantined: { timestamp: string; value: number }[] = [];

      for (let i = bucketCount - 1; i >= 0; i--) {
        const bucketStart = now - (i + 1) * bucketMs;
        const bucketEnd = now - i * bucketMs;

        const bucketDecisions = events.filter((h) => {
          const t = new Date(h.timestamp).getTime();
          return t >= bucketStart && t < bucketEnd;
        });

        const timestamp = new Date(bucketStart).toISOString();
        allowed.push({ timestamp, value: bucketDecisions.filter((d) => d.decision === 'ALLOW').length });
        denied.push({ timestamp, value: bucketDecisions.filter((d) => d.decision === 'DENY').length });
        quarantined.push({ timestamp, value: bucketDecisions.filter((d) => d.decision === 'QUARANTINE').length });
      }

      return reply.code(200).send({
        allowed,
        denied,
        quarantined,
      });
    } catch (error) {
      return reply.code(500).send({
        success: false,
        error: { code: 'INTERNAL_ERROR', message: 'Failed to get timeseries' },
      });
    }
  });
}
