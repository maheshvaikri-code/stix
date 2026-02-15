/**
 * STIX Integration Test
 * Verifies core functionality works end-to-end
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import {
  // Types
  type Actor,
  type Resource,
  type Context,
  type AuthorizeRequest,
  type DecisionKind,
  
  // Utils
  generateTraceId,
  generateEventId,
  hashCanonical,
  canonicalize,
  isoTimestamp,
  ZERO_HASH,
  
  // Validators
  validateAuthorizeRequest,
  validatePolicyArtifact,
  
  // Crypto
  generateEd25519KeyPair,
  InMemoryKeyStore,
  createProofToken,
  verifyProofToken,
  signEvidence,
  verifyEvidenceSignature,
  
  // Errors
  StixError,
  isStixError,
  
  // Logger
  createLogger,
} from '@stix/shared';

describe('STIX Shared Package', () => {
  describe('ID Generation', () => {
    it('should generate valid trace IDs', () => {
      const traceId = generateTraceId();
      expect(traceId).toMatch(/^stix_[a-f0-9-]{36}$/);
    });

    it('should generate unique trace IDs', () => {
      const id1 = generateTraceId();
      const id2 = generateTraceId();
      expect(id1).not.toBe(id2);
    });

    it('should generate valid event IDs', () => {
      const eventId = generateEventId();
      expect(eventId).toMatch(/^evt_[a-f0-9-]{36}$/);
    });
  });

  describe('Canonicalization & Hashing', () => {
    it('should produce consistent canonical JSON', () => {
      const obj1 = { b: 2, a: 1 };
      const obj2 = { a: 1, b: 2 };
      
      expect(canonicalize(obj1)).toBe(canonicalize(obj2));
    });

    it('should produce valid SHA-256 hashes', () => {
      const hash = hashCanonical({ test: 'data' });
      expect(hash).toMatch(/^sha256:[a-f0-9]{64}$/);
    });

    it('should have a valid ZERO_HASH', () => {
      expect(ZERO_HASH).toBe('sha256:' + '0'.repeat(64));
    });
  });

  describe('Validators', () => {
    it('should validate a valid authorization request', () => {
      const request: AuthorizeRequest = {
        actor: {
          id: 'agent-1',
          type: 'AI_AGENT',
          tenant: 'test-tenant',
        },
        action: 'read_data',
        resource: {
          type: 'database',
          id: 'db-1',
        },
        context: {
          env: 'dev',
          purpose: 'Testing',
        },
      };

      const validated = validateAuthorizeRequest(request);
      expect(validated.actor.id).toBe('agent-1');
      expect(validated.action).toBe('read_data');
    });

    it('should validate a policy artifact', () => {
      const policy = {
        policy_id: 'test-policy',
        version: '1.0.0',
        scope: {
          actor_type: 'AI_AGENT' as const,
          action: '*',
          resource_type: 'database',
        },
        decision: 'ALLOW' as DecisionKind,
        reason_code: 'TEST_ALLOW',
      };

      const validated = validatePolicyArtifact(policy);
      expect(validated.policy_id).toBe('test-policy');
    });
  });

  describe('Cryptography', () => {
    let keyStore: InMemoryKeyStore;
    let keyId: string;

    beforeAll(() => {
      keyStore = new InMemoryKeyStore();
      const keyPair = generateEd25519KeyPair();
      keyStore.addKeyPair(keyPair);
      keyId = keyPair.keyId;
    });

    it('should generate Ed25519 key pairs', () => {
      const keyPair = generateEd25519KeyPair();
      expect(keyPair.algorithm).toBe('Ed25519');
      expect(keyPair.publicKey).toContain('BEGIN PUBLIC KEY');
      expect(keyPair.privateKey).toContain('BEGIN PRIVATE KEY');
    });

    it('should create and verify proof tokens', async () => {
      const signingKey = await keyStore.getSigningKey();
      
      const claims = {
        iss: 'stix' as const,
        sub: 'agent-1',
        act: 'read_data',
        res: 'database',
        cls: ['internal'],
        pol: hashCanonical({ policy_id: 'test' }),
        tid: generateTraceId(),
        iat: Math.floor(Date.now() / 1000),
        exp: Math.floor(Date.now() / 1000) + 300,
      };

      const token = createProofToken(claims, signingKey);
      expect(token).toContain('.');

      const getKey = (kid: string) => {
        if (kid === keyId) {
          const verKey = keyStore['verificationKeys'].get(kid);
          return verKey;
        }
        return undefined;
      };

      const result = verifyProofToken(token, getKey);
      expect(result.valid).toBe(true);
      expect(result.claims?.sub).toBe('agent-1');
    });

    it('should sign and verify evidence', async () => {
      const signingKey = await keyStore.getSigningKey();
      
      const eventData = {
        event_id: generateEventId(),
        trace_id: generateTraceId(),
        timestamp: isoTimestamp(),
        decision: 'ALLOW',
        actor: { id: 'agent-1', type: 'AI_AGENT' },
      };

      const prevHash = ZERO_HASH;
      const result = signEvidence(eventData, prevHash, signingKey);

      expect(result.eventHash).toMatch(/^sha256:[a-f0-9]{64}$/);
      expect(result.signature).toBeTruthy();
      expect(result.keyId).toBe(keyId);

      const verificationKey = await keyStore.getVerificationKey(keyId);
      const verifyResult = verifyEvidenceSignature(
        eventData,
        {
          event_hash: result.eventHash,
          prev_hash: prevHash,
          signature: result.signature,
          key_id: result.keyId,
        },
        verificationKey
      );

      expect(verifyResult.valid).toBe(true);
    });
  });

  describe('Errors', () => {
    it('should create StixError with proper properties', () => {
      const error = new StixError('Test error', 'TEST_CODE', 400);
      
      expect(error.message).toBe('Test error');
      expect(error.code).toBe('TEST_CODE');
      expect(error.statusCode).toBe(400);
      expect(error.timestamp).toBeTruthy();
    });

    it('should identify StixErrors correctly', () => {
      const stixError = new StixError('Test', 'TEST', 400);
      const regularError = new Error('Test');

      expect(isStixError(stixError)).toBe(true);
      expect(isStixError(regularError)).toBe(false);
    });
  });

  describe('Logger', () => {
    it('should create a logger', () => {
      const logger = createLogger({
        service: 'test-service',
        level: 'debug',
      });

      expect(logger).toBeDefined();
      expect(typeof logger.info).toBe('function');
      expect(typeof logger.error).toBe('function');
    });

    it('should create child loggers with context', () => {
      const logger = createLogger({
        service: 'test-service',
        level: 'debug',
      });

      const childLogger = logger.child({ trace_id: 'test-trace' });
      expect(childLogger).toBeDefined();
    });
  });
});
