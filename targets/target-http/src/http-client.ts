/**
 * STIX Target HTTP - HTTP Client Service
 *
 * @module @stix/target-http
 */

import { request as undiciRequest, type Dispatcher } from 'undici';
import { z } from 'zod';
import { isoTimestamp, type Logger } from '@stix/shared';
import type { Config } from './config.js';

// =============================================================================
// HTTP REQUEST SCHEMA
// =============================================================================

export const HttpRequestSchema = z.object({
  method: z.enum(['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']),
  url: z.string().url(),
  headers: z.record(z.string()).optional(),
  body: z.union([z.string(), z.record(z.unknown())]).optional(),
  timeout: z.number().optional(),
  followRedirects: z.boolean().optional(),
  metadata: z.record(z.unknown()).optional(),
});

export type HttpRequest = z.infer<typeof HttpRequestSchema>;

// =============================================================================
// HTTP RESPONSE
// =============================================================================

export interface HttpResponse {
  success: boolean;
  statusCode: number;
  statusMessage: string;
  headers: Record<string, string | string[]>;
  body?: string | Record<string, unknown>;
  contentType?: string;
  contentLength?: number;
  timestamp: string;
  duration_ms: number;
  error?: {
    code: string;
    message: string;
  };
}

// =============================================================================
// PRIVATE NETWORK DETECTION
// =============================================================================

const PRIVATE_NETWORK_RANGES = [
  /^10\./,
  /^172\.(1[6-9]|2[0-9]|3[0-1])\./,
  /^192\.168\./,
  /^127\./,
  /^169\.254\./,
  /^::1$/,
  /^fc00:/i,
  /^fe80:/i,
  /^localhost$/i,
  /^0\.0\.0\.0$/,
];

function isPrivateHost(hostname: string): boolean {
  return PRIVATE_NETWORK_RANGES.some((pattern) => pattern.test(hostname));
}

// =============================================================================
// HTTP CLIENT SERVICE
// =============================================================================

/**
 * Protected HTTP client service
 */
export class HttpClientService {
  private readonly config: Config;
  private readonly logger: Logger;

  constructor(config: Config, logger: Logger) {
    this.config = config;
    this.logger = logger;
  }

  /**
   * Execute an HTTP request
   */
  async execute(
    request: HttpRequest,
    traceId: string
  ): Promise<HttpResponse> {
    const startTime = Date.now();

    try {
      // Parse URL and validate host
      const url = new URL(request.url);
      const validationError = this.validateHost(url.hostname);
      if (validationError) {
        return this.errorResponse(validationError.code, validationError.message, startTime);
      }

      // Prepare request options
      const options: Dispatcher.RequestOptions = {
        method: request.method,
        path: `${url.pathname}${url.search}`,
        headers: {
          'User-Agent': this.config.http.userAgent,
          'X-STIX-Trace-Id': traceId,
          ...request.headers,
        },
        maxRedirections: request.followRedirects !== false ? this.config.http.maxRedirects : 0,
        bodyTimeout: request.timeout || this.config.http.timeout,
        headersTimeout: request.timeout || this.config.http.timeout,
      };

      // Add body if present
      if (request.body) {
        if (typeof request.body === 'string') {
          options.body = request.body;
        } else {
          options.body = JSON.stringify(request.body);
          options.headers = {
            ...options.headers,
            'Content-Type': 'application/json',
          };
        }
      }

      this.logger.debug('Executing HTTP request', {
        trace_id: traceId,
        method: request.method,
        url: request.url,
      });

      // Execute request
      const response = await undiciRequest(request.url, options);

      // Read response body
      const bodyBuffer = await response.body.arrayBuffer();
      const bodyText = new TextDecoder().decode(bodyBuffer);

      // Check response size
      if (bodyBuffer.byteLength > this.config.http.maxResponseSize) {
        return this.errorResponse(
          'RESPONSE_TOO_LARGE',
          `Response size ${bodyBuffer.byteLength} exceeds maximum ${this.config.http.maxResponseSize}`,
          startTime
        );
      }

      // Parse content type
      const contentType = response.headers['content-type'] as string | undefined;
      let body: string | Record<string, unknown> = bodyText;

      if (contentType?.includes('application/json')) {
        try {
          body = JSON.parse(bodyText);
        } catch {
          // Keep as string if parse fails
        }
      }

      const duration_ms = Date.now() - startTime;

      this.logger.info('HTTP request completed', {
        trace_id: traceId,
        method: request.method,
        url: request.url,
        status_code: response.statusCode,
        duration_ms,
      });

      return {
        success: response.statusCode >= 200 && response.statusCode < 400,
        statusCode: response.statusCode,
        statusMessage: this.getStatusMessage(response.statusCode),
        headers: this.normalizeHeaders(response.headers),
        body,
        contentType,
        contentLength: bodyBuffer.byteLength,
        timestamp: isoTimestamp(),
        duration_ms,
      };
    } catch (error) {
      const err = error as Error & { code?: string };
      const duration_ms = Date.now() - startTime;

      this.logger.error('HTTP request failed', {
        trace_id: traceId,
        method: request.method,
        url: request.url,
        duration_ms,
      }, err);

      return this.errorResponse(
        err.code || 'REQUEST_FAILED',
        err.message,
        startTime
      );
    }
  }

  /**
   * Execute multiple HTTP requests in parallel
   */
  async executeBatch(
    requests: HttpRequest[],
    traceId: string
  ): Promise<HttpResponse[]> {
    return Promise.all(
      requests.map((req, index) =>
        this.execute(req, `${traceId}-${index}`)
      )
    );
  }

  /**
   * Validate a host against allowed/blocked lists
   */
  private validateHost(hostname: string): { code: string; message: string } | null {
    // Check blocked hosts
    if (this.config.http.blockedHosts?.length) {
      for (const blocked of this.config.http.blockedHosts) {
        if (hostname === blocked || hostname.endsWith(`.${blocked}`)) {
          return {
            code: 'HOST_BLOCKED',
            message: `Host ${hostname} is blocked`,
          };
        }
      }
    }

    // Check allowed hosts
    if (this.config.http.allowedHosts?.length) {
      const allowed = this.config.http.allowedHosts.some(
        (allowed) => hostname === allowed || hostname.endsWith(`.${allowed}`)
      );
      if (!allowed) {
        return {
          code: 'HOST_NOT_ALLOWED',
          message: `Host ${hostname} is not in the allowed list`,
        };
      }
    }

    // Check private networks
    if (!this.config.http.allowPrivateNetworks && isPrivateHost(hostname)) {
      return {
        code: 'PRIVATE_NETWORK_BLOCKED',
        message: `Access to private network host ${hostname} is blocked`,
      };
    }

    return null;
  }

  /**
   * Create an error response
   */
  private errorResponse(
    code: string,
    message: string,
    startTime: number
  ): HttpResponse {
    return {
      success: false,
      statusCode: 0,
      statusMessage: 'Error',
      headers: {},
      timestamp: isoTimestamp(),
      duration_ms: Date.now() - startTime,
      error: { code, message },
    };
  }

  /**
   * Normalize response headers
   */
  private normalizeHeaders(
    headers: Dispatcher.ResponseData['headers']
  ): Record<string, string | string[]> {
    const result: Record<string, string | string[]> = {};

    for (const [key, value] of Object.entries(headers)) {
      if (value !== undefined) {
        result[key.toLowerCase()] = value;
      }
    }

    return result;
  }

  /**
   * Get status message for status code
   */
  private getStatusMessage(code: number): string {
    const messages: Record<number, string> = {
      200: 'OK',
      201: 'Created',
      204: 'No Content',
      301: 'Moved Permanently',
      302: 'Found',
      400: 'Bad Request',
      401: 'Unauthorized',
      403: 'Forbidden',
      404: 'Not Found',
      500: 'Internal Server Error',
      502: 'Bad Gateway',
      503: 'Service Unavailable',
    };
    return messages[code] || 'Unknown';
  }
}

// =============================================================================
// MOCK HTTP CLIENT (for testing)
// =============================================================================

export class MockHttpClientService extends HttpClientService {
  public requests: Array<{ request: HttpRequest; traceId: string }> = [];
  public mockResponses: Map<string, HttpResponse> = new Map();

  override async execute(
    request: HttpRequest,
    traceId: string
  ): Promise<HttpResponse> {
    this.requests.push({ request, traceId });

    // Check for mock response
    const mockKey = `${request.method}:${request.url}`;
    const mockResponse = this.mockResponses.get(mockKey);
    if (mockResponse) {
      return mockResponse;
    }

    // Default mock response
    return {
      success: true,
      statusCode: 200,
      statusMessage: 'OK',
      headers: { 'content-type': 'application/json' },
      body: { mock: true, url: request.url },
      contentType: 'application/json',
      contentLength: 10,
      timestamp: isoTimestamp(),
      duration_ms: 1,
    };
  }

  setMockResponse(method: string, url: string, response: HttpResponse): void {
    this.mockResponses.set(`${method}:${url}`, response);
  }
}
