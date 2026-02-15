-- STIX Database Schema Migration 001: Initial Schema
-- This migration creates the core tables for the STIX platform

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- POLICIES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_id VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    priority INTEGER NOT NULL DEFAULT 1000,
    description TEXT,

    -- Scope
    scope_actor_type VARCHAR(50) NOT NULL DEFAULT '*',
    scope_action VARCHAR(255) NOT NULL,
    scope_resource_type VARCHAR(255) NOT NULL,

    -- Conditions (stored as JSONB for flexibility)
    conditions JSONB DEFAULT '{}',

    -- Decision
    decision VARCHAR(20) NOT NULL CHECK (decision IN ('ALLOW', 'DENY', 'QUARANTINE')),
    reason_code VARCHAR(255) NOT NULL,

    -- Obligations (for ALLOW decisions)
    obligations JSONB DEFAULT '[]',

    -- Approval config (for QUARANTINE decisions)
    approval_config JSONB,

    -- Compliance mappings
    controls TEXT[] DEFAULT '{}',
    regulations TEXT[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',

    -- Status
    active BOOLEAN NOT NULL DEFAULT true,

    -- Content hash for integrity
    content_hash VARCHAR(64) NOT NULL,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint on policy_id + version
    CONSTRAINT policies_policy_version_unique UNIQUE (policy_id, version)
);

-- Indexes for policies
CREATE INDEX idx_policies_active ON policies(active) WHERE active = true;
CREATE INDEX idx_policies_scope ON policies(scope_actor_type, scope_action, scope_resource_type);
CREATE INDEX idx_policies_priority ON policies(priority);
CREATE INDEX idx_policies_decision ON policies(decision);
CREATE INDEX idx_policies_tags ON policies USING GIN(tags);
CREATE INDEX idx_policies_controls ON policies USING GIN(controls);

-- =============================================================================
-- EVIDENCE TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS evidence (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE DEFAULT uuid_generate_v4(),
    trace_id UUID NOT NULL,

    -- Schema version for forward compatibility
    schema_version VARCHAR(10) NOT NULL DEFAULT '1.0',

    -- Timestamp with high precision
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Decision information
    decision VARCHAR(20) NOT NULL CHECK (decision IN ('ALLOW', 'DENY', 'QUARANTINE')),
    reason_code VARCHAR(255) NOT NULL,

    -- Actor
    actor_id VARCHAR(255) NOT NULL,
    actor_type VARCHAR(50) NOT NULL,
    actor_role VARCHAR(255),
    actor_tenant VARCHAR(255),
    actor_attributes JSONB DEFAULT '{}',

    -- Action
    action_name VARCHAR(255) NOT NULL,
    action_tool VARCHAR(255),
    action_risk_tier VARCHAR(20),

    -- Resource
    resource_type VARCHAR(255) NOT NULL,
    resource_id VARCHAR(255),
    resource_classification TEXT[] DEFAULT '{}',
    resource_attributes JSONB DEFAULT '{}',

    -- Context
    context_env VARCHAR(20) NOT NULL,
    context_purpose TEXT,
    context_run_id VARCHAR(255),
    context_session_id VARCHAR(255),
    context_ticket_id VARCHAR(255),
    context_jurisdiction VARCHAR(50),
    context_tags TEXT[] DEFAULT '{}',
    context_signals JSONB DEFAULT '{}',
    context_attributes JSONB DEFAULT '{}',

    -- Policy reference
    policy_id VARCHAR(255) NOT NULL,
    policy_version VARCHAR(50) NOT NULL,
    policy_hash VARCHAR(64) NOT NULL,

    -- Compliance mappings
    controls TEXT[] DEFAULT '{}',
    regulations TEXT[] DEFAULT '{}',

    -- Outcome (filled in after execution)
    outcome_status VARCHAR(20) CHECK (outcome_status IN ('SUCCESS', 'FAILED', 'SKIPPED', 'PENDING')),
    outcome_result_summary TEXT,
    outcome_error_class VARCHAR(255),
    obligations_applied JSONB DEFAULT '{}',

    -- Integrity chain
    event_hash VARCHAR(64) NOT NULL,
    prev_hash VARCHAR(64) NOT NULL,
    signature TEXT NOT NULL,
    key_id VARCHAR(255) NOT NULL,

    -- Partition key (for time-based partitioning)
    partition_date DATE NOT NULL DEFAULT CURRENT_DATE
) PARTITION BY RANGE (partition_date);

-- Create initial partitions (monthly for first year)
CREATE TABLE evidence_y2024m01 PARTITION OF evidence
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE evidence_y2024m02 PARTITION OF evidence
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE evidence_y2024m03 PARTITION OF evidence
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
CREATE TABLE evidence_y2024m04 PARTITION OF evidence
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE evidence_y2024m05 PARTITION OF evidence
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE evidence_y2024m06 PARTITION OF evidence
    FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE evidence_y2024m07 PARTITION OF evidence
    FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
CREATE TABLE evidence_y2024m08 PARTITION OF evidence
    FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE evidence_y2024m09 PARTITION OF evidence
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE evidence_y2024m10 PARTITION OF evidence
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE evidence_y2024m11 PARTITION OF evidence
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE evidence_y2024m12 PARTITION OF evidence
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
CREATE TABLE evidence_y2025m01 PARTITION OF evidence
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE evidence_y2025m02 PARTITION OF evidence
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE evidence_y2025m03 PARTITION OF evidence
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

-- Indexes for evidence
CREATE INDEX idx_evidence_trace_id ON evidence(trace_id);
CREATE INDEX idx_evidence_timestamp ON evidence(timestamp DESC);
CREATE INDEX idx_evidence_actor ON evidence(actor_id, actor_type);
CREATE INDEX idx_evidence_action ON evidence(action_name);
CREATE INDEX idx_evidence_resource ON evidence(resource_type, resource_id);
CREATE INDEX idx_evidence_decision ON evidence(decision);
CREATE INDEX idx_evidence_env ON evidence(context_env);
CREATE INDEX idx_evidence_run_id ON evidence(context_run_id) WHERE context_run_id IS NOT NULL;
CREATE INDEX idx_evidence_session ON evidence(context_session_id) WHERE context_session_id IS NOT NULL;
CREATE INDEX idx_evidence_controls ON evidence USING GIN(controls);
CREATE INDEX idx_evidence_regulations ON evidence USING GIN(regulations);

-- =============================================================================
-- APPROVALS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trace_id UUID NOT NULL,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'denied', 'expired', 'cancelled')),

    -- Requester
    actor_id VARCHAR(255) NOT NULL,
    actor_type VARCHAR(50) NOT NULL,
    actor_role VARCHAR(255),
    actor_tenant VARCHAR(255),

    -- Request details
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(255) NOT NULL,
    resource_id VARCHAR(255),
    resource_classification TEXT[] DEFAULT '{}',

    -- Context
    context_env VARCHAR(20) NOT NULL,
    context_purpose TEXT,
    context_run_id VARCHAR(255),
    context_ticket_id VARCHAR(255),
    context_attributes JSONB DEFAULT '{}',

    -- Approval requirements
    approver_role VARCHAR(255),
    required_count INTEGER NOT NULL DEFAULT 1,
    current_count INTEGER NOT NULL DEFAULT 0,
    require_justification BOOLEAN NOT NULL DEFAULT false,

    -- Policy reference
    policy_id VARCHAR(255) NOT NULL,
    policy_version VARCHAR(50) NOT NULL,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,

    -- Indexes
    CONSTRAINT approvals_trace_unique UNIQUE (trace_id)
);

-- Individual approval records
CREATE TABLE IF NOT EXISTS approval_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    approval_id UUID NOT NULL REFERENCES approvals(id) ON DELETE CASCADE,

    -- Approver
    approver_id VARCHAR(255) NOT NULL,
    approver_role VARCHAR(255),

    -- Decision
    decision VARCHAR(20) NOT NULL CHECK (decision IN ('approve', 'deny')),
    justification TEXT,

    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent duplicate approvals
    CONSTRAINT approval_records_unique UNIQUE (approval_id, approver_id)
);

-- Indexes for approvals
CREATE INDEX idx_approvals_status ON approvals(status);
CREATE INDEX idx_approvals_actor ON approvals(actor_id);
CREATE INDEX idx_approvals_expires ON approvals(expires_at) WHERE status = 'pending';
CREATE INDEX idx_approvals_created ON approvals(created_at DESC);
CREATE INDEX idx_approvals_env ON approvals(context_env);

-- =============================================================================
-- API KEYS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Key identity
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    key_prefix VARCHAR(12) NOT NULL,

    -- Permissions
    scopes TEXT[] NOT NULL DEFAULT '{}',

    -- Owner
    owner_id VARCHAR(255) NOT NULL,
    owner_type VARCHAR(50) NOT NULL,

    -- Status
    active BOOLEAN NOT NULL DEFAULT true,

    -- Rate limiting
    rate_limit_rpm INTEGER,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,

    -- Audit
    created_by VARCHAR(255) NOT NULL,
    revoked_by VARCHAR(255)
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash) WHERE active = true;
CREATE INDEX idx_api_keys_owner ON api_keys(owner_id, owner_type);
CREATE INDEX idx_api_keys_expires ON api_keys(expires_at) WHERE active = true AND expires_at IS NOT NULL;

-- =============================================================================
-- RATE LIMITS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS rate_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Identifier (actor:action:resource pattern)
    key VARCHAR(512) NOT NULL UNIQUE,

    -- Current window
    window_start TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    window_count INTEGER NOT NULL DEFAULT 0,

    -- Limits
    max_requests INTEGER NOT NULL,
    window_ms INTEGER NOT NULL,

    -- Updated
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rate_limits_key ON rate_limits(key);
CREATE INDEX idx_rate_limits_window ON rate_limits(window_start);

-- =============================================================================
-- SCHEMA MIGRATIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    version BIGINT PRIMARY KEY,
    dirty BOOLEAN NOT NULL DEFAULT false,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Record this migration
INSERT INTO schema_migrations (version, dirty) VALUES (1, false);

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to policies table
CREATE TRIGGER update_policies_updated_at
    BEFORE UPDATE ON policies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to create future evidence partitions
CREATE OR REPLACE FUNCTION create_evidence_partition(partition_date DATE)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    partition_name := 'evidence_y' || to_char(partition_date, 'YYYY') || 'm' || to_char(partition_date, 'MM');
    start_date := date_trunc('month', partition_date);
    end_date := start_date + interval '1 month';

    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF evidence FOR VALUES FROM (%L) TO (%L)',
        partition_name,
        start_date,
        end_date
    );
END;
$$ LANGUAGE plpgsql;

-- Function to expire pending approvals
CREATE OR REPLACE FUNCTION expire_pending_approvals()
RETURNS INTEGER AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    UPDATE approvals
    SET status = 'expired', resolved_at = NOW()
    WHERE status = 'pending' AND expires_at < NOW();

    GET DIAGNOSTICS expired_count = ROW_COUNT;
    RETURN expired_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- COMMENTS
-- =============================================================================
COMMENT ON TABLE policies IS 'Policy artifacts for STIX authorization decisions';
COMMENT ON TABLE evidence IS 'Immutable audit trail of all authorization decisions and outcomes';
COMMENT ON TABLE approvals IS 'Pending and resolved approval requests for quarantined actions';
COMMENT ON TABLE approval_records IS 'Individual approval/denial records from approvers';
COMMENT ON TABLE api_keys IS 'API keys for service authentication';
COMMENT ON TABLE rate_limits IS 'Rate limiting state for actors and resources';
