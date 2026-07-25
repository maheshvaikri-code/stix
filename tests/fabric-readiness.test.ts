/**
 * Dashboard Fabric readiness model tests.
 */

import { describe, expect, it } from 'vitest';
import type { FabricInventory } from '@stix/fabric-types';
import {
  buildDoctrinePosture,
  buildFabricPosture,
  getDoctrineInventory,
} from '@stix/fabric-types';

const now = '2026-07-25T00:00:00.000Z';

describe('Fabric readiness model', () => {
  it('marks a fully wired Fabric inventory as ready', () => {
    const posture = buildFabricPosture(createReadyInventory());

    expect(posture.score).toBe(100);
    expect(posture.level).toBe('ready');
    expect(posture.issues).toEqual([]);
    expect(posture.signals).toHaveLength(6);
  });

  it('reports release-blocking Fabric gaps with remediation', () => {
    const inventory = createReadyInventory();
    inventory.agents.data[0].status = 'QUARANTINED';
    inventory.stats.active_agents = 0;
    inventory.graph.edges = [];
    inventory.toolActions.data[2].approval_required = false;

    const posture = buildFabricPosture(inventory);

    expect(posture.level).toBe('blocked');
    expect(posture.issues.map((issue) => issue.id)).toContain(
      'critical-actions-without-approval',
    );
    expect(posture.issues.some((issue) => issue.remediation.length > 0)).toBe(
      true,
    );
  });

  it('computes Doctrine readiness from Fabric registry records', () => {
    const inventory = createReadyInventory();

    const doctrine = getDoctrineInventory(inventory);
    const posture = buildDoctrinePosture(inventory);

    expect(doctrine.agents).toHaveLength(1);
    expect(doctrine.enforcementPoints).toHaveLength(1);
    expect(doctrine.actions).toHaveLength(2);
    expect(doctrine.channels).toHaveLength(1);
    expect(posture.score).toBe(100);
    expect(posture.level).toBe('ready');
    expect(posture.counts.gates).toBe(8);
  });

  it('surfaces missing Doctrine controls before enforcement wrapping', () => {
    const inventory = createReadyInventory();
    inventory.toolActions.data = inventory.toolActions.data.filter(
      (action) => action.action_id !== 'tool_doctrine_checkpoint',
    );
    inventory.policyChannels.data[0].rollout_state = 'PAUSED';
    inventory.policyChannels.data[0].metadata = {};
    inventory.agents.data[0].metadata = {};

    const posture = buildDoctrinePosture(inventory);

    expect(posture.level).toBe('blocked');
    expect(posture.issues.map((issue) => issue.id)).toEqual(
      expect.arrayContaining([
        'doctrine-checkpoint-action',
        'doctrine-release-channel',
        'doctrine-g0-g7-coverage',
      ]),
    );
  });
});

function createReadyInventory(): FabricInventory {
  return {
    agents: {
      total: 1,
      data: [
        {
          agent_id: 'agent_doctrine_os',
          display_name: 'Doctrine Engineering OS',
          owner: 'engineering-governance',
          runtime: 'doctrineos',
          environment: 'prod',
          risk_tier: 'HIGH',
          status: 'ACTIVE',
          labels: ['doctrine', 'release'],
          metadata: {
            gates: ['G0', 'G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7'],
          },
          created_at: now,
          updated_at: now,
        },
      ],
    },
    enforcementPoints: {
      total: 1,
      data: [
        {
          enforcement_point_id: 'ep_doctrine_gatekeeper',
          display_name: 'Doctrine Gatekeeper',
          type: 'mcp_gateway',
          environment: 'prod',
          status: 'ACTIVE',
          url: 'http://localhost:3003',
          agent_ids: ['agent_doctrine_os'],
          metadata: {},
          created_at: now,
          updated_at: now,
        },
      ],
    },
    toolActions: {
      total: 3,
      data: [
        {
          action_id: 'tool_doctrine_verify',
          display_name: 'Run Doctrine Verify Gates',
          action: 'doctrine_verify',
          resource_type: 'engineering_governance',
          risk_tier: 'HIGH',
          approval_required: true,
          allowed_environments: ['prod'],
          metadata: {},
          created_at: now,
          updated_at: now,
        },
        {
          action_id: 'tool_doctrine_checkpoint',
          display_name: 'Checkpoint Doctrine State',
          action: 'doctrine_checkpoint',
          resource_type: 'hash_chained_state_plane',
          risk_tier: 'MEDIUM',
          approval_required: false,
          allowed_environments: ['prod'],
          metadata: {},
          created_at: now,
          updated_at: now,
        },
        {
          action_id: 'tool_deploy_prod',
          display_name: 'Deploy Production Release',
          action: 'deploy',
          resource_type: 'production_environment',
          risk_tier: 'CRITICAL',
          approval_required: true,
          allowed_environments: ['prod'],
          metadata: {},
          created_at: now,
          updated_at: now,
        },
      ],
    },
    policyChannels: {
      total: 1,
      data: [
        {
          channel_id: 'channel_doctrine_gold_build',
          display_name: 'Doctrine Gold Build Gate',
          environment: 'prod',
          rollout_state: 'ACTIVE',
          active_bundle_id: 'bundle_0_1_8_doctrine',
          metadata: {
            coverage: 'g0-g7',
          },
          created_at: now,
          updated_at: now,
        },
      ],
    },
    stats: {
      agents: 1,
      enforcement_points: 1,
      tool_actions: 3,
      policy_channels: 1,
      active_agents: 1,
      active_enforcement_points: 1,
      critical_tool_actions: 1,
    },
    graph: {
      nodes: [
        {
          id: 'agent_doctrine_os',
          type: 'agent',
          label: 'Doctrine Engineering OS',
          status: 'ACTIVE',
          risk_tier: 'HIGH',
        },
        {
          id: 'ep_doctrine_gatekeeper',
          type: 'enforcement_point',
          label: 'Doctrine Gatekeeper',
          status: 'ACTIVE',
        },
        {
          id: 'tool_doctrine_verify',
          type: 'tool_action',
          label: 'Run Doctrine Verify Gates',
          risk_tier: 'HIGH',
        },
        {
          id: 'channel_doctrine_gold_build',
          type: 'policy_channel',
          label: 'Doctrine Gold Build Gate',
          status: 'ACTIVE',
        },
      ],
      edges: [
        {
          from: 'agent_doctrine_os',
          to: 'ep_doctrine_gatekeeper',
          relation: 'protected_by',
        },
        {
          from: 'agent_doctrine_os',
          to: 'tool_doctrine_verify',
          relation: 'can_execute',
        },
        {
          from: 'agent_doctrine_os',
          to: 'channel_doctrine_gold_build',
          relation: 'governed_by',
        },
      ],
      stats: {
        agents: 1,
        enforcement_points: 1,
        tool_actions: 3,
        policy_channels: 1,
        active_agents: 1,
        active_enforcement_points: 1,
        critical_tool_actions: 1,
      },
    },
  };
}
