/**
 * STIX Evidence Service Configuration
 */

import { z } from 'zod';
import {
  SERVICE_PORTS,
  EVIDENCE_CONFIG,
  getEnv,
  getEnvNumber,
  getEnvBool,
} from '@stix/shared';

const ConfigSchema = z.object({
  service: z.object({
    name: z.string(),
    version: z.string(),
    port: z.number(),
    host: z.string(),
    env: z.enum(['dev', 'test', 'stage', 'prod']),
  }),
  logging: z.object({
    level: z.enum(['error', 'warn', 'info', 'http', 'debug', 'trace']),
    pretty: z.boolean(),
  }),
  evidence: z.object({
    schemaVersion: z.string(),
    maxBatchSize: z.number(),
    retentionDays: z.number(),
    archiveAfterDays: z.number(),
  }),
  storage: z.object({
    type: z.enum(['memory', 'postgres']),
    postgresUrl: z.string().optional(),
  }),
  signing: z.object({
    enabled: z.boolean(),
    keyPath: z.string().optional(),
    keyPem: z.string().optional(),
    keyId: z.string().optional(),
  }),
  auth: z.object({
    serviceTokenAuthEnabled: z.boolean(),
    serviceToken: z.string().optional(),
  }),
});

export type Config = z.infer<typeof ConfigSchema>;

export function loadConfig(): Config {
  const rawEnv = getEnv('NODE_ENV', 'dev');
  const normalizedEnv = rawEnv.toLowerCase() === 'production' ? 'prod' : rawEnv.toLowerCase();
  const env = normalizedEnv as 'dev' | 'test' | 'stage' | 'prod';
  
  const config: Config = {
    service: {
      name: 'stix-evidence',
      version: getEnv('SERVICE_VERSION', '0.1.14'),
      port: getEnvNumber('PORT', SERVICE_PORTS.EVIDENCE),
      host: getEnv('HOST', '0.0.0.0'),
      env,
    },
    logging: {
      level: (getEnv('LOG_LEVEL', env === 'prod' ? 'info' : 'debug')) as Config['logging']['level'],
      pretty: getEnvBool('LOG_PRETTY', env !== 'prod'),
    },
    evidence: {
      schemaVersion: EVIDENCE_CONFIG.SCHEMA_VERSION,
      maxBatchSize: getEnvNumber('EVIDENCE_MAX_BATCH', EVIDENCE_CONFIG.MAX_BATCH_SIZE),
      retentionDays: getEnvNumber('EVIDENCE_RETENTION_DAYS', EVIDENCE_CONFIG.DEFAULT_RETENTION_DAYS),
      archiveAfterDays: getEnvNumber('EVIDENCE_ARCHIVE_DAYS', EVIDENCE_CONFIG.ARCHIVE_AFTER_DAYS),
    },
    storage: {
      type: (getEnv('STORAGE_TYPE', 'memory')) as Config['storage']['type'],
      postgresUrl: getEnv('POSTGRES_URL', ''),
    },
    signing: {
      enabled: getEnvBool('SIGNING_ENABLED', true),
      keyPath: getEnv('SIGNING_KEY_PATH', ''),
      keyPem: getEnv('SIGNING_KEY_PEM', ''),
      keyId: getEnv('SIGNING_KEY_ID', ''),
    },
    auth: {
      serviceTokenAuthEnabled: getEnvBool('SERVICE_TOKEN_AUTH_ENABLED', env === 'prod'),
      serviceToken: getEnv('SERVICE_AUTH_TOKEN', ''),
    },
  };
  
  const parsed = ConfigSchema.parse(config);

  if (parsed.service.env === 'prod' && parsed.storage.type === 'memory') {
    throw new Error(
      'STORAGE_TYPE=memory is not allowed in prod for stix-evidence. Configure a durable store before startup.'
    );
  }

  if (parsed.storage.type === 'postgres' && !parsed.storage.postgresUrl) {
    throw new Error('STORAGE_TYPE=postgres requires POSTGRES_URL for stix-evidence.');
  }

  if (parsed.auth.serviceTokenAuthEnabled && !parsed.auth.serviceToken) {
    throw new Error('SERVICE_TOKEN_AUTH_ENABLED=true requires SERVICE_AUTH_TOKEN for stix-evidence.');
  }

  return parsed;
}
