/**
 * STIX Target Verifier SDK
 * Verify proof tokens before executing protected actions
 *
 * @module @stix/target-verifier
 * @version 0.1.16
 *
 * @example
 * ```typescript
 * import { createVerifier, createFastifyVerifier } from '@stix/target-verifier';
 *
 * // Create verifier
 * const verifier = createVerifier({
 *   publicKeys: [{ keyId: 'key-1', algorithm: 'EdDSA', pem: '...' }],
 * }, logger);
 *
 * // Manual verification
 * const result = await verifier.verify({
 *   token: 'eyJ...',
 *   expectedAction: 'send_email',
 *   expectedResourceType: 'email',
 * });
 *
 * if (result.valid) {
 *   console.log('Authorization valid:', result.traceId);
 * }
 *
 * // Fastify middleware
 * const stixVerify = createFastifyVerifier(verifier);
 *
 * fastify.post('/send-email', {
 *   preHandler: stixVerify({ action: 'send_email', resourceType: 'email' }),
 * }, async (request, reply) => {
 *   const { claims, obligations } = request.stix;
 *   // Execute protected action
 * });
 * ```
 */

// =============================================================================
// TYPE EXPORTS
// =============================================================================

export type {
  // Verification
  VerifyRequest,
  VerifyResult,
  VerificationError,
  VerificationErrorCode,
  TokenClaims,

  // Configuration
  VerifierConfig,
  PublicKeyConfig,

  // Protection
  ProtectOptions,
  ProtectedContext,

  // Audit
  VerificationAuditEvent,
  AuditLogger,
} from './types.js';

// =============================================================================
// CLASS EXPORTS
// =============================================================================

export { TargetVerifier } from './verifier.js';

// =============================================================================
// FUNCTION EXPORTS
// =============================================================================

export { createVerifier } from './verifier.js';

export {
  createFastifyVerifier,
  createExpressVerifier,
  protect,
  withStixVerification,
  StixVerificationError,
} from './middleware.js';

// =============================================================================
// VERSION
// =============================================================================

export const VERSION = '0.1.16';
export const PACKAGE_NAME = '@stix/target-verifier';
