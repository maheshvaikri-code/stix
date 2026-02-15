/**
 * Cache Service
 * Redis-based caching with in-memory fallback
 */

import { type Logger } from '@stix/shared';
import type { Config } from '../config/index.js';

// =============================================================================
// CACHE SERVICE INTERFACE
// =============================================================================

export interface CacheService {
  get<T>(key: string): Promise<T | null>;
  set<T>(key: string, value: T, ttlSeconds?: number): Promise<void>;
  delete(key: string): Promise<void>;
  clear(): Promise<void>;
  health(): Promise<boolean>;
}

// =============================================================================
// REDIS CACHE SERVICE
// =============================================================================

export class RedisCacheService implements CacheService {
  private readonly config: Config;
  private readonly logger: Logger;
  private client: any = null; // Type depends on ioredis import
  private readonly keyPrefix: string;

  constructor(config: Config, logger: Logger) {
    this.config = config;
    this.logger = logger.child({ component: 'RedisCacheService' });
    this.keyPrefix = config.redis.keyPrefix;
  }

  /**
   * Initialize Redis connection
   */
  async initialize(): Promise<void> {
    if (!this.config.redis.enabled) {
      this.logger.info('Redis disabled, using in-memory cache');
      return;
    }

    try {
      // Dynamic import to handle environments without ioredis
      const redisModule = await import('ioredis');
      const Redis: any = (redisModule as any).default ?? (redisModule as any);
      
      if (this.config.redis.url) {
        this.client = new Redis(this.config.redis.url);
      } else {
        this.client = new Redis({
          host: this.config.redis.host,
          port: this.config.redis.port,
          password: this.config.redis.password || undefined,
          db: this.config.redis.db,
          lazyConnect: true,
          retryStrategy: (times: number) => {
            if (times > 3) return null;
            return Math.min(times * 100, 3000);
          },
        });
      }

      this.client.on('error', (err: Error) => {
        this.logger.error('Redis error', {}, err);
      });

      this.client.on('connect', () => {
        this.logger.info('Redis connected');
      });

      await this.client.connect();
    } catch (error) {
      this.logger.warn('Failed to connect to Redis, using in-memory cache', {
        error: (error as Error).message,
      });
      this.client = null;
    }
  }

  /**
   * Close Redis connection
   */
  async close(): Promise<void> {
    if (this.client) {
      await this.client.quit();
      this.client = null;
    }
  }

  async get<T>(key: string): Promise<T | null> {
    if (!this.client) return null;

    try {
      const fullKey = this.keyPrefix + key;
      const value = await this.client.get(fullKey);
      if (!value) return null;
      return JSON.parse(value) as T;
    } catch (error) {
      this.logger.warn('Cache get failed', { key, error: (error as Error).message });
      return null;
    }
  }

  async set<T>(key: string, value: T, ttlSeconds?: number): Promise<void> {
    if (!this.client) return;

    try {
      const fullKey = this.keyPrefix + key;
      const serialized = JSON.stringify(value);
      
      if (ttlSeconds) {
        await this.client.setex(fullKey, ttlSeconds, serialized);
      } else {
        await this.client.set(fullKey, serialized);
      }
    } catch (error) {
      this.logger.warn('Cache set failed', { key, error: (error as Error).message });
    }
  }

  async delete(key: string): Promise<void> {
    if (!this.client) return;

    try {
      const fullKey = this.keyPrefix + key;
      await this.client.del(fullKey);
    } catch (error) {
      this.logger.warn('Cache delete failed', { key, error: (error as Error).message });
    }
  }

  async clear(): Promise<void> {
    if (!this.client) return;

    try {
      const pattern = this.keyPrefix + '*';
      const keys = await this.client.keys(pattern);
      if (keys.length > 0) {
        await this.client.del(...keys);
      }
    } catch (error) {
      this.logger.warn('Cache clear failed', { error: (error as Error).message });
    }
  }

  async health(): Promise<boolean> {
    if (!this.client) return false;
    try {
      await this.client.ping();
      return true;
    } catch {
      return false;
    }
  }
}

// =============================================================================
// IN-MEMORY CACHE SERVICE
// =============================================================================

interface CacheEntry<T> {
  value: T;
  expiresAt?: number;
}

export class InMemoryCacheService implements CacheService {
  private readonly cache: Map<string, CacheEntry<unknown>> = new Map();
  private readonly logger: Logger;
  private cleanupInterval: NodeJS.Timeout | null = null;

  constructor(logger: Logger) {
    this.logger = logger.child({ component: 'InMemoryCacheService' });
  }

  /**
   * Start periodic cleanup
   */
  start(): void {
    // Clean up expired entries every 60 seconds
    this.cleanupInterval = setInterval(() => {
      this.cleanupExpired();
    }, 60000);
    this.logger.debug('In-memory cache started');
  }

  /**
   * Stop periodic cleanup
   */
  stop(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
  }

  async get<T>(key: string): Promise<T | null> {
    const entry = this.cache.get(key) as CacheEntry<T> | undefined;
    
    if (!entry) return null;
    
    // Check expiration
    if (entry.expiresAt && Date.now() > entry.expiresAt) {
      this.cache.delete(key);
      return null;
    }
    
    return entry.value;
  }

  async set<T>(key: string, value: T, ttlSeconds?: number): Promise<void> {
    const entry: CacheEntry<T> = {
      value,
      expiresAt: ttlSeconds ? Date.now() + ttlSeconds * 1000 : undefined,
    };
    this.cache.set(key, entry);
  }

  async delete(key: string): Promise<void> {
    this.cache.delete(key);
  }

  async clear(): Promise<void> {
    this.cache.clear();
  }

  async health(): Promise<boolean> {
    return true;
  }

  /**
   * Get cache statistics
   */
  stats(): { size: number; keys: string[] } {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys()),
    };
  }

  /**
   * Clean up expired entries
   */
  private cleanupExpired(): void {
    const now = Date.now();
    let cleaned = 0;
    
    for (const [key, entry] of this.cache.entries()) {
      if (entry.expiresAt && now > entry.expiresAt) {
        this.cache.delete(key);
        cleaned++;
      }
    }
    
    if (cleaned > 0) {
      this.logger.debug('Cleaned up expired cache entries', { count: cleaned });
    }
  }
}

// =============================================================================
// CACHE SERVICE FACTORY
// =============================================================================

export async function createCacheService(
  config: Config,
  logger: Logger
): Promise<CacheService> {
  const isProd = config.service.env === 'prod';

  if (config.redis.enabled) {
    const redisCache = new RedisCacheService(config, logger);
    await redisCache.initialize();
    
    // Check if Redis is actually connected
    if (await redisCache.health()) {
      return redisCache;
    }

    if (isProd) {
      throw new Error('Redis cache is required in prod but is unavailable.');
    }

    logger.warn('Redis not available, falling back to in-memory cache');
  } else if (isProd) {
    throw new Error('Redis cache is required in prod. Set REDIS_ENABLED=true with valid connection settings.');
  }

  const memoryCache = new InMemoryCacheService(logger);
  memoryCache.start();
  return memoryCache;
}
