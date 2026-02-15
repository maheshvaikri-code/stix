/**
 * STIX Hash Chain Manager
 * Implements tamper-evident event chain with cryptographic integrity
 */

import {
  type EvidenceEvent,
  type SigningKey,
  hashCanonical,
  signEvidence,
  isoTimestamp,
  generateEventId,
  ZERO_HASH,
} from '@stix/shared';

// =============================================================================
// TYPES
// =============================================================================

export interface ChainVerificationResult {
  valid: boolean;
  eventCount: number;
  firstEventId?: string;
  lastEventId?: string;
  brokenAtEventId?: string;
  errors: string[];
}

export interface DecisionEventData {
  trace_id: string;
  decision: string;
  reason_code: string;
  actor: unknown;
  action: unknown;
  resource: unknown;
  context: unknown;
  policy: unknown;
  controls: string[];
  regulations: string[];
}

export interface OutcomeEventData {
  trace_id: string;
  status: string;
  result_summary?: string;
  error_class?: string;
  obligations_applied?: Record<string, boolean>;
}

// =============================================================================
// HASH CHAIN MANAGER
// =============================================================================

export class HashChainManager {
  private readonly signingKey: SigningKey | null;
  private chainHeads: Map<string, string> = new Map();

  constructor(signingKey: SigningKey | null) {
    this.signingKey = signingKey;
  }

  /**
   * Create a decision event
   */
  createDecisionEvent(data: DecisionEventData): EvidenceEvent {
    const prevHash = this.chainHeads.get(data.trace_id) ?? ZERO_HASH;
    const eventId = generateEventId();
    const timestamp = isoTimestamp();

    const event: EvidenceEvent = {
      event_id: eventId,
      trace_id: data.trace_id,
      event_type: 'DECISION',
      timestamp,
      version: 'v1.0',
      integrity: {
        prev_hash: prevHash,
        event_hash: '', // Computed below
        signature: '',
        algorithm: 'sha256',
        key_id: this.signingKey?.keyId,
      },
      decision: data.decision as any,
      reason_code: data.reason_code,
      actor: data.actor as any,
      action: data.action as any,
      resource: data.resource as any,
      context: data.context as any,
      policy: data.policy as any,
      controls: data.controls,
      regulations: data.regulations,
    };

    // Compute event hash
    event.integrity.event_hash = this.computeEventHash(event);

    // Sign if key available
    if (this.signingKey) {
      const signingPayload = this.buildSigningPayload(event);
      const signResult = signEvidence(signingPayload, prevHash, this.signingKey);
      event.integrity.signature = signResult.signature;
      event.integrity.key_id = signResult.keyId;
    }

    // Update chain head
    this.chainHeads.set(data.trace_id, event.integrity.event_hash);

    return event;
  }

  /**
   * Create an outcome event
   */
  createOutcomeEvent(data: OutcomeEventData): EvidenceEvent {
    const prevHash = this.chainHeads.get(data.trace_id) ?? ZERO_HASH;
    const eventId = generateEventId();
    const timestamp = isoTimestamp();

    const event: EvidenceEvent = {
      event_id: eventId,
      trace_id: data.trace_id,
      event_type: 'OUTCOME',
      timestamp,
      version: 'v1.0',
      integrity: {
        prev_hash: prevHash,
        event_hash: '',
        signature: '',
        algorithm: 'sha256',
        key_id: this.signingKey?.keyId,
      },
      outcome: {
        status: data.status as any,
        result_summary: data.result_summary,
        error_class: data.error_class,
      },
      obligations_applied: data.obligations_applied,
    };

    // Compute event hash
    event.integrity.event_hash = this.computeEventHash(event);

    // Sign if key available
    if (this.signingKey) {
      const signingPayload = this.buildSigningPayload(event);
      const signResult = signEvidence(signingPayload, prevHash, this.signingKey);
      event.integrity.signature = signResult.signature;
      event.integrity.key_id = signResult.keyId;
    }

    // Update chain head
    this.chainHeads.set(data.trace_id, event.integrity.event_hash);

    return event;
  }

  /**
   * Compute hash of event (excluding signature)
   */
  computeEventHash(event: EvidenceEvent): string {
    // Create hash data excluding signature
    const hashData: Record<string, unknown> = {
      event_id: event.event_id,
      trace_id: event.trace_id,
      event_type: event.event_type,
      timestamp: event.timestamp,
      version: event.version,
      prev_hash: event.integrity.prev_hash,
    };

    // Add type-specific fields
    if (event.event_type === 'DECISION') {
      hashData.decision = event.decision;
      hashData.reason_code = event.reason_code;
      hashData.actor = event.actor;
      hashData.action = event.action;
      hashData.resource = event.resource;
      hashData.context = event.context;
      hashData.policy = event.policy;
      hashData.controls = event.controls;
      hashData.regulations = event.regulations;
    } else if (event.event_type === 'OUTCOME') {
      hashData.outcome = event.outcome;
      hashData.obligations_applied = event.obligations_applied;
    }

    return hashCanonical(hashData);
  }

  /**
   * Verify a single event's integrity
   */
  async verifyEvent(event: EvidenceEvent): Promise<boolean> {
    // Verify hash
    const computedHash = this.computeEventHash(event);
    if (computedHash !== event.integrity.event_hash) {
      return false;
    }

    return true;
  }

  private buildSigningPayload(event: EvidenceEvent): Record<string, unknown> {
    const payload: Record<string, unknown> = {
      event_id: event.event_id,
      trace_id: event.trace_id,
      event_type: event.event_type,
      timestamp: event.timestamp,
      version: event.version,
      decision: event.decision,
      reason_code: event.reason_code,
      actor: event.actor,
      action: event.action,
      resource: event.resource,
      context: event.context,
      policy: event.policy,
      controls: event.controls,
      regulations: event.regulations,
      outcome: event.outcome,
      obligations_applied: event.obligations_applied,
    };
    return payload;
  }

  /**
   * Verify entire chain integrity
   */
  verifyChain(events: EvidenceEvent[]): ChainVerificationResult {
    if (events.length === 0) {
      return {
        valid: true,
        eventCount: 0,
        errors: [],
      };
    }

    // Sort by timestamp
    const sorted = [...events].sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    const errors: string[] = [];
    let expectedPrevHash = ZERO_HASH;

    for (let i = 0; i < sorted.length; i++) {
      const event = sorted[i];

      // Check prev_hash linkage
      if (event.integrity.prev_hash !== expectedPrevHash) {
        errors.push(`Event ${event.event_id}: prev_hash mismatch. Expected ${expectedPrevHash.substring(0, 16)}..., got ${event.integrity.prev_hash.substring(0, 16)}...`);
        return {
          valid: false,
          eventCount: sorted.length,
          firstEventId: sorted[0].event_id,
          lastEventId: sorted[sorted.length - 1].event_id,
          brokenAtEventId: event.event_id,
          errors,
        };
      }

      // Verify event hash
      const computedHash = this.computeEventHash(event);
      if (computedHash !== event.integrity.event_hash) {
        errors.push(`Event ${event.event_id}: event_hash mismatch (possible tampering)`);
        return {
          valid: false,
          eventCount: sorted.length,
          firstEventId: sorted[0].event_id,
          lastEventId: sorted[sorted.length - 1].event_id,
          brokenAtEventId: event.event_id,
          errors,
        };
      }

      expectedPrevHash = event.integrity.event_hash;
    }

    return {
      valid: true,
      eventCount: sorted.length,
      firstEventId: sorted[0].event_id,
      lastEventId: sorted[sorted.length - 1].event_id,
      errors: [],
    };
  }

  /**
   * Get current chain head for a trace
   */
  getChainHead(traceId: string): string {
    return this.chainHeads.get(traceId) ?? ZERO_HASH;
  }

  /**
   * Initialize chain head from stored events
   */
  initializeChainHead(traceId: string, lastHash: string): void {
    this.chainHeads.set(traceId, lastHash);
  }

  /**
   * Clear all chain heads (for testing)
   */
  clearChainHeads(): void {
    this.chainHeads.clear();
  }
}
