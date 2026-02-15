-- STIX Database Schema Migration 002: Performance Indexes and Optimizations

-- =============================================================================
-- ADDITIONAL INDEXES FOR COMMON QUERIES
-- =============================================================================

-- Evidence: Composite indexes for common query patterns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evidence_actor_time
    ON evidence(actor_id, timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evidence_resource_time
    ON evidence(resource_type, resource_id, timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evidence_decision_time
    ON evidence(decision, timestamp DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evidence_env_time
    ON evidence(context_env, timestamp DESC);

-- Evidence: Partial indexes for outcome status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evidence_pending_outcome
    ON evidence(trace_id, timestamp)
    WHERE outcome_status IS NULL OR outcome_status = 'PENDING';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evidence_failed_outcome
    ON evidence(timestamp DESC, actor_id)
    WHERE outcome_status = 'FAILED';

-- Policies: Covering index for scope matching
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_policies_scope_covering
    ON policies(scope_actor_type, scope_action, scope_resource_type, priority, decision)
    WHERE active = true;

-- Approvals: Index for dashboard queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_approvals_dashboard
    ON approvals(status, context_env, created_at DESC)
    WHERE status = 'pending';

-- =============================================================================
-- MATERIALIZED VIEW FOR DASHBOARD STATISTICS
-- =============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS evidence_stats_hourly AS
SELECT
    date_trunc('hour', timestamp) AS hour,
    context_env,
    decision,
    COUNT(*) as count,
    COUNT(DISTINCT actor_id) as unique_actors,
    COUNT(DISTINCT trace_id) as unique_traces
FROM evidence
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY date_trunc('hour', timestamp), context_env, decision;

CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_stats_hourly_pk
    ON evidence_stats_hourly(hour, context_env, decision);

-- Refresh function for materialized view
CREATE OR REPLACE FUNCTION refresh_evidence_stats_hourly()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY evidence_stats_hourly;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- STATISTICS VIEWS
-- =============================================================================

CREATE OR REPLACE VIEW evidence_summary AS
SELECT
    context_env,
    decision,
    COUNT(*) as total_count,
    COUNT(DISTINCT actor_id) as unique_actors,
    COUNT(DISTINCT resource_type) as unique_resource_types,
    MIN(timestamp) as first_seen,
    MAX(timestamp) as last_seen
FROM evidence
GROUP BY context_env, decision;

CREATE OR REPLACE VIEW approvals_summary AS
SELECT
    status,
    context_env,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (COALESCE(resolved_at, NOW()) - created_at))) as avg_resolution_seconds
FROM approvals
GROUP BY status, context_env;

CREATE OR REPLACE VIEW policy_usage AS
SELECT
    e.policy_id,
    e.policy_version,
    e.decision,
    COUNT(*) as usage_count,
    MAX(e.timestamp) as last_used
FROM evidence e
WHERE e.timestamp > NOW() - INTERVAL '30 days'
GROUP BY e.policy_id, e.policy_version, e.decision
ORDER BY usage_count DESC;

-- =============================================================================
-- BLOOM FILTER INDEX FOR LARGE TEXT SEARCHES
-- =============================================================================

-- Note: Requires btree_gin extension for this optimization
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Composite GIN index for full-text search on evidence
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evidence_gin_search
    ON evidence USING gin(actor_id gin_trgm_ops, action_name gin_trgm_ops)
    WHERE FALSE; -- Placeholder - enable pg_trgm if needed

-- =============================================================================
-- PARTITION MANAGEMENT
-- =============================================================================

-- Create partitions for next 12 months automatically
DO $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    FOR i IN 0..11 LOOP
        partition_date := date_trunc('month', NOW() + (i || ' months')::interval);
        partition_name := 'evidence_y' || to_char(partition_date, 'YYYY') || 'm' || to_char(partition_date, 'MM');
        start_date := partition_date;
        end_date := partition_date + interval '1 month';

        BEGIN
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF evidence FOR VALUES FROM (%L) TO (%L)',
                partition_name,
                start_date,
                end_date
            );
        EXCEPTION WHEN duplicate_table THEN
            -- Partition already exists, ignore
            NULL;
        END;
    END LOOP;
END;
$$;

-- Record this migration
INSERT INTO schema_migrations (version, dirty) VALUES (2, false)
ON CONFLICT (version) DO NOTHING;
