/**
 * STIX Target HTTP Configuration
 *
 * @module @stix/target-http
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

  http: z.object({
    timeout: z.number(),
    maxRedirects: z.number(),
    retries: z.number(),
    allowedHosts: z.array(z.string()).optional(),
    blockedHosts: z.array(z.string()).optional(),
    allowPrivateNetworks: z.boolean(),
    maxResponseSize: z.number(),
    userAgent: z.string(),
  }),

  rateLimiting: z.object({
    enabled: z.boolean(),
    maxRequests: z.number(),
    windowMs: z.number(),
  }),

  audit: z.object({
    enabled: z.boolean(),
    logLevel: z.enum(['debug', 'info', 'warn', 'error']),
    logRequestBody: z.boolean(),
    logResponseBody: z.boolean(),
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
      name: getEnv('SERVICE_NAME', 'stix-target-http'),
      version: getEnv('SERVICE_VERSION', '0.1.11'),
      env: getEnv('NODE_ENV', 'dev') as Config['service']['env'],
      port: getEnvNumber('PORT', 3081),
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

    http: {
      timeout: getEnvNumber('HTTP_TIMEOUT', 30000),
      maxRedirects: getEnvNumber('HTTP_MAX_REDIRECTS', 5),
      retries: getEnvNumber('HTTP_RETRIES', 3),
      allowedHosts: getEnv('HTTP_ALLOWED_HOSTS', '').split(',').filter(Boolean) || undefined,
      blockedHosts: getEnv('HTTP_BLOCKED_HOSTS', '').split(',').filter(Boolean) || undefined,
      allowPrivateNetworks: getEnvBool('HTTP_ALLOW_PRIVATE_NETWORKS', false),
      maxResponseSize: getEnvNumber('HTTP_MAX_RESPONSE_SIZE', 10 * 1024 * 1024), // 10MB
      userAgent: getEnv('HTTP_USER_AGENT', 'STIX-Target-HTTP/1.0'),
    },

    rateLimiting: {
      enabled: getEnvBool('RATE_LIMIT_ENABLED', true),
      maxRequests: getEnvNumber('RATE_LIMIT_MAX', 100),
      windowMs: getEnvNumber('RATE_LIMIT_WINDOW_MS', 60000),
    },

    audit: {
      enabled: getEnvBool('AUDIT_ENABLED', true),
      logLevel: getEnv('AUDIT_LOG_LEVEL', 'info') as Config['audit']['logLevel'],
      logRequestBody: getEnvBool('AUDIT_LOG_REQUEST_BODY', false),
      logResponseBody: getEnvBool('AUDIT_LOG_RESPONSE_BODY', false),
    },
  };

  const result = ConfigSchema.safeParse(config);
  if (!result.success) {
    console.error('Invalid configuration:', result.error.format());
    throw new Error('Invalid configuration');
  }

  return result.data;
}
