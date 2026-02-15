/**
 * STIX Target Verifier Middleware
 * Express/Fastify middleware for protecting routes
 *
 * @module @stix/target-verifier
 */

import type { Logger } from '@stix/shared';
import { TargetVerifier } from './verifier.js';
import type {
  VerifyResult,
  ProtectOptions,
  ProtectedContext,
  TokenClaims,
} from './types.js';

// =============================================================================
// FASTIFY MIDDLEWARE
// =============================================================================

/**
 * Fastify preHandler hook for STIX verification
 */
export function createFastifyVerifier(verifier: TargetVerifier) {
  return function stixVerifyHook(options: ProtectOptions) {
    return async (
      request: {
        headers: Record<string, string | string[] | undefined>;
        stix?: ProtectedContext;
      },
      reply: {
        code: (code: number) => { send: (body: unknown) => void };
      }
    ): Promise<void> => {
      const result = await verifier.verifyFromHeaders(
        request.headers,
        options.action,
        options.resourceType,
        options.resourceId
      );

      if (!result.valid) {
        reply.code(403).send({
          error: 'STIX_VERIFICATION_FAILED',
          message: 'Authorization verification failed',
          errors: result.errors,
        });
        return;
      }

      // Custom validation
      if (options.validate && result.claims) {
        const customValid = await options.validate(result.claims);
        if (!customValid) {
          reply.code(403).send({
            error: 'STIX_CUSTOM_VALIDATION_FAILED',
            message: 'Custom validation failed',
          });
          return;
        }
      }

      // Attach context to request
      request.stix = {
        verification: result,
        traceId: result.traceId!,
        claims: result.claims!,
        obligations: result.obligations || [],
        reportOutcome: async (success, details) => {
          // Outcome reporting would be implemented here
          // Could call back to evidence service
        },
      };
    };
  };
}

// =============================================================================
// EXPRESS MIDDLEWARE
// =============================================================================

/**
 * Express middleware for STIX verification
 */
export function createExpressVerifier(verifier: TargetVerifier, logger: Logger) {
  return function stixVerify(options: ProtectOptions) {
    return async (
      req: {
        headers: Record<string, string | string[] | undefined>;
        stix?: ProtectedContext;
      },
      res: {
        status: (code: number) => { json: (body: unknown) => void };
      },
      next: (error?: Error) => void
    ): Promise<void> => {
      try {
        const result = await verifier.verifyFromHeaders(
          req.headers,
          options.action,
          options.resourceType,
          options.resourceId
        );

        if (!result.valid) {
          res.status(403).json({
            error: 'STIX_VERIFICATION_FAILED',
            message: 'Authorization verification failed',
            errors: result.errors,
          });
          return;
        }

        // Custom validation
        if (options.validate && result.claims) {
          const customValid = await options.validate(result.claims);
          if (!customValid) {
            res.status(403).json({
              error: 'STIX_CUSTOM_VALIDATION_FAILED',
              message: 'Custom validation failed',
            });
            return;
          }
        }

        // Attach context to request
        req.stix = {
          verification: result,
          traceId: result.traceId!,
          claims: result.claims!,
          obligations: result.obligations || [],
          reportOutcome: async (success, details) => {
            // Outcome reporting
          },
        };

        next();
      } catch (error) {
        logger.error('STIX verification error', {}, error as Error);
        next(error as Error);
      }
    };
  };
}

// =============================================================================
// DECORATOR PATTERN
// =============================================================================

/**
 * Decorator for protecting async functions
 */
export function protect<TArgs extends unknown[], TResult>(
  verifier: TargetVerifier,
  options: ProtectOptions
) {
  return function decorator(
    _target: unknown,
    _propertyKey: string,
    descriptor: TypedPropertyDescriptor<(...args: TArgs) => Promise<TResult>>
  ): TypedPropertyDescriptor<(...args: TArgs) => Promise<TResult>> {
    const originalMethod = descriptor.value!;

    descriptor.value = async function (this: unknown, ...args: TArgs): Promise<TResult> {
      // Find token in arguments (assumes first arg with headers)
      const headersArg = args.find(
        (arg): arg is { headers: Record<string, string> } =>
          arg !== null &&
          typeof arg === 'object' &&
          'headers' in arg
      );

      if (!headersArg) {
        throw new Error('No headers found in arguments for STIX verification');
      }

      const result = await verifier.verifyFromHeaders(
        headersArg.headers,
        options.action,
        options.resourceType,
        options.resourceId
      );

      if (!result.valid) {
        const error = new Error('STIX verification failed');
        (error as Error & { stixErrors: unknown[] }).stixErrors = result.errors || [];
        throw error;
      }

      return originalMethod.apply(this, args);
    };

    return descriptor;
  };
}

// =============================================================================
// WRAPPER FUNCTION
// =============================================================================

/**
 * Wrap a function with STIX verification
 */
export function withStixVerification<TArgs extends unknown[], TResult>(
  verifier: TargetVerifier,
  options: ProtectOptions,
  fn: (context: ProtectedContext, ...args: TArgs) => Promise<TResult>,
  getToken: (...args: TArgs) => string | undefined
): (...args: TArgs) => Promise<TResult> {
  return async (...args: TArgs): Promise<TResult> => {
    const token = getToken(...args);

    if (!token) {
      throw new StixVerificationError('TOKEN_MISSING', 'No STIX token provided');
    }

    const result = await verifier.verify({
      token,
      expectedAction: options.action,
      expectedResourceType: options.resourceType,
      expectedResourceId: options.resourceId,
    });

    if (!result.valid) {
      throw new StixVerificationError(
        result.errors?.[0]?.code || 'VERIFICATION_FAILED',
        result.errors?.[0]?.message || 'Verification failed',
        result.errors
      );
    }

    const context: ProtectedContext = {
      verification: result,
      traceId: result.traceId!,
      claims: result.claims!,
      obligations: result.obligations || [],
      reportOutcome: async () => {},
    };

    return fn(context, ...args);
  };
}

// =============================================================================
// ERROR CLASS
// =============================================================================

/**
 * STIX Verification Error
 */
export class StixVerificationError extends Error {
  public readonly code: string;
  public readonly errors?: Array<{ code: string; message: string }>;

  constructor(
    code: string,
    message: string,
    errors?: Array<{ code: string; message: string }>
  ) {
    super(message);
    this.name = 'StixVerificationError';
    this.code = code;
    this.errors = errors;
  }
}
