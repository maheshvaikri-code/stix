import fs from 'node:fs';
import path from 'node:path';

function arg(name, fallback) {
  const idx = process.argv.indexOf(`--${name}`);
  if (idx === -1) return fallback;
  return process.argv[idx + 1] ?? fallback;
}

function usage() {
  return `
Usage:
  node scripts/integrations/combined-architecture-adapter.mjs \\
    --provider <bedrock|azure|vertex|generic> \\
    --provider-input <json-file> \\
    --stix-request <json-file> \\
    --enforcer-url <base-url> \\
    [--dry-run <true|false>] \\
    [--api-key <key>] \\
    [--output <json-file>]
`;
}

function loadJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function boolFrom(value, fallback = false) {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'number') return value !== 0;
  if (typeof value === 'string') {
    const normalized = value.toLowerCase();
    if (['true', 'yes', '1', 'block', 'blocked'].includes(normalized)) return true;
    if (['false', 'no', '0', 'allow', 'allowed', 'none'].includes(normalized)) return false;
  }
  return fallback;
}

function toRiskTier(score) {
  if (score >= 0.85) return 'CRITICAL';
  if (score >= 0.65) return 'HIGH';
  if (score >= 0.35) return 'MEDIUM';
  return 'LOW';
}

function normalizeBedrock(payload) {
  const action = String(payload?.guardrail?.action ?? payload?.action ?? '').toUpperCase();
  const promptInjection = boolFrom(
    payload?.guardrail?.promptInjection ??
      payload?.guardrail?.prompt_injection ??
      payload?.promptInjection,
    false
  );
  const piiDetected = boolFrom(payload?.guardrail?.piiDetected ?? payload?.piiDetected, false);
  const score = Number(payload?.guardrail?.score ?? payload?.score ?? 0.2);
  const blockRecommended = action === 'BLOCKED' || promptInjection;
  const reasons = [];
  if (action === 'BLOCKED') reasons.push('provider_action_blocked');
  if (promptInjection) reasons.push('prompt_injection_detected');
  if (piiDetected) reasons.push('pii_detected');

  return {
    provider: 'bedrock',
    blockRecommended,
    riskTier: blockRecommended ? 'HIGH' : toRiskTier(score),
    piiDetected,
    promptInjectionDetected: promptInjection,
    reasons,
  };
}

function normalizeAzure(payload) {
  const jailbreak = boolFrom(
    payload?.promptShield?.attackDetected ??
      payload?.promptShield?.jailbreakDetected ??
      payload?.jailbreakDetected,
    false
  );
  const piiDetected = boolFrom(payload?.pii?.detected ?? payload?.piiDetected, false);
  const blocked = boolFrom(
    payload?.contentSafety?.blocked ??
      payload?.contentSafety?.blocklisted ??
      payload?.blocked,
    false
  );
  const severity = String(payload?.contentSafety?.severity ?? 'medium').toLowerCase();
  const riskTier =
    severity === 'high' ? 'HIGH' : severity === 'critical' ? 'CRITICAL' : 'MEDIUM';
  const blockRecommended = blocked || jailbreak;
  const reasons = [];
  if (blocked) reasons.push('content_safety_blocked');
  if (jailbreak) reasons.push('jailbreak_detected');
  if (piiDetected) reasons.push('pii_detected');

  return {
    provider: 'azure',
    blockRecommended,
    riskTier: blockRecommended ? 'HIGH' : riskTier,
    piiDetected,
    promptInjectionDetected: jailbreak,
    reasons,
  };
}

function normalizeVertex(payload) {
  const safetyRatings = Array.isArray(payload?.safetyRatings) ? payload.safetyRatings : [];
  const hasBlockedRating = safetyRatings.some((rating) => boolFrom(rating?.blocked, false));
  const highProbability = safetyRatings.some((rating) => {
    const value = String(rating?.probability ?? '').toUpperCase();
    return value === 'HIGH' || value === 'VERY_HIGH';
  });
  const blockReason = String(payload?.promptFeedback?.blockReason ?? '').trim();
  const piiDetected = boolFrom(payload?.piiDetected ?? false, false);
  const blockRecommended = hasBlockedRating || blockReason.length > 0;
  const reasons = [];
  if (hasBlockedRating) reasons.push('safety_rating_blocked');
  if (blockReason) reasons.push(`prompt_feedback:${blockReason}`);
  if (piiDetected) reasons.push('pii_detected');

  return {
    provider: 'vertex',
    blockRecommended,
    riskTier: blockRecommended ? 'HIGH' : highProbability ? 'MEDIUM' : 'LOW',
    piiDetected,
    promptInjectionDetected: false,
    reasons,
  };
}

function normalizeGeneric(payload, providerName) {
  const blockRecommended = boolFrom(payload?.blockRecommended ?? payload?.blocked, false);
  const piiDetected = boolFrom(payload?.piiDetected, false);
  const promptInjectionDetected = boolFrom(payload?.promptInjectionDetected, false);
  const riskTier = String(payload?.riskTier ?? 'MEDIUM').toUpperCase();
  const reasons = Array.isArray(payload?.reasons) ? payload.reasons.map(String) : [];
  return {
    provider: providerName,
    blockRecommended,
    riskTier: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].includes(riskTier) ? riskTier : 'MEDIUM',
    piiDetected,
    promptInjectionDetected,
    reasons,
  };
}

function normalizeProviderSignals(provider, payload) {
  switch (provider) {
    case 'bedrock':
      return normalizeBedrock(payload);
    case 'azure':
      return normalizeAzure(payload);
    case 'vertex':
      return normalizeVertex(payload);
    case 'generic':
      return normalizeGeneric(payload, 'generic');
    default:
      throw new Error(`Unsupported provider "${provider}". Expected bedrock|azure|vertex|generic.`);
  }
}

function buildAuthorizeRequest(baseRequest, normalized) {
  const cloned = structuredClone(baseRequest);
  const context = cloned.context ?? {};
  const existingSignals = context.signals ?? {};
  const existingCustom = existingSignals.custom ?? {};
  const existingTags = Array.isArray(context.tags) ? context.tags : [];

  cloned.context = {
    ...context,
    signals: {
      ...existingSignals,
      piiDetected: normalized.piiDetected || existingSignals.piiDetected,
      custom: {
        ...existingCustom,
        provider_block_recommended: normalized.blockRecommended,
        prompt_injection_detected: normalized.promptInjectionDetected,
      },
    },
    tags: [...new Set([...existingTags, `provider:${normalized.provider}`, `safety:${normalized.riskTier.toLowerCase()}`])],
    attributes: {
      ...(context.attributes ?? {}),
      guardrail: {
        provider: normalized.provider,
        blockRecommended: normalized.blockRecommended,
        riskTier: normalized.riskTier,
        reasons: normalized.reasons,
      },
    },
  };

  cloned.tool_call = {
    ...(cloned.tool_call ?? { tool: 'external-tool' }),
    risk_tier: normalized.riskTier,
    args_summary: cloned.tool_call?.args_summary ?? 'combined architecture adapter request',
  };

  return cloned;
}

async function main() {
  const provider = String(arg('provider', '')).toLowerCase();
  const providerInputFile = arg('provider-input', '');
  const stixRequestFile = arg('stix-request', '');
  const enforcerUrl = arg('enforcer-url', 'http://localhost:3001');
  const dryRun = boolFrom(arg('dry-run', 'false'), false);
  const apiKey = arg('api-key', '');
  const outputFile = arg('output', '');

  if (!provider || !providerInputFile || !stixRequestFile) {
    throw new Error(`Missing required arguments.\n${usage()}`);
  }

  const providerPayload = loadJson(providerInputFile);
  const baseStixRequest = loadJson(stixRequestFile);
  const normalized = normalizeProviderSignals(provider, providerPayload);
  const authorizeRequest = buildAuthorizeRequest(baseStixRequest, normalized);

  let stixDecision = null;
  let combinedResult = null;

  if (!dryRun) {
    const endpoint = `${enforcerUrl.replace(/\/$/, '')}/api/v1/authorize`;
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['x-stix-api-key'] = apiKey;

    const response = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(authorizeRequest),
    });

    const bodyText = await response.text();
    if (!response.ok) {
      throw new Error(`Enforcer call failed (${response.status}): ${bodyText}`);
    }

    stixDecision = JSON.parse(bodyText);
    const finalDecision = normalized.blockRecommended ? 'DENY' : stixDecision.decision;
    combinedResult = {
      provider: normalized.provider,
      provider_block_recommended: normalized.blockRecommended,
      provider_reasons: normalized.reasons,
      stix_decision: stixDecision.decision,
      stix_reason_code: stixDecision.reason_code,
      trace_id: stixDecision.trace_id,
      final_gate_decision: finalDecision,
      enforce: finalDecision === 'ALLOW',
    };
  } else {
    combinedResult = {
      provider: normalized.provider,
      provider_block_recommended: normalized.blockRecommended,
      provider_reasons: normalized.reasons,
      stix_decision: 'SKIPPED_DRY_RUN',
      stix_reason_code: 'SKIPPED_DRY_RUN',
      trace_id: null,
      final_gate_decision: normalized.blockRecommended ? 'DENY' : 'ALLOW',
      enforce: !normalized.blockRecommended,
    };
  }

  if (outputFile) {
    fs.mkdirSync(path.dirname(outputFile), { recursive: true });
    fs.writeFileSync(
      outputFile,
      JSON.stringify(
        {
          normalized_provider: normalized,
          stix_request: authorizeRequest,
          stix_response: stixDecision,
          combined_result: combinedResult,
        },
        null,
        2
      ),
      'utf8'
    );
    console.log(`Wrote ${outputFile}`);
  }

  console.log(JSON.stringify(combinedResult, null, 2));
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
