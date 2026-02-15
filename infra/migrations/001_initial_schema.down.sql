-- STIX Database Schema Migration 001: Rollback Initial Schema
-- WARNING: This will destroy all data

-- Drop functions first
DROP FUNCTION IF EXISTS expire_pending_approvals();
DROP FUNCTION IF EXISTS create_evidence_partition(DATE);
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS rate_limits CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS approval_records CASCADE;
DROP TABLE IF EXISTS approvals CASCADE;

-- Drop evidence partitions
DROP TABLE IF EXISTS evidence_y2025m03 CASCADE;
DROP TABLE IF EXISTS evidence_y2025m02 CASCADE;
DROP TABLE IF EXISTS evidence_y2025m01 CASCADE;
DROP TABLE IF EXISTS evidence_y2024m12 CASCADE;
DROP TABLE IF EXISTS evidence_y2024m11 CASCADE;
DROP TABLE IF EXISTS evidence_y2024m10 CASCADE;
DROP TABLE IF EXISTS evidence_y2024m09 CASCADE;
DROP TABLE IF EXISTS evidence_y2024m08 CASCADE;
DROP TABLE IF EXISTS evidence_y2024m07 CASCADE;
DROP TABLE IF EXISTS evidence_y2024m06 CASCADE;
DROP TABLE IF EXISTS evidence_y2024m05 CASCADE;
DROP TABLE IF EXISTS evidence_y2024m04 CASCADE;
DROP TABLE IF EXISTS evidence_y2024m03 CASCADE;
DROP TABLE IF EXISTS evidence_y2024m02 CASCADE;
DROP TABLE IF EXISTS evidence_y2024m01 CASCADE;
DROP TABLE IF EXISTS evidence CASCADE;

DROP TABLE IF EXISTS policies CASCADE;
DROP TABLE IF EXISTS schema_migrations CASCADE;

-- Note: We don't drop extensions as they may be used by other databases
