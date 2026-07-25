/**
 * STIX Policy Service Configuration
 */

import { z } from 'zod';
import {
  SERVICE_PORTS,
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

  storage: z.object({
    type: z.enum(['memory', 'file', 'file-watch', 'postgres']),
    policyDirectory: z.string().optional(),
    postgresUrl: z.string().optional(),
  }),

  auth: z.object({
    serviceTokenAuthEnabled: z.boolean(),
    serviceToken: z.string().optional(),
  }),

  caching: z.object({
    enabled: z.boolean(),
    ttlSeconds: z.number(),
  }),
});

export type Config = z.infer<typeof ConfigSchema>;

export function loadConfig(): Config {
  const rawEnv = getEnv('NODE_ENV', 'dev');
  const normalizedEnv = rawEnv.toLowerCase() === 'production' ? 'prod' : rawEnv.toLowerCase();
  const env = normalizedEnv as 'dev' | 'test' | 'stage' | 'prod';

  const config: Config = {
    service: {
      name: 'stix-policy',
      version: getEnv('SERVICE_VERSION', '0.1.7'),
      port: getEnvNumber('PORT', SERVICE_PORTS.POLICY),
      host: getEnv('HOST', '0.0.0.0'),
      env,
    },

    logging: {
      level: getEnv('LOG_LEVEL', env === 'prod' ? 'info' : 'debug') as Config['logging']['level'],
      pretty: getEnvBool('LOG_PRETTY', env !== 'prod'),
    },

    storage: {
      type: getEnv('STORAGE_TYPE', 'file-watch') as Config['storage']['type'],
      policyDirectory: getEnv('POLICY_DIRECTORY', './policies/examples'),
      postgresUrl: getEnv('POSTGRES_URL', ''),
    },

    auth: {
      serviceTokenAuthEnabled: getEnvBool('SERVICE_TOKEN_AUTH_ENABLED', env === 'prod'),
      serviceToken: getEnv('SERVICE_AUTH_TOKEN', ''),
    },

    caching: {
      enabled: getEnvBool('CACHE_ENABLED', true),
      ttlSeconds: getEnvNumber('CACHE_TTL_SECONDS', 60),
    },
  };

  const parsed = ConfigSchema.parse(config);

  if (parsed.service.env === 'prod' && parsed.storage.type === 'memory') {
    throw new Error(
      'STORAGE_TYPE=memory is not allowed in prod for stix-policy. Use file/file-watch with persistent volume or a durable backend.'
    );
  }

  if (parsed.storage.type === 'postgres' && !parsed.storage.postgresUrl) {
    throw new Error('STORAGE_TYPE=postgres requires POSTGRES_URL for stix-policy.');
  }

  if (parsed.auth.serviceTokenAuthEnabled && !parsed.auth.serviceToken) {
    throw new Error('SERVICE_TOKEN_AUTH_ENABLED=true requires SERVICE_AUTH_TOKEN for stix-policy.');
  }

  return parsed;
}
