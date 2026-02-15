# STIX Branch Protection Checklist

This checklist is for GitHub repository settings on `STIX-Govern/stix` to keep `main` release-safe.

## 1. Branch Protection Rule (`main`)

Create a branch protection rule (or ruleset target) for `main` with:

- [ ] `Require a pull request before merging`
- [ ] `Require approvals`: at least `2` (or `1` if your team is smaller)
- [ ] `Dismiss stale pull request approvals when new commits are pushed`
- [ ] `Require review from Code Owners` (after `.github/CODEOWNERS` is defined)
- [ ] `Require conversation resolution before merging`
- [ ] `Require status checks to pass before merging`
- [ ] Add required check: `Build and Typecheck`
- [ ] `Require branches to be up to date before merging`
- [ ] `Require linear history`
- [ ] `Do not allow bypassing the above settings` (include administrators)
- [ ] `Restrict who can push to matching branches` (no direct pushes except release maintainers if strictly needed)
- [ ] `Allow force pushes`: disabled
- [ ] `Allow deletions`: disabled

## 2. Tag Protection Rule (`v*`)

Create a tag protection rule (or tag ruleset) for `v*` with:

- [ ] Only maintainers/release managers can create tags matching `v*`
- [ ] Block tag deletion for `v*`
- [ ] Block tag updates (immutable release tags)

## 3. Pull Request Governance

Use repository settings and templates to enforce review quality:

- [ ] Require PR template usage (`.github/pull_request_template.md`)
- [ ] Require linked issue/ticket in PR description
- [ ] Require risk and rollback notes for production-impacting changes
- [ ] Require evidence of local validation (`pnpm build`, targeted tests)

## 4. Workflow and Token Hardening

Current workflows already use least privilege for CI validation jobs. Keep hardening with:

- [ ] Enforce `actions` policy to allow only trusted actions
- [ ] Pin third-party actions to commit SHA where practical
- [ ] Restrict `GITHUB_TOKEN` default permissions at org/repo level
- [ ] Require environment protection rules for production deploy environments

## 5. Required Checks Baseline

Set this required check for `main`:

- [ ] `Build and Typecheck` (from `.github/workflows/ci.yml`)

Optional additional checks as maturity increases:

- [ ] Security scan (SAST/dependency scan)
- [ ] Policy pack validation workflow
- [ ] Replay/verify smoke workflow

## 6. Release Governance

`v*` tags trigger `.github/workflows/release.yml`.

- [ ] Only release maintainers can create `v*` tags
- [ ] Release tag is created from reviewed `main` commit only
- [ ] Validate generated GitHub release notes and attached source archive

## 7. Monthly Audit Cadence

Run monthly and archive evidence:

- [ ] Export branch protection configuration snapshot
- [ ] Verify required checks list still matches active workflows
- [ ] Verify maintainer list for tag/release permissions
- [ ] Verify no bypass/force-push exceptions were introduced

