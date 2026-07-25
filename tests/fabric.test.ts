/**
 * STIX Fabric control-plane API tests.
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { createApp, type AppContext } from '@stix/fabric';
import { loadConfig } from '../services/fabric/src/config/index.js';

const originalEnv = { ...process.env };

describe('STIX Fabric service', () => {
  let app: AppContext | undefined;

  beforeEach(() => {
    process.env = {
      ...originalEnv,
      NODE_ENV: 'test',
      LOG_LEVEL: 'error',
      LOG_PRETTY: 'false',
      SERVICE_TOKEN_AUTH_ENABLED: 'false',
      STORAGE_TYPE: 'memory',
    };
  });

  afterEach(async () => {
    if (app) {
      await app.server.close();
      app = undefined;
    }
    process.env = { ...originalEnv };
  });

  it('reports health and readiness', async () => {
    app = await createApp();

    const health = await app.server.inject({ method: 'GET', url: '/health' });
    expect(health.statusCode).toBe(200);
    expect(health.json()).toMatchObject({
      status: 'healthy',
      service: 'stix-fabric',
    });

    const ready = await app.server.inject({ method: 'GET', url: '/ready' });
    expect(ready.statusCode).toBe(200);
    expect(ready.json()).toMatchObject({
      ready: true,
      service: 'stix-fabric',
    });
  });

  it('registers agents, enforcement points, tool actions, and policy channels into a graph', async () => {
    app = await createApp();

    const agentResponse = await app.server.inject({
      method: 'POST',
      url: '/api/v1/fabric/agents',
      payload: {
        agent_id: 'agent_test_001',
        display_name: 'Claims Automation Agent',
        owner: 'compliance-ops',
        runtime: 'codex',
        environment: 'prod',
        risk_tier: 'HIGH',
        labels: ['claims', 'phi'],
      },
    });
    expect(agentResponse.statusCode).toBe(201);

    const enforcementPointResponse = await app.server.inject({
      method: 'POST',
      url: '/api/v1/fabric/enforcement-points',
      payload: {
        enforcement_point_id: 'ep_sdk_001',
        display_name: 'Agent SDK Wrapper',
        type: 'sdk',
        environment: 'prod',
        agent_ids: ['agent_test_001'],
      },
    });
    expect(enforcementPointResponse.statusCode).toBe(201);

    const toolActionResponse = await app.server.inject({
      method: 'POST',
      url: '/api/v1/fabric/tool-actions',
      payload: {
        action_id: 'action_write_claim',
        display_name: 'Write Claim Record',
        action: 'write_claim',
        resource_type: 'claim_record',
        risk_tier: 'CRITICAL',
        approval_required: true,
        allowed_environments: ['prod'],
      },
    });
    expect(toolActionResponse.statusCode).toBe(201);

    const channelResponse = await app.server.inject({
      method: 'POST',
      url: '/api/v1/fabric/policy-channels',
      payload: {
        channel_id: 'channel_prod',
        display_name: 'Production HIPAA Policy Channel',
        environment: 'prod',
        rollout_state: 'ACTIVE',
        active_bundle_id: 'hipaa-prod-v1',
      },
    });
    expect(channelResponse.statusCode).toBe(201);

    const statsResponse = await app.server.inject({ method: 'GET', url: '/api/v1/fabric/stats' });
    expect(statsResponse.statusCode).toBe(200);
    expect(statsResponse.json()).toMatchObject({
      agents: 1,
      enforcement_points: 1,
      tool_actions: 1,
      policy_channels: 1,
      critical_tool_actions: 1,
    });

    const graphResponse = await app.server.inject({ method: 'GET', url: '/api/v1/fabric/graph/summary' });
    expect(graphResponse.statusCode).toBe(200);
    expect(graphResponse.json()).toMatchObject({
      stats: {
        agents: 1,
        enforcement_points: 1,
        tool_actions: 1,
        policy_channels: 1,
      },
    });
    expect(graphResponse.json().edges).toEqual(
      expect.arrayContaining([
        { from: 'agent_test_001', to: 'ep_sdk_001', relation: 'protected_by' },
        { from: 'agent_test_001', to: 'action_write_claim', relation: 'can_execute' },
        { from: 'agent_test_001', to: 'channel_prod', relation: 'governed_by' },
      ])
    );

    const readinessResponse = await app.server.inject({
      method: 'GET',
      url: '/api/v1/fabric/readiness',
    });
    expect(readinessResponse.statusCode).toBe(200);
    expect(readinessResponse.json()).toMatchObject({
      fabric: {
        score: 100,
        level: 'ready',
      },
      doctrine: {
        registered: false,
      },
    });
  });

  it('rejects invalid registry payloads', async () => {
    app = await createApp();

    const response = await app.server.inject({
      method: 'POST',
      url: '/api/v1/fabric/tool-actions',
      payload: {
        display_name: 'Incomplete Tool Action',
        risk_tier: 'CRITICAL',
      },
    });

    expect(response.statusCode).toBe(400);
    expect(response.json()).toMatchObject({ error: 'Validation failed' });
  });

  it('enforces service-token auth when enabled while keeping health endpoints public', async () => {
    process.env.SERVICE_TOKEN_AUTH_ENABLED = 'true';
    process.env.SERVICE_AUTH_TOKEN = 'fabric-test-token';
    app = await createApp();

    const health = await app.server.inject({ method: 'GET', url: '/health' });
    expect(health.statusCode).toBe(200);

    const unauthenticated = await app.server.inject({
      method: 'GET',
      url: '/api/v1/fabric/agents',
    });
    expect(unauthenticated.statusCode).toBe(401);

    const authenticated = await app.server.inject({
      method: 'GET',
      url: '/api/v1/fabric/agents',
      headers: { 'x-stix-service-token': 'fabric-test-token' },
    });
    expect(authenticated.statusCode).toBe(200);
  });

  it('requires durable storage in production mode', () => {
    process.env.NODE_ENV = 'prod';
    process.env.STORAGE_TYPE = 'memory';
    process.env.SERVICE_TOKEN_AUTH_ENABLED = 'false';

    expect(() => loadConfig()).toThrow(/durable registry backend/);
  });

  it('requires POSTGRES_URL when postgres storage is enabled', () => {
    process.env.NODE_ENV = 'test';
    process.env.STORAGE_TYPE = 'postgres';
    process.env.POSTGRES_URL = '';

    expect(() => loadConfig()).toThrow(/POSTGRES_URL/);
  });
});
