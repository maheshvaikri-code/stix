/**
 * STIX Observability Package
 * Metrics and tracing for STIX services
 *
 * @packageDocumentation
 *
 * @example Complete Setup
 * ```typescript
 * import { StixMetrics, StixTracing, createObservability } from '@stix/observability';
 *
 * // Quick setup with createObservability
 * const { metrics, tracing } = await createObservability({
 *   serviceName: 'stix-enforcer',
 *   serviceVersion: '0.1.13',
 *   environment: 'production',
 *   otlpEndpoint: 'http://otel-collector:4318',
 * });
 *
 * // Register with Fastify
 * import Fastify from 'fastify';
 * const app = Fastify();
 *
 * app.register(createMetricsPlugin(metrics));
 * app.register(createTracingPlugin(tracing));
 * app.addHook('onRequest', createHttpMetricsHook(metrics).onRequest);
 * app.addHook('onResponse', createHttpMetricsHook(metrics).onResponse);
 *
 * // Record authorization
 * const start = Date.now();
 * // ... authorization logic ...
 * metrics.recordAuthorization({
 *   decision: 'ALLOW',
 *   actorType: 'AI_AGENT',
 *   action: 'send_email',
 *   resourceType: 'email',
 *   env: 'prod',
 *   durationSeconds: (Date.now() - start) / 1000,
 * });
 * ```
 */

export {
  StixMetrics,
  createMetricsPlugin,
  createHttpMetricsHook,
  type MetricsConfig,
} from './metrics';

export {
  StixTracing,
  createTracingPlugin,
  traced,
  Traced,
  type TracingConfig,
} from './tracing';

import { StixMetrics, type MetricsConfig } from './metrics';
import { StixTracing, type TracingConfig } from './tracing';

/**
 * Combined observability configuration
 */
export interface ObservabilityConfig {
  /** Service name */
  serviceName: string;

  /** Service version */
  serviceVersion?: string;

  /** Deployment environment */
  environment?: string;

  /** OTLP exporter endpoint for tracing and metrics export */
  otlpEndpoint?: string;

  /** Sample rate for tracing (0.0 to 1.0) */
  tracingSampleRate?: number;

  /** Enable default Node.js metrics collection */
  collectDefaultMetrics?: boolean;

  /** Metrics prefix */
  metricsPrefix?: string;

  /** Additional resource attributes for tracing */
  resourceAttributes?: Record<string, string>;
}

/**
 * Observability instances
 */
export interface Observability {
  /** Metrics instance */
  metrics: StixMetrics;

  /** Tracing instance */
  tracing: StixTracing;

  /** Shutdown all observability components */
  shutdown: () => Promise<void>;
}

/**
 * Create complete observability setup
 *
 * @example
 * ```typescript
 * const { metrics, tracing, shutdown } = await createObservability({
 *   serviceName: 'stix-enforcer',
 *   environment: 'production',
 *   otlpEndpoint: process.env.OTEL_EXPORTER_OTLP_ENDPOINT,
 * });
 *
 * // Graceful shutdown
 * process.on('SIGTERM', async () => {
 *   await shutdown();
 *   process.exit(0);
 * });
 * ```
 */
export async function createObservability(
  config: ObservabilityConfig
): Promise<Observability> {
  const metricsConfig: MetricsConfig = {
    serviceName: config.serviceName,
    collectDefaultMetrics: config.collectDefaultMetrics ?? true,
    prefix: config.metricsPrefix ?? 'stix',
    defaultLabels: {
      environment: config.environment ?? 'production',
      version: config.serviceVersion ?? '1.0.0',
    },
  };

  const tracingConfig: TracingConfig = {
    serviceName: config.serviceName,
    serviceVersion: config.serviceVersion ?? '1.0.0',
    environment: config.environment ?? 'production',
    otlpEndpoint: config.otlpEndpoint,
    sampleRate: config.tracingSampleRate ?? 0.1,
    resourceAttributes: config.resourceAttributes,
    enableHttpInstrumentation: true,
    enableFastifyInstrumentation: true,
    enablePgInstrumentation: true,
  };

  const metrics = new StixMetrics(metricsConfig);
  const tracing = new StixTracing(tracingConfig);

  // Start tracing
  await tracing.start();

  // Mark service as up
  metrics.serviceUp.set({ component: 'main' }, 1);

  return {
    metrics,
    tracing,
    shutdown: async () => {
      metrics.serviceUp.set({ component: 'main' }, 0);
      await tracing.shutdown();
    },
  };
}

/**
 * Create observability from environment variables
 *
 * Reads from:
 * - SERVICE_NAME or OTEL_SERVICE_NAME
 * - SERVICE_VERSION
 * - NODE_ENV or ENVIRONMENT
 * - OTEL_EXPORTER_OTLP_ENDPOINT
 * - TRACING_SAMPLE_RATE
 */
export async function createObservabilityFromEnv(): Promise<Observability> {
  return createObservability({
    serviceName: process.env.SERVICE_NAME ?? process.env.OTEL_SERVICE_NAME ?? 'stix',
    serviceVersion: process.env.SERVICE_VERSION ?? '0.1.13',
    environment: process.env.NODE_ENV ?? process.env.ENVIRONMENT ?? 'production',
    otlpEndpoint: process.env.OTEL_EXPORTER_OTLP_ENDPOINT,
    tracingSampleRate: parseFloat(process.env.TRACING_SAMPLE_RATE ?? '0.1'),
  });
}
