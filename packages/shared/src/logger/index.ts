/**
 * STIX Logger
 * Structured logging wrapper for enterprise observability
 * 
 * @module @stix/shared/logger
 */

import { LOG_LEVELS, LOG_LEVEL_PRIORITY } from '../constants/index.js';

// =============================================================================
// TYPES
// =============================================================================

export type LogLevel = keyof typeof LOG_LEVELS;

export interface LogContext {
  /** Trace ID for correlation */
  trace_id?: string;
  /** Request ID */
  request_id?: string;
  /** Service name */
  service?: string;
  /** Operation name */
  operation?: string;
  /** Actor ID */
  actor_id?: string;
  /** Tenant ID */
  tenant_id?: string;
  /** Duration in milliseconds */
  duration_ms?: number;
  /** Additional fields */
  [key: string]: unknown;
}

export interface LogEntry {
  level: string;
  message: string;
  timestamp: string;
  service: string;
  context?: LogContext;
  error?: {
    name: string;
    message: string;
    stack?: string;
    code?: string;
  };
}

export interface LoggerConfig {
  /** Service name */
  service: string;
  /** Minimum log level */
  level: LogLevel;
  /** Pretty print (development) */
  pretty?: boolean;
  /** Redact sensitive fields */
  redact?: string[];
  /** Default context */
  defaultContext?: LogContext;
}

// =============================================================================
// SENSITIVE FIELD PATTERNS
// =============================================================================

const DEFAULT_REDACT_PATTERNS = [
  'password',
  'secret',
  'token',
  'api_key',
  'apikey',
  'authorization',
  'credential',
  'private_key',
  'ssn',
  'social_security',
  'credit_card',
  'card_number',
];

// =============================================================================
// LOGGER CLASS
// =============================================================================

export class Logger {
  private readonly config: Required<LoggerConfig>;
  private readonly levelPriority: number;
  private childContext: LogContext = {};

  constructor(config: LoggerConfig) {
    this.config = {
      service: config.service,
      level: config.level,
      pretty: config.pretty ?? process.env.NODE_ENV !== 'production',
      redact: [...DEFAULT_REDACT_PATTERNS, ...(config.redact ?? [])],
      defaultContext: config.defaultContext ?? {},
    };
    this.levelPriority = LOG_LEVEL_PRIORITY[this.config.level];
  }

  /**
   * Create child logger with additional context
   */
  child(context: LogContext): Logger {
    const child = new Logger(this.config);
    child.childContext = { ...this.childContext, ...context };
    return child;
  }

  /**
   * Log at error level
   */
  error(message: string, context?: LogContext, error?: Error): void {
    this.log('error', message, context, error);
  }

  /**
   * Log at warn level
   */
  warn(message: string, context?: LogContext): void {
    this.log('warn', message, context);
  }

  /**
   * Log at info level
   */
  info(message: string, context?: LogContext): void {
    this.log('info', message, context);
  }

  /**
   * Log at http level
   */
  http(message: string, context?: LogContext): void {
    this.log('http', message, context);
  }

  /**
   * Log at debug level
   */
  debug(message: string, context?: LogContext): void {
    this.log('debug', message, context);
  }

  /**
   * Log at trace level
   */
  trace(message: string, context?: LogContext): void {
    this.log('trace', message, context);
  }

  /**
   * Core log method
   */
  private log(level: LogLevel, message: string, context?: LogContext, error?: Error): void {
    const priority = LOG_LEVEL_PRIORITY[level];
    if (priority > this.levelPriority) {
      return;
    }

    const entry: LogEntry = {
      level,
      message,
      timestamp: new Date().toISOString(),
      service: this.config.service,
    };

    // Merge contexts
    const mergedContext = {
      ...this.config.defaultContext,
      ...this.childContext,
      ...context,
    };

    if (Object.keys(mergedContext).length > 0) {
      entry.context = this.redactSensitive(mergedContext);
    }

    if (error) {
      entry.error = {
        name: error.name,
        message: error.message,
        stack: error.stack,
        code: (error as { code?: string }).code,
      };
    }

    this.output(entry);
  }

  /**
   * Output log entry
   */
  private output(entry: LogEntry): void {
    const output = this.config.pretty
      ? this.formatPretty(entry)
      : JSON.stringify(entry);

    if (entry.level === 'error') {
      console.error(output);
    } else if (entry.level === 'warn') {
      console.warn(output);
    } else {
      console.log(output);
    }
  }

  /**
   * Pretty format for development
   */
  private formatPretty(entry: LogEntry): string {
    const levelColors: Record<string, string> = {
      error: '\x1b[31m', // red
      warn: '\x1b[33m',  // yellow
      info: '\x1b[36m',  // cyan
      http: '\x1b[35m',  // magenta
      debug: '\x1b[90m', // gray
      trace: '\x1b[90m', // gray
    };
    const reset = '\x1b[0m';
    const color = levelColors[entry.level] || '';
    
    const time = new Date(entry.timestamp).toLocaleTimeString();
    const level = entry.level.toUpperCase().padEnd(5);
    
    let line = `${color}[${time}] ${level}${reset} ${entry.message}`;
    
    if (entry.context?.trace_id) {
      line += ` ${'\x1b[90m'}trace=${entry.context.trace_id}${reset}`;
    }
    
    if (entry.context?.duration_ms) {
      line += ` ${'\x1b[90m'}${entry.context.duration_ms}ms${reset}`;
    }
    
    if (entry.error) {
      line += `\n  ${'\x1b[31m'}Error: ${entry.error.message}${reset}`;
      if (entry.error.stack && this.config.level === 'debug') {
        line += `\n${entry.error.stack}`;
      }
    }
    
    return line;
  }

  /**
   * Redact sensitive fields
   */
  private redactSensitive(obj: LogContext): LogContext {
    return this.deepRedact(obj) as LogContext;
  }

  private deepRedact(value: unknown): unknown {
    if (value === null || value === undefined) {
      return value;
    }

    if (Array.isArray(value)) {
      return value.map(item => this.deepRedact(item));
    }

    if (typeof value === 'object') {
      const result: Record<string, unknown> = {};
      for (const [key, val] of Object.entries(value as Record<string, unknown>)) {
        const lowerKey = key.toLowerCase();
        const shouldRedact = this.config.redact.some(pattern => 
          lowerKey.includes(pattern.toLowerCase())
        );
        result[key] = shouldRedact ? '[REDACTED]' : this.deepRedact(val);
      }
      return result;
    }

    return value;
  }
}

// =============================================================================
// FACTORY FUNCTIONS
// =============================================================================

/**
 * Create logger for a service
 */
export function createLogger(config: LoggerConfig): Logger {
  return new Logger(config);
}

/**
 * Create logger from environment
 */
export function createLoggerFromEnv(service: string): Logger {
  const level = (process.env.LOG_LEVEL as LogLevel) || 'info';
  const pretty = process.env.LOG_PRETTY === 'true' || process.env.NODE_ENV !== 'production';
  
  return new Logger({
    service,
    level,
    pretty,
  });
}

// =============================================================================
// REQUEST LOGGING
// =============================================================================

export interface RequestLogContext extends LogContext {
  method: string;
  path: string;
  status_code: number;
  duration_ms: number;
  user_agent?: string;
  ip?: string;
}

/**
 * Log HTTP request
 */
export function logRequest(logger: Logger, context: RequestLogContext): void {
  const level = context.status_code >= 500 ? 'error' :
                context.status_code >= 400 ? 'warn' : 'http';
  
  const message = `${context.method} ${context.path} ${context.status_code}`;
  
  logger[level](message, context);
}

// =============================================================================
// AUDIT LOGGING
// =============================================================================

export interface AuditLogContext extends LogContext {
  event_type: string;
  actor_id: string;
  actor_type: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  decision?: string;
  reason_code?: string;
}

/**
 * Log audit event
 */
export function logAudit(logger: Logger, context: AuditLogContext): void {
  const message = `AUDIT: ${context.actor_type}:${context.actor_id} ${context.action} ${context.resource_type}`;
  logger.info(message, { ...context, event_type: 'audit' });
}

// =============================================================================
// METRICS LOGGING
// =============================================================================

export interface MetricLogContext extends LogContext {
  metric_name: string;
  metric_value: number;
  metric_type: 'counter' | 'gauge' | 'histogram';
  labels?: Record<string, string>;
}

/**
 * Log metric
 */
export function logMetric(logger: Logger, context: MetricLogContext): void {
  logger.trace(`METRIC: ${context.metric_name}=${context.metric_value}`, {
    ...context,
    event_type: 'metric',
  });
}
