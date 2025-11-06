-- ============================================================================
-- MERL-T Orchestration Database Schema
-- Migration: 001_create_orchestration_tables.sql
-- Description: Core tables for orchestration API persistence
-- Author: MERL-T Team
-- Date: January 2025
-- ============================================================================

-- Enable UUID extension for generating unique IDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for text search optimization
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- TABLE: queries
-- Description: Core query tracking table
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
    -- Status values: 'pending', 'processing', 'completed', 'failed', 'timeout'

    -- Execution Options
    options JSONB DEFAULT '{}'::jsonb,
    -- Stores max_iterations, timeout_ms, return_trace, etc.

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

-- Indexes for queries table
CREATE INDEX idx_queries_session_id ON queries(session_id);
CREATE INDEX idx_queries_user_id ON queries(user_id);
CREATE INDEX idx_queries_created_at ON queries(created_at DESC);
CREATE INDEX idx_queries_status ON queries(status);
CREATE INDEX idx_queries_session_created ON queries(session_id, created_at DESC);

-- GIN index for JSONB query_context searchability
CREATE INDEX idx_queries_query_context_gin ON queries USING GIN (query_context);

-- Text search index for query_text
CREATE INDEX idx_queries_query_text_trgm ON queries USING GIN (query_text gin_trgm_ops);

-- ============================================================================
-- TABLE: query_results
-- Description: Stores query answers and execution traces
-- ============================================================================

CREATE TABLE IF NOT EXISTS query_results (
    -- Primary Key
    result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign Key to queries
    trace_id VARCHAR(50) NOT NULL UNIQUE,

    -- Answer Data
    primary_answer TEXT NOT NULL,
    confidence NUMERIC(4, 3) NOT NULL DEFAULT 0.0,
    -- confidence: 0.000 to 1.000

    legal_basis JSONB DEFAULT '[]'::jsonb,
    -- Array of {norm_id, norm_title, article, relevance, text_excerpt}

    alternatives JSONB DEFAULT '[]'::jsonb,
    -- Array of {alternative_answer, confidence, reasoning}

    uncertainty_preserved BOOLEAN DEFAULT FALSE,
    sources_consulted JSONB DEFAULT '[]'::jsonb,

    -- Execution Trace
    execution_trace JSONB DEFAULT '{}'::jsonb,
    -- Stores: stages_executed, iterations, stop_reason, experts_consulted, agents_used, total_time_ms, errors

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    -- Stores: complexity_score, intent_detected, concepts_identified, norms_consulted, jurisprudence_consulted

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT fk_query_results_trace_id FOREIGN KEY (trace_id)
        REFERENCES queries(trace_id) ON DELETE CASCADE,
    CONSTRAINT query_results_confidence_check CHECK (
        confidence >= 0.0 AND confidence <= 1.0
    )
);

-- Indexes for query_results table
CREATE INDEX idx_query_results_trace_id ON query_results(trace_id);
CREATE INDEX idx_query_results_confidence ON query_results(confidence DESC);
CREATE INDEX idx_query_results_created_at ON query_results(created_at DESC);

-- GIN indexes for JSONB fields
CREATE INDEX idx_query_results_legal_basis_gin ON query_results USING GIN (legal_basis);
CREATE INDEX idx_query_results_execution_trace_gin ON query_results USING GIN (execution_trace);
CREATE INDEX idx_query_results_metadata_gin ON query_results USING GIN (metadata);

-- ============================================================================
-- TABLE: user_feedback
-- Description: User feedback with ratings and comments
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_feedback (
    -- Primary Key
    feedback_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign Key to queries
    trace_id VARCHAR(50) NOT NULL,

    -- User Identification
    user_id VARCHAR(100),

    -- Feedback Data
    rating INTEGER NOT NULL,
    -- Rating: 1-5 stars

    feedback_text TEXT,

    categories JSONB DEFAULT '{}'::jsonb,
    -- Optional detailed ratings: {accuracy: 4, completeness: 3, clarity: 5, legal_soundness: 4}

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT fk_user_feedback_trace_id FOREIGN KEY (trace_id)
        REFERENCES queries(trace_id) ON DELETE CASCADE,
    CONSTRAINT user_feedback_rating_check CHECK (
        rating >= 1 AND rating <= 5
    )
);

-- Indexes for user_feedback table
CREATE INDEX idx_user_feedback_trace_id ON user_feedback(trace_id);
CREATE INDEX idx_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX idx_user_feedback_rating ON user_feedback(rating);
CREATE INDEX idx_user_feedback_created_at ON user_feedback(created_at DESC);

-- GIN index for categories JSONB
CREATE INDEX idx_user_feedback_categories_gin ON user_feedback USING GIN (categories);

-- ============================================================================
-- TABLE: rlcf_feedback
-- Description: RLCF expert feedback with corrections and authority weighting
-- ============================================================================

CREATE TABLE IF NOT EXISTS rlcf_feedback (
    -- Primary Key
    feedback_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign Key to queries
    trace_id VARCHAR(50) NOT NULL,

    -- Expert Identification
    expert_id VARCHAR(100) NOT NULL,

    -- Authority Weighting
    authority_score NUMERIC(4, 3) NOT NULL,
    -- authority_score: 0.000 to 1.000

    -- Corrections Data
    corrections JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Structure: {
    --   concept_mapping: {issue: "...", correction: {...}},
    --   routing_decision: {issue: "...", improved_plan: {...}},
    --   answer_quality: {validated_answer: "...", position: "...", reasoning: "...", missing_norms: [...]}
    -- }

    overall_rating INTEGER NOT NULL,
    -- Rating: 1-5 for overall query result quality

    -- Training Examples
    training_examples_generated INTEGER DEFAULT 0,
    scheduled_for_retraining BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT fk_rlcf_feedback_trace_id FOREIGN KEY (trace_id)
        REFERENCES queries(trace_id) ON DELETE CASCADE,
    CONSTRAINT rlcf_feedback_authority_check CHECK (
        authority_score >= 0.0 AND authority_score <= 1.0
    ),
    CONSTRAINT rlcf_feedback_rating_check CHECK (
        overall_rating >= 1 AND overall_rating <= 5
    )
);

-- Indexes for rlcf_feedback table
CREATE INDEX idx_rlcf_feedback_trace_id ON rlcf_feedback(trace_id);
CREATE INDEX idx_rlcf_feedback_expert_id ON rlcf_feedback(expert_id);
CREATE INDEX idx_rlcf_feedback_authority_score ON rlcf_feedback(authority_score DESC);
CREATE INDEX idx_rlcf_feedback_created_at ON rlcf_feedback(created_at DESC);
CREATE INDEX idx_rlcf_feedback_scheduled ON rlcf_feedback(scheduled_for_retraining)
    WHERE scheduled_for_retraining = TRUE;

-- GIN index for corrections JSONB
CREATE INDEX idx_rlcf_feedback_corrections_gin ON rlcf_feedback USING GIN (corrections);

-- ============================================================================
-- TABLE: ner_corrections
-- Description: NER entity extraction corrections for model training
-- ============================================================================

CREATE TABLE IF NOT EXISTS ner_corrections (
    -- Primary Key
    correction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign Key to queries
    trace_id VARCHAR(50) NOT NULL,

    -- Expert Identification
    expert_id VARCHAR(100) NOT NULL,

    -- Correction Type
    correction_type VARCHAR(20) NOT NULL,
    -- Types: 'MISSING_ENTITY', 'SPURIOUS_ENTITY', 'WRONG_BOUNDARY', 'WRONG_TYPE'

    -- Correction Data
    correction_data JSONB NOT NULL,
    -- Structure: {
    --   text_span: "...",
    --   start_char: 37,
    --   end_char: 46,
    --   correct_label: "PERSON",
    --   incorrect_label: "ORG" (optional),
    --   attributes: {...} (optional)
    -- }

    -- Training Example
    training_example_generated BOOLEAN DEFAULT TRUE,
    scheduled_for_retraining BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT fk_ner_corrections_trace_id FOREIGN KEY (trace_id)
        REFERENCES queries(trace_id) ON DELETE CASCADE,
    CONSTRAINT ner_corrections_type_check CHECK (
        correction_type IN ('MISSING_ENTITY', 'SPURIOUS_ENTITY', 'WRONG_BOUNDARY', 'WRONG_TYPE')
    )
);

-- Indexes for ner_corrections table
CREATE INDEX idx_ner_corrections_trace_id ON ner_corrections(trace_id);
CREATE INDEX idx_ner_corrections_expert_id ON ner_corrections(expert_id);
CREATE INDEX idx_ner_corrections_type ON ner_corrections(correction_type);
CREATE INDEX idx_ner_corrections_created_at ON ner_corrections(created_at DESC);
CREATE INDEX idx_ner_corrections_scheduled ON ner_corrections(scheduled_for_retraining)
    WHERE scheduled_for_retraining = TRUE;

-- GIN index for correction_data JSONB
CREATE INDEX idx_ner_corrections_data_gin ON ner_corrections USING GIN (correction_data);

-- ============================================================================
-- TRIGGER FUNCTIONS
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
CREATE TRIGGER trigger_queries_updated_at
    BEFORE UPDATE ON queries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS FOR ANALYTICS
-- ============================================================================

-- View: Query performance metrics
CREATE OR REPLACE VIEW v_query_performance AS
SELECT
    DATE(q.created_at) AS query_date,
    COUNT(*) AS total_queries,
    COUNT(CASE WHEN q.status = 'completed' THEN 1 END) AS completed_queries,
    COUNT(CASE WHEN q.status = 'failed' THEN 1 END) AS failed_queries,
    COUNT(CASE WHEN q.status = 'timeout' THEN 1 END) AS timeout_queries,
    ROUND(AVG(EXTRACT(EPOCH FROM (q.completed_at - q.created_at)) * 1000), 2) AS avg_response_time_ms,
    ROUND(AVG(qr.confidence), 3) AS avg_confidence
FROM queries q
LEFT JOIN query_results qr ON q.trace_id = qr.trace_id
WHERE q.status = 'completed'
GROUP BY DATE(q.created_at)
ORDER BY query_date DESC;

-- View: Feedback statistics
CREATE OR REPLACE VIEW v_feedback_stats AS
SELECT
    DATE(uf.created_at) AS feedback_date,
    COUNT(*) AS total_user_feedback,
    ROUND(AVG(uf.rating), 2) AS avg_user_rating,
    COUNT(CASE WHEN uf.rating >= 4 THEN 1 END) AS positive_feedback_count,
    COUNT(CASE WHEN uf.rating <= 2 THEN 1 END) AS negative_feedback_count
FROM user_feedback uf
GROUP BY DATE(uf.created_at)
ORDER BY feedback_date DESC;

-- View: RLCF expert activity
CREATE OR REPLACE VIEW v_rlcf_expert_activity AS
SELECT
    rf.expert_id,
    COUNT(*) AS total_feedback,
    ROUND(AVG(rf.authority_score), 3) AS avg_authority_score,
    SUM(rf.training_examples_generated) AS total_training_examples,
    COUNT(CASE WHEN rf.scheduled_for_retraining THEN 1 END) AS scheduled_retraining_count,
    MAX(rf.created_at) AS last_feedback_at
FROM rlcf_feedback rf
GROUP BY rf.expert_id
ORDER BY total_feedback DESC;

-- ============================================================================
-- GRANTS (if using specific database users)
-- ============================================================================

-- Grant permissions to orchestration API user
-- Uncomment and adjust based on your user setup
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO orchestration_api;
-- GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO orchestration_api;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO orchestration_api;

-- ============================================================================
-- INITIAL DATA (Optional)
-- ============================================================================

-- No initial data required for orchestration tables

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Migration 001 completed successfully
-- Tables created: queries, query_results, user_feedback, rlcf_feedback, ner_corrections
-- Indexes created: 29 total (primary keys, foreign keys, GIN indexes)
-- Views created: v_query_performance, v_feedback_stats, v_rlcf_expert_activity
-- Triggers created: trigger_queries_updated_at
