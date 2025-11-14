# Changelog

All notable changes to the MERL-T project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### In Progress
- Phase 3: Vector Database Integration (Qdrant)
- Phase 3: LangGraph Workflow Orchestration
- Advanced RLCF Feedback Loops
- Production deployment configurations

---

## [0.9.0] - 2025-11-14 (Week 9 Complete)

### Added - OpenAPI/Swagger Documentation
- Custom OpenAPI 3.1.0 schema generation with API key authentication
- Rate limiting headers documentation (X-RateLimit-*)
- 24 comprehensive request/response examples across all endpoints
- Postman Collection v2.1 with environment variables
- Complete user documentation:
  - AUTHENTICATION.md (401 lines) - API key authentication guide
  - RATE_LIMITING.md (506 lines) - Rate limiting and best practices
  - API_EXAMPLES.md (734 lines) - Real-world Italian legal scenarios
- Automatic Postman collection generation script
- Enhanced Swagger UI configuration (persistent auth, request duration, filtering)

### Changed
- OpenAPI schema now includes security requirements for all endpoints
- All API responses include rate limiting headers
- Feedback and stats routers enhanced with error response examples

### Documentation
- Week 9 complete summary (WEEK9_COMPLETE_SUMMARY.md)
- Postman collection README with usage instructions

---

## [0.7.0] - 2025-11-12 (Week 7 Complete)

### Added - Preprocessing Integration
- Unified preprocessing pipeline in orchestration workflow
- PostgreSQL database for orchestration persistence
- Graceful degradation patterns for service failures
- Comprehensive preprocessing integration tests (33 tests, 1,650 LOC)

### Changed
- LangGraph workflow now includes preprocessing node
- Query understanding integrated before routing
- KG enrichment integrated in preprocessing phase

### Fixed
- Preprocessing service initialization in main workflow
- Database connection handling in orchestration API

---

## [0.6.0] - 2025-11-08 (Week 6 Complete)

### Added - Complete Orchestration Layer
- **LLM Router**: 100% LLM-based decision engine (no hardcoded rules)
- **Retrieval Agents**:
  - KG Agent: Neo4j knowledge graph queries
  - API Agent: Integration with Norma Controller (visualex)
  - VectorDB Agent: Qdrant semantic search with E5-large embeddings
- **4 Reasoning Experts**:
  - Literal Interpreter: Strict textual interpretation
  - Systemic-Teleological: Purpose-driven analysis
  - Principles Balancer: Constitutional principles weighing
  - Precedent Analyst: Case law analysis
- **Synthesizer**: Multi-opinion synthesis with uncertainty preservation
- **Iteration Controller**: Multi-turn refinement with 6 stopping criteria
- **Complete REST API**: 13 endpoints across 4 routers
  - Query execution (4 endpoints)
  - Feedback submission (3 endpoints)
  - Statistics & analytics (2 endpoints)
  - Health checks (2 endpoints)
- **LangGraph Workflow**: Complete 6-node graph with routing and loops
- **E5-large Embeddings**: Multilingual semantic search (1024 dimensions)
- **Qdrant Integration**: Vector database with filtered search
- **Data Ingestion**: Legal corpus ingestion script (419 lines)

### Changed
- Migrated from simple pipeline to LangGraph state machine
- Router now uses Claude 3.5 Sonnet for decision-making
- Experts receive full context (query, retrieval results, previous iterations)

### Documentation
- Week 6 complete API documentation (WEEK6_DAY5_API_COMPLETE.md)
- Orchestration configuration guide (orchestration_config.yaml)
- Comprehensive test summaries for all Day 1-5 deliverables

### Tests
- LLM Router tests (19 test cases)
- Embedding service tests (20+ test cases)
- VectorDB agent integration tests (25+ test cases)
- Expert system tests
- Iteration controller tests (25+ test cases)
- Complete API test suite (40+ test cases, 788 LOC)

---

## [0.2.0] - 2025-11-05 (Phase 2 Week 3 Complete)

### Added - Knowledge Graph & Pipeline Integration
- **Multi-Source KG Enrichment** (3,500+ LOC):
  - 5 data sources: Normattiva (official), Cassazione (jurisprudence), Dottrina (academic), Community, RLCF
  - Dual-provenance tracking (PostgreSQL + Neo4j)
  - Temporal versioning per source type
  - Controversy detection (RLCF vs official source conflicts)
  - Redis caching for performance

- **Full Pipeline Integration** (2,920+ LOC):
  - 7-stage pipeline: Intent Classification → KG Enrichment → RLCF Processing → Feedback
  - PipelineContext for state management
  - Comprehensive execution logging and timing
  - Error handling and recovery mechanisms

- **NER Feedback Loop** (500 lines):
  - 4 correction types: MISSING_ENTITY, SPURIOUS_ENTITY, WRONG_BOUNDARY, WRONG_TYPE
  - Automatic training example generation
  - Performance tracking (F1, precision, recall)
  - Batch retraining coordination

- **RLCF Aggregation** (520 lines):
  - Expert vote aggregation with authority weighting
  - Shannon entropy-based uncertainty preservation
  - Dynamic quorum by entity type (Norma: 3 experts, Sentenza: 4, Dottrina: 5)
  - Controversy flagging for polarized disagreement

- **FastAPI Integration**:
  - 5 new endpoints: /pipeline/query, /feedback/submit, /ner/correct, /stats, /health
  - Service initialization and lifecycle management
  - Dependency injection for all components

### Tests
- KG enrichment tests (100+ test cases, 2,156 LOC)
- Full pipeline integration tests (50+ test cases, 850 LOC)
- RLCF quorum detection tests
- Controversy flagging tests
- Normattiva sync tests

### Documentation
- Phase 2 Week 3 complete summary
- KG enrichment test summary (KG_TEST_SUMMARY.md)
- Full pipeline integration summary

---

## [0.1.0] - 2025-10-20 (Phase 1 Complete)

### Added - RLCF Core Framework
- **FastAPI Backend** (1,734 LOC):
  - 50+ REST API endpoints
  - SQLAlchemy 2.0 async models
  - Pydantic 2.5 validation schemas
  - Authority scoring algorithm (`A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)`)
  - Uncertainty-preserving aggregation (Shannon entropy)
  - Bias detection algorithms
  - OpenRouter LLM integration

- **CLI Tools** (507 lines):
  - `rlcf-cli`: User commands (task management, query history)
  - `rlcf-admin`: Admin commands (config, database, server)

- **React 19 Frontend**:
  - TypeScript + Vite + TailwindCSS
  - TanStack Query for data fetching
  - Zustand for state management
  - Modular component architecture

- **Docker Configuration**:
  - Development environment (SQLite + hot-reload)
  - Production environment (PostgreSQL + multi-worker)
  - Docker Compose profiles for different scenarios

- **Configuration Management**:
  - YAML-based config files (hot-reloadable)
  - Environment variable support
  - Gradio admin interface
  - API-based config updates

### Tests
- Comprehensive test suite (2,278 LOC)
- 85%+ coverage on core RLCF algorithms
- Async DB fixtures
- Integration test report (INTEGRATION_TEST_REPORT.md)

### Documentation
- Executive summary and vision documents
- RLCF theoretical paper (RLCF.md)
- Architecture specifications (5-layer system)
- Implementation blueprints
- API reference
- Quick start guide
- Manual testing guide

---

## [0.0.1] - 2025-10-01 (Initial Planning)

### Added
- Project structure and repository setup
- Documentation framework (101 files, 69,000+ LOC)
- Technology recommendations (TECHNOLOGY_RECOMMENDATIONS.md)
- Implementation roadmap (42-week plan)
- AI Act compliance documentation
- ALIS association governance framework

### Documentation
- 6 main documentation sections:
  - 01-introduction: Executive summary, vision, problem statement
  - 02-methodology: RLCF, knowledge graphs, legal reasoning
  - 03-architecture: 5-layer system design
  - 04-implementation: API gateway, deployment, RLCF pipeline
  - 05-governance: AI Act compliance, data protection
  - 06-resources: Bibliography, datasets, API reference

---

## Release Notes

### Version Scheme

- **Major version** (x.0.0): Breaking changes, major feature releases
- **Minor version** (0.x.0): New features, backward-compatible
- **Patch version** (0.0.x): Bug fixes, minor improvements

### Supported Versions

- **0.9.x**: ✅ Currently supported (Week 9)
- **0.6.x**: ✅ Supported (Week 6)
- **0.2.x**: ✅ Supported (Phase 2)
- **0.1.x**: ⚠️ Security updates only

---

## Contributors

Thank you to all contributors who have helped make MERL-T possible!

- ALIS Team (Artificial Legal Intelligence Society)
- Open Source Community Contributors

---

## Links

- **GitHub**: https://github.com/ALIS-ai/MERL-T
- **Documentation**: https://github.com/ALIS-ai/MERL-T/tree/main/docs
- **Issues**: https://github.com/ALIS-ai/MERL-T/issues
- **Discussions**: https://github.com/ALIS-ai/MERL-T/discussions

---

[Unreleased]: https://github.com/ALIS-ai/MERL-T/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/ALIS-ai/MERL-T/compare/v0.7.0...v0.9.0
[0.7.0]: https://github.com/ALIS-ai/MERL-T/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/ALIS-ai/MERL-T/compare/v0.2.0...v0.6.0
[0.2.0]: https://github.com/ALIS-ai/MERL-T/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ALIS-ai/MERL-T/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/ALIS-ai/MERL-T/releases/tag/v0.0.1
