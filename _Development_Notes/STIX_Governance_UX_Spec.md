# STIX Governance UX Spec

Date: 2026-02-14

## Delivered UI Surface

- New dashboard page: `/governance`
- Navigation link added in sidebar.

## Implemented Workflows

1. Policy lifecycle visibility by state:
   - `DRAFT -> REVIEW -> APPROVED -> DEPLOYED`
2. Delegation matrix:
   - action class to primary/backup approver mapping + SLA.
3. Reporting cadence panel:
   - daily/weekly/monthly governance tasks.

## Files

- `dashboard/src/app/governance/page.tsx`
- `dashboard/src/components/layout/sidebar.tsx`

## Next UX Iteration (Optional)

1. Bind lifecycle cards to real policy APIs.
2. Add approver delegation CRUD with RBAC.
3. Add exportable governance reports.

