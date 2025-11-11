-- ============================================================================
-- MERL-T Orchestration API - Database Migration 001
-- ============================================================================
-- Description: Initial schema for orchestration API
-- Created: Week 8 - Database Integration
-- Author: Claude Code
--
-- This migration creates 5 core tables for the orchestration API:
-- 1. queries - Main query tracking
-- 2. query_results - Answer storage (1:1 with queries)
-- 3. user_feedback - User ratings and comments (1:N with queries)
-- 4. rlcf_feedback - Expert corrections with authority weighting (1:N with queries)
-- 5. ner_corrections - NER entity corrections for training (1:N with queries)
-- ============================================================================

-- Enable UUID extension for PostgreSQL (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE: queries
-- ============================================================================
-- Core query tracking table storing all legal queries with metadata,
-- execution status, and timing information.
-- ============================================================================

CREATE TABLE IF NOT EXISTS queries (
    -- Primary Key
    trace_id VARCHAR(50) PRIMARY KEY,

    -- Query Identification
    session_id VARCHAR(100),
    user_id VARCHAR(100),

    -- Query Data
    query_text TEXT NOT NULL,
    query_context JSONB DEFAULT '{}'::jsonb,
    enriched_context JSONB DEFAULT '{}'::jsonb,

    -- Execution Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',

    -- Execution Options
    options JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT queries_status_check CHECK (
        status IN ('pending', 'processing', 'completed', 'failed', 'timeout')
    )
);

-- Create indexes for queries table
CREATE INDEX IF NOT EXISTS idx_queries_trace_id ON queries(trace_id);
CREATE INDEX IF NOT EXISTS idx_queries_session_id ON queries(session_id);
CREATE INDEX IF NOT EXISTS idx_queries_user_id ON queries(user_id);
CREATE INDEX IF NOT EXISTS idx_queries_status ON queries(status);
CREATE INDEX IF NOT EXISTS idx_queries_created_at ON queries(created_at);

-- Add comment to queries table
COMMENT ON TABLE queries IS 'Main query tracking table for all legal queries';
COMMENT ON COLUMN queries.trace_id IS 'Unique trace identifier for request tracing';
COMMENT ON COLUMN queries.status IS 'Execution status: pending, processing, completed, failed, timeout';
COMMENT ON COLUMN queries.query_context IS 'Preprocessed query context (intent, entities, complexity)';
COMMENT ON COLUMN queries.enriched_context IS 'KG-enriched context (norms, concepts, relationships)';


-- ============================================================================
-- TABLE: query_results
-- ============================================================================
-- Query result table storing answers, execution traces, and metadata.
-- 1:1 relationship with queries table.
-- ============================================================================

CREATE TABLE IF NOT EXISTS query_results (
    -- Primary Key
    result_id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,

    -- Foreign Key to Query (unique = 1:1 relationship)
    trace_id VARCHAR(50) NOT NULL UNIQUE,

    -- Answer Data
    primary_answer TEXT NOT NULL,
    confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.0,

    legal_basis JSONB DEFAULT '[]'::jsonb,
    alternatives JSONB DEFAULT '[]'::jsonb,

    uncertainty_preserved BOOLEAN DEFAULT FALSE,
    sources_consulted JSONB DEFAULT '[]'::jsonb,

    -- Execution Trace
    execution_trace JSONB DEFAULT '{}'::jsonb,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT query_results_confidence_check CHECK (
        confidence >= 0.0 AND confidence <= 1.0
    ),
    CONSTRAINT fk_query_results_trace_id FOREIGN KEY (trace_id)
        REFERENCES queries(trace_id) ON DELETE CASCADE
);

-- Create indexes for query_results table
CREATE INDEX IF NOT EXISTS idx_query_results_trace_id ON query_results(trace_id);
CREATE INDEX IF NOT EXISTS idx_query_results_created_at ON query_results(created_at);

-- Add comments to query_results table
COMMENT ON TABLE query_results IS 'Query answer storage with execution traces (1:1 with queries)';
COMMENT ON COLUMN query_results.confidence IS 'Answer confidence score (0.0-1.0)';
COMMENT ON COLUMN query_results.legal_basis IS 'Array of legal basis objects (norms, articles, precedents)';
COMMENT ON COLUMN query_results.alternatives IS 'Array of alternative interpretation objects';
COMMENT ON COLUMN query_results.execution_trace IS 'Full execution trace (agents, experts, iterations)';


-- ============================================================================
-- TABLE: user_feedback
-- ============================================================================
-- User feedback table storing ratings (1-5 stars) and optional comments.
-- 1:N relationship with queries table.
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_feedback (
    -- Primary Key
    feedback_id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,

    -- Foreign Key to Query
    trace_id VARCHAR(50) NOT NULL,

    -- User Identification
    user_id VARCHAR(100),

    -- Feedback Data
    rating INTEGER NOT NULL,
    feedback_text TEXT,
    categories JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT user_feedback_rating_check CHECK (
        rating >= 1 AND rating <= 5
    ),
    CONSTRAINT fk_user_feedback_trace_id FOREIGN KEY (trace_id)
        REFERENCES queries(trace_id) ON DELETE CASCADE
);

-- Create indexes for user_feedback table
CREATE INDEX IF NOT EXISTS idx_user_feedback_trace_id ON user_feedback(trace_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON user_feedback(created_at);

-- Add comments to user_feedback table
COMMENT ON TABLE user_feedback IS 'User ratings and feedback for query results (1:N with queries)';
COMMENT ON COLUMN user_feedback.rating IS 'User rating (1-5 stars)';
COMMENT ON COLUMN user_feedback.categories IS 'Feedback categories (correctness, completeness, clarity)';


-- ============================================================================
-- TABLE: rlcf_feedback
-- ============================================================================
-- RLCF expert feedback table storing corrections with authority weighting.
-- 1:N relationship with queries table.
-- ============================================================================

CREATE TABLE IF NOT EXISTS rlcf_feedback (
    -- Primary Key
    feedback_id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,

    -- Foreign Key to Query
    trace_id VARCHAR(50) NOT NULL,

    -- Expert Identification
    expert_id VARCHAR(100) NOT NULL,

    -- Authority Weighting
    authority_score NUMERIC(4, 3) NOT NULL,

    -- Corrections Data
    corrections JSONB NOT NULL DEFAULT '{}'::jsonb,

    overall_rating INTEGER NOT NULL,

    -- Training Examples
    training_examples_generated INTEGER DEFAULT 0,
    scheduled_for_retraining BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT rlcf_feedback_authority_check CHECK (
        authority_score >= 0.0 AND authority_score <= 1.0
    ),
    CONSTRAINT rlcf_feedback_rating_check CHECK (
        overall_rating >= 1 AND overall_rating <= 5
    ),
    CONSTRAINT fk_rlcf_feedback_trace_id FOREIGN KEY (trace_id)
        REFERENCES queries(trace_id) ON DELETE CASCADE
);

-- Create indexes for rlcf_feedback table
CREATE INDEX IF NOT EXISTS idx_rlcf_feedback_trace_id ON rlcf_feedback(trace_id);
CREATE INDEX IF NOT EXISTS idx_rlcf_feedback_expert_id ON rlcf_feedback(expert_id);
CREATE INDEX IF NOT EXISTS idx_rlcf_feedback_scheduled ON rlcf_feedback(scheduled_for_retraining);
CREATE INDEX IF NOT EXISTS idx_rlcf_feedback_created_at ON rlcf_feedback(created_at);

-- Add comments to rlcf_feedback table
COMMENT ON TABLE rlcf_feedback IS 'RLCF expert corrections with authority weighting (1:N with queries)';
COMMENT ON COLUMN rlcf_feedback.authority_score IS 'Expert authority score (0.0-1.0) based on A_u(t) formula';
COMMENT ON COLUMN rlcf_feedback.corrections IS 'Expert corrections object with field-level changes';
COMMENT ON COLUMN rlcf_feedback.scheduled_for_retraining IS 'Flag for batch retraining (triggered at threshold)';


-- ============================================================================
-- TABLE: ner_corrections
-- ============================================================================
-- NER correction table storing entity extraction corrections for model training.
-- 1:N relationship with queries table.
-- ============================================================================

CREATE TABLE IF NOT EXISTS ner_corrections (
    -- Primary Key
    correction_id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,

    -- Foreign Key to Query
    trace_id VARCHAR(50) NOT NULL,

    -- Expert Identification
    expert_id VARCHAR(100) NOT NULL,

    -- Correction Type
    correction_type VARCHAR(20) NOT NULL,

    -- Correction Data
    correction_data JSONB NOT NULL,

    -- Training Example
    training_example_generated BOOLEAN DEFAULT TRUE,
    scheduled_for_retraining BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT ner_corrections_type_check CHECK (
        correction_type IN ('MISSING_ENTITY', 'SPURIOUS_ENTITY', 'WRONG_BOUNDARY', 'WRONG_TYPE')
    ),
    CONSTRAINT fk_ner_corrections_trace_id FOREIGN KEY (trace_id)
        REFERENCES queries(trace_id) ON DELETE CASCADE
);

-- Create indexes for ner_corrections table
CREATE INDEX IF NOT EXISTS idx_ner_corrections_trace_id ON ner_corrections(trace_id);
CREATE INDEX IF NOT EXISTS idx_ner_corrections_expert_id ON ner_corrections(expert_id);
CREATE INDEX IF NOT EXISTS idx_ner_corrections_type ON ner_corrections(correction_type);
CREATE INDEX IF NOT EXISTS idx_ner_corrections_scheduled ON ner_corrections(scheduled_for_retraining);
CREATE INDEX IF NOT EXISTS idx_ner_corrections_created_at ON ner_corrections(created_at);

-- Add comments to ner_corrections table
COMMENT ON TABLE ner_corrections IS 'NER entity extraction corrections for model training (1:N with queries)';
COMMENT ON COLUMN ner_corrections.correction_type IS 'Type: MISSING_ENTITY, SPURIOUS_ENTITY, WRONG_BOUNDARY, WRONG_TYPE';
COMMENT ON COLUMN ner_corrections.correction_data IS 'Correction data with entity details and spans';


-- ============================================================================
-- Additional Indexes for Performance
-- ============================================================================

-- Composite index for query history pagination
CREATE INDEX IF NOT EXISTS idx_queries_user_created ON queries(user_id, created_at DESC);

-- Composite index for status tracking
CREATE INDEX IF NOT EXISTS idx_queries_status_created ON queries(status, created_at DESC);

-- Index for JSONB query_context (GIN index for efficient JSONB queries)
CREATE INDEX IF NOT EXISTS idx_queries_query_context_gin ON queries USING gin(query_context);
CREATE INDEX IF NOT EXISTS idx_queries_enriched_context_gin ON queries USING gin(enriched_context);

-- Index for JSONB execution_trace (GIN index for trace queries)
CREATE INDEX IF NOT EXISTS idx_query_results_execution_trace_gin ON query_results USING gin(execution_trace);


-- ============================================================================
-- Triggers for updated_at Timestamp
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for queries table
CREATE TRIGGER update_queries_updated_at
    BEFORE UPDATE ON queries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- Grant Permissions (adjust as needed for your environment)
-- ============================================================================

-- Grant all privileges to merl_t user (development)
-- Uncomment and adjust for production environment

-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO merl_t;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO merl_t;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO merl_t;


-- ============================================================================
-- Verification Queries
-- ============================================================================

-- After running this migration, verify with:
--
-- -- List all tables
-- \dt
--
-- -- Check table structure
-- \d queries
-- \d query_results
-- \d user_feedback
-- \d rlcf_feedback
-- \d ner_corrections
--
-- -- Verify indexes
-- \di
--
-- -- Check constraints
-- SELECT conname, contype, conrelid::regclass, pg_get_constraintdef(oid)
-- FROM pg_constraint
-- WHERE conrelid IN ('queries'::regclass, 'query_results'::regclass,
--                    'user_feedback'::regclass, 'rlcf_feedback'::regclass,
--                    'ner_corrections'::regclass);


-- ============================================================================
-- Migration Complete
-- ============================================================================

-- Log successful migration
DO $$
BEGIN
    RAISE NOTICE 'Migration 001 completed successfully';
    RAISE NOTICE 'Created tables: queries, query_results, user_feedback, rlcf_feedback, ner_corrections';
    RAISE NOTICE 'Created % indexes', (SELECT count(*) FROM pg_indexes WHERE schemaname = 'public');
    RAISE NOTICE 'Database schema version: 001';
END
$$;
