/**
 * STIX Fabric-aware Agent SDK example.
 *
 * Run after STIX Core/Fabric services are available:
 *   pnpm build
 *   pnpm exec tsx examples/fabric-agent-sdk.ts
 */

import { createStixAgent } from '@stix/agent-sdk';

const agent = await createStixAgent({
  enforcerUrl: process.env.STIX_ENFORCER_URL ?? 'http://localhost:3001',
  fabricUrl: process.env.STIX_FABRIC_URL ?? 'http://localhost:3005',
  apiKey: process.env.STIX_API_KEY,
  serviceToken: process.env.STIX_SERVICE_TOKEN,
  agent: {
    agent_id: 'agent_claims_assistant',
    display_name: 'Claims Assistant Agent',
    owner: 'compliance-ops',
    runtime: 'nodejs',
    environment: 'stage',
    risk_tier: 'HIGH',
    labels: ['claims', 'phi-review'],
  },
  tools: [
    {
      name: 'read_claim',
      description: 'Read a claim record by ID',
      action: 'read_claim',
      resourceType: 'claim_record',
      riskTier: 'MEDIUM',
      getResource: (args: { claimId: string }) => ({
        type: 'claim_record',
        id: args.claimId,
        classification: ['PHI'],
      }),
      execute: async (args: { claimId: string }) => ({
        claimId: args.claimId,
        status: 'review_ready',
      }),
    },
  ],
});

const result = await agent.execute<{ claimId: string }, { claimId: string; status: string }>('read_claim', {
  claimId: 'claim-123',
});

if (!result.success) {
  console.log('STIX blocked the tool call:', result.authorization.reasonCode);
  process.exitCode = 1;
} else {
  console.log('Tool executed with STIX proof context:', {
    traceId: result.authorization.traceId,
    result: result.result,
  });
}

const graph = await agent.getGraphSummary();
console.log('Fabric graph summary:', graph.stats);
