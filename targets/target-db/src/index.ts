/**
 * STIX Target DB Service
 * Protected database access service that requires STIX proof tokens
 *
 * @module @stix/target-db
 */

import Fastify, { type FastifyInstance } from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import rateLimit from '@fastify/rate-limit';
import * as fs from 'fs';
import {
  createLoggerFromEnv,
  generateEd25519KeyPair,
  type Logger,
  HEADERS,
} from '@stix/shared';
import {
  createVerifier,
  type TargetVerifier,
  type VerifierConfig,
} from '@stix/target-verifier';

import { loadConfig, type Config } from './config.js';
import { DatabaseService, MockDatabaseService } from './database.js';
import { registerRoutes } from './routes.js';

// =============================================================================
// APPLICATION CONTEXT
// =============================================================================

interface AppContext {
  config: Config;
  logger: Logger;
  server: FastifyInstance;
  database: DatabaseService;
  verifier: TargetVerifier;
  startTime: number;
}

// =============================================================================
// CREATE APPLICATION
// =============================================================================

async function createApp(): Promise<AppContext> {
  const config = loadConfig();

  const logger = createLoggerFromEnv(config.service.name);
  logger.info('Starting STIX Target DB', {
    version: config.service.version,
    env: config.service.env,
    db_type: config.database.type,
  });

  const server = Fastify({
    logger: false,
    requestIdHeader: HEADERS.REQUEST_ID,
    trustProxy: true,
  });

  await server.register(cors, {
    origin: config.service.env === 'prod' ? false : true,
    methods: ['GET', 'POST', 'OPTIONS'],
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

  // Load STIX public key
  let publicKeyPem = config.stix.publicKeyPem;

  if (!publicKeyPem && config.stix.publicKeyPath) {
    try {
      publicKeyPem = fs.readFileSync(config.stix.publicKeyPath, 'utf-8');
    } catch (error) {
      logger.warn('Could not load public key from file', {
        path: config.stix.publicKeyPath,
      });
    }
  }

  // Create STIX verifier
  const verifierConfig: VerifierConfig = {
    publicKeys: publicKeyPem
      ? [
          {
            keyId: config.stix.keyId,
            algorithm: config.stix.algorithm,
            pem: publicKeyPem,
          },
        ]
      : [],
    expectedIssuer: config.stix.expectedIssuer,
    requireActionMatch: config.stix.requireActionMatch,
    requireResourceMatch: config.stix.requireResourceMatch,
    defaultMaxTokenAge: config.stix.maxTokenAge,
  };

  if (verifierConfig.publicKeys.length === 0 && config.service.env !== 'prod') {
    logger.warn('No public key configured - generating test key pair');
    const keyPair = generateEd25519KeyPair();
    verifierConfig.publicKeys = [
      {
        keyId: 'dev-key',
        algorithm: 'EdDSA',
        pem: keyPair.publicKey,
      },
    ];
  }

  const verifier = createVerifier(verifierConfig, logger);

  // Create database service
  const database =
    config.service.env === 'test'
      ? new MockDatabaseService(config, logger)
      : new DatabaseService(config, logger);

  // Initialize database
  await database.initialize();

  const startTime = Date.now();

  // Register routes
  await registerRoutes(server, {
    config,
    logger,
    database,
    verifier,
    startTime,
  });

  // Request logging hook
  server.addHook('onResponse', async (request, reply) => {
    logger.http(`${request.method} ${request.url} ${reply.statusCode}`, {
      request_id: request.id,
      method: request.method,
      path: request.url,
      status_code: reply.statusCode,
      duration_ms: reply.elapsedTime,
    });
  });

  return {
    config,
    logger,
    server,
    database,
    verifier,
    startTime,
  };
}

// =============================================================================
// START SERVER
// =============================================================================

async function start(): Promise<void> {
  const app = await createApp();
  const { config, logger, server, database } = app;

  const shutdown = async (signal: string) => {
    logger.info(`Received ${signal}, shutting down gracefully...`);

    try {
      await database.close();
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

  try {
    await server.listen({
      port: config.service.port,
      host: config.service.host,
    });

    logger.info(`STIX Target DB listening`, {
      port: config.service.port,
      host: config.service.host,
      env: config.service.env,
      db_type: config.database.type,
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
export type { Config } from './config.js';
export { DatabaseService, MockDatabaseService } from './database.js';
export type { QueryRequest, QueryResult } from './database.js';

// =============================================================================
// MAIN
// =============================================================================

const isMain = import.meta.url === `file://${process.argv[1]}`;
if (isMain) {
  start().catch((err) => {
    console.error('Fatal error:', err);
    process.exit(1);
  });
}
