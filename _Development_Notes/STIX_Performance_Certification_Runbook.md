# STIX Performance Certification Runbook

Date: 2026-02-14

## Goal

Produce reproducible load metrics and a capacity envelope for enterprise planning.

## Commands

1. Run load test:
   - `pnpm perf:load -- --url http://localhost:3001 --requests 2000 --concurrency 50 --output artifacts/perf/load-result.json`
2. Generate report:
   - `pnpm perf:report -- --input artifacts/perf/load-result.json --output _Development_Notes/STIX_Performance_Certification.md`

## Required Profiles

1. Baseline: 2k requests at concurrency 50.
2. Elevated: 5k requests at concurrency 100.
3. Saturation probe: step concurrency by +50 until p95 > target or failure rate > 1%.

## Acceptance

- p95 authorization latency <= 150ms at baseline.
- Error rate <= 0.5% at baseline.
- Documented throughput and recommended sustained/burst envelope.

