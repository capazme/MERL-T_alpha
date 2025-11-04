# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MERL-T (Multi-Expert Legal Retrieval Transformer)** is an AI-powered architecture for legal research, compliance monitoring, and regulatory analysis. Sponsored by ALIS (Artificial Legal Intelligence Society), this repository contains both **comprehensive technical documentation** and **working implementation code**.

**Current Status**: **Phase 1 Complete** (RLCF Core + Learning Layer)

This repository includes:
- **Comprehensive documentation** (architectural specifications, research papers, technical designs)
- **Working RLCF implementation** (backend, frontend, tests - Phase 1)
- **CLI tools** for administration and user operations
- **Docker configuration** for development and production deployment
- **Test suite** with 2,278 lines of test code and 85%+ coverage

## Repository Structure

### Implementation Code (Phase 1 - Complete)

```
MERL-T_alpha/
├── backend/
│   └── rlcf_framework/        # RLCF Core implementation (1,734 lines)
│       ├── models.py           # SQLAlchemy 2.0 async models
│       ├── schemas.py          # Pydantic validation schemas
│       ├── main.py             # FastAPI application (50+ endpoints)
│       ├── authority_module.py # Authority scoring (A_u(t) formula)
│       ├── aggregation_engine.py # Uncertainty-preserving aggregation
│       ├── bias_analysis.py    # Bias detection algorithms
│       ├── ai_service.py       # OpenRouter LLM integration
│       ├── database.py         # Async DB setup
│       ├── config.py           # YAML configuration loader
│       ├── cli/                # CLI tools (rlcf-cli, rlcf-admin)
│       ├── task_handlers/      # Polymorphic task handlers
│       └── services/           # Shared services
├── frontend/
│   └── rlcf-web/               # React 19 application
│       ├── src/                # TypeScript source code
│       ├── components/         # React components
│       └── package.json        # Vite + TanStack Query + Zustand
├── tests/
│   └── rlcf/                   # Test suite (2,278 lines, 85%+ coverage)
│       ├── test_authority_module.py
│       ├── test_aggregation_engine.py
│       ├── test_bias_analysis.py
│       ├── test_models.py
│       └── conftest.py
├── docs/                       # Comprehensive documentation
│   ├── 01-introduction/
│   ├── 02-methodology/
│   ├── 03-architecture/
│   ├── 04-implementation/
│   ├── 05-governance/
│   ├── 06-resources/
│   ├── IMPLEMENTATION_ROADMAP.md
│   └── TECHNOLOGY_RECOMMENDATIONS.md
├── infrastructure/             # Deployment configs
├── scripts/                    # Development scripts
├── setup.py                    # Package configuration
├── requirements.txt            # Python dependencies
├── .env.template               # Environment configuration template
├── Dockerfile                  # Production container image
├── docker-compose.yml          # Development stack
├── docker-compose.prod.yml     # Production deployment
└── README.md                   # Project documentation
```

### Documentation Structure

The `docs/` directory contains comprehensive technical documentation organized into 6 sections:

- **`docs/01-introduction/`** - Executive summary, vision, problem statement
- **`docs/02-methodology/`** - Core methodologies including RLCF framework, knowledge graphs, vector databases, legal reasoning
- **`docs/03-architecture/`** - 5-layer system architecture (preprocessing, orchestration, reasoning, storage, learning)
- **`docs/04-implementation/`** - Implementation blueprints for API gateway, LLM integration, databases, deployment
- **`docs/05-governance/`** - AI Act compliance, data protection, ALIS association governance
- **`docs/06-resources/`** - API references, bibliography, datasets

## Key Concepts

### RLCF Framework (Reinforcement Learning from Community Feedback)

The centerpiece methodology located in `docs/02-methodology/rlcf/`. RLCF is a novel alignment approach for legal AI that differs from traditional RLHF by:

- **Dynamic Authority Scoring**: Expert influence based on demonstrated competence, not just credentials
- **Uncertainty Preservation**: Disagreement among experts is valuable information, not noise
- **Community-Driven Validation**: Distributed expert feedback with transparent aggregation
- **Mathematical Rigor**: Formally defined authority scores, aggregation algorithms, and bias detection

Key RLCF documentation:
- `docs/02-methodology/rlcf/RLCF.md` - Core theoretical paper
- `docs/02-methodology/rlcf/technical/architecture.md` - System architecture
- `docs/02-methodology/rlcf/guides/quick-start.md` - Getting started guide
- `docs/02-methodology/rlcf/testing/MANUAL_TESTING_GUIDE.md` - Testing procedures

### System Architecture (5 Layers)

1. **Preprocessing Layer** - Query understanding, NER, intent classification, KG enrichment
2. **Orchestration Layer** - LLM Router (100% LLM-based decision engine), retrieval agents (KG, API, VectorDB)
3. **Reasoning Layer** - 4 expert types (Literal Interpreter, Systemic-Teleological, Principles Balancer, Precedent Analyst), Synthesizer
4. **Storage Layer** - PostgreSQL, Neo4j (knowledge graph), ChromaDB/Weaviate (vectors), Redis (cache)
5. **Learning Layer** - RLCF feedback loops, model fine-tuning, A/B testing

Key architecture files:
- `docs/03-architecture/02-orchestration-layer.md` - Detailed orchestration design (100+ pages)
- `docs/03-architecture/03-reasoning-layer.md` - Expert system design

### Technology Stack

**Backend**: FastAPI (async/await), SQLAlchemy 2.0, Pydantic 2.5, Click (CLI)
**Databases**: SQLite (dev), PostgreSQL (prod), Memgraph (graph - Phase 2+), Qdrant (vectors - Phase 3+), Redis (cache - Phase 2+)
**Frontend**: React 19, Vite, TypeScript, TailwindCSS, TanStack Query, Zustand
**AI/ML**: OpenRouter (LLM provider), NumPy, SciPy (RLCF algorithms), LangGraph (Phase 3+)
**Infrastructure**: Docker, Docker Compose, Kubernetes, GitHub Actions
**Development**: pytest, pytest-asyncio, Gradio (admin interface)

## Working with the Codebase

### Import Patterns (CRITICAL)

The repository uses a **monorepo structure** with specific import conventions:

**Backend internal imports** (within `backend/rlcf_framework/`):
```python
# Use RELATIVE imports
from .models import User, LegalTask
from .config import load_model_config
from . import authority_module
```

**Test imports** (from `tests/rlcf/`):
```python
# Use ABSOLUTE imports with backend prefix
from backend.rlcf_framework import models
from backend.rlcf_framework.authority_module import calculate_authority_score
from backend.rlcf_framework.database import SessionLocal
```

**Why this pattern?**
- Relative imports within the package ensure modularity
- Absolute imports from tests allow proper package resolution
- Supports both `pip install -e .` and direct Python execution

### CLI Tools

The repository provides two CLI entry points defined in `setup.py`:

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

**Implementation**: `backend/rlcf_framework/cli/commands.py` (507 lines)

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
- `neo4j`: Memgraph/Neo4j (Phase 2+, profile-based)
- `redis`: Redis 7 (Phase 2+, profile-based)
- `qdrant`: Vector database (Phase 3+, profile-based)

### Configuration Management

**Environment variables**: Copy `.env.template` to `.env` and fill in:
- `OPENROUTER_API_KEY`: AI model API key
- `ADMIN_API_KEY`: Admin endpoint protection
- `DATABASE_URL`: Database connection string
- RLCF parameters (authority weights, thresholds)

**YAML configuration files** (hot-reloadable):
- `backend/rlcf_framework/model_config.yaml`: Authority scoring, AI model settings
- `backend/rlcf_framework/task_config.yaml`: Task type definitions, validation schemas

Edit via:
- Gradio admin interface
- API endpoints (`PUT /config/model`, `PUT /config/tasks`)
- Direct file editing (auto-reloads on change)

### Testing

**Run test suite**:
```bash
pytest tests/rlcf/ -v
pytest tests/rlcf/ --cov=backend/rlcf_framework --cov-report=html
pytest tests/rlcf/test_authority_module.py -v
```

**Test structure**:
- `tests/rlcf/conftest.py`: Shared fixtures (async DB, test config)
- `tests/rlcf/test_*.py`: Test modules (2,278 lines total)
- Coverage: 85%+ on core RLCF algorithms

**Key fixtures**:
```python
@pytest.fixture
async def db_session():
    # Provides async SQLAlchemy session

@pytest.fixture
def model_config():
    # Provides test ModelConfig with known values
```

### Development Workflow

1. **Setup**:
   ```bash
   pip install -e .
   cp .env.template .env
   # Edit .env with your API keys
   ```

2. **Database initialization**:
   ```bash
   rlcf-admin db migrate
   rlcf-admin db seed --users 5 --tasks 10
   ```

3. **Start backend**:
   ```bash
   rlcf-admin server --reload
   ```

4. **Start frontend** (separate terminal):
   ```bash
   cd frontend/rlcf-web
   npm install
   npm run dev
   ```

5. **Run tests**:
   ```bash
   pytest tests/rlcf/ -v
   ```

## Documentation Conventions

### File Naming & Organization

- Documentation files use kebab-case: `knowledge-graph.md`, `rlcf-pipeline.md`
- Numbered prefixes for sequential reading: `01-preprocessing-layer.md`, `02-orchestration-layer.md`
- UPPERCASE for important guides: `RLCF.md`, `README.md`, `MANUAL_TESTING_GUIDE.md`

### Document Structure

Most technical documents follow this structure:
1. **Status/Metadata** - Implementation status, layer, dependencies, technologies
2. **Table of Contents** - Section navigation
3. **Overview** - High-level description
4. **Architecture/Design** - Detailed specifications with diagrams
5. **Implementation Details** - Code examples, schemas, APIs
6. **Performance/Metrics** - Latency targets, resource requirements
7. **Cross-References** - Links to related documents

### Code Examples in Documentation

Documentation includes extensive code examples in multiple languages:
- **Python**: FastAPI services, SQLAlchemy models, async/await patterns
- **YAML**: Configuration files, Docker Compose, Kubernetes manifests
- **Cypher**: Neo4j graph queries
- **JSON**: API schemas, request/response formats
- **SQL**: Database schemas and queries
- **Bash**: Command-line operations, testing scripts

## Common Documentation Tasks

### Updating Architecture Diagrams

Architecture diagrams are ASCII art in markdown code blocks:
```
┌────────────────────┐
│   Component Name   │
└──────────┬─────────┘
           ↓
    Next Component
```

When updating diagrams:
- Maintain consistent box widths and alignment
- Use Unicode box-drawing characters (├ ─ │ └ ┌ ┐ ┘)
- Include arrows (↓ → ←) to show data flow
- Keep diagrams under 80 characters wide for readability

### Adding New Documentation

When adding new technical documents:
1. Place in appropriate section (01-06)
2. Follow the standard structure (status, TOC, overview, etc.)
3. Include cross-references to related documents
4. Add mathematical formulas using LaTeX notation ($$ ... $$)
5. Provide code examples with syntax highlighting
6. Update parent README.md files with links to new content

### Referencing Implementation Patterns

The documentation describes implementation patterns without actual code:
- **Abstract interfaces** - JSON schema specifications for components
- **API contracts** - Request/response formats, endpoint definitions
- **Database schemas** - Table structures, relationships, indexes
- **Service configurations** - Environment variables, Docker settings, Kubernetes manifests

## Cross-References Between Documents

Key cross-reference patterns:

**From Architecture → Methodology**:
- Orchestration layer references `docs/02-methodology/legal-reasoning.md` for LLM Router design
- Storage layer references `docs/02-methodology/knowledge-graph.md` for Neo4j schema

**From Implementation → Architecture**:
- `docs/04-implementation/07-rlcf-pipeline.md` implements `docs/03-architecture/05-learning-layer.md`
- Deployment blueprints reference all architecture layers

**Within RLCF Framework**:
- Theoretical → Technical → Guides → Examples (progressive detail)
- All reference the core `RLCF.md` paper for mathematical foundations

## AI Act Compliance & Legal Context

The system is designed for **EU AI Act compliance** as a high-risk AI system (legal assistance domain):
- Transparency requirements: Full traceability via trace IDs
- Human oversight: Community feedback loops
- Accuracy requirements: Multi-expert validation
- Bias detection: Built into RLCF aggregation

See `docs/05-governance/ai-act-compliance.md` for details.

## Implementation Guides (NEW - Nov 2025)

**CRITICAL**: Two new comprehensive guides have been added for transitioning from documentation to implementation:

### Implementation Roadmap
**File**: `docs/IMPLEMENTATION_ROADMAP.md`

Complete 42-week implementation plan with:
- **7 phases** from setup to production launch
- **Deliverables** and tasks for each phase with time estimates
- **Team requirements**: 8-10 people, skills matrix
- **Budget estimate**: €663,000 (10 months)
- **Risk management** strategies
- **Build-Measure-Learn** approach for complex project management
- **Vertical slice architecture** pattern
- Concrete code examples and checklist per phase

**Start here** if you need to understand how to build the system step-by-step.

### Technology Recommendations
**File**: `docs/TECHNOLOGY_RECOMMENDATIONS.md`

State-of-the-art technology choices for 2025 based on performance benchmarks:
- **LangGraph** for orchestration (vs LangChain)
- **Qdrant** for vector DB (30-40ms latency, beats Weaviate)
- **Memgraph** for graph DB (10-25x faster than Neo4j!)
- **Voyage Multilingual 2** embeddings (SOTA for Italian)
- **ITALIAN-LEGAL-BERT** for legal NLP
- **SigNoz** for observability (open-source alternative to Datadog)
- Detailed cost analysis: €2,450/month (self-hosted) vs €3,650/month (managed)
- Code examples for each technology
- Decision matrices and migration paths

**Consult this** when making architectural technology decisions.

## Important Notes for AI Assistants

1. **Phase 1 is implemented** - RLCF Core (backend, frontend, tests) is complete and working
   - Backend: 1,734 lines of FastAPI code in `backend/rlcf_framework/`
   - Frontend: React 19 application in `frontend/rlcf-web/`
   - Tests: 2,278 lines in `tests/rlcf/` with 85%+ coverage
   - CLI: Two entry points (`rlcf-cli`, `rlcf-admin`) with full command set
   - Docker: Development and production configurations ready

2. **Import patterns are critical** - Follow the monorepo conventions:
   - **Relative imports** within `backend/rlcf_framework/` (e.g., `from .models import User`)
   - **Absolute imports** from tests (e.g., `from backend.rlcf_framework import models`)
   - Never use old-style `from rlcf_framework.X` imports

3. **Preserve mathematical rigor** - RLCF formulas and algorithms are academically grounded
   - Authority score: `A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)`
   - Aggregation uses Shannon entropy for disagreement quantification
   - All implemented in `backend/rlcf_framework/authority_module.py` and `aggregation_engine.py`

4. **Maintain cross-references** - When updating one document, check for references in others

5. **Respect Italian legal context** - Examples use Italian law (Codice Civile, Costituzione)

6. **Version tracking** - Documents include version numbers and last updated dates

7. **Academic style** - Documentation is intended for peer review and publication

8. **Technology choices** - Refer to TECHNOLOGY_RECOMMENDATIONS.md for 2025 state-of-the-art stack

9. **Testing is mandatory** - All code changes must include tests
   - Use async fixtures from `tests/rlcf/conftest.py`
   - Maintain 85%+ coverage on core algorithms
   - Run `pytest tests/rlcf/ -v` before committing

10. **Configuration is YAML-based** - Hot-reloadable configs in `backend/rlcf_framework/*.yaml`

## Key Files to Understand the System

### For Understanding the Vision & Theory
Start with these files in order:
1. `docs/01-introduction/executive-summary.md` - High-level overview
2. `docs/02-methodology/rlcf/README.md` - RLCF framework navigation
3. `docs/02-methodology/rlcf/RLCF.md` - Core theoretical paper (mathematical foundations)
4. `docs/03-architecture/02-orchestration-layer.md` - Most detailed architecture doc (100+ pages)
5. `docs/02-methodology/rlcf/guides/quick-start.md` - Practical usage guide

### For Working with the Codebase (Phase 1)
**Start here if you want to understand or modify the implementation**:
1. `README.md` - Quick start, architecture overview, development guide
2. `INTEGRATION_TEST_REPORT.md` - Complete validation of Phase 1 implementation
3. `backend/rlcf_framework/models.py` - Database models (SQLAlchemy 2.0)
4. `backend/rlcf_framework/main.py` - FastAPI application (50+ endpoints)
5. `backend/rlcf_framework/authority_module.py` - Authority scoring implementation
6. `backend/rlcf_framework/aggregation_engine.py` - Uncertainty-preserving aggregation
7. `backend/rlcf_framework/cli/commands.py` - CLI tools implementation
8. `tests/rlcf/` - Test suite (read `conftest.py` first for fixtures)

### For Implementation & Building Future Phases
**Essential reading for Phases 2-7**:
1. `docs/IMPLEMENTATION_ROADMAP.md` - **START HERE**: Complete 42-week build plan
2. `docs/TECHNOLOGY_RECOMMENDATIONS.md` - Modern tech stack with benchmarks (2025)
3. `docs/04-implementation/07-rlcf-pipeline.md` - RLCF implementation blueprint
4. `docs/02-methodology/rlcf/testing/MANUAL_TESTING_GUIDE.md` - Testing procedures

### For Deployment & Operations
1. `.env.template` - Complete environment configuration reference
2. `docker-compose.yml` - Development stack configuration
3. `docker-compose.prod.yml` - Production deployment configuration
4. `Dockerfile` - Container image build specification
5. `setup.py` - Package configuration and CLI entry points
