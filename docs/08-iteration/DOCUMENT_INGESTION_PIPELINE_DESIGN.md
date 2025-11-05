# Document Ingestion Pipeline - Design Document

**Status**: 🚧 IN DESIGN
**Phase**: Phase 2 Week 5
**Date**: November 5, 2025
**Owner**: Claude Code

---

## 1. Overview

### Purpose
Create an LLM-based pipeline to ingest legal textbooks/manuals (PDF/DOCX/TXT) and automatically extract structured knowledge into the Neo4j Knowledge Graph according to the MERL-T KG schema.

### Key Differentiator
Unlike the previous approach (focused on ingesting specific laws from APIs), this pipeline:
- **Ingests unstructured documents** (PDF manuals, textbooks)
- **Uses LLM for extraction** (not rule-based NER)
- **Extracts all 23 node types** from knowledge-graph.md
- **Preserves complete provenance** (file, page, paragraph)

---

## 2. Architecture

###  High-Level Flow

```
┌─────────────────┐
│  PDF Manual     │
│ "Manuale di     │
│  Diritto Civile"│
└────────┬────────┘
         │
         v
┌─────────────────────────────────────────┐
│  DOCUMENT READER                        │
│  - Extract text + structure             │
│  - Page/paragraph segmentation          │
│  - Provenance tracking (file:page:para) │
└────────┬────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────┐
│  LLM EXTRACTOR                          │
│  - GPT-4/Claude via OpenRouter          │
│  - Prompt with KG schema (23 node types)│
│  - Extract entities + relationships     │
│  - Confidence scoring                   │
└────────┬────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────┐
│  VALIDATION & ENRICHMENT                │
│  - Check extracted entities             │
│  - Resolve ambiguities                  │
│  - Add cross-references                 │
└────────┬────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────┐
│  NEO4J WRITER                           │
│  - Map to KG schema                     │
│  - Create nodes with properties         │
│  - Create relationships                 │
│  - Add provenance metadata              │
└────────┬────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────┐
│  NEO4J KNOWLEDGE GRAPH                  │
│  23 node types + relationships          │
│  Full provenance for every entity       │
└─────────────────────────────────────────┘
```

---

## 3. Components

### A. Document Reader (`document_reader.py`)

**Purpose**: Extract text and structure from documents with provenance tracking.

**Supported Formats**:
- PDF (via PyPDF2 or pdfplumber)
- DOCX (via python-docx)
- TXT (plain text)

**Output**: List of `DocumentSegment` objects:
```python
@dataclass
class DocumentSegment:
    text: str
    provenance: Provenance
    metadata: Dict[str, Any]

@dataclass
class Provenance:
    source_file: str
    page_number: int | None
    paragraph_index: int
    char_start: int
    char_end: int
    extraction_timestamp: datetime
```

**Key Features**:
- Page-level extraction (for PDFs)
- Paragraph segmentation
- Preserve structure (headings, lists)
- Handle multi-column layouts
- OCR fallback for scanned PDFs (optional)

---

### B. LLM Extractor (`llm_extractor.py`)

**Purpose**: Use LLM to extract entities and relationships according to KG schema.

**LLM Provider**: OpenRouter (supports multiple models)
**Recommended Model**: `anthropic/claude-3.5-sonnet` or `openai/gpt-4-turbo`

**Prompt Engineering**:
```python
EXTRACTION_PROMPT = """
You are a legal knowledge extraction system. Extract structured entities and relationships from the following legal text.

ENTITY TYPES (extract ALL applicable):
1. Norma - Legal norms (laws, articles, decrees)
2. Concetto Giuridico - Legal concepts (e.g., "buona fede", "simulazione")
3. Soggetto Giuridico - Legal subjects (persons, entities)
4. Atto Giudiziario - Judicial acts (court decisions, orders)
5. Dottrina - Legal doctrine/commentary
6. Procedura - Legal procedures
7. Comma/Lettera/Numero - Clause-level elements
8. Versione - Versions of norms
9. Direttiva UE / Regolamento UE - EU acts
10. Organo Giurisdizionale - Courts, tribunals
... (full list of 23 types)

RELATIONSHIP TYPES (extract ALL applicable):
- MODIFICA (modifies)
- ABROGA (repeals)
- INTEGRA (supplements)
- APPLICA (applies)
- INTERPRETA (interprets)
... (full list from KG schema)

TEXT:
{segment_text}

Return JSON:
{{
  "entities": [
    {{
      "type": "Norma",
      "label": "Art. 1321 c.c.",
      "properties": {{
        "estremi": "Art. 1321 c.c.",
        "titolo": "Nozione di contratto",
        "descrizione": "...",
        ...
      }},
      "confidence": 0.95
    }}
  ],
  "relationships": [
    {{
      "source_label": "Art. 1321 c.c.",
      "target_label": "Contratto",
      "type": "TRATTA",
      "properties": {{}},
      "confidence": 0.90
    }}
  ]
}}
"""
```

**Features**:
- Batch processing (process multiple segments in parallel)
- Confidence scoring (LLM provides confidence for each extraction)
- Error handling and retry logic
- Cost tracking (OpenRouter API calls)
- Caching (avoid re-processing same text)

---

### C. Validation & Enrichment (`validator.py`)

**Purpose**: Validate and enrich extracted entities before writing to Neo4j.

**Validation Steps**:
1. **Schema Compliance**: Check all properties match KG schema
2. **Completeness**: Required fields present
3. **Consistency**: No contradictions (e.g., two different dates for same event)
4. **Reference Resolution**: Link entities to existing nodes in Neo4j

**Enrichment Steps**:
1. **Cross-References**: Find references to other parts of the document
2. **External Linking**: Match to official sources (Normattiva URNs)
3. **Hierarchy Building**: Construct parent-child relationships (Norm → Article → Comma)
4. **Temporal Ordering**: Order by publication/enforcement dates

---

### D. Neo4j Writer (`neo4j_writer.py`)

**Purpose**: Write extracted knowledge to Neo4j with proper schema.

**Key Operations**:
1. **Node Creation**: Create nodes with all properties from KG schema
2. **Relationship Creation**: Create typed relationships with MERGE (avoid duplicates)
3. **Provenance Linking**: Add provenance metadata to every node/edge
4. **Batch Writing**: Use Neo4j transactions for performance

**Example Cypher Generation**:
```cypher
// Create Norma node
MERGE (n:Norma {node_id: $node_id})
SET n.estremi = $estremi,
    n.titolo = $titolo,
    n.descrizione = $descrizione,
    n.testo_vigente = $testo_vigente,
    n.stato = $stato,
    n.data_pubblicazione = date($data_pubblicazione),
    n.provenance_file = $provenance_file,
    n.provenance_page = $provenance_page,
    n.provenance_paragraph = $provenance_paragraph,
    n.confidence = $confidence,
    n.created_at = datetime()
RETURN n.node_id
```

**Features**:
- Transaction management (commit/rollback)
- Duplicate detection (MERGE vs CREATE)
- Relationship validation (target node exists)
- Performance optimization (batch inserts)

---

### E. Pipeline Orchestrator (`ingestion_pipeline.py`)

**Purpose**: Coordinate the entire ingestion workflow.

**Workflow**:
```python
class DocumentIngestionPipeline:
    async def ingest_document(
        self,
        file_path: Path,
        auto_approve: bool = False,
        dry_run: bool = False
    ) -> IngestionResult:
        """
        Ingest a legal document into the knowledge graph.

        Steps:
        1. Read document → segments with provenance
        2. Extract entities/relationships via LLM
        3. Validate and enrich extractions
        4. Write to Neo4j (or stage for review)
        5. Return stats and report
        """

        # Step 1: Read
        segments = await self.reader.read_document(file_path)

        # Step 2: Extract (parallel processing)
        extraction_results = await self.extractor.extract_batch(segments)

        # Step 3: Validate & Enrich
        validated = await self.validator.validate_and_enrich(extraction_results)

        # Step 4: Write or Stage
        if auto_approve:
            result = await self.writer.write_to_neo4j(validated)
        else:
            result = await self.writer.stage_for_review(validated)

        # Step 5: Report
        return IngestionResult(
            file_path=file_path,
            segments_processed=len(segments),
            entities_extracted=result.entities_created,
            relationships_created=result.relationships_created,
            duration_seconds=...,
            cost_usd=...,
            errors=...
        )
```

**Features**:
- Progress tracking (real-time updates)
- Error recovery (skip failed segments, continue processing)
- Cost monitoring (LLM API costs)
- Dry-run mode (extract but don't write)
- Batch processing (multiple documents)

---

## 4. Configuration

### kg_config.yaml Extension

```yaml
document_ingestion:
  # LLM Configuration
  llm:
    provider: "openrouter"
    model: "anthropic/claude-3.5-sonnet"
    api_key: "${OPENROUTER_API_KEY}"
    temperature: 0.1  # Low for consistency
    max_tokens: 4000
    timeout_seconds: 60

  # Document Reader
  reader:
    supported_formats: ["pdf", "docx", "txt"]
    max_file_size_mb: 50
    ocr_enabled: false  # Enable for scanned PDFs
    paragraph_min_words: 10

  # Extraction
  extraction:
    batch_size: 10  # Process 10 segments per LLM call
    parallel_requests: 3  # Max concurrent LLM requests
    confidence_threshold: 0.7  # Min confidence to accept
    retry_attempts: 3
    cache_enabled: true
    cache_ttl_hours: 24

  # Validation
  validation:
    strict_mode: false  # If true, reject on any validation error
    enrich_with_external: true  # Try to match Normattiva URNs
    resolve_references: true  # Link to existing Neo4j nodes

  # Writing
  writing:
    batch_size: 100  # Nodes per transaction
    auto_approve: false  # Require manual review
    duplicate_strategy: "merge"  # or "skip", "error"
    provenance_required: true

  # Cost Control
  cost_control:
    max_cost_per_document_usd: 5.0
    alert_threshold_usd: 100.0  # Daily alert

  # Monitoring
  monitoring:
    log_level: "INFO"
    track_performance: true
    export_stats: true
```

---

## 5. Data Models

### Extraction Result
```python
@dataclass
class ExtractedEntity:
    type: str  # One of 23 KG node types
    label: str
    properties: Dict[str, Any]
    confidence: float
    provenance: Provenance

@dataclass
class ExtractedRelationship:
    source_label: str
    target_label: str
    type: str  # Relationship type from KG schema
    properties: Dict[str, Any]
    confidence: float
    provenance: Provenance

@dataclass
class ExtractionResult:
    segment: DocumentSegment
    entities: List[ExtractedEntity]
    relationships: List[ExtractedRelationship]
    llm_model: str
    cost_usd: float
    duration_seconds: float
    error: Optional[str]
```

### Ingestion Result
```python
@dataclass
class IngestionResult:
    file_path: Path
    segments_processed: int
    entities_extracted: int
    entities_written: int
    relationships_created: int
    duration_seconds: float
    cost_usd: float
    errors: List[str]
    warnings: List[str]
    dry_run: bool
```

---

## 6. CLI Tool

### Command-Line Interface

```bash
# Ingest single document
python -m backend.preprocessing.cli_ingest \
    --file "Manuale_Diritto_Civile.pdf" \
    --auto-approve \
    --dry-run

# Ingest directory
python -m backend.preprocessing.cli_ingest \
    --directory "data/manuals/" \
    --pattern "*.pdf" \
    --parallel 3

# With specific model
python -m backend.preprocessing.cli_ingest \
    --file "manual.pdf" \
    --model "openai/gpt-4-turbo" \
    --confidence-threshold 0.8

# Stage for review (no auto-approve)
python -m backend.preprocessing.cli_ingest \
    --file "manual.pdf" \
    --stage-only

# Re-process with different model
python -m backend.preprocessing.cli_ingest \
    --file "manual.pdf" \
    --force-reprocess \
    --model "anthropic/claude-3-opus"

# Export results to JSON
python -m backend.preprocessing.cli_ingest \
    --file "manual.pdf" \
    --export-json results.json
```

---

## 7. Testing Strategy

### Unit Tests
- Document reader (PDF/DOCX/TXT parsing)
- LLM extractor (prompt generation, response parsing)
- Validator (schema compliance, reference resolution)
- Neo4j writer (Cypher generation, transaction handling)

### Integration Tests
- End-to-end pipeline with sample documents
- Neo4j schema validation
- Provenance tracking verification
- Cost calculation accuracy

### Manual Testing
1. **Small Document** (~5 pages) - Verify all entities extracted correctly
2. **Medium Document** (~50 pages) - Test performance and cost
3. **Large Document** (~500 pages) - Stress test, batch processing
4. **Scanned PDF** - Test OCR fallback (if enabled)
5. **Multi-Format** - Test PDF, DOCX, TXT with same content

---

## 8. Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Document Size | Up to 500 pages | Per document |
| Processing Time | 1-2 min per page | With parallel LLM calls |
| LLM Cost | $0.05-0.15 per page | Claude 3.5 Sonnet pricing |
| Extraction Accuracy | >85% precision | For high-confidence entities |
| Neo4j Write Speed | 1000+ nodes/sec | With batching |
| Memory Usage | <2GB RAM | Per document |

---

## 9. Cost Analysis

### Example: 100-page Manual

**LLM Costs** (Claude 3.5 Sonnet):
- Input: ~500 tokens per page × 100 pages = 50K tokens
- Output: ~1000 tokens per page × 100 pages = 100K tokens
- Cost: $0.15 (input) + $0.75 (output) = **$0.90 per manual**

**Infrastructure Costs**:
- Neo4j: $0 (self-hosted)
- Redis: $0 (self-hosted)
- Storage: Negligible

**Total**: ~$1 per 100-page manual

**For 1,000 manuals**: ~$1,000 (one-time cost)

---

## 10. Implementation Plan

### Week 5 Day 3-5 (3 days)

**Day 3: Core Components**
- ✅ Document Reader (PDF/DOCX/TXT) - 4 hours
- ✅ Provenance Models - 1 hour
- ✅ Configuration in kg_config.yaml - 1 hour

**Day 4: LLM & Neo4j**
- ✅ LLM Extractor with OpenRouter - 4 hours
- ✅ Neo4j Writer with KG schema - 3 hours
- ✅ Validator - 1 hour

**Day 5: Pipeline & Testing**
- ✅ Pipeline Orchestrator - 2 hours
- ✅ CLI Tool - 2 hours
- ✅ Integration Tests - 2 hours
- ✅ Manual Testing with Sample PDF - 2 hours

**Total Estimated**: ~24 hours (3 days)

---

## 11. Future Enhancements (Post-Week 5)

### Phase 3+ Features
1. **Active Learning**: Feed uncertain extractions to RLCF for expert validation
2. **Incremental Updates**: Re-process only changed pages
3. **Multi-Language**: Support for English, French legal texts
4. **Table Extraction**: Parse legal tables and schedules
5. **Citation Linking**: Auto-link article references across documents
6. **Image Analysis**: Extract diagrams, flowcharts via vision models
7. **Audio Transcription**: Process legal lectures/seminars
8. **Collaborative Annotation**: Web UI for manual corrections
9. **Quality Metrics**: Track extraction quality over time
10. **Model Fine-Tuning**: Fine-tune LLM on legal domain

---

## 12. Open Questions

1. **OCR Library**: Use Tesseract or commercial API (e.g., AWS Textract)?
2. **Vector Embeddings**: Should we also create embeddings for semantic search?
3. **Chunking Strategy**: Fixed-size chunks vs. semantic chunks (paragraphs)?
4. **Multi-Pass Extraction**: Extract entities first, then relationships?
5. **Human-in-the-Loop**: When to require expert validation?

---

## 13. References

- **Knowledge Graph Schema**: `docs/02-methodology/knowledge-graph.md`
- **RLCF Framework**: `docs/02-methodology/rlcf/RLCF.md`
- **Phase 2 Architecture**: `docs/03-architecture/02-orchestration-layer.md`
- **NormGraph Inspiration**: `NormGraph/NormGraph/README_GRAPH_SYSTEM.md`

---

**Status**: 🚧 Design Complete → Ready for Implementation
**Next**: Create `backend/preprocessing/document_ingestion/` package
