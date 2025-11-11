-- ============================================================================
-- MERL-T Orchestration API - Database Migration 002
-- ============================================================================
-- Description: Authentication and rate limiting tables
-- Created: Week 8 Day 4 - API Security
-- Author: Claude Code
--
-- This migration creates 2 core tables for API security:
-- 1. api_keys - API key management with roles and quotas
-- 2. api_usage - Usage tracking for rate limiting and analytics
-- ============================================================================

-- Enable UUID extension for PostgreSQL (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE: api_keys
-- ============================================================================
-- API key management table storing hashed keys with role-based access control.
-- Supports rate limiting tiers and expiration dates.
-- ============================================================================

CREATE TABLE IF NOT EXISTS api_keys (
    -- Primary Key
    key_id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,

    -- User Association (optional - for future user management)
    user_id VARCHAR(100),

    -- API Key (SHA-256 hash for security)
    api_key_hash VARCHAR(64) NOT NULL UNIQUE,

    -- Role-Based Access Control
    role VARCHAR(20) NOT NULL DEFAULT 'user',

    -- Rate Limiting Tier
    rate_limit_tier VARCHAR(20) NOT NULL DEFAULT 'standard',

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Metadata
    description TEXT,
    created_by VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,

    -- Constraints
    CONSTRAINT api_keys_role_check CHECK (
        role IN ('admin', 'user', 'guest')
    ),
    CONSTRAINT api_keys_tier_check CHECK (
        rate_limit_tier IN ('unlimited', 'premium', 'standard', 'limited')
    )
);

-- Create indexes for api_keys table
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(api_key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_api_keys_role ON api_keys(role);
CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at ON api_keys(expires_at);

-- Add comments to api_keys table
COMMENT ON TABLE api_keys IS 'API key management with role-based access control and rate limiting tiers';
COMMENT ON COLUMN api_keys.api_key_hash IS 'SHA-256 hash of API key (never store plaintext)';
COMMENT ON COLUMN api_keys.role IS 'Access role: admin, user, guest';
COMMENT ON COLUMN api_keys.rate_limit_tier IS 'Rate limit tier: unlimited, premium, standard, limited';
COMMENT ON COLUMN api_keys.last_used_at IS 'Timestamp of last API request using this key';


-- ============================================================================
-- TABLE: api_usage
-- ============================================================================
-- API usage tracking table for rate limiting, analytics, and auditing.
-- Records every API request with timing and response information.
-- ============================================================================

CREATE TABLE IF NOT EXISTS api_usage (
    -- Primary Key
    usage_id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,

    -- Foreign Key to API Key
    key_id VARCHAR(36) NOT NULL,

    -- Request Information
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,

    -- Response Information
    response_status INTEGER NOT NULL,
    response_time_ms NUMERIC(10, 2),

    -- Client Information
    ip_address VARCHAR(45),
    user_agent TEXT,

    -- Timestamp
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT fk_api_usage_key_id FOREIGN KEY (key_id)
        REFERENCES api_keys(key_id) ON DELETE CASCADE,
    CONSTRAINT api_usage_method_check CHECK (
        method IN ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS')
    )
);

-- Create indexes for api_usage table
CREATE INDEX IF NOT EXISTS idx_api_usage_key_id ON api_usage(key_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON api_usage(endpoint);
CREATE INDEX IF NOT EXISTS idx_api_usage_timestamp ON api_usage(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_api_usage_key_timestamp ON api_usage(key_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_api_usage_response_status ON api_usage(response_status);

-- Add comments to api_usage table
COMMENT ON TABLE api_usage IS 'API usage tracking for rate limiting and analytics';
COMMENT ON COLUMN api_usage.endpoint IS 'API endpoint path (e.g., /query/execute)';
COMMENT ON COLUMN api_usage.response_time_ms IS 'Response time in milliseconds';
COMMENT ON COLUMN api_usage.ip_address IS 'Client IP address (IPv4 or IPv6)';


-- ============================================================================
-- Triggers for Automatic Timestamp Updates
-- ============================================================================

-- Trigger to update last_used_at when API key is used
CREATE OR REPLACE FUNCTION update_api_key_last_used()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE api_keys
    SET last_used_at = NEW.timestamp
    WHERE key_id = NEW.key_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_api_key_last_used
    AFTER INSERT ON api_usage
    FOR EACH ROW
    EXECUTE FUNCTION update_api_key_last_used();


-- ============================================================================
-- Helper Functions for Rate Limiting
-- ============================================================================

-- Function to count requests in time window (for rate limiting)
CREATE OR REPLACE FUNCTION count_requests_in_window(
    p_key_id VARCHAR(36),
    p_window_seconds INTEGER
)
RETURNS INTEGER AS $$
DECLARE
    request_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO request_count
    FROM api_usage
    WHERE key_id = p_key_id
      AND timestamp > NOW() - (p_window_seconds || ' seconds')::INTERVAL;

    RETURN request_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION count_requests_in_window IS 'Count API requests within sliding time window for rate limiting';


-- Function to get rate limit quota by tier
CREATE OR REPLACE FUNCTION get_rate_limit_quota(p_tier VARCHAR(20))
RETURNS INTEGER AS $$
BEGIN
    RETURN CASE p_tier
        WHEN 'unlimited' THEN 999999
        WHEN 'premium' THEN 1000
        WHEN 'standard' THEN 100
        WHEN 'limited' THEN 10
        ELSE 100  -- Default
    END;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_rate_limit_quota IS 'Get hourly rate limit quota by tier (unlimited=999999, premium=1000, standard=100, limited=10)';


-- ============================================================================
-- Indexes for Performance Optimization
-- ============================================================================

-- Composite index for rate limiting queries (key_id + recent timestamp)
CREATE INDEX IF NOT EXISTS idx_api_usage_rate_limit ON api_usage(key_id, timestamp DESC)
WHERE timestamp > NOW() - INTERVAL '1 hour';

-- Partial index for active keys only
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(key_id, role, rate_limit_tier)
WHERE is_active = TRUE;


-- ============================================================================
-- Grant Permissions (adjust as needed for your environment)
-- ============================================================================

-- Grant all privileges to merl_t user (development)
-- Uncomment and adjust for production environment

-- GRANT ALL PRIVILEGES ON TABLE api_keys TO merl_t;
-- GRANT ALL PRIVILEGES ON TABLE api_usage TO merl_t;
-- GRANT EXECUTE ON FUNCTION count_requests_in_window TO merl_t;
-- GRANT EXECUTE ON FUNCTION get_rate_limit_quota TO merl_t;


-- ============================================================================
-- Seed Data (Development Only)
-- ============================================================================

-- Insert default admin API key (hash of "merl-t-admin-key-dev-only-change-in-production")
-- SECURITY WARNING: Change this in production!
INSERT INTO api_keys (
    key_id,
    api_key_hash,
    role,
    rate_limit_tier,
    is_active,
    description,
    created_by
) VALUES (
    'admin-key-001',
    '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92',  -- SHA-256 of "merl-t-admin-key-dev-only-change-in-production"
    'admin',
    'unlimited',
    TRUE,
    'Development admin key - CHANGE IN PRODUCTION',
    'system'
) ON CONFLICT (api_key_hash) DO NOTHING;

-- Insert default user API key (hash of "merl-t-user-key-dev-only")
INSERT INTO api_keys (
    key_id,
    api_key_hash,
    role,
    rate_limit_tier,
    is_active,
    description,
    created_by
) VALUES (
    'user-key-001',
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',  -- SHA-256 of "merl-t-user-key-dev-only"
    'user',
    'standard',
    TRUE,
    'Development user key',
    'system'
) ON CONFLICT (api_key_hash) DO NOTHING;


-- ============================================================================
-- Verification Queries
-- ============================================================================

-- After running this migration, verify with:
--
-- -- List all tables
-- \dt
--
-- -- Check table structure
-- \d api_keys
-- \d api_usage
--
-- -- Verify indexes
-- \di
--
-- -- Test rate limit function
-- SELECT get_rate_limit_quota('premium');  -- Should return 1000
-- SELECT get_rate_limit_quota('standard');  -- Should return 100
--
-- -- Check seed data
-- SELECT key_id, role, rate_limit_tier, is_active, description FROM api_keys;


-- ============================================================================
-- Migration Complete
-- ============================================================================

-- Log successful migration
DO $$
BEGIN
    RAISE NOTICE 'Migration 002 completed successfully';
    RAISE NOTICE 'Created tables: api_keys, api_usage';
    RAISE NOTICE 'Created functions: count_requests_in_window, get_rate_limit_quota';
    RAISE NOTICE 'Inserted % seed API keys', (SELECT COUNT(*) FROM api_keys);
    RAISE NOTICE 'Database schema version: 002';
END
$$;
