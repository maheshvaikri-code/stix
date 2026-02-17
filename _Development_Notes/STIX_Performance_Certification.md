# STIX Performance Certification

Date: 2026-02-17

## Profile Suite Summary

- Target: `http://localhost:3101`
- Generated at: 2026-02-17T00:05:52.098Z

## Profiles

| Profile | Requests | Concurrency | Throughput (rps) | p95 (ms) | Failure Rate |
|---|---:|---:|---:|---:|---:|
| Baseline | 2000 | 50 | 1617.74 | 44.04 | 0.304 |
| Elevated | 5000 | 100 | 3445.9 | 46.67 | 0.6784 |
| saturation-150 | 4000 | 150 | 4057.21 | 50.6 | 0.75 |

## Saturation Findings

- Breach point: concurrency 150 (fail rate 0.75 exceeded 0.01)
- Max verified concurrency within target: 100

## Capacity Envelope (Certified)

- Recommended sustained rate: 970 req/s
- Recommended burst ceiling: 2929 req/s
- Max verified concurrency: 100
