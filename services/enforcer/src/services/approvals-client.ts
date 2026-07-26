/**
 * Approvals Service Client
 * HTTP client for communicating with the STIX Approvals Service
 */

import {
  type Actor,
  type Resource,
  type Context,
  type ApprovalBinding,
  type Logger,
  retry,
  withTimeout,
  ServiceUnavailableError,
  ApprovalNotFoundError,
  ApprovalExpiredError,
} from '@stix/shared';
import type { Config } from '../config/index.js';

// =============================================================================
// TYPES
// =============================================================================

export interface CreateTicketRequest {
  ticket_id: string;
  trace_id: string;
  actor: Actor;
  action: string;
  resource: Resource;
  context: Context;
  required_count: number;
  required_role?: string;
  require_justification: boolean;
  expires_at: string;
  security_binding: ApprovalBinding;
}

export interface ApprovalTicket {
  ticket_id: string;
  trace_id: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED' | 'CANCELLED';
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

export interface ApprovalDecision {
  approver_id: string;
  approver_role?: string;
  decision: 'APPROVE' | 'REJECT';
  justification?: string;
  timestamp: string;
}

export interface CheckApprovalResponse {
  approved: boolean;
  status: ApprovalTicket['status'];
  ticket?: ApprovalTicket;
}

// =============================================================================
// APPROVALS CLIENT
// =============================================================================

export class ApprovalsClient {
  private readonly config: Config;
  protected readonly logger: Logger;
  private readonly baseUrl: string;
  private readonly serviceAuthToken: string | null;

  constructor(config: Config, logger: Logger) {
    this.config = config;
    this.logger = logger.child({ component: 'ApprovalsClient' });
    this.baseUrl = config.services.approvalsUrl;
    this.serviceAuthToken = config.services.serviceAuthToken || null;
  }

  /**
   * Create approval ticket
   */
  async createTicket(request: CreateTicketRequest): Promise<ApprovalTicket> {
    this.logger.debug('Creating approval ticket', {
      ticket_id: request.ticket_id,
      trace_id: request.trace_id,
    });

    try {
      const result = await retry(
        async () => {
          return withTimeout(
            this.doCreateTicket(request),
            this.config.timeouts.serviceRequest
          );
        },
        {
          maxAttempts: this.config.retry.maxAttempts,
          initialDelayMs: this.config.retry.initialDelayMs,
          maxDelayMs: this.config.retry.maxDelayMs,
        }
      );

      return result;
    } catch (error) {
      throw new ServiceUnavailableError('Approvals service', (error as Error).message);
    }
  }

  /**
   * Perform actual ticket creation
   */
  private async doCreateTicket(request: CreateTicketRequest): Promise<ApprovalTicket> {
    const headers = this.buildHeaders();
    const response = await fetch(`${this.baseUrl}/api/v1/approvals/tickets`, {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
    });

    const payload = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(`Ticket creation failed: ${this.extractErrorMessage(payload, response.status)}`);
    }

    return this.parseTicketResponse(payload);
  }

  /**
   * Get approval ticket by ID
   */
  async getTicket(ticketId: string): Promise<ApprovalTicket> {
    this.logger.debug('Fetching approval ticket', { ticket_id: ticketId });

    const response = await fetch(`${this.baseUrl}/api/v1/approvals/tickets/${ticketId}`, {
      headers: this.buildHeaders(false),
    });
    const payload = await response.json().catch(() => null);

    if (!response.ok) {
      if (response.status === 404) {
        throw new ApprovalNotFoundError(ticketId);
      }
      throw new ServiceUnavailableError(
        'Approvals service',
        this.extractErrorMessage(payload, response.status)
      );
    }

    return this.parseTicketResponse(payload);
  }

  /**
   * Check if approval has been granted for a trace
   */
  async checkApproval(traceId: string): Promise<CheckApprovalResponse> {
    this.logger.debug('Checking approval status', { trace_id: traceId });

    const response = await fetch(
      `${this.baseUrl}/api/v1/approvals/check?trace_id=${encodeURIComponent(traceId)}`,
      { headers: this.buildHeaders(false) }
    );
    const payload = await response.json().catch(() => null);

    if (!response.ok) {
      if (response.status === 404) {
        return { approved: false, status: 'PENDING' };
      }
      throw new ServiceUnavailableError(
        'Approvals service',
        this.extractErrorMessage(payload, response.status)
      );
    }

    return this.parseCheckApprovalResponse(payload);
  }

  /**
   * Health check
   */
  async health(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        headers: this.buildHeaders(false),
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  private buildHeaders(withJson = true): Record<string, string> {
    const headers: Record<string, string> = {};
    if (withJson) {
      headers['Content-Type'] = 'application/json';
    }
    if (this.serviceAuthToken) {
      headers['X-STIX-Service-Token'] = this.serviceAuthToken;
    }
    return headers;
  }

  private extractErrorMessage(payload: unknown, status: number): string {
    if (payload && typeof payload === 'object') {
      const body = payload as {
        message?: unknown;
        error?: { message?: unknown };
      };
      const fromError = body.error?.message;
      if (typeof fromError === 'string' && fromError.length > 0) {
        return fromError;
      }
      if (typeof body.message === 'string' && body.message.length > 0) {
        return body.message;
      }
    }
    return `Status ${status}`;
  }

  private parseTicketResponse(payload: unknown): ApprovalTicket {
    if (!payload || typeof payload !== 'object') {
      throw new Error('Invalid ticket response from approvals service');
    }

    const body = payload as { ticket_id?: unknown; data?: unknown };
    if (typeof body.ticket_id === 'string') {
      return payload as ApprovalTicket;
    }

    if (body.data && typeof body.data === 'object') {
      const ticket = body.data as { ticket_id?: unknown };
      if (typeof ticket.ticket_id === 'string') {
        return body.data as ApprovalTicket;
      }
    }

    throw new Error('Invalid ticket response from approvals service');
  }

  private parseCheckApprovalResponse(payload: unknown): CheckApprovalResponse {
    if (!payload || typeof payload !== 'object') {
      throw new Error('Invalid approval check response from approvals service');
    }

    const body = payload as {
      approved?: unknown;
      status?: unknown;
      ticket?: unknown;
      data?: unknown;
    };

    if (typeof body.approved === 'boolean' && typeof body.status === 'string') {
      return {
        approved: body.approved,
        status: body.status as CheckApprovalResponse['status'],
        ticket: body.ticket as ApprovalTicket | undefined,
      };
    }

    if (body.data && typeof body.data === 'object') {
      const nested = body.data as {
        approved?: unknown;
        status?: unknown;
        ticket?: unknown;
      };
      if (typeof nested.approved === 'boolean' && typeof nested.status === 'string') {
        return {
          approved: nested.approved,
          status: nested.status as CheckApprovalResponse['status'],
          ticket: nested.ticket as ApprovalTicket | undefined,
        };
      }
    }

    throw new Error('Invalid approval check response from approvals service');
  }
}

// =============================================================================
// MOCK APPROVALS CLIENT (for development/testing)
// =============================================================================

export class MockApprovalsClient extends ApprovalsClient {
  private readonly tickets: Map<string, ApprovalTicket> = new Map();
  private readonly traceIndex: Map<string, string> = new Map(); // trace_id -> ticket_id

  async createTicket(request: CreateTicketRequest): Promise<ApprovalTicket> {
    const ticket: ApprovalTicket = {
      ticket_id: request.ticket_id,
      trace_id: request.trace_id,
      status: 'PENDING',
      actor: request.actor,
      action: request.action,
      resource: request.resource,
      context: request.context,
      required_count: request.required_count,
      required_role: request.required_role,
      require_justification: request.require_justification,
      decisions: [],
      created_at: new Date().toISOString(),
      expires_at: request.expires_at,
      security_binding: request.security_binding,
    };

    this.tickets.set(request.ticket_id, ticket);
    this.traceIndex.set(request.trace_id, request.ticket_id);
    
    this.logger.debug('Mock: Created approval ticket', { ticket_id: request.ticket_id });
    return ticket;
  }

  async getTicket(ticketId: string): Promise<ApprovalTicket> {
    const ticket = this.tickets.get(ticketId);
    if (!ticket) {
      throw new ApprovalNotFoundError(ticketId);
    }
    
    // Check expiration
    if (new Date(ticket.expires_at) < new Date() && ticket.status === 'PENDING') {
      ticket.status = 'EXPIRED';
    }
    
    return ticket;
  }

  async checkApproval(traceId: string): Promise<CheckApprovalResponse> {
    const ticketId = this.traceIndex.get(traceId);
    if (!ticketId) {
      return { approved: false, status: 'PENDING' };
    }

    const ticket = await this.getTicket(ticketId);
    return {
      approved: ticket.status === 'APPROVED',
      status: ticket.status,
      ticket,
    };
  }

  async health(): Promise<boolean> {
    return true;
  }

  // Test helpers
  approveTicket(ticketId: string, approverId: string, role?: string, justification?: string): void {
    const ticket = this.tickets.get(ticketId);
    if (!ticket) throw new ApprovalNotFoundError(ticketId);
    
    ticket.decisions.push({
      approver_id: approverId,
      approver_role: role,
      decision: 'APPROVE',
      justification,
      timestamp: new Date().toISOString(),
    });

    if (ticket.decisions.filter(d => d.decision === 'APPROVE').length >= ticket.required_count) {
      ticket.status = 'APPROVED';
      ticket.resolved_at = new Date().toISOString();
    }
  }

  rejectTicket(ticketId: string, approverId: string, role?: string, justification?: string): void {
    const ticket = this.tickets.get(ticketId);
    if (!ticket) throw new ApprovalNotFoundError(ticketId);

    ticket.decisions.push({
      approver_id: approverId,
      approver_role: role,
      decision: 'REJECT',
      justification,
      timestamp: new Date().toISOString(),
    });
    ticket.status = 'REJECTED';
    ticket.resolved_at = new Date().toISOString();
  }

  clear(): void {
    this.tickets.clear();
    this.traceIndex.clear();
  }
}
