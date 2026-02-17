# STIX Performance Certification Runbook

Date: 2026-02-14

## Goal

Produce reproducible load metrics and a capacity envelope for enterprise planning.

## Commands

1. Run profile suite:
   - `pnpm perf:suite -- --url http://localhost:3101 --baseline-requests 2000 --baseline-concurrency 50 --elevated-requests 5000 --elevated-concurrency 100 --saturation-requests 4000 --saturation-start-concurrency 150 --saturation-max-concurrency 250 --output-dir artifacts/perf`
2. Generate report:
   - `pnpm perf:report -- --input artifacts/perf/profile-suite.json --output _Development_Notes/STIX_Performance_Certification.md`

## Required Profiles

1. Baseline: 2k requests at concurrency 50.
2. Elevated: 5k requests at concurrency 100.
3. Saturation probe: step concurrency by +50 until p95 > target or failure rate > 1%.

## Acceptance

- p95 authorization latency <= 150ms at baseline.
- Error rate <= 0.5% at baseline.
- Documented throughput and recommended sustained/burst envelope.
