/**
 * STIX Target DB Configuration
 *
 * @module @stix/target-db
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

  database: z.object({
    type: z.enum(['postgres', 'mysql', 'sqlite']),
    host: z.string().optional(),
    port: z.number().optional(),
    database: z.string(),
    user: z.string().optional(),
    password: z.string().optional(),
    ssl: z.boolean().optional(),
    poolMin: z.number(),
    poolMax: z.number(),
    connectionTimeout: z.number(),
    idleTimeout: z.number(),
  }),

  security: z.object({
    allowedTables: z.array(z.string()).optional(),
    blockedTables: z.array(z.string()).optional(),
    allowDdl: z.boolean(),
    allowTruncate: z.boolean(),
    allowDrop: z.boolean(),
    maxRowsPerQuery: z.number(),
    queryTimeout: z.number(),
  }),

  rateLimiting: z.object({
    enabled: z.boolean(),
    maxRequests: z.number(),
    windowMs: z.number(),
  }),

  audit: z.object({
    enabled: z.boolean(),
    logLevel: z.enum(['debug', 'info', 'warn', 'error']),
    logQueries: z.boolean(),
    logResults: z.boolean(),
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
      name: getEnv('SERVICE_NAME', 'stix-target-db'),
      version: getEnv('SERVICE_VERSION', '0.1.9'),
      env: getEnv('NODE_ENV', 'dev') as Config['service']['env'],
      port: getEnvNumber('PORT', 3082),
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
      requireResourceMatch: getEnvBool('STIX_REQUIRE_RESOURCE_MATCH', true),
      maxTokenAge: getEnvNumber('STIX_MAX_TOKEN_AGE', 300),
    },

    database: {
      type: getEnv('DB_TYPE', 'sqlite') as Config['database']['type'],
      host: getEnv('DB_HOST', 'localhost'),
      port: getEnvNumber('DB_PORT', 5432),
      database: getEnv('DB_DATABASE', ':memory:'),
      user: getEnv('DB_USER', ''),
      password: getEnv('DB_PASSWORD', ''),
      ssl: getEnvBool('DB_SSL', false),
      poolMin: getEnvNumber('DB_POOL_MIN', 2),
      poolMax: getEnvNumber('DB_POOL_MAX', 10),
      connectionTimeout: getEnvNumber('DB_CONNECTION_TIMEOUT', 5000),
      idleTimeout: getEnvNumber('DB_IDLE_TIMEOUT', 30000),
    },

    security: {
      allowedTables: getEnv('DB_ALLOWED_TABLES', '').split(',').filter(Boolean) || undefined,
      blockedTables: getEnv('DB_BLOCKED_TABLES', 'pg_catalog,information_schema,mysql,sys').split(',').filter(Boolean),
      allowDdl: getEnvBool('DB_ALLOW_DDL', false),
      allowTruncate: getEnvBool('DB_ALLOW_TRUNCATE', false),
      allowDrop: getEnvBool('DB_ALLOW_DROP', false),
      maxRowsPerQuery: getEnvNumber('DB_MAX_ROWS', 1000),
      queryTimeout: getEnvNumber('DB_QUERY_TIMEOUT', 30000),
    },

    rateLimiting: {
      enabled: getEnvBool('RATE_LIMIT_ENABLED', true),
      maxRequests: getEnvNumber('RATE_LIMIT_MAX', 100),
      windowMs: getEnvNumber('RATE_LIMIT_WINDOW_MS', 60000),
    },

    audit: {
      enabled: getEnvBool('AUDIT_ENABLED', true),
      logLevel: getEnv('AUDIT_LOG_LEVEL', 'info') as Config['audit']['logLevel'],
      logQueries: getEnvBool('AUDIT_LOG_QUERIES', true),
      logResults: getEnvBool('AUDIT_LOG_RESULTS', false),
    },
  };

  const result = ConfigSchema.safeParse(config);
  if (!result.success) {
    console.error('Invalid configuration:', result.error.format());
    throw new Error('Invalid configuration');
  }

  return result.data;
}
