/**
 * STIX Policy Service
 * Policy management and evaluation service
 * 
 * @module @stix/policy
 */

import Fastify, { type FastifyInstance } from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import { createLoggerFromEnv, type Logger, HEADERS } from '@stix/shared';

import { loadConfig, type Config } from './config/index.js';
import { PolicyEngine } from './core/engine.js';
import { createPolicyStore, type PolicyStore } from './store/index.js';
import { evaluateRoutes, policyRoutes, statsRoutes, healthRoutes } from './routes/index.js';

// =============================================================================
// APPLICATION CONTEXT
// =============================================================================

interface AppContext {
  config: Config;
  logger: Logger;
  server: FastifyInstance;
  store: PolicyStore;
  engine: PolicyEngine;
  startTime: number;
}

// =============================================================================
// CREATE APPLICATION
// =============================================================================

async function createApp(): Promise<AppContext> {
  const config = loadConfig();
  const logger = createLoggerFromEnv(config.service.name);
  
  logger.info('Starting STIX Policy Service', {
    version: config.service.version,
    env: config.service.env,
  });

  // Create Fastify server
  const server = Fastify({
    logger: false,
    requestIdHeader: HEADERS.REQUEST_ID,
    trustProxy: true,
  });

  // Register plugins
  await server.register(cors, {
    origin: config.service.env === 'prod' ? false : true,
  });
  await server.register(helmet, { contentSecurityPolicy: false });

  // Create policy store
  const store = await createPolicyStore(config, logger);

  // Create policy engine
  const engine = new PolicyEngine(config, logger, store);

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
  await server.register(healthRoutes, {
    store,
    startTime,
    version: config.service.version,
  });

  await server.register(evaluateRoutes, { engine });
  await server.register(policyRoutes, { store, engine });
  await server.register(statsRoutes, { store });

  return { config, logger, server, store, engine, startTime };
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
    logger.info('STIX Policy Service listening', {
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
export { PolicyEngine } from './core/engine.js';
export { createPolicyStore, type PolicyStore } from './store/index.js';

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
