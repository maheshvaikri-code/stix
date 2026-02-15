/**
 * STIX Target Verifier SDK
 * Proof token verification for protected services
 * 
 * Enables protected targets (databases, APIs, file systems) to:
 * - Verify STIX proof tokens
 * - Enforce authorization requirements
 * - Reject requests without valid tokens
 * 
 * @module @stix/target-verifier
 */

import {
  type ProofTokenClaims,
  type ProofTokenHeader,
  type VerificationKey,
  type KeyStore,
  type Logger,
  verifyProofToken,
  parseProofTokenUnsafe,
  createLoggerFromEnv,
  InMemoryKeyStore,
  loadPublicKey,
  HEADERS,
  MissingStixTokenError,
  InvalidTokenError,
  TokenExpiredError,
} from '@stix/shared';

// =============================================================================
// CONFIGURATION
// =============================================================================

export interface VerifierConfig {
  /** Key store for verification keys */
  keyStore?: KeyStore;
  /** Static verification keys (if not using key store) */
  publicKeys?: Array<{
    keyId: string;
    algorithm: 'Ed25519' | 'ES256';
    publicKeyPem: string;
  }>;
  /** URL to fetch keys from (JWKS-style) */
  keysUrl?: string;
  /** Whether token is required (default: true) */
  required?: boolean;
  /** Allowed clock skew in seconds (default: 60) */
  clockSkewSeconds?: number;
  /** Resource type to match (optional) */
  resourceType?: string;
  /** Allowed actions (optional) */
  allowedActions?: string[];
  /** Custom logger */
  logger?: Logger;
  /** Enable debug logging */
  debug?: boolean;
  /** Enforce strict verification posture (default true in prod) */
  strictMode?: boolean;
  /** Allow skip-path bypass hooks while strict mode is enabled */
  allowPathBypass?: boolean;
}

// =============================================================================
// VERIFICATION RESULT
// =============================================================================

export interface VerificationResult {
  /** Whether the token is valid */
  valid: boolean;
  /** Token claims (if valid) */
  claims?: ProofTokenClaims;
  /** Token header (if valid) */
  header?: ProofTokenHeader;
  /** Error message (if invalid) */
  error?: string;
  /** Error code */
  errorCode?: string;
}

export interface RequestContext {
  /** The action being performed */
  action?: string;
  /** The resource being accessed */
  resource?: {
    type?: string;
    id?: string;
    classification?: string[];
  };
  /** Additional context for validation */
  [key: string]: unknown;
}

// =============================================================================
// STIX VERIFIER
// =============================================================================

export class StixVerifier {
  private readonly config: Required<Omit<VerifierConfig, 'publicKeys' | 'keysUrl'>> & 
    Pick<VerifierConfig, 'publicKeys' | 'keysUrl' | 'resourceType' | 'allowedActions'>;
  private readonly logger: Logger;
  private keyStore: KeyStore;
  private keysInitialized: boolean = false;

  constructor(config: VerifierConfig = {}) {
    this.config = {
      keyStore: config.keyStore ?? new InMemoryKeyStore(),
      publicKeys: config.publicKeys,
      keysUrl: config.keysUrl,
      required: config.required ?? true,
      clockSkewSeconds: config.clockSkewSeconds ?? 60,
      resourceType: config.resourceType,
      allowedActions: config.allowedActions,
      logger: config.logger ?? createLoggerFromEnv('stix-target-verifier'),
      debug: config.debug ?? false,
      strictMode: config.strictMode ?? (process.env.NODE_ENV === 'production'),
      allowPathBypass: config.allowPathBypass ?? false,
    };

    this.logger = this.config.logger;
    this.keyStore = this.config.keyStore;

    // Initialize with static keys if provided
    if (config.publicKeys) {
      this.initializeStaticKeys(config.publicKeys);
    }
  }

  /**
   * Initialize static keys
   */
  private initializeStaticKeys(
    keys: Array<{
      keyId: string;
      algorithm: 'Ed25519' | 'ES256';
      publicKeyPem: string;
    }>
  ): void {
    if (this.keyStore instanceof InMemoryKeyStore) {
      for (const key of keys) {
        const publicKeyObj = loadPublicKey(key.publicKeyPem);
        // We need to use addKeyPair but only have public key
        // For now, we'll store verification keys directly
        (this.keyStore as any).verificationKeys = (this.keyStore as any).verificationKeys ?? new Map();
        (this.keyStore as any).verificationKeys.set(key.keyId, {
          keyId: key.keyId,
          algorithm: key.algorithm,
          publicKey: publicKeyObj,
        });
      }
    }
    this.keysInitialized = true;
    this.logger.debug('Initialized static verification keys', { count: keys.length });
  }

  /**
   * Fetch keys from remote URL
   */
  async fetchKeys(): Promise<void> {
    if (!this.config.keysUrl) {
      if (this.config.strictMode) {
        throw new Error('Strict mode requires keysUrl or static publicKeys configuration.');
      }
      this.logger.debug('No keys URL configured, skipping key fetch');
      return;
    }

    try {
      const response = await fetch(this.config.keysUrl);
      if (!response.ok) {
        throw new Error(`Failed to fetch keys: ${response.statusText}`);
      }

      const data = await response.json() as {
        keys: Array<{
          kid: string;
          alg: 'EdDSA' | 'ES256';
          kty: string;
          x?: string;
          crv?: string;
        }>;
      };

      // Process JWKS-style response
      // This would need to convert JWK to PEM format
      this.logger.info('Fetched verification keys', { count: data.keys.length });
      this.keysInitialized = true;
    } catch (error) {
      this.logger.error('Failed to fetch keys', {}, error as Error);
      throw error;
    }
  }

  /**
   * Verify a STIX proof token
   */
  verify(token: string, context?: RequestContext): VerificationResult {
    this.logger.debug('Verifying token', {
      context_action: context?.action,
      context_resource: context?.resource?.type,
    });

    // Get verification key by key ID
    const getKey = (keyId: string): VerificationKey | undefined => {
      // Access verification keys from key store
      const keys = (this.keyStore as any).verificationKeys;
      if (keys instanceof Map) {
        return keys.get(keyId);
      }
      return undefined;
    };

    if (this.config.strictMode && !this.hasVerificationKeys()) {
      return {
        valid: false,
        error: 'No verification keys configured',
        errorCode: 'KEYS_NOT_CONFIGURED',
      };
    }

    const result = verifyProofToken(token, getKey);

    if (!result.valid) {
      this.logger.debug('Token verification failed', { error: result.error });
      return {
        valid: false,
        error: result.error,
        errorCode: this.getErrorCode(result.error ?? ''),
      };
    }

    // Additional validation
    const claims = result.claims!;
    const header = result.header!;

    // Check action if specified
    if (context?.action && claims.act !== context.action) {
      return {
        valid: false,
        error: `Action mismatch: expected ${context.action}, got ${claims.act}`,
        errorCode: 'ACTION_MISMATCH',
      };
    }

    // Check allowed actions
    if (this.config.allowedActions && !this.config.allowedActions.includes(claims.act)) {
      return {
        valid: false,
        error: `Action not allowed: ${claims.act}`,
        errorCode: 'ACTION_NOT_ALLOWED',
      };
    }

    // Check resource type if specified
    if (this.config.resourceType && claims.res !== this.config.resourceType) {
      return {
        valid: false,
        error: `Resource type mismatch: expected ${this.config.resourceType}, got ${claims.res}`,
        errorCode: 'RESOURCE_MISMATCH',
      };
    }

    if (context?.resource?.type && claims.res !== context.resource.type) {
      return {
        valid: false,
        error: `Resource type mismatch: expected ${context.resource.type}, got ${claims.res}`,
        errorCode: 'RESOURCE_MISMATCH',
      };
    }

    // Check classification if specified
    if (context?.resource?.classification && context.resource.classification.length > 0) {
      const requestedClassifications = new Set(context.resource.classification);
      const tokenClassifications = new Set(claims.cls);
      
      for (const cls of requestedClassifications) {
        if (!tokenClassifications.has(cls)) {
          return {
            valid: false,
            error: `Classification not authorized: ${cls}`,
            errorCode: 'CLASSIFICATION_NOT_AUTHORIZED',
          };
        }
      }
    }

    this.logger.debug('Token verified successfully', {
      subject: claims.sub,
      action: claims.act,
      trace_id: claims.tid,
    });

    return {
      valid: true,
      claims,
      header,
    };
  }

  /**
   * Verify token from request headers
   */
  verifyFromHeaders(
    headers: Record<string, string | string[] | undefined>,
    context?: RequestContext
  ): VerificationResult {
    const token = this.extractToken(headers);

    if (!token) {
      if (this.config.required) {
        return {
          valid: false,
          error: 'STIX proof token required',
          errorCode: 'TOKEN_REQUIRED',
        };
      }
      // Not required, return valid with no claims
      return { valid: true };
    }

    return this.verify(token, context);
  }

  /**
   * Extract token from headers
   */
  private extractToken(
    headers: Record<string, string | string[] | undefined>
  ): string | null {
    // Check X-STIX-Proof header
    const stixHeader = headers[HEADERS.STIX_PROOF] || headers[HEADERS.STIX_PROOF.toLowerCase()];
    if (stixHeader) {
      return Array.isArray(stixHeader) ? stixHeader[0] : stixHeader;
    }

    // Check Authorization header with Bearer scheme
    const authHeader = headers['authorization'] || headers['Authorization'];
    if (authHeader) {
      const value = Array.isArray(authHeader) ? authHeader[0] : authHeader;
      if (value.startsWith('Bearer ')) {
        return value.substring(7);
      }
    }

    return null;
  }

  /**
   * Get error code from error message
   */
  private getErrorCode(error: string): string {
    if (error.includes('expired')) return 'TOKEN_EXPIRED';
    if (error.includes('signature')) return 'INVALID_SIGNATURE';
    if (error.includes('not yet valid')) return 'TOKEN_NOT_YET_VALID';
    if (error.includes('Unknown key')) return 'UNKNOWN_KEY';
    if (error.includes('verification keys')) return 'KEYS_NOT_CONFIGURED';
    return 'INVALID_TOKEN';
  }

  isStrictMode(): boolean {
    return this.config.strictMode;
  }

  allowsPathBypass(): boolean {
    return this.config.allowPathBypass;
  }

  private hasVerificationKeys(): boolean {
    const keys = (this.keyStore as any).verificationKeys;
    return keys instanceof Map && keys.size > 0;
  }

  /**
   * Parse token without verification (for inspection)
   */
  parseUnsafe(token: string): {
    header?: ProofTokenHeader;
    claims?: ProofTokenClaims;
    error?: string;
  } {
    return parseProofTokenUnsafe(token);
  }

  /**
   * Get trace ID from token without full verification
   */
  getTraceId(token: string): string | null {
    const parsed = parseProofTokenUnsafe(token);
    return parsed.claims?.tid ?? null;
  }
}

// =============================================================================
// MIDDLEWARE FACTORIES
// =============================================================================

/**
 * Express/Connect-style middleware
 */
export interface VerifierMiddlewareOptions extends VerifierConfig {
  /** Skip verification for these paths */
  skipPaths?: string[];
  /** Error handler */
  onError?: (error: VerificationResult, req: any, res: any) => void;
}

export function createExpressMiddleware(options: VerifierMiddlewareOptions = {}) {
  const verifier = new StixVerifier(options);
  const skipPaths = new Set(options.skipPaths ?? []);

  if (verifier.isStrictMode() && skipPaths.size > 0 && !verifier.allowsPathBypass()) {
    throw new Error('Strict mode forbids skipPaths unless allowPathBypass=true.');
  }

  return async (req: any, res: any, next: any) => {
    // Skip verification for certain paths
    if (skipPaths.has(req.path)) {
      return next();
    }

    const result = verifier.verifyFromHeaders(req.headers, {
      action: req.method,
      resource: {
        type: req.baseUrl || req.path,
      },
    });

    if (!result.valid) {
      if (options.onError) {
        return options.onError(result, req, res);
      }

      return res.status(401).json({
        error: {
          code: result.errorCode,
          message: result.error,
        },
      });
    }

    // Attach claims to request
    req.stix = {
      claims: result.claims,
      header: result.header,
      traceId: result.claims?.tid,
    };

    next();
  };
}

/**
 * Fastify plugin
 */
export function createFastifyPlugin(options: VerifierMiddlewareOptions = {}) {
  const verifier = new StixVerifier(options);
  const skipPaths = new Set(options.skipPaths ?? []);

  if (verifier.isStrictMode() && skipPaths.size > 0 && !verifier.allowsPathBypass()) {
    throw new Error('Strict mode forbids skipPaths unless allowPathBypass=true.');
  }

  return async (fastify: any) => {
    fastify.addHook('onRequest', async (request: any, reply: any) => {
      // Skip verification for certain paths
      if (skipPaths.has(request.url)) {
        return;
      }

      const result = verifier.verifyFromHeaders(request.headers, {
        action: request.method,
        resource: {
          type: request.url,
        },
      });

      if (!result.valid) {
        if (options.onError) {
          return options.onError(result, request, reply);
        }

        return reply.status(401).send({
          error: {
            code: result.errorCode,
            message: result.error,
          },
        });
      }

      // Attach claims to request
      request.stix = {
        claims: result.claims,
        header: result.header,
        traceId: result.claims?.tid,
      };
    });

    // Decorate request
    fastify.decorateRequest('stix', null);
  };
}

// =============================================================================
// DECORATOR FOR METHODS
// =============================================================================

/**
 * Decorator that requires STIX token verification
 */
export function requireStixToken(
  resourceType?: string,
  allowedActions?: string[]
) {
  return function (
    target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      const verifier: StixVerifier = (this as any).stixVerifier;
      if (!verifier) {
        throw new Error('StixVerifier not found on class instance');
      }

      // Assume first argument has headers
      const requestArg = args[0];
      const headers = requestArg?.headers ?? {};

      const result = verifier.verifyFromHeaders(headers, {
        resource: resourceType ? { type: resourceType } : undefined,
      });

      if (!result.valid) {
        if (result.errorCode === 'TOKEN_REQUIRED') {
          throw new MissingStixTokenError();
        }
        if (result.errorCode === 'TOKEN_EXPIRED') {
          throw new TokenExpiredError();
        }
        throw new InvalidTokenError(result.error);
      }

      // Call original method with stix claims injected
      return originalMethod.apply(this, [...args, result.claims]);
    };

    return descriptor;
  };
}

// =============================================================================
// EXPORTS
// =============================================================================

export {
  // Re-export types from shared
  type ProofTokenClaims,
  type ProofTokenHeader,
  type VerificationKey,
  type KeyStore,
  
  // Re-export utilities
  InMemoryKeyStore,
  loadPublicKey,
  
  // Re-export errors
  MissingStixTokenError,
  InvalidTokenError,
  TokenExpiredError,
  
  // Re-export constants
  HEADERS,
} from '@stix/shared';
