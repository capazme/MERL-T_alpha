# Next Steps - Development Roadmap

**Last Updated**: November 2025
**Current Version**: v0.9.0 (75% complete)
**Status**: Production components ready, integration and persistence work needed

---

## Table of Contents

1. [Current Project Status](#current-project-status)
2. [Immediate Next Steps](#immediate-next-steps-priority-1-3)
3. [Short-Term Development](#short-term-development-1-2-months)
4. [Medium-Term Development](#medium-term-development-3-6-months)
5. [Long-Term Vision](#long-term-vision-6-12-months)
6. [Technical Debt & Improvements](#technical-debt--improvements)
7. [Success Metrics](#success-metrics)
8. [Related Documentation](#related-documentation)

---

## Current Project Status

**Overall Progress**: 75% of core system implementation complete

### Completed Components ✅

| Layer | Status | Key Features |
|-------|--------|--------------|
| **Preprocessing** | ✅ Complete (100%) | Entity extraction, KG enrichment (5 sources), NER feedback loop, LangGraph integration |
| **Orchestration** | ✅ Functionally Complete (95%) | LLM Router, 3 retrieval agents (KG, API, VectorDB), LangGraph workflow, 11 REST endpoints |
| **Reasoning** | ✅ Complete (100%) | 4 expert types, synthesizer (convergent/divergent), iteration controller (6 stopping criteria) |
| **Storage** | 🚧 Partial (70%) | PostgreSQL (RLCF), Qdrant (vectors), Redis (rate limiting), Neo4j (schema ready, not deployed) |
| **Learning (RLCF)** | 🚧 Partial (40%) | Authority scoring, feedback aggregation, bias detection, hot-reload config |

**Code Metrics**:
- **Backend**: 41,888 LOC (117 modules)
- **Frontend**: ~3,000 LOC (React 19)
- **Tests**: 19,541 LOC (200+ test cases, 88-90% coverage)
- **Documentation**: 101 files, 69,323 LOC

**Total**: ~52,860 LOC

### Partially Implemented 🚧

**Database Persistence for Orchestration**:
- ❌ Query storage (PostgreSQL) - currently in-memory
- ❌ Result caching (Redis) - only rate limiting implemented
- ✅ RLCF database (PostgreSQL) - complete
- ✅ Vector storage (Qdrant) - complete
- ⏳ Graph database (Neo4j) - schema ready, not deployed in production

**Query Understanding**:
- ❌ LLM integration - mock values present in `query_executor.py:72-96`
- ✅ NER service - implemented but not integrated into workflow
- ✅ Intent classification - implemented but not integrated
- ✅ KG enrichment - complete and integrated

**Authentication & Security**:
- ❌ API key authentication for orchestration endpoints
- ❌ Rate limiting for orchestration (only RLCF endpoints have it)
- ❌ Usage tracking and quotas
- ✅ CORS configuration - complete

### Not Implemented ❌

**Admin Interface**:
- Orchestration query monitoring dashboard
- Expert opinion review interface
- System performance metrics visualization
- Configuration management UI for orchestration

**Production Deployment**:
- Kubernetes manifests
- CI/CD pipeline (GitHub Actions)
- Observability stack (OpenTelemetry + SigNoz)
- Production monitoring and alerting
- Load balancing and auto-scaling

**Advanced Features**:
- Automated training data generation
- Model fine-tuning pipeline
- A/B testing framework
- Multi-language support (only Italian currently)

---

## Immediate Next Steps (Priority 1-3)

### Priority 1: Database Persistence (CRITICAL) 🔴

**Status**: Not started
**Effort**: 14-16 hours (2 days)
**Blocking**: Production deployment

**Problem**: Orchestration API stores queries/results in-memory, lost on restart

**Solution**: Implement PostgreSQL + Redis persistence layer

**Tasks**:

1. **Database Schema Design** (4 hours)
   ```sql
   -- File: migrations/001_create_orchestration_tables.sql

   CREATE TABLE queries (
       trace_id UUID PRIMARY KEY,
       session_id UUID,
       user_id INTEGER,
       query_text TEXT NOT NULL,
       status VARCHAR(50) NOT NULL, -- pending, processing, completed, failed
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW()
   );

   CREATE TABLE query_results (
       id SERIAL PRIMARY KEY,
       trace_id UUID REFERENCES queries(trace_id),
       answer TEXT,
       execution_trace JSONB,
       metadata JSONB,
       created_at TIMESTAMP DEFAULT NOW()
   );

   CREATE TABLE user_feedback (
       id SERIAL PRIMARY KEY,
       trace_id UUID REFERENCES queries(trace_id),
       user_id INTEGER,
       rating INTEGER CHECK (rating BETWEEN 1 AND 5),
       feedback_text TEXT,
       created_at TIMESTAMP DEFAULT NOW()
   );

   CREATE TABLE rlcf_feedback (
       id SERIAL PRIMARY KEY,
       trace_id UUID REFERENCES queries(trace_id),
       expert_id INTEGER,
       feedback_type VARCHAR(50),
       feedback_data JSONB,
       created_at TIMESTAMP DEFAULT NOW()
   );

   CREATE TABLE ner_corrections (
       id SERIAL PRIMARY KEY,
       query_id INTEGER,
       correction_type VARCHAR(50),
       original_entity JSONB,
       corrected_entity JSONB,
       expert_id INTEGER,
       created_at TIMESTAMP DEFAULT NOW()
   );

   CREATE INDEX idx_queries_status ON queries(status);
   CREATE INDEX idx_queries_session ON queries(session_id);
   CREATE INDEX idx_queries_created ON queries(created_at DESC);
   ```

2. **Redis Caching Layer** (4 hours)
   ```python
   # File: backend/orchestration/api/services/cache_service.py

   from redis import asyncio as aioredis
   from typing import Optional, Any
   import json

   class CacheService:
       def __init__(self, redis_url: str):
           self.redis = aioredis.from_url(redis_url)

       async def get_query_status(self, trace_id: str) -> Optional[str]:
           # Cache query status (TTL: 24h)
           pass

       async def cache_query_result(self, trace_id: str, result: Any, ttl: int = 86400):
           # Cache complete query result
           pass

       async def get_user_session(self, session_id: str) -> Optional[dict]:
           # Cache user session (TTL: 7 days)
           pass
   ```

3. **Update API Services** (6 hours)
   ```python
   # Modify: backend/orchestration/api/services/query_executor.py

   from .persistence_service import PersistenceService
   from .cache_service import CacheService

   class QueryExecutor:
       def __init__(self, db: PersistenceService, cache: CacheService):
           self.db = db
           self.cache = cache

       async def execute_query(self, request: QueryRequest) -> QueryResponse:
           # 1. Check cache
           cached = await self.cache.get_query_result(trace_id)
           if cached:
               return cached

           # 2. Execute workflow
           result = await self.workflow.run(...)

           # 3. Save to database
           await self.db.save_query(trace_id, result)

           # 4. Cache result
           await self.cache.cache_query_result(trace_id, result)

           return result
   ```

**Files to Create**:
- `migrations/001_create_orchestration_tables.sql` (100 LOC)
- `backend/orchestration/api/database.py` (150 LOC) - SQLAlchemy models
- `backend/orchestration/api/models.py` (200 LOC) - Database models
- `backend/orchestration/api/services/persistence_service.py` (300 LOC) - CRUD operations
- `backend/orchestration/api/services/cache_service.py` (200 LOC) - Redis caching
- `tests/orchestration/test_persistence.py` (400 LOC) - Persistence tests

**Expected Deliverables**:
- ✅ PostgreSQL schema migrated and indexed
- ✅ Redis caching functional with TTL management
- ✅ QueryExecutor persisting to database
- ✅ Feedback endpoints saving to RLCF tables
- ✅ All orchestration tests passing with persistence

---

### Priority 2: Query Understanding LLM Integration (CRITICAL) 🔴

**Status**: Partially implemented (mock values present)
**Effort**: 16-18 hours (2 days)
**Blocking**: Production accuracy

**Problem**: Query executor uses hardcoded mock values for intent and complexity

**Current Gap**:
```python
# backend/orchestration/api/services/query_executor.py:72-96
query_context = {
    "query": request.query,
    "intent": "unknown",  # ← TODO: Replace with real intent classification
    "complexity": 0.5,    # ← TODO: Replace with real complexity score
}
```

**Solution**: Integrate real preprocessing modules

**Tasks**:

1. **Import Preprocessing Modules** (2 hours)
   ```python
   # Modify: backend/orchestration/api/services/query_executor.py

   from backend.preprocessing.query_understanding import QueryUnderstandingModule
   from backend.preprocessing.kg_enrichment_service import KGEnrichmentService

   class QueryExecutor:
       def __init__(self):
           self.query_understanding = QueryUnderstandingModule()
           self.kg_enrichment = KGEnrichmentService()
   ```

2. **Update _build_initial_state()** (8 hours)
   ```python
   async def _build_initial_state(self, request: QueryRequest, trace_id: str) -> dict:
       # 1. Real query understanding
       understanding_result = await self.query_understanding.analyze_query(
           query_text=request.query,
           query_id=trace_id
       )

       # 2. KG enrichment with real data
       enriched_context = await self.kg_enrichment.enrich_context(
           query_understanding=understanding_result
       )

       # 3. Build state with real values
       return {
           "query": request.query,
           "trace_id": trace_id,
           "query_understanding": understanding_result,  # Real intent, entities, complexity
           "enriched_context": enriched_context,         # Real KG data
           "retrieval_results": {},
           "expert_opinions": {},
           "synthesis": {},
           "iteration_count": 0,
           "max_iterations": request.max_iterations,
           "errors": [],
       }
   ```

3. **Update Tests** (6 hours)
   ```python
   # Modify: tests/orchestration/test_api_query.py

   @pytest.mark.asyncio
   async def test_query_with_real_preprocessing():
       """Test query execution with real preprocessing (no mocks)"""
       request = QueryRequest(query="Test legal query")
       response = await client.post("/query/execute", json=request.dict())

       assert response.status_code == 200
       data = response.json()

       # Verify real preprocessing ran
       assert data["query_understanding"]["intent"] != "unknown"
       assert data["query_understanding"]["entities"] != []
       assert data["query_understanding"]["complexity"] > 0
   ```

**Files to Modify**:
- `backend/orchestration/api/services/query_executor.py` (+180 LOC)
- `backend/orchestration/langgraph_workflow.py` (update preprocessing node)
- `tests/orchestration/test_api_query.py` (+100 LOC)
- `tests/orchestration/test_workflow_with_preprocessing.py` (update assertions)

**Expected Deliverables**:
- ✅ Mock values removed from query_executor
- ✅ Real intent classification integrated
- ✅ Real complexity scoring integrated
- ✅ Real KG enrichment integrated
- ✅ All tests passing with real preprocessing

---

### Priority 3: Authentication & Rate Limiting (HIGH) 🟡

**Status**: Not started for orchestration (exists for RLCF)
**Effort**: 6-8 hours (1 day)
**Blocking**: Production security

**Problem**: Orchestration API endpoints are completely open

**Solution**: Implement API key authentication + Redis-based rate limiting

**Tasks**:

1. **Create Auth Tables** (2 hours)
   ```sql
   -- File: migrations/002_create_auth_tables.sql

   CREATE TABLE api_keys (
       id SERIAL PRIMARY KEY,
       key_hash VARCHAR(255) UNIQUE NOT NULL,
       user_id INTEGER,
       role VARCHAR(50) NOT NULL, -- unlimited, premium, standard, limited
       is_active BOOLEAN DEFAULT TRUE,
       created_at TIMESTAMP DEFAULT NOW(),
       expires_at TIMESTAMP
   );

   CREATE TABLE api_usage (
       id SERIAL PRIMARY KEY,
       api_key_id INTEGER REFERENCES api_keys(id),
       endpoint VARCHAR(255),
       method VARCHAR(10),
       status_code INTEGER,
       latency_ms INTEGER,
       timestamp TIMESTAMP DEFAULT NOW()
   );

   CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
   CREATE INDEX idx_api_usage_timestamp ON api_usage(timestamp DESC);
   ```

2. **Implement Auth Middleware** (4 hours)
   ```python
   # File: backend/orchestration/api/middleware/auth.py

   from fastapi import Request, HTTPException, status
   from fastapi.security import APIKeyHeader

   api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

   async def verify_api_key(api_key: str = Depends(api_key_header)):
       if not api_key:
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail="Missing API key"
           )

       # Verify key in database
       key_data = await db.get_api_key(api_key)
       if not key_data or not key_data.is_active:
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail="Invalid or expired API key"
           )

       return key_data
   ```

   ```python
   # File: backend/orchestration/api/middleware/rate_limit.py

   from fastapi import Request, HTTPException
   import redis.asyncio as aioredis

   class RateLimiter:
       def __init__(self, redis: aioredis.Redis):
           self.redis = redis

       async def check_limit(self, api_key: str, role: str) -> bool:
           # Rate limits per role
           limits = {
               "unlimited": None,      # No limit
               "premium": 1000,        # 1000 req/hour
               "standard": 100,        # 100 req/hour
               "limited": 10           # 10 req/hour
           }

           if limits[role] is None:
               return True

           # Redis sliding window
           key = f"rate_limit:{api_key}:{datetime.now().hour}"
           count = await self.redis.incr(key)
           await self.redis.expire(key, 3600)

           return count <= limits[role]
   ```

3. **Apply Middleware** (2 hours)
   ```python
   # Modify: backend/orchestration/api/main.py

   from .middleware.auth import verify_api_key
   from .middleware.rate_limit import RateLimiter

   app = FastAPI()
   rate_limiter = RateLimiter(redis)

   @app.middleware("http")
   async def rate_limit_middleware(request: Request, call_next):
       api_key = request.headers.get("X-API-Key")
       if api_key:
           key_data = await verify_api_key(api_key)
           if not await rate_limiter.check_limit(api_key, key_data.role):
               raise HTTPException(status_code=429, detail="Rate limit exceeded")

       response = await call_next(request)
       return response
   ```

**Files to Create**:
- `migrations/002_create_auth_tables.sql` (50 LOC)
- `backend/orchestration/api/middleware/auth.py` (150 LOC)
- `backend/orchestration/api/middleware/rate_limit.py` (100 LOC)
- `tests/orchestration/test_auth.py` (200 LOC)

**Expected Deliverables**:
- ✅ API key authentication working
- ✅ Rate limiting functional (4 tiers)
- ✅ Usage tracking in database
- ✅ HTTP 429 responses for rate-limited requests

---

## Short-Term Development (1-2 months)

### Priority 4: Admin Interface

**Objective**: Web-based dashboard for orchestration monitoring and management

**Components**:
- Query monitoring dashboard (real-time status, execution traces)
- Expert opinion review interface (convergent/divergent synthesis visualization)
- System performance metrics (latency, error rates, throughput)
- Configuration management UI (orchestration_config.yaml editor)

**Technology**: React 19 (extend existing frontend)

**Estimated Effort**: 3-4 weeks

---

### Priority 5: Frontend Integration

**Objective**: Integrate orchestration API with RLCF frontend

**Components**:
- Query submission interface (legal question input with context)
- Results display with provenance (expert opinions, synthesis, sources)
- Feedback submission interface (expert corrections, ratings)
- Analytics dashboard (query history, accuracy metrics)

**Technology**: React 19, TanStack Query, Zustand

**Estimated Effort**: 2-3 weeks

---

### Priority 6: End-to-End Testing

**Objective**: Comprehensive integration and E2E test suite

**Components**:
- E2E workflow tests (preprocessing → routing → retrieval → reasoning → synthesis)
- Performance tests (latency benchmarks, load testing)
- Resilience tests (failure scenarios, graceful degradation)
- Regression test suite (prevent breaking changes)

**Technology**: pytest, pytest-asyncio, locust (load testing)

**Estimated Effort**: 2 weeks

---

## Medium-Term Development (3-6 months)

### Priority 7: Performance Optimization

**Objectives**:
- Reduce query latency from ~8s to <5s (p95)
- Implement aggressive caching strategy (Redis L2 cache)
- Optimize database queries (indexes, query optimization)
- Parallel agent execution (reduce sequential bottlenecks)

**Estimated Effort**: 4-6 weeks

---

### Priority 8: Production Deployment

**Objectives**:
- Kubernetes manifests for all services
- CI/CD pipeline (GitHub Actions: test → build → deploy)
- Production environment configuration (staging, production)
- Load balancing and auto-scaling

**Technology**: Kubernetes, Helm, GitHub Actions, ArgoCD

**Estimated Effort**: 6-8 weeks

---

### Priority 9: Observability & Monitoring

**Objectives**:
- OpenTelemetry instrumentation (traces, metrics, logs)
- SigNoz deployment (open-source observability stack)
- Custom dashboards (Grafana)
- Alerting and incident response (PagerDuty integration)

**Technology**: OpenTelemetry, SigNoz, Grafana, Prometheus

**Estimated Effort**: 4 weeks

---

## Long-Term Vision (6-12 months)

### Priority 10: Multi-Language Support

**Objectives**:
- Extend beyond Italian to: English, French, German, Spanish
- Multi-language embeddings (Voyage Multilingual 2)
- Localized legal knowledge graphs
- Language-specific expert reasoning

**Estimated Effort**: 12+ weeks

---

### Priority 11: Advanced Learning Loops

**Objectives**:
- Automated training data generation from RLCF feedback
- Continuous model fine-tuning pipeline
- A/B testing framework for experts
- Adaptive routing based on performance metrics

**Estimated Effort**: 16+ weeks

---

### Priority 12: Research Publications

**Objectives**:
- RLCF methodology paper (peer-reviewed)
- Multi-expert architecture paper (AI & Law journal)
- Empirical evaluation studies (user studies, accuracy benchmarks)
- Open-source dataset publication

**Estimated Effort**: Ongoing

---

## Technical Debt & Improvements

### Code Quality

- [ ] Increase test coverage to 90%+ across all modules
- [ ] Add type hints to all functions (mypy compliance)
- [ ] Refactor large modules (e.g., synthesizer.py >1,000 LOC)
- [ ] Remove deprecated code and TODOs

### Documentation

- [ ] API documentation (OpenAPI/Swagger) - complete and accurate
- [ ] Architecture diagrams (Mermaid, PlantUML)
- [ ] Deployment guides (Kubernetes, Docker Compose)
- [ ] Troubleshooting guides (common errors, solutions)

### Performance

- [ ] Profile slow endpoints (py-spy, cProfile)
- [ ] Optimize database queries (EXPLAIN ANALYZE)
- [ ] Reduce memory footprint (batch processing, streaming)
- [ ] Implement query result streaming (SSE, WebSockets)

### Security

- [ ] Security audit (penetration testing)
- [ ] Dependency vulnerability scanning (Snyk, Dependabot)
- [ ] Secrets management (HashiCorp Vault)
- [ ] HTTPS enforcement and certificate management

---

## Success Metrics

### Technical Metrics

**Latency**:
- Query preprocessing: <200ms (p95)
- Retrieval agents: <2s parallel execution (p95)
- Expert reasoning: <8s for 4 experts (p95)
- Synthesis: <3s (p95)
- **Total end-to-end**: <11s → Target: <8s (p95)

**Accuracy**:
- Source attribution: 98%+ (provenance completeness)
- Expert agreement (convergent cases): 85%+
- RLCF validation accuracy: 92% → Target: 95%

**Availability**:
- API uptime: 99.5%+
- Error rate: <1%
- Mean time to recovery (MTTR): <30 minutes

### Business Metrics

**Adoption**:
- Registered users: Target 10,000 (legal professionals + citizens)
- Active monthly users: Target 1,000
- Queries per month: Target 100,000

**Quality**:
- User satisfaction (NPS): Target 50+
- Expert feedback rate: Target 60%+ queries validated
- Repeat usage: Target 70%+ monthly retention

**RLCF Community**:
- Expert members: Target 500 active validators
- Feedback submissions: Target 1,000/month
- Authority score distribution: Healthy (no single expert dominance)

---

## Related Documentation

### Implementation Guides

- **[Implementation Roadmap](../IMPLEMENTATION_ROADMAP.md)** - 42-week build plan with phases
- **[Technology Recommendations](../TECHNOLOGY_RECOMMENDATIONS.md)** - Tech stack with benchmarks (2025)
- **[Local Setup Guide](../07-guides/LOCAL_SETUP.md)** - Development environment setup
- **[Contributing Guide](../../CONTRIBUTING.md)** - Development workflow

### Architecture Documentation

- **[Architecture Overview](../ARCHITECTURE.md)** - 5-layer system architecture
- **[Preprocessing Layer](../03-architecture/01-preprocessing-layer.md)** - Query understanding + KG enrichment
- **[Orchestration Layer](../03-architecture/02-orchestration-layer.md)** - LLM Router + agents
- **[Reasoning Layer](../03-architecture/03-reasoning-layer.md)** - 4 experts + synthesizer
- **[Storage Layer](../03-architecture/04-storage-layer.md)** - Databases + caching
- **[Learning Layer](../03-architecture/05-learning-layer.md)** - RLCF framework

### Methodology

- **[RLCF Framework](../02-methodology/rlcf/RLCF.md)** - Core theoretical paper
- **[Legal Reasoning](../02-methodology/legal-reasoning.md)** - Expert methodologies
- **[Knowledge Graph](../02-methodology/knowledge-graph.md)** - Multi-source enrichment

### API & Testing

- **[API Documentation](../api/)** - REST endpoints, authentication, examples
- **[Testing Strategy](TESTING_STRATEGY.md)** - Consolidated testing guide

### Governance

- **[AI Act Compliance](../05-governance/ai-act-compliance.md)** - EU AI Act compliance strategy
- **[Data Protection](../05-governance/data-protection.md)** - GDPR implementation
- **[ALIS Association](../05-governance/arial-association.md)** - Community governance

---

## Conclusion

**Current State**: MERL-T has a solid foundation with 75% of core components implemented. The RLCF framework, multi-source knowledge graph, LLM-based orchestration, and multi-expert reasoning are all functionally complete.

**Immediate Priorities**: The next critical steps are database persistence, query understanding LLM integration, and authentication. These are blocking production deployment and must be completed before further feature work.

**Medium-Term Goals**: Focus on production readiness - deployment infrastructure, observability, performance optimization, and end-to-end testing.

**Long-Term Vision**: Expand to multi-language support, advanced learning loops, and research dissemination to establish MERL-T as a reference implementation for ethical legal AI.

**Success Path**: Follow the Build-Measure-Learn cycle. Implement vertical slices (complete features end-to-end), validate with RLCF feedback, iterate based on metrics, and maintain 85%+ test coverage throughout.

---

**Next Milestone**: Database persistence + Query Understanding LLM integration
**Target Timeline**: 2-3 weeks
**Owner**: Development Team
**Status**: Ready to start - all prerequisites met

---

*Document Version*: 3.0 (Refactored - Removed temporal references)
*Last Updated*: November 2025
*Maintained By*: ALIS Technical Team
