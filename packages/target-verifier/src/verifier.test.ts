import { describe, expect, it } from 'vitest';
import {
  createProofToken,
  generateEd25519KeyPair,
  hashCanonical,
  loadPrivateKey,
  loadPublicKey,
  type Logger,
} from '@stix/shared';
import { TargetVerifier } from './verifier.js';

const logger = {
  debug: () => {},
  info: () => {},
  warn: () => {},
  error: () => {},
  child: () => logger,
} as unknown as Logger;

function makeToken() {
  const key = generateEd25519KeyPair();
  const requestHash = hashCanonical({ action: 'write', resource: { type: 'file', id: 'file-1' } });
  const token = createProofToken({
    iss: 'stix',
    sub: 'workload-1',
    act: 'write',
    res: 'file',
    cls: [],
    pol: hashCanonical({ policy: 'test' }),
    tid: 'stix_trace_1',
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + 300,
    jti: 'req_replay_1',
    replay_id: 'req_replay_1',
    request_hash: requestHash,
    arguments_hash: hashCanonical({ tool: 'write', args: 'safe' }),
    action_id: 'act_1',
    resource_id: 'file-1',
    decision: 'ALLOW',
    reason_code: 'POLICY_ALLOW',
    policy_id: 'policy-1',
    policy_version: '1.0.0',
    policy_hash: hashCanonical({ policy: 'test' }),
    actor_id: 'workload-1',
    actor_type: 'SERVICE',
    action: 'write',
    resource_type: 'file',
  }, {
    keyId: key.keyId,
    algorithm: key.algorithm,
    privateKey: loadPrivateKey(key.privateKey),
  });

  return { key, token, requestHash };
}

describe('TargetVerifier security binding', () => {
  it('selects the public key by JWT kid and requires resource matching by default', async () => {
    const { key, token, requestHash } = makeToken();
    const verifier = new TargetVerifier({
      publicKeys: [{ keyId: key.keyId, algorithm: key.algorithm, pem: key.publicKey }],
    }, logger);

    const valid = await verifier.verify({
      token,
      expectedAction: 'write',
      expectedResourceType: 'file',
      expectedResourceId: 'file-1',
      expectedRequestHash: requestHash,
    });
    expect(valid.valid).toBe(true);

    const wrongResource = await verifier.verify({
      token,
      expectedAction: 'write',
      expectedResourceType: 'file',
      expectedResourceId: 'file-2',
    });
    expect(wrongResource.valid).toBe(false);
    expect(wrongResource.errors?.[0]?.code).toBe('RESOURCE_MISMATCH');
  });

  it('rejects a validly signed token whose kid is not configured', async () => {
    const { token } = makeToken();
    const otherKey = generateEd25519KeyPair();
    const verifier = new TargetVerifier({
      publicKeys: [{ keyId: otherKey.keyId, algorithm: otherKey.algorithm, pem: otherKey.publicKey }],
    }, logger);

    const result = await verifier.verify({
      token,
      expectedAction: 'write',
      expectedResourceType: 'file',
      expectedResourceId: 'file-1',
    });
    expect(result.valid).toBe(false);
    expect(result.errors?.[0]?.code).toBe('KEY_NOT_FOUND');
  });
});
