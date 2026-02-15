/**
 * STIX Shared Utilities
 * Core utility functions used across all STIX services
 * 
 * @module @stix/shared/utils
 */

import { createHash, randomUUID } from 'node:crypto';

// =============================================================================
// ID GENERATION
// =============================================================================

/**
 * Generate a unique trace ID
 * Format: stix_{uuid}
 */
export function generateTraceId(): string {
  return `stix_${randomUUID()}`;
}

/**
 * Generate a unique event ID
 * Format: evt_{uuid}
 */
export function generateEventId(): string {
  return `evt_${randomUUID()}`;
}

/**
 * Generate a unique request ID
 * Format: req_{uuid}
 */
export function generateRequestId(): string {
  return `req_${randomUUID()}`;
}

/**
 * Generate a unique approval ticket ID
 * Format: appr_{uuid}
 */
export function generateApprovalTicketId(): string {
  return `appr_${randomUUID()}`;
}

// =============================================================================
// CANONICALIZATION
// =============================================================================

/**
 * Canonicalize an object for deterministic hashing/signing
 * - Sorts keys lexicographically at every level
 * - Removes undefined values
 * - Preserves array order
 * - Minifies output (no whitespace)
 * 
 * @param obj Object to canonicalize
 * @returns Canonical JSON string
 */
export function canonicalize(obj: unknown): string {
  return JSON.stringify(sortObjectKeys(obj));
}

/**
 * Recursively sort object keys lexicographically
 */
export function sortObjectKeys(obj: unknown): unknown {
  if (obj === null || obj === undefined) {
    return obj;
  }

  if (Array.isArray(obj)) {
    return obj.map(sortObjectKeys);
  }

  if (typeof obj === 'object' && obj !== null) {
    const sorted: Record<string, unknown> = {};
    const keys = Object.keys(obj as Record<string, unknown>).sort();
    
    for (const key of keys) {
      const value = (obj as Record<string, unknown>)[key];
      // Skip undefined values
      if (value !== undefined) {
        sorted[key] = sortObjectKeys(value);
      }
    }
    
    return sorted;
  }

  return obj;
}

// =============================================================================
// HASHING
// =============================================================================

/**
 * Compute SHA-256 hash with prefix
 * @param data Data to hash (string or buffer)
 * @returns Hash with sha256: prefix
 */
export function sha256(data: string | Buffer): string {
  const hash = createHash('sha256')
    .update(typeof data === 'string' ? Buffer.from(data, 'utf8') : data)
    .digest('hex');
  return `sha256:${hash}`;
}

/**
 * Compute SHA-256 hash without prefix
 * @param data Data to hash
 * @returns Raw hex hash
 */
export function sha256Raw(data: string | Buffer): string {
  return createHash('sha256')
    .update(typeof data === 'string' ? Buffer.from(data, 'utf8') : data)
    .digest('hex');
}

/**
 * Compute hash of canonical JSON
 * @param obj Object to hash
 * @returns Hash with sha256: prefix
 */
export function hashCanonical(obj: unknown): string {
  return sha256(canonicalize(obj));
}

/**
 * Zero hash for chain initialization
 */
export const ZERO_HASH = `sha256:${'0'.repeat(64)}`;

// =============================================================================
// TIMESTAMP UTILITIES
// =============================================================================

/**
 * Get current timestamp in ISO-8601 format with milliseconds
 */
export function isoTimestamp(): string {
  return new Date().toISOString();
}

/**
 * Get current Unix timestamp in seconds
 */
export function unixTimestamp(): number {
  return Math.floor(Date.now() / 1000);
}

/**
 * Parse ISO timestamp to Date
 */
export function parseIsoTimestamp(ts: string): Date {
  return new Date(ts);
}

/**
 * Check if a timestamp has expired
 */
export function isExpired(expiresAt: string | number): boolean {
  const expiry = typeof expiresAt === 'string' 
    ? new Date(expiresAt).getTime() 
    : expiresAt * 1000;
  return Date.now() > expiry;
}

/**
 * Add seconds to current time and return ISO timestamp
 */
export function addSeconds(seconds: number): string {
  return new Date(Date.now() + seconds * 1000).toISOString();
}

// =============================================================================
// BASE64 UTILITIES
// =============================================================================

/**
 * Encode buffer to base64url (URL-safe base64)
 */
export function toBase64Url(buf: Buffer): string {
  return buf
    .toString('base64')
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');
}

/**
 * Decode base64url to buffer
 */
export function fromBase64Url(str: string): Buffer {
  // Add padding if needed
  const padded = str
    .replace(/-/g, '+')
    .replace(/_/g, '/')
    + '==='.slice((str.length + 3) % 4);
  return Buffer.from(padded, 'base64');
}

/**
 * Encode string to base64url
 */
export function stringToBase64Url(str: string): string {
  return toBase64Url(Buffer.from(str, 'utf8'));
}

/**
 * Decode base64url to string
 */
export function base64UrlToString(str: string): string {
  return fromBase64Url(str).toString('utf8');
}

// =============================================================================
// HEX UTILITIES
// =============================================================================

/**
 * Convert hex string to Uint8Array
 */
export function hexToBytes(hex: string): Uint8Array {
  const clean = hex.trim().toLowerCase();
  if (clean.length % 2 !== 0) {
    throw new Error('Invalid hex string length');
  }
  const bytes = new Uint8Array(clean.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(clean.slice(i * 2, i * 2 + 2), 16);
  }
  return bytes;
}

/**
 * Convert Uint8Array to hex string
 */
export function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

// =============================================================================
// VALIDATION UTILITIES
// =============================================================================

/**
 * Check if a string is a valid SHA-256 hash with prefix
 */
export function isValidHash(hash: string): boolean {
  return /^sha256:[a-f0-9]{64}$/.test(hash);
}

/**
 * Check if a string is a valid trace ID
 */
export function isValidTraceId(id: string): boolean {
  return /^stix_[a-f0-9-]{36}$/.test(id);
}

/**
 * Check if a string is a valid event ID
 */
export function isValidEventId(id: string): boolean {
  return /^evt_[a-f0-9-]{36}$/.test(id);
}

/**
 * Check if a string is a valid UUID
 */
export function isValidUuid(id: string): boolean {
  return /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(id);
}

// =============================================================================
// OBJECT UTILITIES
// =============================================================================

/**
 * Deep clone an object
 */
export function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

/**
 * Deep merge objects (last wins)
 */
export function deepMerge<T extends Record<string, unknown>>(...objects: Partial<T>[]): T {
  const result: Record<string, unknown> = {};
  
  for (const obj of objects) {
    for (const key of Object.keys(obj)) {
      const value = obj[key];
      if (value !== undefined) {
        if (
          typeof value === 'object' &&
          value !== null &&
          !Array.isArray(value) &&
          typeof result[key] === 'object' &&
          result[key] !== null &&
          !Array.isArray(result[key])
        ) {
          result[key] = deepMerge(
            result[key] as Record<string, unknown>,
            value as Record<string, unknown>
          );
        } else {
          result[key] = value;
        }
      }
    }
  }
  
  return result as T;
}

/**
 * Pick specified keys from an object
 */
export function pick<T extends Record<string, unknown>, K extends keyof T>(
  obj: T,
  keys: K[]
): Pick<T, K> {
  const result = {} as Pick<T, K>;
  for (const key of keys) {
    if (key in obj) {
      result[key] = obj[key];
    }
  }
  return result;
}

/**
 * Omit specified keys from an object
 */
export function omit<T extends Record<string, unknown>, K extends keyof T>(
  obj: T,
  keys: K[]
): Omit<T, K> {
  const result = { ...obj };
  for (const key of keys) {
    delete result[key];
  }
  return result;
}

// =============================================================================
// STRING UTILITIES
// =============================================================================

/**
 * Truncate a string to a maximum length
 */
export function truncate(str: string, maxLength: number, suffix = '...'): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - suffix.length) + suffix;
}

/**
 * Mask sensitive data (show first/last N characters)
 */
export function mask(str: string, visibleStart = 4, visibleEnd = 4): string {
  if (str.length <= visibleStart + visibleEnd) {
    return '*'.repeat(str.length);
  }
  return (
    str.slice(0, visibleStart) +
    '*'.repeat(str.length - visibleStart - visibleEnd) +
    str.slice(-visibleEnd)
  );
}

/**
 * Mask SSN pattern: XXX-XX-XXXX → ***-**-XXXX
 */
export function maskSsn(str: string): string {
  return str.replace(/\b(\d{3})-(\d{2})-(\d{4})\b/g, '***-**-$3');
}

/**
 * Mask email: user@example.com → u***r@example.com
 */
export function maskEmail(email: string): string {
  const [local, domain] = email.split('@');
  if (!domain || local.length <= 2) return email;
  return `${local[0]}${'*'.repeat(local.length - 2)}${local[local.length - 1]}@${domain}`;
}

// =============================================================================
// ASYNC UTILITIES
// =============================================================================

/**
 * Sleep for specified milliseconds
 */
export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Retry an async operation with exponential backoff
 */
export async function retry<T>(
  fn: () => Promise<T>,
  options: {
    maxAttempts?: number;
    initialDelayMs?: number;
    maxDelayMs?: number;
    factor?: number;
    onRetry?: (error: Error, attempt: number) => void;
  } = {}
): Promise<T> {
  const {
    maxAttempts = 3,
    initialDelayMs = 100,
    maxDelayMs = 5000,
    factor = 2,
    onRetry,
  } = options;

  let lastError: Error;
  let delay = initialDelayMs;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      
      if (attempt === maxAttempts) {
        throw lastError;
      }

      onRetry?.(lastError, attempt);
      await sleep(delay);
      delay = Math.min(delay * factor, maxDelayMs);
    }
  }

  throw lastError!;
}

/**
 * Timeout wrapper for promises
 */
export function withTimeout<T>(
  promise: Promise<T>,
  timeoutMs: number,
  message = 'Operation timed out'
): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(message));
    }, timeoutMs);

    promise
      .then(result => {
        clearTimeout(timer);
        resolve(result);
      })
      .catch(error => {
        clearTimeout(timer);
        reject(error);
      });
  });
}

// =============================================================================
// ENVIRONMENT UTILITIES
// =============================================================================

/**
 * Get environment variable or throw
 */
export function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Required environment variable ${name} is not set`);
  }
  return value;
}

/**
 * Get environment variable with default
 */
export function getEnv(name: string, defaultValue: string): string {
  return process.env[name] ?? defaultValue;
}

/**
 * Get environment variable as number
 */
export function getEnvNumber(name: string, defaultValue: number): number {
  const value = process.env[name];
  if (!value) return defaultValue;
  const num = parseInt(value, 10);
  return isNaN(num) ? defaultValue : num;
}

/**
 * Get environment variable as boolean
 */
export function getEnvBool(name: string, defaultValue: boolean): boolean {
  const value = process.env[name];
  if (!value) return defaultValue;
  return value.toLowerCase() === 'true' || value === '1';
}

/**
 * Check if running in production
 */
export function isProduction(): boolean {
  return process.env.NODE_ENV === 'production';
}

/**
 * Check if running in development
 */
export function isDevelopment(): boolean {
  return process.env.NODE_ENV === 'development' || !process.env.NODE_ENV;
}
