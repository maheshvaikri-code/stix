/**
 * STIX Target Email - Email Sending Service
 *
 * @module @stix/target-email
 */

import nodemailer from 'nodemailer';
import type { Transporter } from 'nodemailer';
import { z } from 'zod';
import { isoTimestamp, type Logger } from '@stix/shared';
import type { Config } from './config.js';

// =============================================================================
// EMAIL REQUEST SCHEMA
// =============================================================================

export const SendEmailRequestSchema = z.object({
  to: z.union([z.string().email(), z.array(z.string().email())]),
  cc: z.union([z.string().email(), z.array(z.string().email())]).optional(),
  bcc: z.union([z.string().email(), z.array(z.string().email())]).optional(),
  subject: z.string().min(1).max(998),
  body: z.object({
    text: z.string().optional(),
    html: z.string().optional(),
  }).refine((body) => body.text || body.html, {
    message: 'Either text or html body is required',
  }),
  replyTo: z.string().email().optional(),
  priority: z.enum(['high', 'normal', 'low']).optional(),
  attachments: z.array(z.object({
    filename: z.string(),
    content: z.string(), // base64 encoded
    contentType: z.string().optional(),
  })).optional(),
  headers: z.record(z.string()).optional(),
  metadata: z.record(z.unknown()).optional(),
});

export type SendEmailRequest = z.infer<typeof SendEmailRequestSchema>;

// =============================================================================
// EMAIL RESULT
// =============================================================================

export interface SendEmailResult {
  success: boolean;
  messageId?: string;
  timestamp: string;
  recipients: {
    accepted: string[];
    rejected: string[];
  };
  error?: {
    code: string;
    message: string;
  };
  duration_ms: number;
}

// =============================================================================
// EMAIL SERVICE
// =============================================================================

/**
 * Email sending service
 */
export class EmailService {
  private readonly config: Config;
  private readonly logger: Logger;
  private transporter: Transporter | null = null;
  private initialized = false;

  constructor(config: Config, logger: Logger) {
    this.config = config;
    this.logger = logger;
  }

  /**
   * Initialize the email transporter
   */
  async initialize(): Promise<void> {
    if (this.initialized) {
      return;
    }

    const { smtp } = this.config;

    this.transporter = nodemailer.createTransport({
      host: smtp.host,
      port: smtp.port,
      secure: smtp.secure,
      auth: smtp.auth,
      tls: {
        rejectUnauthorized: this.config.service.env === 'prod',
      },
    });

    // Verify connection
    try {
      await this.transporter.verify();
      this.logger.info('Email transporter initialized', {
        host: smtp.host,
        port: smtp.port,
        secure: smtp.secure,
      });
      this.initialized = true;
    } catch (error) {
      this.logger.error('Failed to verify email transporter', {}, error as Error);
      throw error;
    }
  }

  /**
   * Send an email
   */
  async send(
    request: SendEmailRequest,
    traceId: string
  ): Promise<SendEmailResult> {
    const startTime = Date.now();

    if (!this.transporter) {
      await this.initialize();
    }

    try {
      // Build message
      const message = {
        from: this.config.smtp.from,
        to: request.to,
        cc: request.cc,
        bcc: request.bcc,
        subject: request.subject,
        text: request.body.text,
        html: request.body.html,
        replyTo: request.replyTo,
        priority: request.priority,
        headers: {
          'X-STIX-Trace-Id': traceId,
          ...request.headers,
        },
        attachments: request.attachments?.map((att) => ({
          filename: att.filename,
          content: Buffer.from(att.content, 'base64'),
          contentType: att.contentType,
        })),
      };

      // Send email
      const info = await this.transporter!.sendMail(message);

      const duration_ms = Date.now() - startTime;

      this.logger.info('Email sent successfully', {
        trace_id: traceId,
        message_id: info.messageId,
        to: Array.isArray(request.to) ? request.to : [request.to],
        subject: request.subject,
        duration_ms,
      });

      return {
        success: true,
        messageId: info.messageId,
        timestamp: isoTimestamp(),
        recipients: {
          accepted: info.accepted?.map(String) || [],
          rejected: info.rejected?.map(String) || [],
        },
        duration_ms,
      };
    } catch (error) {
      const err = error as Error & { code?: string };
      const duration_ms = Date.now() - startTime;

      this.logger.error('Failed to send email', {
        trace_id: traceId,
        to: request.to,
        subject: request.subject,
        duration_ms,
      }, err);

      return {
        success: false,
        timestamp: isoTimestamp(),
        recipients: {
          accepted: [],
          rejected: Array.isArray(request.to) ? request.to : [request.to],
        },
        error: {
          code: err.code || 'SEND_FAILED',
          message: err.message,
        },
        duration_ms,
      };
    }
  }

  /**
   * Check if the email service is healthy
   */
  async healthCheck(): Promise<{ healthy: boolean; message?: string }> {
    if (!this.transporter) {
      return { healthy: false, message: 'Transporter not initialized' };
    }

    try {
      await this.transporter.verify();
      return { healthy: true };
    } catch (error) {
      return {
        healthy: false,
        message: (error as Error).message,
      };
    }
  }

  /**
   * Close the transporter
   */
  async close(): Promise<void> {
    if (this.transporter) {
      this.transporter.close();
      this.transporter = null;
      this.initialized = false;
    }
  }
}

// =============================================================================
// MOCK EMAIL SERVICE (for testing)
// =============================================================================

/**
 * Mock email service for testing
 */
export class MockEmailService extends EmailService {
  public sentEmails: Array<{ request: SendEmailRequest; traceId: string }> = [];

  override async initialize(): Promise<void> {
    // No-op for mock
  }

  override async send(
    request: SendEmailRequest,
    traceId: string
  ): Promise<SendEmailResult> {
    this.sentEmails.push({ request, traceId });

    return {
      success: true,
      messageId: `mock-${Date.now()}@test`,
      timestamp: isoTimestamp(),
      recipients: {
        accepted: Array.isArray(request.to) ? request.to : [request.to],
        rejected: [],
      },
      duration_ms: 1,
    };
  }

  override async healthCheck(): Promise<{ healthy: boolean; message?: string }> {
    return { healthy: true };
  }

  override async close(): Promise<void> {
    this.sentEmails = [];
  }
}
