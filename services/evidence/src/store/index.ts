/**
 * STIX Evidence Store
 * Storage backends for evidence management
 */

import {
  type EvidenceEvent,
  type SigningKey,
  type Logger,
  EvidenceNotFoundError,
} from '@stix/shared';
import type { Config } from '../config/index.js';
import { Pool } from 'pg';
import {
  HashChainManager,
  type ChainVerificationResult,
  type DecisionEventData,
  type OutcomeEventData,
} from '../core/chain.js';

// =============================================================================
// TYPES
// =============================================================================

export interface QueryOptions {
  limit?: number;
  offset?: number;
  startDate?: string;
  endDate?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface EvidenceStore {
  recordDecision(data: DecisionEventData): Promise<EvidenceEvent>;
  recordOutcome(data: OutcomeEventData): Promise<EvidenceEvent>;
  getEvent(eventId: string): Promise<EvidenceEvent | null>;
  getEventsByTrace(traceId: string): Promise<EvidenceEvent[]>;
  getEventsByActor(actorId: string, options?: QueryOptions): Promise<EvidenceEvent[]>;
  getEventsByResource(resourceType: string, resourceId?: string, options?: QueryOptions): Promise<EvidenceEvent[]>;
  verifyChain(traceId: string): Promise<ChainVerificationResult>;
  getStats(): Promise<EvidenceStats>;
  health(): Promise<boolean>;
  getAll(): Promise<EvidenceEvent[]>;
}

export interface EvidenceStats {
  total: number;
  by_decision: Record<string, number>;
  by_actor_type: Record<string, number>;
  by_action: Record<string, number>;
  unique_actors: number;
  unique_traces: number;
}

// =============================================================================
// IN-MEMORY EVIDENCE STORE
// =============================================================================

export class InMemoryEvidenceStore implements EvidenceStore {
  private events: Map<string, EvidenceEvent> = new Map();
  private traceIndex: Map<string, string[]> = new Map();
  private actorIndex: Map<string, string[]> = new Map();
  private resourceIndex: Map<string, string[]> = new Map();
  private chainManager: HashChainManager;
  private logger: Logger;

  constructor(logger: Logger, signingKey: SigningKey | null) {
    this.logger = logger.child({ component: 'InMemoryEvidenceStore' });
    this.chainManager = new HashChainManager(signingKey);
  }

  async recordDecision(data: DecisionEventData): Promise<EvidenceEvent> {
    const event = this.chainManager.createDecisionEvent(data);
    this.storeEvent(event);

    this.logger.debug('Recorded decision event', {
      event_id: event.event_id,
      trace_id: event.trace_id,
      decision: data.decision,
    });

    return event;
  }

  async recordOutcome(data: OutcomeEventData): Promise<EvidenceEvent> {
    const event = this.chainManager.createOutcomeEvent(data);
    this.storeEvent(event);

    this.logger.debug('Recorded outcome event', {
      event_id: event.event_id,
      trace_id: event.trace_id,
      status: data.status,
    });

    return event;
  }

  async getEvent(eventId: string): Promise<EvidenceEvent | null> {
    return this.events.get(eventId) ?? null;
  }

  async getEventsByTrace(traceId: string): Promise<EvidenceEvent[]> {
    const eventIds = this.traceIndex.get(traceId) ?? [];
    const events = eventIds
      .map(id => this.events.get(id))
      .filter((e): e is EvidenceEvent => e !== undefined);

    events.sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    return events;
  }

  async getEventsByActor(actorId: string, options?: QueryOptions): Promise<EvidenceEvent[]> {
    const eventIds = this.actorIndex.get(actorId) ?? [];
    let events = eventIds
      .map(id => this.events.get(id))
      .filter((e): e is EvidenceEvent => e !== undefined);

    events = this.applyQueryOptions(events, options);
    return events;
  }

  async getEventsByResource(
    resourceType: string,
    resourceId?: string,
    options?: QueryOptions
  ): Promise<EvidenceEvent[]> {
    const key = resourceId ? `${resourceType}:${resourceId}` : resourceType;
    const eventIds = this.resourceIndex.get(key) ?? [];

    let events = eventIds
      .map(id => this.events.get(id))
      .filter((e): e is EvidenceEvent => e !== undefined);

    if (!resourceId) {
      const typeOnlyIds = this.resourceIndex.get(resourceType) ?? [];
      const allIds = new Set([...eventIds, ...typeOnlyIds]);
      events = Array.from(allIds)
        .map(id => this.events.get(id))
        .filter((e): e is EvidenceEvent => e !== undefined);
    }

    events = this.applyQueryOptions(events, options);
    return events;
  }

  async verifyChain(traceId: string): Promise<ChainVerificationResult> {
    const events = await this.getEventsByTrace(traceId);
    return this.chainManager.verifyChain(events);
  }

  async getStats(): Promise<EvidenceStats> {
    const events = Array.from(this.events.values());
    return calculateStats(events, this.traceIndex.size);
  }

  async health(): Promise<boolean> {
    return true;
  }

  async getAll(): Promise<EvidenceEvent[]> {
    return Array.from(this.events.values());
  }

  private storeEvent(event: EvidenceEvent): void {
    this.events.set(event.event_id, event);

    const traceEvents = this.traceIndex.get(event.trace_id) ?? [];
    traceEvents.push(event.event_id);
    this.traceIndex.set(event.trace_id, traceEvents);

    if (event.event_type === 'DECISION' && event.actor) {
      const actorId = (event.actor as { id?: string }).id;
      if (actorId) {
        const actorEvents = this.actorIndex.get(actorId) ?? [];
        actorEvents.push(event.event_id);
        this.actorIndex.set(actorId, actorEvents);
      }
    }

    if (event.event_type === 'DECISION' && event.resource) {
      const resourceType = (event.resource as { type?: string }).type;
      const resourceId = (event.resource as { id?: string }).id;
      if (!resourceType) return;

      const typeEvents = this.resourceIndex.get(resourceType) ?? [];
      typeEvents.push(event.event_id);
      this.resourceIndex.set(resourceType, typeEvents);

      if (resourceId) {
        const fullKey = `${resourceType}:${resourceId}`;
        const fullEvents = this.resourceIndex.get(fullKey) ?? [];
        fullEvents.push(event.event_id);
        this.resourceIndex.set(fullKey, fullEvents);
      }
    }
  }

  private applyQueryOptions(events: EvidenceEvent[], options?: QueryOptions): EvidenceEvent[] {
    if (!options) return events;

    if (options.startDate) {
      const start = new Date(options.startDate).getTime();
      events = events.filter(e => new Date(e.timestamp).getTime() >= start);
    }
    if (options.endDate) {
      const end = new Date(options.endDate).getTime();
      events = events.filter(e => new Date(e.timestamp).getTime() <= end);
    }

    const sortOrder = options.sortOrder ?? 'desc';
    events.sort((a, b) => {
      const timeA = new Date(a.timestamp).getTime();
      const timeB = new Date(b.timestamp).getTime();
      return sortOrder === 'asc' ? timeA - timeB : timeB - timeA;
    });

    const offset = options.offset ?? 0;
    const limit = options.limit ?? 100;
    return events.slice(offset, offset + limit);
  }
}

// =============================================================================
// POSTGRES EVIDENCE STORE
// =============================================================================

type DbRow = {
  event_id: string;
  trace_id: string;
  event_data: EvidenceEvent;
  timestamp: string;
  actor_id: string | null;
  actor_type: string | null;
  action_name: string | null;
  resource_type: string | null;
  resource_id: string | null;
  decision: string | null;
};

export class PostgresEvidenceStore implements EvidenceStore {
  private readonly logger: Logger;
  private readonly pool: Pool;
  private readonly chainManager: HashChainManager;

  constructor(logger: Logger, signingKey: SigningKey | null, postgresUrl: string) {
    this.logger = logger.child({ component: 'PostgresEvidenceStore' });
    this.pool = new Pool({
      connectionString: postgresUrl,
      max: 20,
      min: 2,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
    });
    this.chainManager = new HashChainManager(signingKey);
  }

  async initialize(): Promise<void> {
    await this.pool.query(`
      CREATE TABLE IF NOT EXISTS stix_evidence_events (
        event_id TEXT PRIMARY KEY,
        trace_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        actor_id TEXT,
        actor_type TEXT,
        action_name TEXT,
        resource_type TEXT,
        resource_id TEXT,
        decision TEXT,
        event_data JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );
      CREATE INDEX IF NOT EXISTS idx_stix_evidence_trace ON stix_evidence_events(trace_id);
      CREATE INDEX IF NOT EXISTS idx_stix_evidence_timestamp ON stix_evidence_events(timestamp);
      CREATE INDEX IF NOT EXISTS idx_stix_evidence_actor ON stix_evidence_events(actor_id);
      CREATE INDEX IF NOT EXISTS idx_stix_evidence_resource ON stix_evidence_events(resource_type, resource_id);
      CREATE INDEX IF NOT EXISTS idx_stix_evidence_decision ON stix_evidence_events(decision);
    `);

    // Restore chain heads so prev_hash continuity survives restarts.
    const result = await this.pool.query<{ trace_id: string; event_hash: string }>(
      `SELECT DISTINCT ON (trace_id)
         trace_id,
         event_data->'integrity'->>'event_hash' AS event_hash
       FROM stix_evidence_events
       ORDER BY trace_id, timestamp DESC, created_at DESC`
    );

    for (const row of result.rows) {
      if (row.event_hash) {
        this.chainManager.initializeChainHead(row.trace_id, row.event_hash);
      }
    }
  }

  async recordDecision(data: DecisionEventData): Promise<EvidenceEvent> {
    const event = this.chainManager.createDecisionEvent(data);
    await this.insertEvent(event);
    return event;
  }

  async recordOutcome(data: OutcomeEventData): Promise<EvidenceEvent> {
    const event = this.chainManager.createOutcomeEvent(data);
    await this.insertEvent(event);
    return event;
  }

  async getEvent(eventId: string): Promise<EvidenceEvent | null> {
    const result = await this.pool.query<DbRow>(
      'SELECT event_id, trace_id, event_data, timestamp, actor_id, actor_type, action_name, resource_type, resource_id, decision FROM stix_evidence_events WHERE event_id = $1',
      [eventId]
    );
    if (result.rows.length === 0) {
      return null;
    }
    return this.toEvent(result.rows[0]);
  }

  async getEventsByTrace(traceId: string): Promise<EvidenceEvent[]> {
    const result = await this.pool.query<DbRow>(
      `SELECT event_id, trace_id, event_data, timestamp, actor_id, actor_type, action_name, resource_type, resource_id, decision
       FROM stix_evidence_events
       WHERE trace_id = $1
       ORDER BY timestamp ASC, created_at ASC`,
      [traceId]
    );
    return result.rows.map(row => this.toEvent(row));
  }

  async getEventsByActor(actorId: string, options?: QueryOptions): Promise<EvidenceEvent[]> {
    const params: unknown[] = [actorId];
    let where = 'WHERE actor_id = $1';
    let idx = 2;

    if (options?.startDate) {
      where += ` AND timestamp >= $${idx++}`;
      params.push(options.startDate);
    }
    if (options?.endDate) {
      where += ` AND timestamp <= $${idx++}`;
      params.push(options.endDate);
    }

    const sortOrder = options?.sortOrder === 'asc' ? 'ASC' : 'DESC';
    const offset = options?.offset ?? 0;
    const limit = options?.limit ?? 100;
    params.push(offset, limit);

    const result = await this.pool.query<DbRow>(
      `SELECT event_id, trace_id, event_data, timestamp, actor_id, actor_type, action_name, resource_type, resource_id, decision
       FROM stix_evidence_events
       ${where}
       ORDER BY timestamp ${sortOrder}
       OFFSET $${idx++}
       LIMIT $${idx}`,
      params
    );

    return result.rows.map(row => this.toEvent(row));
  }

  async getEventsByResource(
    resourceType: string,
    resourceId?: string,
    options?: QueryOptions
  ): Promise<EvidenceEvent[]> {
    const params: unknown[] = [resourceType];
    let where = 'WHERE resource_type = $1';
    let idx = 2;

    if (resourceId) {
      where += ` AND resource_id = $${idx++}`;
      params.push(resourceId);
    }
    if (options?.startDate) {
      where += ` AND timestamp >= $${idx++}`;
      params.push(options.startDate);
    }
    if (options?.endDate) {
      where += ` AND timestamp <= $${idx++}`;
      params.push(options.endDate);
    }

    const sortOrder = options?.sortOrder === 'asc' ? 'ASC' : 'DESC';
    const offset = options?.offset ?? 0;
    const limit = options?.limit ?? 100;
    params.push(offset, limit);

    const result = await this.pool.query<DbRow>(
      `SELECT event_id, trace_id, event_data, timestamp, actor_id, actor_type, action_name, resource_type, resource_id, decision
       FROM stix_evidence_events
       ${where}
       ORDER BY timestamp ${sortOrder}
       OFFSET $${idx++}
       LIMIT $${idx}`,
      params
    );

    return result.rows.map(row => this.toEvent(row));
  }

  async verifyChain(traceId: string): Promise<ChainVerificationResult> {
    const events = await this.getEventsByTrace(traceId);
    return this.chainManager.verifyChain(events);
  }

  async getStats(): Promise<EvidenceStats> {
    const [totalRes, decisionRes, actorTypeRes, actionRes, uniqueRes] = await Promise.all([
      this.pool.query<{ total: string }>('SELECT COUNT(*)::text AS total FROM stix_evidence_events'),
      this.pool.query<{ key: string; count: string }>(
        `SELECT decision AS key, COUNT(*)::text AS count
         FROM stix_evidence_events
         WHERE decision IS NOT NULL
         GROUP BY decision`
      ),
      this.pool.query<{ key: string; count: string }>(
        `SELECT actor_type AS key, COUNT(*)::text AS count
         FROM stix_evidence_events
         WHERE actor_type IS NOT NULL
         GROUP BY actor_type`
      ),
      this.pool.query<{ key: string; count: string }>(
        `SELECT action_name AS key, COUNT(*)::text AS count
         FROM stix_evidence_events
         WHERE action_name IS NOT NULL
         GROUP BY action_name`
      ),
      this.pool.query<{ unique_actors: string; unique_traces: string }>(
        `SELECT COUNT(DISTINCT actor_id)::text AS unique_actors,
                COUNT(DISTINCT trace_id)::text AS unique_traces
         FROM stix_evidence_events`
      ),
    ]);

    return {
      total: Number.parseInt(totalRes.rows[0]?.total ?? '0', 10),
      by_decision: Object.fromEntries(decisionRes.rows.map(r => [r.key, Number.parseInt(r.count, 10)])),
      by_actor_type: Object.fromEntries(actorTypeRes.rows.map(r => [r.key, Number.parseInt(r.count, 10)])),
      by_action: Object.fromEntries(actionRes.rows.map(r => [r.key, Number.parseInt(r.count, 10)])),
      unique_actors: Number.parseInt(uniqueRes.rows[0]?.unique_actors ?? '0', 10),
      unique_traces: Number.parseInt(uniqueRes.rows[0]?.unique_traces ?? '0', 10),
    };
  }

  async health(): Promise<boolean> {
    try {
      await this.pool.query('SELECT 1');
      return true;
    } catch {
      return false;
    }
  }

  async getAll(): Promise<EvidenceEvent[]> {
    const result = await this.pool.query<DbRow>(
      `SELECT event_id, trace_id, event_data, timestamp, actor_id, actor_type, action_name, resource_type, resource_id, decision
       FROM stix_evidence_events
       ORDER BY timestamp DESC, created_at DESC`
    );
    return result.rows.map(row => this.toEvent(row));
  }

  private async insertEvent(event: EvidenceEvent): Promise<void> {
    const actor = event.event_type === 'DECISION' ? (event.actor as { id?: string; type?: string } | undefined) : undefined;
    const action = event.event_type === 'DECISION' ? (event.action as { name?: string } | undefined) : undefined;
    const resource = event.event_type === 'DECISION' ? (event.resource as { type?: string; id?: string } | undefined) : undefined;

    await this.pool.query(
      `INSERT INTO stix_evidence_events (
         event_id, trace_id, event_type, timestamp, actor_id, actor_type,
         action_name, resource_type, resource_id, decision, event_data
       ) VALUES (
         $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb
       )`,
      [
        event.event_id,
        event.trace_id,
        event.event_type,
        event.timestamp,
        actor?.id ?? null,
        actor?.type ?? null,
        action?.name ?? null,
        resource?.type ?? null,
        resource?.id ?? null,
        event.decision ?? null,
        JSON.stringify(event),
      ]
    );
  }

  private toEvent(row: DbRow): EvidenceEvent {
    return row.event_data;
  }
}

// =============================================================================
// FACTORY
// =============================================================================

export async function createEvidenceStore(
  config: Config,
  logger: Logger,
  signingKey: SigningKey | null
): Promise<EvidenceStore> {
  const storeType = config.storage?.type ?? 'memory';

  switch (storeType) {
    case 'memory':
      return new InMemoryEvidenceStore(logger, signingKey);

    case 'postgres': {
      if (!config.storage.postgresUrl) {
        throw new Error('STORAGE_TYPE=postgres requires POSTGRES_URL for stix-evidence.');
      }
      const store = new PostgresEvidenceStore(logger, signingKey, config.storage.postgresUrl);
      await store.initialize();
      return store;
    }

    default:
      throw new Error(`Unsupported evidence storage type: ${storeType}`);
  }
}

function calculateStats(events: EvidenceEvent[], traceCount: number): EvidenceStats {
  const byDecision: Record<string, number> = {};
  const byActorType: Record<string, number> = {};
  const byAction: Record<string, number> = {};
  const uniqueActors = new Set<string>();

  for (const event of events) {
    if (event.event_type === 'DECISION' && event.decision) {
      byDecision[event.decision] = (byDecision[event.decision] || 0) + 1;
    }
    if (event.event_type === 'DECISION' && event.actor) {
      const actorType = (event.actor as { type?: string }).type;
      const actorId = (event.actor as { id?: string }).id;
      if (actorType) {
        byActorType[actorType] = (byActorType[actorType] || 0) + 1;
      }
      if (actorId) {
        uniqueActors.add(actorId);
      }
    }
    if (event.event_type === 'DECISION' && event.action) {
      const actionName = (event.action as { name?: string }).name || String(event.action);
      byAction[actionName] = (byAction[actionName] || 0) + 1;
    }
  }

  return {
    total: events.length,
    by_decision: byDecision,
    by_actor_type: byActorType,
    by_action: byAction,
    unique_actors: uniqueActors.size,
    unique_traces: traceCount,
  };
}

// Re-export types
export type { ChainVerificationResult, DecisionEventData, OutcomeEventData };
