/**
 * Pattern matching utilities for policy evaluation
 * Supports wildcards (*), glob patterns, and exact matching
 */

/**
 * Match exact value or wildcard '*'
 */
export function matchesPattern(pattern: string | '*', value: string): boolean {
  if (pattern === '*') return true;
  return pattern.toLowerCase() === value.toLowerCase();
}

/**
 * Match glob patterns (*, prefix*, *suffix, pre*suf)
 * Case-insensitive matching
 */
export function matchesGlob(pattern: string, value: string): boolean {
  if (pattern === '*') return true;
  if (!pattern.includes('*')) return pattern.toLowerCase() === value.toLowerCase();

  // Convert glob to regex
  const regexPattern = pattern
    .replace(/[.+^${}()|[\]\\]/g, '\\$&') // Escape special chars
    .replace(/\*/g, '.*') // * -> .*
    .replace(/\?/g, '.'); // ? -> .

  const regex = new RegExp(`^${regexPattern}$`, 'i');
  return regex.test(value);
}

/**
 * Match any pattern in array (OR logic)
 */
export function matchesAnyPattern(patterns: string[], value: string): boolean {
  if (patterns.length === 0) return true;
  return patterns.some(p => matchesGlob(p, value));
}

/**
 * Match all patterns in array (AND logic)
 * Each pattern must match at least one value
 */
export function matchesAllPatterns(patterns: string[], values: string[]): boolean {
  if (patterns.length === 0) return true;
  return patterns.every(p => values.some(v => matchesGlob(p, v)));
}

/**
 * Check if value is in array (case-insensitive)
 */
export function isInArray(value: string, array: string[]): boolean {
  const lowerValue = value.toLowerCase();
  return array.some(item => item.toLowerCase() === lowerValue);
}

/**
 * Check if all required values are present in array
 */
export function hasAllValues(required: string[], present: string[]): boolean {
  const lowerPresent = present.map(v => v.toLowerCase());
  return required.every(r => lowerPresent.includes(r.toLowerCase()));
}

/**
 * Check if any required value is present in array
 */
export function hasAnyValue(required: string[], present: string[]): boolean {
  if (required.length === 0) return true;
  const lowerPresent = present.map(v => v.toLowerCase());
  return required.some(r => lowerPresent.includes(r.toLowerCase()));
}

/**
 * Match actor type with wildcard support
 * Supports '*' to match any actor type
 */
export function matchesActorType(
  pattern: string | '*',
  actorType: string
): boolean {
  return matchesPattern(pattern, actorType);
}

/**
 * Match action with glob pattern support
 * Examples: 'read', 'data.*', '*.write', 'db.*.read'
 */
export function matchesAction(pattern: string, action: string): boolean {
  return matchesGlob(pattern, action);
}

/**
 * Match resource type with glob pattern support
 */
export function matchesResourceType(pattern: string, resourceType: string): boolean {
  return matchesGlob(pattern, resourceType);
}

/**
 * Match environment against allowed environments
 */
export function matchesEnvironment(
  allowedEnvs: string[] | undefined,
  currentEnv: string
): boolean {
  if (!allowedEnvs || allowedEnvs.length === 0) return true;
  return isInArray(currentEnv, allowedEnvs);
}

/**
 * Match classifications (all required must be present)
 */
export function matchesClassifications(
  requiredClassifications: string[] | undefined,
  resourceClassifications: string[] | undefined
): boolean {
  if (!requiredClassifications || requiredClassifications.length === 0) return true;
  if (!resourceClassifications || resourceClassifications.length === 0) return false;
  return hasAllValues(requiredClassifications, resourceClassifications);
}
