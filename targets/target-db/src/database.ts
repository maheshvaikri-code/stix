/**
 * STIX Target DB - Database Service
 *
 * @module @stix/target-db
 */

import { z } from 'zod';
import { isoTimestamp, type Logger } from '@stix/shared';
import type { Config } from './config.js';

// =============================================================================
// QUERY REQUEST SCHEMA
// =============================================================================

export const QueryRequestSchema = z.object({
  sql: z.string().min(1).max(100000),
  params: z.array(z.unknown()).optional(),
  timeout: z.number().optional(),
  maxRows: z.number().optional(),
  metadata: z.record(z.unknown()).optional(),
});

export type QueryRequest = z.infer<typeof QueryRequestSchema>;

// =============================================================================
// QUERY RESULT
// =============================================================================

export interface QueryResult {
  success: boolean;
  operation: 'SELECT' | 'INSERT' | 'UPDATE' | 'DELETE' | 'DDL' | 'OTHER';
  rows?: Record<string, unknown>[];
  rowCount: number;
  affectedRows?: number;
  insertId?: string | number;
  fields?: Array<{ name: string; type: string }>;
  timestamp: string;
  duration_ms: number;
  error?: {
    code: string;
    message: string;
  };
}

// =============================================================================
// SQL PARSER (BASIC)
// =============================================================================

type QueryOperation = 'SELECT' | 'INSERT' | 'UPDATE' | 'DELETE' | 'DDL' | 'OTHER';

interface ParsedQuery {
  operation: QueryOperation;
  tables: string[];
  isDdl: boolean;
  isTruncate: boolean;
  isDrop: boolean;
}

function parseQuery(sql: string): ParsedQuery {
  const normalized = sql.trim().toUpperCase();
  const firstWord = normalized.split(/\s+/)[0];

  let operation: QueryOperation = 'OTHER';
  const tables: string[] = [];
  let isDdl = false;
  let isTruncate = false;
  let isDrop = false;

  switch (firstWord) {
    case 'SELECT':
      operation = 'SELECT';
      // Extract tables from FROM clause
      const fromMatch = normalized.match(/FROM\s+([^\s,;]+)/);
      if (fromMatch) {
        tables.push(fromMatch[1].toLowerCase());
      }
      break;

    case 'INSERT':
      operation = 'INSERT';
      const intoMatch = normalized.match(/INTO\s+([^\s(]+)/);
      if (intoMatch) {
        tables.push(intoMatch[1].toLowerCase());
      }
      break;

    case 'UPDATE':
      operation = 'UPDATE';
      const updateMatch = normalized.match(/UPDATE\s+([^\s]+)/);
      if (updateMatch) {
        tables.push(updateMatch[1].toLowerCase());
      }
      break;

    case 'DELETE':
      operation = 'DELETE';
      const deleteMatch = normalized.match(/FROM\s+([^\s]+)/);
      if (deleteMatch) {
        tables.push(deleteMatch[1].toLowerCase());
      }
      break;

    case 'CREATE':
    case 'ALTER':
      operation = 'DDL';
      isDdl = true;
      break;

    case 'DROP':
      operation = 'DDL';
      isDdl = true;
      isDrop = true;
      break;

    case 'TRUNCATE':
      operation = 'DELETE';
      isTruncate = true;
      const truncMatch = normalized.match(/TRUNCATE\s+(?:TABLE\s+)?([^\s]+)/);
      if (truncMatch) {
        tables.push(truncMatch[1].toLowerCase());
      }
      break;
  }

  return { operation, tables, isDdl, isTruncate, isDrop };
}

// =============================================================================
// DATABASE SERVICE
// =============================================================================

/**
 * Abstract database service interface
 */
export interface DatabaseDriver {
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  query(sql: string, params?: unknown[]): Promise<{
    rows: Record<string, unknown>[];
    rowCount: number;
    affectedRows?: number;
    insertId?: string | number;
    fields?: Array<{ name: string; type: string }>;
  }>;
  healthCheck(): Promise<boolean>;
}

/**
 * Protected database service
 */
export class DatabaseService {
  private readonly config: Config;
  private readonly logger: Logger;
  private driver: DatabaseDriver | null = null;

  constructor(config: Config, logger: Logger) {
    this.config = config;
    this.logger = logger;
  }

  /**
   * Initialize database connection
   */
  async initialize(): Promise<void> {
    // Create appropriate driver based on config
    switch (this.config.database.type) {
      case 'sqlite':
        this.driver = new SQLiteDriver(this.config, this.logger);
        break;
      case 'postgres':
        this.driver = new PostgresDriver(this.config, this.logger);
        break;
      case 'mysql':
        this.driver = new MySQLDriver(this.config, this.logger);
        break;
      default:
        throw new Error(`Unsupported database type: ${this.config.database.type}`);
    }

    await this.driver.connect();
    this.logger.info('Database connection established', {
      type: this.config.database.type,
      database: this.config.database.database,
    });
  }

  /**
   * Execute a query
   */
  async execute(
    request: QueryRequest,
    traceId: string
  ): Promise<QueryResult> {
    const startTime = Date.now();

    if (!this.driver) {
      return this.errorResult('NOT_INITIALIZED', 'Database not initialized', startTime);
    }

    try {
      // Parse and validate query
      const parsed = parseQuery(request.sql);
      const validationError = this.validateQuery(parsed);
      if (validationError) {
        return this.errorResult(validationError.code, validationError.message, startTime);
      }

      // Log query (redact sensitive params)
      if (this.config.audit.logQueries) {
        this.logger.info('Executing SQL query', {
          trace_id: traceId,
          operation: parsed.operation,
          tables: parsed.tables,
          sql: request.sql.substring(0, 200),
        });
      }

      // Execute query with timeout
      const timeout = Math.min(
        request.timeout || this.config.security.queryTimeout,
        this.config.security.queryTimeout
      );

      const result = await Promise.race([
        this.driver.query(request.sql, request.params),
        new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('Query timeout')), timeout)
        ),
      ]);

      // Apply row limit
      const maxRows = Math.min(
        request.maxRows || this.config.security.maxRowsPerQuery,
        this.config.security.maxRowsPerQuery
      );

      const rows = result.rows.slice(0, maxRows);
      const duration_ms = Date.now() - startTime;

      this.logger.info('Query executed successfully', {
        trace_id: traceId,
        operation: parsed.operation,
        row_count: rows.length,
        affected_rows: result.affectedRows,
        duration_ms,
      });

      return {
        success: true,
        operation: parsed.operation,
        rows: parsed.operation === 'SELECT' ? rows : undefined,
        rowCount: rows.length,
        affectedRows: result.affectedRows,
        insertId: result.insertId,
        fields: result.fields,
        timestamp: isoTimestamp(),
        duration_ms,
      };
    } catch (error) {
      const err = error as Error & { code?: string };
      const duration_ms = Date.now() - startTime;

      this.logger.error('Query execution failed', {
        trace_id: traceId,
        sql: request.sql.substring(0, 100),
        duration_ms,
      }, err);

      return this.errorResult(
        err.code || 'QUERY_FAILED',
        err.message,
        startTime
      );
    }
  }

  /**
   * Validate a query against security rules
   */
  private validateQuery(parsed: ParsedQuery): { code: string; message: string } | null {
    // Check DDL restrictions
    if (parsed.isDdl && !this.config.security.allowDdl) {
      return { code: 'DDL_NOT_ALLOWED', message: 'DDL statements are not allowed' };
    }

    if (parsed.isDrop && !this.config.security.allowDrop) {
      return { code: 'DROP_NOT_ALLOWED', message: 'DROP statements are not allowed' };
    }

    if (parsed.isTruncate && !this.config.security.allowTruncate) {
      return { code: 'TRUNCATE_NOT_ALLOWED', message: 'TRUNCATE statements are not allowed' };
    }

    // Check blocked tables
    if (this.config.security.blockedTables?.length) {
      for (const table of parsed.tables) {
        if (this.config.security.blockedTables.includes(table)) {
          return { code: 'TABLE_BLOCKED', message: `Access to table '${table}' is blocked` };
        }
      }
    }

    // Check allowed tables
    if (this.config.security.allowedTables?.length) {
      for (const table of parsed.tables) {
        if (!this.config.security.allowedTables.includes(table)) {
          return { code: 'TABLE_NOT_ALLOWED', message: `Table '${table}' is not in allowed list` };
        }
      }
    }

    return null;
  }

  /**
   * Create an error result
   */
  private errorResult(code: string, message: string, startTime: number): QueryResult {
    return {
      success: false,
      operation: 'OTHER',
      rowCount: 0,
      timestamp: isoTimestamp(),
      duration_ms: Date.now() - startTime,
      error: { code, message },
    };
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ healthy: boolean; message?: string }> {
    if (!this.driver) {
      return { healthy: false, message: 'Not initialized' };
    }

    try {
      const healthy = await this.driver.healthCheck();
      return { healthy };
    } catch (error) {
      return { healthy: false, message: (error as Error).message };
    }
  }

  /**
   * Close database connection
   */
  async close(): Promise<void> {
    if (this.driver) {
      await this.driver.disconnect();
      this.driver = null;
    }
  }
}

// =============================================================================
// SQLITE DRIVER
// =============================================================================

class SQLiteDriver implements DatabaseDriver {
  private db: any = null;
  private readonly config: Config;
  private readonly logger: Logger;

  constructor(config: Config, logger: Logger) {
    this.config = config;
    this.logger = logger;
  }

  async connect(): Promise<void> {
    // Dynamic import to avoid loading if not used
    const Database = (await import('better-sqlite3')).default;
    this.db = new Database(this.config.database.database);
  }

  async disconnect(): Promise<void> {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
  }

  async query(sql: string, params?: unknown[]): Promise<{
    rows: Record<string, unknown>[];
    rowCount: number;
    affectedRows?: number;
    insertId?: string | number;
    fields?: Array<{ name: string; type: string }>;
  }> {
    const stmt = this.db.prepare(sql);
    const isSelect = sql.trim().toUpperCase().startsWith('SELECT');

    if (isSelect) {
      const rows = params ? stmt.all(...params) : stmt.all();
      return {
        rows,
        rowCount: rows.length,
      };
    } else {
      const result = params ? stmt.run(...params) : stmt.run();
      return {
        rows: [],
        rowCount: 0,
        affectedRows: result.changes,
        insertId: result.lastInsertRowid,
      };
    }
  }

  async healthCheck(): Promise<boolean> {
    if (!this.db) return false;
    try {
      this.db.prepare('SELECT 1').get();
      return true;
    } catch {
      return false;
    }
  }
}

// =============================================================================
// POSTGRES DRIVER (stub - requires pg package)
// =============================================================================

class PostgresDriver implements DatabaseDriver {
  private pool: any = null;
  private readonly config: Config;
  private readonly logger: Logger;

  constructor(config: Config, logger: Logger) {
    this.config = config;
    this.logger = logger;
  }

  async connect(): Promise<void> {
    const { Pool } = await import('pg');
    this.pool = new Pool({
      host: this.config.database.host,
      port: this.config.database.port,
      database: this.config.database.database,
      user: this.config.database.user,
      password: this.config.database.password,
      ssl: this.config.database.ssl ? { rejectUnauthorized: false } : undefined,
      min: this.config.database.poolMin,
      max: this.config.database.poolMax,
      connectionTimeoutMillis: this.config.database.connectionTimeout,
      idleTimeoutMillis: this.config.database.idleTimeout,
    });
  }

  async disconnect(): Promise<void> {
    if (this.pool) {
      await this.pool.end();
      this.pool = null;
    }
  }

  async query(sql: string, params?: unknown[]): Promise<{
    rows: Record<string, unknown>[];
    rowCount: number;
    affectedRows?: number;
    fields?: Array<{ name: string; type: string }>;
  }> {
    const result = await this.pool.query(sql, params);
    return {
      rows: result.rows,
      rowCount: result.rowCount || result.rows.length,
      affectedRows: result.rowCount,
      fields: result.fields?.map((f: any) => ({ name: f.name, type: f.dataTypeID?.toString() })),
    };
  }

  async healthCheck(): Promise<boolean> {
    if (!this.pool) return false;
    try {
      await this.pool.query('SELECT 1');
      return true;
    } catch {
      return false;
    }
  }
}

// =============================================================================
// MYSQL DRIVER (stub - requires mysql2 package)
// =============================================================================

class MySQLDriver implements DatabaseDriver {
  private pool: any = null;
  private readonly config: Config;
  private readonly logger: Logger;

  constructor(config: Config, logger: Logger) {
    this.config = config;
    this.logger = logger;
  }

  async connect(): Promise<void> {
    const mysql = await import('mysql2/promise');
    this.pool = mysql.createPool({
      host: this.config.database.host,
      port: this.config.database.port,
      database: this.config.database.database,
      user: this.config.database.user,
      password: this.config.database.password,
      ssl: this.config.database.ssl ? {} : undefined,
      waitForConnections: true,
      connectionLimit: this.config.database.poolMax,
      queueLimit: 0,
      connectTimeout: this.config.database.connectionTimeout,
    });
  }

  async disconnect(): Promise<void> {
    if (this.pool) {
      await this.pool.end();
      this.pool = null;
    }
  }

  async query(sql: string, params?: unknown[]): Promise<{
    rows: Record<string, unknown>[];
    rowCount: number;
    affectedRows?: number;
    insertId?: string | number;
    fields?: Array<{ name: string; type: string }>;
  }> {
    const [rows, fields] = await this.pool.execute(sql, params);

    if (Array.isArray(rows)) {
      return {
        rows: rows as Record<string, unknown>[],
        rowCount: rows.length,
        fields: (fields as any[])?.map((f: any) => ({ name: f.name, type: f.type?.toString() })),
      };
    } else {
      const result = rows as any;
      return {
        rows: [],
        rowCount: 0,
        affectedRows: result.affectedRows,
        insertId: result.insertId,
      };
    }
  }

  async healthCheck(): Promise<boolean> {
    if (!this.pool) return false;
    try {
      await this.pool.execute('SELECT 1');
      return true;
    } catch {
      return false;
    }
  }
}

// =============================================================================
// MOCK DATABASE SERVICE
// =============================================================================

export class MockDatabaseService extends DatabaseService {
  public queries: Array<{ request: QueryRequest; traceId: string }> = [];

  override async initialize(): Promise<void> {
    // No-op for mock
  }

  override async execute(
    request: QueryRequest,
    traceId: string
  ): Promise<QueryResult> {
    this.queries.push({ request, traceId });

    return {
      success: true,
      operation: 'SELECT',
      rows: [{ id: 1, name: 'mock' }],
      rowCount: 1,
      timestamp: isoTimestamp(),
      duration_ms: 1,
    };
  }

  override async healthCheck(): Promise<{ healthy: boolean; message?: string }> {
    return { healthy: true };
  }

  override async close(): Promise<void> {
    this.queries = [];
  }
}
