/**
 * STIX Replay - Evidence Verification Helpers
 * Pre-replay integrity validation (schema, hash chain, and optional signatures)
 */

import * as fs from 'node:fs';
import {
  type EvidenceEvent,
  loadPublicKey,
  validateEvidenceEvent,
  verifyEvidenceSignature,
  verifyHashChain,
} from '@stix/shared';

export interface ReplayVerificationOptions {
  /** Optional public key PEM path for signature verification */
  publicKeyPath?: string;
  /** Optional key ID filter for signature verification */
  keyId?: string;
}

export interface ReplayVerificationResult {
  valid: boolean;
  verifiedBundles: number;
  verifiedEvents: number;
  signatureChecks: number;
  signatureFailures: number;
  errors: string[];
  warnings: string[];
}

/**
 * Verify replay bundles before policy replay.
 */
export function verifyBundlesForReplay(
  bundles: any[],
  options: ReplayVerificationOptions = {}
): ReplayVerificationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  let verifiedBundles = 0;
  let verifiedEvents = 0;
  let signatureChecks = 0;
  let signatureFailures = 0;

  let publicKey: ReturnType<typeof loadPublicKey> | undefined;
  if (options.publicKeyPath) {
    const keyPem = fs.readFileSync(options.publicKeyPath, 'utf-8');
    publicKey = loadPublicKey(keyPem);
  } else {
    warnings.push('Signature verification skipped (no --verify-key provided).');
  }

  for (let bundleIndex = 0; bundleIndex < bundles.length; bundleIndex++) {
    const bundle = bundles[bundleIndex];
    const events = normalizeBundleEvents(bundle);

    if (events.length === 0) {
      errors.push(`Bundle[${bundleIndex}] has no events.`);
      continue;
    }

    const validatedEvents: EvidenceEvent[] = [];

    for (let eventIndex = 0; eventIndex < events.length; eventIndex++) {
      const rawEvent = events[eventIndex];
      try {
        const validated = validateEvidenceEvent(rawEvent);
        validatedEvents.push(validated);
      } catch (error) {
        const traceId = (rawEvent as any)?.trace_id ?? bundle?.trace_id ?? 'unknown_trace';
        const eventId = (rawEvent as any)?.event_id ?? `event_${eventIndex}`;
        errors.push(
          `Bundle[${bundleIndex}] ${traceId}/${eventId} failed schema validation: ${(error as Error).message}`
        );
      }
    }

    if (validatedEvents.length === 0) {
      continue;
    }

    const chain = verifyHashChain(validatedEvents);
    if (!chain.valid) {
      for (const chainError of chain.errors) {
        errors.push(
          `Bundle[${bundleIndex}] ${chainError.eventId} hash-chain error: ${chainError.error}`
        );
      }
    }

    if (publicKey) {
      for (const event of validatedEvents) {
        if (options.keyId && event.integrity.key_id !== options.keyId) {
          continue;
        }
        if (!event.integrity.key_id) {
          warnings.push(
            `${event.trace_id}/${event.event_id} has no integrity.key_id; skipping signature verification.`
          );
          continue;
        }

        signatureChecks++;

        const { integrity, ...eventWithoutIntegrity } = event;
        const keyId = integrity.key_id as string;
        const sig = verifyEvidenceSignature(
          eventWithoutIntegrity as Record<string, unknown>,
          {
            ...integrity,
            key_id: keyId,
          },
          {
            keyId,
            algorithm: 'EdDSA',
            publicKey,
          }
        );

        if (!sig.valid) {
          signatureFailures++;
          errors.push(
            `${event.trace_id}/${event.event_id} signature error: ${sig.error ?? 'verification failed'}`
          );
        }
      }
    }

    verifiedBundles++;
    verifiedEvents += validatedEvents.length;
  }

  if (publicKey && signatureChecks === 0) {
    warnings.push('No signatures were checked (no matching events for provided --verify-key-id).');
  }

  return {
    valid: errors.length === 0,
    verifiedBundles,
    verifiedEvents,
    signatureChecks,
    signatureFailures,
    errors,
    warnings,
  };
}

function normalizeBundleEvents(bundle: any): any[] {
  if (bundle?.events && Array.isArray(bundle.events)) {
    return bundle.events;
  }
  if (Array.isArray(bundle)) {
    return bundle;
  }
  if (bundle && typeof bundle === 'object') {
    return [bundle];
  }
  return [];
}
