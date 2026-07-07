/**
 * STIX Guardian - GitLab CI Runner
 *
 * Runs the STIX compliance gate in a GitLab CI/CD pipeline.
 * Fetches MR diffs from GitLab API, runs STIX authorization,
 * and posts results back as MR comments and labels.
 *
 * Usage:
 *   node scripts/gitlab/guardian-ci.mjs \
 *     --enforcer-url http://localhost:3001 \
 *     --policy-pack default \
 *     --mr-iid 42 \
 *     --project-path org/repo \
 *     --gitlab-url https://gitlab.com \
 *     --gitlab-token $GITLAB_TOKEN
 */

function arg(name, fallback) {
  const idx = process.argv.indexOf(`--${name}`);
  if (idx === -1) return fallback;
  return process.argv[idx + 1] ?? fallback;
}

const enforcerUrl = arg('enforcer-url', 'http://localhost:3001');
const policyPack = arg('policy-pack', 'default');
const mrIid = arg('mr-iid', '');
const projectPath = arg('project-path', '');
const gitlabUrl = arg('gitlab-url', 'https://gitlab.com');
const gitlabToken = arg('gitlab-token', '');

if (!mrIid || !projectPath) {
  console.error('Missing required arguments: --mr-iid and --project-path');
  process.exit(1);
}

if (!gitlabToken) {
  console.warn('Warning: No --gitlab-token provided. Results will not be posted to GitLab.');
}

const encodedPath = encodeURIComponent(projectPath);

// =============================================================================
// PII/PHI/SECRET DETECTION (inline to avoid build dependency in CI)
// =============================================================================

const PII_PATTERNS = [
  { pattern: /\b\d{3}-\d{2}-\d{4}\b/, label: 'SSN' },
  { pattern: /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/, label: 'credit_card' },
  { pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/, label: 'email_address' },
  { pattern: /\bdate[_\s]?of[_\s]?birth\b/i, label: 'dob' },
];

const PHI_PATTERNS = [
  { pattern: /\bpatient[_\s]?(id|name|record|data|info)\b/i, label: 'patient_data' },
  { pattern: /\bdiagnos[ei]s\b/i, label: 'diagnosis' },
  { pattern: /\bmedical[_\s]?record\b/i, label: 'medical_record' },
  { pattern: /\bprescription\b/i, label: 'prescription' },
];

const SECRET_PATTERNS = [
  { pattern: /(?:api[_-]?key|apikey)\s*[:=]\s*['"][^'"]{8,}/i, label: 'api_key' },
  { pattern: /(?:password|passwd|pwd)\s*[:=]\s*['"][^'"]+/i, label: 'password' },
  { pattern: /(?:secret|token)\s*[:=]\s*['"][^'"]{8,}/i, label: 'secret_token' },
  { pattern: /-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----/, label: 'private_key' },
  { pattern: /ghp_[A-Za-z0-9_]{36,}/, label: 'github_pat' },
  { pattern: /glpat-[A-Za-z0-9_-]{20,}/, label: 'gitlab_pat' },
];

function scanDiffContent(diffs) {
  const findings = [];
  let piiDetected = false;
  let phiDetected = false;
  let secretsDetected = false;
  const classifications = [];

  for (const entry of diffs) {
    if (entry.deleted_file) continue;

    const addedLines = entry.diff
      .split('\n')
      .filter(l => l.startsWith('+') && !l.startsWith('+++'));

    for (const line of addedLines) {
      const content = line.substring(1);

      for (const { pattern, label } of PII_PATTERNS) {
        if (pattern.test(content)) {
          piiDetected = true;
          findings.push({ file: entry.new_path, type: 'PII', label, snippet: content.trim().substring(0, 100) });
        }
      }
      for (const { pattern, label } of PHI_PATTERNS) {
        if (pattern.test(content)) {
          phiDetected = true;
          findings.push({ file: entry.new_path, type: 'PHI', label, snippet: content.trim().substring(0, 100) });
        }
      }
      for (const { pattern, label } of SECRET_PATTERNS) {
        if (pattern.test(content)) {
          secretsDetected = true;
          findings.push({ file: entry.new_path, type: 'SECRET', label, snippet: content.trim().substring(0, 60) + '***' });
        }
      }
    }
  }

  if (piiDetected) classifications.push('PII');
  if (phiDetected) classifications.push('PHI');
  if (secretsDetected) classifications.push('SECRETS');

  let riskTier = 'LOW';
  if (secretsDetected) riskTier = 'CRITICAL';
  else if (phiDetected) riskTier = 'HIGH';
  else if (piiDetected) riskTier = 'MEDIUM';

  return { piiDetected, phiDetected, secretsDetected, classifications, riskTier, findings };
}

// =============================================================================
// MAIN
// =============================================================================

async function main() {
  console.log('=== STIX Guardian - Compliance Gate ===');
  console.log(`Project: ${projectPath}`);
  console.log(`MR: !${mrIid}`);
  console.log(`Enforcer: ${enforcerUrl}`);
  console.log(`Policy Pack: ${policyPack}`);
  console.log('');

  // 1. Fetch MR details
  console.log('Fetching MR details...');
  const mrResponse = await fetch(
    `${gitlabUrl}/api/v4/projects/${encodedPath}/merge_requests/${mrIid}`,
    { headers: gitlabToken ? { 'PRIVATE-TOKEN': gitlabToken } : {} }
  );

  if (!mrResponse.ok) {
    console.error(`Failed to fetch MR: ${mrResponse.status}`);
    process.exit(1);
  }

  const mr = await mrResponse.json();
  console.log(`MR Title: ${mr.title}`);
  console.log(`Target Branch: ${mr.target_branch}`);

  // 2. Fetch MR diffs
  console.log('Fetching MR diffs...');
  const diffsResponse = await fetch(
    `${gitlabUrl}/api/v4/projects/${encodedPath}/merge_requests/${mrIid}/diffs`,
    { headers: gitlabToken ? { 'PRIVATE-TOKEN': gitlabToken } : {} }
  );

  const diffs = diffsResponse.ok ? await diffsResponse.json() : [];
  console.log(`Files changed: ${diffs.length}`);

  // 3. Scan diffs for compliance signals
  console.log('Scanning for compliance signals...');
  const scan = scanDiffContent(diffs);
  console.log(`  PII detected: ${scan.piiDetected}`);
  console.log(`  PHI detected: ${scan.phiDetected}`);
  console.log(`  Secrets detected: ${scan.secretsDetected}`);
  console.log(`  Risk tier: ${scan.riskTier}`);
  console.log(`  Findings: ${scan.findings.length}`);

  // 4. Build STIX AuthorizeRequest
  const isProduction = ['main', 'master', 'production'].includes(mr.target_branch);
  const authorizeRequest = {
    actor: {
      id: `gitlab:user:${mr.author?.username ?? 'unknown'}`,
      type: 'AI_AGENT',
      tenant: projectPath.split('/')[0],
      attributes: { gitlab_user_id: mr.author?.id },
    },
    action: 'mr_review',
    resource: {
      type: 'merge_request',
      id: `${projectPath}!${mrIid}`,
      classification: scan.classifications,
      attributes: {
        project_path: projectPath,
        mr_iid: parseInt(mrIid, 10),
        target_branch: mr.target_branch,
        title: mr.title,
        labels: mr.labels?.map(l => l.name ?? l) ?? [],
      },
    },
    context: {
      env: isProduction ? 'prod' : 'dev',
      purpose: 'compliance_review',
      ticket_id: `MR-${mrIid}`,
      tags: ['platform:gitlab', 'event:mr_review', `branch:${mr.target_branch}`, `policy_pack:${policyPack}`],
      signals: {
        piiDetected: scan.piiDetected,
        phiDetected: scan.phiDetected,
        secretsDetected: scan.secretsDetected,
      },
      attributes: {
        findings_count: scan.findings.length,
        files_changed: diffs.length,
      },
    },
    tool_call: {
      tool: 'gitlab.mr_review',
      risk_tier: scan.riskTier,
      args_summary: `MR !${mrIid}: "${mr.title}" → ${mr.target_branch}`,
    },
  };

  // 5. Call STIX Enforcer
  console.log('\nAuthorizing with STIX Enforcer...');
  const stixResponse = await fetch(`${enforcerUrl}/api/v1/authorize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(authorizeRequest),
  });

  if (!stixResponse.ok) {
    const errText = await stixResponse.text();
    console.error(`Enforcer error (${stixResponse.status}): ${errText}`);
    process.exit(1);
  }

  const decision = await stixResponse.json();
  console.log(`\n  Decision: ${decision.decision}`);
  console.log(`  Reason: ${decision.reason_code}`);
  console.log(`  Trace ID: ${decision.trace_id}`);
  if (decision.controls?.length) console.log(`  Controls: ${decision.controls.join(', ')}`);
  if (decision.regulations?.length) console.log(`  Regulations: ${decision.regulations.join(', ')}`);

  // 6. Format and post results to GitLab
  const icon = decision.decision === 'ALLOW' ? ':white_check_mark:' :
               decision.decision === 'DENY' ? ':x:' : ':warning:';
  const statusText = decision.decision === 'ALLOW' ? 'Compliant' :
                     decision.decision === 'DENY' ? 'Violation Detected' : 'Review Required';

  let comment = `## ${icon} STIX Guardian - ${statusText}\n\n`;
  comment += `| Field | Value |\n|---|---|\n`;
  comment += `| **Decision** | \`${decision.decision}\` |\n`;
  comment += `| **Reason** | \`${decision.reason_code}\` |\n`;
  comment += `| **Trace ID** | \`${decision.trace_id}\` |\n`;
  comment += `| **Risk Tier** | \`${scan.riskTier}\` |\n`;
  comment += `| **Policy Pack** | \`${policyPack}\` |\n`;

  if (decision.explanation) {
    comment += `\n### Explanation\n\n${decision.explanation}\n`;
  }

  if (scan.findings.length > 0 && decision.decision !== 'ALLOW') {
    comment += `\n### Findings (${scan.findings.length})\n\n`;
    comment += `| Type | Label | File | Snippet |\n|---|---|---|---|\n`;
    for (const f of scan.findings.slice(0, 15)) {
      const snippet = f.snippet.replace(/\|/g, '\\|');
      comment += `| \`${f.type}\` | \`${f.label}\` | \`${f.file}\` | ${snippet} |\n`;
    }
    if (scan.findings.length > 15) {
      comment += `\n_...and ${scan.findings.length - 15} more findings_\n`;
    }
  }

  if (decision.decision === 'ALLOW' && decision.proof_token) {
    comment += `\n### Cryptographic Proof\n\n`;
    comment += `Ed25519 signed proof token generated. Verify: \`stix-verify event --trace-id ${decision.trace_id}\`\n`;
  }

  comment += `\n---\n_Powered by STIX Guardian | Trace: \`${decision.trace_id}\`_\n`;

  // Post comment
  if (gitlabToken) {
    console.log('\nPosting results to GitLab...');

    await fetch(`${gitlabUrl}/api/v4/projects/${encodedPath}/merge_requests/${mrIid}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'PRIVATE-TOKEN': gitlabToken },
      body: JSON.stringify({ body: comment }),
    });

    // Update labels
    const labelsToAdd = decision.decision === 'ALLOW' ? 'stix:compliant' :
                        decision.decision === 'DENY' ? 'stix:violation' : 'stix:review-required';
    const labelsToRemove = ['stix:compliant', 'stix:violation', 'stix:review-required']
      .filter(l => l !== labelsToAdd)
      .join(',');

    await fetch(`${gitlabUrl}/api/v4/projects/${encodedPath}/merge_requests/${mrIid}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'PRIVATE-TOKEN': gitlabToken },
      body: JSON.stringify({ add_labels: labelsToAdd, remove_labels: labelsToRemove }),
    });

    console.log(`Labels updated: +${labelsToAdd}`);
  }

  // 7. Write CI summary
  if (process.env.CI_JOB_URL) {
    const summary = [
      `## STIX Guardian Compliance Report`,
      ``,
      `| Metric | Value |`,
      `|---|---|`,
      `| Decision | ${decision.decision} |`,
      `| Risk Tier | ${scan.riskTier} |`,
      `| Findings | ${scan.findings.length} |`,
      `| Trace ID | ${decision.trace_id} |`,
      `| Policy Pack | ${policyPack} |`,
    ].join('\n');

    // Write to job artifacts
    const { writeFileSync, mkdirSync } = await import('node:fs');
    mkdirSync('artifacts/compliance', { recursive: true });
    writeFileSync('artifacts/compliance/report.md', summary);
    console.log('\nCompliance report written to artifacts/compliance/report.md');
  }

  // 8. Exit with appropriate code
  if (decision.decision === 'DENY') {
    console.log('\n*** COMPLIANCE GATE FAILED - Merge request blocked ***');
    process.exit(1);
  } else if (decision.decision === 'QUARANTINE') {
    console.log('\n*** COMPLIANCE REVIEW REQUIRED - Awaiting human approval ***');
    // Don't fail the pipeline for QUARANTINE - let the human decide
    process.exit(0);
  } else {
    console.log('\n*** COMPLIANCE GATE PASSED ***');
    process.exit(0);
  }
}

main().catch((err) => {
  console.error('STIX Guardian failed:', err.message ?? err);
  process.exit(1);
});
