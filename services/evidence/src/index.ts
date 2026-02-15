/**
 * STIX Evidence Service
 * Tamper-evident audit trail with hash chain integrity
 * 
 * @module @stix/evidence
 */

import Fastify, { type FastifyInstance } from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import {
  createLoggerFromEnv,
  type Logger,
  type SigningKey,
  generateEd25519KeyPair,
  InMemoryKeyStore,
  loadPrivateKey,
  HEADERS,
} from '@stix/shared';
import * as fs from 'node:fs';

import { loadConfig, type Config } from './config/index.js';
import { createEvidenceStore, type EvidenceStore } from './store/index.js';
import { evidenceRoutes, healthRoutes } from './routes/index.js';

// =============================================================================
// APPLICATION CONTEXT
// =============================================================================

interface AppContext {
  config: Config;
  logger: Logger;
  server: FastifyInstance;
  store: EvidenceStore;
  signingKey: SigningKey | null;
  startTime: number;
}

// =============================================================================
// CREATE APPLICATION
// =============================================================================

async function createApp(): Promise<AppContext> {
  const config = loadConfig();
  const logger = createLoggerFromEnv(config.service.name);
  
  logger.info('Starting STIX Evidence Service', {
    version: config.service.version,
    env: config.service.env,
  });

  // Create Fastify server
  const server = Fastify({
    logger: false,
    requestIdHeader: HEADERS.REQUEST_ID,
    trustProxy: true,
  });

  await server.register(cors, { origin: config.service.env === 'prod' ? false : true });
  await server.register(helmet, { contentSecurityPolicy: false });

  // Setup signing key
  let signingKey: SigningKey | null = null;

  if (config.service.env === 'prod' && !config.signing.enabled) {
    throw new Error('Production evidence service requires SIGNING_ENABLED=true.');
  }

  if (config.signing.enabled) {
    const keyPath = config.signing.keyPath;
    const keyPem = config.signing.keyPem;
    const keyId = config.signing.keyId;
    const hasKeyPath = Boolean(keyPath);
    const hasKeyPem = Boolean(keyPem);
    const hasKeyId = Boolean(keyId);
    const hasPathKey = hasKeyPath && hasKeyId;
    const hasPemKey = hasKeyPem && hasKeyId;

    if (hasKeyPath && hasKeyPem) {
      throw new Error('Configure exactly one signing key source: SIGNING_KEY_PATH or SIGNING_KEY_PEM.');
    }

    if ((hasKeyPath || hasKeyPem) && !hasKeyId) {
      throw new Error('SIGNING_KEY_ID is required when using SIGNING_KEY_PATH or SIGNING_KEY_PEM.');
    }

    if (hasKeyId && !hasKeyPath && !hasKeyPem) {
      throw new Error('SIGNING_KEY_ID requires a key source (SIGNING_KEY_PATH or SIGNING_KEY_PEM).');
    }

    if (config.service.env === 'prod' && !hasPathKey && !hasPemKey) {
      throw new Error('Production evidence service requires SIGNING_KEY_ID with SIGNING_KEY_PATH or SIGNING_KEY_PEM.');
    }

    if (hasPathKey) {
      if (!fs.existsSync(keyPath!)) {
        throw new Error(`Signing key file not found: ${keyPath}`);
      }

      const privateKey = loadPrivateKey(fs.readFileSync(keyPath!, 'utf8'));
      const keyType = privateKey.asymmetricKeyType;
      const algorithm =
        keyType === 'ed25519'
          ? 'EdDSA'
          : keyType === 'ec'
            ? 'ES256'
            : null;

      if (!algorithm) {
        throw new Error(`Unsupported signing key type: ${keyType}`);
      }

      signingKey = {
        keyId: keyId!,
        algorithm,
        privateKey,
      };

      logger.info('Evidence signing key loaded from configured path', {
        key_id: signingKey.keyId,
        algorithm: signingKey.algorithm,
      });
    } else if (hasPemKey) {
      const privateKey = loadPrivateKey(keyPem!);
      const keyType = privateKey.asymmetricKeyType;
      const algorithm =
        keyType === 'ed25519'
          ? 'EdDSA'
          : keyType === 'ec'
            ? 'ES256'
            : null;

      if (!algorithm) {
        throw new Error(`Unsupported signing key type: ${keyType}`);
      }

      signingKey = {
        keyId: keyId!,
        algorithm,
        privateKey,
      };

      logger.info('Evidence signing key loaded from inline secret', {
        key_id: signingKey.keyId,
        algorithm: signingKey.algorithm,
      });
    } else {
      const keyStore = new InMemoryKeyStore();
      const keyPair = generateEd25519KeyPair();
      keyStore.addKeyPair(keyPair);
      signingKey = await keyStore.getSigningKey();
      logger.warn('Generated ephemeral signing key (non-production only)', {
        key_id: signingKey.keyId,
      });
    }
  } else {
    logger.warn('Evidence signing disabled');
  }

  // Create evidence store
  const store = await createEvidenceStore(config, logger, signingKey);

  const startTime = Date.now();

  // Request auth hook (must be registered before routes)
  server.addHook('onRequest', async (request, reply) => {
    if (!config.auth.serviceTokenAuthEnabled) {
      return;
    }

    const path = request.url.split('?')[0];
    const publicPaths = new Set(['/health', '/ready']);
    if (publicPaths.has(path)) {
      return;
    }

    const providedToken = request.headers['x-stix-service-token'];
    const token = Array.isArray(providedToken) ? providedToken[0] : providedToken;
    if (!token || token !== config.auth.serviceToken) {
      return reply.code(401).send({
        success: false,
        error: {
          code: 'AUTHENTICATION_REQUIRED',
          message: 'Valid service token is required',
        },
      });
    }
  });

  server.addHook('onResponse', async (request, reply) => {
    logger.http(`${request.method} ${request.url} ${reply.statusCode}`, {
      method: request.method,
      path: request.url,
      status_code: reply.statusCode,
      duration_ms: reply.elapsedTime,
    });
  });

  // Register routes
  await server.register(healthRoutes, { store, startTime, version: config.service.version });
  await server.register(evidenceRoutes, { store });

  return { config, logger, server, store, signingKey, startTime };
}

// =============================================================================
// START SERVER
// =============================================================================

async function start(): Promise<void> {
  const app = await createApp();
  const { config, logger, server } = app;

  const shutdown = async (signal: string) => {
    logger.info(`Received ${signal}, shutting down...`);
    await server.close();
    process.exit(0);
  };

  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGINT', () => shutdown('SIGINT'));

  try {
    await server.listen({ port: config.service.port, host: config.service.host });
    logger.info('STIX Evidence Service listening', {
      port: config.service.port,
      env: config.service.env,
    });
  } catch (err) {
    logger.error('Failed to start server', {}, err as Error);
    process.exit(1);
  }
}

// =============================================================================
// EXPORTS
// =============================================================================

export { createApp, start };
export type { AppContext, Config };
export { createEvidenceStore, type EvidenceStore } from './store/index.js';

// Start if running directly
const isMainModule = () => {
  const moduleUrl = import.meta.url;
  const scriptPath = process.argv[1];
  const normalizedModuleUrl = moduleUrl.replace(/\\/g, '/');
  const normalizedScriptPath = scriptPath?.replace(/\\/g, '/');
  return normalizedModuleUrl.endsWith(normalizedScriptPath) ||
         normalizedModuleUrl === `file:///${normalizedScriptPath}` ||
         normalizedModuleUrl === `file://${normalizedScriptPath}`;
};

if (isMainModule()) {
  start().catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
  });
}
