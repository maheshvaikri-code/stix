/**
 * STIX Cryptographic Operations
 * Enterprise-grade cryptographic utilities for signing, verification, and key management
 * 
 * @module @stix/shared/crypto
 */

import * as crypto from 'crypto';
import { TOKEN_CONFIG, EVIDENCE_CONFIG } from '../constants/index.js';
import type { ProofTokenHeader, ProofTokenClaims } from '../types/index.js';

// =============================================================================
// KEY TYPES
// =============================================================================

export interface KeyPair {
  publicKey: string;
  privateKey: string;
  keyId: string;
  algorithm: 'EdDSA' | 'ES256';
  createdAt: string;
  expiresAt?: string;
}

export interface SigningKey {
  keyId: string;
  algorithm: 'EdDSA' | 'ES256';
  privateKey: crypto.KeyObject;
}

export interface VerificationKey {
  keyId: string;
  algorithm: 'EdDSA' | 'ES256';
  publicKey: crypto.KeyObject;
}

export interface KeyStore {
  getSigningKey(keyId?: string): Promise<SigningKey>;
  getVerificationKey(keyId: string): Promise<VerificationKey>;
  getAllVerificationKeys(): Promise<VerificationKey[]>;
}

// =============================================================================
// KEY GENERATION
// =============================================================================

/**
 * Generate Ed25519 key pair
 */
export function generateEd25519KeyPair(): KeyPair {
  const { publicKey, privateKey } = crypto.generateKeyPairSync('ed25519');
  const keyId = `stix_ed25519_${Date.now()}_${crypto.randomBytes(4).toString('hex')}`;
  
  return {
    publicKey: publicKey.export({ type: 'spki', format: 'pem' }) as string,
    privateKey: privateKey.export({ type: 'pkcs8', format: 'pem' }) as string,
    keyId,
    algorithm: 'EdDSA',
    createdAt: new Date().toISOString(),
  };
}

/**
 * Generate ES256 (P-256) key pair
 */
export function generateES256KeyPair(): KeyPair {
  const { publicKey, privateKey } = crypto.generateKeyPairSync('ec', {
    namedCurve: 'P-256',
  });
  const keyId = `stix_es256_${Date.now()}_${crypto.randomBytes(4).toString('hex')}`;
  
  return {
    publicKey: publicKey.export({ type: 'spki', format: 'pem' }) as string,
    privateKey: privateKey.export({ type: 'pkcs8', format: 'pem' }) as string,
    keyId,
    algorithm: 'ES256',
    createdAt: new Date().toISOString(),
  };
}

/**
 * Load private key from PEM
 */
export function loadPrivateKey(pem: string): crypto.KeyObject {
  return crypto.createPrivateKey(pem);
}

/**
 * Load public key from PEM
 */
export function loadPublicKey(pem: string): crypto.KeyObject {
  return crypto.createPublicKey(pem);
}

// =============================================================================
// SIGNING OPERATIONS
// =============================================================================

/**
 * Sign data with Ed25519
 */
export function signEd25519(data: Buffer | string, privateKey: crypto.KeyObject): Buffer {
  const dataBuffer = typeof data === 'string' ? Buffer.from(data, 'utf8') : data;
  return crypto.sign(null, dataBuffer, privateKey);
}

/**
 * Sign data with ES256 (ECDSA P-256)
 */
export function signES256(data: Buffer | string, privateKey: crypto.KeyObject): Buffer {
  const dataBuffer = typeof data === 'string' ? Buffer.from(data, 'utf8') : data;
  const signature = crypto.sign('sha256', dataBuffer, privateKey);
  // Convert DER to raw R||S format for JWT
  return derToRaw(signature);
}

/**
 * Generic sign function
 */
export function sign(
  data: Buffer | string,
  privateKey: crypto.KeyObject,
  algorithm: 'EdDSA' | 'ES256'
): Buffer {
  if (algorithm === 'EdDSA') {
    return signEd25519(data, privateKey);
  }
  return signES256(data, privateKey);
}

// =============================================================================
// VERIFICATION OPERATIONS
// =============================================================================

/**
 * Verify Ed25519 signature
 */
export function verifyEd25519(
  data: Buffer | string,
  signature: Buffer,
  publicKey: crypto.KeyObject
): boolean {
  const dataBuffer = typeof data === 'string' ? Buffer.from(data, 'utf8') : data;
  return crypto.verify(null, dataBuffer, publicKey, signature);
}

/**
 * Verify ES256 signature
 */
export function verifyES256(
  data: Buffer | string,
  signature: Buffer,
  publicKey: crypto.KeyObject
): boolean {
  const dataBuffer = typeof data === 'string' ? Buffer.from(data, 'utf8') : data;
  // Convert raw R||S format back to DER for verification
  const derSignature = rawToDer(signature);
  return crypto.verify('sha256', dataBuffer, publicKey, derSignature);
}

/**
 * Generic verify function
 */
export function verify(
  data: Buffer | string,
  signature: Buffer,
  publicKey: crypto.KeyObject,
  algorithm: 'EdDSA' | 'ES256'
): boolean {
  if (algorithm === 'EdDSA') {
    return verifyEd25519(data, signature, publicKey);
  }
  return verifyES256(data, signature, publicKey);
}

// =============================================================================
// HASHING OPERATIONS
// =============================================================================

/**
 * Compute SHA-256 hash
 */
export function sha256(data: Buffer | string): string {
  const dataBuffer = typeof data === 'string' ? Buffer.from(data, 'utf8') : data;
  const hash = crypto.createHash('sha256').update(dataBuffer).digest('hex');
  return `sha256:${hash}`;
}

/**
 * Compute SHA-256 hash (raw bytes)
 */
export function sha256Raw(data: Buffer | string): Buffer {
  const dataBuffer = typeof data === 'string' ? Buffer.from(data, 'utf8') : data;
  return crypto.createHash('sha256').update(dataBuffer).digest();
}

/**
 * Compute hash of canonical JSON
 */
export function hashCanonical(obj: unknown): string {
  const canonical = canonicalize(obj);
  return sha256(canonical);
}

/**
 * Verify hash
 */
export function verifyHash(data: Buffer | string, expectedHash: string): boolean {
  const actualHash = sha256(data);
  return crypto.timingSafeEqual(
    Buffer.from(actualHash, 'utf8'),
    Buffer.from(expectedHash, 'utf8')
  );
}

/** Zero hash for genesis blocks */
export const ZERO_HASH = 'sha256:' + '0'.repeat(64);

// =============================================================================
// CANONICALIZATION
// =============================================================================

/**
 * Canonicalize object for deterministic hashing
 * Follows RFC 8785 (JCS - JSON Canonicalization Scheme)
 */
export function canonicalize(obj: unknown): string {
  return JSON.stringify(sortObjectKeys(obj));
}

/**
 * Recursively sort object keys
 */
function sortObjectKeys(value: unknown): unknown {
  if (value === null || value === undefined) {
    return value;
  }

  if (Array.isArray(value)) {
    return value.map(sortObjectKeys);
  }

  if (typeof value === 'object') {
    const sorted: Record<string, unknown> = {};
    const keys = Object.keys(value as Record<string, unknown>).sort();
    for (const key of keys) {
      sorted[key] = sortObjectKeys((value as Record<string, unknown>)[key]);
    }
    return sorted;
  }

  return value;
}

// =============================================================================
// BASE64URL ENCODING
// =============================================================================

/**
 * Encode buffer to base64url
 */
export function toBase64Url(data: Buffer | string): string {
  const buffer = typeof data === 'string' ? Buffer.from(data, 'utf8') : data;
  return buffer.toString('base64url');
}

/**
 * Decode base64url to buffer
 */
export function fromBase64Url(data: string): Buffer {
  return Buffer.from(data, 'base64url');
}

/**
 * Encode string to base64url
 */
export function stringToBase64Url(str: string): string {
  return Buffer.from(str, 'utf8').toString('base64url');
}

/**
 * Decode base64url to string
 */
export function base64UrlToString(data: string): string {
  return Buffer.from(data, 'base64url').toString('utf8');
}

// =============================================================================
// PROOF TOKEN OPERATIONS
// =============================================================================

/**
 * Create a STIX proof token (JWT-like)
 */
export function createProofToken(
  claims: ProofTokenClaims,
  signingKey: SigningKey
): string {
  const header: ProofTokenHeader = {
    alg: signingKey.algorithm,
    typ: 'JWT',
    kid: signingKey.keyId,
  };

  const headerB64 = stringToBase64Url(JSON.stringify(header));
  const payloadB64 = stringToBase64Url(JSON.stringify(claims));
  const signingInput = `${headerB64}.${payloadB64}`;

  const signature = sign(signingInput, signingKey.privateKey, signingKey.algorithm);
  const signatureB64 = toBase64Url(signature);

  return `${signingInput}.${signatureB64}`;
}

/**
 * Verify and decode a STIX proof token
 */
export function verifyProofToken(
  token: string,
  getKey: (keyId: string) => VerificationKey | undefined
): { valid: boolean; header?: ProofTokenHeader; claims?: ProofTokenClaims; error?: string } {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) {
      return { valid: false, error: 'Invalid token format' };
    }

    const [headerB64, payloadB64, signatureB64] = parts;

    // Decode header
    const header = JSON.parse(base64UrlToString(headerB64)) as ProofTokenHeader;

    // Get verification key
    const verificationKey = getKey(header.kid);
    if (!verificationKey) {
      return { valid: false, error: `Unknown key: ${header.kid}` };
    }

    // Verify signature
    const signingInput = `${headerB64}.${payloadB64}`;
    const signature = fromBase64Url(signatureB64);
    const isValid = verify(signingInput, signature, verificationKey.publicKey, header.alg);

    if (!isValid) {
      return { valid: false, error: 'Invalid signature' };
    }

    // Decode claims
    const claims = JSON.parse(base64UrlToString(payloadB64)) as ProofTokenClaims;

    // Check expiration
    const now = Math.floor(Date.now() / 1000);
    if (claims.exp <= now) {
      return { valid: false, header, claims, error: 'Token expired' };
    }

    // Check not-before (iat)
    if (claims.iat > now + 60) { // Allow 60s clock skew
      return { valid: false, header, claims, error: 'Token not yet valid' };
    }

    return { valid: true, header, claims };
  } catch (err) {
    return { valid: false, error: `Token verification failed: ${(err as Error).message}` };
  }
}

/**
 * Parse token without verification (for inspection)
 */
export function parseProofTokenUnsafe(token: string): {
  header?: ProofTokenHeader;
  claims?: ProofTokenClaims;
  error?: string;
} {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) {
      return { error: 'Invalid token format' };
    }

    const header = JSON.parse(base64UrlToString(parts[0])) as ProofTokenHeader;
    const claims = JSON.parse(base64UrlToString(parts[1])) as ProofTokenClaims;

    return { header, claims };
  } catch (err) {
    return { error: `Token parse failed: ${(err as Error).message}` };
  }
}

// =============================================================================
// EVIDENCE SIGNING
// =============================================================================

export interface EvidenceSigningResult {
  eventHash: string;
  signature: string;
  keyId: string;
}

/**
 * Sign evidence event (canonical hash + signature)
 */
export function signEvidence(
  eventWithoutIntegrity: Record<string, unknown>,
  prevHash: string,
  signingKey: SigningKey
): EvidenceSigningResult {
  // Create canonical representation for hashing
  const canonical = canonicalize(eventWithoutIntegrity);
  const eventHash = sha256(canonical);

  // Sign the combination of event hash and prev hash
  const signingData = `${eventHash}|${prevHash}`;
  const signature = sign(signingData, signingKey.privateKey, signingKey.algorithm);

  return {
    eventHash,
    signature: toBase64Url(signature),
    keyId: signingKey.keyId,
  };
}

/**
 * Verify evidence signature
 */
export function verifyEvidenceSignature(
  eventWithoutIntegrity: Record<string, unknown>,
  integrity: {
    event_hash: string;
    prev_hash: string;
    signature: string;
    key_id: string;
  },
  verificationKey: VerificationKey
): { valid: boolean; error?: string } {
  try {
    // Verify event hash
    const canonical = canonicalize(eventWithoutIntegrity);
    const computedHash = sha256(canonical);
    
    if (computedHash !== integrity.event_hash) {
      return { valid: false, error: 'Event hash mismatch' };
    }

    // Verify signature
    const signingData = `${integrity.event_hash}|${integrity.prev_hash}`;
    const signature = fromBase64Url(integrity.signature);
    const isValid = verify(signingData, signature, verificationKey.publicKey, verificationKey.algorithm);

    if (!isValid) {
      return { valid: false, error: 'Invalid signature' };
    }

    return { valid: true };
  } catch (err) {
    return { valid: false, error: `Verification failed: ${(err as Error).message}` };
  }
}

// =============================================================================
// HASH CHAIN VERIFICATION
// =============================================================================

export interface HashChainVerificationResult {
  valid: boolean;
  verifiedCount: number;
  errors: Array<{ index: number; eventId: string; error: string }>;
}

/**
 * Verify hash chain integrity for a sequence of events
 */
export function verifyHashChain(
  events: Array<{
    event_id: string;
    integrity: {
      event_hash: string;
      prev_hash: string;
    };
  }>
): HashChainVerificationResult {
  const errors: Array<{ index: number; eventId: string; error: string }> = [];

  for (let i = 1; i < events.length; i++) {
    const current = events[i];
    const previous = events[i - 1];

    if (current.integrity.prev_hash !== previous.integrity.event_hash) {
      errors.push({
        index: i,
        eventId: current.event_id,
        error: `Hash chain break: prev_hash doesn't match previous event's hash`,
      });
    }
  }

  return {
    valid: errors.length === 0,
    verifiedCount: events.length,
    errors,
  };
}

// =============================================================================
// IN-MEMORY KEY STORE (FOR DEVELOPMENT/TESTING)
// =============================================================================

export class InMemoryKeyStore implements KeyStore {
  private signingKeys: Map<string, SigningKey> = new Map();
  private verificationKeys: Map<string, VerificationKey> = new Map();
  private defaultKeyId?: string;

  /**
   * Add a key pair to the store
   */
  addKeyPair(keyPair: KeyPair): void {
    const privateKeyObj = loadPrivateKey(keyPair.privateKey);
    const publicKeyObj = loadPublicKey(keyPair.publicKey);

    this.signingKeys.set(keyPair.keyId, {
      keyId: keyPair.keyId,
      algorithm: keyPair.algorithm,
      privateKey: privateKeyObj,
    });

    this.verificationKeys.set(keyPair.keyId, {
      keyId: keyPair.keyId,
      algorithm: keyPair.algorithm,
      publicKey: publicKeyObj,
    });

    if (!this.defaultKeyId) {
      this.defaultKeyId = keyPair.keyId;
    }
  }

  /**
   * Set the default signing key
   */
  setDefaultKey(keyId: string): void {
    if (!this.signingKeys.has(keyId)) {
      throw new Error(`Key not found: ${keyId}`);
    }
    this.defaultKeyId = keyId;
  }

  async getSigningKey(keyId?: string): Promise<SigningKey> {
    const id = keyId ?? this.defaultKeyId;
    if (!id) {
      throw new Error('No signing key available');
    }
    const key = this.signingKeys.get(id);
    if (!key) {
      throw new Error(`Signing key not found: ${id}`);
    }
    return key;
  }

  async getVerificationKey(keyId: string): Promise<VerificationKey> {
    const key = this.verificationKeys.get(keyId);
    if (!key) {
      throw new Error(`Verification key not found: ${keyId}`);
    }
    return key;
  }

  async getAllVerificationKeys(): Promise<VerificationKey[]> {
    return Array.from(this.verificationKeys.values());
  }
}

// =============================================================================
// DER <-> RAW SIGNATURE CONVERSION (for ES256)
// =============================================================================

/**
 * Convert DER signature to raw R||S format
 */
function derToRaw(signature: Buffer): Buffer {
  // DER format: 0x30 [len] 0x02 [r-len] [r] 0x02 [s-len] [s]
  let offset = 2; // Skip 0x30 and total length
  
  // Get R
  if (signature[offset] !== 0x02) throw new Error('Invalid DER signature');
  offset++;
  const rLen = signature[offset];
  offset++;
  let r = signature.subarray(offset, offset + rLen);
  offset += rLen;
  
  // Get S
  if (signature[offset] !== 0x02) throw new Error('Invalid DER signature');
  offset++;
  const sLen = signature[offset];
  offset++;
  let s = signature.subarray(offset, offset + sLen);
  
  // Remove leading zeros and pad to 32 bytes
  if (r.length > 32) r = r.subarray(r.length - 32);
  if (s.length > 32) s = s.subarray(s.length - 32);
  
  const raw = Buffer.alloc(64);
  r.copy(raw, 32 - r.length);
  s.copy(raw, 64 - s.length);
  
  return raw;
}

/**
 * Convert raw R||S format to DER
 */
function rawToDer(signature: Buffer): Buffer {
  if (signature.length !== 64) {
    throw new Error('Invalid raw signature length');
  }
  
  let r = signature.subarray(0, 32);
  let s = signature.subarray(32, 64);
  
  // Remove leading zeros
  while (r.length > 1 && r[0] === 0) r = r.subarray(1);
  while (s.length > 1 && s[0] === 0) s = s.subarray(1);
  
  // Add leading zero if high bit is set (to ensure positive integer)
  if (r[0] & 0x80) r = Buffer.concat([Buffer.from([0]), r]);
  if (s[0] & 0x80) s = Buffer.concat([Buffer.from([0]), s]);
  
  const totalLen = 4 + r.length + s.length;
  
  return Buffer.concat([
    Buffer.from([0x30, totalLen]),
    Buffer.from([0x02, r.length]),
    r,
    Buffer.from([0x02, s.length]),
    s,
  ]);
}

// =============================================================================
// RANDOM GENERATION
// =============================================================================

/**
 * Generate cryptographically secure random bytes
 */
export function randomBytes(length: number): Buffer {
  return crypto.randomBytes(length);
}

/**
 * Generate random hex string
 */
export function randomHex(length: number): string {
  return crypto.randomBytes(length).toString('hex');
}

/**
 * Generate random UUID v4
 */
export function randomUuid(): string {
  return crypto.randomUUID();
}
