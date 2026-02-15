/**
 * STIX Approval Workflow Manager
 * Handles approval ticket lifecycle and decision processing
 */

import {
  type Actor,
  type Resource,
  type Context,
  type Logger,
  generateApprovalTicketId,
  isoTimestamp,
  ApprovalNotFoundError,
  ApprovalExpiredError,
  ApprovalAlreadyProcessedError,
} from '@stix/shared';
import { Pool } from 'pg';
import type { Config } from '../config/index.js';
import { createPostgresApprovalStore } from '../store/postgres.js';

// =============================================================================
// TYPES
// =============================================================================

export type ApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED' | 'CANCELLED';

export interface ApprovalDecision {
  approver_id: string;
  approver_role?: string;
  decision: 'APPROVE' | 'REJECT';
  justification?: string;
  timestamp: string;
}

export interface ApprovalTicket {
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
  cancellation_reason?: string;
}

export interface CreateTicketRequest {
  ticket_id?: string;
  trace_id: string;
  actor: Actor;
  action: string;
  resource: Resource;
  context: Context;
  required_count?: number;
  required_role?: string;
  require_justification?: boolean;
  expires_at?: string;
  timeout_hours?: number;
}

export interface SubmitDecisionRequest {
  ticket_id: string;
  approver_id: string;
  approver_role?: string;
  decision: 'APPROVE' | 'REJECT';
  justification?: string;
}

export interface ListTicketsOptions {
  status?: ApprovalStatus;
  approver_role?: string;
  actor_id?: string;
  limit?: number;
  offset?: number;
}

// =============================================================================
// APPROVAL STORE INTERFACE
// =============================================================================

export interface ApprovalStore {
  createTicket(ticket: ApprovalTicket): Promise<ApprovalTicket>;
  getTicket(ticketId: string): Promise<ApprovalTicket | null>;
  getTicketByTrace(traceId: string): Promise<ApprovalTicket | null>;
  updateTicket(ticket: ApprovalTicket): Promise<void>;
  listTickets(options?: ListTicketsOptions): Promise<ApprovalTicket[]>;
  deleteTicket(ticketId: string): Promise<void>;
  health(): Promise<boolean>;
}

// =============================================================================
// IN-MEMORY APPROVAL STORE
// =============================================================================

export class InMemoryApprovalStore implements ApprovalStore {
  private tickets: Map<string, ApprovalTicket> = new Map();
  private traceIndex: Map<string, string> = new Map();

  async createTicket(ticket: ApprovalTicket): Promise<ApprovalTicket> {
    this.tickets.set(ticket.ticket_id, ticket);
    this.traceIndex.set(ticket.trace_id, ticket.ticket_id);
    return ticket;
  }

  async getTicket(ticketId: string): Promise<ApprovalTicket | null> {
    return this.tickets.get(ticketId) ?? null;
  }

  async getTicketByTrace(traceId: string): Promise<ApprovalTicket | null> {
    const ticketId = this.traceIndex.get(traceId);
    if (!ticketId) return null;
    return this.tickets.get(ticketId) ?? null;
  }

  async updateTicket(ticket: ApprovalTicket): Promise<void> {
    this.tickets.set(ticket.ticket_id, ticket);
  }

  async listTickets(options?: ListTicketsOptions): Promise<ApprovalTicket[]> {
    let tickets = Array.from(this.tickets.values());

    if (options?.status) {
      tickets = tickets.filter(t => t.status === options.status);
    }

    if (options?.approver_role) {
      tickets = tickets.filter(t => 
        !t.required_role || t.required_role === options.approver_role
      );
    }

    if (options?.actor_id) {
      tickets = tickets.filter(t => t.actor.id === options.actor_id);
    }

    // Sort by created_at descending
    tickets.sort((a, b) => 
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );

    // Pagination
    const offset = options?.offset ?? 0;
    const limit = options?.limit ?? 50;
    tickets = tickets.slice(offset, offset + limit);

    return tickets;
  }

  async deleteTicket(ticketId: string): Promise<void> {
    const ticket = this.tickets.get(ticketId);
    if (ticket) {
      this.traceIndex.delete(ticket.trace_id);
      this.tickets.delete(ticketId);
    }
  }

  async health(): Promise<boolean> {
    return true;
  }

  clear(): void {
    this.tickets.clear();
    this.traceIndex.clear();
  }
}

// =============================================================================
// APPROVAL WORKFLOW MANAGER
// =============================================================================

export class ApprovalWorkflow {
  private readonly config: Config;
  private readonly logger: Logger;
  private readonly store: ApprovalStore;
  private cleanupInterval: ReturnType<typeof setInterval> | null = null;

  constructor(config: Config, logger: Logger, store: ApprovalStore) {
    this.config = config;
    this.logger = logger.child({ component: 'ApprovalWorkflow' });
    this.store = store;

    // Start cleanup job
    this.startCleanup();
  }

  /**
   * Create a new approval ticket
   */
  async createTicket(request: CreateTicketRequest): Promise<ApprovalTicket> {
    const ticketId = request.ticket_id ?? generateApprovalTicketId();
    const now = isoTimestamp();

    // Calculate expiration
    const timeoutHours = Math.min(
      request.timeout_hours ?? this.config.approvals.defaultTimeoutHours,
      this.config.approvals.maxTimeoutHours
    );
    const expiresAt = request.expires_at ?? 
      new Date(Date.now() + timeoutHours * 60 * 60 * 1000).toISOString();

    const ticket: ApprovalTicket = {
      ticket_id: ticketId,
      trace_id: request.trace_id,
      status: 'PENDING',
      actor: request.actor,
      action: request.action,
      resource: request.resource,
      context: request.context,
      required_count: request.required_count ?? 1,
      required_role: request.required_role,
      require_justification: request.require_justification ?? false,
      decisions: [],
      created_at: now,
      expires_at: expiresAt,
    };

    await this.store.createTicket(ticket);

    this.logger.info('Approval ticket created', {
      ticket_id: ticketId,
      trace_id: request.trace_id,
      expires_at: expiresAt,
      required_count: ticket.required_count,
    });

    // Send notifications if enabled
    if (this.config.approvals.enableNotifications) {
      await this.notifyApprovers(ticket);
    }

    return ticket;
  }

  /**
   * Get a ticket by ID
   */
  async getTicket(ticketId: string): Promise<ApprovalTicket> {
    const ticket = await this.store.getTicket(ticketId);
    
    if (!ticket) {
      throw new ApprovalNotFoundError(ticketId);
    }

    // Check and update expiration status
    if (ticket.status === 'PENDING' && this.isExpired(ticket)) {
      ticket.status = 'EXPIRED';
      ticket.resolved_at = isoTimestamp();
      await this.store.updateTicket(ticket);
    }

    return ticket;
  }

  /**
   * Get a ticket by trace ID
   */
  async getTicketByTrace(traceId: string): Promise<ApprovalTicket | null> {
    const ticket = await this.store.getTicketByTrace(traceId);
    
    if (ticket && ticket.status === 'PENDING' && this.isExpired(ticket)) {
      ticket.status = 'EXPIRED';
      ticket.resolved_at = isoTimestamp();
      await this.store.updateTicket(ticket);
    }

    return ticket;
  }

  /**
   * List tickets with optional filtering
   */
  async listTickets(options?: ListTicketsOptions): Promise<ApprovalTicket[]> {
    return this.store.listTickets(options);
  }

  /**
   * Submit an approval decision
   */
  async submitDecision(request: SubmitDecisionRequest): Promise<ApprovalTicket> {
    const ticket = await this.getTicket(request.ticket_id);

    // Validate ticket is still pending
    if (ticket.status !== 'PENDING') {
      throw new ApprovalAlreadyProcessedError(ticket.ticket_id, ticket.status);
    }

    // Validate role if required
    if (ticket.required_role && request.approver_role !== ticket.required_role) {
      throw new Error(`Approver role '${request.approver_role}' does not match required role '${ticket.required_role}'`);
    }

    // Validate justification if required
    if (ticket.require_justification && !request.justification) {
      throw new Error('Justification is required for this approval');
    }

    // Check if this approver has already decided
    const existingDecision = ticket.decisions.find(d => d.approver_id === request.approver_id);
    if (existingDecision) {
      throw new Error(`Approver '${request.approver_id}' has already submitted a decision`);
    }

    // Add decision
    const decision: ApprovalDecision = {
      approver_id: request.approver_id,
      approver_role: request.approver_role,
      decision: request.decision,
      justification: request.justification,
      timestamp: isoTimestamp(),
    };

    ticket.decisions.push(decision);

    // Check if ticket should be resolved
    if (request.decision === 'REJECT') {
      // Any rejection resolves the ticket as rejected
      ticket.status = 'REJECTED';
      ticket.resolved_at = isoTimestamp();
      
      this.logger.info('Approval ticket rejected', {
        ticket_id: ticket.ticket_id,
        approver_id: request.approver_id,
      });
    } else {
      // Check if we have enough approvals
      const approveCount = ticket.decisions.filter(d => d.decision === 'APPROVE').length;
      
      if (approveCount >= ticket.required_count) {
        ticket.status = 'APPROVED';
        ticket.resolved_at = isoTimestamp();
        
        this.logger.info('Approval ticket approved', {
          ticket_id: ticket.ticket_id,
          approve_count: approveCount,
          required_count: ticket.required_count,
        });
      }
    }

    await this.store.updateTicket(ticket);

    // Send notification about decision
    if (this.config.approvals.enableNotifications) {
      await this.notifyRequester(ticket, request.decision);
    }

    return ticket;
  }

  /**
   * Cancel a pending ticket
   */
  async cancelTicket(ticketId: string, reason?: string): Promise<ApprovalTicket> {
    const ticket = await this.getTicket(ticketId);

    if (ticket.status !== 'PENDING') {
      throw new ApprovalAlreadyProcessedError(ticket.ticket_id, ticket.status);
    }

    ticket.status = 'CANCELLED';
    ticket.resolved_at = isoTimestamp();
    ticket.cancellation_reason = reason;

    await this.store.updateTicket(ticket);

    this.logger.info('Approval ticket cancelled', {
      ticket_id: ticketId,
      reason,
    });

    return ticket;
  }

  /**
   * Check if a trace has approved status
   */
  async isApproved(traceId: string): Promise<boolean> {
    const ticket = await this.getTicketByTrace(traceId);
    return ticket?.status === 'APPROVED';
  }

  /**
   * Check if a ticket is expired
   */
  private isExpired(ticket: ApprovalTicket): boolean {
    return new Date(ticket.expires_at) < new Date();
  }

  /**
   * Notify approvers about new ticket
   */
  private async notifyApprovers(ticket: ApprovalTicket): Promise<void> {
    this.logger.debug('Sending approver notifications', {
      ticket_id: ticket.ticket_id,
      required_role: ticket.required_role,
    });

    // Webhook notification
    if (this.config.notifications.webhookUrl) {
      try {
        await fetch(this.config.notifications.webhookUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'approval_required',
            ticket_id: ticket.ticket_id,
            trace_id: ticket.trace_id,
            actor: ticket.actor,
            action: ticket.action,
            resource: ticket.resource,
            required_role: ticket.required_role,
            expires_at: ticket.expires_at,
          }),
        });
      } catch (error) {
        this.logger.warn('Failed to send webhook notification', {
          error: (error as Error).message,
        });
      }
    }
  }

  /**
   * Notify requester about decision
   */
  private async notifyRequester(ticket: ApprovalTicket, decision: string): Promise<void> {
    this.logger.debug('Sending requester notification', {
      ticket_id: ticket.ticket_id,
      status: ticket.status,
    });

    if (this.config.notifications.webhookUrl) {
      try {
        await fetch(this.config.notifications.webhookUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            type: 'approval_decision',
            ticket_id: ticket.ticket_id,
            trace_id: ticket.trace_id,
            status: ticket.status,
            decision,
            actor: ticket.actor,
          }),
        });
      } catch (error) {
        this.logger.warn('Failed to send webhook notification', {
          error: (error as Error).message,
        });
      }
    }
  }

  /**
   * Start cleanup job for expired tickets
   */
  private startCleanup(): void {
    const intervalMs = this.config.approvals.cleanupIntervalMinutes * 60 * 1000;

    this.cleanupInterval = setInterval(async () => {
      await this.expireStaleTickets();
    }, intervalMs);

    this.logger.debug('Cleanup job started', {
      interval_minutes: this.config.approvals.cleanupIntervalMinutes,
    });
  }

  /**
   * Expire stale tickets
   */
  async expireStaleTickets(): Promise<number> {
    const pendingTickets = await this.store.listTickets({ status: 'PENDING' });
    let expired = 0;

    for (const ticket of pendingTickets) {
      if (this.isExpired(ticket)) {
        ticket.status = 'EXPIRED';
        ticket.resolved_at = isoTimestamp();
        await this.store.updateTicket(ticket);
        expired++;

        this.logger.debug('Ticket expired', { ticket_id: ticket.ticket_id });
      }
    }

    if (expired > 0) {
      this.logger.info('Expired stale tickets', { count: expired });
    }

    return expired;
  }

  /**
   * Stop cleanup job
   */
  stopCleanup(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
  }
}

// =============================================================================
// FACTORY
// =============================================================================

export async function createApprovalStore(
  config: Config,
  logger: Logger
): Promise<ApprovalStore> {
  const storeType = config.storage?.type ?? 'memory';

  switch (storeType) {
    case 'memory':
      return new InMemoryApprovalStore();

    case 'postgres':
      if (!config.storage.postgresUrl) {
        throw new Error('STORAGE_TYPE=postgres requires POSTGRES_URL for stix-approvals.');
      }
      return createPostgresApprovalStore(
        new Pool({
          connectionString: config.storage.postgresUrl,
          max: 20,
          min: 2,
          idleTimeoutMillis: 30000,
          connectionTimeoutMillis: 5000,
        }),
        logger
      );

    default:
      throw new Error(`Unsupported approvals storage type: ${storeType}`);
  }
}
