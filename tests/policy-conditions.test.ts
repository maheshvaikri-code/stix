import { describe, expect, it } from 'vitest';
import { evaluateConditions, type ConditionContext } from '../services/policy/src/core/conditions.js';

const baseContext: ConditionContext = {
  actor: {
    id: 'agent-1',
    type: 'AI_AGENT',
    attributes: {},
  },
  resource: {
    type: 'tool',
    attributes: {},
  },
  context: {
    env: 'prod',
    signals: {},
    attributes: {},
  },
};

describe('policy condition evaluation', () => {
  it('honors policy-pack require_signal conditions', () => {
    expect(
      evaluateConditions(
        { require_signal: { phiDetected: true } },
        {
          ...baseContext,
          context: { ...baseContext.context, signals: { phiDetected: true } },
        },
      ),
    ).toBe(true);

    expect(evaluateConditions({ require_signal: { phiDetected: true } }, baseContext)).toBe(false);
  });

  it('honors env and resource attribute guards before broad rules match', () => {
    expect(evaluateConditions({ env: 'prod' }, baseContext)).toBe(true);
    expect(evaluateConditions({ env: 'dev' }, baseContext)).toBe(false);

    expect(
      evaluateConditions(
        { require_resource_attr: { risk_tier: 'HIGH' } },
        {
          ...baseContext,
          resource: { ...baseContext.resource, attributes: { risk_tier: 'HIGH' } },
        },
      ),
    ).toBe(true);

    expect(
      evaluateConditions({ require_resource_attr: { risk_tier: 'HIGH' } }, baseContext),
    ).toBe(false);
  });
});
