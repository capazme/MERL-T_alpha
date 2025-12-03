-- =============================================================================
-- KG Staging Tables Migration
-- =============================================================================
--
-- Creates tables for LLM-driven Knowledge Graph construction workflow:
-- 1. kg_staging_entities: Review queue for extracted entities
-- 2. kg_staging_relationships: Review queue for extracted relationships
-- 3. kg_edge_audit: Provenance tracking for approved relationships
-- 4. kg_quality_metrics: Quality statistics per batch
-- 5. controversy_records: Flagged controversial items
-- 6. contributions: Community contribution tracking
--
-- Author: MERL-T Team
-- Date: November 2025
-- Version: 1.0
--
-- =============================================================================

-- Create custom types (enums)
-- =============================================================================

CREATE TYPE entity_type_enum AS ENUM (
    'norma',
    'concetto_giuridico',
    'soggetto_giuridico',
    'atto_giudiziario',
    'dottrina',
    'procedura',
    'principio_giuridico',
    'responsabilita',
    'diritto_soggettivo',
    'sanzione',
    'definizione_legale',
    'fatto_giuridico',
    'modalita_giuridica',
    'sentenza',
    'contribution'
);

CREATE TYPE source_type_enum AS ENUM (
    'visualex',
    'normattiva',
    'cassazione',
    'tar',
    'corte_costituzionale',
    'curated_doctrine',
    'community_contribution',
    'rlcf_feedback',
    'documents'
);

CREATE TYPE review_status_enum AS ENUM (
    'pending',
    'approved',
    'rejected',
    'needs_revision',
    'hold'
);

CREATE TYPE doctrine_type_enum AS ENUM (
    'interpretativo',
    'critico',
    'applicativo',
    'sistematico'
);

CREATE TYPE contribution_type_enum AS ENUM (
    'academic_paper',
    'expert_commentary',
    'case_analysis',
    'practice_guide'
);

CREATE TYPE relationship_type_enum AS ENUM (
    'applica',
    'interpreta',
    'commenta',
    'cita',
    'disciplina',
    'impone',
    'esprime_principio',
    'contiene',
    'ha_versione',
    'sostituisce',
    'inserisce',
    'abroga',
    'dipende_da',
    'presuppone',
    'other'
);


-- =============================================================================
-- Table: kg_staging_entities
-- =============================================================================

CREATE TABLE kg_staging_entities (
    -- Primary Key
    id VARCHAR(36) PRIMARY KEY,

    -- Entity Classification
    entity_type entity_type_enum NOT NULL,
    source_type source_type_enum NOT NULL,

    -- Entity Metadata
    label VARCHAR(500) NOT NULL,
    description TEXT,
    metadata_json JSONB DEFAULT '{}'::JSONB,

    -- Confidence Scores
    confidence_initial FLOAT DEFAULT 0.5,
    confidence_final FLOAT,

    -- Review Workflow
    status review_status_enum DEFAULT 'pending' NOT NULL,
    reviewer_id VARCHAR(100),
    review_comments TEXT,
    review_suggestions JSONB DEFAULT '{}'::JSONB,

    -- Tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    reviewed_at TIMESTAMP,
    approved_at TIMESTAMP,

    -- Neo4j Reference
    neo4j_node_id VARCHAR(100) UNIQUE,

    -- Auditing
    created_by VARCHAR(100),
    last_modified_by VARCHAR(100),
    last_modified_at TIMESTAMP
);

-- Indexes for kg_staging_entities
CREATE INDEX idx_staging_entity_type ON kg_staging_entities(entity_type);
CREATE INDEX idx_staging_source_type ON kg_staging_entities(source_type);
CREATE INDEX idx_staging_entity_status ON kg_staging_entities(status);
CREATE INDEX idx_staging_entity_status_created ON kg_staging_entities(status, created_at);
CREATE INDEX idx_staging_entity_reviewer ON kg_staging_entities(reviewer_id, status);
CREATE INDEX idx_staging_entity_confidence ON kg_staging_entities(confidence_initial);

COMMENT ON TABLE kg_staging_entities IS 'Review queue for extracted entities before Neo4j import';
COMMENT ON COLUMN kg_staging_entities.confidence_initial IS 'Initial confidence from extraction (NER, API, LLM)';
COMMENT ON COLUMN kg_staging_entities.confidence_final IS 'Final confidence after review';
COMMENT ON COLUMN kg_staging_entities.neo4j_node_id IS 'Neo4j node ID after approval';


-- =============================================================================
-- Table: kg_staging_relationships
-- =============================================================================

CREATE TABLE kg_staging_relationships (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Relationship Type
    relationship_type VARCHAR(100) NOT NULL,

    -- Source and Target Entities
    source_entity_data JSONB NOT NULL,  -- {entity_type, identifier, properties}
    target_entity_data JSONB NOT NULL,  -- {entity_type, identifier, properties}

    -- Relationship Properties
    properties JSONB DEFAULT '{}'::JSONB,

    -- Source Tracking
    source_type source_type_enum NOT NULL,
    raw_data JSONB DEFAULT '{}'::JSONB,  -- Full extraction data

    -- Confidence
    confidence_score FLOAT DEFAULT 0.5 NOT NULL,

    -- Review Workflow
    status review_status_enum DEFAULT 'pending' NOT NULL,
    reviewer_id VARCHAR(100),
    review_comments TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}'::JSONB,  -- source_article, llm_model, etc.

    -- Tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    reviewed_at TIMESTAMP,
    approved_at TIMESTAMP,

    -- Neo4j Reference
    neo4j_edge_id VARCHAR(100),

    -- Auditing
    created_by VARCHAR(100),
    last_modified_at TIMESTAMP
);

-- Indexes for kg_staging_relationships
CREATE INDEX idx_staging_rel_type ON kg_staging_relationships(relationship_type);
CREATE INDEX idx_staging_rel_source_type ON kg_staging_relationships(source_type);
CREATE INDEX idx_staging_rel_status ON kg_staging_relationships(status);
CREATE INDEX idx_staging_rel_status_created ON kg_staging_relationships(status, created_at);
CREATE INDEX idx_staging_rel_type_status ON kg_staging_relationships(relationship_type, status);
CREATE INDEX idx_staging_rel_reviewer ON kg_staging_relationships(reviewer_id, status);
CREATE INDEX idx_staging_rel_confidence ON kg_staging_relationships(confidence_score);

-- GIN indexes for JSONB search
CREATE INDEX idx_staging_rel_source_entity_gin ON kg_staging_relationships USING GIN (source_entity_data);
CREATE INDEX idx_staging_rel_target_entity_gin ON kg_staging_relationships USING GIN (target_entity_data);
CREATE INDEX idx_staging_rel_metadata_gin ON kg_staging_relationships USING GIN (metadata);

COMMENT ON TABLE kg_staging_relationships IS 'Review queue for extracted relationships before Neo4j import';
COMMENT ON COLUMN kg_staging_relationships.source_entity_data IS 'Source entity identification (type, identifier, properties)';
COMMENT ON COLUMN kg_staging_relationships.target_entity_data IS 'Target entity identification (type, identifier, properties)';
COMMENT ON COLUMN kg_staging_relationships.confidence_score IS 'Confidence from LLM/extraction (0.0-1.0)';


-- =============================================================================
-- Table: kg_edge_audit
-- =============================================================================

CREATE TABLE kg_edge_audit (
    -- Primary Key
    id VARCHAR(36) PRIMARY KEY,

    -- Edge Identification
    edge_id VARCHAR(100) NOT NULL,
    source_node_id VARCHAR(100) NOT NULL,
    target_node_id VARCHAR(100) NOT NULL,
    relationship_type relationship_type_enum NOT NULL,

    -- Source Tracking
    source_type source_type_enum NOT NULL,
    source_record_id VARCHAR(100),  -- e.g., norm_id, sentenza_numero
    source_url TEXT,

    -- Confidence
    confidence_score FLOAT DEFAULT 0.5,

    -- Provenance
    extracted_by VARCHAR(100),  -- User or system that extracted this
    extraction_method VARCHAR(50),  -- 'manual', 'api', 'llm', 'ner'
    extraction_metadata JSONB DEFAULT '{}'::JSONB,

    -- Community Validation
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    flags INTEGER DEFAULT 0,

    -- Tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_validated_at TIMESTAMP,

    -- Auditing
    created_by VARCHAR(100),
    last_modified_at TIMESTAMP
);

-- Indexes for kg_edge_audit
CREATE INDEX idx_edge_audit_edge_id ON kg_edge_audit(edge_id);
CREATE INDEX idx_edge_audit_source_node ON kg_edge_audit(source_node_id);
CREATE INDEX idx_edge_audit_target_node ON kg_edge_audit(target_node_id);
CREATE INDEX idx_edge_audit_rel_type ON kg_edge_audit(relationship_type);
CREATE INDEX idx_edge_audit_source_type ON kg_edge_audit(source_type);
CREATE INDEX idx_edge_audit_confidence ON kg_edge_audit(confidence_score);
CREATE INDEX idx_edge_audit_extraction_method ON kg_edge_audit(extraction_method);

COMMENT ON TABLE kg_edge_audit IS 'Provenance tracking for Neo4j relationships';
COMMENT ON COLUMN kg_edge_audit.edge_id IS 'Neo4j relationship ID';
COMMENT ON COLUMN kg_edge_audit.extraction_method IS 'How this relationship was extracted (manual, api, llm, ner)';


-- =============================================================================
-- Table: kg_quality_metrics
-- =============================================================================

CREATE TABLE kg_quality_metrics (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Batch Identification
    batch_id VARCHAR(100) NOT NULL,
    metric_date DATE DEFAULT CURRENT_DATE NOT NULL,

    -- Entity Metrics
    total_entities INTEGER DEFAULT 0,
    approved_entities INTEGER DEFAULT 0,
    rejected_entities INTEGER DEFAULT 0,
    pending_entities INTEGER DEFAULT 0,
    avg_entity_confidence FLOAT,

    -- Relationship Metrics
    total_relationships INTEGER DEFAULT 0,
    approved_relationships INTEGER DEFAULT 0,
    rejected_relationships INTEGER DEFAULT 0,
    pending_relationships INTEGER DEFAULT 0,
    avg_relationship_confidence FLOAT,

    -- Source Breakdown
    entities_by_source JSONB DEFAULT '{}'::JSONB,  -- {visualex: 100, documents: 50}
    relationships_by_source JSONB DEFAULT '{}'::JSONB,

    -- Quality Indicators
    duplicate_rate FLOAT,
    conflict_rate FLOAT,
    avg_review_time_seconds FLOAT,

    -- LLM Metrics (if applicable)
    llm_cost_usd FLOAT,
    llm_api_calls INTEGER DEFAULT 0,

    -- Tracking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);

-- Indexes for kg_quality_metrics
CREATE INDEX idx_quality_metrics_batch ON kg_quality_metrics(batch_id);
CREATE INDEX idx_quality_metrics_date ON kg_quality_metrics(metric_date);

COMMENT ON TABLE kg_quality_metrics IS 'Quality statistics per ingestion batch';
COMMENT ON COLUMN kg_quality_metrics.batch_id IS 'Ingestion batch identifier (e.g., codice_civile_2043_2045)';


-- =============================================================================
-- Table: controversy_records
-- =============================================================================

CREATE TABLE controversy_records (
    -- Primary Key
    id SERIAL PRIMARY KEY,

    -- Entity Identification
    entity_id VARCHAR(100),
    entity_type entity_type_enum,

    -- Controversy Details
    controversy_type VARCHAR(50) NOT NULL,  -- 'conflicting_interpretations', 'disputed_relationship'
    description TEXT,

    -- Conflicting Views
    views JSONB DEFAULT '[]'::JSONB,  -- [{position: "...", supporters: [...], evidence: "..."}]

    -- Community Metrics
    debate_intensity FLOAT DEFAULT 0.0,  -- Based on number of conflicting votes
    resolved BOOLEAN DEFAULT FALSE,
    resolution_summary TEXT,

    -- Tracking
    flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,
    flagged_by VARCHAR(100),
    resolved_by VARCHAR(100)
);

-- Indexes for controversy_records
CREATE INDEX idx_controversy_entity_id ON controversy_records(entity_id);
CREATE INDEX idx_controversy_type ON controversy_records(controversy_type);
CREATE INDEX idx_controversy_resolved ON controversy_records(resolved);

COMMENT ON TABLE controversy_records IS 'Track controversial entities/relationships with conflicting expert views';


-- =============================================================================
-- Table: contributions
-- =============================================================================

CREATE TABLE contributions (
    -- Primary Key
    id VARCHAR(36) PRIMARY KEY,

    -- Contributor
    contributor_id VARCHAR(100) NOT NULL,
    contributor_name VARCHAR(255),

    -- Contribution Type
    contribution_type contribution_type_enum NOT NULL,

    -- Content
    title VARCHAR(500) NOT NULL,
    abstract TEXT,
    full_text TEXT,
    source_url TEXT,

    -- Metadata
    authors JSONB DEFAULT '[]'::JSONB,  -- [{name: "...", affiliation: "..."}]
    publication_year INTEGER,
    journal VARCHAR(255),
    keywords JSONB DEFAULT '[]'::JSONB,

    -- Related Entities
    related_norms JSONB DEFAULT '[]'::JSONB,  -- [urn:lex:it:codice.civile:2043, ...]
    related_concepts JSONB DEFAULT '[]'::JSONB,

    -- Review Status
    status review_status_enum DEFAULT 'pending' NOT NULL,
    reviewer_id VARCHAR(100),
    review_comments TEXT,

    -- Quality Metrics
    citation_count INTEGER DEFAULT 0,
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,

    -- Tracking
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    reviewed_at TIMESTAMP,
    published_at TIMESTAMP,

    -- Auditing
    created_by VARCHAR(100),
    last_modified_at TIMESTAMP
);

-- Indexes for contributions
CREATE INDEX idx_contributions_contributor ON contributions(contributor_id);
CREATE INDEX idx_contributions_type ON contributions(contribution_type);
CREATE INDEX idx_contributions_status ON contributions(status);
CREATE INDEX idx_contributions_year ON contributions(publication_year);

-- GIN indexes for JSONB search
CREATE INDEX idx_contributions_authors_gin ON contributions USING GIN (authors);
CREATE INDEX idx_contributions_keywords_gin ON contributions USING GIN (keywords);
CREATE INDEX idx_contributions_related_norms_gin ON contributions USING GIN (related_norms);

COMMENT ON TABLE contributions IS 'Community contributions (academic papers, expert commentary, case analyses)';


-- =============================================================================
-- Triggers for Timestamp Updates
-- =============================================================================

CREATE OR REPLACE FUNCTION update_modified_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_staging_entities_modified
    BEFORE UPDATE ON kg_staging_entities
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_timestamp();

CREATE TRIGGER trigger_staging_relationships_modified
    BEFORE UPDATE ON kg_staging_relationships
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_timestamp();

CREATE TRIGGER trigger_edge_audit_modified
    BEFORE UPDATE ON kg_edge_audit
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_timestamp();

CREATE TRIGGER trigger_contributions_modified
    BEFORE UPDATE ON contributions
    FOR EACH ROW
    EXECUTE FUNCTION update_modified_timestamp();


-- =============================================================================
-- Sample Data (for testing)
-- =============================================================================

-- Insert sample staging entity (Art. 2043 from visualex)
INSERT INTO kg_staging_entities (
    id,
    entity_type,
    source_type,
    label,
    description,
    metadata_json,
    confidence_initial,
    status,
    created_at
) VALUES (
    'norma-codice-civile-2043',
    'norma',
    'visualex',
    'Art. 2043 Codice Civile',
    'Risarcimento per fatto illecito',
    '{"urn": "urn:lex:it:codice.civile:2043", "testo_completo": "Qualunque fatto doloso o colposo...", "libro": "VI", "titolo": "Tutela dei diritti"}'::JSONB,
    0.98,
    'pending',
    CURRENT_TIMESTAMP
);

-- Insert sample LLM-extracted relationship
INSERT INTO kg_staging_relationships (
    relationship_type,
    source_entity_data,
    target_entity_data,
    properties,
    source_type,
    confidence_score,
    status,
    metadata,
    created_at
) VALUES (
    'APPLICA',
    '{"entity_type": "norma", "numero_articolo": "2043", "codice": "codice civile"}'::JSONB,
    '{"entity_type": "principio_giuridico", "nome": "Neminem laedere"}'::JSONB,
    '{"contesto": "responsabilità extracontrattuale"}'::JSONB,
    'documents',
    0.92,
    'pending',
    '{"llm_model": "google/gemini-2.5-flash", "extraction_method": "llm", "source_article": "2043"}'::JSONB,
    CURRENT_TIMESTAMP
);


-- =============================================================================
-- Migration Complete
-- =============================================================================

-- Verify tables created
SELECT
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
  AND table_name LIKE 'kg_%'
ORDER BY table_name;

COMMENT ON SCHEMA public IS 'MERL-T KG Staging Tables - Migration 001 applied';
