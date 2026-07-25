/**
 * STIX Approvals Service Configuration
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
    type: z.enum(['memory', 'postgres']),
    postgresUrl: z.string().optional(),
  }),

  approvals: z.object({
    defaultTimeoutHours: z.number(),
    maxTimeoutHours: z.number(),
    cleanupIntervalMinutes: z.number(),
    enableNotifications: z.boolean(),
  }),

  notifications: z.object({
    webhookUrl: z.string().optional(),
    emailFrom: z.string().optional(),
    smtpHost: z.string().optional(),
    smtpPort: z.number().optional(),
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
      name: 'stix-approvals',
      version: getEnv('SERVICE_VERSION', '0.1.6'),
      port: getEnvNumber('PORT', SERVICE_PORTS.APPROVALS),
      host: getEnv('HOST', '0.0.0.0'),
      env,
    },

    logging: {
      level: getEnv('LOG_LEVEL', env === 'prod' ? 'info' : 'debug') as Config['logging']['level'],
      pretty: getEnvBool('LOG_PRETTY', env !== 'prod'),
    },

    storage: {
      type: getEnv('STORAGE_TYPE', 'memory') as Config['storage']['type'],
      postgresUrl: getEnv('POSTGRES_URL', ''),
    },

    approvals: {
      defaultTimeoutHours: getEnvNumber('APPROVAL_TIMEOUT_HOURS', 24),
      maxTimeoutHours: getEnvNumber('APPROVAL_MAX_TIMEOUT_HOURS', 168), // 1 week
      cleanupIntervalMinutes: getEnvNumber('APPROVAL_CLEANUP_INTERVAL_MINUTES', 60),
      enableNotifications: getEnvBool('APPROVAL_ENABLE_NOTIFICATIONS', false),
    },

    notifications: {
      webhookUrl: getEnv('NOTIFICATION_WEBHOOK_URL', ''),
      emailFrom: getEnv('NOTIFICATION_EMAIL_FROM', ''),
      smtpHost: getEnv('SMTP_HOST', ''),
      smtpPort: getEnvNumber('SMTP_PORT', 587),
    },
    auth: {
      serviceTokenAuthEnabled: getEnvBool('SERVICE_TOKEN_AUTH_ENABLED', env === 'prod'),
      serviceToken: getEnv('SERVICE_AUTH_TOKEN', ''),
    },
  };

  const parsed = ConfigSchema.parse(config);

  if (parsed.service.env === 'prod' && parsed.storage.type === 'memory') {
    throw new Error(
      'STORAGE_TYPE=memory is not allowed in prod for stix-approvals. Configure postgres before startup.'
    );
  }

  if (parsed.storage.type === 'postgres' && !parsed.storage.postgresUrl) {
    throw new Error('STORAGE_TYPE=postgres requires POSTGRES_URL for stix-approvals.');
  }

  if (parsed.auth.serviceTokenAuthEnabled && !parsed.auth.serviceToken) {
    throw new Error('SERVICE_TOKEN_AUTH_ENABLED=true requires SERVICE_AUTH_TOKEN for stix-approvals.');
  }

  return parsed;
}
