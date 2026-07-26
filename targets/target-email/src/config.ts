/**
 * STIX Target Email Configuration
 *
 * @module @stix/target-email
 */

import { z } from 'zod';
import { getEnv, getEnvNumber, getEnvBool } from '@stix/shared';

// =============================================================================
// CONFIGURATION SCHEMA
// =============================================================================

const ConfigSchema = z.object({
  service: z.object({
    name: z.string(),
    version: z.string(),
    env: z.enum(['dev', 'test', 'staging', 'prod']),
    port: z.number(),
    host: z.string(),
  }),

  stix: z.object({
    enforcerUrl: z.string(),
    publicKeyPem: z.string().optional(),
    publicKeyPath: z.string().optional(),
    keyId: z.string(),
    algorithm: z.enum(['EdDSA', 'ES256']),
    expectedIssuer: z.string(),
    requireActionMatch: z.boolean(),
    requireResourceMatch: z.boolean(),
    maxTokenAge: z.number(),
  }),

  smtp: z.object({
    host: z.string(),
    port: z.number(),
    secure: z.boolean(),
    auth: z.object({
      user: z.string(),
      pass: z.string(),
    }).optional(),
    from: z.string(),
  }),

  rateLimiting: z.object({
    enabled: z.boolean(),
    maxRequests: z.number(),
    windowMs: z.number(),
  }),

  audit: z.object({
    enabled: z.boolean(),
    logLevel: z.enum(['debug', 'info', 'warn', 'error']),
  }),
});

export type Config = z.infer<typeof ConfigSchema>;

// =============================================================================
// LOAD CONFIGURATION
// =============================================================================

/**
 * Load configuration from environment variables
 */
export function loadConfig(): Config {
  const config: Config = {
    service: {
      name: getEnv('SERVICE_NAME', 'stix-target-email'),
      version: getEnv('SERVICE_VERSION', '0.1.11'),
      env: getEnv('NODE_ENV', 'dev') as Config['service']['env'],
      port: getEnvNumber('PORT', 3080),
      host: getEnv('HOST', '0.0.0.0'),
    },

    stix: {
      enforcerUrl: getEnv('STIX_ENFORCER_URL', 'http://localhost:3001'),
      publicKeyPem: getEnv('STIX_PUBLIC_KEY', ''),
      publicKeyPath: getEnv('STIX_PUBLIC_KEY_PATH', ''),
      keyId: getEnv('STIX_KEY_ID', 'stix-enforcer-key-1'),
      algorithm: getEnv('STIX_ALGORITHM', 'EdDSA') as 'EdDSA' | 'ES256',
      expectedIssuer: getEnv('STIX_EXPECTED_ISSUER', 'stix-enforcer'),
      requireActionMatch: getEnvBool('STIX_REQUIRE_ACTION_MATCH', true),
      requireResourceMatch: getEnvBool('STIX_REQUIRE_RESOURCE_MATCH', false),
      maxTokenAge: getEnvNumber('STIX_MAX_TOKEN_AGE', 300),
    },

    smtp: {
      host: getEnv('SMTP_HOST', 'localhost'),
      port: getEnvNumber('SMTP_PORT', 1025),
      secure: getEnvBool('SMTP_SECURE', false),
      auth: getEnv('SMTP_USER', '')
        ? {
            user: getEnv('SMTP_USER', ''),
            pass: getEnv('SMTP_PASS', ''),
          }
        : undefined,
      from: getEnv('SMTP_FROM', 'stix@localhost'),
    },

    rateLimiting: {
      enabled: getEnvBool('RATE_LIMIT_ENABLED', true),
      maxRequests: getEnvNumber('RATE_LIMIT_MAX', 100),
      windowMs: getEnvNumber('RATE_LIMIT_WINDOW_MS', 60000),
    },

    audit: {
      enabled: getEnvBool('AUDIT_ENABLED', true),
      logLevel: getEnv('AUDIT_LOG_LEVEL', 'info') as Config['audit']['logLevel'],
    },
  };

  // Validate configuration
  const result = ConfigSchema.safeParse(config);
  if (!result.success) {
    console.error('Invalid configuration:', result.error.format());
    throw new Error('Invalid configuration');
  }

  return result.data;
}
