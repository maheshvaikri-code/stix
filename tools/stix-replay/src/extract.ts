/**
 * STIX Replay - Evidence Extraction
 * Extract replay inputs from evidence bundles
 */

import * as fs from 'fs';
import * as path from 'path';
import { glob } from 'glob';
import type { EvidenceEvent } from '@stix/shared';
import type { RecordedDecision } from './types.js';

// =============================================================================
// BUNDLE LOADING
// =============================================================================

/**
 * Load evidence bundles from a file or directory
 */
export async function loadBundles(bundlePath: string): Promise<any[]> {
  const stat = fs.statSync(bundlePath);
  const bundles: any[] = [];

  if (stat.isDirectory()) {
    const files = await glob('**/*.{json,jsonl}', {
      cwd: bundlePath,
      absolute: true,
    });

    for (const file of files) {
      const fileBundles = await loadBundleFile(file);
      bundles.push(...fileBundles);
    }
  } else {
    const fileBundles = await loadBundleFile(bundlePath);
    bundles.push(...fileBundles);
  }

  return bundles;
}

/**
 * Load bundles from a single file
 */
async function loadBundleFile(filePath: string): Promise<any[]> {
  const content = fs.readFileSync(filePath, 'utf-8');
  const ext = path.extname(filePath).toLowerCase();

  if (ext === '.jsonl') {
    // JSONL: each line is a bundle or event
    const lines = content.split('\n').filter(l => l.trim());
    return lines.map(l => JSON.parse(l));
  }

  // JSON: single bundle or array
  const parsed = JSON.parse(content);

  if (Array.isArray(parsed)) {
    // Array of bundles
    return parsed;
  }

  if (parsed.events && Array.isArray(parsed.events)) {
    // Single bundle with events array
    return [parsed];
  }

  if (parsed.trace_id) {
    // Single event - wrap in bundle-like structure
    return [{ trace_id: parsed.trace_id, events: [parsed] }];
  }

  return [parsed];
}

// =============================================================================
// EXTRACTION
// =============================================================================

/**
 * Extract replay input from an evidence bundle
 */
export function extractFromBundle(bundle: any): RecordedDecision {
  // Handle different bundle formats
  let events: EvidenceEvent[];

  if (bundle.events && Array.isArray(bundle.events)) {
    events = bundle.events;
  } else if (Array.isArray(bundle)) {
    events = bundle;
  } else {
    // Single event
    events = [bundle];
  }

  // Find DECISION event
  const decisionEvent = events.find((e: any) =>
    e.event_type === 'DECISION' ||
    (e.decision !== undefined && e.actor !== undefined)
  );

  if (!decisionEvent) {
    throw new Error('Bundle missing DECISION event');
  }

  // Extract fields - handle both flat and payload formats
  const payload = (decisionEvent as any).payload || decisionEvent;

  const actor = payload.actor || decisionEvent.actor;
  const action = payload.action || decisionEvent.action;
  const resource = payload.resource || decisionEvent.resource;
  const context = payload.context || decisionEvent.context;
  const decision = payload.decision || decisionEvent.decision;
  const reasonCode = payload.reason_code || decisionEvent.reason_code || '';
  const policyHash = payload.policy_hash || payload.policy?.hash || decisionEvent.policy?.hash || '';
  const policyId = payload.policy_id || payload.policy?.id || decisionEvent.policy?.id || '';

  // Validate required fields
  if (!actor) throw new Error('DECISION event missing actor');
  if (!action) throw new Error('DECISION event missing action');
  if (!resource) throw new Error('DECISION event missing resource');
  if (!decision) throw new Error('DECISION event missing decision');

  // Extract obligations
  const obligations = payload.obligations || (decisionEvent as any).obligations || [];
  const obligationTypes = obligations.map((o: any) =>
    typeof o === 'string' ? o : o.type
  );

  return {
    trace_id: decisionEvent.trace_id || bundle.trace_id,
    timestamp: decisionEvent.timestamp,
    actor,
    action: typeof action === 'string' ? action : action.name || 'unknown',
    resource,
    context: context || { env: 'prod' },
    recorded: {
      decision,
      reason_code: reasonCode,
      obligations: obligationTypes,
      policy_id: policyId,
      policy_hash: policyHash,
    },
  };
}

/**
 * Extract multiple decisions from bundles
 */
export function extractMultiple(bundles: any[]): RecordedDecision[] {
  const decisions: RecordedDecision[] = [];

  for (const bundle of bundles) {
    try {
      const decision = extractFromBundle(bundle);
      decisions.push(decision);
    } catch (error) {
      // Skip bundles that can't be extracted
      console.warn(`Failed to extract from bundle: ${(error as Error).message}`);
    }
  }

  return decisions;
}

/**
 * Validate that a bundle has sufficient data for replay
 */
export function validateForReplay(bundle: any): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  try {
    const decision = extractFromBundle(bundle);

    if (!decision.recorded.policy_hash) {
      errors.push('Missing policy_hash - cannot verify policy match');
    }

    if (!decision.actor.type) {
      errors.push('Missing actor.type');
    }

    if (!decision.resource.type) {
      errors.push('Missing resource.type');
    }

  } catch (error) {
    errors.push((error as Error).message);
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
