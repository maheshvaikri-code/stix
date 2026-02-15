-- =============================================================================
-- STIX PostgreSQL Initialization Script
-- =============================================================================
-- Creates databases and tables for all STIX services
-- =============================================================================

-- Create databases for each service
CREATE DATABASE stix_policy;
CREATE DATABASE stix_evidence;
CREATE DATABASE stix_approvals;
CREATE DATABASE stix_target;

-- =============================================================================
-- POLICY SERVICE TABLES
-- =============================================================================

\c stix_policy;

CREATE TABLE IF NOT EXISTS policy_packs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    hash VARCHAR(64) NOT NULL UNIQUE,
    source VARCHAR(255),
    policies_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(name, version)
);

CREATE TABLE IF NOT EXISTS policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pack_id UUID REFERENCES policy_packs(id) ON DELETE CASCADE,
    policy_id VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    priority INTEGER NOT NULL DEFAULT 100,
    hash VARCHAR(64) NOT NULL,
    scope JSONB NOT NULL,
    conditions JSONB,
    decision VARCHAR(20) NOT NULL,
    reason_code VARCHAR(255) NOT NULL,
    controls TEXT[],
    regulations TEXT[],
    obligations JSONB,
    approval JSONB,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(pack_id, policy_id, version)
);

CREATE INDEX idx_policies_decision ON policies(decision);
CREATE INDEX idx_policies_active ON policies(active);
CREATE INDEX idx_policies_scope ON policies USING GIN(scope);

-- =============================================================================
-- EVIDENCE SERVICE TABLES
-- =============================================================================

\c stix_evidence;

CREATE TABLE IF NOT EXISTS evidence_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    trace_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,

    -- Decision fields
    decision VARCHAR(20),
    reason_code VARCHAR(255),

    -- Actor
    actor_id VARCHAR(255),
    actor_type VARCHAR(50),

    -- Action
    action_name VARCHAR(255),
    action_params JSONB,

    -- Resource
    resource_type VARCHAR(255),
    resource_id VARCHAR(255),

    -- Context
    context JSONB,

    -- Policy reference
    policy_id VARCHAR(255),
    policy_version VARCHAR(50),
    policy_hash VARCHAR(64),
    pack_hash VARCHAR(64),

    -- Integrity
    prev_hash VARCHAR(64),
    event_hash VARCHAR(64) NOT NULL,
    signature TEXT,

    -- Obligations
    obligations JSONB,

    -- Outcome
    outcome_status VARCHAR(50),
    outcome_details JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_evidence_trace_id ON evidence_events(trace_id);
CREATE INDEX idx_evidence_timestamp ON evidence_events(timestamp);
CREATE INDEX idx_evidence_actor ON evidence_events(actor_id, actor_type);
CREATE INDEX idx_evidence_decision ON evidence_events(decision);
CREATE INDEX idx_evidence_event_type ON evidence_events(event_type);

-- Hash chain verification view
CREATE VIEW evidence_chain AS
SELECT
    id,
    trace_id,
    event_hash,
    prev_hash,
    LAG(event_hash) OVER (PARTITION BY trace_id ORDER BY timestamp) as expected_prev_hash,
    CASE
        WHEN prev_hash = LAG(event_hash) OVER (PARTITION BY trace_id ORDER BY timestamp) THEN true
        WHEN prev_hash IS NULL AND LAG(event_hash) OVER (PARTITION BY trace_id ORDER BY timestamp) IS NULL THEN true
        ELSE false
    END as chain_valid
FROM evidence_events
ORDER BY trace_id, timestamp;

-- =============================================================================
-- APPROVALS SERVICE TABLES
-- =============================================================================

\c stix_approvals;

CREATE TABLE IF NOT EXISTS approval_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id VARCHAR(100) NOT NULL UNIQUE,
    trace_id VARCHAR(100) NOT NULL,

    -- Request details
    actor_id VARCHAR(255) NOT NULL,
    actor_type VARCHAR(50) NOT NULL,
    action_name VARCHAR(255) NOT NULL,
    resource_type VARCHAR(255),
    resource_id VARCHAR(255),
    context JSONB,

    -- Policy reference
    policy_id VARCHAR(255) NOT NULL,
    policy_version VARCHAR(50),
    reason_code VARCHAR(255),

    -- Approval config
    approver_roles TEXT[] NOT NULL,
    timeout_at TIMESTAMPTZ NOT NULL,

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',

    -- Resolution
    resolved_by VARCHAR(255),
    resolved_at TIMESTAMPTZ,
    resolution_decision VARCHAR(20),
    resolution_notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_approvals_status ON approval_tickets(status);
CREATE INDEX idx_approvals_trace ON approval_tickets(trace_id);
CREATE INDEX idx_approvals_timeout ON approval_tickets(timeout_at) WHERE status = 'PENDING';

-- Approval audit log
CREATE TABLE IF NOT EXISTS approval_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id VARCHAR(100) NOT NULL REFERENCES approval_tickets(ticket_id),
    action VARCHAR(50) NOT NULL,
    performed_by VARCHAR(255),
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_approval_audit_ticket ON approval_audit(ticket_id);

-- =============================================================================
-- TARGET SERVICE TABLES
-- =============================================================================

\c stix_target;

-- Example table for target-db testing
CREATE TABLE IF NOT EXISTS sample_data (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Insert sample data
INSERT INTO sample_data (name, email, data) VALUES
    ('Test User 1', 'user1@example.com', '{"level": 1}'),
    ('Test User 2', 'user2@example.com', '{"level": 2}'),
    ('Test User 3', 'user3@example.com', '{"level": 3}');

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

\c stix_evidence;

-- Function to verify hash chain integrity
CREATE OR REPLACE FUNCTION verify_evidence_chain(p_trace_id VARCHAR)
RETURNS TABLE (
    is_valid BOOLEAN,
    invalid_count INTEGER,
    first_invalid_id UUID
) AS $$
BEGIN
    RETURN QUERY
    WITH chain_check AS (
        SELECT
            id,
            chain_valid
        FROM evidence_chain
        WHERE trace_id = p_trace_id
    )
    SELECT
        bool_and(chain_valid) as is_valid,
        count(*) FILTER (WHERE NOT chain_valid)::INTEGER as invalid_count,
        min(id) FILTER (WHERE NOT chain_valid) as first_invalid_id
    FROM chain_check;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- GRANTS
-- =============================================================================

-- Grant permissions to stix user on all databases
\c stix_policy;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO stix;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO stix;

\c stix_evidence;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO stix;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO stix;

\c stix_approvals;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO stix;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO stix;

\c stix_target;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO stix;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO stix;
