/**
 * Tests for STIX Agent SDK - GitLab Integration
 *
 * Tests cover:
 * - Diff scanner: PII, PHI, PCI, secrets pattern detection
 * - Event normalizers: MR, pipeline, issue, note → STIX AuthorizeInput
 * - Decision mapper: STIX decisions → GitLab API actions
 * - Comment formatter: Markdown output for MR comments
 */

import { describe, it, expect } from 'vitest';
import {
  scanDiff,
  normalizeMergeRequestEvent,
  normalizePipelineEvent,
  normalizeIssueEvent,
  normalizeGitLabEvent,
  formatDecisionComment,
  mapDecisionToGitLabActions,
} from './gitlab';
import type {
  GitLabDiffEntry,
  GitLabMergeRequestEvent,
  GitLabPipelineEvent,
  GitLabIssueEvent,
  GitLabNoteEvent,
  GitLabProject,
  GitLabUser,
  GitLabAuthorizeInput,
} from './gitlab';
import type { AuthorizationResult } from '../types';

// =============================================================================
// TEST FIXTURES
// =============================================================================

const testUser: GitLabUser = {
  id: 42,
  username: 'dev-alice',
  name: 'Alice Developer',
  state: 'active',
  email: 'alice@example.com',
};

const testProject: GitLabProject = {
  id: 100,
  name: 'patient-portal',
  path_with_namespace: 'acme/patient-portal',
  default_branch: 'main',
  namespace: {
    id: 10,
    name: 'acme',
    full_path: 'acme',
  },
};

function makeMREvent(
  overrides: Partial<GitLabMergeRequestEvent> & {
    mrOverrides?: Partial<GitLabMergeRequestEvent['merge_request']>;
  } = {}
): GitLabMergeRequestEvent {
  const { mrOverrides, ...rest } = overrides;
  return {
    event_type: 'merge_request',
    action: 'open',
    merge_request: {
      iid: 42,
      title: 'Add patient data export',
      state: 'opened',
      source_branch: 'feature/export',
      target_branch: 'main',
      author: testUser,
      labels: [],
      ...mrOverrides,
    },
    project: testProject,
    ...rest,
  };
}

function makeDiff(overrides: Partial<GitLabDiffEntry> = {}): GitLabDiffEntry {
  return {
    old_path: 'src/handler.ts',
    new_path: 'src/handler.ts',
    diff: '',
    new_file: false,
    renamed_file: false,
    deleted_file: false,
    ...overrides,
  };
}

function makeAuthResult(overrides: Partial<AuthorizationResult> = {}): AuthorizationResult {
  return {
    allowed: true,
    decision: 'ALLOW',
    traceId: 'trace-abc-123',
    reasonCode: 'policy_matched',
    obligations: [],
    controls: [],
    regulations: [],
    proofToken: 'eyJ0eXAiOiJKV1QiLC...',
    ...overrides,
  };
}

// =============================================================================
// DIFF SCANNER TESTS
// =============================================================================

describe('scanDiff', () => {
  it('should detect SSN patterns in added lines', () => {
    const diffs = [makeDiff({
      diff: '--- a/src/handler.ts\n+++ b/src/handler.ts\n+const ssn = "123-45-6789";',
    })];

    const result = scanDiff(diffs);

    expect(result.piiDetected).toBe(true);
    expect(result.piiLabels).toContain('SSN');
    expect(result.classifications).toContain('PII');
    expect(result.riskTier).toBe('MEDIUM');
    expect(result.findings.length).toBeGreaterThan(0);
    expect(result.findings[0].type).toBe('pii');
    expect(result.findings[0].label).toBe('SSN');
  });

  it('should detect credit card numbers', () => {
    const diffs = [makeDiff({
      diff: '+const card = "4111 1111 1111 1111";',
    })];

    const result = scanDiff(diffs);

    expect(result.piiDetected).toBe(true);
    expect(result.piiLabels).toContain('credit_card');
  });

  it('should detect email addresses', () => {
    const diffs = [makeDiff({
      diff: '+const email = "user@hospital.org";',
    })];

    const result = scanDiff(diffs);

    expect(result.piiDetected).toBe(true);
    expect(result.piiLabels).toContain('email');
  });

  it('should detect PHI patterns (patient data)', () => {
    const diffs = [makeDiff({
      diff: '+const patient_name = getPatient();\n+const diagnosis = "Type 2 diabetes";',
    })];

    const result = scanDiff(diffs);

    expect(result.phiDetected).toBe(true);
    expect(result.phiLabels).toContain('patient_data');
    expect(result.phiLabels).toContain('diagnosis');
    expect(result.classifications).toContain('PHI');
    expect(result.riskTier).toBe('HIGH');
  });

  it('should detect medical records and prescriptions', () => {
    const diffs = [makeDiff({
      diff: '+const medical_record = fetchRecord(id);\n+const prescription = loadRx(patientId);',
    })];

    const result = scanDiff(diffs);

    expect(result.phiDetected).toBe(true);
    expect(result.phiLabels).toContain('medical_record');
    expect(result.phiLabels).toContain('prescription');
  });

  it('should detect secrets (API keys)', () => {
    const diffs = [makeDiff({
      diff: '+const api_key = "sk-1234567890abcdef1234567890abcdef12";',
    })];

    const result = scanDiff(diffs);

    expect(result.secretsDetected).toBe(true);
    expect(result.secretLabels).toContain('openai_key');
    expect(result.riskTier).toBe('CRITICAL');
    expect(result.classifications).toContain('SECRETS');
  });

  it('should detect GitHub PATs', () => {
    const diffs = [makeDiff({
      diff: '+const token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij";',
    })];

    const result = scanDiff(diffs);

    expect(result.secretsDetected).toBe(true);
    expect(result.secretLabels).toContain('github_pat');
  });

  it('should detect GitLab PATs', () => {
    const diffs = [makeDiff({
      diff: '+const token = "glpat-ABCDEFGHIJKLMNOPQRSTx";',
    })];

    const result = scanDiff(diffs);

    expect(result.secretsDetected).toBe(true);
    expect(result.secretLabels).toContain('gitlab_pat');
  });

  it('should detect private keys', () => {
    const diffs = [makeDiff({
      diff: '+-----BEGIN RSA PRIVATE KEY-----',
    })];

    const result = scanDiff(diffs);

    expect(result.secretsDetected).toBe(true);
    expect(result.secretLabels).toContain('private_key');
  });

  it('should detect PCI data (CVV, cardholder)', () => {
    const diffs = [makeDiff({
      diff: '+const cvv = input.cvv;\n+const card_holder = getCardHolder();',
    })];

    const result = scanDiff(diffs);

    expect(result.pciDetected).toBe(true);
    expect(result.pciLabels).toContain('cvv');
    expect(result.pciLabels).toContain('cardholder');
    expect(result.classifications).toContain('PCI');
  });

  it('should ignore deleted files', () => {
    const diffs = [makeDiff({
      diff: '+const patient_name = "secret";',
      deleted_file: true,
    })];

    const result = scanDiff(diffs);

    expect(result.piiDetected).toBe(false);
    expect(result.phiDetected).toBe(false);
    expect(result.findings.length).toBe(0);
  });

  it('should only scan added lines (not removed)', () => {
    const diffs = [makeDiff({
      diff: '-const patient_name = "John";\n context line\n+const name = "safe_var";',
    })];

    const result = scanDiff(diffs);

    // The removed line contains patient_name but should be ignored
    // The added line is safe
    expect(result.phiDetected).toBe(false);
  });

  it('should return LOW risk for clean diffs', () => {
    const diffs = [makeDiff({
      diff: '+const x = 42;\n+console.log("hello");',
    })];

    const result = scanDiff(diffs);

    expect(result.piiDetected).toBe(false);
    expect(result.phiDetected).toBe(false);
    expect(result.pciDetected).toBe(false);
    expect(result.secretsDetected).toBe(false);
    expect(result.riskTier).toBe('LOW');
    expect(result.findings.length).toBe(0);
    expect(result.classifications.length).toBe(0);
  });

  it('should handle multiple findings across multiple files', () => {
    const diffs = [
      makeDiff({
        new_path: 'src/export.ts',
        diff: '+const patient_id = getPatient();',
      }),
      makeDiff({
        new_path: 'src/api.ts',
        diff: '+const api_key = "sk-abcdef12345678901234567890123456";',
      }),
    ];

    const result = scanDiff(diffs);

    expect(result.phiDetected).toBe(true);
    expect(result.secretsDetected).toBe(true);
    expect(result.riskTier).toBe('CRITICAL'); // secrets trump PHI
    expect(result.findings.some(f => f.file === 'src/export.ts')).toBe(true);
    expect(result.findings.some(f => f.file === 'src/api.ts')).toBe(true);
  });

  it('should redact secret snippets', () => {
    const diffs = [makeDiff({
      diff: '+const api_key = "sk-abcdef12345678901234567890123456";',
    })];

    const result = scanDiff(diffs);
    const secretFinding = result.findings.find(f => f.type === 'secret');

    expect(secretFinding).toBeDefined();
    expect(secretFinding!.snippet).toContain('***REDACTED***');
  });

  it('should handle empty diffs', () => {
    const result = scanDiff([]);

    expect(result.piiDetected).toBe(false);
    expect(result.riskTier).toBe('LOW');
    expect(result.findings.length).toBe(0);
  });
});

// =============================================================================
// EVENT NORMALIZER TESTS
// =============================================================================

describe('normalizeMergeRequestEvent', () => {
  it('should normalize a basic MR open event', () => {
    const event = makeMREvent();
    const input = normalizeMergeRequestEvent(event);

    expect(input.actor.id).toBe('gitlab:user:dev-alice');
    expect(input.actor.type).toBe('AI_AGENT');
    expect(input.actor.tenant).toBe('acme');
    expect(input.action).toBe('mr_create');
    expect(input.resource.type).toBe('merge_request');
    expect(input.resource.id).toBe('acme/patient-portal!42');
    expect(input.context.env).toBe('prod'); // target branch is main
    expect(input.context.tags).toContain('platform:gitlab');
    expect(input.toolSummary).toContain('!42');
    expect(input.toolSummary).toContain('Add patient data export');
  });

  it('should map MR actions to correct STIX actions', () => {
    const actions = ['open', 'update', 'merge', 'close', 'reopen', 'approved', 'unapproved'] as const;
    const expected = ['mr_create', 'mr_update', 'mr_merge', 'mr_close', 'mr_reopen', 'mr_approve', 'mr_unapprove'];

    actions.forEach((action, i) => {
      const event = makeMREvent({ action });
      const input = normalizeMergeRequestEvent(event);
      expect(input.action).toBe(expected[i]);
    });
  });

  it('should elevate risk for production target branches', () => {
    for (const branch of ['main', 'master', 'production']) {
      const event = makeMREvent({ mrOverrides: { target_branch: branch } });
      const input = normalizeMergeRequestEvent(event);
      // 'open' normally maps to MEDIUM, elevated to HIGH for prod branches
      expect(input.riskTier).toBe('HIGH');
    }
  });

  it('should keep dev branch risk at base level', () => {
    const event = makeMREvent({
      action: 'update',
      mrOverrides: { target_branch: 'feature/something' },
    });
    const input = normalizeMergeRequestEvent(event);
    expect(input.riskTier).toBe('LOW');
    expect(input.context.env).toBe('dev');
  });

  it('should elevate risk when scan finds critical issues', () => {
    const event = makeMREvent({
      action: 'update',
      mrOverrides: { target_branch: 'dev' },
    });
    const scanResult = scanDiff([makeDiff({
      diff: '+const token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij";',
    })]);

    const input = normalizeMergeRequestEvent(event, scanResult);
    expect(input.riskTier).toBe('CRITICAL');
  });

  it('should include scan signals in context', () => {
    const scanResult = scanDiff([makeDiff({
      diff: '+const patient_id = getPatient();',
    })]);
    const event = makeMREvent();
    const input = normalizeMergeRequestEvent(event, scanResult);

    expect(input.context.signals).toBeDefined();
    expect((input.context.signals as Record<string, boolean>).phiDetected).toBe(true);
  });

  it('should include resource attributes', () => {
    const event = makeMREvent({
      mrOverrides: { draft: true, has_conflicts: true, labels: ['urgent'] },
    });
    const input = normalizeMergeRequestEvent(event);

    expect(input.resource.attributes?.is_draft).toBe(true);
    expect(input.resource.attributes?.has_conflicts).toBe(true);
    expect(input.resource.attributes?.labels).toEqual(['urgent']);
  });
});

describe('normalizePipelineEvent', () => {
  it('should normalize a pipeline event', () => {
    const event: GitLabPipelineEvent = {
      event_type: 'pipeline',
      pipeline: {
        id: 999,
        iid: 10,
        ref: 'main',
        status: 'running',
        source: 'push',
        sha: 'abc123',
        tag: false,
        stages: ['build', 'test', 'deploy'],
      },
      project: testProject,
      user: testUser,
    };

    const input = normalizePipelineEvent(event);

    expect(input.actor.id).toBe('gitlab:user:dev-alice');
    expect(input.actor.type).toBe('JOB');
    expect(input.action).toBe('pipeline_execute');
    expect(input.resource.type).toBe('pipeline');
    expect(input.resource.id).toBe('acme/patient-portal#999');
    expect(input.riskTier).toBe('HIGH'); // main branch
    expect(input.context.env).toBe('prod');
    expect(input.context.tags).toContain('event:pipeline');
    expect(input.context.tags).toContain('ref:main');
  });

  it('should set MEDIUM risk for non-production refs', () => {
    const event: GitLabPipelineEvent = {
      event_type: 'pipeline',
      pipeline: {
        id: 1000,
        iid: 11,
        ref: 'feature/test',
        status: 'running',
        source: 'push',
        sha: 'def456',
        tag: false,
      },
      project: testProject,
      user: testUser,
    };

    const input = normalizePipelineEvent(event);
    expect(input.riskTier).toBe('MEDIUM');
    expect(input.context.env).toBe('dev');
  });
});

describe('normalizeIssueEvent', () => {
  it('should normalize an issue event', () => {
    const event: GitLabIssueEvent = {
      event_type: 'issue',
      action: 'open',
      issue: {
        iid: 7,
        title: 'Fix login bug',
        state: 'opened',
        author: testUser,
        labels: ['bug', 'priority:high'],
      },
      project: testProject,
    };

    const input = normalizeIssueEvent(event);

    expect(input.actor.type).toBe('HUMAN');
    expect(input.action).toBe('issue_create');
    expect(input.resource.type).toBe('issue');
    expect(input.resource.id).toBe('acme/patient-portal#7');
    expect(input.riskTier).toBe('LOW');
    expect(input.context.tags).toContain('label:bug');
    expect(input.context.tags).toContain('label:priority:high');
  });

  it('should set HIGH risk for confidential issues', () => {
    const event: GitLabIssueEvent = {
      event_type: 'issue',
      action: 'open',
      issue: {
        iid: 8,
        title: 'Security vulnerability report',
        state: 'opened',
        author: testUser,
        confidential: true,
      },
      project: testProject,
    };

    const input = normalizeIssueEvent(event);
    expect(input.riskTier).toBe('HIGH');
    expect(input.resource.classification).toEqual(['CONFIDENTIAL']);
  });
});

describe('normalizeGitLabEvent', () => {
  it('should dispatch MR events correctly', () => {
    const event = makeMREvent();
    const input = normalizeGitLabEvent(event);
    expect(input.resource.type).toBe('merge_request');
  });

  it('should dispatch pipeline events correctly', () => {
    const event: GitLabPipelineEvent = {
      event_type: 'pipeline',
      pipeline: { id: 1, iid: 1, ref: 'dev', status: 'running', source: 'push', sha: 'abc', tag: false },
      project: testProject,
      user: testUser,
    };
    const input = normalizeGitLabEvent(event);
    expect(input.resource.type).toBe('pipeline');
  });

  it('should handle note events on MRs', () => {
    const noteEvent: GitLabNoteEvent = {
      event_type: 'note',
      note: {
        id: 1,
        body: '@stix-guardian review this',
        author: testUser,
        noteable_type: 'MergeRequest',
        noteable_id: 42,
      },
      merge_request: {
        iid: 42,
        title: 'Test MR',
        state: 'opened',
        source_branch: 'feature',
        target_branch: 'main',
        author: testUser,
      },
      project: testProject,
    };

    const input = normalizeGitLabEvent(noteEvent);
    expect(input.resource.type).toBe('merge_request');
    expect(input.action).toBe('mr_update');
  });

  it('should handle note events on issues', () => {
    const noteEvent: GitLabNoteEvent = {
      event_type: 'note',
      note: {
        id: 2,
        body: 'Comment on issue',
        author: testUser,
        noteable_type: 'Issue',
        noteable_id: 7,
      },
      issue: {
        iid: 7,
        title: 'Bug report',
        state: 'opened',
        author: testUser,
      },
      project: testProject,
    };

    const input = normalizeGitLabEvent(noteEvent);
    expect(input.resource.type).toBe('issue');
    expect(input.action).toBe('issue_update');
  });

  it('should handle generic note events', () => {
    const noteEvent: GitLabNoteEvent = {
      event_type: 'note',
      note: {
        id: 3,
        body: 'Commit comment',
        author: testUser,
        noteable_type: 'Commit',
        noteable_id: 0,
      },
      project: testProject,
    };

    const input = normalizeGitLabEvent(noteEvent);
    expect(input.action).toBe('note_create');
    expect(input.resource.type).toBe('commit');
    expect(input.riskTier).toBe('LOW');
  });

  it('should scan diffs when provided with MR events', () => {
    const event = makeMREvent();
    const diffs = [makeDiff({
      diff: '+const patient_id = getData();',
    })];

    const input = normalizeGitLabEvent(event, diffs);
    expect(input.scanResult).toBeDefined();
    expect(input.scanResult!.phiDetected).toBe(true);
  });
});

// =============================================================================
// DECISION MAPPER TESTS
// =============================================================================

describe('mapDecisionToGitLabActions', () => {
  const baseInput: GitLabAuthorizeInput = {
    actor: { id: 'gitlab:user:dev-alice', type: 'AI_AGENT' },
    action: 'mr_create',
    resource: { type: 'merge_request', id: 'acme/project!42' },
    context: { env: 'prod', tags: [], signals: {} },
    riskTier: 'MEDIUM',
    toolSummary: 'MR !42: "Test" → main',
  };

  it('should generate approve actions for ALLOW decisions', () => {
    const result = makeAuthResult({ decision: 'ALLOW' });
    const response = mapDecisionToGitLabActions(
      'acme/project', 42, 'ALLOW', result, baseInput
    );

    expect(response.decision).toBe('ALLOW');
    expect(response.labelsToAdd).toContain('stix:compliant');
    expect(response.labelsToRemove).toContain('stix:violation');
    expect(response.labelsToRemove).toContain('stix:review-required');
    expect(response.actions.some(a => a.type === 'mr_approve')).toBe(true);
    expect(response.actions.some(a => a.type === 'mr_comment')).toBe(true);
  });

  it('should generate violation labels for DENY decisions', () => {
    const result = makeAuthResult({
      decision: 'DENY',
      allowed: false,
      reasonCode: 'hipaa_violation',
    });
    const response = mapDecisionToGitLabActions(
      'acme/project', 42, 'DENY', result, baseInput
    );

    expect(response.decision).toBe('DENY');
    expect(response.labelsToAdd).toContain('stix:violation');
    expect(response.labelsToRemove).toContain('stix:compliant');
    // Should NOT approve
    expect(response.actions.some(a => a.type === 'mr_approve')).toBe(false);
  });

  it('should generate review-required labels for QUARANTINE', () => {
    const result = makeAuthResult({
      decision: 'QUARANTINE',
      allowed: false,
      approvalTicketId: 'APR-001',
    });
    const response = mapDecisionToGitLabActions(
      'acme/project', 42, 'QUARANTINE', result, baseInput
    );

    expect(response.decision).toBe('QUARANTINE');
    expect(response.labelsToAdd).toContain('stix:review-required');
  });

  it('should create issue for CRITICAL DENY', () => {
    const criticalInput: GitLabAuthorizeInput = {
      ...baseInput,
      riskTier: 'CRITICAL',
      scanResult: {
        piiDetected: false,
        phiDetected: false,
        pciDetected: false,
        secretsDetected: true,
        piiLabels: [],
        phiLabels: [],
        pciLabels: [],
        secretLabels: ['api_key'],
        classifications: ['SECRETS'],
        riskTier: 'CRITICAL',
        findings: [{ file: 'src/config.ts', type: 'secret', label: 'api_key', snippet: 'api_key = "***"' }],
      },
    };

    const result = makeAuthResult({ decision: 'DENY', allowed: false });
    const response = mapDecisionToGitLabActions(
      'acme/project', 42, 'DENY', result, criticalInput
    );

    expect(response.actions.some(a => a.type === 'create_issue')).toBe(true);
    const issueAction = response.actions.find(a => a.type === 'create_issue')!;
    expect(issueAction.body.confidential).toBe(true);
    expect((issueAction.body.title as string)).toContain('Critical compliance violation');
  });

  it('should URL-encode project path in endpoints', () => {
    const result = makeAuthResult();
    const response = mapDecisionToGitLabActions(
      'acme/patient-portal', 42, 'ALLOW', result, baseInput
    );

    const commentAction = response.actions.find(a => a.type === 'mr_comment')!;
    expect(commentAction.endpoint).toContain(encodeURIComponent('acme/patient-portal'));
  });
});

// =============================================================================
// COMMENT FORMATTER TESTS
// =============================================================================

describe('formatDecisionComment', () => {
  const baseInput: GitLabAuthorizeInput = {
    actor: { id: 'gitlab:user:dev-alice', type: 'AI_AGENT' },
    action: 'mr_create',
    resource: { type: 'merge_request', id: 'acme/project!42' },
    context: { env: 'prod', tags: [], signals: {} },
    riskTier: 'MEDIUM',
    toolSummary: 'MR !42: "Test" → main',
  };

  it('should show Compliant header for ALLOW', () => {
    const result = makeAuthResult({ decision: 'ALLOW' });
    const comment = formatDecisionComment('ALLOW', result, baseInput);

    expect(comment).toContain('Compliant');
    expect(comment).toContain(':white_check_mark:');
    expect(comment).toContain('trace-abc-123');
  });

  it('should show Violation header for DENY', () => {
    const result = makeAuthResult({
      decision: 'DENY',
      allowed: false,
      reasonCode: 'hipaa_violation',
      controls: ['HIPAA-164.502'],
      regulations: ['HIPAA'],
    });
    const comment = formatDecisionComment('DENY', result, baseInput);

    expect(comment).toContain('Violation Detected');
    expect(comment).toContain(':x:');
    expect(comment).toContain('HIPAA-164.502');
    expect(comment).toContain('HIPAA');
  });

  it('should show Review Required header for QUARANTINE', () => {
    const result = makeAuthResult({
      decision: 'QUARANTINE',
      allowed: false,
      approvalTicketId: 'APR-001',
    });
    const comment = formatDecisionComment('QUARANTINE', result, baseInput);

    expect(comment).toContain('Review Required');
    expect(comment).toContain(':warning:');
    expect(comment).toContain('APR-001');
    expect(comment).toContain('Approval Required');
  });

  it('should include findings table for DENY with scan results', () => {
    const inputWithFindings: GitLabAuthorizeInput = {
      ...baseInput,
      scanResult: {
        piiDetected: true,
        phiDetected: true,
        pciDetected: false,
        secretsDetected: false,
        piiLabels: ['SSN'],
        phiLabels: ['patient_data'],
        pciLabels: [],
        secretLabels: [],
        classifications: ['PII', 'PHI'],
        riskTier: 'HIGH',
        findings: [
          { file: 'src/export.ts', type: 'pii', label: 'SSN', snippet: 'ssn = 123-45-6789' },
          { file: 'src/data.ts', type: 'phi', label: 'patient_data', snippet: 'patient_name = ...' },
        ],
      },
    };

    const result = makeAuthResult({ decision: 'DENY', allowed: false });
    const comment = formatDecisionComment('DENY', result, inputWithFindings);

    expect(comment).toContain('Findings');
    expect(comment).toContain('SSN');
    expect(comment).toContain('patient_data');
    expect(comment).toContain('src/export.ts');
  });

  it('should show proof token reference for ALLOW', () => {
    const result = makeAuthResult({ decision: 'ALLOW', proofToken: 'eyJ...' });
    const comment = formatDecisionComment('ALLOW', result, baseInput);

    expect(comment).toContain('Cryptographic Proof');
    expect(comment).toContain('stix-verify event');
  });

  it('should include STIX Guardian footer', () => {
    const result = makeAuthResult();
    const comment = formatDecisionComment('ALLOW', result, baseInput);

    expect(comment).toContain('STIX Guardian');
    expect(comment).toContain('trace-abc-123');
  });
});
