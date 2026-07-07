/**
 * Tests for STIX Compliance Analyzer (Claude-Powered Reasoning Engine)
 *
 * Tests cover:
 * - ComplianceAnalyzer construction and config
 * - formatAnalysisAsComment output
 * - Factory function (createComplianceAnalyzerFromEnv)
 * - Fallback behavior when Claude returns invalid JSON
 *
 * Note: Tests that call Claude API are mocked to avoid requiring API keys.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  ComplianceAnalyzer,
  createComplianceAnalyzerFromEnv,
  formatAnalysisAsComment,
} from './compliance-analyzer';
import type {
  ComplianceAnalysis,
  ComplianceViolation,
} from './compliance-analyzer';
import type { GitLabDiffEntry, DiffScanResult } from '../integrations/gitlab';

// =============================================================================
// TEST FIXTURES
// =============================================================================

function makeAnalysis(overrides: Partial<ComplianceAnalysis> = {}): ComplianceAnalysis {
  return {
    overallRisk: 'HIGH',
    recommendedDecision: 'DENY',
    summary: 'Code changes expose patient health information in application logs without encryption.',
    violations: [
      {
        severity: 'critical',
        regulation: 'HIPAA',
        section: '164.502(a)',
        title: 'Minimum Necessary Standard Violation',
        explanation: 'Patient diagnosis data is logged to stdout without sanitization.',
        file: 'src/handler.ts',
        line: 42,
        problematicCode: 'console.log(`Patient: ${patient.diagnosis}`)',
        suggestedFix: 'logger.info("Patient processed", { id: patient.id })',
        dataClassification: 'PHI',
      },
      {
        severity: 'high',
        regulation: 'HIPAA',
        section: '164.312(a)(1)',
        title: 'Access Control Violation',
        explanation: 'No authentication check before accessing patient records.',
        file: 'src/api.ts',
        line: 15,
        dataClassification: 'PHI',
      },
    ],
    positives: [
      'Uses TypeScript for type safety',
      'Database queries use parameterized statements',
    ],
    recommendations: [
      'Add field-level encryption for PHI data',
      'Implement role-based access control',
    ],
    applicableRegulations: ['HIPAA', 'SOC 2'],
    requiresHumanReview: true,
    humanReviewReason: 'PHI exposure requires Privacy Officer review',
    tokenUsage: {
      inputTokens: 1500,
      outputTokens: 800,
    },
    ...overrides,
  };
}

function makeScanResult(overrides: Partial<DiffScanResult> = {}): DiffScanResult {
  return {
    piiDetected: false,
    phiDetected: true,
    pciDetected: false,
    secretsDetected: false,
    piiLabels: [],
    phiLabels: ['patient_data', 'diagnosis'],
    pciLabels: [],
    secretLabels: [],
    classifications: ['PHI'],
    riskTier: 'HIGH',
    findings: [
      {
        file: 'src/handler.ts',
        type: 'phi',
        label: 'patient_data',
        snippet: 'const patient_name = getPatient()',
      },
    ],
    ...overrides,
  };
}

function makeDiffs(): GitLabDiffEntry[] {
  return [
    {
      old_path: 'src/handler.ts',
      new_path: 'src/handler.ts',
      diff: '--- a/src/handler.ts\n+++ b/src/handler.ts\n+const patient_name = getPatient();\n+console.log(patient_name);',
      new_file: false,
      renamed_file: false,
      deleted_file: false,
    },
  ];
}

// =============================================================================
// FORMAT ANALYSIS AS COMMENT
// =============================================================================

describe('formatAnalysisAsComment', () => {
  it('should include risk level and recommended decision', () => {
    const analysis = makeAnalysis();
    const comment = formatAnalysisAsComment(analysis);

    expect(comment).toContain('Claude Compliance Analysis');
    expect(comment).toContain('`HIGH`');
    expect(comment).toContain('`DENY`');
  });

  it('should include summary', () => {
    const analysis = makeAnalysis();
    const comment = formatAnalysisAsComment(analysis);

    expect(comment).toContain('patient health information');
  });

  it('should list violations with severity icons', () => {
    const analysis = makeAnalysis();
    const comment = formatAnalysisAsComment(analysis);

    expect(comment).toContain('Violations (2)');
    expect(comment).toContain(':rotating_light:'); // critical
    expect(comment).toContain(':red_circle:'); // high
    expect(comment).toContain('HIPAA 164.502(a)');
    expect(comment).toContain('HIPAA 164.312(a)(1)');
    expect(comment).toContain('Minimum Necessary Standard Violation');
  });

  it('should include suggested fixes in collapsible sections', () => {
    const analysis = makeAnalysis();
    const comment = formatAnalysisAsComment(analysis);

    expect(comment).toContain('<details>');
    expect(comment).toContain('Suggested Fix');
    expect(comment).toContain('logger.info');
  });

  it('should include positive observations', () => {
    const analysis = makeAnalysis();
    const comment = formatAnalysisAsComment(analysis);

    expect(comment).toContain('Positive Observations');
    expect(comment).toContain(':white_check_mark:');
    expect(comment).toContain('TypeScript');
    expect(comment).toContain('parameterized statements');
  });

  it('should include recommendations', () => {
    const analysis = makeAnalysis();
    const comment = formatAnalysisAsComment(analysis);

    expect(comment).toContain('Recommendations');
    expect(comment).toContain('field-level encryption');
    expect(comment).toContain('role-based access control');
  });

  it('should show token usage', () => {
    const analysis = makeAnalysis();
    const comment = formatAnalysisAsComment(analysis);

    expect(comment).toContain('2300 tokens used'); // 1500 + 800
  });

  it('should handle analysis with no violations', () => {
    const analysis = makeAnalysis({
      overallRisk: 'LOW',
      recommendedDecision: 'ALLOW',
      violations: [],
      positives: ['Clean code'],
      recommendations: [],
    });
    const comment = formatAnalysisAsComment(analysis);

    expect(comment).toContain('`LOW`');
    expect(comment).toContain('`ALLOW`');
    expect(comment).not.toContain('Violations');
    expect(comment).toContain('Clean code');
  });

  it('should handle analysis with no positives or recommendations', () => {
    const analysis = makeAnalysis({
      positives: [],
      recommendations: [],
    });
    const comment = formatAnalysisAsComment(analysis);

    expect(comment).not.toContain('Positive Observations');
    expect(comment).not.toContain('Recommendations');
  });

  it('should handle medium and low severity icons', () => {
    const analysis = makeAnalysis({
      violations: [
        {
          severity: 'medium',
          regulation: 'SOC 2',
          section: 'CC6.1',
          title: 'Logging gap',
          explanation: 'Missing audit log for data access',
          file: 'src/db.ts',
        },
        {
          severity: 'low',
          regulation: 'NIST',
          section: 'ID.AM-1',
          title: 'Asset tracking',
          explanation: 'No asset tag on resource',
          file: 'src/config.ts',
        },
      ],
    });
    const comment = formatAnalysisAsComment(analysis);

    expect(comment).toContain(':orange_circle:'); // medium
    expect(comment).toContain(':yellow_circle:'); // low
  });

  it('should include file line references when available', () => {
    const analysis = makeAnalysis();
    const comment = formatAnalysisAsComment(analysis);

    expect(comment).toContain('line ~42');
  });

  it('should omit token usage when not provided', () => {
    const analysis = makeAnalysis({ tokenUsage: undefined });
    const comment = formatAnalysisAsComment(analysis);

    expect(comment).not.toContain('tokens used');
  });
});

// =============================================================================
// COMPLIANCE ANALYZER CONSTRUCTION
// =============================================================================

describe('ComplianceAnalyzer', () => {
  it('should construct with default config', () => {
    const analyzer = new ComplianceAnalyzer();
    // Should not throw
    expect(analyzer).toBeDefined();
  });

  it('should construct with custom config', () => {
    const analyzer = new ComplianceAnalyzer({
      apiKey: 'test-key',
      model: 'claude-sonnet-4-20250514',
      policyPacks: ['hipaa', 'sox-pci'],
      maxTokens: 2048,
      temperature: 0.2,
    });
    expect(analyzer).toBeDefined();
  });
});

// =============================================================================
// ANALYZER WITH MOCKED API
// =============================================================================

describe('ComplianceAnalyzer.analyzeDiff (mocked)', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    // Mock fetch for Anthropic API calls
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('should parse valid Claude JSON response', async () => {
    const mockAnalysis: ComplianceAnalysis = {
      overallRisk: 'HIGH',
      recommendedDecision: 'DENY',
      summary: 'PHI exposure detected.',
      violations: [{
        severity: 'critical',
        regulation: 'HIPAA',
        section: '164.502(a)',
        title: 'PHI in logs',
        explanation: 'Patient data logged to stdout',
        file: 'src/handler.ts',
      }],
      positives: [],
      recommendations: ['Encrypt PHI'],
      applicableRegulations: ['HIPAA'],
      requiresHumanReview: true,
    };

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        content: [{ type: 'text', text: JSON.stringify(mockAnalysis) }],
        usage: { input_tokens: 500, output_tokens: 300 },
      }),
    });

    const analyzer = new ComplianceAnalyzer({ apiKey: 'test-key' });
    const result = await analyzer.analyzeDiff(makeDiffs(), makeScanResult());

    expect(result.overallRisk).toBe('HIGH');
    expect(result.recommendedDecision).toBe('DENY');
    expect(result.violations.length).toBe(1);
    expect(result.violations[0].regulation).toBe('HIPAA');
    expect(result.tokenUsage).toEqual({ inputTokens: 500, outputTokens: 300 });
  });

  it('should return fallback when Claude returns invalid JSON', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        content: [{ type: 'text', text: 'This is not valid JSON, but a plain text response about compliance.' }],
        usage: { input_tokens: 200, output_tokens: 100 },
      }),
    });

    const scanResult = makeScanResult({
      riskTier: 'CRITICAL',
      findings: [{
        file: 'src/config.ts',
        type: 'secret',
        label: 'api_key',
        snippet: 'api_key = "***"',
      }],
    });

    const analyzer = new ComplianceAnalyzer({ apiKey: 'test-key' });
    const result = await analyzer.analyzeDiff(makeDiffs(), scanResult);

    // Should use scan result as fallback
    expect(result.overallRisk).toBe('CRITICAL');
    expect(result.recommendedDecision).toBe('DENY');
    expect(result.violations.length).toBe(1);
    expect(result.violations[0].severity).toBe('critical'); // secret → critical
    expect(result.summary).toContain('not valid JSON');
  });

  it('should throw on API error', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 401,
      text: async () => 'Invalid API key',
    });

    const analyzer = new ComplianceAnalyzer({ apiKey: 'bad-key' });

    await expect(analyzer.analyzeDiff(makeDiffs(), makeScanResult()))
      .rejects.toThrow('Anthropic API error (401)');
  });
});

describe('ComplianceAnalyzer.summarizeForApproval (mocked)', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('should parse valid approval summary', async () => {
    const mockSummary = {
      executiveSummary: 'MR exposes PHI data in logs.',
      riskFactors: ['Patient data in stdout'],
      mitigatingFactors: ['Uses TypeScript'],
      recommendation: 'deny',
      reasoning: 'PHI exposure is a HIPAA violation.',
      questionsToConsider: ['Is logging necessary?'],
    };

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        content: [{ type: 'text', text: JSON.stringify(mockSummary) }],
        usage: { input_tokens: 300, output_tokens: 200 },
      }),
    });

    const analyzer = new ComplianceAnalyzer({ apiKey: 'test-key' });
    const result = await analyzer.summarizeForApproval(
      {
        allowed: false,
        decision: 'QUARANTINE',
        traceId: 'trace-123',
        reasonCode: 'phi_detected',
        obligations: [],
        controls: ['HIPAA-164.502'],
        regulations: ['HIPAA'],
      },
      makeAnalysis(),
      'Add patient export',
      'Exports patient data for billing'
    );

    expect(result.recommendation).toBe('deny');
    expect(result.executiveSummary).toContain('PHI');
    expect(result.riskFactors.length).toBeGreaterThan(0);
  });

  it('should return fallback when Claude returns invalid JSON', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        content: [{ type: 'text', text: 'Plain text summary instead of JSON.' }],
        usage: { input_tokens: 100, output_tokens: 50 },
      }),
    });

    const analysis = makeAnalysis({ overallRisk: 'CRITICAL' });
    const analyzer = new ComplianceAnalyzer({ apiKey: 'test-key' });
    const result = await analyzer.summarizeForApproval(
      {
        allowed: false,
        decision: 'QUARANTINE',
        traceId: 'trace-123',
        reasonCode: 'phi_detected',
        obligations: [],
        controls: [],
        regulations: [],
      },
      analysis,
      'Test MR'
    );

    expect(result.recommendation).toBe('deny'); // CRITICAL → deny
    expect(result.executiveSummary).toContain('Test MR');
    expect(result.riskFactors.length).toBeGreaterThan(0);
  });
});

// =============================================================================
// FACTORY FUNCTION
// =============================================================================

describe('createComplianceAnalyzerFromEnv', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it('should create analyzer from env vars', () => {
    process.env.ANTHROPIC_API_KEY = 'test-env-key';
    process.env.STIX_CLAUDE_MODEL = 'claude-haiku-4-5-20251001';
    process.env.STIX_POLICY_PACK = 'hipaa,sox-pci';

    const analyzer = createComplianceAnalyzerFromEnv();
    expect(analyzer).toBeDefined();
  });

  it('should accept overrides', () => {
    const analyzer = createComplianceAnalyzerFromEnv({
      apiKey: 'override-key',
      maxTokens: 2048,
    });
    expect(analyzer).toBeDefined();
  });
});
