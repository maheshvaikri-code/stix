/**
 * STIX PostgreSQL Approval Store
 * Production-ready persistent storage for approval workflows
 */

import type { Pool } from 'pg';
import type {
  ApprovalStore,
  ApprovalTicket,
  ApprovalDecision,
  ListTicketsOptions,
} from '../core/workflow.js';
import type { Logger, Actor, Context } from '@stix/shared';

/**
 * PostgreSQL-based approval store
 */
export class PostgresApprovalStore implements ApprovalStore {
  private readonly logger: Logger;

  constructor(
    private readonly pool: Pool,
    logger: Logger
  ) {
    this.logger = logger.child({ component: 'PostgresApprovalStore' });
  }

  /**
   * Initialize database schema
   */
  async initialize(): Promise<void> {
    await this.pool.query(`
      CREATE TABLE IF NOT EXISTS approvals (
        id TEXT PRIMARY KEY,
        trace_id TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL,
        actor_id TEXT NOT NULL,
        actor_type TEXT NOT NULL,
        actor_role TEXT,
        actor_tenant TEXT,
        action TEXT NOT NULL,
        resource_type TEXT NOT NULL,
        resource_id TEXT,
        resource_classification TEXT[] NOT NULL DEFAULT '{}',
        context_env TEXT NOT NULL,
        context_purpose TEXT,
        context_run_id TEXT,
        context_ticket_id TEXT,
        context_attributes JSONB,
        security_binding JSONB,
        approver_role TEXT,
        required_count INTEGER NOT NULL DEFAULT 1,
        current_count INTEGER NOT NULL DEFAULT 0,
        require_justification BOOLEAN NOT NULL DEFAULT false,
        policy_id TEXT,
        policy_version TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL,
        resolved_at TIMESTAMPTZ
      );

      CREATE TABLE IF NOT EXISTS approval_records (
        approval_id TEXT NOT NULL REFERENCES approvals(id) ON DELETE CASCADE,
        approver_id TEXT NOT NULL,
        approver_role TEXT,
        decision TEXT NOT NULL,
        justification TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (approval_id, approver_id)
      );

      CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);
      CREATE INDEX IF NOT EXISTS idx_approvals_trace_id ON approvals(trace_id);
      CREATE INDEX IF NOT EXISTS idx_approvals_actor_id ON approvals(actor_id);
      CREATE INDEX IF NOT EXISTS idx_approvals_created_at ON approvals(created_at);
      CREATE INDEX IF NOT EXISTS idx_approvals_expires_at ON approvals(expires_at);
      CREATE INDEX IF NOT EXISTS idx_approval_records_approval_id ON approval_records(approval_id);
      ALTER TABLE approvals ADD COLUMN IF NOT EXISTS security_binding JSONB;
    `);

    this.logger.info('Postgres approval store initialized');
  }

  /**
   * Create a new approval ticket
   */
  async createTicket(ticket: ApprovalTicket): Promise<ApprovalTicket> {
    const client = await this.pool.connect();

    try {
      await client.query('BEGIN');

      // Insert approval record
      await client.query(
        `INSERT INTO approvals (
          id, trace_id, status, actor_id, actor_type, actor_role, actor_tenant,
          action, resource_type, resource_id, resource_classification,
          context_env, context_purpose, context_run_id, context_ticket_id, context_attributes, security_binding,
          approver_role, required_count, current_count, require_justification,
          policy_id, policy_version, created_at, expires_at
        ) VALUES (
          $1, $2, $3, $4, $5, $6, $7,
          $8, $9, $10, $11,
          $12, $13, $14, $15, $16,
          $17, $18, $19, $20, $21,
          $22, $23, $24, $25
        )`,
        [
          ticket.ticket_id,
          ticket.trace_id,
          ticket.status.toLowerCase(),
          ticket.actor.id,
          ticket.actor.type,
          ticket.actor.role,
          ticket.actor.tenant,
          ticket.action,
          ticket.resource.type,
          ticket.resource.id,
          ticket.resource.classification ?? [],
          ticket.context.env,
          ticket.context.purpose,
          ticket.context.run_id,
          ticket.context.ticket_id,
          JSON.stringify(ticket.context.attributes ?? {}),
          JSON.stringify(ticket.security_binding ?? null),
          ticket.required_role,
          ticket.required_count,
          0,
          ticket.require_justification,
          'policy-from-quarantine', // Would come from authorization context
          '1.0.0',
          ticket.created_at,
          ticket.expires_at,
        ]
      );

      await client.query('COMMIT');

      this.logger.debug('Approval ticket created in database', {
        ticket_id: ticket.ticket_id,
        trace_id: ticket.trace_id,
      });

      return ticket;
    } catch (error) {
      await client.query('ROLLBACK');
      this.logger.error('Failed to create approval ticket', {
        ticket_id: ticket.ticket_id,
        error: (error as Error).message,
      });
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * Get a ticket by ID
   */
  async getTicket(ticketId: string): Promise<ApprovalTicket | null> {
    const result = await this.pool.query(
      `SELECT * FROM approvals WHERE id = $1`,
      [ticketId]
    );

    if (result.rows.length === 0) {
      return null;
    }

    const row = result.rows[0];
    const decisions = await this.getDecisions(ticketId);

    return this.rowToTicket(row, decisions);
  }

  /**
   * Get a ticket by trace ID
   */
  async getTicketByTrace(traceId: string): Promise<ApprovalTicket | null> {
    const result = await this.pool.query(
      `SELECT * FROM approvals WHERE trace_id = $1`,
      [traceId]
    );

    if (result.rows.length === 0) {
      return null;
    }

    const row = result.rows[0];
    const decisions = await this.getDecisions(row.id);

    return this.rowToTicket(row, decisions);
  }

  /**
   * Update an existing ticket
   */
  async updateTicket(ticket: ApprovalTicket): Promise<void> {
    const client = await this.pool.connect();

    try {
      await client.query('BEGIN');

      // Update approval record
      const approveCount = ticket.decisions.filter(d => d.decision === 'APPROVE').length;

      await client.query(
        `UPDATE approvals SET
          status = $1,
          current_count = $2,
          resolved_at = $3
        WHERE id = $4`,
        [
          ticket.status.toLowerCase(),
          approveCount,
          ticket.resolved_at,
          ticket.ticket_id,
        ]
      );

      // Insert any new decisions
      for (const decision of ticket.decisions) {
        await client.query(
          `INSERT INTO approval_records (approval_id, approver_id, approver_role, decision, justification, created_at)
           VALUES ($1, $2, $3, $4, $5, $6)
           ON CONFLICT (approval_id, approver_id) DO NOTHING`,
          [
            ticket.ticket_id,
            decision.approver_id,
            decision.approver_role,
            decision.decision.toLowerCase(),
            decision.justification,
            decision.timestamp,
          ]
        );
      }

      await client.query('COMMIT');

      this.logger.debug('Approval ticket updated', {
        ticket_id: ticket.ticket_id,
        status: ticket.status,
      });
    } catch (error) {
      await client.query('ROLLBACK');
      this.logger.error('Failed to update approval ticket', {
        ticket_id: ticket.ticket_id,
        error: (error as Error).message,
      });
      throw error;
    } finally {
      client.release();
    }
  }

  /**
   * List tickets with filtering
   */
  async listTickets(options?: ListTicketsOptions): Promise<ApprovalTicket[]> {
    const conditions: string[] = [];
    const params: unknown[] = [];
    let paramIndex = 1;

    if (options?.status) {
      conditions.push(`status = $${paramIndex++}`);
      params.push(options.status.toLowerCase());
    }

    if (options?.approver_role) {
      conditions.push(`(approver_role IS NULL OR approver_role = $${paramIndex++})`);
      params.push(options.approver_role);
    }

    if (options?.actor_id) {
      conditions.push(`actor_id = $${paramIndex++}`);
      params.push(options.actor_id);
    }

    const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
    const limit = options?.limit ?? 50;
    const offset = options?.offset ?? 0;

    const result = await this.pool.query(
      `SELECT * FROM approvals ${whereClause}
       ORDER BY created_at DESC
       LIMIT $${paramIndex++} OFFSET $${paramIndex}`,
      [...params, limit, offset]
    );

    const tickets: ApprovalTicket[] = [];

    for (const row of result.rows) {
      const decisions = await this.getDecisions(row.id);
      tickets.push(this.rowToTicket(row, decisions));
    }

    return tickets;
  }

  /**
   * Delete a ticket
   */
  async deleteTicket(ticketId: string): Promise<void> {
    await this.pool.query(
      `DELETE FROM approvals WHERE id = $1`,
      [ticketId]
    );
  }

  /**
   * Health check
   */
  async health(): Promise<boolean> {
    try {
      await this.pool.query('SELECT 1');
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get pending approvals count
   */
  async getPendingCount(env?: string): Promise<number> {
    const result = env
      ? await this.pool.query(
          `SELECT COUNT(*) FROM approvals WHERE status = 'pending' AND context_env = $1`,
          [env]
        )
      : await this.pool.query(
          `SELECT COUNT(*) FROM approvals WHERE status = 'pending'`
        );

    return parseInt(result.rows[0].count, 10);
  }

  /**
   * Get approvals expiring soon
   */
  async getExpiringCount(withinHours: number = 1): Promise<number> {
    const result = await this.pool.query(
      `SELECT COUNT(*) FROM approvals
       WHERE status = 'pending'
       AND expires_at < NOW() + $1 * INTERVAL '1 hour'`,
      [withinHours]
    );

    return parseInt(result.rows[0].count, 10);
  }

  /**
   * Expire all stale tickets
   */
  async expireStaleTickets(): Promise<number> {
    const result = await this.pool.query(
      `UPDATE approvals
       SET status = 'expired', resolved_at = NOW()
       WHERE status = 'pending' AND expires_at < NOW()`
    );

    return result.rowCount ?? 0;
  }

  /**
   * Get statistics
   */
  async getStats(startTime: string, endTime: string): Promise<ApprovalStats> {
    const result = await this.pool.query(
      `SELECT
         status,
         COUNT(*) as count,
         AVG(EXTRACT(EPOCH FROM (COALESCE(resolved_at, NOW()) - created_at))) as avg_resolution_seconds
       FROM approvals
       WHERE created_at >= $1 AND created_at < $2
       GROUP BY status`,
      [startTime, endTime]
    );

    const stats: ApprovalStats = {
      total: 0,
      pending: 0,
      approved: 0,
      rejected: 0,
      expired: 0,
      cancelled: 0,
      avgResolutionSeconds: 0,
    };

    let totalResolutionTime = 0;
    let resolvedCount = 0;

    for (const row of result.rows) {
      const count = parseInt(row.count, 10);
      stats.total += count;

      switch (row.status) {
        case 'pending':
          stats.pending = count;
          break;
        case 'approved':
          stats.approved = count;
          totalResolutionTime += parseFloat(row.avg_resolution_seconds) * count;
          resolvedCount += count;
          break;
        case 'rejected':
          stats.rejected = count;
          totalResolutionTime += parseFloat(row.avg_resolution_seconds) * count;
          resolvedCount += count;
          break;
        case 'expired':
          stats.expired = count;
          break;
        case 'cancelled':
          stats.cancelled = count;
          break;
      }
    }

    if (resolvedCount > 0) {
      stats.avgResolutionSeconds = totalResolutionTime / resolvedCount;
    }

    return stats;
  }

  /**
   * Get decisions for a ticket
   */
  private async getDecisions(ticketId: string): Promise<ApprovalDecision[]> {
    const result = await this.pool.query(
      `SELECT * FROM approval_records WHERE approval_id = $1 ORDER BY created_at ASC`,
      [ticketId]
    );

    return result.rows.map(row => ({
      approver_id: row.approver_id,
      approver_role: row.approver_role,
      decision: row.decision.toUpperCase() as 'APPROVE' | 'REJECT',
      justification: row.justification,
      timestamp: row.created_at.toISOString(),
    }));
  }

  /**
   * Convert database row to ApprovalTicket
   */
  private rowToTicket(row: Record<string, unknown>, decisions: ApprovalDecision[]): ApprovalTicket {
    return {
      ticket_id: row.id as string,
      trace_id: row.trace_id as string,
      status: (row.status as string).toUpperCase() as ApprovalTicket['status'],
      actor: {
        id: row.actor_id as string,
        type: row.actor_type as Actor['type'],
        role: row.actor_role as string | undefined,
        tenant: row.actor_tenant as string | undefined,
      },
      action: row.action as string,
      resource: {
        type: row.resource_type as string,
        id: row.resource_id as string | undefined,
        classification: row.resource_classification as string[],
      },
      context: {
        env: row.context_env as Context['env'],
        purpose: row.context_purpose as string | undefined,
        run_id: row.context_run_id as string | undefined,
        ticket_id: row.context_ticket_id as string | undefined,
        attributes: typeof row.context_attributes === 'string'
          ? JSON.parse(row.context_attributes)
          : row.context_attributes,
      },
      security_binding: typeof row.security_binding === 'string'
        ? JSON.parse(row.security_binding)
        : row.security_binding,
      required_count: row.required_count as number,
      required_role: row.approver_role as string | undefined,
      require_justification: row.require_justification as boolean,
      decisions,
      created_at: (row.created_at as Date).toISOString(),
      expires_at: (row.expires_at as Date).toISOString(),
      resolved_at: row.resolved_at ? (row.resolved_at as Date).toISOString() : undefined,
    };
  }
}

/**
 * Approval statistics
 */
export interface ApprovalStats {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  expired: number;
  cancelled: number;
  avgResolutionSeconds: number;
}

/**
 * Create PostgreSQL approval store
 */
export async function createPostgresApprovalStore(
  pool: Pool,
  logger: Logger
): Promise<PostgresApprovalStore> {
  const store = new PostgresApprovalStore(pool, logger);
  await store.initialize();

  // Verify connection
  const healthy = await store.health();
  if (!healthy) {
    throw new Error('Failed to connect to PostgreSQL for approval store');
  }

  return store;
}
