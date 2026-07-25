/**
 * STIX Enforcer Configuration
 * Environment-based configuration with validation
 */

import { z } from 'zod';
import {
  SERVICE_PORTS,
  TIMEOUTS,
  RETRY_CONFIG,
  RATE_LIMITS,
  getEnv,
  getEnvNumber,
  getEnvBool,
} from '@stix/shared';

// =============================================================================
// CONFIGURATION SCHEMA
// =============================================================================

const ConfigSchema = z.object({
  // Service
  service: z.object({
    name: z.string(),
    version: z.string(),
    port: z.number(),
    host: z.string(),
    env: z.enum(['dev', 'test', 'stage', 'prod']),
  }),
  
  // Logging
  logging: z.object({
    level: z.enum(['error', 'warn', 'info', 'http', 'debug', 'trace']),
    pretty: z.boolean(),
  }),
  
  // Authorization
  authorization: z.object({
    defaultFailMode: z.enum(['CLOSED', 'OPEN_LOW_RISK_ONLY', 'OPEN']),
    tokenExpirySeconds: z.number(),
    cacheEnabled: z.boolean(),
    cacheTtlSeconds: z.number(),
  }),
  
  // External services
  services: z.object({
    policyUrl: z.string(),
    evidenceUrl: z.string(),
    approvalsUrl: z.string(),
    serviceAuthToken: z.string().optional(),
    useMockClients: z.boolean(),
  }),

  // Evidence write behavior
  evidence: z.object({
    writeMode: z.enum(['best_effort', 'strict']),
  }),
  
  // Redis
  redis: z.object({
    enabled: z.boolean(),
    url: z.string().optional(),
    host: z.string(),
    port: z.number(),
    password: z.string().optional(),
    db: z.number(),
    keyPrefix: z.string(),
  }),
  
  // Rate limiting
  rateLimiting: z.object({
    enabled: z.boolean(),
    maxRequests: z.number(),
    windowMs: z.number(),
  }),
  
  // Timeouts
  timeouts: z.object({
    serviceRequest: z.number(),
    policyEvaluation: z.number(),
    gracefulShutdown: z.number(),
  }),
  
  // Retry
  retry: z.object({
    maxAttempts: z.number(),
    initialDelayMs: z.number(),
    maxDelayMs: z.number(),
  }),
  
  // Security
  security: z.object({
    signingKeyPath: z.string().optional(),
    signingKeyPem: z.string().optional(),
    signingKeyId: z.string().optional(),
    verificationKeysPath: z.string().optional(),
    apiKeyAuthEnabled: z.boolean(),
    apiKeys: z.array(z.string()),
  }),
});

export type Config = z.infer<typeof ConfigSchema>;

// =============================================================================
// LOAD CONFIGURATION
// =============================================================================

export function loadConfig(): Config {
  const parseCsv = (value: string): string[] =>
    value
      .split(',')
      .map((v) => v.trim())
      .filter((v) => v.length > 0);

  const rawEnv = getEnv('NODE_ENV', 'dev');
  const normalizedEnv = rawEnv.toLowerCase() === 'production' ? 'prod' : rawEnv.toLowerCase();
  const env = normalizedEnv as 'dev' | 'test' | 'stage' | 'prod';
  
  const config: Config = {
    service: {
      name: 'stix-enforcer',
      version: getEnv('SERVICE_VERSION', '0.1.5'),
      port: getEnvNumber('PORT', SERVICE_PORTS.ENFORCER),
      host: getEnv('HOST', '0.0.0.0'),
      env,
    },
    
    logging: {
      level: (getEnv('LOG_LEVEL', env === 'prod' ? 'info' : 'debug')) as Config['logging']['level'],
      pretty: getEnvBool('LOG_PRETTY', env !== 'prod'),
    },
    
    authorization: {
      defaultFailMode: (getEnv('DEFAULT_FAIL_MODE', 'CLOSED')) as Config['authorization']['defaultFailMode'],
      tokenExpirySeconds: getEnvNumber('TOKEN_EXPIRY_SECONDS', 300),
      cacheEnabled: getEnvBool('CACHE_ENABLED', true),
      cacheTtlSeconds: getEnvNumber('CACHE_TTL_SECONDS', 60),
    },
    
    services: {
      policyUrl: getEnv('POLICY_SERVICE_URL', 'http://stix-policy:3002'),
      evidenceUrl: getEnv('EVIDENCE_SERVICE_URL', 'http://stix-evidence:3003'),
      approvalsUrl: getEnv('APPROVALS_SERVICE_URL', 'http://stix-approvals:3004'),
      serviceAuthToken: getEnv('SERVICE_AUTH_TOKEN', ''),
      useMockClients: getEnvBool('USE_MOCK_CLIENTS', env === 'dev' || env === 'test'),
    },

    evidence: {
      writeMode: getEnv('EVIDENCE_WRITE_MODE', env === 'prod' ? 'strict' : 'best_effort') as Config['evidence']['writeMode'],
    },
    
    redis: {
      enabled: getEnvBool('REDIS_ENABLED', true),
      url: getEnv('REDIS_URL', ''),
      host: getEnv('REDIS_HOST', 'localhost'),
      port: getEnvNumber('REDIS_PORT', 6379),
      password: getEnv('REDIS_PASSWORD', ''),
      db: getEnvNumber('REDIS_DB', 0),
      keyPrefix: getEnv('REDIS_KEY_PREFIX', 'stix:'),
    },
    
    rateLimiting: {
      enabled: getEnvBool('RATE_LIMIT_ENABLED', true),
      maxRequests: getEnvNumber('RATE_LIMIT_MAX', RATE_LIMITS.AUTHORIZE_RPS),
      windowMs: getEnvNumber('RATE_LIMIT_WINDOW_MS', RATE_LIMITS.WINDOW_MS),
    },
    
    timeouts: {
      serviceRequest: getEnvNumber('TIMEOUT_SERVICE_REQUEST', TIMEOUTS.SERVICE_REQUEST),
      policyEvaluation: getEnvNumber('TIMEOUT_POLICY_EVALUATION', TIMEOUTS.POLICY_EVALUATION),
      gracefulShutdown: getEnvNumber('TIMEOUT_GRACEFUL_SHUTDOWN', TIMEOUTS.GRACEFUL_SHUTDOWN),
    },
    
    retry: {
      maxAttempts: getEnvNumber('RETRY_MAX_ATTEMPTS', RETRY_CONFIG.MAX_ATTEMPTS),
      initialDelayMs: getEnvNumber('RETRY_INITIAL_DELAY_MS', RETRY_CONFIG.INITIAL_DELAY_MS),
      maxDelayMs: getEnvNumber('RETRY_MAX_DELAY_MS', RETRY_CONFIG.MAX_DELAY_MS),
    },
    
    security: {
      signingKeyPath: getEnv('SIGNING_KEY_PATH', ''),
      signingKeyPem: getEnv('SIGNING_KEY_PEM', ''),
      signingKeyId: getEnv('SIGNING_KEY_ID', ''),
      verificationKeysPath: getEnv('VERIFICATION_KEYS_PATH', ''),
      apiKeyAuthEnabled: getEnvBool('API_KEY_AUTH_ENABLED', env === 'prod'),
      apiKeys: parseCsv(getEnv('API_KEYS', '')),
    },
  };

  // Validate configuration
  const parsed = ConfigSchema.parse(config);

  if (parsed.security.apiKeyAuthEnabled && parsed.security.apiKeys.length === 0) {
    throw new Error('API_KEY_AUTH_ENABLED=true requires API_KEYS to be configured.');
  }

  if (parsed.service.env === 'prod' && !parsed.services.serviceAuthToken) {
    throw new Error('Production enforcer requires SERVICE_AUTH_TOKEN for downstream service calls.');
  }

  return parsed;
}
