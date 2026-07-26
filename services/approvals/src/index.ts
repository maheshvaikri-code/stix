/**
 * STIX Approvals Service
 * Human-in-the-loop approval workflows for QUARANTINE decisions
 * 
 * @module @stix/approvals
 */

import Fastify, { type FastifyInstance, type FastifyRequest, type FastifyReply } from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import { Pool } from 'pg';
import { z } from 'zod';
import {
  createLoggerFromEnv,
  type Logger,
  type Actor,
  type Resource,
  type Context,
  type ApprovalBinding,
  SERVICE_PORTS,
  APPROVAL_CONFIG,
  HEADERS,
  getEnv,
  getEnvNumber,
  getEnvBool,
  isStixError,
  StixError,
  createErrorResponse,
  ApprovalNotFoundError,
  ApprovalExpiredError,
  ApprovalAlreadyProcessedError,
  isoTimestamp,
} from '@stix/shared';

// =============================================================================
// CONFIGURATION
// =============================================================================

const ConfigSchema = z.object({
  service: z.object({
    name: z.string(),
    version: z.string(),
    port: z.number(),
    host: z.string(),
    env: z.enum(['dev', 'test', 'stage', 'prod']),
  }),
  logging: z.object({
    level: z.enum(['error', 'warn', 'info', 'http', 'debug', 'trace']),
    pretty: z.boolean(),
  }),
  approval: z.object({
    defaultTimeoutHours: z.number(),
    maxTimeoutHours: z.number(),
    defaultRequiredApprovers: z.number(),
  }),
  storage: z.object({
    type: z.enum(['memory', 'postgres']),
    postgresUrl: z.string().optional(),
  }),
  auth: z.object({
    serviceTokenAuthEnabled: z.boolean(),
    serviceToken: z.string().optional(),
  }),
});

type Config = z.infer<typeof ConfigSchema>;

function loadConfig(): Config {
  const rawEnv = getEnv('NODE_ENV', 'dev');
  const normalizedEnv = rawEnv.toLowerCase() === 'production' ? 'prod' : rawEnv.toLowerCase();
  const env = normalizedEnv as 'dev' | 'test' | 'stage' | 'prod';
  const storageType = getEnv('STORAGE_TYPE', 'memory');

  if (env === 'prod' && storageType === 'memory') {
    throw new Error(
      'STORAGE_TYPE=memory is not allowed in prod for stix-approvals. Configure a durable backend before startup.'
    );
  }

  if (storageType !== 'memory' && storageType !== 'postgres') {
    throw new Error(
      `Unsupported STORAGE_TYPE=${storageType} for stix-approvals. Supported: memory, postgres.`
    );
  }
  
  const parsed = ConfigSchema.parse({
    service: {
      name: 'stix-approvals',
      version: getEnv('SERVICE_VERSION', '0.1.14'),
      port: getEnvNumber('PORT', SERVICE_PORTS.APPROVALS),
      host: getEnv('HOST', '0.0.0.0'),
      env,
    },
    logging: {
      level: getEnv('LOG_LEVEL', env === 'prod' ? 'info' : 'debug'),
      pretty: getEnvBool('LOG_PRETTY', env !== 'prod'),
    },
    approval: {
      defaultTimeoutHours: getEnvNumber('APPROVAL_TIMEOUT_HOURS', APPROVAL_CONFIG.DEFAULT_TIMEOUT_HOURS),
      maxTimeoutHours: getEnvNumber('APPROVAL_MAX_TIMEOUT_HOURS', APPROVAL_CONFIG.MAX_TIMEOUT_HOURS),
      defaultRequiredApprovers: getEnvNumber('APPROVAL_REQUIRED_COUNT', APPROVAL_CONFIG.DEFAULT_REQUIRED_APPROVERS),
    },
    storage: {
      type: storageType,
      postgresUrl: getEnv('POSTGRES_URL', ''),
    },
    auth: {
      serviceTokenAuthEnabled: getEnvBool('SERVICE_TOKEN_AUTH_ENABLED', env === 'prod'),
      serviceToken: getEnv('SERVICE_AUTH_TOKEN', ''),
    },
  });

  if (parsed.storage.type === 'postgres' && !parsed.storage.postgresUrl) {
    throw new Error('STORAGE_TYPE=postgres requires POSTGRES_URL for stix-approvals.');
  }

  if (parsed.auth.serviceTokenAuthEnabled && !parsed.auth.serviceToken) {
    throw new Error('SERVICE_TOKEN_AUTH_ENABLED=true requires SERVICE_AUTH_TOKEN for stix-approvals.');
  }

  return parsed;
}

// =============================================================================
// TYPES
// =============================================================================

type ApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED' | 'CANCELLED';

interface ApprovalDecision {
  approver_id: string;
  approver_role?: string;
  decision: 'APPROVE' | 'REJECT';
  justification?: string;
  timestamp: string;
}

interface ApprovalTicket {
  ticket_id: string;
  trace_id: string;
  status: ApprovalStatus;
  actor: Actor;
  action: string;
  resource: Resource;
  context: Context;
  required_count: number;
  required_role?: string;
  require_justification: boolean;
  decisions: ApprovalDecision[];
  created_at: string;
  expires_at: string;
  resolved_at?: string;
  security_binding?: ApprovalBinding;
}

interface CreateTicketInput {
  ticket_id: string;
  trace_id: string;
  actor: Actor;
  action: string;
  resource: Resource;
  context: Context;
  required_count?: number;
  required_role?: string;
  require_justification?: boolean;
  expires_at: string;
  security_binding?: ApprovalBinding;
}

interface ApproveInput {
  approver_id: string;
  approver_role?: string;
  justification?: string;
}

interface ApprovalStoreContract {
  createTicket(input: CreateTicketInput): Promise<ApprovalTicket>;
  getTicket(ticketId: string): Promise<ApprovalTicket | null>;
  getTicketByTraceId(traceId: string): Promise<ApprovalTicket | null>;
  getAll(): Promise<ApprovalTicket[]>;
  approve(ticketId: string, input: ApproveInput): Promise<ApprovalTicket>;
  reject(ticketId: string, input: ApproveInput): Promise<ApprovalTicket>;
  cancel(ticketId: string): Promise<ApprovalTicket>;
  listPending(options?: { required_role?: string; limit?: number }): Promise<ApprovalTicket[]>;
  health(): Promise<boolean>;
}

// =============================================================================
// APPROVAL STORE
// =============================================================================

class ApprovalStore implements ApprovalStoreContract {
  private readonly tickets: Map<string, ApprovalTicket> = new Map();
  private readonly traceIndex: Map<string, string> = new Map();
  private readonly logger: Logger;

  constructor(logger: Logger) {
    this.logger = logger.child({ component: 'ApprovalStore' });
  }

  async createTicket(input: CreateTicketInput): Promise<ApprovalTicket> {
    const ticket: ApprovalTicket = {
      ticket_id: input.ticket_id,
      trace_id: input.trace_id,
      status: 'PENDING',
      actor: input.actor,
      action: input.action,
      resource: input.resource,
      context: input.context,
      required_count: input.required_count ?? 1,
      required_role: input.required_role,
      require_justification: input.require_justification ?? false,
      decisions: [],
      created_at: isoTimestamp(),
      expires_at: input.expires_at,
      security_binding: input.security_binding,
    };

    this.tickets.set(ticket.ticket_id, ticket);
    this.traceIndex.set(ticket.trace_id, ticket.ticket_id);
    
    this.logger.info('Approval ticket created', {
      ticket_id: ticket.ticket_id,
      trace_id: ticket.trace_id,
    });

    return ticket;
  }

  async getTicket(ticketId: string): Promise<ApprovalTicket | null> {
    const ticket = this.tickets.get(ticketId);
    if (ticket) {
      this.checkExpiration(ticket);
    }
    return ticket ?? null;
  }

  async getTicketByTraceId(traceId: string): Promise<ApprovalTicket | null> {
    const ticketId = this.traceIndex.get(traceId);
    if (!ticketId) return null;
    return this.getTicket(ticketId);
  }

  async getAll(): Promise<ApprovalTicket[]> {
    return Array.from(this.tickets.values());
  }

  async approve(ticketId: string, input: ApproveInput): Promise<ApprovalTicket> {
    const ticket = await this.getTicket(ticketId);
    if (!ticket) throw new ApprovalNotFoundError(ticketId);
    
    this.validateForDecision(ticket, input);

    ticket.decisions.push({
      approver_id: input.approver_id,
      approver_role: input.approver_role,
      decision: 'APPROVE',
      justification: input.justification,
      timestamp: isoTimestamp(),
    });

    // Check if we have enough approvals
    const approvalCount = ticket.decisions.filter(d => d.decision === 'APPROVE').length;
    if (approvalCount >= ticket.required_count) {
      ticket.status = 'APPROVED';
      ticket.resolved_at = isoTimestamp();
      this.logger.info('Ticket approved', { ticket_id: ticketId });
    }

    return ticket;
  }

  async reject(ticketId: string, input: ApproveInput): Promise<ApprovalTicket> {
    const ticket = await this.getTicket(ticketId);
    if (!ticket) throw new ApprovalNotFoundError(ticketId);
    
    this.validateForDecision(ticket, input);

    ticket.decisions.push({
      approver_id: input.approver_id,
      approver_role: input.approver_role,
      decision: 'REJECT',
      justification: input.justification,
      timestamp: isoTimestamp(),
    });

    ticket.status = 'REJECTED';
    ticket.resolved_at = isoTimestamp();
    
    this.logger.info('Ticket rejected', { ticket_id: ticketId });
    return ticket;
  }

  async cancel(ticketId: string): Promise<ApprovalTicket> {
    const ticket = await this.getTicket(ticketId);
    if (!ticket) throw new ApprovalNotFoundError(ticketId);
    
    if (ticket.status !== 'PENDING') {
      throw new ApprovalAlreadyProcessedError(ticketId, ticket.status);
    }

    ticket.status = 'CANCELLED';
    ticket.resolved_at = isoTimestamp();
    
    this.logger.info('Ticket cancelled', { ticket_id: ticketId });
    return ticket;
  }

  async listPending(options?: { required_role?: string; limit?: number }): Promise<ApprovalTicket[]> {
    let tickets = Array.from(this.tickets.values())
      .filter(t => t.status === 'PENDING')
      .filter(t => !this.isExpired(t));

    if (options?.required_role) {
      tickets = tickets.filter(t => !t.required_role || t.required_role === options.required_role);
    }

    tickets.sort((a, b) => a.created_at.localeCompare(b.created_at));

    if (options?.limit) {
      tickets = tickets.slice(0, options.limit);
    }

    return tickets;
  }

  private validateForDecision(ticket: ApprovalTicket, input: ApproveInput): void {
    if (ticket.status !== 'PENDING') {
      throw new ApprovalAlreadyProcessedError(ticket.ticket_id, ticket.status);
    }

    if (this.isExpired(ticket)) {
      ticket.status = 'EXPIRED';
      throw new ApprovalExpiredError(ticket.ticket_id);
    }

    if (ticket.required_role && input.approver_role !== ticket.required_role) {
      throw new Error(`Approver must have role: ${ticket.required_role}`);
    }

    if (ticket.require_justification && !input.justification) {
      throw new Error('Justification required');
    }

    // Check for duplicate approver
    if (ticket.decisions.some(d => d.approver_id === input.approver_id)) {
      throw new Error('Approver has already provided a decision');
    }
  }

  private checkExpiration(ticket: ApprovalTicket): void {
    if (ticket.status === 'PENDING' && this.isExpired(ticket)) {
      ticket.status = 'EXPIRED';
    }
  }

  private isExpired(ticket: ApprovalTicket): boolean {
    return new Date(ticket.expires_at) < new Date();
  }

  async health(): Promise<boolean> {
    return true;
  }
}

class PostgresApprovalStore implements ApprovalStoreContract {
  private readonly logger: Logger;

  constructor(private readonly pool: Pool, logger: Logger) {
    this.logger = logger.child({ component: 'PostgresApprovalStore' });
  }

  async initialize(): Promise<void> {
    await this.pool.query(`
      CREATE TABLE IF NOT EXISTS stix_approval_tickets (
        ticket_id TEXT PRIMARY KEY,
        trace_id TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL,
        required_role TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL,
        resolved_at TIMESTAMPTZ,
        ticket_data JSONB NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );
      CREATE INDEX IF NOT EXISTS idx_stix_approvals_status ON stix_approval_tickets(status);
      CREATE INDEX IF NOT EXISTS idx_stix_approvals_trace ON stix_approval_tickets(trace_id);
      CREATE INDEX IF NOT EXISTS idx_stix_approvals_expires ON stix_approval_tickets(expires_at);
    `);
  }

  async createTicket(input: CreateTicketInput): Promise<ApprovalTicket> {
    const ticket: ApprovalTicket = {
      ticket_id: input.ticket_id,
      trace_id: input.trace_id,
      status: 'PENDING',
      actor: input.actor,
      action: input.action,
      resource: input.resource,
      context: input.context,
      required_count: input.required_count ?? 1,
      required_role: input.required_role,
      require_justification: input.require_justification ?? false,
      decisions: [],
      created_at: isoTimestamp(),
      expires_at: input.expires_at,
      security_binding: input.security_binding,
    };

    await this.write(ticket);
    this.logger.info('Approval ticket created', {
      ticket_id: ticket.ticket_id,
      trace_id: ticket.trace_id,
    });
    return ticket;
  }

  async getTicket(ticketId: string): Promise<ApprovalTicket | null> {
    const result = await this.pool.query<{ ticket_data: ApprovalTicket }>(
      `SELECT ticket_data FROM stix_approval_tickets WHERE ticket_id = $1`,
      [ticketId]
    );
    if (result.rows.length === 0) {
      return null;
    }
    const ticket = result.rows[0].ticket_data;
    if (ticket.status === 'PENDING' && this.isExpired(ticket)) {
      ticket.status = 'EXPIRED';
      ticket.resolved_at = isoTimestamp();
      await this.write(ticket);
    }
    return ticket;
  }

  async getTicketByTraceId(traceId: string): Promise<ApprovalTicket | null> {
    const result = await this.pool.query<{ ticket_data: ApprovalTicket }>(
      `SELECT ticket_data FROM stix_approval_tickets WHERE trace_id = $1`,
      [traceId]
    );
    if (result.rows.length === 0) {
      return null;
    }
    const ticket = result.rows[0].ticket_data;
    if (ticket.status === 'PENDING' && this.isExpired(ticket)) {
      ticket.status = 'EXPIRED';
      ticket.resolved_at = isoTimestamp();
      await this.write(ticket);
    }
    return ticket;
  }

  async getAll(): Promise<ApprovalTicket[]> {
    const result = await this.pool.query<{ ticket_data: ApprovalTicket }>(
      `SELECT ticket_data
       FROM stix_approval_tickets
       ORDER BY created_at DESC`
    );
    return result.rows.map(r => r.ticket_data);
  }

  async approve(ticketId: string, input: ApproveInput): Promise<ApprovalTicket> {
    const ticket = await this.getTicket(ticketId);
    if (!ticket) throw new ApprovalNotFoundError(ticketId);

    this.validateForDecision(ticket, input);

    ticket.decisions.push({
      approver_id: input.approver_id,
      approver_role: input.approver_role,
      decision: 'APPROVE',
      justification: input.justification,
      timestamp: isoTimestamp(),
    });

    const approvalCount = ticket.decisions.filter(d => d.decision === 'APPROVE').length;
    if (approvalCount >= ticket.required_count) {
      ticket.status = 'APPROVED';
      ticket.resolved_at = isoTimestamp();
      this.logger.info('Ticket approved', { ticket_id: ticketId });
    }

    await this.write(ticket);
    return ticket;
  }

  async reject(ticketId: string, input: ApproveInput): Promise<ApprovalTicket> {
    const ticket = await this.getTicket(ticketId);
    if (!ticket) throw new ApprovalNotFoundError(ticketId);

    this.validateForDecision(ticket, input);

    ticket.decisions.push({
      approver_id: input.approver_id,
      approver_role: input.approver_role,
      decision: 'REJECT',
      justification: input.justification,
      timestamp: isoTimestamp(),
    });

    ticket.status = 'REJECTED';
    ticket.resolved_at = isoTimestamp();
    this.logger.info('Ticket rejected', { ticket_id: ticketId });

    await this.write(ticket);
    return ticket;
  }

  async cancel(ticketId: string): Promise<ApprovalTicket> {
    const ticket = await this.getTicket(ticketId);
    if (!ticket) throw new ApprovalNotFoundError(ticketId);

    if (ticket.status !== 'PENDING') {
      throw new ApprovalAlreadyProcessedError(ticketId, ticket.status);
    }

    ticket.status = 'CANCELLED';
    ticket.resolved_at = isoTimestamp();
    this.logger.info('Ticket cancelled', { ticket_id: ticketId });

    await this.write(ticket);
    return ticket;
  }

  async listPending(options?: { required_role?: string; limit?: number }): Promise<ApprovalTicket[]> {
    const result = await this.pool.query<{ ticket_data: ApprovalTicket }>(
      `SELECT ticket_data
       FROM stix_approval_tickets
       WHERE status = 'PENDING'
       ORDER BY created_at ASC`
    );

    let tickets = result.rows.map(r => r.ticket_data);
    for (const ticket of tickets) {
      if (ticket.status !== 'PENDING' || !this.isExpired(ticket)) {
        continue;
      }
      ticket.status = 'EXPIRED';
      ticket.resolved_at = isoTimestamp();
      await this.write(ticket);
    }
    tickets = tickets.filter(t => !this.isExpired(t));

    if (options?.required_role) {
      tickets = tickets.filter(t => !t.required_role || t.required_role === options.required_role);
    }

    if (options?.limit) {
      tickets = tickets.slice(0, options.limit);
    }

    return tickets;
  }

  async health(): Promise<boolean> {
    try {
      await this.pool.query('SELECT 1');
      return true;
    } catch {
      return false;
    }
  }

  private validateForDecision(ticket: ApprovalTicket, input: ApproveInput): void {
    if (ticket.status !== 'PENDING') {
      throw new ApprovalAlreadyProcessedError(ticket.ticket_id, ticket.status);
    }

    if (this.isExpired(ticket)) {
      ticket.status = 'EXPIRED';
      throw new ApprovalExpiredError(ticket.ticket_id);
    }

    if (ticket.required_role && input.approver_role !== ticket.required_role) {
      throw new Error(`Approver must have role: ${ticket.required_role}`);
    }

    if (ticket.require_justification && !input.justification) {
      throw new Error('Justification required');
    }

    if (ticket.decisions.some(d => d.approver_id === input.approver_id)) {
      throw new Error('Approver has already provided a decision');
    }
  }

  private isExpired(ticket: ApprovalTicket): boolean {
    return new Date(ticket.expires_at) < new Date();
  }

  private async write(ticket: ApprovalTicket): Promise<void> {
    await this.pool.query(
      `INSERT INTO stix_approval_tickets (
         ticket_id, trace_id, status, required_role, created_at, expires_at, resolved_at, ticket_data, updated_at
       ) VALUES (
         $1, $2, $3, $4, $5, $6, $7, $8::jsonb, NOW()
       )
       ON CONFLICT (ticket_id) DO UPDATE SET
         trace_id = EXCLUDED.trace_id,
         status = EXCLUDED.status,
         required_role = EXCLUDED.required_role,
         created_at = EXCLUDED.created_at,
         expires_at = EXCLUDED.expires_at,
         resolved_at = EXCLUDED.resolved_at,
         ticket_data = EXCLUDED.ticket_data,
         updated_at = NOW()`,
      [
        ticket.ticket_id,
        ticket.trace_id,
        ticket.status,
        ticket.required_role ?? null,
        ticket.created_at,
        ticket.expires_at,
        ticket.resolved_at ?? null,
        JSON.stringify(ticket),
      ]
    );
  }
}

// =============================================================================
// ROUTES
// =============================================================================

async function registerRoutes(
  fastify: FastifyInstance,
  store: ApprovalStoreContract,
  config: Config,
  startTime: number
): Promise<void> {
  // Health routes
  fastify.get('/health', async (_, reply) => {
    return reply.send({
      status: 'healthy',
      service: config.service.name,
      version: config.service.version,
      uptime: Math.floor((Date.now() - startTime) / 1000),
    });
  });

  fastify.get('/ready', async (_, reply) => {
    const healthy = await store.health();
    return reply.code(healthy ? 200 : 503).send({
      status: healthy ? 'healthy' : 'unhealthy',
      service: config.service.name,
    });
  });

  // Stats endpoint
  fastify.get('/api/v1/stats', async (_request, reply) => {
    const tickets = await store.getAll();
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());

    const pending = tickets.filter(t => t.status === 'PENDING').length;
    const approvedToday = tickets.filter(t =>
      t.status === 'APPROVED' &&
      t.resolved_at &&
      new Date(t.resolved_at) >= today
    ).length;
    const rejectedToday = tickets.filter(t =>
      t.status === 'REJECTED' &&
      t.resolved_at &&
      new Date(t.resolved_at) >= today
    ).length;

    // Calculate average response time for resolved tickets
    const resolvedTickets = tickets.filter(t => t.resolved_at);
    let avgResponseTimeMs = 0;
    if (resolvedTickets.length > 0) {
      const totalResponseTime = resolvedTickets.reduce((sum, t) => {
        return sum + (new Date(t.resolved_at!).getTime() - new Date(t.created_at).getTime());
      }, 0);
      avgResponseTimeMs = totalResponseTime / resolvedTickets.length;
    }

    return reply.code(200).send({
      pending,
      approved_today: approvedToday,
      rejected_today: rejectedToday,
      avg_response_time_ms: Math.round(avgResponseTimeMs),
    });
  });

  // List approvals
  fastify.get<{
    Querystring: {
      page?: string;
      page_size?: string;
      status?: string;
      actor_id?: string;
      action?: string;
    };
  }>('/api/v1/approvals', async (request, reply) => {
    const page = parseInt(request.query.page || '1');
    const pageSize = parseInt(request.query.page_size || '20');
    const statusFilter = request.query.status;
    const actorIdFilter = request.query.actor_id;
    const actionFilter = request.query.action;

    let tickets = await store.getAll();
    if (statusFilter) {
      tickets = tickets.filter(t => t.status === statusFilter);
    }
    if (actorIdFilter) {
      tickets = tickets.filter(t => t.actor.id === actorIdFilter);
    }
    if (actionFilter) {
      tickets = tickets.filter(t => t.action === actionFilter);
    }

    // Sort by created_at descending (newest first)
    tickets.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

    const total = tickets.length;
    const start = (page - 1) * pageSize;
    const paginatedTickets = tickets.slice(start, start + pageSize);

    // Transform to dashboard format
    const data = paginatedTickets.map(t => ({
      request_id: t.ticket_id,
      trace_id: t.trace_id,
      actor_id: t.actor.id,
      actor_type: t.actor.type,
      action: t.action,
      resource_type: t.resource.type,
      resource_id: t.resource.id,
      reason_code: (t.context as any).reason_code || 'QUARANTINE',
      context: t.context,
      created_at: t.created_at,
      expires_at: t.expires_at,
      status: t.status,
        reviewed_by: t.decisions[0]?.approver_id,
        reviewed_at: t.resolved_at,
        review_notes: t.decisions[0]?.justification,
        required_role: t.required_role,
        require_justification: t.require_justification,
        security_binding: t.security_binding,
    }));

    return reply.code(200).send({
      data,
      total,
      page,
      page_size: pageSize,
      has_more: start + pageSize < total,
    });
  });

  // Create ticket
  fastify.post<{ Body: CreateTicketInput }>('/api/v1/approvals/tickets', async (request, reply) => {
    try {
      const ticket = await store.createTicket(request.body);
      return reply.code(201).send({ success: true, data: ticket });
    } catch (error) {
      request.log.error({ err: error }, 'Failed to create ticket');
      return reply.code(500).send({
        success: false,
        error: { code: 'CREATE_FAILED', message: (error as Error).message },
      });
    }
  });

  // Get approval by ID (dashboard uses requestId)
  fastify.get<{ Params: { requestId: string } }>('/api/v1/approvals/:requestId', async (request, reply) => {
    try {
      const ticket = await store.getTicket(request.params.requestId);
      if (!ticket) throw new ApprovalNotFoundError(request.params.requestId);

      // Transform to dashboard format
      return reply.send({
        request_id: ticket.ticket_id,
        trace_id: ticket.trace_id,
        actor_id: ticket.actor.id,
        actor_type: ticket.actor.type,
        action: ticket.action,
        resource_type: ticket.resource.type,
        resource_id: ticket.resource.id,
        reason_code: (ticket.context as any).reason_code || 'QUARANTINE',
        context: ticket.context,
        created_at: ticket.created_at,
        expires_at: ticket.expires_at,
        status: ticket.status,
        reviewed_by: ticket.decisions[0]?.approver_id,
        reviewed_at: ticket.resolved_at,
        review_notes: ticket.decisions[0]?.justification,
      });
    } catch (error) {
      if (isStixError(error)) {
        const stixError = error as StixError;
        return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
      }
      return reply.code(500).send({
        success: false,
        error: { code: 'GET_FAILED', message: (error as Error).message },
      });
    }
  });

  // Legacy: Get ticket (for backwards compat)
  fastify.get<{ Params: { ticketId: string } }>('/api/v1/approvals/tickets/:ticketId', async (request, reply) => {
    try {
      const ticket = await store.getTicket(request.params.ticketId);
      if (!ticket) throw new ApprovalNotFoundError(request.params.ticketId);
      return reply.send({ success: true, data: ticket });
    } catch (error) {
      if (isStixError(error)) {
        const stixError = error as StixError;
        return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
      }
      return reply.code(500).send({
        success: false,
        error: { code: 'GET_FAILED', message: (error as Error).message },
      });
    }
  });

  // Check approval by trace ID
  fastify.get('/api/v1/approvals/check', async (request, reply) => {
    const { trace_id } = request.query as { trace_id?: string };
    if (!trace_id) {
      return reply.code(400).send({
        success: false,
        error: { code: 'MISSING_TRACE_ID', message: 'trace_id query parameter required' },
      });
    }

    const ticket = await store.getTicketByTraceId(trace_id);
    if (!ticket) {
      return reply.code(404).send({ approved: false, status: 'NOT_FOUND' });
    }

    return reply.send({
      approved: ticket.status === 'APPROVED',
      status: ticket.status,
      ticket,
    });
  });

  // Approve request (dashboard format)
  fastify.post<{
    Params: { requestId: string };
    Body: {
      notes?: string;
      approver_id?: string;
      approver_role?: string;
      justification?: string;
    };
  }>(
    '/api/v1/approvals/:requestId/approve',
    async (request, reply) => {
      try {
        const ticket = await store.approve(request.params.requestId, {
          approver_id: request.body.approver_id ?? 'dashboard-user',
          approver_role: request.body.approver_role,
          justification: request.body.justification ?? request.body.notes,
        });

        // Transform to dashboard format
        return reply.send({
          request_id: ticket.ticket_id,
          trace_id: ticket.trace_id,
          actor_id: ticket.actor.id,
          actor_type: ticket.actor.type,
          action: ticket.action,
          resource_type: ticket.resource.type,
          resource_id: ticket.resource.id,
          reason_code: (ticket.context as any).reason_code || 'QUARANTINE',
          context: ticket.context,
          created_at: ticket.created_at,
          expires_at: ticket.expires_at,
          status: ticket.status,
          reviewed_by: ticket.decisions[0]?.approver_id,
          reviewed_at: ticket.resolved_at,
          review_notes: ticket.decisions[0]?.justification,
          required_role: ticket.required_role,
          require_justification: ticket.require_justification,
          security_binding: ticket.security_binding,
        });
      } catch (error) {
        if (isStixError(error)) {
          const stixError = error as StixError;
          return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
        }
        return reply.code(400).send({
          success: false,
          error: { code: 'APPROVE_FAILED', message: (error as Error).message },
        });
      }
    }
  );

  // Reject request (dashboard format)
  fastify.post<{
    Params: { requestId: string };
    Body: {
      notes?: string;
      approver_id?: string;
      approver_role?: string;
      justification?: string;
    };
  }>(
    '/api/v1/approvals/:requestId/reject',
    async (request, reply) => {
      try {
        const ticket = await store.reject(request.params.requestId, {
          approver_id: request.body.approver_id ?? 'dashboard-user',
          approver_role: request.body.approver_role,
          justification: request.body.justification ?? request.body.notes,
        });

        // Transform to dashboard format
        return reply.send({
          request_id: ticket.ticket_id,
          trace_id: ticket.trace_id,
          actor_id: ticket.actor.id,
          actor_type: ticket.actor.type,
          action: ticket.action,
          resource_type: ticket.resource.type,
          resource_id: ticket.resource.id,
          reason_code: (ticket.context as any).reason_code || 'QUARANTINE',
          context: ticket.context,
          created_at: ticket.created_at,
          expires_at: ticket.expires_at,
          status: ticket.status,
          reviewed_by: ticket.decisions[0]?.approver_id,
          reviewed_at: ticket.resolved_at,
          review_notes: ticket.decisions[0]?.justification,
          required_role: ticket.required_role,
          require_justification: ticket.require_justification,
          security_binding: ticket.security_binding,
        });
      } catch (error) {
        if (isStixError(error)) {
          const stixError = error as StixError;
          return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
        }
        return reply.code(400).send({
          success: false,
          error: { code: 'REJECT_FAILED', message: (error as Error).message },
        });
      }
    }
  );

  // Legacy: Approve ticket
  fastify.post<{ Params: { ticketId: string }; Body: ApproveInput }>(
    '/api/v1/approvals/tickets/:ticketId/approve',
    async (request, reply) => {
      try {
        const ticket = await store.approve(request.params.ticketId, request.body);
        return reply.send({ success: true, data: ticket });
      } catch (error) {
        if (isStixError(error)) {
          const stixError = error as StixError;
          return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
        }
        return reply.code(400).send({
          success: false,
          error: { code: 'APPROVE_FAILED', message: (error as Error).message },
        });
      }
    }
  );

  // Legacy: Reject ticket
  fastify.post<{ Params: { ticketId: string }; Body: ApproveInput }>(
    '/api/v1/approvals/tickets/:ticketId/reject',
    async (request, reply) => {
      try {
        const ticket = await store.reject(request.params.ticketId, request.body);
        return reply.send({ success: true, data: ticket });
      } catch (error) {
        if (isStixError(error)) {
          const stixError = error as StixError;
          return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
        }
        return reply.code(400).send({
          success: false,
          error: { code: 'REJECT_FAILED', message: (error as Error).message },
        });
      }
    }
  );

  // Cancel ticket
  fastify.post<{ Params: { ticketId: string } }>(
    '/api/v1/approvals/tickets/:ticketId/cancel',
    async (request, reply) => {
      try {
        const ticket = await store.cancel(request.params.ticketId);
        return reply.send({ success: true, data: ticket });
      } catch (error) {
        if (isStixError(error)) {
          const stixError = error as StixError;
          return reply.code(stixError.statusCode).send(createErrorResponse(stixError));
        }
        return reply.code(400).send({
          success: false,
          error: { code: 'CANCEL_FAILED', message: (error as Error).message },
        });
      }
    }
  );

  // Get approvals by trace ID (dashboard format)
  fastify.get<{ Params: { traceId: string } }>('/api/v1/approvals/trace/:traceId', async (request, reply) => {
    try {
      const ticket = await store.getTicketByTraceId(request.params.traceId);

      if (!ticket) {
        return reply.code(200).send([]);
      }

      // Return as array (dashboard expects ApprovalRequest[])
      return reply.send([{
        request_id: ticket.ticket_id,
        trace_id: ticket.trace_id,
        actor_id: ticket.actor.id,
        actor_type: ticket.actor.type,
        action: ticket.action,
        resource_type: ticket.resource.type,
        resource_id: ticket.resource.id,
        reason_code: (ticket.context as any).reason_code || 'QUARANTINE',
        context: ticket.context,
        created_at: ticket.created_at,
        expires_at: ticket.expires_at,
        status: ticket.status,
        reviewed_by: ticket.decisions[0]?.approver_id,
        reviewed_at: ticket.resolved_at,
        review_notes: ticket.decisions[0]?.justification,
        required_role: ticket.required_role,
        require_justification: ticket.require_justification,
        security_binding: ticket.security_binding,
      }]);
    } catch (error) {
      return reply.code(500).send({
        success: false,
        error: { code: 'GET_FAILED', message: (error as Error).message },
      });
    }
  });

  // List pending tickets
  fastify.get('/api/v1/approvals/pending', async (request, reply) => {
    const { required_role, limit } = request.query as { required_role?: string; limit?: number };
    const tickets = await store.listPending({ required_role, limit: limit ?? 50 });
    return reply.send({ success: true, data: tickets, meta: { count: tickets.length } });
  });
}

// =============================================================================
// APPLICATION
// =============================================================================

async function createApp() {
  const config = loadConfig();
  const logger = createLoggerFromEnv(config.service.name);
  
  logger.info('Starting STIX Approvals Service', {
    version: config.service.version,
    env: config.service.env,
  });

  const server = Fastify({
    logger: false,
    requestIdHeader: HEADERS.REQUEST_ID,
    trustProxy: true,
  });

  await server.register(cors, { origin: config.service.env === 'prod' ? false : true });
  await server.register(helmet, { contentSecurityPolicy: false });

  server.addHook('onRequest', async (request, reply) => {
    if (!config.auth.serviceTokenAuthEnabled) {
      return;
    }

    const path = request.url.split('?')[0];
    const publicPaths = new Set(['/health', '/ready']);
    if (publicPaths.has(path)) {
      return;
    }

    const providedToken = request.headers['x-stix-service-token'];
    const token = Array.isArray(providedToken) ? providedToken[0] : providedToken;
    if (!token || token !== config.auth.serviceToken) {
      return reply.code(401).send({
        success: false,
        error: {
          code: 'AUTHENTICATION_REQUIRED',
          message: 'Valid service token is required',
        },
      });
    }
  });

  let pool: Pool | null = null;
  let store: ApprovalStoreContract;
  if (config.storage.type === 'postgres') {
    pool = new Pool({
      connectionString: config.storage.postgresUrl,
      max: 20,
      min: 2,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
    });
    const pgStore = new PostgresApprovalStore(pool, logger);
    await pgStore.initialize();
    store = pgStore;
  } else {
    store = new ApprovalStore(logger);
  }
  const startTime = Date.now();

  server.addHook('onResponse', async (request, reply) => {
    logger.http(`${request.method} ${request.url} ${reply.statusCode}`, {
      method: request.method,
      path: request.url,
      status_code: reply.statusCode,
      duration_ms: reply.elapsedTime,
    });
  });

  await registerRoutes(server, store, config, startTime);

  return { config, logger, server, store, startTime, pool };
}

async function start(): Promise<void> {
  const { config, logger, server, pool } = await createApp();

  process.on('SIGTERM', async () => {
    logger.info('Shutting down...');
    await server.close();
    if (pool) {
      await pool.end();
    }
    process.exit(0);
  });

  try {
    await server.listen({ port: config.service.port, host: config.service.host });
    logger.info('STIX Approvals Service listening', {
      port: config.service.port,
      env: config.service.env,
    });
  } catch (err) {
    logger.error('Failed to start', {}, err as Error);
    process.exit(1);
  }
}

export { createApp, start };

// Start if running directly
const isMainModule = () => {
  const moduleUrl = import.meta.url;
  const scriptPath = process.argv[1];
  const normalizedModuleUrl = moduleUrl.replace(/\\/g, '/');
  const normalizedScriptPath = scriptPath?.replace(/\\/g, '/');
  return normalizedModuleUrl.endsWith(normalizedScriptPath) ||
         normalizedModuleUrl === `file:///${normalizedScriptPath}` ||
         normalizedModuleUrl === `file://${normalizedScriptPath}`;
};

if (isMainModule()) {
  start().catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
  });
}
