/**
 * STIX Fabric Control Plane Service.
 *
 * Fabric coordinates the governance registry above STIX Core enforcement.
 */

import Fastify, { type FastifyInstance } from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import { HEADERS, createLoggerFromEnv, type Logger } from '@stix/shared';
import { loadConfig, type Config } from './config/index.js';
import { createFabricStore, type FabricStore } from './store/index.js';
import { fabricRoutes, healthRoutes } from './routes/index.js';

interface AppContext {
  config: Config;
  logger: Logger;
  server: FastifyInstance;
  store: FabricStore;
  startTime: number;
}

async function createApp(): Promise<AppContext> {
  const config = loadConfig();
  const logger = createLoggerFromEnv(config.service.name);

  logger.info('Starting STIX Fabric Service', {
    version: config.service.version,
    env: config.service.env,
  });

  const server = Fastify({
    logger: false,
    requestIdHeader: HEADERS.REQUEST_ID,
    trustProxy: true,
  });

  await server.register(cors, {
    origin: config.service.env === 'prod' ? false : true,
  });
  await server.register(helmet, { contentSecurityPolicy: false });

  const store = await createFabricStore(logger);
  const startTime = Date.now();

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

  await server.register(healthRoutes, {
    store,
    startTime,
    version: config.service.version,
  });
  await server.register(fabricRoutes, { store });

  return { config, logger, server, store, startTime };
}

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
    await server.listen({
      port: config.service.port,
      host: config.service.host,
    });

    logger.info('STIX Fabric listening', {
      port: config.service.port,
      host: config.service.host,
      env: config.service.env,
    });
  } catch (error) {
    logger.error('Failed to start server', {}, error as Error);
    process.exit(1);
  }
}

export { createApp, start };
export type { AppContext };
export { createFabricStore, InMemoryFabricStore, type FabricStore } from './store/index.js';
export { fabricRoutes, healthRoutes } from './routes/index.js';
export type { Config } from './config/index.js';

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
  start().catch((error) => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}
