# MERL-T: Multi-Expert Legal Retrieval Transformer

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Phase](https://img.shields.io/badge/Phase-Week%209%20Complete-brightgreen.svg)](CHANGELOG.md)
[![Coverage](https://img.shields.io/badge/Coverage-85%25%2B-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/Tests-200%2B%20Cases-blue.svg)](tests/)

**MERL-T** is an AI-powered architecture for legal research, compliance monitoring, and regulatory analysis. Sponsored by **ALIS** (Artificial Legal Intelligence Society), it implements a novel **RLCF (Reinforcement Learning from Community Feedback)** framework for aligning legal AI systems with expert knowledge.

**📚 Documentation**: [Architecture](ARCHITECTURE.md) | [API Docs](docs/api/) | [Contributing](CONTRIBUTING.md) | [Changelog](CHANGELOG.md) | [Security](SECURITY.md)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- Node.js 18+ and npm (for frontend)
- Git

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/ALIS/MERL-T_alpha.git
cd MERL-T_alpha

# 2. Install backend dependencies
pip install -e .

# 3. Run database migrations
rlcf-admin db migrate

# 4. Seed demo data (optional)
rlcf-admin db seed --users 5 --tasks 10

# 5. Start backend server
rlcf-admin server --reload

# 6. (In another terminal) Start frontend
cd frontend/rlcf-web
npm install
npm run dev
```

**Access the application**:
- Backend API: http://localhost:8000/docs
- Frontend: http://localhost:3000
- Gradio Admin: `python backend/rlcf_framework/app_interface.py`

---

## 📋 What is MERL-T?

MERL-T (Multi-Expert Legal Retrieval Transformer) is a comprehensive system for legal AI that:

1. **Retrieves** relevant legal information from multiple sources (norms, case law, doctrine)
2. **Reasons** using multiple legal methodologies (literal, systemic-teleological, principles-based, precedent-based)
3. **Learns** from community feedback using a novel RLCF framework
4. **Complies** with EU AI Act requirements for high-risk legal AI systems

### Key Innovation: RLCF Framework

**Reinforcement Learning from Community Feedback (RLCF)** differs from traditional RLHF by:

- **Dynamic Authority Scoring**: Expert influence based on demonstrated competence, not just credentials
- **Uncertainty Preservation**: Disagreement among experts is valuable information, not noise
- **Community-Driven Validation**: Distributed expert feedback with transparent aggregation
- **Mathematical Rigor**: Formally defined authority scores, aggregation algorithms, and bias detection

📖 **Read the full RLCF paper**: [`docs/02-methodology/rlcf/RLCF.md`](docs/02-methodology/rlcf/RLCF.md)

### 📄 Scientific Papers

**NEW**: We have published two complementary academic papers:

#### 1. Architecture & Epistemology (Theoretical Foundation)

📄 **[Operationalizing Legal Epistemology: A Multi-Expert Pipeline Architecture for Trustworthy Legal AI](docs/MERL-T_Architecture_Paper.md)** (~14 pages)

**Focus**: Theoretical foundations and architectural design principles

The paper develops:
- **Epistemic Analysis**: Law's dual structure (principles vs. rules) and implications for AI design
- **Knowledge Graph Theory**: Formal model as epistemic structure with typed relationships
- **Multi-Expert Framework**: Why 4 specialized experts (not 1 monolith), grounded in legal philosophy
- **Orchestration Theory**: LLM-based deliberative planning vs. traditional gating networks
- **Synthesis Logic**: Convergent vs. divergent modes for preserving epistemic plurality
- **Comparative Analysis**: Why this architecture is theoretically necessary

**Target Audience**: AI researchers, legal scholars, system architects
**Suitable for**: *Artificial Intelligence and Law*, *Journal of Legal Analysis*, *AI* journal

#### 2. Complete System & Validation (Implementation)

📄 **[MERL-T: A Multi-Expert Architecture for Trustworthy Artificial Legal Intelligence](docs/MERL-T_Scientific_Paper.md)** (7 pages)

**Focus**: Complete system description with empirical validation

The paper covers:
- **RLCF Framework**: Mathematical formulation with dynamic authority scoring
- **5-Layer Architecture**: Preprocessing, Orchestration, Reasoning, Storage, Learning
- **4 Expert Types**: Literal Interpreter, Systemic-Teleological, Principles Balancer, Precedent Analyst
- **Empirical Results**: 34% improvement in factual grounding (97% claim traceability), 40% increase in practitioner trust
- **EU AI Act Compliance**: Responsible-by-design approach for high-risk legal systems

**Target Audience**: Practitioners, implementers, applied researchers

### 🎬 Interactive RLCF Simulation

Want to see RLCF in action? Try our **interactive end-to-end simulation** that visualizes the complete workflow:

🔗 **[Open simulation.html](./simulation.html)** (just open the file in your browser!)

The simulation demonstrates:
- ✅ Legal task creation and expert matching
- ✅ Multi-expert feedback collection with varying authority levels
- ✅ Real-time authority score calculation using the RLCF formula
- ✅ Uncertainty-preserving aggregation with Shannon entropy
- ✅ Automated bias detection and mitigation strategies
- ✅ Final output with full EU AI Act compliance traceability

**Features**:
- 6 interactive steps with animated transitions
- Live Chart.js visualizations of authority scores, consensus, and bias
- Auto-play mode for presentations
- Real case study: Italian civil law (autonomous vehicle accident)
- No installation required - runs in any modern browser

📖 **Full guide**: [`docs/02-methodology/rlcf/guides/simulation-guide.md`](docs/02-methodology/rlcf/guides/simulation-guide.md)

---

## 🏗️ System Architecture

MERL-T is designed as a **5-layer architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│  1. PREPROCESSING LAYER                                     │
│     Query understanding, NER, intent classification          │
│     Knowledge Graph enrichment                               │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  2. ORCHESTRATION LAYER                                     │
│     LLM Router (100% LLM-based decision engine)             │
│     Retrieval Agents: KG, API, VectorDB                     │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  3. REASONING LAYER                                         │
│     4 Expert Types: Literal, Systemic, Principles, Precedent│
│     Synthesizer (convergent / divergent modes)              │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  4. STORAGE LAYER                                           │
│     PostgreSQL, Memgraph (graph), Qdrant (vectors), Redis   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  5. LEARNING LAYER (RLCF)                                   │
│     Feedback collection, Authority scoring, Aggregation      │
│     Model fine-tuning, A/B testing                          │
└─────────────────────────────────────────────────────────────┘
```

**Current Status**: **Phase 1 Complete** (RLCF Core) + **Phase 2 Week 3 Complete** (KG Enrichment + Pipeline Integration)
- ✅ Phase 1: 100% Complete (15,635 LOC)
- ✅ Phase 2 Week 3: 60% Complete (9,000 LOC)
  - ✅ Multi-source KG enrichment (Normattiva, Cassazione, Dottrina, Community, RLCF)
  - ✅ Full pipeline orchestration (Intent → KG → RLCF → Feedback)
  - ✅ RLCF feedback processor with authority weighting
  - ✅ NER feedback learning loop
  - ✅ 150+ new test cases with 3,000+ LOC
**Next**: Phase 2 Query Understanding (NER/Intent refinement) + Phase 3 Orchestration (LLM Router, Agents)

📖 **Full architecture docs**: [`docs/03-architecture/`](docs/03-architecture/)

---

## 🧪 RLCF Framework (Phase 1 - Complete)

### What's Implemented

✅ **Core RLCF Algorithms**:
- Dynamic authority scoring (`A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)`)
- Uncertainty-preserving aggregation (Algorithm 1 from RLCF paper)
- Disagreement quantification (Shannon entropy-based)
- Track record evolution (exponential smoothing)

✅ **Backend (FastAPI)**:
- 50+ REST API endpoints
- SQLAlchemy 2.0 async models
- Task handlers (polymorphic design)
- Configuration-driven behavior (YAML)
- OpenRouter AI service integration

✅ **Frontend (React 19 + TypeScript)**:
- Modern stack: Vite, TanStack Query, Zustand, TailwindCSS
- Blind evaluation interface
- Analytics dashboard (authority leaderboard, system metrics)
- Configuration editor (YAML hot-reload)
- Dataset export (JSONL, CSV)

✅ **CLI Tools**:
- `rlcf-cli` (user commands: tasks, users, feedback)
- `rlcf-admin` (admin commands: config, db, server)

✅ **Testing**:
- 2,750+ lines of test code
- 85%+ coverage on core algorithms
- pytest + pytest-asyncio

✅ **Gradio Admin Interface**:
- Task creation (YAML, CSV upload)
- AI response generation
- Aggregation visualization
- Bias analysis reports
- Training cycle management

### Example: Creating a Legal QA Task

```bash
# Using CLI
rlcf-cli tasks create examples/qa_tasks.yaml

# Using API
curl -X POST "http://localhost:8000/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "QA",
    "input_data": {
      "question": "È valido un contratto firmato da un minorenne?",
      "context": "Diritto civile italiano"
    },
    "ground_truth_data": {
      "answer": "No, il contratto è annullabile per incapacità di agire (Art. 2 c.c.)"
    }
  }'
```

---

## ✨ Recent Updates (January 2025)

### 🎯 Task Types Alignment & RETRIEVAL_VALIDATION
**Status**: ✅ Complete

- **Aligned task types** with MERL-T methodology (11 official types)
- **Removed 6 undocumented types** that had no implementation
- **Added RETRIEVAL_VALIDATION** - new task type for validating KG/API/Vector retrieval quality
- **Complete implementation** with handler, config, tests, and documentation
- See [`docs/08-iteration/TASK_TYPES_COMPARISON.md`](docs/08-iteration/TASK_TYPES_COMPARISON.md) for details

### 🔧 Dynamic Configuration System
**Status**: ✅ Complete

A powerful hot-reload configuration system that enables:

✅ **Dynamic Task Type Management**:
- Create, update, delete task types **without server restart**
- API endpoints + manual YAML editing both supported
- Automatic validation with Pydantic schemas

✅ **Hot-Reload Support**:
- File watching with `watchdog` library
- Changes take effect immediately across all workers
- Thread-safe concurrent access

✅ **Safety Features**:
- Automatic backup before every modification (timestamped)
- Robust validation (invalid configs rejected)
- Rollback support via API
- Full audit trail of changes

✅ **API Endpoints**:
```bash
# Create new task type dynamically
POST /config/task/type

# Update existing task type
PUT /config/task/type/{name}

# List all backups
GET /config/backups

# Restore from backup
POST /config/backups/restore
```

**Quick Start**: [`docs/08-iteration/DYNAMIC_CONFIG_QUICKSTART.md`](docs/08-iteration/DYNAMIC_CONFIG_QUICKSTART.md)
**Full Documentation**: [`docs/04-implementation/DYNAMIC_CONFIGURATION.md`](docs/04-implementation/DYNAMIC_CONFIGURATION.md)
**Test Script**: `./scripts/test_dynamic_config.sh`

**Example - Add Custom Task Type:**
```bash
curl -X POST http://localhost:8000/config/task/type \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: $ADMIN_API_KEY" \
  -d '{
    "task_type_name": "CONTRACT_REVIEW",
    "schema": {
      "input_data": {"contract_text": "str"},
      "feedback_data": {"review_result": "str"},
      "ground_truth_keys": ["review_result"]
    }
  }'

# ✨ Immediately available for use - no restart needed!
```

### 🧪 Comprehensive Test Suite
**Status**: ✅ Complete

A robust test suite covering all Phase 1 components with **68 new test cases**:

✅ **Test Modules Created**:
- `test_config_manager.py` - ConfigManager unit tests (24 tests)
  - Singleton pattern and thread-safety
  - Hot-reload and file watching
  - Backup/restore functionality
  - Task type CRUD operations

- `test_config_router.py` - API endpoint tests (22 tests)
  - All REST endpoints (GET, POST, PUT, DELETE)
  - Authentication and authorization
  - Request/response validation
  - Error handling and edge cases

- `test_retrieval_validation_handler.py` - Handler tests (22 tests)
  - Authority-weighted aggregation
  - Consistency calculation (Jaccard similarity)
  - Correctness calculation (F1 scores)
  - Export formatting (SFT & Preference Learning)

✅ **Coverage**:
- **Overall**: ≥ 85% (Phase 1 requirement met)
- **ConfigManager**: ≥ 90%
- **Config Router**: ≥ 85%
- **RETRIEVAL_VALIDATION Handler**: ≥ 90%

✅ **Test Features**:
- Async/await testing with `pytest-asyncio`
- Integration testing with FastAPI TestClient
- Thread-safety validation
- Mock database sessions for unit tests
- Edge case and error handling coverage

**Run Tests**:
```bash
# All new tests
pytest tests/rlcf/test_config_manager.py \
       tests/rlcf/test_config_router.py \
       tests/rlcf/test_retrieval_validation_handler.py -v

# Full regression suite with coverage
pytest tests/rlcf/ -v --cov=backend/rlcf_framework --cov-report=html
```

**Testing Guide**: [`docs/08-iteration/TESTING_GUIDE.md`](docs/08-iteration/TESTING_GUIDE.md)

---

## 🚀 Recent Updates (November 2025 - Week 3)

### Knowledge Graph Enrichment System (Phase 2 Week 3)
**Status**: ✅ Complete

A comprehensive multi-source legal knowledge graph integration with 5 data sources:

✅ **KG Enrichment Service** (700 LOC):
- Async enrichment with Redis caching
- Multi-source aggregation: Normattiva (official norms), Cassazione (case law), Dottrina (academic doctrine), Community (crowdsourced), RLCF (consensus results)
- Dual-provenance tracking (PostgreSQL + Neo4j)
- Source-specific confidence scoring

✅ **Neo4j Integration** (500 LOC Cypher queries):
- 20+ Cypher query templates for entity resolution
- Temporal version management per source type
- Efficient graph traversal and aggregation

✅ **NER Feedback Loop** (500 LOC):
- 4 correction types: MISSING_ENTITY, SPURIOUS_ENTITY, WRONG_BOUNDARY, WRONG_TYPE
- Automatic training example generation from expert corrections
- Performance tracking (F1, precision, recall)
- Batch retraining coordination

✅ **Complete Test Coverage** (2,156 LOC, 100+ test cases):
- KG enrichment service tests
- Cypher query tests
- RLCF quorum detection
- Controversy flagging
- Community voting workflow tests

**Read more**: [`tests/preprocessing/KG_TEST_SUMMARY.md`](tests/preprocessing/KG_TEST_SUMMARY.md)

### Full Pipeline Integration (Phase 2 Week 3)
**Status**: ✅ Complete

End-to-end pipeline coordination for legal query processing:

✅ **Pipeline Orchestrator** (720 LOC):
- Async execution of 7 pipeline stages
- Intent Classification → KG Enrichment → RLCF Processing → Feedback Loops
- PipelineContext for state management across stages
- Comprehensive execution logging and error handling

✅ **RLCF Feedback Processor** (520 LOC):
- Expert vote aggregation with authority weighting
- Shannon entropy-based uncertainty preservation
- Dynamic quorum by entity type (Norma: 3/0.80, Sentenza: 4/0.85, Dottrina: 5/0.75)
- Controversy detection for polarized disagreements

✅ **Pipeline API Endpoints** (5 new endpoints):
- `POST /pipeline/query` - Execute full pipeline
- `POST /pipeline/feedback/submit` - Submit expert feedback
- `POST /pipeline/ner/correct` - Submit NER corrections
- `GET /pipeline/stats` - Pipeline statistics
- `GET /pipeline/health` - Component health check

✅ **Integration Tests** (850 LOC, 50+ test cases):
- End-to-end pipeline execution
- RLCF integration with authority weighting
- Feedback distribution
- Error handling and recovery

**Documentation**: [`FULL_PIPELINE_INTEGRATION_SUMMARY.md`](FULL_PIPELINE_INTEGRATION_SUMMARY.md) (28 pages)

### Week 3 Summary
- **Production Code**: 3,920 LOC (preprocessing + orchestration)
- **Test Code**: 3,000+ LOC (100+ new test cases)
- **Test Coverage**: 100+ new test cases with comprehensive coverage
- **API Endpoints**: 5 new endpoints for pipeline execution and management
- **Documentation**: 30+ pages of architecture and implementation guides

---

## 📚 Documentation

### For Understanding the Theory
1. [`docs/01-introduction/executive-summary.md`](docs/01-introduction/executive-summary.md) - High-level overview
2. [`docs/02-methodology/rlcf/RLCF.md`](docs/02-methodology/rlcf/RLCF.md) - **Core RLCF paper** (mathematical foundations)
3. [`docs/03-architecture/02-orchestration-layer.md`](docs/03-architecture/02-orchestration-layer.md) - Detailed architecture (100+ pages)

### For Implementation & Development
1. **[`docs/IMPLEMENTATION_ROADMAP.md`](docs/IMPLEMENTATION_ROADMAP.md)** - 42-week build plan (Phases 0-7)
2. **[`docs/TECHNOLOGY_RECOMMENDATIONS.md`](docs/TECHNOLOGY_RECOMMENDATIONS.md)** - Tech stack with benchmarks (2025)
3. [`docs/02-methodology/rlcf/testing/MANUAL_TESTING_GUIDE.md`](docs/02-methodology/rlcf/testing/MANUAL_TESTING_GUIDE.md) - Testing procedures
4. [`docs/02-methodology/rlcf/guides/quick-start.md`](docs/02-methodology/rlcf/guides/quick-start.md) - RLCF quick start

---

## 🛠️ Development

### Repository Structure

```
MERL-T_alpha/
├── backend/
│   ├── rlcf_framework/      # Phase 1: RLCF core (100% COMPLETE)
│   ├── preprocessing/       # Phase 2: KG Enrichment (60% Week 3 COMPLETE) + Query understanding (TODO)
│   ├── orchestration/       # Phase 2-3: Pipeline orchestrator (15% Week 3 COMPLETE) + LLM Router + Agents (TODO)
│   ├── reasoning/           # Phase 4: Experts + Synthesizer (TODO)
│   └── shared/              # Shared utilities
├── frontend/
│   └── rlcf-web/            # React app (100% COMPLETE)
├── tests/
│   ├── rlcf/                # Phase 1 tests (COMPLETE)
│   ├── preprocessing/       # Phase 2 KG tests (100+ cases, Week 3 COMPLETE)
│   └── integration/         # Phase 2 Pipeline tests (50+ cases, Week 3 COMPLETE)
├── docs/                    # Comprehensive documentation
├── scripts/                 # Development scripts
└── infrastructure/          # Docker, K8s configs
```

### Running Tests

```bash
# Run all tests
pytest tests/rlcf/

# Run with coverage
pytest tests/rlcf/ --cov=backend/rlcf_framework --cov-report=html

# Run specific test file
pytest tests/rlcf/test_authority_module.py -v
```

### CLI Usage Examples

```bash
# User commands (rlcf-cli)
rlcf-cli users create john_doe --authority-score 0.5
rlcf-cli users list --sort-by authority_score --limit 10
rlcf-cli tasks list --status OPEN
rlcf-cli tasks export 123 --format json -o task_123.json

# Admin commands (rlcf-admin)
rlcf-admin config show --type model
rlcf-admin config validate
rlcf-admin db migrate
rlcf-admin db seed --users 10 --tasks 20
rlcf-admin server --host 0.0.0.0 --port 8080 --reload
```

### Configuration

Configuration is YAML-based and hot-reloadable:

- **`backend/rlcf_framework/model_config.yaml`**: Authority weights, thresholds, AI model settings
- **`backend/rlcf_framework/task_config.yaml`**: Task type definitions, validation schemas

Edit via:
- Gradio interface (Admin tab)
- API: `PUT /config/model` or `PUT /config/tasks`
- Direct file editing (auto-reloads)

---

## 🐳 Docker Deployment

### Development Environment

```bash
# Start databases (PostgreSQL, Redis, etc.)
docker-compose -f docker-compose.dev.yml up -d

# Backend and frontend run natively (see Quick Start)
```

### Production Deployment (Phase 6)

```bash
# Full stack deployment
docker-compose up -d

# Access:
# - Backend: http://localhost:8000
# - Frontend: http://localhost:3000
```

📖 **Deployment guide**: [`docs/04-implementation/09-deployment.md`](docs/04-implementation/09-deployment.md)

---

## 🎯 Roadmap

### ✅ Phase 0: Setup (Weeks 1-2) - **COMPLETE**
- Repository structure
- CI/CD pipeline
- Development environment

### ✅ Phase 1: RLCF Core (Weeks 3-8) - **COMPLETE**
- Database models
- Authority module
- Aggregation engine
- API + Frontend
- CLI tools
- Testing suite

### 🚧 Phase 2: Preprocessing Layer (Weeks 9-14) - **NEXT**
- Knowledge Graph population (Neo4j → Memgraph)
- NER for legal entities (ITALIAN-LEGAL-BERT)
- Intent classification
- KG enrichment service

### 📋 Phase 3: Orchestration Layer (Weeks 15-22)
- LLM Router (LangGraph-based)
- VectorDB Agent (Qdrant)
- KG Agent (Memgraph)
- API Agent (Akoma Ntoso)

### 📋 Phase 4: Reasoning Layer (Weeks 23-30)
- 4 Expert types
- Synthesizer (convergent/divergent)
- Iteration controller

### 📋 Phase 5: Integration & Testing (Weeks 31-36)
- End-to-end testing
- Performance optimization
- Security hardening

### 📋 Phase 6: Production Readiness (Weeks 37-42)
- Kubernetes deployment
- Observability (SigNoz)
- CI/CD automation

📖 **Full roadmap**: [`docs/IMPLEMENTATION_ROADMAP.md`](docs/IMPLEMENTATION_ROADMAP.md)

---

## 🤝 Contributing

We welcome contributions from legal experts, AI researchers, and developers!

**📖 Please read**:
- **[Contributing Guide](CONTRIBUTING.md)** - Development setup, coding standards, PR process
- **[Code of Conduct](CODE_OF_CONDUCT.md)** - Community guidelines
- **[Security Policy](SECURITY.md)** - Reporting vulnerabilities

**How to contribute**:
1. Read the [Contributing Guide](CONTRIBUTING.md)
2. Fork the repository
3. Create a feature branch (`git checkout -b feature/amazing-feature`)
4. Make your changes (ensure tests pass: `pytest tests/`)
5. Commit with conventional commits (`feat:`, `fix:`, `docs:`)
6. Push and create a Pull Request

**Areas where we need help**:
- 🧑‍⚖️ **Legal experts**: Annotate datasets, provide feedback on legal reasoning
- 🧠 **AI/ML researchers**: Improve RLCF algorithms, LLM integration
- 💻 **Developers**: Implement future phases, frontend enhancements
- 📚 **Technical writers**: Documentation improvements
- 🔒 **Security researchers**: Vulnerability testing and security audits

---

## 📄 License & Compliance

**License**: MIT (see [LICENSE](LICENSE))

**AI Act Compliance**: MERL-T is designed for EU AI Act compliance as a high-risk AI system (legal assistance domain):
- ✅ Transparency: Full traceability via trace IDs
- ✅ Human oversight: Community feedback loops (RLCF)
- ✅ Accuracy: Multi-expert validation
- ✅ Bias detection: Built into aggregation algorithms

📖 **Compliance details**: [`docs/05-governance/ai-act-compliance.md`](docs/05-governance/ai-act-compliance.md)

---

## 📞 Support & Community

- **Documentation**: [`docs/`](docs/)
- **Issues**: [GitHub Issues](https://github.com/ALIS/MERL-T_alpha/issues)
- **Discussions**: [GitHub Discussions](https://github.com/ALIS/MERL-T_alpha/discussions)
- **ALIS Website**: [alis.org](https://alis.org)

---

## 🙏 Acknowledgments

- **ALIS (Artificial Legal Intelligence Society)** for sponsoring and governing the project
- **Legal experts** who contributed to dataset annotation and validation
- **Open-source community** for the amazing tools we build upon (FastAPI, React, SQLAlchemy, etc.)

---

## 🌟 Star History

If you find MERL-T useful, please consider starring the repository! ⭐

---

**Built with ❤️ by the ALIS community**

*For detailed implementation progress, see [`docs/IMPLEMENTATION_ROADMAP.md`](docs/IMPLEMENTATION_ROADMAP.md)*
