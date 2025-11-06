# MERL-T Next Steps Roadmap

**Current Status**: Week 6 COMPLETE ✅ (Orchestration Layer with full API)
**Date**: January 2025
**Total LOC Implemented**: ~18,287 (Week 6) + Previous phases

---

## Table of Contents

1. [Week 6 Achievements](#week-6-achievements)
2. [Immediate Next Steps (Week 7)](#immediate-next-steps-week-7)
3. [Short-Term Priorities (Weeks 8-10)](#short-term-priorities-weeks-8-10)
4. [Medium-Term Goals (Weeks 11-15)](#medium-term-goals-weeks-11-15)
5. [Critical Path Dependencies](#critical-path-dependencies)
6. [Resource Requirements](#resource-requirements)

---

## Week 6 Achievements

### ✅ Completed Components (18,287 LOC)

**Day 1-2: Router + Retrieval Layer** (~6,600 LOC)
- LLM Router with ExecutionPlan generation
- 3 Retrieval Agents (KG, API, VectorDB)
- E5-large embeddings integration
- Qdrant vector database setup
- 64 integration tests

**Day 3: Reasoning Layer** (~3,400 LOC)
- 4 Expert types (Literal, Systemic, Principles, Precedent)
- Convergent/Divergent Synthesizer
- Opinion aggregation with uncertainty preservation

**Day 4: Iteration Control** (~1,530 LOC)
- Multi-turn refinement controller
- 6 stopping criteria with priority evaluation
- Improvement delta calculation
- Convergence detection
- 25+ comprehensive tests

**Day 5: Complete API** (~4,856 LOC)
- **LangGraph Workflow** (750 LOC): 6 nodes, conditional routing, iteration loop
- **REST API** (3,318 LOC): 11 endpoints across 4 functional groups
- **Test Suite** (788 LOC): 40+ test cases with mocks

### 🎯 API Endpoints Implemented (11 total)

**Query Execution** (4):
- `POST /query/execute` - Execute complete pipeline
- `GET /query/status/{trace_id}` - Check execution status
- `GET /query/history/{user_id}` - User query history (paginated)
- `GET /query/retrieve/{trace_id}` - Full query retrieval

**Feedback Submission** (4):
- `POST /feedback/user` - User ratings (1-5 stars)
- `POST /feedback/rlcf` - Expert corrections with authority weighting
- `POST /feedback/ner` - Entity extraction corrections
- `GET /feedback/stats` - Real-time feedback statistics

**Analytics** (2):
- `GET /stats/pipeline` - Performance metrics (latency, usage, success rate)
- `GET /stats/feedback` - RLCF metrics and model improvements

**Health** (1):
- `GET /health` - Component status check

---

## Immediate Next Steps (Week 7)

### Priority 1: Database Integration (Days 1-2) 🔴 HIGH

**Objective**: Replace in-memory storage with PostgreSQL + Redis persistence

#### Task 1.1: PostgreSQL Schema Design (4 hours)
```sql
-- Migration: 001_create_core_tables.sql

CREATE TABLE queries (
    trace_id VARCHAR(50) PRIMARY KEY,
    session_id VARCHAR(100),
    query_text TEXT NOT NULL,
    query_context JSONB,
    enriched_context JSONB,
    status VARCHAR(20) NOT NULL, -- pending, in_progress, completed, failed
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at)
);

CREATE TABLE query_results (
    trace_id VARCHAR(50) PRIMARY KEY REFERENCES queries(trace_id),
    answer JSONB NOT NULL,
    execution_trace JSONB,
    metadata JSONB NOT NULL,
    confidence FLOAT,
    consensus_level FLOAT,
    iterations INT,
    stop_reason VARCHAR(50)
);

CREATE TABLE user_feedback (
    feedback_id VARCHAR(50) PRIMARY KEY,
    trace_id VARCHAR(50) REFERENCES queries(trace_id),
    user_id VARCHAR(100),
    rating INT CHECK (rating BETWEEN 1 AND 5),
    feedback_text TEXT,
    categories JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_trace_id (trace_id),
    INDEX idx_created_at (created_at)
);

CREATE TABLE rlcf_feedback (
    feedback_id VARCHAR(50) PRIMARY KEY,
    trace_id VARCHAR(50) REFERENCES queries(trace_id),
    expert_id VARCHAR(100) NOT NULL,
    authority_score FLOAT NOT NULL,
    corrections JSONB NOT NULL,
    overall_rating INT CHECK (overall_rating BETWEEN 1 AND 5),
    training_examples_generated INT,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_expert_id (expert_id),
    INDEX idx_created_at (created_at)
);

CREATE TABLE ner_corrections (
    correction_id VARCHAR(50) PRIMARY KEY,
    trace_id VARCHAR(50) REFERENCES queries(trace_id),
    expert_id VARCHAR(100) NOT NULL,
    correction_type VARCHAR(20) NOT NULL, -- MISSING_ENTITY, SPURIOUS_ENTITY, etc.
    correction_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_expert_id (expert_id),
    INDEX idx_created_at (created_at)
);
```

**Files to Create/Modify**:
- `backend/orchestration/api/database.py` (150 LOC) - SQLAlchemy models
- `backend/orchestration/api/services/persistence_service.py` (300 LOC) - CRUD operations
- `migrations/001_create_core_tables.sql` (100 LOC) - Database schema

#### Task 1.2: Redis Caching Layer (4 hours)

**Use Cases**:
- Query status cache (TTL: 24h)
- User sessions (TTL: 7d)
- Hot feedback (TTL: 7d)
- Rate limiting counters

**Implementation**:
```python
# backend/orchestration/api/services/cache_service.py

import redis
from typing import Optional, Dict, Any
import json

class CacheService:
    def __init__(self):
        self.redis = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )

    async def set_query_status(self, trace_id: str, status_data: Dict[str, Any], ttl: int = 86400):
        """Cache query status for 24 hours."""
        key = f"query:status:{trace_id}"
        self.redis.setex(key, ttl, json.dumps(status_data))

    async def get_query_status(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached query status."""
        key = f"query:status:{trace_id}"
        data = self.redis.get(key)
        return json.loads(data) if data else None

    async def increment_rate_limit(self, user_id: str, window: int = 3600) -> int:
        """Increment rate limit counter for user."""
        key = f"ratelimit:{user_id}"
        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, window)
        return count
```

**Files to Create**:
- `backend/orchestration/api/services/cache_service.py` (200 LOC)

#### Task 1.3: Update API Services (6 hours)

**Modify** `QueryExecutor` to use persistence:
```python
# backend/orchestration/api/services/query_executor.py

from .persistence_service import PersistenceService
from .cache_service import CacheService

class QueryExecutor:
    def __init__(self):
        self.persistence = PersistenceService()
        self.cache = CacheService()

    async def execute_query(self, request: QueryRequest) -> QueryResponse:
        trace_id = self._generate_trace_id()

        # 1. Save initial query to PostgreSQL
        await self.persistence.create_query(
            trace_id=trace_id,
            query_text=request.query,
            query_context=request.context.model_dump() if request.context else {},
            status="in_progress"
        )

        # 2. Cache status in Redis
        await self.cache.set_query_status(trace_id, {
            "status": "in_progress",
            "started_at": datetime.utcnow().isoformat()
        })

        try:
            # 3. Execute workflow
            final_state = await self._execute_workflow(request, trace_id)

            # 4. Extract response
            response = self._build_response(final_state, trace_id)

            # 5. Save result to PostgreSQL
            await self.persistence.save_query_result(
                trace_id=trace_id,
                answer=response.answer.model_dump(),
                execution_trace=response.execution_trace.model_dump() if response.execution_trace else None,
                metadata=response.metadata.model_dump()
            )

            # 6. Update cache
            await self.cache.set_query_status(trace_id, {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat()
            })

            return response

        except Exception as e:
            # Update status to failed
            await self.persistence.update_query_status(trace_id, "failed")
            await self.cache.set_query_status(trace_id, {"status": "failed", "error": str(e)})
            raise
```

**Files to Modify**:
- `backend/orchestration/api/services/query_executor.py` (+100 LOC)
- `backend/orchestration/api/services/feedback_processor.py` (+80 LOC)
- `backend/orchestration/api/routers/query.py` (+50 LOC)

**Estimated Time**: 14-16 hours (2 days)
**Priority**: 🔴 HIGH (blocks production deployment)

---

### Priority 2: Preprocessing Integration (Days 3-4) 🔴 HIGH

**Objective**: Integrate Query Understanding and KG Enrichment before Router

#### Task 2.1: Query Understanding Module Integration (6 hours)

**Current Gap**: `QueryExecutor._build_initial_state()` uses placeholder values:
```python
query_context = {
    "query": request.query,
    "intent": "unknown",  # ← TODO
    "complexity": 0.5,    # ← TODO
}
```

**Solution**: Integrate existing `backend/preprocessing/` modules

**Implementation**:
```python
# backend/orchestration/api/services/query_executor.py

from backend.preprocessing.intent_classifier import IntentClassifier
from backend.preprocessing.ner_service import NERService
from backend.preprocessing.complexity_scorer import ComplexityScorer

class QueryExecutor:
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.ner_service = NERService()
        self.complexity_scorer = ComplexityScorer()
        # ...

    async def _preprocess_query(self, query_text: str) -> Dict[str, Any]:
        """Execute preprocessing pipeline."""

        # 1. Intent Classification
        intent = await self.intent_classifier.classify(query_text)

        # 2. NER for entity extraction
        entities = await self.ner_service.extract_entities(query_text)

        # 3. Complexity Scoring
        complexity = await self.complexity_scorer.score(query_text, entities)

        return {
            "intent": intent,
            "entities": entities,
            "complexity": complexity
        }

    async def _build_initial_state(self, request, trace_id):
        # Run preprocessing first
        preprocessing_result = await self._preprocess_query(request.query)

        query_context = {
            "query": request.query,
            "intent": preprocessing_result["intent"],  # ← Real value
            "complexity": preprocessing_result["complexity"],  # ← Real value
            "entities": preprocessing_result["entities"],  # ← Real entities
            # ...
        }
```

**Files to Modify**:
- `backend/orchestration/api/services/query_executor.py` (+80 LOC)

#### Task 2.2: KG Enrichment Integration (6 hours)

**Current Gap**: `enriched_context` is placeholder:
```python
enriched_context = {
    "concepts": [],  # ← TODO
    "entities": [],  # ← TODO
    "norms": [],     # ← TODO
}
```

**Solution**: Integrate `backend/preprocessing/kg_enrichment_service.py`

**Implementation**:
```python
# backend/orchestration/api/services/query_executor.py

from backend.preprocessing.kg_enrichment_service import KGEnrichmentService

class QueryExecutor:
    def __init__(self):
        self.kg_enrichment = KGEnrichmentService()
        # ...

    async def _enrich_with_kg(self, query_text: str, entities: List[Dict]) -> Dict[str, Any]:
        """Enrich query with Knowledge Graph data."""

        # Call KG enrichment service
        enrichment_result = await self.kg_enrichment.enrich(
            query_text=query_text,
            entities=entities
        )

        return {
            "concepts": enrichment_result.concepts,
            "entities": enrichment_result.entities_enriched,
            "norms": enrichment_result.norms_mapped,
            "jurisprudence": enrichment_result.jurisprudence,
            "controversy_flags": enrichment_result.controversy_flags
        }

    async def _build_initial_state(self, request, trace_id):
        # 1. Preprocessing
        preprocessing_result = await self._preprocess_query(request.query)

        # 2. KG Enrichment
        enriched_context = await self._enrich_with_kg(
            request.query,
            preprocessing_result["entities"]
        )

        # Now build state with real data
        initial_state = {
            "query_context": {
                "intent": preprocessing_result["intent"],
                "complexity": preprocessing_result["complexity"],
                # ...
            },
            "enriched_context": enriched_context,  # ← Real data
            # ...
        }
```

**Files to Modify**:
- `backend/orchestration/api/services/query_executor.py` (+100 LOC)

**Estimated Time**: 12-14 hours (2 days)
**Priority**: 🔴 HIGH (required for accurate routing)

---

### Priority 3: Authentication & Rate Limiting (Day 5) 🟡 MEDIUM

**Objective**: Secure API with key-based authentication and quotas

#### Task 3.1: API Key Authentication (4 hours)

**Schema**:
```sql
CREATE TABLE api_keys (
    key_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    api_key VARCHAR(64) UNIQUE NOT NULL, -- SHA-256 hash
    role VARCHAR(20) NOT NULL, -- user, expert, admin
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_api_key (api_key),
    INDEX idx_user_id (user_id)
);

CREATE TABLE api_usage (
    usage_id BIGSERIAL PRIMARY KEY,
    key_id VARCHAR(50) REFERENCES api_keys(key_id),
    endpoint VARCHAR(100) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INT,
    latency_ms FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_key_id (key_id),
    INDEX idx_created_at (created_at)
);
```

**Middleware Implementation**:
```python
# backend/orchestration/api/middleware/auth.py

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    # Verify key in database
    key_data = await persistence.get_api_key(api_key)

    if not key_data or not key_data["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key"
        )

    # Check expiration
    if key_data["expires_at"] and key_data["expires_at"] < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired"
        )

    return key_data

# Apply to endpoints
@router.post("/query/execute", dependencies=[Depends(verify_api_key)])
async def execute_query(...):
    ...
```

#### Task 3.2: Rate Limiting (2 hours)

**Implementation**:
```python
# backend/orchestration/api/middleware/rate_limit.py

from fastapi import Request, HTTPException, status

async def rate_limit_middleware(request: Request, call_next):
    # Extract user_id from API key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        key_data = await persistence.get_api_key(api_key)
        user_id = key_data["user_id"]

        # Check rate limit
        count = await cache.increment_rate_limit(user_id, window=3600)

        # Get user quota
        quota = key_data.get("hourly_quota", 100)

        if count > quota:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Quota: {quota} requests/hour"
            )

    response = await call_next(request)
    return response

app.middleware("http")(rate_limit_middleware)
```

**Files to Create/Modify**:
- `backend/orchestration/api/middleware/auth.py` (150 LOC)
- `backend/orchestration/api/middleware/rate_limit.py` (100 LOC)
- `backend/orchestration/api/main.py` (+30 LOC)
- `migrations/002_create_auth_tables.sql` (50 LOC)

**Estimated Time**: 6-8 hours (1 day)
**Priority**: 🟡 MEDIUM (required for production, not blocking)

---

## Short-Term Priorities (Weeks 8-10)

### Week 8: Admin Interface & Monitoring

#### Task: Gradio Admin Panel (3 days)

**Features**:
1. **Dashboard** - Real-time pipeline metrics, active queries, error logs
2. **Feedback Management** - Review RLCF corrections, approve/reject, trigger retraining
3. **Configuration** - Update orchestration_config.yaml, adjust thresholds, enable/disable components
4. **User Management** - Create API keys, manage quotas, view usage

**Files to Create**:
- `backend/orchestration/admin/dashboard.py` (500 LOC)
- `backend/orchestration/admin/feedback_manager.py` (400 LOC)
- `backend/orchestration/admin/config_editor.py` (300 LOC)

#### Task: Observability (2 days)

**Implement**:
- Structured logging with trace_id propagation
- Prometheus metrics export
- Grafana dashboards
- Error alerting (email/Slack)

**Files to Create**:
- `backend/orchestration/observability/metrics.py` (200 LOC)
- `infrastructure/grafana/dashboards/pipeline.json` (500 LOC)
- `infrastructure/prometheus/prometheus.yml` (100 LOC)

---

### Week 9: Frontend Integration

#### Task: React Frontend (5 days)

**Features**:
1. **Query Interface** - Submit queries, view real-time progress
2. **Answer Display** - Primary answer, legal basis, alternative interpretations
3. **Feedback Forms** - User ratings, RLCF corrections, NER fixes
4. **History** - View past queries, re-submit similar queries

**Tech Stack**:
- React 19 + TypeScript
- TanStack Query for API calls
- Zustand for state management
- TailwindCSS for styling

**Files to Create**:
- `frontend/merl-t-web/src/pages/QueryPage.tsx` (400 LOC)
- `frontend/merl-t-web/src/pages/HistoryPage.tsx` (300 LOC)
- `frontend/merl-t-web/src/components/AnswerCard.tsx` (200 LOC)
- `frontend/merl-t-web/src/services/api.ts` (300 LOC)

---

### Week 10: RLCF Retraining Pipeline

#### Task: Automated Model Retraining (3 days)

**Components**:
1. **Training Data Preparation** - Collect feedback, generate training examples
2. **Model Fine-Tuning** - Fine-tune Router, NER model with LoRA/QLoRA
3. **Evaluation** - Test new models, compare metrics
4. **Deployment** - Hot-swap models if improvements confirmed

**Files to Create**:
- `backend/orchestration/training/training_pipeline.py` (600 LOC)
- `backend/orchestration/training/data_prep.py` (400 LOC)
- `backend/orchestration/training/evaluator.py` (300 LOC)

#### Task: A/B Testing Framework (2 days)

**Features**:
- Route 10% of queries to new model
- Compare performance metrics
- Gradual rollout if successful

**Files to Create**:
- `backend/orchestration/api/services/ab_testing.py` (250 LOC)

---

## Medium-Term Goals (Weeks 11-15)

### Week 11-12: Advanced Features

1. **SSE Streaming** - Real-time query progress updates
2. **Multi-Turn Conversations** - Contextual follow-up questions
3. **Document Upload** - Analyze user-provided legal documents
4. **Export Functionality** - PDF reports, citations

### Week 13-14: Performance Optimization

1. **Caching Strategy** - Semantic cache for similar queries
2. **Database Indexing** - Optimize slow queries
3. **Async Task Queue** - Celery for background jobs
4. **Load Balancing** - Nginx + multiple Uvicorn workers

### Week 15: Production Deployment

1. **Kubernetes Setup** - Helm charts, autoscaling
2. **CI/CD Pipeline** - GitHub Actions for automated deployment
3. **Backup Strategy** - PostgreSQL daily backups, Redis snapshots
4. **Security Audit** - Penetration testing, vulnerability scanning

---

## Critical Path Dependencies

```
Week 7 (Database + Preprocessing)
    ↓
Week 8 (Admin Interface)
    ↓
Week 9 (Frontend) ← Parallel → Week 10 (Retraining)
    ↓
Week 11-12 (Advanced Features)
    ↓
Week 13-14 (Optimization)
    ↓
Week 15 (Production Deployment)
```

**Blockers**:
- Week 7 Day 1-2 (Database) blocks all persistence-dependent features
- Week 7 Day 3-4 (Preprocessing) blocks accurate routing
- Week 8 (Admin) required before public beta

---

## Resource Requirements

### Week 7

**Personnel**:
- 1 Backend Engineer (database, API integration)
- 0.5 DevOps Engineer (Redis setup, migrations)

**Infrastructure**:
- PostgreSQL instance (16 GB RAM, 100 GB SSD)
- Redis instance (8 GB RAM)
- Development environment (Docker Compose)

**Time**: 5 days (1 week)

### Weeks 8-10

**Personnel**:
- 1 Backend Engineer (admin panel, retraining)
- 1 Frontend Engineer (React interface)
- 0.5 ML Engineer (model fine-tuning)
- 0.5 DevOps Engineer (monitoring setup)

**Time**: 3 weeks

---

## Summary

**Week 6 Achievement**: Complete orchestration layer with 11-endpoint REST API ✅

**Next Immediate Steps**:
1. **Week 7 Days 1-2**: Database integration (PostgreSQL + Redis) 🔴
2. **Week 7 Days 3-4**: Preprocessing integration (Query Understanding + KG Enrichment) 🔴
3. **Week 7 Day 5**: Authentication & rate limiting 🟡
4. **Week 8**: Admin interface + monitoring
5. **Week 9**: React frontend
6. **Week 10**: RLCF retraining pipeline

**Critical Path**: Database → Preprocessing → Admin → Frontend → Production

**Estimated Timeline to Production**: 9 weeks (Week 7-15)

---

**Document Version**: 1.0
**Last Updated**: January 2025
**Status**: Ready for Week 7 implementation
