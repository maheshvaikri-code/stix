/**
 * STIX Tracing Module
 * OpenTelemetry-based distributed tracing for STIX services
 */

import { NodeSDK } from '@opentelemetry/sdk-node';
import { resourceFromAttributes } from '@opentelemetry/resources';
import {
  SEMRESATTRS_SERVICE_NAME,
  SEMRESATTRS_SERVICE_VERSION,
  SEMRESATTRS_DEPLOYMENT_ENVIRONMENT,
} from '@opentelemetry/semantic-conventions';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http';
import { PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';
import { HttpInstrumentation } from '@opentelemetry/instrumentation-http';
import { FastifyInstrumentation } from '@opentelemetry/instrumentation-fastify';
import { PgInstrumentation } from '@opentelemetry/instrumentation-pg';
import {
  trace,
  context,
  SpanKind,
  SpanStatusCode,
  Span,
  Tracer,
  Context,
  propagation,
} from '@opentelemetry/api';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-node';

/**
 * Tracing configuration
 */
export interface TracingConfig {
  /** Service name */
  serviceName: string;

  /** Service version */
  serviceVersion?: string;

  /** Deployment environment */
  environment?: string;

  /** OTLP exporter endpoint */
  otlpEndpoint?: string;

  /** Sample rate (0.0 to 1.0) */
  sampleRate?: number;

  /** Enable HTTP instrumentation */
  enableHttpInstrumentation?: boolean;

  /** Enable Fastify instrumentation */
  enableFastifyInstrumentation?: boolean;

  /** Enable PostgreSQL instrumentation */
  enablePgInstrumentation?: boolean;

  /** Additional resource attributes */
  resourceAttributes?: Record<string, string>;
}

/**
 * STIX Tracing - OpenTelemetry integration
 */
export class StixTracing {
  private sdk: NodeSDK | null = null;
  private tracer: Tracer;
  private readonly serviceName: string;

  constructor(private readonly config: TracingConfig) {
    this.serviceName = config.serviceName;
    this.tracer = trace.getTracer(config.serviceName, config.serviceVersion);
  }

  /**
   * Initialize tracing SDK
   * Must be called before any other imports in your application
   */
  async start(): Promise<void> {
    const instrumentations = [];

    if (this.config.enableHttpInstrumentation !== false) {
      instrumentations.push(new HttpInstrumentation());
    }

    if (this.config.enableFastifyInstrumentation !== false) {
      instrumentations.push(new FastifyInstrumentation());
    }

    if (this.config.enablePgInstrumentation !== false) {
      instrumentations.push(new PgInstrumentation());
    }

    const resource = resourceFromAttributes({
      [SEMRESATTRS_SERVICE_NAME]: this.config.serviceName,
      [SEMRESATTRS_SERVICE_VERSION]: this.config.serviceVersion ?? '0.1.15',
      [SEMRESATTRS_DEPLOYMENT_ENVIRONMENT]: this.config.environment ?? 'production',
      ...this.config.resourceAttributes,
    });

    const traceExporter = this.config.otlpEndpoint
      ? new OTLPTraceExporter({
          url: `${this.config.otlpEndpoint}/v1/traces`,
        })
      : undefined;

    const metricExporter = this.config.otlpEndpoint
      ? new OTLPMetricExporter({
          url: `${this.config.otlpEndpoint}/v1/metrics`,
        })
      : undefined;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const sdkOptions: any = {
      resource,
      traceExporter,
      instrumentations,
    };

    if (metricExporter) {
      sdkOptions.metricReader = new PeriodicExportingMetricReader({
        exporter: metricExporter,
        exportIntervalMillis: 60000,
      });
    }

    if (traceExporter) {
      sdkOptions.spanProcessors = [new BatchSpanProcessor(traceExporter)];
    }

    this.sdk = new NodeSDK(sdkOptions);

    await this.sdk.start();

    // Update tracer reference
    this.tracer = trace.getTracer(this.serviceName, this.config.serviceVersion);
  }

  /**
   * Shutdown tracing SDK
   */
  async shutdown(): Promise<void> {
    if (this.sdk) {
      await this.sdk.shutdown();
    }
  }

  /**
   * Get the tracer instance
   */
  getTracer(): Tracer {
    return this.tracer;
  }

  /**
   * Create a new span for authorization
   */
  startAuthorizationSpan(params: {
    action: string;
    actorId: string;
    resourceType: string;
    traceId?: string;
  }): Span {
    return this.tracer.startSpan('stix.authorize', {
      kind: SpanKind.INTERNAL,
      attributes: {
        'stix.action': params.action,
        'stix.actor.id': params.actorId,
        'stix.resource.type': params.resourceType,
        'stix.trace_id': params.traceId,
      },
    });
  }

  /**
   * Create a new span for evidence recording
   */
  startEvidenceSpan(params: {
    traceId: string;
    eventId: string;
    decision: string;
  }): Span {
    return this.tracer.startSpan('stix.evidence.write', {
      kind: SpanKind.INTERNAL,
      attributes: {
        'stix.trace_id': params.traceId,
        'stix.event_id': params.eventId,
        'stix.decision': params.decision,
      },
    });
  }

  /**
   * Create a new span for policy evaluation
   */
  startPolicySpan(params: {
    policyId: string;
    action: string;
    resourceType: string;
  }): Span {
    return this.tracer.startSpan('stix.policy.evaluate', {
      kind: SpanKind.INTERNAL,
      attributes: {
        'stix.policy.id': params.policyId,
        'stix.action': params.action,
        'stix.resource.type': params.resourceType,
      },
    });
  }

  /**
   * Create a new span for approval operations
   */
  startApprovalSpan(params: {
    operation: 'create' | 'resolve' | 'poll';
    ticketId?: string;
    traceId?: string;
  }): Span {
    return this.tracer.startSpan(`stix.approval.${params.operation}`, {
      kind: SpanKind.INTERNAL,
      attributes: {
        'stix.approval.operation': params.operation,
        'stix.approval.ticket_id': params.ticketId,
        'stix.trace_id': params.traceId,
      },
    });
  }

  /**
   * Wrap an async function with a span
   */
  async withSpan<T>(
    name: string,
    fn: (span: Span) => Promise<T>,
    options?: {
      kind?: SpanKind;
      attributes?: Record<string, string | number | boolean>;
    }
  ): Promise<T> {
    const span = this.tracer.startSpan(name, {
      kind: options?.kind ?? SpanKind.INTERNAL,
      attributes: options?.attributes,
    });

    try {
      const result = await context.with(
        trace.setSpan(context.active(), span),
        () => fn(span)
      );
      span.setStatus({ code: SpanStatusCode.OK });
      return result;
    } catch (error) {
      span.setStatus({
        code: SpanStatusCode.ERROR,
        message: error instanceof Error ? error.message : 'Unknown error',
      });
      span.recordException(error instanceof Error ? error : new Error(String(error)));
      throw error;
    } finally {
      span.end();
    }
  }

  /**
   * Add event to current span
   */
  addEvent(name: string, attributes?: Record<string, string | number | boolean>): void {
    const span = trace.getActiveSpan();
    if (span) {
      span.addEvent(name, attributes);
    }
  }

  /**
   * Set attribute on current span
   */
  setAttribute(key: string, value: string | number | boolean): void {
    const span = trace.getActiveSpan();
    if (span) {
      span.setAttribute(key, value);
    }
  }

  /**
   * Record exception on current span
   */
  recordException(error: Error): void {
    const span = trace.getActiveSpan();
    if (span) {
      span.recordException(error);
      span.setStatus({ code: SpanStatusCode.ERROR, message: error.message });
    }
  }

  /**
   * Extract trace context from headers
   */
  extractContext(headers: Record<string, string | string[] | undefined>): Context {
    return propagation.extract(context.active(), headers);
  }

  /**
   * Inject trace context into headers
   */
  injectContext(headers: Record<string, string>): void {
    propagation.inject(context.active(), headers);
  }

  /**
   * Get current trace ID
   */
  getCurrentTraceId(): string | undefined {
    const span = trace.getActiveSpan();
    if (span) {
      return span.spanContext().traceId;
    }
    return undefined;
  }

  /**
   * Get current span ID
   */
  getCurrentSpanId(): string | undefined {
    const span = trace.getActiveSpan();
    if (span) {
      return span.spanContext().spanId;
    }
    return undefined;
  }
}

/**
 * Create a traced function wrapper
 */
export function traced<T extends (...args: unknown[]) => Promise<unknown>>(
  tracer: Tracer,
  name: string,
  fn: T,
  options?: {
    kind?: SpanKind;
    getAttributes?: (...args: Parameters<T>) => Record<string, string | number | boolean>;
  }
): T {
  return (async (...args: Parameters<T>) => {
    const attributes = options?.getAttributes?.(...args);
    const span = tracer.startSpan(name, {
      kind: options?.kind ?? SpanKind.INTERNAL,
      attributes,
    });

    try {
      const result = await context.with(
        trace.setSpan(context.active(), span),
        () => fn(...args)
      );
      span.setStatus({ code: SpanStatusCode.OK });
      return result;
    } catch (error) {
      span.setStatus({
        code: SpanStatusCode.ERROR,
        message: error instanceof Error ? error.message : 'Unknown error',
      });
      span.recordException(error instanceof Error ? error : new Error(String(error)));
      throw error;
    } finally {
      span.end();
    }
  }) as T;
}

/**
 * Decorator for tracing class methods
 */
export function Traced(name?: string, options?: { kind?: SpanKind }) {
  return function (
    _target: unknown,
    propertyKey: string,
    descriptor: PropertyDescriptor
  ): PropertyDescriptor {
    const originalMethod = descriptor.value;
    const spanName = name ?? propertyKey;

    descriptor.value = async function (this: { tracer?: Tracer }, ...args: unknown[]) {
      const tracer = this.tracer ?? trace.getTracer('stix');
      const span = tracer.startSpan(spanName, {
        kind: options?.kind ?? SpanKind.INTERNAL,
      });

      try {
        const result = await context.with(
          trace.setSpan(context.active(), span),
          () => originalMethod.apply(this, args)
        );
        span.setStatus({ code: SpanStatusCode.OK });
        return result;
      } catch (error) {
        span.setStatus({
          code: SpanStatusCode.ERROR,
          message: error instanceof Error ? error.message : 'Unknown error',
        });
        span.recordException(error instanceof Error ? error : new Error(String(error)));
        throw error;
      } finally {
        span.end();
      }
    };

    return descriptor;
  };
}

/**
 * Create correlation ID middleware for Fastify
 */
export function createTracingPlugin(tracing: StixTracing) {
  return async function tracingPlugin(
    fastify: {
      addHook: (hook: string, handler: (...args: any[]) => Promise<void>) => void;
      decorateRequest: (name: string, value: unknown) => void;
    },
  ): Promise<void> {
    fastify.decorateRequest('traceId', null);
    fastify.decorateRequest('spanId', null);

    fastify.addHook('onRequest', async (request: { headers: Record<string, string>; traceId?: string; spanId?: string }) => {
      const ctx = tracing.extractContext(request.headers);
      context.with(ctx, () => {
        request.traceId = tracing.getCurrentTraceId();
        request.spanId = tracing.getCurrentSpanId();
      });
    });

    fastify.addHook('onSend', async (_request: any, reply: { header: (name: string, value: string) => void }) => {
      const headers: Record<string, string> = {};
      tracing.injectContext(headers);
      for (const [key, value] of Object.entries(headers)) {
        reply.header(key, value);
      }
    });
  };
}
