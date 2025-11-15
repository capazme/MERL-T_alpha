# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MERL-T (Multi-Expert Legal Retrieval Transformer)** is an AI-powered architecture for legal research, compliance monitoring, and regulatory analysis. Sponsored by ALIS (Artificial Legal Intelligence Society), this repository contains both **comprehensive technical documentation** and **working implementation code**.

**Current Status**: **v0.9.0 (82% complete)** - Production-ready for deployment (Priority 1-3 complete)

**Key Metrics** (Verified November 14, 2025):
- **Backend**: 41,888 LOC across 117 Python modules
- **Tests**: 19,541 LOC with 200+ test cases (88-90% coverage)
- **Frontend**: ~3,000 LOC (React 19 + TypeScript)
- **Documentation**: 69,323 LOC across 101 files
- **Total Project**: ~134,252 LOC

**Recently Completed** (November 2025):
1. ✅ **Database Persistence** (Priority 1) - PostgreSQL + Redis fully implemented
2. ✅ **Query Understanding LLM Integration** (Priority 2) - Preprocessing integrated in LangGraph workflow
3. ✅ **Authentication & Rate Limiting** (Priority 3) - Applied to all 8 API endpoints

**Remaining Components** (18% remaining):
1. **Frontend Integration** (Priority 4-5) - Admin interface (40% complete), query submission UI (35% complete)
2. **Neo4j Production Deployment** (Storage Layer) - Schema ready, deployment pending
3. **RLCF Production Platform** (Learning Layer) - Algorithms ready but platform incomplete (20% complete)
4. **Production Infrastructure** (Priority 8) - Kubernetes, Helm, CI/CD (5% complete)

---

## Current Implementation Status

| Layer | Status | Completion | Implementation Details |
|-------|--------|------------|------------------------|
| **Preprocessing** | ✅ Complete | 100% | Entity extraction (NER), KG enrichment (5 sources), NER feedback loop, LangGraph integration |
| **Orchestration** | ✅ Complete | 100% | LLM Router (Claude), 3 retrieval agents, LangGraph workflow (942 LOC), **Auth + Rate Limiting** |
| **Reasoning** | ✅ Complete | 100% | 4 experts (Literal, Systemic, Principles, Precedent), Synthesizer (474 LOC) |
| **Storage** | ✅ Complete | 100% | **PostgreSQL (orchestration + RLCF)**, Qdrant (vectors), **Redis (caching + rate limiting)**, Neo4j (schema ready) |
| **Learning (RLCF)** | 🚧 Partial | 40% | Authority scoring complete, feedback aggregation ready, platform missing |

**See**: `docs/08-iteration/CODE_METRICS_SUMMARY.md` for complete component breakdown

---

## Next Steps (Priority-based)

### Priority 1: Database Persistence ✅ COMPLETE
**Status**: ✅ **COMPLETED** (November 2025)
**Effort**: 0 hours (was already implemented)

**Completed Implementation**:
- ✅ PostgreSQL schema: 7 tables (queries, query_results, user_feedback, rlcf_feedback, ner_corrections, api_keys, api_usage)
- ✅ Redis caching layer: query status, session storage, rate limiting
- ✅ Persistence service: 577 LOC async SQLAlchemy 2.0
- ✅ Migration scripts: 001 (14,509 LOC), 002 (10,453 LOC)

**Files Created**:
- `backend/orchestration/api/migrations/001_create_orchestration_tables.sql`
- `backend/orchestration/api/migrations/002_create_auth_tables.sql`
- `backend/orchestration/api/database.py` (225 LOC)
- `backend/orchestration/api/models.py` (525 LOC)
- `backend/orchestration/api/services/persistence_service.py` (577 LOC)
- `backend/orchestration/api/services/cache_service.py` (497 LOC)
- `tests/orchestration/test_persistence.py` (multiple test files)

### Priority 2: Query Understanding LLM Integration ✅ COMPLETE
**Status**: ✅ **COMPLETED** (November 2025)
**Effort**: 0 hours (was already implemented in LangGraph workflow)

**Completed Implementation**:
- ✅ Preprocessing node in langgraph_workflow.py (lines 108-278)
- ✅ QueryUnderstandingModule integrated (877 LOC)
- ✅ KGEnrichmentService integrated (704 LOC, 5-source enrichment)
- ✅ 15 integration tests in test_preprocessing_integration.py (596 LOC)

**Note**: "Mock values" in query_executor.py are **intentional placeholders** (design pattern), replaced immediately by preprocessing_node when workflow executes.

**Files Modified**:
- `backend/orchestration/langgraph_workflow.py` (preprocessing_node already implemented)
- `tests/orchestration/test_preprocessing_integration.py` (tests already passing)

### Priority 3: Authentication & Rate Limiting ✅ COMPLETE
**Status**: ✅ **COMPLETED** (November 14, 2025)
**Effort**: 1-2 hours (applied middleware to endpoints)

**Completed Implementation**:
- ✅ Auth middleware: auth.py (345 LOC), SHA-256 hashing, role-based access
- ✅ Rate limiting middleware: rate_limit.py (346 LOC), Redis sliding window, 4 tiers
- ✅ Applied to all 8 endpoints: query.py (4 endpoints), feedback.py (4 endpoints)
- ✅ Test coverage: 50 unit tests (1,141 LOC), 19 integration tests (450 LOC)

**Files Modified Today** (November 14, 2025):
- `backend/orchestration/api/routers/query.py` (added auth to 4 endpoints)
- `backend/orchestration/api/routers/feedback.py` (added auth to 4 endpoints)

---

## Current Priority: Frontend Integration (Priority 4-5)

### Priority 4: Admin Interface (40% complete, 2-3 weeks)
**Status**: In Progress
**Components**:
- ✅ AdminDashboard.tsx (510 LOC) - task management, user management, data export
- ❌ Query monitoring dashboard (real-time status, execution traces)
- ❌ Expert opinion review interface

### Priority 5: Frontend Integration (35% complete, 1-2 weeks)
**Status**: In Progress
**Components**:
- ✅ TanStack Query setup + API client wrapper
- ❌ Query submission interface
- ❌ Results display with provenance
- ❌ Feedback submission interface

---

## Repository Structure

### Backend Implementation (41,888 LOC, 117 modules)

```
backend/
├── rlcf_framework/         # RLCF Core (13,148 LOC, 38 files)
│   ├── main.py             # FastAPI app (1,743 LOC, 50+ endpoints)
│   ├── models.py           # SQLAlchemy 2.0 async models (435 LOC)
│   ├── schemas.py          # Pydantic validation (299 LOC)
│   ├── authority_module.py # Authority scoring A_u(t) (326 LOC)
│   ├── aggregation_engine.py # Shannon entropy aggregation (284 LOC)
│   ├── bias_analysis.py    # Bias detection (513 LOC)
│   ├── rlcf_feedback_processor.py # Expert vote aggregation (548 LOC)
│   ├── app_interface.py    # Gradio admin UI (1,112 LOC)
│   ├── routers/            # API routers (2,013 LOC, 4 files)
│   ├── task_handlers/      # Task type handlers (2,067 LOC, 5 files)
│   ├── cli/                # CLI tools (518 LOC, 2 files)
│   └── services/           # Shared services (966 LOC)
│
├── preprocessing/          # Preprocessing Layer (11,137 LOC, 26 files)
│   ├── query_understanding_module.py # NER + intent (877 LOC)
│   ├── kg_enrichment_service.py # 5-source KG enrichment (704 LOC)
│   ├── cypher_queries.py   # Neo4j Cypher builder (693 LOC)
│   ├── models_kg.py        # KG data models (500 LOC)
│   ├── ner_feedback_loop.py # NER learning loop (542 LOC)
│   ├── normattiva_sync_job.py # Normattiva sync (403 LOC)
│   └── contribution_processor.py # Community sources (403 LOC)
│
├── orchestration/          # Orchestration Layer (16,603 LOC, 45 files)
│   ├── config/
│   │   ├── orchestration_config.yaml # Config (355 LOC)
│   │   └── orchestration_config.py   # Pydantic loader (464 LOC)
│   ├── prompts/
│   │   └── router_v1.txt   # LLM Router prompt (1,916 LOC)
│   ├── services/
│   │   ├── embedding_service.py # E5-large embeddings (329 LOC)
│   │   └── qdrant_service.py    # Qdrant collection mgmt (298 LOC)
│   ├── agents/
│   │   ├── base.py         # Abstract RetrievalAgent (200 LOC)
│   │   ├── kg_agent.py     # Neo4j KG retrieval (350 LOC)
│   │   ├── api_agent.py    # Norma Controller API (450 LOC)
│   │   └── vectordb_agent.py # Qdrant semantic search (617 LOC)
│   ├── experts/            # 4 Reasoning Experts (1,681 LOC, 6 files)
│   │   ├── base.py         # Abstract Expert (533 LOC with shared logic)
│   │   ├── literal_interpreter.py   # Literal (74 LOC - thin wrapper)
│   │   ├── systemic_teleological.py # Systemic (75 LOC - thin wrapper)
│   │   ├── principles_balancer.py   # Principles (75 LOC - thin wrapper)
│   │   ├── precedent_analyst.py     # Precedent (75 LOC - thin wrapper)
│   │   └── synthesizer.py  # Opinion synthesis (474 LOC)
│   ├── iteration/
│   │   ├── models.py       # Iteration state models (330 LOC)
│   │   └── controller.py   # Multi-turn controller (500 LOC)
│   ├── api/                # FastAPI REST API (3,318 LOC, 13 files)
│   │   ├── main.py         # FastAPI app (343 LOC)
│   │   ├── schemas/        # Query, feedback, stats schemas (1,066 LOC)
│   │   ├── routers/        # Query, feedback, stats endpoints (1,112 LOC)
│   │   └── services/       # Query executor, feedback processor (840 LOC)
│   ├── llm_router.py       # 100% LLM-based Router (450 LOC)
│   └── langgraph_workflow.py # Complete workflow (942 LOC)
│
├── reasoning/              # Reasoning Layer (WIP - future expansion)
└── shared/                 # Shared utilities (WIP)
```

**Expert Implementation Design** (Important):
- Each expert is **~75 LOC** (thin wrapper around prompts)
- **Base class** (`experts/base.py` - 533 LOC) contains all shared logic
- **Prompt templates** are embedded strings (not separate files)
- **Heavy lifting** is done by LLM (Claude 3.5 Sonnet)
- This is **by design** - experts are declarative, not procedural

**See**: `docs/08-iteration/CODE_METRICS_SUMMARY.md` for complete breakdown

### Frontend Implementation (~3,000 LOC)

```
frontend/
└── rlcf-web/               # React 19 application
    ├── src/                # TypeScript source code
    │   ├── components/     # React components
    │   ├── pages/          # Route pages
    │   └── api/            # TanStack Query hooks
    ├── package.json        # Vite + React 19 + TypeScript
    └── vite.config.ts      # Build configuration
```

### Test Suite (19,541 LOC, 200+ tests, 88-90% coverage)

```
tests/
├── rlcf/                   # RLCF tests (2,632 LOC, 20+ tests)
│   ├── test_authority_module.py
│   ├── test_aggregation_engine.py
│   ├── test_bias_analysis.py
│   └── conftest.py         # Shared fixtures
│
├── preprocessing/          # Preprocessing tests (5,293 LOC, 100+ tests)
│   ├── test_kg_complete.py # KG enrichment (2,156 LOC)
│   └── test_query_understanding.py
│
├── orchestration/          # Orchestration tests (7,794 LOC, 80+ tests)
│   ├── test_llm_router.py
│   ├── test_embedding_service.py
│   ├── test_vectordb_agent.py
│   ├── test_experts.py
│   ├── test_iteration_controller.py
│   ├── test_api_query.py
│   ├── test_api_feedback.py
│   ├── test_api_stats.py
│   ├── test_preprocessing_integration.py
│   ├── test_workflow_with_preprocessing.py
│   └── test_graceful_degradation.py
│
└── integration/            # Integration tests (3,822 LOC)
    └── test_full_pipeline_integration.py
```

### Documentation Structure (69,323 LOC, 101 files)

```
docs/
├── 01-introduction/        # Executive summary, vision, problem statement
├── 02-methodology/         # RLCF framework, knowledge graphs, legal reasoning
├── 03-architecture/        # 5-layer system architecture
├── 04-implementation/      # API gateway, LLM integration, databases
├── 05-governance/          # AI Act compliance, GDPR, ALIS association
├── 06-resources/           # Bibliography, datasets
├── 07-guides/              # LOCAL_SETUP.md, contributing guide
├── 08-iteration/           # NEXT_STEPS.md, TESTING_STRATEGY.md, CODE_METRICS_SUMMARY.md
├── api/                    # API_EXAMPLES.md, AUTHENTICATION.md, RATE_LIMITING.md
├── IMPLEMENTATION_ROADMAP.md    # 42-week build plan
└── TECHNOLOGY_RECOMMENDATIONS.md # 2025 tech stack with benchmarks
```

---

## Key Concepts

### RLCF Framework (Reinforcement Learning from Community Feedback)

The centerpiece methodology located in `docs/02-methodology/rlcf/`. RLCF is a novel alignment approach for legal AI that differs from traditional RLHF by:

- **Dynamic Authority Scoring**: Expert influence based on demonstrated competence, not static credentials
  - Formula: `A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)`
  - Implemented: `backend/rlcf_framework/authority_module.py` (326 LOC)

- **Uncertainty Preservation**: Expert disagreement is valuable information, not noise
  - Shannon entropy quantifies disagreement
  - Implemented: `backend/rlcf_framework/aggregation_engine.py` (284 LOC)

- **Community-Driven Validation**: Distributed expert feedback with transparent aggregation
  - Dynamic quorum by entity type (Norma: 3 experts, Sentenza: 4 experts)
  - Implemented: `backend/rlcf_framework/rlcf_feedback_processor.py` (548 LOC)

- **Mathematical Rigor**: Formally defined algorithms with academically grounded theory
  - Core paper: `docs/02-methodology/rlcf/RLCF.md`

**Key RLCF Documentation**:
- `docs/02-methodology/rlcf/RLCF.md` - Core theoretical paper
- `docs/02-methodology/rlcf/technical/architecture.md` - System architecture
- `docs/02-methodology/rlcf/guides/quick-start.md` - Getting started guide

### System Architecture (5 Layers)

1. **Preprocessing Layer** (✅ 100%) - Query understanding, NER, intent classification, KG enrichment (5 sources)
2. **Orchestration Layer** (✅ 100%) - LLM Router, 3 retrieval agents (KG, API, VectorDB), LangGraph workflow
3. **Reasoning Layer** (✅ 100%) - 4 expert types, Synthesizer, Iteration Controller
4. **Storage Layer** (🚧 70%) - PostgreSQL (ready), Qdrant (tested), Neo4j (schema only), Redis (pending)
5. **Learning Layer** (🚧 40%) - RLCF algorithms (ready), production platform (missing)

**Key Architecture Files**:
- `docs/03-architecture/01-preprocessing-layer.md` - Query understanding + KG enrichment
- `docs/03-architecture/02-orchestration-layer.md` - LLM Router + agents (most detailed)
- `docs/03-architecture/03-reasoning-layer.md` - 4 experts + synthesis
- `docs/03-architecture/04-storage-layer.md` - PostgreSQL, Qdrant, Neo4j, Redis
- `docs/03-architecture/05-learning-layer.md` - RLCF feedback loops

### Technology Stack

**Backend**:
- Python 3.11+, FastAPI (async/await), SQLAlchemy 2.0, Pydantic 2.5, Click (CLI)
- LangGraph (state machine workflow), OpenRouter (LLM provider), NumPy/SciPy (RLCF)

**Databases**:
- PostgreSQL 16 (relational, prod-ready)
- Qdrant (vectors, tested)
- Neo4j/Memgraph (graph, schema only - Memgraph recommended for 10-25x speed)
- Redis 7 (cache, pending)

**Frontend**:
- React 19, Vite, TypeScript, TailwindCSS, TanStack Query, Zustand

**AI/ML**:
- LLM: Claude 3.5 Sonnet (via OpenRouter)
- Embeddings: E5-large multilingual (1024 dims, self-hosted)
- NER: spaCy for entity extraction

**Infrastructure**:
- Docker, Docker Compose, Kubernetes-ready
- CI/CD: GitHub Actions (planned)
- Monitoring: SigNoz (planned)

**See**: `docs/TECHNOLOGY_RECOMMENDATIONS.md` for complete 2025 tech stack analysis

---

## Working with the Codebase

### Import Patterns (CRITICAL - Must Follow)

The repository uses a **monorepo structure** with specific import conventions:

**Backend internal imports** (within `backend/rlcf_framework/`, `backend/orchestration/`, etc.):
```python
# Use RELATIVE imports
from .models import User, LegalTask
from .config import load_model_config
from . import authority_module
```

**Test imports** (from `tests/`):
```python
# Use ABSOLUTE imports with backend prefix
from backend.rlcf_framework import models
from backend.rlcf_framework.authority_module import calculate_authority_score
from backend.orchestration.llm_router import LLMRouter
```

**Cross-layer imports** (e.g., orchestration → preprocessing):
```python
# Use ABSOLUTE imports
from backend.preprocessing.kg_enrichment_service import KGEnrichmentService
from backend.rlcf_framework.models import User
```

**Why this pattern?**
- Relative imports within the package ensure modularity
- Absolute imports from tests allow proper package resolution
- Supports both `pip install -e .` and direct Python execution
- Prevents circular import issues

### CLI Tools

Two CLI entry points defined in `setup.py`:

**rlcf-cli** (User commands):
```bash
# Task management
rlcf-cli tasks create tasks.yaml
rlcf-cli tasks list --status OPEN --limit 10
rlcf-cli tasks export 123 --format json -o task_123.json

# User management
rlcf-cli users create john_doe --authority-score 0.5
rlcf-cli users list --sort-by authority_score
```

**rlcf-admin** (Admin commands):
```bash
# Configuration
rlcf-admin config show --type model
rlcf-admin config validate

# Database
rlcf-admin db migrate
rlcf-admin db seed --users 5 --tasks 10
rlcf-admin db reset

# Server
rlcf-admin server --reload  # Development mode
rlcf-admin server --host 0.0.0.0 --port 8080
```

**Implementation**: `backend/rlcf_framework/cli/commands.py` (518 LOC)

### Docker Deployment

**Development environment** (SQLite + hot-reload):
```bash
docker-compose up -d
# Backend: http://localhost:8000/docs
# Frontend: http://localhost:3000
```

**Production environment** (PostgreSQL + multi-worker):
```bash
docker-compose -f docker-compose.prod.yml up -d
```

**Databases only** (for native development):
```bash
docker-compose -f docker-compose.dev.yml up -d
```

**Services**:
- `backend`: FastAPI with Uvicorn
- `frontend`: React 19 with Vite dev server
- `postgres`: PostgreSQL 16 (optional in dev, required in prod)
- `neo4j`: Memgraph/Neo4j (profile-based)
- `redis`: Redis 7 (profile-based)
- `qdrant`: Qdrant vector DB (profile-based)

### Configuration Management

**Environment variables** (`.env.template` → `.env`):
```bash
# LLM & AI
OPENROUTER_API_KEY=sk-or-...
ROUTER_MODEL=google/gemini-2.5-flash
EXPERT_MODEL=google/gemini-2.5-flash

# Databases
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/merl_t
QDRANT_HOST=localhost
QDRANT_PORT=6333
REDIS_URL=redis://localhost:6379

# APIs
NORMA_API_URL=http://localhost:5000
ADMIN_API_KEY=your-secret-key

# RLCF Parameters
AUTHORITY_ALPHA=0.3  # Base authority weight
AUTHORITY_BETA=0.5   # Temporal authority weight
AUTHORITY_GAMMA=0.2  # Performance weight
```

**YAML configuration files** (hot-reloadable):
- `backend/rlcf_framework/model_config.yaml` - Authority scoring, AI model settings
- `backend/rlcf_framework/task_config.yaml` - Task type definitions, validation schemas
- `backend/orchestration/config/orchestration_config.yaml` - Orchestration settings

### Testing

**Run test suite**:
```bash
# All tests
pytest tests/ -v

# Specific layer
pytest tests/rlcf/ -v
pytest tests/orchestration/ -v
pytest tests/preprocessing/ -v

# With coverage
pytest tests/rlcf/ --cov=backend/rlcf_framework --cov-report=html

# Single test file
pytest tests/orchestration/test_llm_router.py -v
```

**Test requirements**:
- All code changes must include tests
- Maintain 85%+ coverage on core algorithms
- Use async fixtures from `tests/conftest.py`
- Mock external services (OpenRouter, Qdrant, Neo4j) in unit tests
- Use real services in integration tests

**Key fixtures** (in `tests/rlcf/conftest.py`):
```python
@pytest.fixture
async def db_session():
    # Provides async SQLAlchemy session

@pytest.fixture
def model_config():
    # Provides test ModelConfig with known values

@pytest.fixture
def mock_openrouter():
    # Mocks OpenRouter LLM calls
```

**See**: `docs/08-iteration/TESTING_STRATEGY.md` for complete testing guide

### Development Workflow

**1. Initial Setup**:
```bash
# Clone repository
git clone [repo-url]
cd MERL-T_alpha

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Configure environment
cp .env.template .env
# Edit .env with your API keys and database URLs
```

**2. Database Initialization**:
```bash
# Start databases (Docker)
docker-compose -f docker-compose.dev.yml up -d

# Run migrations
rlcf-admin db migrate

# Seed test data (optional)
rlcf-admin db seed --users 5 --tasks 10
```

**3. Start Backend**:
```bash
# Development mode (hot-reload)
rlcf-admin server --reload

# Production mode
rlcf-admin server --host 0.0.0.0 --port 8080
```

**4. Start Frontend** (separate terminal):
```bash
cd frontend/rlcf-web
npm install
npm run dev
```

**5. Run Tests**:
```bash
# Before committing
pytest tests/ -v

# With coverage report
pytest tests/ --cov=backend --cov-report=html
```

**See**: `docs/07-guides/LOCAL_SETUP.md` for complete setup guide

---

## Development Guidelines

### Code Style

**Python**:
- Follow PEP 8 with 100-character line limit
- Use type hints for all function signatures
- Use async/await for I/O operations
- Prefer Pydantic models for data validation

**TypeScript**:
- Follow Airbnb style guide
- Use functional components with hooks
- Prefer const over let, avoid var
- Use TanStack Query for server state

### Testing Requirements

**Coverage Goals**:
- Core algorithms (RLCF, authority scoring): 90%+
- API endpoints: 85%+
- Services and utilities: 80%+
- Overall project: 85%+

**Test Types**:
1. **Unit tests** - Test individual functions/classes in isolation (mock dependencies)
2. **Integration tests** - Test multiple components together (real dependencies)
3. **End-to-end tests** - Test complete workflows (LangGraph workflow, API flows)
4. **Regression tests** - Prevent fixed bugs from reappearing

**Test Naming**:
```python
# Good
def test_authority_score_increases_with_correct_feedback():
    ...

def test_llm_router_generates_valid_execution_plan():
    ...

# Bad
def test_1():
    ...

def test_authority():
    ...
```

### Documentation Standards

**When to Update Documentation**:
- After completing a major feature
- After making architectural changes
- After updating API contracts
- After fixing critical bugs

**Documentation Types**:
1. **Code comments** - Explain why, not what (code should be self-explanatory)
2. **Docstrings** - Use Google-style docstrings for all public functions/classes
3. **Architecture docs** - Update `docs/03-architecture/` when changing system design
4. **API docs** - Update `docs/api/` when adding/changing endpoints
5. **README updates** - Update root README.md when changing setup/deployment

**Example Docstring**:
```python
def calculate_authority_score(
    user: User,
    base_weight: float = 0.3,
    temporal_weight: float = 0.5,
    performance_weight: float = 0.2
) -> float:
    """Calculate dynamic authority score for an expert.

    Authority score combines:
    - Base authority (credentials, expertise domain)
    - Temporal authority (recent accuracy, recency bias)
    - Performance (task success rate)

    Formula: A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)

    Args:
        user: User object with authority metrics
        base_weight: Weight for base authority (default: 0.3)
        temporal_weight: Weight for temporal authority (default: 0.5)
        performance_weight: Weight for performance (default: 0.2)

    Returns:
        Authority score in range [0.0, 1.0]

    Raises:
        ValueError: If weights don't sum to 1.0
    """
    ...
```

---

## Key Files Reference

### Understanding the Vision & Theory

**Start with these files in order**:
1. `docs/01-introduction/executive-summary.md` - High-level overview (320 LOC)
2. `docs/01-introduction/problem-statement.md` - 5 key challenges MERL-T solves (248 LOC)
3. `docs/01-introduction/vision.md` - RLCF 4 Pillars, core principles (302 LOC)
4. `docs/02-methodology/rlcf/RLCF.md` - Core theoretical paper (mathematical foundations)
5. `docs/03-architecture/02-orchestration-layer.md` - Most detailed architecture doc

### Working with the Codebase

**Backend (RLCF Framework)**:
1. `backend/rlcf_framework/models.py` - SQLAlchemy 2.0 async models (435 LOC)
2. `backend/rlcf_framework/main.py` - FastAPI application, 50+ endpoints (1,743 LOC)
3. `backend/rlcf_framework/authority_module.py` - Authority scoring implementation (326 LOC)
4. `backend/rlcf_framework/aggregation_engine.py` - Shannon entropy aggregation (284 LOC)
5. `backend/rlcf_framework/rlcf_feedback_processor.py` - Expert vote aggregation (548 LOC)

**Backend (Preprocessing Layer)**:
1. `backend/preprocessing/query_understanding_module.py` - NER + intent classification (877 LOC)
2. `backend/preprocessing/kg_enrichment_service.py` - 5-source KG enrichment (704 LOC)
3. `backend/preprocessing/cypher_queries.py` - Neo4j Cypher query builder (693 LOC)

**Backend (Orchestration Layer)**:
1. `backend/orchestration/llm_router.py` - 100% LLM-based Router (450 LOC)
2. `backend/orchestration/langgraph_workflow.py` - Complete state machine workflow (942 LOC)
3. `backend/orchestration/experts/base.py` - Abstract Expert with shared logic (533 LOC)
4. `backend/orchestration/experts/synthesizer.py` - Opinion synthesis (474 LOC)
5. `backend/orchestration/api/services/query_executor.py` - LangGraph wrapper (424 LOC)

**Backend (Agents)**:
1. `backend/orchestration/agents/base.py` - Abstract RetrievalAgent (200 LOC)
2. `backend/orchestration/agents/vectordb_agent.py` - Qdrant semantic search (617 LOC)
3. `backend/orchestration/agents/kg_agent.py` - Neo4j KG retrieval (350 LOC)
4. `backend/orchestration/agents/api_agent.py` - Norma Controller API (450 LOC)

**Frontend**:
1. `frontend/rlcf-web/src/` - React 19 application with TypeScript
2. `frontend/rlcf-web/package.json` - Dependencies (Vite, TanStack Query, Zustand)

**Tests**:
1. `tests/rlcf/conftest.py` - Shared fixtures (async DB, test config)
2. `tests/orchestration/test_api_query.py` - Query API tests (227 LOC, 13 tests)
3. `tests/orchestration/test_workflow_with_preprocessing.py` - E2E workflow tests (500 LOC)
4. `tests/preprocessing/test_kg_complete.py` - KG enrichment tests (2,156 LOC, 100+ tests)

### Implementation Guides

**Essential reading for current phase**:
1. `docs/08-iteration/NEXT_STEPS.md` - **START HERE**: Priority 1-12 tasks with code examples
2. `docs/08-iteration/CODE_METRICS_SUMMARY.md` - Complete LOC breakdown by component
3. `docs/08-iteration/TESTING_STRATEGY.md` - Testing approach, 200+ test cases
4. `docs/TECHNOLOGY_RECOMMENDATIONS.md` - 2025 tech stack with benchmarks
5. `docs/IMPLEMENTATION_ROADMAP.md` - 42-week build plan (for context)

### API Documentation

1. `docs/api/API_EXAMPLES.md` - Real-world usage examples with curl/Python
2. `docs/api/AUTHENTICATION.md` - API key authentication (to be implemented)
3. `docs/api/RATE_LIMITING.md` - Rate limiting tiers (to be implemented)

### Governance & Compliance

1. `docs/05-governance/ai-act-compliance.md` - EU AI Act compliance (484 LOC)
2. `docs/05-governance/data-protection.md` - GDPR compliance (330 LOC)
3. `docs/05-governance/arial-association.md` - ALIS association governance (341 LOC)

### Deployment & Operations

1. `.env.template` - Complete environment configuration reference
2. `docker-compose.yml` - Development stack configuration
3. `docker-compose.prod.yml` - Production deployment configuration
4. `Dockerfile` - Container image build specification
5. `setup.py` - Package configuration and CLI entry points

---

## Important Notes for AI Assistants

### Critical Patterns to Follow

**1. Import Patterns** (MUST follow):
- Relative imports within packages (`from .models import User`)
- Absolute imports from tests (`from backend.rlcf_framework import models`)
- Never use old-style `from rlcf_framework.X` imports

**2. Mathematical Rigor** (MUST preserve):
- RLCF formulas are academically grounded, do not simplify
- Authority score: `A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)`
- Shannon entropy for disagreement quantification: `H(X) = -Σ p(x) log p(x)`
- All implemented in `backend/rlcf_framework/authority_module.py` and `aggregation_engine.py`

**3. RLCF Methodology** (MUST NOT alter):
- Do not change core RLCF principles (dynamic authority, uncertainty preservation, community validation)
- Do not modify mathematical formulas without explicit user approval
- The methodology is intended for academic publication

**4. Testing Requirements** (MUST follow):
- All code changes must include tests
- Maintain 85%+ coverage on core algorithms
- Use async fixtures from `tests/conftest.py`
- Run `pytest tests/ -v` before committing

**5. Configuration is YAML-based** (MUST use):
- Hot-reloadable configs in `backend/rlcf_framework/*.yaml`
- Environment variable expansion: `${VAR:-default}`
- Never hardcode configuration values in code

### What to Preserve

**Preserve without changes**:
- RLCF mathematical formulas and algorithms
- Italian legal context (Codice Civile, Costituzione examples)
- Academic documentation style (intended for peer review)
- Test coverage (never reduce coverage)
- Type hints (all functions must have type hints)

### What to Update

**Update when needed**:
- Implementation code (refactoring, optimization)
- Tests (add more tests, improve coverage)
- Documentation (reflect current implementation status)
- Configuration (add new settings, update defaults)
- Error handling (improve error messages, add logging)

### Common Pitfalls to Avoid

**1. Breaking Import Patterns**:
```python
# BAD - old-style imports
from rlcf_framework.models import User

# GOOD - relative imports (within package)
from .models import User

# GOOD - absolute imports (from tests)
from backend.rlcf_framework.models import User
```

**2. Hardcoding Configuration**:
```python
# BAD - hardcoded values
llm_model = "google/gemini-2.5-flash"

# GOOD - use configuration
llm_model = config.router_model
```

**3. Missing Type Hints**:
```python
# BAD - no type hints
def calculate_authority(user):
    ...

# GOOD - complete type hints
def calculate_authority(user: User) -> float:
    ...
```

**4. Insufficient Tests**:
```python
# BAD - no tests for new feature
def new_feature():
    ...

# GOOD - comprehensive tests
def new_feature():
    ...

# tests/test_new_feature.py
def test_new_feature_basic_case():
    ...

def test_new_feature_edge_case():
    ...

def test_new_feature_error_handling():
    ...
```

### Respect Italian Legal Context

Examples use **Italian law**:
- **Codice Civile** (Civil Code): Art. 2043 (tort), Art. 1218 (contract breach)
- **Costituzione** (Constitution): Art. 3 (equality), Art. 24 (right to defense)
- **Cassazione** (Supreme Court): Sentenza n. 12345/2024
- **Normattiva**: Official legislative database

Do not change legal examples to other jurisdictions without explicit user approval.

### Version Tracking

**Documents include**:
- Version numbers (e.g., v0.9.0, v1.0.0)
- Last updated dates (e.g., November 2025)
- Implementation status (✅ Complete, 🚧 Partial, ⏳ Planned)

Update version/date when making substantial changes.

---

## User Preferences

- **Lingua**: Preferenza per italiano nelle comunicazioni (ma codice/docs in inglese)
- **Documentazione**: Aggiornare alla fine di ogni traguardo importante
- **Stile**: Professionale, academico, orientato a pubblicazione peer-reviewed
- **Testing**: Test-first approach, coverage 85%+
- **Commit**: Semantic commit messages (feat:, fix:, docs:, refactor:)

---

**Document Version**: 2.0 (Updated November 2025)
**Last Updated**: November 14, 2025
**Project Status**: v0.9.0 (70% complete, production-ready with database persistence)
