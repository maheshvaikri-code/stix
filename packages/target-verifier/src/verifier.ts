/**
 * STIX Target Verifier
 * Core verification logic for proof tokens
 *
 * @module @stix/target-verifier
 */

import {
  verifyProofToken,
  parseProofTokenUnsafe,
  loadPublicKey,
  isoTimestamp,
  type Logger,
  type Obligation,
  type RiskTier,
  type DecisionKind,
  type VerificationKey,
} from '@stix/shared';

import type {
  VerifyRequest,
  VerifyResult,
  VerifierConfig,
  TokenClaims,
  VerificationError,
  VerificationErrorCode,
  PublicKeyConfig,
  VerificationAuditEvent,
  AuditLogger,
} from './types.js';

// =============================================================================
// DEFAULT CONFIGURATION
// =============================================================================

const DEFAULT_CONFIG: Required<Omit<VerifierConfig, 'publicKeys'>> = {
  expectedIssuer: 'stix-enforcer',
  clockSkew: 30, // 30 seconds
  defaultMaxTokenAge: 300, // 5 minutes
  requireActionMatch: true,
  requireResourceMatch: false,
  allowedAlgorithms: ['EdDSA', 'ES256'],
  enableCache: false,
  cacheTtl: 60,
};

// =============================================================================
// VERIFIER CLASS
// =============================================================================

/**
 * Target Verifier - Validates proof tokens before executing protected actions
 */
export class TargetVerifier {
  private readonly config: Required<VerifierConfig>;
  private readonly logger: Logger;
  private readonly auditLogger?: AuditLogger;
  private readonly keyMap: Map<string, PublicKeyConfig>;
  private readonly cache: Map<string, { result: VerifyResult; expiresAt: number }>;

  constructor(
    config: VerifierConfig,
    logger: Logger,
    auditLogger?: AuditLogger
  ) {
    this.config = { ...DEFAULT_CONFIG, ...config } as Required<VerifierConfig>;
    this.logger = logger;
    this.auditLogger = auditLogger;
    this.keyMap = new Map();
    this.cache = new Map();

    // Index public keys by ID
    for (const key of config.publicKeys) {
      this.keyMap.set(key.keyId, key);
    }

    this.logger.debug('TargetVerifier initialized', {
      keyCount: this.keyMap.size,
      cacheEnabled: this.config.enableCache,
    });
  }

  // ===========================================================================
  // MAIN VERIFICATION
  // ===========================================================================

  /**
   * Verify a proof token
   */
  async verify(request: VerifyRequest): Promise<VerifyResult> {
    const startTime = Date.now();

    try {
      // Check cache first
      if (this.config.enableCache) {
        const cached = this.getFromCache(request.token);
        if (cached) {
          this.logger.debug('Cache hit for token verification');
          return cached;
        }
      }

      // Step 1: Parse token (unsafe - just to extract header)
      const parsed = this.parseToken(request.token);
      if (!parsed.valid) {
        return this.failResult(parsed.errors || []);
      }

      // Step 2: Find the right public key
      const keyConfig = this.findKey(parsed.claims!);
      if (!keyConfig) {
        return this.failResult([{
          code: 'KEY_NOT_FOUND',
          message: 'No matching public key found for token',
        }]);
      }

      // Step 3: Verify signature
      const signatureValid = await this.verifySignature(
        request.token,
        keyConfig
      );
      if (!signatureValid.valid) {
        return this.failResult(signatureValid.errors || []);
      }

      const claims = parsed.claims!;

      // Step 4: Check expiration
      const expirationValid = this.checkExpiration(
        claims,
        request.strictExpiration,
        request.maxTokenAge
      );
      if (!expirationValid.valid) {
        return this.failResult(expirationValid.errors || []);
      }

      // Step 5: Check issuer
      if (this.config.expectedIssuer && claims.iss !== this.config.expectedIssuer) {
        return this.failResult([{
          code: 'CLAIMS_INVALID',
          message: `Invalid issuer: expected ${this.config.expectedIssuer}, got ${claims.iss}`,
        }]);
      }

      // Step 6: Check decision
      if (claims.decision === 'DENY') {
        return this.failResult([{
          code: 'DECISION_DENIED',
          message: `Action denied by policy: ${claims.reason_code}`,
          details: { reason_code: claims.reason_code, policy_id: claims.policy_id },
        }]);
      }

      if (claims.decision === 'QUARANTINE') {
        return this.failResult([{
          code: 'DECISION_QUARANTINE',
          message: `Action quarantined: ${claims.reason_code}`,
          details: { reason_code: claims.reason_code, policy_id: claims.policy_id },
        }]);
      }

      // Step 7: Check action match
      if (this.config.requireActionMatch && request.expectedAction) {
        const actionMatch = this.matchAction(claims.action, request.expectedAction);
        if (!actionMatch) {
          return this.failResult([{
            code: 'ACTION_MISMATCH',
            message: `Token action '${claims.action}' does not match expected '${request.expectedAction}'`,
          }]);
        }
      }

      // Step 8: Check resource match
      if (this.config.requireResourceMatch) {
        const resourceMatch = this.matchResource(
          claims,
          request.expectedResourceType,
          request.expectedResourceId
        );
        if (!resourceMatch) {
          return this.failResult([{
            code: 'RESOURCE_MISMATCH',
            message: 'Token resource does not match expected resource',
            details: {
              tokenResource: { type: claims.resource_type, id: claims.resource_id },
              expectedResource: {
                type: request.expectedResourceType,
                id: request.expectedResourceId,
              },
            },
          }]);
        }
      }

      // Step 9: Parse obligations
      const obligations = this.parseObligations(claims.obligations);

      // Build success result
      const result: VerifyResult = {
        valid: true,
        decision: claims.decision as DecisionKind,
        traceId: claims.sub,
        policyId: claims.policy_id,
        policyVersion: claims.policy_version,
        reasonCode: claims.reason_code,
        obligations,
        riskTier: claims.risk_tier as RiskTier | undefined,
        expiresAt: new Date(claims.exp * 1000).toISOString(),
        issuedAt: new Date(claims.iat * 1000).toISOString(),
        claims,
      };

      // Cache the result
      if (this.config.enableCache) {
        this.addToCache(request.token, result, claims.exp);
      }

      // Audit log
      const durationMs = Date.now() - startTime;
      this.logAudit({
        timestamp: isoTimestamp(),
        type: 'VERIFICATION_SUCCESS',
        traceId: claims.sub,
        tokenJti: claims.jti,
        action: claims.action,
        resource: { type: claims.resource_type, id: claims.resource_id },
        decision: claims.decision as DecisionKind,
        durationMs,
      });

      return result;
    } catch (error) {
      const err = error as Error;
      this.logger.error('Token verification failed', {}, err);

      this.logAudit({
        timestamp: isoTimestamp(),
        type: 'VERIFICATION_FAILURE',
        action: request.expectedAction,
        resource: {
          type: request.expectedResourceType || 'unknown',
          id: request.expectedResourceId,
        },
        errors: [{
          code: 'INTERNAL_ERROR',
          message: err.message,
        }],
        durationMs: Date.now() - startTime,
      });

      return this.failResult([{
        code: 'INTERNAL_ERROR',
        message: `Verification error: ${err.message}`,
      }]);
    }
  }

  /**
   * Verify token from HTTP headers
   */
  async verifyFromHeaders(
    headers: Record<string, string | string[] | undefined>,
    expectedAction: string,
    expectedResourceType?: string,
    expectedResourceId?: string
  ): Promise<VerifyResult> {
    // Check standard STIX token header
    const tokenHeaders = ['x-stix-token', 'stix-token', 'authorization'];
    let token: string | undefined;

    for (const header of tokenHeaders) {
      const value = headers[header] || headers[header.toLowerCase()];
      if (value) {
        // Handle array headers
        const headerValue = Array.isArray(value) ? value[0] : value;

        // Handle Bearer prefix
        if (header === 'authorization' && headerValue.startsWith('Bearer ')) {
          token = headerValue.slice(7);
        } else {
          token = headerValue;
        }
        break;
      }
    }

    if (!token) {
      return this.failResult([{
        code: 'TOKEN_MISSING',
        message: 'No STIX proof token found in request headers',
      }]);
    }

    return this.verify({
      token,
      expectedAction,
      expectedResourceType,
      expectedResourceId,
    });
  }

  // ===========================================================================
  // PRIVATE HELPERS
  // ===========================================================================

  private parseToken(token: string): VerifyResult {
    try {
      const parsed = parseProofTokenUnsafe(token);
      const payload = (parsed as { claims?: Record<string, unknown> }).claims;

      if (!parsed.header || !payload) {
        return this.failResult([{
          code: 'TOKEN_MALFORMED',
          message: 'Token is not a valid JWT',
        }]);
      }

      // Map payload to claims
      const claims: TokenClaims = {
        iss: String(payload.iss ?? ''),
        sub: String(payload.sub ?? payload.tid ?? ''),
        iat: Number(payload.iat ?? 0),
        exp: Number(payload.exp ?? 0),
        nbf: typeof payload.nbf === 'number' ? payload.nbf : undefined,
        jti: typeof payload.jti === 'string' ? payload.jti : undefined,
        decision: (payload.decision as DecisionKind | undefined) ?? 'ALLOW',
        reason_code: String(payload.reason_code ?? 'POLICY_ALLOW'),
        policy_id: String(payload.policy_id ?? 'unknown'),
        policy_version: String(payload.policy_version ?? '1.0.0'),
        policy_hash: String(payload.policy_hash ?? payload.pol ?? ''),
        pack_hash: String(payload.pack_hash ?? ''),
        actor_id: String(payload.actor_id ?? payload.sub ?? ''),
        actor_type: String(payload.actor_type ?? 'UNKNOWN'),
        action: String(payload.action ?? payload.act ?? ''),
        resource_type: String(payload.resource_type ?? payload.res ?? ''),
        resource_id: typeof payload.resource_id === 'string' ? payload.resource_id : undefined,
        risk_tier: payload.risk_tier as RiskTier | undefined,
        obligations: typeof payload.obligations === 'string' ? payload.obligations : undefined,
        evidence_hash: typeof payload.evidence_hash === 'string' ? payload.evidence_hash : undefined,
        request_hash: typeof payload.request_hash === 'string' ? payload.request_hash : undefined,
      };

      return { valid: true, claims };
    } catch (error) {
      return this.failResult([{
        code: 'TOKEN_MALFORMED',
        message: `Failed to parse token: ${(error as Error).message}`,
      }]);
    }
  }

  private findKey(claims: TokenClaims): PublicKeyConfig | undefined {
    // Try to find key by policy_id or use first key
    // In production, you'd use a key ID from the token header
    if (this.keyMap.size === 0) {
      return undefined;
    }

    // Return first available key for now
    // Real implementation would use kid from JWT header
    return this.keyMap.values().next().value;
  }

  private async verifySignature(
    token: string,
    keyConfig: PublicKeyConfig
  ): Promise<{ valid: boolean; errors?: VerificationError[] }> {
    try {
      if (!keyConfig.pem) {
        return {
          valid: false,
          errors: [{
            code: 'KEY_NOT_FOUND',
            message: 'PEM public key is required for verification',
          }],
        };
      }

      const verificationKey: VerificationKey = {
        keyId: keyConfig.keyId,
        algorithm: keyConfig.algorithm,
        publicKey: loadPublicKey(keyConfig.pem),
      };

      const result = verifyProofToken(token, (keyId: string) => {
        if (keyId !== keyConfig.keyId) {
          return undefined;
        }
        return verificationKey;
      });

      if (!result.valid) {
        return {
          valid: false,
          errors: [{
            code: 'SIGNATURE_INVALID',
            message: result.error || 'Signature verification failed',
          }],
        };
      }

      return { valid: true };
    } catch (error) {
      return {
        valid: false,
        errors: [{
          code: 'SIGNATURE_INVALID',
          message: `Signature verification error: ${(error as Error).message}`,
        }],
      };
    }
  }

  private checkExpiration(
    claims: TokenClaims,
    strict?: boolean,
    maxAge?: number
  ): { valid: boolean; errors?: VerificationError[] } {
    const now = Math.floor(Date.now() / 1000);
    const clockSkew = strict ? 0 : this.config.clockSkew;

    // Check expiration
    if (claims.exp < now - clockSkew) {
      return {
        valid: false,
        errors: [{
          code: 'TOKEN_EXPIRED',
          message: `Token expired at ${new Date(claims.exp * 1000).toISOString()}`,
        }],
      };
    }

    // Check not before
    if (claims.nbf && claims.nbf > now + clockSkew) {
      return {
        valid: false,
        errors: [{
          code: 'TOKEN_NOT_YET_VALID',
          message: `Token not valid until ${new Date(claims.nbf * 1000).toISOString()}`,
        }],
      };
    }

    // Check max age
    const effectiveMaxAge = maxAge || this.config.defaultMaxTokenAge;
    const tokenAge = now - claims.iat;
    if (tokenAge > effectiveMaxAge) {
      return {
        valid: false,
        errors: [{
          code: 'TOKEN_EXPIRED',
          message: `Token too old: ${tokenAge}s exceeds max age of ${effectiveMaxAge}s`,
        }],
      };
    }

    return { valid: true };
  }

  private matchAction(tokenAction: string, expectedAction: string): boolean {
    // Exact match
    if (tokenAction === expectedAction) {
      return true;
    }

    // Wildcard match (e.g., "read_*" matches "read_file")
    if (tokenAction.endsWith('_*')) {
      const prefix = tokenAction.slice(0, -1); // Remove '*'
      return expectedAction.startsWith(prefix);
    }

    return false;
  }

  private matchResource(
    claims: TokenClaims,
    expectedType?: string,
    expectedId?: string
  ): boolean {
    if (expectedType && claims.resource_type !== expectedType) {
      return false;
    }

    if (expectedId && claims.resource_id !== expectedId) {
      return false;
    }

    return true;
  }

  private parseObligations(obligationsJson?: string): Obligation[] {
    if (!obligationsJson) {
      return [];
    }

    try {
      return JSON.parse(obligationsJson);
    } catch {
      return [];
    }
  }

  private failResult(errors: VerificationError[]): VerifyResult {
    return { valid: false, errors };
  }

  private getFromCache(token: string): VerifyResult | undefined {
    const cached = this.cache.get(token);
    if (!cached) {
      return undefined;
    }

    if (Date.now() > cached.expiresAt) {
      this.cache.delete(token);
      return undefined;
    }

    return cached.result;
  }

  private addToCache(token: string, result: VerifyResult, tokenExp: number): void {
    // Cache expires at the earlier of token expiration or cache TTL
    const cacheTtlMs = this.config.cacheTtl * 1000;
    const tokenExpMs = tokenExp * 1000;
    const expiresAt = Math.min(tokenExpMs, Date.now() + cacheTtlMs);

    this.cache.set(token, { result, expiresAt });

    // Clean up old entries periodically
    if (this.cache.size > 1000) {
      const now = Date.now();
      for (const [key, value] of this.cache) {
        if (now > value.expiresAt) {
          this.cache.delete(key);
        }
      }
    }
  }

  private logAudit(event: VerificationAuditEvent): void {
    if (this.auditLogger) {
      this.auditLogger.log(event);
    }

    // Also log to standard logger
    if (event.type === 'VERIFICATION_SUCCESS') {
      this.logger.debug('Token verification succeeded', {
        trace_id: event.traceId,
        action: event.action,
        decision: event.decision,
        duration_ms: event.durationMs,
      });
    } else if (event.type === 'VERIFICATION_FAILURE') {
      this.logger.warn('Token verification failed', {
        action: event.action,
        errors: event.errors?.map(e => e.message),
        duration_ms: event.durationMs,
      });
    }
  }
}

// =============================================================================
// FACTORY FUNCTION
// =============================================================================

/**
 * Create a new TargetVerifier instance
 */
export function createVerifier(
  config: VerifierConfig,
  logger: Logger,
  auditLogger?: AuditLogger
): TargetVerifier {
  return new TargetVerifier(config, logger, auditLogger);
}
