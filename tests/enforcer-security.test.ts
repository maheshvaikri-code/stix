import { describe, expect, it } from 'vitest';
import { loadConfig } from '../services/enforcer/src/config/index.js';
import { validateActorBinding } from '../services/enforcer/src/security/identity.js';

const identity = {
  actorId: 'workload-1',
  actorType: 'SERVICE' as const,
  tenant: 'tenant-1',
  role: 'writer',
};

describe('authenticated workload identity binding', () => {
  it('accepts exact actor, tenant, role, and attributes', () => {
    expect(validateActorBinding({
      id: 'workload-1',
      type: 'SERVICE',
      tenant: 'tenant-1',
      role: 'writer',
      attributes: {},
    }, identity)).toBeUndefined();
  });

  it('rejects request-supplied actor identity changes', () => {
    expect(validateActorBinding({
      id: 'spoofed-workload',
      type: 'SERVICE',
      tenant: 'tenant-1',
      role: 'writer',
    }, identity)).toContain('actor.id');
    expect(validateActorBinding({
      id: 'workload-1',
      type: 'SERVICE',
      tenant: 'other-tenant',
      role: 'writer',
    }, identity)).toContain('actor.tenant');
    expect(validateActorBinding({
      id: 'workload-1',
      type: 'SERVICE',
      tenant: 'tenant-1',
      role: 'admin',
    }, identity)).toContain('actor.role');
  });

  it('forces closed failure mode in enterprise mode', () => {
    const previous = { ...process.env };
    process.env.NODE_ENV = 'stage';
    process.env.ENTERPRISE_MODE = 'true';
    process.env.DEFAULT_FAIL_MODE = 'OPEN';
    process.env.API_KEYS = 'key-1';
    process.env.WORKLOAD_IDENTITIES = JSON.stringify({
      'key-1': identity,
    });

    try {
      const config = loadConfig();
      expect(config.authorization.enterpriseMode).toBe(true);
      expect(config.authorization.defaultFailMode).toBe('CLOSED');
      expect(config.security.apiKeyAuthEnabled).toBe(true);
    } finally {
      for (const key of Object.keys(process.env)) {
        if (!(key in previous)) delete process.env[key];
      }
      for (const [key, value] of Object.entries(previous)) {
        process.env[key] = value;
      }
    }
  });
});
