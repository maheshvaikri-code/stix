import { hashCanonical, type Actor } from '@stix/shared';
import type { WorkloadIdentity } from '../config/index.js';

/** Return a stable error when request actor fields do not match the authenticated workload. */
export function validateActorBinding(
  actor: Actor,
  identity: WorkloadIdentity
): string | undefined {
  const checks: Array<[string, unknown, unknown]> = [
    ['actor.id', actor.id, identity.actorId],
    ['actor.type', actor.type, identity.actorType],
    ['actor.tenant', actor.tenant, identity.tenant],
    ['actor.role', actor.role, identity.role],
  ];

  for (const [field, requested, authenticated] of checks) {
    if (requested !== authenticated) {
      return `${field} is not bound to the authenticated workload identity`;
    }
  }

  if (hashCanonical(actor.attributes ?? {}) !== hashCanonical(identity.attributes ?? {})) {
    return 'actor.attributes are not bound to the authenticated workload identity';
  }

  return undefined;
}
