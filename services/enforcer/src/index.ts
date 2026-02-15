/**
 * STIX Enforcer Service
 * Main entry point for the authorization decision engine
 * 
 * @module @stix/enforcer
 */

import Fastify, { type FastifyInstance } from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import rateLimit from '@fastify/rate-limit';
import {
  createLoggerFromEnv,
  generateEd25519KeyPair,
  InMemoryKeyStore,
  loadPrivateKey,
  type SigningKey,
  type Logger,
  HEADERS,
} from '@stix/shared';
import * as fs from 'node:fs';

import { loadConfig, type Config } from './config/index.js';
import { AuthorizationEngine } from './core/engine.js';
import {
  PolicyClient,
  MockPolicyClient,
  EvidenceClient,
  MockEvidenceClient,
  ApprovalsClient,
  MockApprovalsClient,
  createCacheService,
  type CacheService,
} from './services/index.js';
import { authorizationRoutes, healthRoutes, statsRoutes } from './routes/index.js';

// =============================================================================
// APPLICATION CONTEXT
// =============================================================================

interface AppContext {
  config: Config;
  logger: Logger;
  server: FastifyInstance;
  policyClient: PolicyClient;
  evidenceClient: EvidenceClient;
  approvalsClient: ApprovalsClient;
  cache: CacheService | null;
  engine: AuthorizationEngine;
  signingKey: SigningKey | null;
  startTime: number;
}

// =============================================================================
// CREATE APPLICATION
// =============================================================================

async function createApp(): Promise<AppContext> {
  // Load configuration
  const config = loadConfig();
  
  // Create logger
  const logger = createLoggerFromEnv(config.service.name);
  logger.info('Starting STIX Enforcer', {
    version: config.service.version,
    env: config.service.env,
  });

  // Create Fastify server
  const server = Fastify({
    logger: false, // We use our own logger
    requestIdHeader: HEADERS.REQUEST_ID,
    trustProxy: true,
  });

  // Register plugins
  await server.register(cors, {
    origin: config.service.env === 'prod' ? false : true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  });

  await server.register(helmet, {
    contentSecurityPolicy: false,
  });

  if (config.rateLimiting.enabled) {
    await server.register(rateLimit, {
      max: config.rateLimiting.maxRequests,
      timeWindow: config.rateLimiting.windowMs,
    });
  }

  // Create service clients
  let policyClient: PolicyClient;
  let evidenceClient: EvidenceClient;
  let approvalsClient: ApprovalsClient;

  if (config.service.env === 'dev' || config.service.env === 'test') {
    logger.info('Using mock service clients');
    policyClient = new MockPolicyClient(config, logger);
    evidenceClient = new MockEvidenceClient(config, logger);
    approvalsClient = new MockApprovalsClient(config, logger);
  } else {
    policyClient = new PolicyClient(config, logger);
    evidenceClient = new EvidenceClient(config, logger);
    approvalsClient = new ApprovalsClient(config, logger);
  }

  // Create cache
  const cache = await createCacheService(config, logger);

  // Setup signing key
  let signingKey: SigningKey | null = null;

  const keyPath = config.security.signingKeyPath;
  const keyPem = config.security.signingKeyPem;
  const keyId = config.security.signingKeyId;
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
    throw new Error('Production enforcer requires SIGNING_KEY_ID with SIGNING_KEY_PATH or SIGNING_KEY_PEM.');
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

    logger.info('Loaded signing key from configured path', {
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

    logger.info('Loaded signing key from inline secret', {
      key_id: signingKey.keyId,
      algorithm: signingKey.algorithm,
    });
  } else {
    // Generate development signing key
    const keyStore = new InMemoryKeyStore();
    const keyPair = generateEd25519KeyPair();
    keyStore.addKeyPair(keyPair);
    signingKey = await keyStore.getSigningKey();
    logger.warn('Generated ephemeral signing key (non-production only)', {
      key_id: signingKey.keyId,
    });
  }

  // Create authorization engine
  const engine = new AuthorizationEngine(
    config,
    logger,
    policyClient,
    evidenceClient,
    approvalsClient,
    cache,
    signingKey
  );

  const startTime = Date.now();

  // Request logging + auth hook (must be registered before routes)
  server.addHook('onRequest', async (request, reply) => {
    const reqLogger = logger.child({
      request_id: request.id,
      method: request.method,
      url: request.url,
    });
    (request as typeof request & { stixLog?: Logger }).stixLog = reqLogger;

    if (!config.security.apiKeyAuthEnabled) {
      return;
    }

    const path = request.url.split('?')[0];
    const publicPaths = new Set(['/health', '/ready', '/metrics']);
    if (publicPaths.has(path)) {
      return;
    }

    const apiKeyHeader = request.headers[HEADERS.API_KEY.toLowerCase()] as string | undefined;
    const authHeader = request.headers.authorization as string | undefined;
    const bearerKey = authHeader?.startsWith('Bearer ') ? authHeader.slice(7).trim() : undefined;
    const presentedKey = apiKeyHeader?.trim() || bearerKey;

    if (!presentedKey || !config.security.apiKeys.includes(presentedKey)) {
      return reply.code(401).send({
        success: false,
        error: {
          code: 'AUTHENTICATION_REQUIRED',
          message: 'Valid API key is required',
        },
      });
    }
  });

  // Response logging hook
  server.addHook('onResponse', async (request, reply) => {
    logger.http(`${request.method} ${request.url} ${reply.statusCode}`, {
      request_id: request.id,
      method: request.method,
      path: request.url,
      status_code: reply.statusCode,
      duration_ms: reply.elapsedTime,
    });
  });

  // Register routes
  await server.register(healthRoutes, {
    config,
    policyClient,
    evidenceClient,
    approvalsClient,
    cache,
    startTime,
  });

  await server.register(authorizationRoutes, {
    engine,
    evidenceClient,
  });

  await server.register(statsRoutes, {
    evidenceClient,
  });

  return {
    config,
    logger,
    server,
    policyClient,
    evidenceClient,
    approvalsClient,
    cache,
    engine,
    signingKey,
    startTime,
  };
}

// =============================================================================
// START SERVER
// =============================================================================

async function start(): Promise<void> {
  const app = await createApp();
  const { config, logger, server } = app;

  // Graceful shutdown
  const shutdown = async (signal: string) => {
    logger.info(`Received ${signal}, shutting down gracefully...`);
    
    try {
      await server.close();
      logger.info('Server closed');
      process.exit(0);
    } catch (err) {
      logger.error('Error during shutdown', {}, err as Error);
      process.exit(1);
    }
  };

  process.on('SIGTERM', () => shutdown('SIGTERM'));
  process.on('SIGINT', () => shutdown('SIGINT'));

  // Start server
  try {
    await server.listen({
      port: config.service.port,
      host: config.service.host,
    });

    logger.info(`STIX Enforcer listening`, {
      port: config.service.port,
      host: config.service.host,
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
export type { AppContext };

// Re-export types
export type { Config } from './config/index.js';
export { AuthorizationEngine } from './core/engine.js';
export {
  PolicyClient,
  MockPolicyClient,
  EvidenceClient,
  MockEvidenceClient,
  ApprovalsClient,
  MockApprovalsClient,
} from './services/index.js';

// =============================================================================
// MAIN
// =============================================================================

// Start if running directly
const isMainModule = () => {
  const moduleUrl = import.meta.url;
  const scriptPath = process.argv[1];
  // Handle Windows paths and normalize
  const normalizedModuleUrl = moduleUrl.replace(/\\/g, '/');
  const normalizedScriptPath = scriptPath?.replace(/\\/g, '/');
  return normalizedModuleUrl.endsWith(normalizedScriptPath) ||
         normalizedModuleUrl === `file:///${normalizedScriptPath}` ||
         normalizedModuleUrl === `file://${normalizedScriptPath}`;
};

if (isMainModule()) {
  start().catch((err) => {
    console.error('Fatal error:', err);
    process.exit(1);
  });
}
