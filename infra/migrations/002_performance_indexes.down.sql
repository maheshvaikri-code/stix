-- STIX Database Schema Migration 002: Rollback Performance Indexes

-- Drop views
DROP VIEW IF EXISTS policy_usage;
DROP VIEW IF EXISTS approvals_summary;
DROP VIEW IF EXISTS evidence_summary;

-- Drop materialized view
DROP MATERIALIZED VIEW IF EXISTS evidence_stats_hourly;
DROP FUNCTION IF EXISTS refresh_evidence_stats_hourly();

-- Drop additional indexes
DROP INDEX CONCURRENTLY IF EXISTS idx_evidence_gin_search;
DROP INDEX CONCURRENTLY IF EXISTS idx_approvals_dashboard;
DROP INDEX CONCURRENTLY IF EXISTS idx_policies_scope_covering;
DROP INDEX CONCURRENTLY IF EXISTS idx_evidence_failed_outcome;
DROP INDEX CONCURRENTLY IF EXISTS idx_evidence_pending_outcome;
DROP INDEX CONCURRENTLY IF EXISTS idx_evidence_env_time;
DROP INDEX CONCURRENTLY IF EXISTS idx_evidence_decision_time;
DROP INDEX CONCURRENTLY IF EXISTS idx_evidence_resource_time;
DROP INDEX CONCURRENTLY IF EXISTS idx_evidence_actor_time;

-- Remove migration record
DELETE FROM schema_migrations WHERE version = 2;
