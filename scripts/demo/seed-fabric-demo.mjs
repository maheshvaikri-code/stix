#!/usr/bin/env node

/**
 * Seed a running STIX Fabric API with a deterministic demo inventory.
 *
 * The records use stable IDs, so the script is safe to run repeatedly against
 * the memory or Postgres registry backends.
 */

const fabricUrl = (process.env.STIX_FABRIC_URL ?? 'http://localhost:3005').replace(/\/$/, '');
const timeoutMs = Number.parseInt(process.env.STIX_DEMO_TIMEOUT_MS ?? '10000', 10);

const demoRecords = [
  {
    path: '/api/v1/fabric/agents',
    body: {
      agent_id: 'agent_doctrine_os',
      display_name: 'Doctrine Engineering OS',
      owner: 'engineering-governance',
      runtime: 'doctrineos',
      environment: 'prod',
      risk_tier: 'HIGH',
      status: 'ACTIVE',
      labels: ['gates', 'evidence', 'release'],
      metadata: {
        lane: 'production',
        role: 'engineering-operating-system',
        gates: ['G0', 'G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7'],
        seed: 'stix-fabric-demo',
      },
    },
  },
  {
    path: '/api/v1/fabric/agents',
    body: {
      agent_id: 'agent_release_captain',
      display_name: 'Autonomous Release Captain',
      owner: 'platform-security',
      runtime: 'codex',
      environment: 'prod',
      risk_tier: 'HIGH',
      status: 'ACTIVE',
      labels: ['release', 'codex', 'fabric'],
      metadata: {
        lane: 'production',
        posture: 'governed',
        proof_tokens: 'required',
        seed: 'stix-fabric-demo',
      },
    },
  },
  {
    path: '/api/v1/fabric/agents',
    body: {
      agent_id: 'agent_clinical_reviewer',
      display_name: 'Clinical Compliance Reviewer',
      owner: 'healthcare-governance',
      runtime: 'claude',
      environment: 'stage',
      risk_tier: 'CRITICAL',
      status: 'QUARANTINED',
      labels: ['hipaa', 'phi', 'review'],
      metadata: {
        lane: 'staging',
        reason: 'pending human approval',
        policy_pack: 'hipaa-healthcare',
        seed: 'stix-fabric-demo',
      },
    },
  },
  {
    path: '/api/v1/fabric/agents',
    body: {
      agent_id: 'agent_finops_sentinel',
      display_name: 'FinOps Sentinel',
      owner: 'finance-platform',
      runtime: 'tool-runner',
      environment: 'prod',
      risk_tier: 'MEDIUM',
      status: 'ACTIVE',
      labels: ['sox', 'pci', 'evidence'],
      metadata: {
        lane: 'production',
        policy_pack: 'financial-sox-pci',
        seed: 'stix-fabric-demo',
      },
    },
  },
  {
    path: '/api/v1/fabric/enforcement-points',
    body: {
      enforcement_point_id: 'ep_doctrine_gatekeeper',
      display_name: 'Doctrine Gatekeeper',
      type: 'mcp_gateway',
      environment: 'prod',
      status: 'ACTIVE',
      url: 'http://localhost:3003',
      agent_ids: ['agent_doctrine_os', 'agent_release_captain'],
      metadata: {
        mode: 'gate-verification',
        transport: 'stdio://doctrineos',
        source: 'D:\\Doctrine\\Doctrine-System',
        seed: 'stix-fabric-demo',
      },
    },
  },
  {
    path: '/api/v1/fabric/enforcement-points',
    body: {
      enforcement_point_id: 'ep_agent_sdk_prod',
      display_name: 'Agent SDK Production Gateway',
      type: 'sdk',
      environment: 'prod',
      status: 'ACTIVE',
      url: 'http://localhost:3001/api/v1/authorize',
      agent_ids: ['agent_release_captain', 'agent_finops_sentinel'],
      metadata: {
        mode: 'proof-token',
        latency_budget_ms: 120,
        seed: 'stix-fabric-demo',
      },
    },
  },
  {
    path: '/api/v1/fabric/enforcement-points',
    body: {
      enforcement_point_id: 'ep_gitlab_ci',
      display_name: 'GitLab CI Policy Gate',
      type: 'ci',
      environment: 'prod',
      status: 'ACTIVE',
      agent_ids: ['agent_release_captain'],
      metadata: {
        branch: 'main',
        required_for_tags: true,
        seed: 'stix-fabric-demo',
      },
    },
  },
  {
    path: '/api/v1/fabric/tool-actions',
    body: {
      action_id: 'tool_doctrine_verify',
      display_name: 'Run Doctrine Verify Gates',
      action: 'doctrine_verify',
      resource_type: 'engineering_governance',
      risk_tier: 'HIGH',
      approval_required: false,
      allowed_environments: ['prod'],
      metadata: {
        gates: ['G3', 'G4', 'G5'],
        evidence: 'required',
        seed: 'stix-fabric-demo',
      },
    },
  },
  {
    path: '/api/v1/fabric/tool-actions',
    body: {
      action_id: 'tool_doctrine_checkpoint',
      display_name: 'Checkpoint Doctrine State',
      action: 'doctrine_checkpoint',
      resource_type: 'hash_chained_state_plane',
      risk_tier: 'MEDIUM',
      approval_required: false,
      allowed_environments: ['dev', 'test', 'stage', 'prod'],
      metadata: {
        state_plane: '.doctrine-state',
        seed: 'stix-fabric-demo',
      },
    },
  },
  {
    path: '/api/v1/fabric/tool-actions',
    body: {
      action_id: 'tool_deploy_prod',
      display_name: 'Deploy Production Release',
      action: 'deploy',
      resource_type: 'production_environment',
      risk_tier: 'CRITICAL',
      approval_required: true,
      allowed_environments: ['prod'],
      metadata: {
        proof: 'required',
        reviewers: 2,
        seed: 'stix-fabric-demo',
      },
    },
  },
  {
    path: '/api/v1/fabric/tool-actions',
    body: {
      action_id: 'tool_scan_diff',
      display_name: 'Scan Merge Request Diff',
      action: 'scan_diff',
      resource_type: 'source_code',
      risk_tier: 'HIGH',
      approval_required: true,
      allowed_environments: ['dev', 'test', 'stage', 'prod'],
      metadata: {
        scanners: ['pii', 'phi', 'pci', 'secrets'],
        seed: 'stix-fabric-demo',
      },
    },
  },
  {
    path: '/api/v1/fabric/tool-actions',
    body: {
      action_id: 'tool_replay_evidence',
      display_name: 'Replay Evidence Chain',
      action: 'replay_evidence',
      resource_type: 'audit_trail',
      risk_tier: 'MEDIUM',
      approval_required: false,
      allowed_environments: ['stage', 'prod'],
      metadata: {
        drift_tolerance: 'zero',
        seed: 'stix-fabric-demo',
      },
    },
  },
  {
    path: '/api/v1/fabric/policy-channels',
    body: {
      channel_id: 'channel_doctrine_gold_build',
      display_name: 'Doctrine Gold Build Gate',
      environment: 'prod',
      rollout_state: 'ACTIVE',
      active_bundle_id: 'bundle_0_1_9_doctrine',
      metadata: {
        coverage: 'g0-g7',
        promotion: 'signed-evidence-required',
        seed: 'stix-fabric-demo',
      },
    },
  },
  {
    path: '/api/v1/fabric/policy-channels',
    body: {
      channel_id: 'channel_prod_guardrails',
      display_name: 'Production Guardrails',
      environment: 'prod',
      rollout_state: 'ACTIVE',
      active_bundle_id: 'bundle_0_1_9_prod',
      metadata: {
        coverage: 'core+fabric',
        rollout: '100%',
        seed: 'stix-fabric-demo',
      },
    },
  },
  {
    path: '/api/v1/fabric/policy-channels',
    body: {
      channel_id: 'channel_stage_canary',
      display_name: 'Stage Canary Policies',
      environment: 'stage',
      rollout_state: 'CANARY',
      active_bundle_id: 'bundle_0_1_9_canary',
      metadata: {
        rollout: '25%',
        owner: 'platform-security',
        seed: 'stix-fabric-demo',
      },
    },
  },
];

async function main() {
  await request('/ready');

  for (const record of demoRecords) {
    await request(record.path, {
      method: 'POST',
      body: JSON.stringify(record.body),
    });
  }

  const [stats, graph] = await Promise.all([
    request('/api/v1/fabric/stats'),
    request('/api/v1/fabric/graph/summary'),
  ]);

  console.log('Seeded STIX Fabric demo inventory');
  console.log(`Fabric URL: ${fabricUrl}`);
  console.log(
    `Agents=${stats.agents} EnforcementPoints=${stats.enforcement_points} ToolActions=${stats.tool_actions} PolicyChannels=${stats.policy_channels}`
  );
  console.log(`GraphNodes=${graph.nodes.length} GraphEdges=${graph.edges.length}`);
}

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${fabricUrl}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers ?? {}),
      },
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`${options.method ?? 'GET'} ${path} failed (${response.status}): ${text}`);
    }

    return response.json();
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(`${options.method ?? 'GET'} ${path} timed out after ${timeoutMs}ms`);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

main().catch((error) => {
  console.error('Failed to seed STIX Fabric demo inventory');
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
