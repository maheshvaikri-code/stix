/**
 * STIX Simulation - Evidence Loader
 * Load and parse evidence bundles for simulation
 */

import * as fs from 'fs';
import * as path from 'path';
import { glob } from 'glob';
import type { EvidenceEvent } from '@stix/shared';
import type { SimulationInput } from './types.js';

// =============================================================================
// EVIDENCE LOADING
// =============================================================================

/**
 * Load evidence bundles from a directory or file
 */
export async function loadEvidenceBundles(
  evidencePath: string,
  options?: {
    since?: string;
    until?: string;
    strict?: boolean;
  }
): Promise<SimulationInput[]> {
  const inputs: SimulationInput[] = [];

  const stat = fs.statSync(evidencePath);

  if (stat.isDirectory()) {
    // Load all JSON/JSONL files from directory
    const files = await glob('**/*.{json,jsonl,ndjson}', {
      cwd: evidencePath,
      absolute: true,
    });

    for (const file of files) {
      const fileInputs = await loadEvidenceFile(file, options);
      inputs.push(...fileInputs);
    }
  } else {
    // Load single file
    const fileInputs = await loadEvidenceFile(evidencePath, options);
    inputs.push(...fileInputs);
  }

  // Sort by timestamp
  inputs.sort((a, b) => a.timestamp.localeCompare(b.timestamp));

  return inputs;
}

/**
 * Load evidence from a single file
 */
async function loadEvidenceFile(
  filePath: string,
  options?: {
    since?: string;
    until?: string;
    strict?: boolean;
  }
): Promise<SimulationInput[]> {
  const content = fs.readFileSync(filePath, 'utf-8');
  const ext = path.extname(filePath).toLowerCase();

  let events: EvidenceEvent[];

  if (ext === '.jsonl' || ext === '.ndjson') {
    // JSONL format: one event per line
    events = content
      .split('\n')
      .filter(line => line.trim())
      .map(line => JSON.parse(line) as EvidenceEvent);
  } else {
    // JSON format: array, single object, or bundle
    const parsed = JSON.parse(content);

    if (Array.isArray(parsed)) {
      events = parsed.flatMap((item) =>
        item?.events && Array.isArray(item.events) ? item.events : [item]
      );
    } else if (parsed.events && Array.isArray(parsed.events)) {
      // Bundle format
      events = parsed.events;
    } else {
      events = [parsed];
    }
  }

  return extractSimulationInputs(events, options);
}

/**
 * Extract simulation inputs from evidence events
 */
function extractSimulationInputs(
  events: EvidenceEvent[],
  options?: {
    since?: string;
    until?: string;
    strict?: boolean;
  }
): SimulationInput[] {
  const inputs: SimulationInput[] = [];

  // Group events by trace_id
  const byTrace = new Map<string, EvidenceEvent[]>();
  for (const event of events) {
    const existing = byTrace.get(event.trace_id) || [];
    existing.push(event);
    byTrace.set(event.trace_id, existing);
  }

  for (const [traceId, traceEvents] of byTrace) {
    // Find DECISION event
    const decisionEvent = traceEvents.find(e =>
      (e as any).event_type === 'DECISION' || (e as any).decision !== undefined
    );

    if (!decisionEvent) continue;

    // In strict mode, require OUTCOME event too
    if (options?.strict) {
      const outcomeEvent = traceEvents.find(e =>
        (e as any).event_type === 'OUTCOME' || (e as any).outcome !== undefined
      );
      if (!outcomeEvent) continue;
    }

    // Apply time filters
    if (options?.since && decisionEvent.timestamp < options.since) continue;
    if (options?.until && decisionEvent.timestamp > options.until) continue;

    // Extract simulation input
    const input = extractInputFromDecision(decisionEvent);
    if (input) {
      inputs.push(input);
    }
  }

  return inputs;
}

/**
 * Extract simulation input from a decision event
 */
function extractInputFromDecision(event: EvidenceEvent): SimulationInput | null {
  try {
    // Handle different evidence formats
    const decision = event.decision || (event as any).payload?.decision;
    const actor = event.actor || (event as any).payload?.actor;
    const action = event.action || (event as any).payload?.action;
    const resource = event.resource || (event as any).payload?.resource;
    const context = event.context || (event as any).payload?.context;
    const policy = event.policy || (event as any).payload?.policy;

    if (!decision || !actor || !resource) {
      return null;
    }

    // Extract obligations
    const obligations = (event as any).obligations ||
                       (event as any).payload?.obligations ||
                       [];
    const obligationTypes = obligations.map((o: any) =>
      typeof o === 'string' ? o : o.type
    );

    return {
      trace_id: event.trace_id,
      timestamp: event.timestamp,
      actor: actor,
      action: typeof action === 'string' ? action : action?.name || 'unknown',
      resource: resource,
      context: context || { env: 'prod' },
      recorded_decision: decision as any,
      recorded_policy_hash: policy?.hash || 'unknown',
      recorded_policy_id: policy?.id || 'unknown',
      recorded_obligations: obligationTypes,
    };
  } catch (error) {
    console.error(`Failed to extract input from event ${event.event_id}:`, error);
    return null;
  }
}

/**
 * Get evidence statistics
 */
export function getEvidenceStats(inputs: SimulationInput[]): {
  total: number;
  byDecision: Record<string, number>;
  timeRange: { first: string; last: string } | null;
  uniqueActors: number;
  uniqueActions: number;
  uniqueResourceTypes: number;
} {
  const stats = {
    total: inputs.length,
    byDecision: { ALLOW: 0, DENY: 0, QUARANTINE: 0 } as Record<string, number>,
    timeRange: null as { first: string; last: string } | null,
    uniqueActors: 0,
    uniqueActions: 0,
    uniqueResourceTypes: 0,
  };

  if (inputs.length === 0) return stats;

  const actors = new Set<string>();
  const actions = new Set<string>();
  const resourceTypes = new Set<string>();

  for (const input of inputs) {
    stats.byDecision[input.recorded_decision] =
      (stats.byDecision[input.recorded_decision] || 0) + 1;
    actors.add(input.actor.id);
    actions.add(input.action);
    resourceTypes.add(input.resource.type);
  }

  stats.uniqueActors = actors.size;
  stats.uniqueActions = actions.size;
  stats.uniqueResourceTypes = resourceTypes.size;

  const sorted = [...inputs].sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  stats.timeRange = {
    first: sorted[0].timestamp,
    last: sorted[sorted.length - 1].timestamp,
  };

  return stats;
}
