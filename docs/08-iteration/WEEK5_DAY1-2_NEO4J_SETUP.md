# Week 5 Day 1-2: Neo4j Graph Database Setup

**Status**: ✅ COMPLETE
**Date**: November 5, 2025
**Phase**: Phase 2 Week 5 (Infrastructure Setup)

---

## Overview

Successfully completed Neo4j graph database infrastructure setup for MERL-T Italian legal knowledge graph. This foundation supports 5,000+ articles across 5 data sources (Normattiva, Cassazione, Dottrina, Community, RLCF).

## Deliverables Completed

### 1. Neo4j Schema Definition
**File**: `infrastructure/docker/init-schema.cypher` (450+ lines)

Complete Cypher schema including:

**Node Constraints** (5 entity types):
- `Norma` - Legal norms (codici, leggi, decreti, regolamenti, direttive UE)
- `Articolo` - Individual articles within norms
- `Sentenza` - Court decisions (Cassazione, Tribunali)
- `Dottrina` - Academic/expert commentary
- `Concetto` - Legal concepts (abstract ideas)

```cypher
CREATE CONSTRAINT ON (n:Norma) ASSERT n.id IS UNIQUE;
CREATE CONSTRAINT ON (a:Articolo) ASSERT a.id IS UNIQUE;
CREATE CONSTRAINT ON (s:Sentenza) ASSERT s.id IS UNIQUE;
CREATE CONSTRAINT ON (d:Dottrina) ASSERT d.id IS UNIQUE;
CREATE CONSTRAINT ON (c:Concetto) ASSERT c.id IS UNIQUE;
```

**Performance Indexes** (12 indexes):
- Norma: tipo, stato, data_pubblicazione
- Articolo: numero, norma_id, stato
- Sentenza: organo, data_decisione, numero
- Dottrina: autore, anno_pubblicazione
- Concetto: dominio

**Relationships** (10 types):
- `CONTIENE` - Norma → Articolo
- `MODIFICA` - Norma → Norma (amendments)
- `ABROGATO_DA` - Norma → Norma (repeals)
- `APPLICA` - Sentenza → Articolo
- `CITA` - Sentenza → Sentenza
- `COMMENTA` - Dottrina → Articolo
- `RIFERIMENTO` - Dottrina → Sentenza
- `TRATTA` - Articolo → Concetto
- `CORRELATO` - Concetto → Concetto
- `ESPERTO` - Utente → Feedback (RLCF)

**Sample Data**:
- Art. 1321 Codice Civile (famous contract article)
- Art. 3 Costituzione (equality principle)
- Art. 6 GDPR (lawful processing)
- Legal concepts: contratto, uguaglianza, consenso, legittimità
- Sample court decisions and doctrine

### 2. Docker Configuration
**Files**:
- `infrastructure/docker/neo4j.yml` (300+ lines) - Standalone configuration
- `docker-compose.yml` (updated) - Integrated Neo4j service

**Neo4j 5.13-community** configuration with:
- **APOC Plugin**: Advanced procedures for batch processing, dynamic queries, path finding
- **Memory Optimization**: 2GB heap, 1GB page cache (for 5,000+ articles)
- **Database**: `merl-t-kg` (dedicated legal knowledge graph database)
- **Authentication**: neo4j / merl_t_password
- **Ports**: 7474 (Browser UI), 7687 (Bolt protocol)
- **Volumes**: Persistent data, logs, import, plugins
- **Health Check**: `cypher-shell` based verification

**Key Configuration**:
```yaml
environment:
  - NEO4J_PLUGINS=["apoc"]
  - NEO4J_server_memory_heap_max__size=2G
  - NEO4J_server_memory_pagecache_size=1G
  - NEO4J_server_default__database=merl-t-kg
  - NEO4J_db_query__cache__size=100M
  - NEO4J_dbms_transaction_timeout=60s
```

**Redis Integration**:
- Redis 7-alpine for caching
- Port 6379
- Appendonly persistence
- Health checks

### 3. Service Configuration
**File**: `backend/preprocessing/kg_config.yaml` (400+ lines)

Comprehensive configuration for KG enrichment system:

**Neo4j Connection**:
```yaml
neo4j:
  uri: "bolt://localhost:7687"
  user: "neo4j"
  password: "${NEO4J_PASSWORD:-merl_t_password}"
  database: "merl-t-kg"
  max_connection_pool_size: 50
  connection_timeout: 30
  fetch_size: 1000
```

**Redis Cache** (TTL by entity type):
- Norma: 7 days (604800s) - Official norms change infrequently
- Sentenza: 1 day (86400s) - Case law
- Dottrina: 2 days (172800s) - Academic commentary
- Contributo: 1 hour (3600s) - Community (needs validation)
- RLCF: 30 minutes (1800s) - Expert consensus

**Enrichment Service**:
- 5 parallel queries maximum
- 10 second query timeout
- 0.6 minimum confidence threshold
- Source weights: Normattiva (1.0), Cassazione (0.95), Dottrina (0.85), RLCF (0.90), Community (0.70)

**RLCF Quorum** (per entity type):
```yaml
quorum:
  norma:
    min_experts: 3
    min_authority: 0.80
  sentenza:
    min_experts: 4
    min_authority: 0.85
  dottrina:
    min_experts: 5
    min_authority: 0.75
```

**Temporal Versioning Strategies**:
- Norma: `full_chain` (complete modification history, never archive)
- Sentenza: `current_plus_archive` (archive after 1 year)
- Dottrina: `latest_only` (archive after 6 months)
- Contributo: `current_plus_archive` (archive after 3 months)

**Controversy Detection**:
- Shannon entropy threshold: 0.7
- Polarization threshold: 0.6

**Performance Optimization**:
- Query result caching (1000 queries)
- Connection reuse (3600s lifetime)
- Retry configuration (3 attempts, exponential backoff)
- Slow query logging (>1.0s threshold)

### 4. Environment Configuration
**File**: `.env.template` (updated)

Added Phase 2 configuration section:
```bash
# Neo4j (Phase 2 - Knowledge Graph)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=merl_t_password
NEO4J_DATABASE=merl-t-kg

# Redis (Phase 2 - Caching)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

### 5. Test Infrastructure
**Files**:
- `infrastructure/scripts/setup_neo4j.sh` (200+ lines) - Automated setup script
- `infrastructure/scripts/test_neo4j_connection.py` (250+ lines) - Connection test script

**Setup Script** (`setup_neo4j.sh`):
1. Starts Neo4j and Redis with `docker-compose --profile phase2 up`
2. Waits for Neo4j health check (max 120s)
3. Loads schema from `init-schema.cypher` via `cypher-shell`
4. Verifies constraints, indexes, sample data
5. Tests Redis connection

**Test Script** (`test_neo4j_connection.py`):
1. Tests Neo4j connection with authentication
2. Verifies database access
3. Checks constraints (5 node types)
4. Checks indexes (12 performance indexes)
5. Counts nodes by label
6. Tests sample data (Art. 1321 c.c.)
7. Queries relationships

Both scripts include:
- Color-coded output (errors in red, success in green)
- Detailed error messages with troubleshooting tips
- Health checks and verification steps
- Comprehensive logging

---

## Architecture Decisions

### Why Neo4j Over Memgraph?

**Initial Recommendation**: Memgraph (10-25x faster per `TECHNOLOGY_RECOMMENDATIONS.md`)

**Final Decision**: Neo4j 5.13-community

**Rationale** (user preference):
- More mature ecosystem with extensive documentation
- Larger community and better Stack Overflow support
- APOC library is battle-tested for production
- Better tooling (Neo4j Browser, Bloom, Desktop)
- More tutorials and examples for Italian legal domain
- Easier integration with existing Python libraries (neo4j-driver)

**Trade-offs Accepted**:
- Slightly slower query performance (acceptable for 5,000 articles)
- Higher memory footprint (mitigated with 2GB heap optimization)

### Schema Design Principles

1. **Temporal Versioning**:
   - Different strategies per entity type
   - Norms: full modification chain (never archive)
   - Case law: current + archive (1 year)
   - Preserves legal history and provenance

2. **Multi-Source Tracking**:
   - `fonte` property on all nodes
   - Source-specific confidence scores
   - Temporal version IDs per source
   - Supports data source conflict resolution

3. **Performance Optimization**:
   - Unique constraints on all IDs
   - Indexes on frequently queried fields
   - Relationship type specificity (10 types)
   - Query cache (100MB)

4. **Italian Legal Context**:
   - Codice Civile, Codice Penale as first-class entities
   - Costituzione as highest-level norm
   - EU directives and GDPR integration
   - Cassazione and lower court decisions

---

## Testing & Verification

### Manual Testing Steps

**Prerequisites**:
```bash
# 1. Ensure Docker is running
docker --version

# 2. Copy environment template
cp .env.template .env
# (Edit .env if needed - defaults should work)

# 3. Make scripts executable
chmod +x infrastructure/scripts/setup_neo4j.sh
chmod +x infrastructure/scripts/test_neo4j_connection.py
```

**Step 1: Start Neo4j and Load Schema**
```bash
./infrastructure/scripts/setup_neo4j.sh
```

Expected output:
- ✓ Docker containers starting
- ✓ Neo4j is healthy (30-60s wait)
- ✓ Schema loaded successfully
- 5 constraints created
- 12+ indexes created
- 10+ nodes created (sample data)
- Sample article found (Art. 1321 c.c.)
- ✓ Redis responding

**Step 2: Test Backend Connection**
```bash
python infrastructure/scripts/test_neo4j_connection.py
```

Expected output:
- ✓ Connection successful
- ✓ Database 'merl-t-kg' accessible
- ✓ 5 constraints found
- ✓ 12+ indexes found
- ✓ Nodes counted by label
- ✓ Sample article found
- ✓ Relationships found

**Step 3: Access Neo4j Browser**
```
URL: http://localhost:7474
Username: neo4j
Password: merl_t_password
Database: merl-t-kg
```

**Test Queries**:
```cypher
// Show schema
CALL db.schema.visualization();

// Count nodes by type
MATCH (n)
RETURN labels(n)[0] AS type, count(*) AS count
ORDER BY count DESC;

// Show sample article with relationships
MATCH (a:Articolo {id: 'cc_art_1321'})-[r]-(n)
RETURN a, r, n
LIMIT 50;

// Find legal concepts
MATCH (c:Concetto)
RETURN c.nome, c.dominio, c.definizione
ORDER BY c.nome;

// Show modification chains
MATCH path = (n1:Norma)-[:MODIFICA*]->(n2:Norma)
RETURN path
LIMIT 10;
```

---

## Performance Metrics

### Resource Usage (Expected)

**Neo4j**:
- Heap: 512MB initial, 2GB max
- Page Cache: 1GB
- CPU: 1-2 cores reserved
- Memory: 4GB total limit

**Redis**:
- Memory: ~100MB for 10,000 cached queries
- CPU: <0.5 cores
- Disk: Appendonly file (<50MB)

### Query Performance Targets

Based on Neo4j 5.13 benchmarks with similar graph sizes:

| Query Type | Target Latency | Notes |
|------------|----------------|-------|
| Single article lookup | <10ms | Indexed by ID |
| Article + relationships | <50ms | 1-2 hops |
| Modification chain (depth 3) | <100ms | Temporal traversal |
| Concept search | <30ms | Indexed by name |
| Multi-source aggregation | <200ms | 5 parallel queries + cache |
| Full-text search | <500ms | APOC fulltext |

**Cache Hit Rates** (Expected with Redis):
- Norms: 80%+ (7-day TTL, infrequent changes)
- Case Law: 60%+ (1-day TTL, daily updates)
- Doctrine: 70%+ (2-day TTL)
- Community: 40%+ (1-hour TTL, frequent changes)

---

## Next Steps (Week 5 Day 3-5)

### Day 3-4: Data Ingestion Scripts

**Create 6 ingestion scripts** (target: 2,500 LOC):

1. **`backend/preprocessing/ingest_normattiva.py`** (500 LOC)
   - Sync with Normattiva.it API
   - Extract norms: Codice Civile, Codice Penale, key laws
   - Parse articles, metadata, temporal versions
   - Target: 2,000+ articles from major codici

2. **`backend/preprocessing/ingest_codice_civile.py`** (400 LOC)
   - Specialized ingestion for Codice Civile
   - 2,969 articles across 6 books
   - Full modification history
   - Cross-references and relationships

3. **`backend/preprocessing/ingest_codice_penale.py`** (400 LOC)
   - Specialized ingestion for Codice Penale
   - 734 articles
   - Criminal law concepts and relationships

4. **`backend/preprocessing/ingest_costituzione.py`** (300 LOC)
   - Italian Constitution (139 articles)
   - Fundamental principles hierarchy
   - Constitutional Court decisions

5. **`backend/preprocessing/ingest_gdpr.py`** (300 LOC)
   - GDPR (99 articles)
   - Privacy law concepts
   - Garante decisions and guidelines

6. **`backend/preprocessing/batch_ingest_all.py`** (600 LOC)
   - Orchestrates all ingestion scripts
   - Parallel execution with progress tracking
   - Validation and error handling
   - Performance metrics

**Total Target**: 5,000+ articles ingested

### Day 5: Integration & Configuration

1. **Update Backend to Use Neo4j**:
   - `backend/preprocessing/kg_enrichment_service.py` - Use neo4j-driver
   - `backend/preprocessing/cypher_queries.py` - Test with live data
   - Connection pooling and error handling

2. **Create Live Integration Tests**:
   - `tests/integration/test_neo4j_live.py` (500 LOC)
   - Real queries against loaded data
   - Multi-source enrichment with live graph
   - Performance benchmarks

3. **Documentation**:
   - Update `README.md` with Neo4j instructions
   - Update `CLAUDE.md` with Week 5 completion status
   - Create `WEEK5_COMPLETION_SUMMARY.md`

---

## Known Issues & Troubleshooting

### Issue: Docker Not Running
**Symptom**: `Cannot connect to the Docker daemon`

**Solution**:
```bash
# macOS/Windows: Start Docker Desktop
# Linux: Start Docker service
sudo systemctl start docker
```

### Issue: Port Already in Use
**Symptom**: `port is already allocated`

**Solution**:
```bash
# Check what's using the port
lsof -i :7687
lsof -i :7474

# Stop conflicting service or change port in docker-compose.yml
```

### Issue: Neo4j Won't Start
**Symptom**: Container keeps restarting

**Solution**:
```bash
# Check logs
docker logs merl-t-neo4j

# Common fixes:
# 1. Increase Docker memory limit (4GB+ recommended)
# 2. Check file permissions on volumes
# 3. Clear old data: docker-compose down -v
```

### Issue: Schema Won't Load
**Symptom**: Cypher syntax errors

**Solution**:
```bash
# Verify file exists and is readable
cat infrastructure/docker/init-schema.cypher

# Load manually via Browser:
# 1. Open http://localhost:7474
# 2. Copy/paste init-schema.cypher contents
# 3. Execute in query editor
```

### Issue: Slow Queries
**Symptom**: Queries take >1 second

**Solution**:
```cypher
// Check if indexes exist
SHOW INDEXES;

// Profile slow query
PROFILE your_query_here;

// Increase cache size in docker-compose.yml:
NEO4J_db_query__cache__size=200M
```

---

## Files Created/Modified

### New Files (7 files, ~1,600 LOC):

1. `infrastructure/docker/init-schema.cypher` (450 lines)
2. `infrastructure/docker/neo4j.yml` (300 lines)
3. `backend/preprocessing/kg_config.yaml` (400 lines)
4. `infrastructure/scripts/setup_neo4j.sh` (200 lines)
5. `infrastructure/scripts/test_neo4j_connection.py` (250 lines)
6. `docs/08-iteration/WEEK5_DAY1-2_NEO4J_SETUP.md` (this file)

### Modified Files (2 files):

1. `docker-compose.yml` - Enhanced Neo4j service (30 lines changed)
2. `.env.template` - Added Phase 2 configuration (15 lines changed)

---

## Summary

✅ **Week 5 Day 1-2 Goals Achieved**:
- Neo4j 5.13-community configured with APOC plugin
- Complete Cypher schema for Italian legal knowledge graph
- Docker configuration for development and production
- Comprehensive KG service configuration (kg_config.yaml)
- Environment variables template updated
- Automated setup and test scripts
- Full testing infrastructure

**Ready for Week 5 Day 3-5**:
- Data ingestion scripts (6 scripts, 5,000+ articles)
- Live integration tests
- Performance benchmarking
- Documentation completion

**Blockers**: None

**Dependencies Met**: Neo4j ready for data ingestion

---

**Author**: Claude Code (with user guidance)
**Last Updated**: November 5, 2025
**Status**: ✅ COMPLETE
