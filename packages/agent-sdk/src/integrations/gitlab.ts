/**
 * STIX Agent SDK - GitLab Integration
 * Maps GitLab Duo Agent Platform events to STIX authorization
 * and translates decisions back to GitLab API actions.
 *
 * Designed for the GitLab AI Hackathon - "STIX Guardian" compliance agent.
 */

import type { StixClient } from '../client';
import type {
  AuthorizationResult,
  RiskTier,
  Resource,
  Context,
  Actor,
  DecisionKind,
} from '../types';

// =============================================================================
// GITLAB EVENT TYPES
// =============================================================================

/** GitLab user reference */
export interface GitLabUser {
  id: number;
  username: string;
  name?: string;
  state?: string;
  email?: string;
}

/** GitLab project reference */
export interface GitLabProject {
  id: number;
  name: string;
  path_with_namespace: string;
  default_branch?: string;
  namespace?: {
    id: number;
    name: string;
    full_path: string;
  };
}

/** A single file change in an MR diff */
export interface GitLabDiffEntry {
  old_path: string;
  new_path: string;
  diff: string;
  new_file: boolean;
  renamed_file: boolean;
  deleted_file: boolean;
}

/** Merge Request event payload */
export interface GitLabMergeRequestEvent {
  event_type: 'merge_request';
  action: 'open' | 'update' | 'merge' | 'close' | 'reopen' | 'approved' | 'unapproved';
  merge_request: {
    iid: number;
    title: string;
    description?: string;
    state: string;
    source_branch: string;
    target_branch: string;
    author: GitLabUser;
    assignees?: GitLabUser[];
    reviewers?: GitLabUser[];
    labels?: string[];
    has_conflicts?: boolean;
    draft?: boolean;
    web_url?: string;
    diff_refs?: {
      base_sha: string;
      head_sha: string;
      start_sha: string;
    };
  };
  project: GitLabProject;
  changes?: GitLabDiffEntry[];
}

/** Pipeline event payload */
export interface GitLabPipelineEvent {
  event_type: 'pipeline';
  pipeline: {
    id: number;
    iid: number;
    ref: string;
    status: string;
    source: string;
    sha: string;
    tag: boolean;
    stages?: string[];
  };
  project: GitLabProject;
  user: GitLabUser;
  jobs?: Array<{
    id: number;
    name: string;
    stage: string;
    status: string;
  }>;
}

/** Issue event payload */
export interface GitLabIssueEvent {
  event_type: 'issue';
  action: 'open' | 'update' | 'close' | 'reopen';
  issue: {
    iid: number;
    title: string;
    description?: string;
    state: string;
    labels?: string[];
    assignees?: GitLabUser[];
    author: GitLabUser;
    confidential?: boolean;
    web_url?: string;
  };
  project: GitLabProject;
}

/** Comment / note event payload */
export interface GitLabNoteEvent {
  event_type: 'note';
  note: {
    id: number;
    body: string;
    author: GitLabUser;
    noteable_type: 'MergeRequest' | 'Issue' | 'Commit' | 'Snippet';
    noteable_id: number;
  };
  merge_request?: GitLabMergeRequestEvent['merge_request'];
  issue?: GitLabIssueEvent['issue'];
  project: GitLabProject;
}

/** Union of all supported GitLab events */
export type GitLabEvent =
  | GitLabMergeRequestEvent
  | GitLabPipelineEvent
  | GitLabIssueEvent
  | GitLabNoteEvent;

// =============================================================================
// COMPLIANCE SIGNAL DETECTION
// =============================================================================

/** PII patterns - common personally identifiable information */
const PII_PATTERNS: Array<{ pattern: RegExp; label: string }> = [
  { pattern: /\b\d{3}-\d{2}-\d{4}\b/, label: 'SSN' },
  { pattern: /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/, label: 'credit_card' },
  { pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/, label: 'email' },
  { pattern: /\b\d{3}[\s.-]?\d{3}[\s.-]?\d{4}\b/, label: 'phone' },
  { pattern: /\bdate[_\s]?of[_\s]?birth\b/i, label: 'dob' },
  { pattern: /\bpassport[_\s]?(number|no|num|#)\b/i, label: 'passport' },
  { pattern: /\bdriver'?s?[_\s]?licen[sc]e\b/i, label: 'drivers_license' },
];

/** PHI patterns - protected health information */
const PHI_PATTERNS: Array<{ pattern: RegExp; label: string }> = [
  { pattern: /\bpatient[_\s]?(id|name|record|data|info)\b/i, label: 'patient_data' },
  { pattern: /\bdiagnos[ei]s\b/i, label: 'diagnosis' },
  { pattern: /\bmedical[_\s]?record\b/i, label: 'medical_record' },
  { pattern: /\bhealth[_\s]?insurance\b/i, label: 'health_insurance' },
  { pattern: /\bprescription\b/i, label: 'prescription' },
  { pattern: /\blab[_\s]?result\b/i, label: 'lab_result' },
  { pattern: /\btreatment[_\s]?(plan|history)\b/i, label: 'treatment' },
  { pattern: /\bHIPAA\b/, label: 'hipaa_reference' },
];

/** Secrets patterns */
const SECRET_PATTERNS: Array<{ pattern: RegExp; label: string }> = [
  { pattern: /(?:api[_-]?key|apikey)\s*[:=]\s*['"][^'"]{8,}/i, label: 'api_key' },
  { pattern: /(?:password|passwd|pwd)\s*[:=]\s*['"][^'"]+/i, label: 'password' },
  { pattern: /(?:secret|token)\s*[:=]\s*['"][^'"]{8,}/i, label: 'secret_token' },
  { pattern: /-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----/, label: 'private_key' },
  { pattern: /(?:aws_access_key_id|aws_secret_access_key)\s*[:=]/i, label: 'aws_credential' },
  { pattern: /ghp_[A-Za-z0-9_]{36,}/, label: 'github_pat' },
  { pattern: /glpat-[A-Za-z0-9_-]{20,}/, label: 'gitlab_pat' },
  { pattern: /sk-[A-Za-z0-9]{32,}/, label: 'openai_key' },
];

/** PCI patterns - payment card data */
const PCI_PATTERNS: Array<{ pattern: RegExp; label: string }> = [
  { pattern: /\bcvv\b/i, label: 'cvv' },
  { pattern: /\bcard[_\s]?holder\b/i, label: 'cardholder' },
  { pattern: /\bexpir(y|ation)[_\s]?date\b/i, label: 'expiry_date' },
  { pattern: /\b(?:credit|debit)[_\s]?card\b/i, label: 'card_reference' },
];

/** Scan results from diff analysis */
export interface DiffScanResult {
  piiDetected: boolean;
  phiDetected: boolean;
  pciDetected: boolean;
  secretsDetected: boolean;
  piiLabels: string[];
  phiLabels: string[];
  pciLabels: string[];
  secretLabels: string[];
  classifications: string[];
  riskTier: RiskTier;
  findings: DiffFinding[];
}

/** A single finding from the diff scanner */
export interface DiffFinding {
  file: string;
  line?: number;
  type: 'pii' | 'phi' | 'pci' | 'secret';
  label: string;
  snippet: string;
}

/**
 * Scan MR diff entries for compliance signals
 */
export function scanDiff(diffs: GitLabDiffEntry[]): DiffScanResult {
  const findings: DiffFinding[] = [];
  const piiLabels = new Set<string>();
  const phiLabels = new Set<string>();
  const pciLabels = new Set<string>();
  const secretLabels = new Set<string>();

  for (const entry of diffs) {
    if (entry.deleted_file) continue;

    const addedLines = entry.diff
      .split('\n')
      .filter(line => line.startsWith('+') && !line.startsWith('+++'));

    for (const line of addedLines) {
      const lineContent = line.substring(1); // strip leading +

      for (const { pattern, label } of PII_PATTERNS) {
        if (pattern.test(lineContent)) {
          piiLabels.add(label);
          findings.push({
            file: entry.new_path,
            type: 'pii',
            label,
            snippet: lineContent.trim().substring(0, 120),
          });
        }
      }

      for (const { pattern, label } of PHI_PATTERNS) {
        if (pattern.test(lineContent)) {
          phiLabels.add(label);
          findings.push({
            file: entry.new_path,
            type: 'phi',
            label,
            snippet: lineContent.trim().substring(0, 120),
          });
        }
      }

      for (const { pattern, label } of PCI_PATTERNS) {
        if (pattern.test(lineContent)) {
          pciLabels.add(label);
          findings.push({
            file: entry.new_path,
            type: 'pci',
            label,
            snippet: lineContent.trim().substring(0, 120),
          });
        }
      }

      for (const { pattern, label } of SECRET_PATTERNS) {
        if (pattern.test(lineContent)) {
          secretLabels.add(label);
          findings.push({
            file: entry.new_path,
            type: 'secret',
            label,
            snippet: lineContent.trim().substring(0, 80) + '***REDACTED***',
          });
        }
      }
    }
  }

  const piiDetected = piiLabels.size > 0;
  const phiDetected = phiLabels.size > 0;
  const pciDetected = pciLabels.size > 0;
  const secretsDetected = secretLabels.size > 0;

  // Determine risk tier
  let riskTier: RiskTier = 'LOW';
  if (secretsDetected) riskTier = 'CRITICAL';
  else if (phiDetected) riskTier = 'HIGH';
  else if (pciDetected) riskTier = 'HIGH';
  else if (piiDetected) riskTier = 'MEDIUM';

  // Build classification labels
  const classifications: string[] = [];
  if (piiDetected) classifications.push('PII');
  if (phiDetected) classifications.push('PHI');
  if (pciDetected) classifications.push('PCI');
  if (secretsDetected) classifications.push('SECRETS');

  return {
    piiDetected,
    phiDetected,
    pciDetected,
    secretsDetected,
    piiLabels: [...piiLabels],
    phiLabels: [...phiLabels],
    pciLabels: [...pciLabels],
    secretLabels: [...secretLabels],
    classifications,
    riskTier,
    findings,
  };
}

// =============================================================================
// EVENT NORMALIZER - GitLab events → STIX AuthorizeRequest
// =============================================================================

/** Normalized request ready for STIX authorization */
export interface GitLabAuthorizeInput {
  actor: Actor;
  action: string;
  resource: Resource;
  context: Context;
  riskTier: RiskTier;
  scanResult?: DiffScanResult;
  toolSummary: string;
}

/**
 * Normalize a GitLab MR event into a STIX authorization input
 */
export function normalizeMergeRequestEvent(
  event: GitLabMergeRequestEvent,
  scanResult?: DiffScanResult
): GitLabAuthorizeInput {
  const mr = event.merge_request;
  const project = event.project;

  const actionMap: Record<string, string> = {
    open: 'mr_create',
    update: 'mr_update',
    merge: 'mr_merge',
    close: 'mr_close',
    reopen: 'mr_reopen',
    approved: 'mr_approve',
    unapproved: 'mr_unapprove',
  };

  const riskMap: Record<string, RiskTier> = {
    open: 'MEDIUM',
    update: 'LOW',
    merge: 'HIGH',
    close: 'LOW',
    reopen: 'LOW',
    approved: 'HIGH',
    unapproved: 'LOW',
  };

  const action = actionMap[event.action] ?? `mr_${event.action}`;
  let riskTier = riskMap[event.action] ?? 'MEDIUM';

  // Elevate risk based on target branch
  if (mr.target_branch === 'main' || mr.target_branch === 'master' || mr.target_branch === 'production') {
    if (riskTier === 'LOW') riskTier = 'MEDIUM';
    if (riskTier === 'MEDIUM') riskTier = 'HIGH';
  }

  // Elevate risk based on scan findings
  if (scanResult && scanResult.riskTier === 'CRITICAL') {
    riskTier = 'CRITICAL';
  } else if (scanResult && scanResult.riskTier === 'HIGH' && riskTier !== 'CRITICAL') {
    riskTier = 'HIGH';
  }

  return {
    actor: {
      id: `gitlab:user:${mr.author.username}`,
      type: 'AI_AGENT',
      role: mr.author.state ?? 'active',
      tenant: project.namespace?.full_path ?? project.path_with_namespace,
      attributes: {
        gitlab_user_id: mr.author.id,
        gitlab_username: mr.author.username,
      },
    },
    action,
    resource: {
      type: 'merge_request',
      id: `${project.path_with_namespace}!${mr.iid}`,
      classification: scanResult?.classifications ?? [],
      attributes: {
        project_id: project.id,
        project_path: project.path_with_namespace,
        mr_iid: mr.iid,
        source_branch: mr.source_branch,
        target_branch: mr.target_branch,
        has_conflicts: mr.has_conflicts ?? false,
        is_draft: mr.draft ?? false,
        labels: mr.labels ?? [],
        title: mr.title,
      },
    },
    context: {
      env: inferEnvironment(mr.target_branch),
      purpose: 'compliance_review',
      ticket_id: `MR-${mr.iid}`,
      tags: [
        'platform:gitlab',
        `event:${action}`,
        `branch:${mr.target_branch}`,
      ],
      signals: {
        piiDetected: scanResult?.piiDetected ?? false,
        phiDetected: scanResult?.phiDetected ?? false,
        pciDetected: scanResult?.pciDetected ?? false,
        secretsDetected: scanResult?.secretsDetected ?? false,
      },
      attributes: {
        gitlab_event: 'merge_request',
        gitlab_action: event.action,
        scan_findings_count: scanResult?.findings.length ?? 0,
      },
    },
    riskTier,
    scanResult,
    toolSummary: `MR !${mr.iid}: "${mr.title}" → ${mr.target_branch}`,
  };
}

/**
 * Normalize a GitLab pipeline event into a STIX authorization input
 */
export function normalizePipelineEvent(event: GitLabPipelineEvent): GitLabAuthorizeInput {
  const pipeline = event.pipeline;
  const project = event.project;

  const isProduction = pipeline.ref === 'main' || pipeline.ref === 'master' || pipeline.ref === 'production';
  const riskTier: RiskTier = isProduction ? 'HIGH' : 'MEDIUM';

  return {
    actor: {
      id: `gitlab:user:${event.user.username}`,
      type: 'JOB',
      tenant: project.namespace?.full_path ?? project.path_with_namespace,
      attributes: {
        gitlab_user_id: event.user.id,
        pipeline_source: pipeline.source,
      },
    },
    action: 'pipeline_execute',
    resource: {
      type: 'pipeline',
      id: `${project.path_with_namespace}#${pipeline.id}`,
      attributes: {
        project_id: project.id,
        project_path: project.path_with_namespace,
        pipeline_id: pipeline.id,
        ref: pipeline.ref,
        sha: pipeline.sha,
        tag: pipeline.tag,
        stages: pipeline.stages ?? [],
        status: pipeline.status,
      },
    },
    context: {
      env: inferEnvironment(pipeline.ref),
      purpose: 'ci_cd_execution',
      tags: [
        'platform:gitlab',
        'event:pipeline',
        `ref:${pipeline.ref}`,
        `source:${pipeline.source}`,
      ],
      signals: {},
      attributes: {
        gitlab_event: 'pipeline',
        job_count: event.jobs?.length ?? 0,
      },
    },
    riskTier,
    toolSummary: `Pipeline #${pipeline.id} on ${pipeline.ref} (${pipeline.status})`,
  };
}

/**
 * Normalize a GitLab issue event into a STIX authorization input
 */
export function normalizeIssueEvent(event: GitLabIssueEvent): GitLabAuthorizeInput {
  const issue = event.issue;
  const project = event.project;

  const actionMap: Record<string, string> = {
    open: 'issue_create',
    update: 'issue_update',
    close: 'issue_close',
    reopen: 'issue_reopen',
  };

  return {
    actor: {
      id: `gitlab:user:${issue.author.username}`,
      type: 'HUMAN',
      tenant: project.namespace?.full_path ?? project.path_with_namespace,
      attributes: {
        gitlab_user_id: issue.author.id,
      },
    },
    action: actionMap[event.action] ?? `issue_${event.action}`,
    resource: {
      type: 'issue',
      id: `${project.path_with_namespace}#${issue.iid}`,
      classification: issue.confidential ? ['CONFIDENTIAL'] : [],
      attributes: {
        project_id: project.id,
        project_path: project.path_with_namespace,
        issue_iid: issue.iid,
        labels: issue.labels ?? [],
        confidential: issue.confidential ?? false,
        title: issue.title,
      },
    },
    context: {
      env: 'prod',
      purpose: 'issue_management',
      ticket_id: `ISSUE-${issue.iid}`,
      tags: [
        'platform:gitlab',
        `event:issue_${event.action}`,
        ...(issue.labels ?? []).map(l => `label:${l}`),
      ],
      signals: {},
      attributes: {
        gitlab_event: 'issue',
        gitlab_action: event.action,
      },
    },
    riskTier: issue.confidential ? 'HIGH' : 'LOW',
    toolSummary: `Issue #${issue.iid}: "${issue.title}"`,
  };
}

/**
 * Normalize any GitLab event into a STIX authorization input
 */
export function normalizeGitLabEvent(
  event: GitLabEvent,
  diffs?: GitLabDiffEntry[]
): GitLabAuthorizeInput {
  switch (event.event_type) {
    case 'merge_request': {
      const scanResult = diffs ? scanDiff(diffs) : undefined;
      return normalizeMergeRequestEvent(event, scanResult);
    }
    case 'pipeline':
      return normalizePipelineEvent(event);
    case 'issue':
      return normalizeIssueEvent(event);
    case 'note': {
      // Notes on MRs are treated as MR events
      if (event.merge_request) {
        const mrEvent: GitLabMergeRequestEvent = {
          event_type: 'merge_request',
          action: 'update',
          merge_request: event.merge_request,
          project: event.project,
        };
        const scanResult = diffs ? scanDiff(diffs) : undefined;
        return normalizeMergeRequestEvent(mrEvent, scanResult);
      }
      // Notes on issues
      if (event.issue) {
        const issueEvent: GitLabIssueEvent = {
          event_type: 'issue',
          action: 'update',
          issue: event.issue,
          project: event.project,
        };
        return normalizeIssueEvent(issueEvent);
      }
      // Fallback for other note types
      return {
        actor: {
          id: `gitlab:user:${event.note.author.username}`,
          type: 'HUMAN',
          tenant: event.project.path_with_namespace,
        },
        action: 'note_create',
        resource: {
          type: event.note.noteable_type.toLowerCase(),
          id: `${event.project.path_with_namespace}#note-${event.note.id}`,
        },
        context: {
          env: 'prod',
          purpose: 'comment',
          tags: ['platform:gitlab', 'event:note'],
          signals: {},
        },
        riskTier: 'LOW',
        toolSummary: `Note on ${event.note.noteable_type} #${event.note.noteable_id}`,
      };
    }
    default:
      throw new Error(`Unsupported GitLab event type: ${(event as GitLabEvent).event_type}`);
  }
}

// =============================================================================
// DECISION MAPPER - STIX decisions → GitLab API actions
// =============================================================================

/** GitLab action to perform after STIX decision */
export interface GitLabAction {
  /** Type of GitLab API action */
  type: 'mr_comment' | 'mr_approve' | 'mr_request_changes' | 'add_label' | 'remove_label' | 'create_issue';
  /** API endpoint path (relative) */
  endpoint: string;
  /** HTTP method */
  method: 'POST' | 'PUT' | 'DELETE';
  /** Request body */
  body: Record<string, unknown>;
}

/** Complete response to send back to GitLab */
export interface GitLabResponse {
  /** STIX decision */
  decision: DecisionKind;
  /** Trace ID for correlation */
  traceId: string;
  /** Actions to execute on GitLab API */
  actions: GitLabAction[];
  /** Formatted MR comment body (Markdown) */
  comment: string;
  /** Labels to add */
  labelsToAdd: string[];
  /** Labels to remove */
  labelsToRemove: string[];
}

/**
 * Format a STIX decision as a GitLab MR comment (Markdown)
 */
export function formatDecisionComment(
  decision: DecisionKind,
  result: AuthorizationResult,
  input: GitLabAuthorizeInput
): string {
  const timestamp = new Date().toISOString();
  const icon = decision === 'ALLOW' ? ':white_check_mark:' : decision === 'DENY' ? ':x:' : ':warning:';
  const statusText = decision === 'ALLOW' ? 'Compliant' : decision === 'DENY' ? 'Violation Detected' : 'Review Required';

  let comment = `## ${icon} STIX Guardian - ${statusText}\n\n`;
  comment += `| Field | Value |\n|---|---|\n`;
  comment += `| **Decision** | \`${decision}\` |\n`;
  comment += `| **Reason** | \`${result.reasonCode}\` |\n`;
  comment += `| **Trace ID** | \`${result.traceId}\` |\n`;
  comment += `| **Risk Tier** | \`${input.riskTier}\` |\n`;
  comment += `| **Timestamp** | ${timestamp} |\n`;

  if (result.explanation) {
    comment += `\n### Explanation\n\n${result.explanation}\n`;
  }

  // Show compliance controls
  if (result.controls.length > 0) {
    comment += `\n### Compliance Controls\n\n`;
    comment += result.controls.map(c => `- \`${c}\``).join('\n') + '\n';
  }

  if (result.regulations.length > 0) {
    comment += `\n### Regulations\n\n`;
    comment += result.regulations.map(r => `- \`${r}\``).join('\n') + '\n';
  }

  // Show findings for DENY/QUARANTINE
  if (decision !== 'ALLOW' && input.scanResult && input.scanResult.findings.length > 0) {
    comment += `\n### Findings\n\n`;
    comment += `| Type | Label | File | Snippet |\n|---|---|---|---|\n`;

    for (const finding of input.scanResult.findings.slice(0, 20)) {
      const typeIcon = finding.type === 'secret' ? ':rotating_light:' :
                       finding.type === 'phi' ? ':hospital:' :
                       finding.type === 'pci' ? ':credit_card:' : ':bust_in_silhouette:';
      const escaped = finding.snippet.replace(/\|/g, '\\|').replace(/\n/g, ' ');
      comment += `| ${typeIcon} ${finding.type.toUpperCase()} | \`${finding.label}\` | \`${finding.file}\` | ${escaped} |\n`;
    }

    if (input.scanResult.findings.length > 20) {
      comment += `\n_...and ${input.scanResult.findings.length - 20} more findings_\n`;
    }
  }

  // Show obligations for ALLOW
  if (decision === 'ALLOW' && result.obligations.length > 0) {
    comment += `\n### Obligations Applied\n\n`;
    for (const ob of result.obligations) {
      comment += `- \`${ob.type}\``;
      if (ob.params) comment += ` (${JSON.stringify(ob.params)})`;
      comment += '\n';
    }
  }

  // Show approval info for QUARANTINE
  if (decision === 'QUARANTINE' && result.approvalTicketId) {
    comment += `\n### Approval Required\n\n`;
    comment += `This merge request requires compliance review before it can proceed.\n\n`;
    comment += `- **Ticket ID:** \`${result.approvalTicketId}\`\n`;
    comment += `- **Status:** Pending review\n`;
    comment += `\nA compliance officer will review this request. `;
    comment += `You will be notified when a decision is made.\n`;
  }

  // Proof token reference for ALLOW
  if (decision === 'ALLOW' && result.proofToken) {
    comment += `\n### Cryptographic Proof\n\n`;
    comment += `A signed proof token (Ed25519) has been generated for this authorization.\n`;
    comment += `Verify with: \`stix-verify event --trace-id ${result.traceId}\`\n`;
  }

  comment += `\n---\n_Powered by [STIX Guardian](https://github.com/stix-guardian) | Trace: \`${result.traceId}\`_\n`;

  return comment;
}

/**
 * Map a STIX authorization result to GitLab API actions
 */
export function mapDecisionToGitLabActions(
  projectPath: string,
  mrIid: number,
  decision: DecisionKind,
  result: AuthorizationResult,
  input: GitLabAuthorizeInput
): GitLabResponse {
  const comment = formatDecisionComment(decision, result, input);
  const actions: GitLabAction[] = [];
  const labelsToAdd: string[] = [];
  const labelsToRemove: string[] = [];
  const encodedPath = encodeURIComponent(projectPath);

  // Always post a comment
  actions.push({
    type: 'mr_comment',
    endpoint: `/api/v4/projects/${encodedPath}/merge_requests/${mrIid}/notes`,
    method: 'POST',
    body: { body: comment },
  });

  switch (decision) {
    case 'ALLOW':
      labelsToAdd.push('stix:compliant');
      labelsToRemove.push('stix:violation', 'stix:review-required');

      actions.push({
        type: 'mr_approve',
        endpoint: `/api/v4/projects/${encodedPath}/merge_requests/${mrIid}/approve`,
        method: 'POST',
        body: {},
      });
      break;

    case 'DENY':
      labelsToAdd.push('stix:violation');
      labelsToRemove.push('stix:compliant', 'stix:review-required');
      break;

    case 'QUARANTINE':
      labelsToAdd.push('stix:review-required');
      labelsToRemove.push('stix:compliant', 'stix:violation');
      break;
  }

  // Add label actions
  if (labelsToAdd.length > 0 || labelsToRemove.length > 0) {
    actions.push({
      type: 'add_label',
      endpoint: `/api/v4/projects/${encodedPath}/merge_requests/${mrIid}`,
      method: 'PUT',
      body: {
        add_labels: labelsToAdd.join(','),
        remove_labels: labelsToRemove.join(','),
      },
    });
  }

  // Create tracking issue for DENY with critical findings
  if (decision === 'DENY' && input.riskTier === 'CRITICAL') {
    actions.push({
      type: 'create_issue',
      endpoint: `/api/v4/projects/${encodedPath}/issues`,
      method: 'POST',
      body: {
        title: `[STIX] Critical compliance violation in MR !${mrIid}`,
        description: `## Compliance Violation Report\n\n` +
          `A critical compliance violation was detected by STIX Guardian.\n\n` +
          `- **MR:** !${mrIid}\n` +
          `- **Trace ID:** \`${result.traceId}\`\n` +
          `- **Risk Tier:** CRITICAL\n` +
          `- **Findings:** ${input.scanResult?.findings.length ?? 0}\n\n` +
          `### Action Required\n\n` +
          `Please review and remediate the compliance violations before resubmitting.\n`,
        labels: 'stix:violation,compliance,critical',
        confidential: true,
      },
    });
  }

  return {
    decision,
    traceId: result.traceId,
    actions,
    comment,
    labelsToAdd,
    labelsToRemove,
  };
}

// =============================================================================
// GITLAB GUARDIAN - Main orchestrator
// =============================================================================

/** Configuration for the GitLab Guardian agent */
export interface GitLabGuardianConfig {
  /** STIX client instance */
  client: StixClient;
  /** GitLab API base URL (e.g., https://gitlab.com) */
  gitlabUrl?: string;
  /** GitLab API token for posting comments, labels, etc. */
  gitlabToken?: string;
  /** Default actor type for GitLab events */
  defaultActorType?: Actor['type'];
  /** Whether to auto-approve compliant MRs */
  autoApprove?: boolean;
  /** Whether to create issues for critical violations */
  createIssuesForCritical?: boolean;
}

/**
 * STIX Guardian - GitLab Compliance Agent
 *
 * Orchestrates the full compliance check flow:
 * 1. Receive GitLab event
 * 2. Scan diffs for compliance signals
 * 3. Normalize to STIX AuthorizeRequest
 * 4. Get STIX decision
 * 5. Map decision to GitLab API actions
 * 6. Execute actions (comments, labels, approvals)
 *
 * @example
 * ```typescript
 * const guardian = new GitLabGuardian({
 *   client: new StixClient({ enforcerUrl: 'http://localhost:3001' }),
 *   gitlabUrl: 'https://gitlab.com',
 *   gitlabToken: process.env.GITLAB_TOKEN,
 * });
 *
 * // Handle a webhook event
 * const response = await guardian.handleEvent(event, diffs);
 * console.log(`Decision: ${response.decision}, Trace: ${response.traceId}`);
 * ```
 */
export class GitLabGuardian {
  private readonly config: Required<GitLabGuardianConfig>;

  constructor(config: GitLabGuardianConfig) {
    this.config = {
      client: config.client,
      gitlabUrl: config.gitlabUrl ?? 'https://gitlab.com',
      gitlabToken: config.gitlabToken ?? '',
      defaultActorType: config.defaultActorType ?? 'AI_AGENT',
      autoApprove: config.autoApprove ?? false,
      createIssuesForCritical: config.createIssuesForCritical ?? true,
    };
  }

  /**
   * Handle a GitLab event end-to-end:
   * normalize → authorize → map response → execute actions
   */
  async handleEvent(
    event: GitLabEvent,
    diffs?: GitLabDiffEntry[]
  ): Promise<GitLabResponse> {
    // 1. Normalize the event
    const input = normalizeGitLabEvent(event, diffs);

    // 2. Authorize through STIX
    const result = await this.config.client.authorize({
      action: input.action,
      resource: input.resource,
      actor: input.actor,
      context: input.context,
      toolCall: {
        tool: `gitlab.${input.action}`,
        risk_tier: input.riskTier,
        args_summary: input.toolSummary,
      },
    });

    // 3. Map decision to GitLab actions
    const projectPath = this.extractProjectPath(event);
    const mrIid = this.extractMrIid(event);

    if (mrIid === null) {
      // Non-MR events: just return the result without GitLab actions
      return {
        decision: result.decision,
        traceId: result.traceId,
        actions: [],
        comment: formatDecisionComment(result.decision, result, input),
        labelsToAdd: [],
        labelsToRemove: [],
      };
    }

    const response = mapDecisionToGitLabActions(
      projectPath,
      mrIid,
      result.decision,
      result,
      input
    );

    // 4. Execute GitLab API actions
    if (this.config.gitlabToken) {
      await this.executeActions(response.actions);
    }

    // 5. Record outcome
    await this.config.client.recordOutcome(result.traceId, 'SUCCESS', {
      resultSummary: `GitLab ${result.decision}: ${input.toolSummary}`,
    });

    return response;
  }

  /**
   * Execute a list of GitLab API actions
   */
  private async executeActions(actions: GitLabAction[]): Promise<void> {
    for (const action of actions) {
      try {
        const url = `${this.config.gitlabUrl}${action.endpoint}`;
        const response = await fetch(url, {
          method: action.method,
          headers: {
            'Content-Type': 'application/json',
            'PRIVATE-TOKEN': this.config.gitlabToken,
          },
          body: JSON.stringify(action.body),
        });

        if (!response.ok) {
          const text = await response.text();
          console.error(`GitLab API error (${action.type}): ${response.status} ${text}`);
        }
      } catch (err) {
        console.error(`GitLab API call failed (${action.type}):`, err);
      }
    }
  }

  private extractProjectPath(event: GitLabEvent): string {
    return event.project.path_with_namespace;
  }

  private extractMrIid(event: GitLabEvent): number | null {
    if (event.event_type === 'merge_request') return event.merge_request.iid;
    if (event.event_type === 'note' && event.merge_request) return event.merge_request.iid;
    return null;
  }
}

// =============================================================================
// FACTORY FUNCTIONS
// =============================================================================

/**
 * Create a GitLab Guardian from environment variables
 *
 * Reads from:
 * - STIX_ENFORCER_URL (default: http://localhost:3001)
 * - STIX_API_KEY
 * - GITLAB_URL (default: https://gitlab.com)
 * - GITLAB_TOKEN
 * - STIX_GITLAB_AUTO_APPROVE (default: false)
 */
export function createGitLabGuardianFromEnv(
  overrides?: Partial<GitLabGuardianConfig>
): GitLabGuardian {
  // Import dynamically to avoid circular dependency at module level
  const { createClientFromEnv } = require('../client');

  const client = overrides?.client ?? createClientFromEnv();

  return new GitLabGuardian({
    client,
    gitlabUrl: process.env.GITLAB_URL ?? 'https://gitlab.com',
    gitlabToken: process.env.GITLAB_TOKEN ?? '',
    autoApprove: process.env.STIX_GITLAB_AUTO_APPROVE === 'true',
    ...overrides,
  });
}

// =============================================================================
// HELPERS
// =============================================================================

function inferEnvironment(ref: string): 'dev' | 'test' | 'stage' | 'prod' {
  if (ref === 'main' || ref === 'master' || ref === 'production') return 'prod';
  if (ref.startsWith('staging') || ref.startsWith('stage')) return 'stage';
  if (ref.startsWith('test') || ref.startsWith('qa')) return 'test';
  return 'dev';
}
