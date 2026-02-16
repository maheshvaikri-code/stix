# STIX Governance UX Spec

Date: 2026-02-14

## Delivered UI Surface

- New dashboard page: `/governance`
- Navigation link added in sidebar.
- 2026-02-16 update: lifecycle board now API-backed from policy service and governance snapshot can be exported as Markdown.

## Implemented Workflows

1. Policy lifecycle visibility by state:
   - `DRAFT -> REVIEW -> APPROVED -> DEPLOYED`
2. Delegation matrix:
   - action class to primary/backup approver mapping + SLA.
3. Reporting cadence panel:
   - daily/weekly/monthly governance tasks.
4. Exportable governance snapshot:
   - one-click Markdown download for audit/governance packet assembly.

## Files

- `dashboard/src/app/governance/page.tsx`
- `dashboard/src/components/layout/sidebar.tsx`

## Next UX Iteration (Optional)

1. Add approver delegation CRUD with RBAC.
2. Add API-backed governance report history view.
