/**
 * STIX Compliance Analyzer - Claude-Powered Reasoning Engine (SDK/Standalone)
 *
 * Uses Anthropic Claude as a compliance reasoning layer to:
 * 1. Analyze code diffs for regulatory violations with natural language explanations
 * 2. Cite specific regulatory sections (HIPAA 164.502, PCI-DSS 3.4, etc.)
 * 3. Generate remediation suggestions with code examples
 * 4. Summarize context for human approvers on QUARANTINE decisions
 *
 * This is NOT a chatbot - Claude's reasoning feeds into the STIX enforcement
 * pipeline where decisions are cryptographically signed and recorded.
 *
 * ARCHITECTURE NOTE:
 * Inside GitLab, the Duo custom agent IS Claude - no separate API call needed.
 * The compliance-gate flow's system prompt instructs Duo's built-in Claude to
 * perform the same analysis. This module is the FALLBACK for:
 *   - SDK users outside GitLab (CI/CD on other platforms)
 *   - Standalone enforcement without GitLab Duo
 *   - Programmatic analysis in custom integrations
 *   - Environments where GitLab Duo is not available
 */

import type { AuthorizationResult } from '../types';
import type { RiskTier, DecisionKind } from '@stix/shared';
import type { DiffScanResult, GitLabDiffEntry } from '../integrations/gitlab';

// =============================================================================
// TYPES
// =============================================================================

/** A single compliance violation identified by Claude */
export interface ComplianceViolation {
  /** Severity: critical, high, medium, low */
  severity: 'critical' | 'high' | 'medium' | 'low';
  /** The regulatory framework violated */
  regulation: string;
  /** Specific section/clause (e.g., "164.502(a)") */
  section: string;
  /** Human-readable violation title */
  title: string;
  /** Detailed explanation of why this is a violation */
  explanation: string;
  /** The file where the violation occurs */
  file: string;
  /** Line number (approximate, from diff context) */
  line?: number;
  /** The problematic code snippet */
  problematicCode?: string;
  /** Suggested fix with code example */
  suggestedFix?: string;
  /** Data classification (PII, PHI, PCI, SECRETS) */
  dataClassification?: string;
}

/** Complete analysis result from Claude */
export interface ComplianceAnalysis {
  /** Overall risk assessment */
  overallRisk: RiskTier;
  /** Recommended STIX decision */
  recommendedDecision: DecisionKind;
  /** Summary suitable for MR comment */
  summary: string;
  /** Detailed violations found */
  violations: ComplianceViolation[];
  /** Positive observations (things done right) */
  positives: string[];
  /** Recommendations for improvement */
  recommendations: string[];
  /** Applicable regulations for this changeset */
  applicableRegulations: string[];
  /** Whether human review is recommended */
  requiresHumanReview: boolean;
  /** Reason for human review (if applicable) */
  humanReviewReason?: string;
  /** Token usage for sustainability tracking */
  tokenUsage?: {
    inputTokens: number;
    outputTokens: number;
  };
}

/** Result of approval context summarization */
export interface ApprovalSummary {
  /** Executive summary for the approver */
  executiveSummary: string;
  /** Key risk factors */
  riskFactors: string[];
  /** Mitigating factors */
  mitigatingFactors: string[];
  /** Recommendation: approve, deny, or request_changes */
  recommendation: 'approve' | 'deny' | 'request_changes';
  /** Reasoning behind the recommendation */
  reasoning: string;
  /** Questions the approver should consider */
  questionsToConsider: string[];
}

/** Configuration for the compliance analyzer */
export interface ComplianceAnalyzerConfig {
  /** Anthropic API key (or use GitLab's injected token) */
  apiKey?: string;
  /** Anthropic API base URL */
  baseUrl?: string;
  /** Model to use (defaults to claude-sonnet-4-20250514) */
  model?: string;
  /** Active policy packs to reference */
  policyPacks?: string[];
  /** Maximum tokens for analysis response */
  maxTokens?: number;
  /** Temperature for analysis (lower = more deterministic) */
  temperature?: number;
}

// =============================================================================
// PROMPTS
// =============================================================================

const DIFF_ANALYSIS_SYSTEM_PROMPT = `You are STIX Guardian's compliance reasoning engine. You analyze code changes for regulatory compliance violations.

You have deep expertise in:
- HIPAA (Health Insurance Portability and Accountability Act) - especially 164.502, 164.312, 164.308
- PCI-DSS (Payment Card Industry Data Security Standard) - especially requirements 3, 4, 6, 8
- SOX (Sarbanes-Oxley Act) - especially Section 302, 404
- GDPR (General Data Protection Regulation) - especially Articles 5, 6, 25, 32
- CCPA (California Consumer Privacy Act)
- SOC 2 (System and Organization Controls)
- NIST Cybersecurity Framework

Your analysis feeds into a cryptographically-enforced decision pipeline. Your findings will be:
1. Evaluated against STIX policy rules
2. Recorded in a tamper-evident evidence chain (SHA-256 hash-chained, Ed25519 signed)
3. Used to generate proof tokens for compliant code

Be precise, cite specific regulatory sections, and provide actionable remediation guidance.
Do NOT hallucinate violations - only flag real compliance concerns.

Respond in JSON format matching the ComplianceAnalysis schema.`;

const APPROVAL_SUMMARY_SYSTEM_PROMPT = `You are STIX Guardian's approval assistant. You summarize compliance decisions for human reviewers.

A QUARANTINE decision means the STIX policy engine found the change requires human judgment.
Your job is to help the compliance officer make an informed decision by:
1. Clearly explaining what triggered the quarantine
2. Presenting risk factors and mitigating factors objectively
3. Offering a recommendation with reasoning
4. Suggesting questions the reviewer should consider

Be concise, objective, and action-oriented. The reviewer is busy - make it easy for them.

Respond in JSON format matching the ApprovalSummary schema.`;

function buildDiffAnalysisPrompt(
  diffs: GitLabDiffEntry[],
  scanResult: DiffScanResult,
  policyPacks: string[]
): string {
  const diffSummary = diffs.map(d => {
    const status = d.new_file ? 'NEW' : d.deleted_file ? 'DELETED' : d.renamed_file ? 'RENAMED' : 'MODIFIED';
    return `[${status}] ${d.new_path}`;
  }).join('\n');

  const addedCode = diffs
    .filter(d => !d.deleted_file)
    .map(d => {
      const added = d.diff
        .split('\n')
        .filter(l => l.startsWith('+') && !l.startsWith('+++'))
        .map(l => l.substring(1))
        .join('\n');
      return added ? `--- ${d.new_path} ---\n${added}` : '';
    })
    .filter(Boolean)
    .join('\n\n');

  const scanFindings = scanResult.findings.length > 0
    ? `\nPre-scan findings (pattern-based):\n${scanResult.findings.map(f =>
        `- [${f.type.toUpperCase()}] ${f.label} in ${f.file}: ${f.snippet}`
      ).join('\n')}`
    : '\nPre-scan: No pattern-based findings.';

  return `Analyze these code changes for compliance violations.

Active policy packs: ${policyPacks.join(', ')}

Files changed:
${diffSummary}

Added/modified code:
${addedCode.substring(0, 12000)}
${scanFindings}

Pre-scan risk tier: ${scanResult.riskTier}
Pre-scan classifications: ${scanResult.classifications.join(', ') || 'none'}

Provide a comprehensive compliance analysis in JSON format with these fields:
- overallRisk: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
- recommendedDecision: "ALLOW" | "DENY" | "QUARANTINE"
- summary: string (2-3 sentence summary)
- violations: array of {severity, regulation, section, title, explanation, file, line?, problematicCode?, suggestedFix?, dataClassification?}
- positives: string[] (things done correctly)
- recommendations: string[] (improvements to suggest)
- applicableRegulations: string[] (which regulations apply)
- requiresHumanReview: boolean
- humanReviewReason?: string`;
}

function buildApprovalSummaryPrompt(
  result: AuthorizationResult,
  analysis: ComplianceAnalysis,
  mrTitle: string,
  mrDescription?: string
): string {
  return `Summarize this QUARANTINE decision for a compliance officer.

MR Title: ${mrTitle}
${mrDescription ? `MR Description: ${mrDescription}` : ''}

STIX Decision: QUARANTINE
Reason Code: ${result.reasonCode}
Risk Tier: ${analysis.overallRisk}
Trace ID: ${result.traceId}

Violations found:
${analysis.violations.map(v =>
  `- [${v.severity.toUpperCase()}] ${v.regulation} ${v.section}: ${v.title}`
).join('\n')}

Applicable regulations: ${analysis.applicableRegulations.join(', ')}

Controls: ${result.controls.join(', ') || 'none'}

Analysis summary: ${analysis.summary}

Provide a concise approval summary in JSON format with these fields:
- executiveSummary: string (2-3 sentences max)
- riskFactors: string[]
- mitigatingFactors: string[]
- recommendation: "approve" | "deny" | "request_changes"
- reasoning: string
- questionsToConsider: string[]`;
}

// =============================================================================
// ANALYZER
// =============================================================================

/**
 * STIX Compliance Analyzer
 *
 * Uses Claude to provide intelligent compliance reasoning that feeds into
 * the STIX enforcement pipeline.
 *
 * @example
 * ```typescript
 * const analyzer = new ComplianceAnalyzer({
 *   apiKey: process.env.ANTHROPIC_API_KEY,
 *   policyPacks: ['hipaa', 'sox-pci'],
 * });
 *
 * const analysis = await analyzer.analyzeDiff(diffs, scanResult);
 * // analysis.violations contains specific regulatory citations
 * // analysis.recommendedDecision feeds into STIX policy evaluation
 * ```
 */
export class ComplianceAnalyzer {
  private readonly config: Required<ComplianceAnalyzerConfig>;

  constructor(config: ComplianceAnalyzerConfig = {}) {
    this.config = {
      apiKey: config.apiKey ?? process.env.ANTHROPIC_API_KEY ?? '',
      baseUrl: config.baseUrl ?? process.env.ANTHROPIC_BASE_URL ?? 'https://api.anthropic.com',
      model: config.model ?? 'claude-sonnet-4-20250514',
      policyPacks: config.policyPacks ?? ['default'],
      maxTokens: config.maxTokens ?? 4096,
      temperature: config.temperature ?? 0.1,
    };
  }

  /**
   * Analyze code diffs for compliance violations using Claude
   */
  async analyzeDiff(
    diffs: GitLabDiffEntry[],
    scanResult: DiffScanResult
  ): Promise<ComplianceAnalysis> {
    const prompt = buildDiffAnalysisPrompt(diffs, scanResult, this.config.policyPacks);

    const response = await this.callClaude(DIFF_ANALYSIS_SYSTEM_PROMPT, prompt);

    try {
      const analysis = JSON.parse(response.content) as ComplianceAnalysis;
      analysis.tokenUsage = response.tokenUsage;
      return analysis;
    } catch {
      // If Claude's response isn't valid JSON, return a structured fallback
      return {
        overallRisk: scanResult.riskTier,
        recommendedDecision: scanResult.riskTier === 'CRITICAL' ? 'DENY' :
                             scanResult.riskTier === 'HIGH' ? 'QUARANTINE' : 'ALLOW',
        summary: response.content.substring(0, 500),
        violations: scanResult.findings.map(f => ({
          severity: f.type === 'secret' ? 'critical' as const : 'high' as const,
          regulation: f.type === 'phi' ? 'HIPAA' : f.type === 'pci' ? 'PCI-DSS' : 'General',
          section: 'Pattern-detected',
          title: `${f.type.toUpperCase()} detected: ${f.label}`,
          explanation: `Pattern-based detection found ${f.label} in ${f.file}`,
          file: f.file,
          dataClassification: f.type.toUpperCase(),
        })),
        positives: [],
        recommendations: ['Review flagged code sections for compliance'],
        applicableRegulations: scanResult.classifications.map(c =>
          c === 'PHI' ? 'HIPAA' : c === 'PCI' ? 'PCI-DSS' : c
        ),
        requiresHumanReview: scanResult.riskTier !== 'LOW',
        tokenUsage: response.tokenUsage,
      };
    }
  }

  /**
   * Generate an approval summary for QUARANTINE decisions
   */
  async summarizeForApproval(
    result: AuthorizationResult,
    analysis: ComplianceAnalysis,
    mrTitle: string,
    mrDescription?: string
  ): Promise<ApprovalSummary> {
    const prompt = buildApprovalSummaryPrompt(result, analysis, mrTitle, mrDescription);

    const response = await this.callClaude(APPROVAL_SUMMARY_SYSTEM_PROMPT, prompt);

    try {
      return JSON.parse(response.content) as ApprovalSummary;
    } catch {
      return {
        executiveSummary: `MR "${mrTitle}" requires compliance review. ${analysis.violations.length} violation(s) detected at ${analysis.overallRisk} risk level.`,
        riskFactors: analysis.violations.map(v => `${v.regulation} ${v.section}: ${v.title}`),
        mitigatingFactors: analysis.positives,
        recommendation: analysis.overallRisk === 'CRITICAL' ? 'deny' : 'request_changes',
        reasoning: analysis.summary,
        questionsToConsider: [
          'Are the identified data flows necessary for this feature?',
          'Can sensitive data handling be deferred to a separate, reviewed module?',
        ],
      };
    }
  }

  /**
   * Generate a policy explanation for a DENY decision
   */
  async explainDenial(
    result: AuthorizationResult,
    analysis: ComplianceAnalysis
  ): Promise<string> {
    const prompt = `Explain this DENY decision in plain English for a developer.

Decision: DENY
Reason Code: ${result.reasonCode}
Explanation: ${result.explanation ?? 'Policy violation detected'}

Violations:
${analysis.violations.map(v =>
  `- [${v.severity}] ${v.regulation} ${v.section}: ${v.title}\n  ${v.explanation}\n  File: ${v.file}`
).join('\n\n')}

Controls triggered: ${result.controls.join(', ') || 'none'}
Regulations: ${result.regulations.join(', ') || 'none'}

Write a clear, developer-friendly explanation that includes:
1. What was detected and why it's a problem
2. Which specific regulation(s) apply and why
3. Exactly what needs to change to get an ALLOW
4. A brief code example showing the fix (if applicable)

Keep it concise and actionable. No jargon without explanation.`;

    const response = await this.callClaude(
      'You are a compliance engineer explaining a policy violation to a developer. Be clear, concise, and helpful.',
      prompt
    );

    return response.content;
  }

  /**
   * Call Claude API
   */
  private async callClaude(
    systemPrompt: string,
    userPrompt: string
  ): Promise<{ content: string; tokenUsage: { inputTokens: number; outputTokens: number } }> {
    const response = await fetch(`${this.config.baseUrl}/v1/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': this.config.apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: this.config.model,
        max_tokens: this.config.maxTokens,
        temperature: this.config.temperature,
        system: systemPrompt,
        messages: [{ role: 'user', content: userPrompt }],
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Anthropic API error (${response.status}): ${errorText}`);
    }

    const data = await response.json() as {
      content: Array<{ type: string; text: string }>;
      usage: { input_tokens: number; output_tokens: number };
    };

    return {
      content: data.content[0]?.text ?? '',
      tokenUsage: {
        inputTokens: data.usage?.input_tokens ?? 0,
        outputTokens: data.usage?.output_tokens ?? 0,
      },
    };
  }
}

// =============================================================================
// FACTORY
// =============================================================================

/**
 * Create a compliance analyzer from environment variables
 *
 * Reads from:
 * - ANTHROPIC_API_KEY
 * - ANTHROPIC_BASE_URL (default: https://api.anthropic.com)
 * - STIX_CLAUDE_MODEL (default: claude-sonnet-4-20250514)
 * - STIX_POLICY_PACK (default: default)
 */
export function createComplianceAnalyzerFromEnv(
  overrides?: Partial<ComplianceAnalyzerConfig>
): ComplianceAnalyzer {
  return new ComplianceAnalyzer({
    apiKey: process.env.ANTHROPIC_API_KEY,
    baseUrl: process.env.ANTHROPIC_BASE_URL,
    model: process.env.STIX_CLAUDE_MODEL ?? 'claude-sonnet-4-20250514',
    policyPacks: (process.env.STIX_POLICY_PACK ?? 'default').split(','),
    ...overrides,
  });
}

/**
 * Format a ComplianceAnalysis as a GitLab MR comment (Markdown)
 */
export function formatAnalysisAsComment(analysis: ComplianceAnalysis): string {
  let comment = `### Claude Compliance Analysis\n\n`;
  comment += `**Risk Level:** \`${analysis.overallRisk}\` | `;
  comment += `**Recommended:** \`${analysis.recommendedDecision}\`\n\n`;
  comment += `${analysis.summary}\n`;

  if (analysis.violations.length > 0) {
    comment += `\n#### Violations (${analysis.violations.length})\n\n`;

    for (const v of analysis.violations) {
      const icon = v.severity === 'critical' ? ':rotating_light:' :
                   v.severity === 'high' ? ':red_circle:' :
                   v.severity === 'medium' ? ':orange_circle:' : ':yellow_circle:';
      comment += `${icon} **${v.regulation} ${v.section}** - ${v.title}\n`;
      comment += `> ${v.explanation}\n`;
      comment += `> File: \`${v.file}\``;
      if (v.line) comment += ` (line ~${v.line})`;
      comment += '\n';

      if (v.suggestedFix) {
        comment += `\n<details><summary>Suggested Fix</summary>\n\n\`\`\`\n${v.suggestedFix}\n\`\`\`\n</details>\n`;
      }
      comment += '\n';
    }
  }

  if (analysis.positives.length > 0) {
    comment += `\n#### Positive Observations\n\n`;
    for (const p of analysis.positives) {
      comment += `- :white_check_mark: ${p}\n`;
    }
  }

  if (analysis.recommendations.length > 0) {
    comment += `\n#### Recommendations\n\n`;
    for (const r of analysis.recommendations) {
      comment += `- ${r}\n`;
    }
  }

  if (analysis.tokenUsage) {
    comment += `\n<sub>Analysis: ${analysis.tokenUsage.inputTokens + analysis.tokenUsage.outputTokens} tokens used</sub>\n`;
  }

  return comment;
}
