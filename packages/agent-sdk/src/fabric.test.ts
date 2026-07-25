/**
 * STIX Agent SDK - Fabric bridge tests.
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { MockAgent, getGlobalDispatcher, setGlobalDispatcher, type Dispatcher } from 'undici';
import { FabricClient, createStixAgent } from './fabric';

let mockAgent: MockAgent;
let previousDispatcher: Dispatcher;

const testAgent = {
  agent_id: 'agent_sdk_test_001',
  display_name: 'SDK Test Agent',
  owner: 'platform',
  runtime: 'vitest',
  environment: 'test' as const,
  risk_tier: 'MEDIUM' as const,
  status: 'ACTIVE' as const,
  labels: ['sdk'],
  metadata: {},
  created_at: '2026-07-25T00:00:00.000Z',
  updated_at: '2026-07-25T00:00:00.000Z',
};

const testEnforcementPoint = {
  enforcement_point_id: 'ep_agent_sdk_test_001_sdk',
  display_name: 'SDK Test Agent SDK Enforcement',
  type: 'sdk' as const,
  environment: 'test' as const,
  status: 'ACTIVE' as const,
  agent_ids: ['agent_sdk_test_001'],
  metadata: { source: '@stix/agent-sdk' },
  created_at: '2026-07-25T00:00:00.000Z',
  updated_at: '2026-07-25T00:00:00.000Z',
};

const testToolAction = {
  action_id: 'send_email',
  display_name: 'send_email',
  action: 'send_email',
  resource_type: 'email',
  risk_tier: 'HIGH' as const,
  approval_required: true,
  allowed_environments: ['test' as const],
  metadata: { description: 'Send a customer email' },
  created_at: '2026-07-25T00:00:00.000Z',
  updated_at: '2026-07-25T00:00:00.000Z',
};

beforeEach(() => {
  previousDispatcher = getGlobalDispatcher();
  mockAgent = new MockAgent();
  mockAgent.disableNetConnect();
  setGlobalDispatcher(mockAgent);
});

afterEach(async () => {
  mockAgent.assertNoPendingInterceptors();
  await mockAgent.close();
  setGlobalDispatcher(previousDispatcher);
});

describe('FabricClient', () => {
  it('registers agents with Fabric service-token auth', async () => {
    const fabric = mockAgent.get('http://fabric.test');
    fabric
      .intercept({
        method: 'POST',
        path: '/api/v1/fabric/agents',
        headers: { 'x-stix-service-token': 'fabric-secret' },
      })
      .reply(201, testAgent);

    const client = new FabricClient({
      fabricUrl: 'http://fabric.test',
      serviceToken: 'fabric-secret',
      retries: 0,
    });

    await expect(
      client.registerAgent({
        agent_id: 'agent_sdk_test_001',
        display_name: 'SDK Test Agent',
        owner: 'platform',
        runtime: 'vitest',
        environment: 'test',
        risk_tier: 'MEDIUM',
      })
    ).resolves.toMatchObject({ agent_id: 'agent_sdk_test_001' });
  });

  it('reads Fabric graph summaries', async () => {
    const fabric = mockAgent.get('http://fabric.test');
    fabric.intercept({ method: 'GET', path: '/api/v1/fabric/graph/summary' }).reply(200, {
      nodes: [{ id: 'agent_sdk_test_001', type: 'agent', label: 'SDK Test Agent' }],
      edges: [],
      stats: {
        agents: 1,
        enforcement_points: 0,
        tool_actions: 0,
        policy_channels: 0,
        active_agents: 1,
        active_enforcement_points: 0,
        critical_tool_actions: 0,
      },
    });

    const client = new FabricClient({ fabricUrl: 'http://fabric.test', retries: 0 });
    const graph = await client.getGraphSummary();

    expect(graph.stats.agents).toBe(1);
    expect(graph.nodes[0]?.id).toBe('agent_sdk_test_001');
  });
});

describe('createStixAgent', () => {
  it('auto-registers agent, SDK enforcement point, and tools before executing through STIX Core', async () => {
    const fabric = mockAgent.get('http://fabric.test');
    fabric.intercept({ method: 'POST', path: '/api/v1/fabric/agents' }).reply(201, testAgent);
    fabric.intercept({ method: 'POST', path: '/api/v1/fabric/enforcement-points' }).reply(201, testEnforcementPoint);
    fabric.intercept({ method: 'POST', path: '/api/v1/fabric/tool-actions' }).reply(201, testToolAction);

    const enforcer = mockAgent.get('http://enforcer.test');
    enforcer.intercept({ method: 'POST', path: '/api/v1/authorize' }).reply(200, {
      decision: 'ALLOW',
      trace_id: 'stix_trace_sdk_test',
      reason_code: 'POLICY_ALLOW',
      obligations: [],
      controls: [],
      regulations: [],
      proof_token: 'header.payload.signature',
    });
    enforcer.intercept({ method: 'POST', path: '/api/v1/outcome' }).reply(200, { success: true });

    const runtime = await createStixAgent({
      enforcerUrl: 'http://enforcer.test',
      fabricUrl: 'http://fabric.test',
      retries: 0,
      agent: {
        agent_id: 'agent_sdk_test_001',
        display_name: 'SDK Test Agent',
        owner: 'platform',
        runtime: 'vitest',
        environment: 'test',
        risk_tier: 'MEDIUM',
      },
      tools: [
        {
          name: 'send_email',
          description: 'Send a customer email',
          action: 'send_email',
          resourceType: 'email',
          riskTier: 'HIGH',
          getResource: (args: { to: string }) => ({ type: 'email', id: args.to }),
          execute: async (args: { to: string }) => ({ sent: true, to: args.to }),
        },
      ],
    });

    expect(runtime.agent.agent_id).toBe('agent_sdk_test_001');
    expect(runtime.enforcementPoint?.type).toBe('sdk');
    expect(runtime.toolActions).toHaveLength(1);
    expect(runtime.registry.has('send_email')).toBe(true);

    const result = await runtime.execute<{ to: string }, { sent: boolean; to: string }>('send_email', {
      to: 'customer@example.com',
    });

    expect(result.success).toBe(true);
    expect(result.authorization.traceId).toBe('stix_trace_sdk_test');
    expect(result.result).toEqual({ sent: true, to: 'customer@example.com' });
  });

  it('can create a local wrapped runtime without automatic Fabric writes', async () => {
    const runtime = await createStixAgent({
      enforcerUrl: 'http://enforcer.test',
      fabricUrl: 'http://fabric.test',
      retries: 0,
      registerOnCreate: false,
      agent: {
        agent_id: 'agent_local_only_001',
        display_name: 'Local Only Agent',
        owner: 'platform',
        runtime: 'vitest',
        environment: 'test',
        risk_tier: 'LOW',
      },
      tools: [
        {
          name: 'read_local',
          action: 'read_local',
          resourceType: 'local_resource',
          riskTier: 'LOW',
          execute: async () => ({ ok: true }),
        },
      ],
    });

    expect(runtime.agent.agent_id).toBe('agent_local_only_001');
    expect(runtime.enforcementPoint).toBeUndefined();
    expect(runtime.toolActions).toHaveLength(0);
    expect(runtime.registry.has('read_local')).toBe(true);
  });
});
