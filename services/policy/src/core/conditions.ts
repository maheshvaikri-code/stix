/**
 * Policy condition evaluation
 * Evaluates time windows, signals, attributes, and custom conditions
 */

import type { PolicyConditions } from '@stix/shared';

export interface ConditionContext {
  context: {
    env: string;
    purpose?: string;
    run_id?: string;
    session_id?: string;
    ticket_id?: string;
    jurisdiction?: string;
    tags?: string[];
    signals?: Record<string, boolean | number | string>;
    attributes?: Record<string, unknown>;
  };
  actor: {
    id: string;
    type: string;
    role?: string;
    tenant?: string;
    attributes?: Record<string, unknown>;
  };
  resource: {
    type: string;
    id?: string;
    classification?: string[];
    attributes?: Record<string, unknown>;
  };
  tool_call?: {
    tool: string;
    risk_tier?: string;
    args_summary?: string;
  };
}

/**
 * Evaluate all conditions for a policy
 * Returns true if all conditions are satisfied
 */
export function evaluateConditions(
  conditions: PolicyConditions,
  ctx: ConditionContext
): boolean {
  // Environment check
  if (conditions.env && conditions.env !== ctx.context.env) {
    return false;
  }

  // Time window check
  if (conditions.time_window) {
    if (!isWithinTimeWindow(conditions.time_window)) {
      return false;
    }
  }

  // Required signals check. Policy packs use `require_signal`; older callers
  // may still emit `require_signals`, so support both shapes.
  const requiredSignals = conditions.require_signal ?? conditions.require_signals;
  if (requiredSignals) {
    if (!hasRequiredSignals(requiredSignals, ctx.context.signals)) {
      return false;
    }
  }

  // Required attributes check
  if (conditions.require_attributes) {
    if (!hasRequiredAttributes(conditions.require_attributes, ctx)) {
      return false;
    }
  }

  if (conditions.require_resource_attr) {
    if (!hasRequiredAttributesInSource(conditions.require_resource_attr, {
      ...(ctx.resource.attributes ?? {}),
      id: ctx.resource.id,
      type: ctx.resource.type,
      classification: ctx.resource.classification,
    })) {
      return false;
    }
  }

  if (conditions.require_actor_attr) {
    if (!hasRequiredAttributesInSource(conditions.require_actor_attr, {
      ...(ctx.actor.attributes ?? {}),
      id: ctx.actor.id,
      type: ctx.actor.type,
      role: ctx.actor.role,
      tenant: ctx.actor.tenant,
    })) {
      return false;
    }
  }

  if (conditions.require_tenant_match) {
    const resourceTenant = ctx.resource.attributes?.tenant;
    if (!ctx.actor.tenant || ctx.actor.tenant !== resourceTenant) {
      return false;
    }
  }

  // Risk tier check
  if (conditions.risk_tiers && conditions.risk_tiers.length > 0) {
    const riskTier = ctx.tool_call?.risk_tier ?? 'UNKNOWN';
    if (!conditions.risk_tiers.includes(riskTier as any)) {
      return false;
    }
  }

  // Tags check (if specified, at least one must match)
  if (conditions.tags && conditions.tags.length > 0) {
    const contextTags = ctx.context.tags ?? [];
    const hasMatchingTag = conditions.tags.some((t: string) => contextTags.includes(t));
    if (!hasMatchingTag) {
      return false;
    }
  }

  // Jurisdiction check
  if (conditions.jurisdictions && conditions.jurisdictions.length > 0) {
    const jurisdiction = ctx.context.jurisdiction;
    if (!jurisdiction || !conditions.jurisdictions.includes(jurisdiction)) {
      return false;
    }
  }

  // Tenant check (for multi-tenant scenarios)
  if (conditions.tenants && conditions.tenants.length > 0) {
    const tenant = ctx.actor.tenant;
    if (!tenant || !conditions.tenants.includes(tenant)) {
      return false;
    }
  }

  // Custom expression evaluation (if provided)
  if (conditions.expression) {
    if (!evaluateExpression(conditions.expression, ctx)) {
      return false;
    }
  }

  return true;
}

/**
 * Check if current time is within specified window
 */
function isWithinTimeWindow(window: { start?: string; end?: string }): boolean {
  const now = new Date();

  if (window.start) {
    const startTime = parseTimeString(window.start, now);
    if (now < startTime) return false;
  }

  if (window.end) {
    const endTime = parseTimeString(window.end, now);
    if (now > endTime) return false;
  }

  return true;
}

/**
 * Parse time string into Date
 * Supports:
 * - "HH:mm" (daily recurring, uses today's date)
 * - "HH:mm:ss" (daily recurring with seconds)
 * - ISO datetime strings
 * - Day-of-week prefixed: "MON-FRI 09:00" (business hours)
 */
function parseTimeString(timeStr: string, referenceDate: Date): Date {
  // Full ISO datetime
  if (timeStr.includes('T') || timeStr.includes('-') && timeStr.length > 10) {
    return new Date(timeStr);
  }

  // Day-of-week pattern: "MON-FRI 09:00"
  const dayTimeMatch = timeStr.match(/^([A-Z]{3})-([A-Z]{3})\s+(\d{2}:\d{2}(?::\d{2})?)$/);
  if (dayTimeMatch) {
    const [, startDay, endDay, time] = dayTimeMatch;
    const dayOfWeek = referenceDate.getDay();
    const days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
    const startDayNum = days.indexOf(startDay);
    const endDayNum = days.indexOf(endDay);

    // Check if current day is in range
    const inRange = startDayNum <= endDayNum
      ? dayOfWeek >= startDayNum && dayOfWeek <= endDayNum
      : dayOfWeek >= startDayNum || dayOfWeek <= endDayNum;

    if (!inRange) {
      // Return a past date to fail the check
      return new Date(0);
    }

    // Parse the time portion
    return parseTimeOfDay(time, referenceDate);
  }

  // Simple time: "HH:mm" or "HH:mm:ss"
  return parseTimeOfDay(timeStr, referenceDate);
}

/**
 * Parse time of day string into Date (using reference date)
 */
function parseTimeOfDay(timeStr: string, referenceDate: Date): Date {
  const parts = timeStr.split(':').map(Number);
  const [hours, minutes, seconds = 0] = parts;

  const result = new Date(referenceDate);
  result.setHours(hours, minutes, seconds, 0);
  return result;
}

/**
 * Check if all required signals are present with expected values
 */
function hasRequiredSignals(
  required: Record<string, unknown>,
  signals?: Record<string, unknown>
): boolean {
  if (!signals) return false;

  for (const [key, expectedValue] of Object.entries(required)) {
    const actualValue = signals[key];

    // Check for presence
    if (actualValue === undefined || actualValue === null) {
      return false;
    }

    // If expectedValue is true, we just need the signal to be truthy
    if (expectedValue === true) {
      if (!actualValue) return false;
      continue;
    }

    // If expectedValue is false, signal must be falsy
    if (expectedValue === false) {
      if (actualValue) return false;
      continue;
    }

    // Otherwise, exact match required
    if (actualValue !== expectedValue) {
      return false;
    }
  }

  return true;
}

/**
 * Check if all required attributes are present
 * Searches across actor, context, and resource attributes
 */
function hasRequiredAttributes(
  required: Record<string, unknown>,
  ctx: ConditionContext
): boolean {
  // Merge all attribute sources
  const allAttributes: Record<string, unknown> = {
    ...(ctx.actor.attributes ?? {}),
    ...(ctx.context.attributes ?? {}),
    ...(ctx.resource.attributes ?? {}),
  };

  for (const [key, expectedValue] of Object.entries(required)) {
    const actualValue = allAttributes[key];

    // Handle nested paths like "actor.role"
    if (key.includes('.')) {
      const value = getNestedValue(ctx, key);
      if (!matchesValue(value, expectedValue)) {
        return false;
      }
      continue;
    }

    if (!matchesValue(actualValue, expectedValue)) {
      return false;
    }
  }

  return true;
}

function hasRequiredAttributesInSource(
  required: Record<string, unknown>,
  source: Record<string, unknown>
): boolean {
  for (const [key, expectedValue] of Object.entries(required)) {
    const actualValue = key.includes('.') ? getNestedValue(source, key) : source[key];
    if (!matchesValue(actualValue, expectedValue)) {
      return false;
    }
  }

  return true;
}

/**
 * Get nested value from object using dot notation
 */
function getNestedValue(obj: unknown, path: string): unknown {
  const parts = path.split('.');
  let current: unknown = obj;

  for (const part of parts) {
    if (current === null || current === undefined) return undefined;
    if (typeof current !== 'object') return undefined;
    current = (current as Record<string, unknown>)[part];
  }

  return current;
}

/**
 * Check if actual value matches expected value
 * Supports arrays (any match), regex patterns, and exact matching
 */
function matchesValue(actual: unknown, expected: unknown): boolean {
  if (actual === undefined || actual === null) {
    return expected === undefined || expected === null;
  }

  // Array expected: actual must be in array
  if (Array.isArray(expected)) {
    return expected.includes(actual);
  }

  // Regex pattern (string starting with /)
  if (typeof expected === 'string' && expected.startsWith('/')) {
    const match = expected.match(/^\/(.+)\/([gimsuy]*)$/);
    if (match) {
      const [, pattern, flags] = match;
      const regex = new RegExp(pattern, flags);
      return regex.test(String(actual));
    }
  }

  // Exact match
  return actual === expected;
}

/**
 * Evaluate custom expression
 * Supports simple boolean expressions with AND, OR, NOT
 */
function evaluateExpression(expression: string, ctx: ConditionContext): boolean {
  // Simple expression parser
  // Supports: "signal.pii_detected AND actor.role == 'admin'"
  try {
    // Replace placeholders with actual values
    let expr = expression;

    // Replace signal references: signal.xxx
    expr = expr.replace(/signal\.(\w+)/g, (_, name) => {
      const value = ctx.context.signals?.[name];
      if (typeof value === 'boolean') return String(value);
      if (typeof value === 'number') return String(value);
      if (typeof value === 'string') return `"${value}"`;
      return 'false';
    });

    // Replace actor references: actor.xxx
    expr = expr.replace(/actor\.(\w+)/g, (_, name) => {
      const value = (ctx.actor as any)[name] ?? ctx.actor.attributes?.[name];
      if (typeof value === 'boolean') return String(value);
      if (typeof value === 'number') return String(value);
      if (typeof value === 'string') return `"${value}"`;
      return 'null';
    });

    // Replace context references: context.xxx
    expr = expr.replace(/context\.(\w+)/g, (_, name) => {
      const value = (ctx.context as any)[name] ?? ctx.context.attributes?.[name];
      if (typeof value === 'boolean') return String(value);
      if (typeof value === 'number') return String(value);
      if (typeof value === 'string') return `"${value}"`;
      return 'null';
    });

    // Replace resource references: resource.xxx
    expr = expr.replace(/resource\.(\w+)/g, (_, name) => {
      const value = (ctx.resource as any)[name] ?? ctx.resource.attributes?.[name];
      if (typeof value === 'boolean') return String(value);
      if (typeof value === 'number') return String(value);
      if (typeof value === 'string') return `"${value}"`;
      return 'null';
    });

    // Evaluate the expression safely (very limited evaluator)
    return safeEvaluate(expr);
  } catch {
    // On error, fail closed
    return false;
  }
}

/**
 * Safe expression evaluator for simple boolean logic
 * Does NOT use eval() - parses manually
 */
function safeEvaluate(expr: string): boolean {
  // Normalize
  expr = expr.trim();

  // Handle NOT
  if (expr.startsWith('NOT ') || expr.startsWith('!')) {
    const inner = expr.startsWith('NOT ') ? expr.slice(4) : expr.slice(1);
    return !safeEvaluate(inner.trim());
  }

  // Handle parentheses
  if (expr.startsWith('(') && expr.endsWith(')')) {
    return safeEvaluate(expr.slice(1, -1));
  }

  // Handle OR (lowest precedence)
  const orParts = splitByOperator(expr, ' OR ');
  if (orParts.length > 1) {
    return orParts.some(part => safeEvaluate(part));
  }

  // Handle AND
  const andParts = splitByOperator(expr, ' AND ');
  if (andParts.length > 1) {
    return andParts.every(part => safeEvaluate(part));
  }

  // Handle comparisons
  const eqMatch = expr.match(/^(.+?)\s*==\s*(.+)$/);
  if (eqMatch) {
    const left = parseValue(eqMatch[1].trim());
    const right = parseValue(eqMatch[2].trim());
    return left === right;
  }

  const neqMatch = expr.match(/^(.+?)\s*!=\s*(.+)$/);
  if (neqMatch) {
    const left = parseValue(neqMatch[1].trim());
    const right = parseValue(neqMatch[2].trim());
    return left !== right;
  }

  // Boolean literal
  if (expr === 'true') return true;
  if (expr === 'false') return false;

  // Unknown expression, fail closed
  return false;
}

/**
 * Split expression by operator, respecting parentheses
 */
function splitByOperator(expr: string, op: string): string[] {
  const parts: string[] = [];
  let depth = 0;
  let current = '';

  for (let i = 0; i < expr.length; i++) {
    const char = expr[i];
    if (char === '(') depth++;
    if (char === ')') depth--;

    if (depth === 0 && expr.slice(i, i + op.length) === op) {
      parts.push(current.trim());
      current = '';
      i += op.length - 1;
    } else {
      current += char;
    }
  }

  if (current.trim()) {
    parts.push(current.trim());
  }

  return parts;
}

/**
 * Parse value from expression string
 */
function parseValue(str: string): unknown {
  str = str.trim();

  // Quoted string
  if ((str.startsWith('"') && str.endsWith('"')) ||
      (str.startsWith("'") && str.endsWith("'"))) {
    return str.slice(1, -1);
  }

  // Boolean
  if (str === 'true') return true;
  if (str === 'false') return false;

  // Null
  if (str === 'null') return null;

  // Number
  const num = Number(str);
  if (!isNaN(num)) return num;

  // Return as-is (for variable values already substituted)
  return str;
}
