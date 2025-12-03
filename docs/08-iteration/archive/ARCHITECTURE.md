# MERL-T Architecture Overview

**Version**: 0.9.0
**Last Updated**: November 14, 2025

---

## System Architecture

MERL-T (Multi-Expert Legal Retrieval Transformer) is built on a **5-layer architecture** designed for scalability, reliability, and academic rigor in legal AI systems.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Applications                       │
│           (Web UI, Mobile App, API Integrations)                 │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    1. PREPROCESSING LAYER                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │Query Under-  │  │NER & Entity  │  │KG Enrichment         │  │
│  │standing      │  │Extraction    │  │(5 data sources)      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                   2. ORCHESTRATION LAYER                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  LLM Router (Claude 3.5 Sonnet)                           │  │
│  │  → Generates ExecutionPlan dynamically                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │KG Agent      │  │API Agent     │  │VectorDB Agent        │  │
│  │(Neo4j)       │  │(Normattiva)  │  │(Qdrant + E5-large)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     3. REASONING LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │Literal       │  │Systemic-     │  │Principles            │  │
│  │Interpreter   │  │Teleological  │  │Balancer              │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                   │
│  ┌──────────────┐  ┌──────────────────────────────────────┐    │
│  │Precedent     │  │Synthesizer                           │    │
│  │Analyst       │  │→ Unifies opinions with uncertainty   │    │
│  └──────────────┘  └──────────────────────────────────────┘    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Iteration Controller (Multi-turn Refinement)              │ │
│  │  → 6 stopping criteria, max 3 iterations                   │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      4. STORAGE LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │PostgreSQL    │  │Neo4j         │  │Qdrant                │  │
│  │(Relational)  │  │(KG)          │  │(Vectors)             │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                   │
│  ┌──────────────┐                                                │
│  │Redis (Cache) │                                                │
│  └──────────────┘                                                │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     5. LEARNING LAYER                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  RLCF (Reinforcement Learning from Community Feedback)    │  │
│  │  → Authority-weighted expert vote aggregation             │  │
│  │  → Uncertainty preservation (Shannon entropy)             │  │
│  │  → Dynamic quorum by entity type                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────┐  ┌──────────────────────────────────────┐    │
│  │NER Learning  │  │Model Fine-tuning                     │    │
│  │Loop          │  │(Batch retraining)                    │    │
│  └──────────────┘  └──────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. Preprocessing Layer

**Purpose**: Transform user queries into structured data for downstream processing.

**Components**:
- **Query Understanding**: Intent classification, user role detection
- **NER & Entity Extraction**: Extract legal entities (norms, cases, concepts)
- **KG Enrichment**: Multi-source knowledge graph enrichment
  - 5 sources: Normattiva (official), Cassazione (jurisprudence), Dottrina (academic), Community, RLCF
  - Temporal versioning, controversy detection
  - Redis caching for performance

**Outputs**: EnrichedContext with entities, intent, temporal metadata

---

### 2. Orchestration Layer

**Purpose**: Coordinate retrieval and reasoning through dynamic planning.

**LLM Router**:
- 100% LLM-based decision engine (no hardcoded rules)
- Generates ExecutionPlan using Claude 3.5 Sonnet
- Selects retrieval agents and reasoning experts based on query

**Retrieval Agents**:
1. **KG Agent**: Neo4j knowledge graph queries
   - 4 task types: concept expansion, hierarchical traversal, jurisprudence lookup, temporal evolution
2. **API Agent**: Integration with Norma Controller (visualex)
   - Full text retrieval, version history, metadata, case law
3. **VectorDB Agent**: Qdrant semantic search with E5-large embeddings
   - 3 search patterns: semantic (P1), filtered (P3), reranked (P4)

**Workflow**: LangGraph state machine with 6 nodes + routing + iteration loop

---

### 3. Reasoning Layer

**Purpose**: Multi-perspective legal analysis with uncertainty preservation.

**4 Reasoning Experts**:

1. **Literal Interpreter**
   - Strict textual interpretation
   - "What does the text explicitly say?"

2. **Systemic-Teleological**
   - Purpose-driven analysis
   - "What is the legislative intent?"

3. **Principles Balancer**
   - Constitutional principles weighing
   - "How do fundamental principles apply?"

4. **Precedent Analyst**
   - Case law analysis
   - "How have courts interpreted this?"

**Synthesizer**:
- Unifies expert opinions into coherent answer
- **Preserves uncertainty** (disagreement is information)
- Highlights alternative interpretations
- Shannon entropy quantifies consensus

**Iteration Controller**:
- Multi-turn refinement (max 3 iterations)
- 6 stopping criteria: high confidence, consensus, max iterations, diminishing returns, contradiction, timeout

---

### 4. Storage Layer

**Databases**:

- **PostgreSQL**: Relational data (queries, feedback, users, statistics)
- **Neo4j/Memgraph**: Knowledge graph (legal entities, relationships)
- **Qdrant**: Vector database (semantic search, E5-large embeddings)
- **Redis**: Caching layer (KG enrichment, API responses)

**Data Flow**:
- Queries → PostgreSQL (persistence + analytics)
- Legal entities → Neo4j (graph traversal)
- Documents → Qdrant (semantic retrieval)
- Hot data → Redis (fast access)

---

### 5. Learning Layer

**RLCF Framework**:

**Core Formula**: `A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)`

Where:
- `A_u(t)` = Authority score for user u at time t
- `B_u` = Base authority (credentials)
- `T_u(t-1)` = Temporal authority (recent accuracy)
- `P_u(t)` = Performance (task success rate)
- `α, β, γ` = Weights (configured per entity type)

**Aggregation**:
- Authority-weighted expert votes
- Dynamic quorum by entity type:
  - Norma (official law): 3 experts, 0.80 authority
  - Sentenza (case law): 4 experts, 0.85 authority
  - Dottrina (academic): 5 experts, 0.75 authority
- Uncertainty preservation via Shannon entropy
- Controversy detection (polarized disagreement)

**NER Learning Loop**:
- 4 correction types: MISSING_ENTITY, SPURIOUS_ENTITY, WRONG_BOUNDARY, WRONG_TYPE
- Automatic training example generation
- Performance tracking (F1, precision, recall)
- Batch retraining when threshold reached

---

## Technology Stack

### Backend

- **Language**: Python 3.11+
- **Framework**: FastAPI (async/await)
- **ORM**: SQLAlchemy 2.0 (async)
- **Validation**: Pydantic 2.5
- **LLM Integration**: OpenRouter (Claude 3.5 Sonnet)
- **Orchestration**: LangGraph
- **Embeddings**: sentence-transformers (E5-large multilingual, 1024 dims)

### Databases

- **Relational**: PostgreSQL 16
- **Graph**: Neo4j 5.x / Memgraph 2.x
- **Vector**: Qdrant 1.7+
- **Cache**: Redis 7.2

### Frontend

- **Framework**: React 19
- **Build Tool**: Vite 5
- **Language**: TypeScript 5
- **State Management**: Zustand
- **Data Fetching**: TanStack Query
- **Styling**: TailwindCSS 3

### Infrastructure

- **Containerization**: Docker 24+, Docker Compose
- **Orchestration**: Kubernetes (planned)
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana (planned)

---

## API Overview

**13 REST Endpoints** across 4 routers:

### Query Execution (4 endpoints)
- `POST /query/execute` - Execute legal query
- `GET /query/status/{trace_id}` - Get query status
- `GET /query/history/{user_id}` - Get query history
- `GET /query/retrieve/{trace_id}` - Retrieve query details

### Feedback (3 endpoints)
- `POST /feedback/user` - Submit user feedback
- `POST /feedback/rlcf` - Submit RLCF expert feedback
- `POST /feedback/ner` - Submit NER correction

### Statistics & Analytics (2 endpoints)
- `GET /stats/pipeline` - Get pipeline statistics
- `GET /stats/feedback` - Get feedback statistics

### System (4 endpoints)
- `GET /` - API root
- `GET /health` - Health check
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc

**Authentication**: API key (`X-API-Key` header)
**Rate Limiting**: Token bucket algorithm, tier-based limits

---

## Data Flow Example

**User Query**: "È valido un contratto firmato da un sedicenne?"

```
1. PREPROCESSING
   └─ Query Understanding: intent=contract_validity, role=citizen
   └─ NER: entities=[contratto, sedicenne]
   └─ KG Enrichment: related_norms=[Codice Civile Art. 1425, 1442]

2. ORCHESTRATION
   └─ LLM Router generates ExecutionPlan:
      - retrieval_agents: [kg_agent, api_agent]
      - reasoning_experts: [literal_interpreter, systemic_teleological, principles_balancer]
   └─ KG Agent: retrieves articles 1425 (incapacity), 1442 (annulment)
   └─ API Agent: retrieves full text from Normattiva

3. REASONING
   └─ Literal Interpreter: "Minor cannot contract" (confidence=0.95)
   └─ Systemic-Teleological: "Protects minors from exploitation" (confidence=0.90)
   └─ Principles Balancer: "Rights of minors vs contractual autonomy" (confidence=0.85)
   └─ Synthesizer: Primary answer + 1 alternative view + uncertainty=0.15

4. STORAGE
   └─ PostgreSQL: Save query, execution trace, timing
   └─ Neo4j: Update entity relationships (query ↔ norms)

5. LEARNING
   └─ User feedback: rating=5, helpful=true
   └─ RLCF: Expert confirms answer (authority_weight=0.85)
   └─ NER: No corrections needed
```

**Response Time**: ~3-5 seconds (95th percentile)

---

## Scalability

### Horizontal Scaling

- **API**: Stateless FastAPI workers (load balanced)
- **Databases**: Read replicas (PostgreSQL), sharding (Qdrant)
- **Cache**: Redis Cluster (distributed caching)

### Vertical Scaling

- **Embeddings**: GPU acceleration for E5-large
- **LLM**: Dedicated inference servers
- **Graph DB**: High-memory instances for complex traversals

### Performance Targets

- **Query Execution**: < 5s (P95)
- **API Response**: < 100ms (simple endpoints)
- **Concurrent Users**: 1,000+ (with load balancing)
- **Throughput**: 100 queries/sec (with caching)

---

## Security

### Authentication & Authorization

- API key authentication (`X-API-Key` header)
- Rate limiting (token bucket algorithm)
- Role-based access control (planned)

### Data Protection

- TLS 1.3 for all connections
- Encrypted data at rest (AES-256)
- PII anonymization
- GDPR compliance

### Vulnerabilities

- Regular security audits
- Dependency scanning (Dependabot)
- Code scanning (CodeQL)
- Penetration testing (planned)

---

## Compliance

### EU AI Act (Regulation 2024/1689)

MERL-T is designed as a **high-risk AI system** for legal assistance:

- **Transparency**: Full traceability via trace_id
- **Human Oversight**: Community feedback loops
- **Accuracy**: Multi-expert validation
- **Bias Detection**: Built into RLCF aggregation
- **Documentation**: Comprehensive technical documentation
- **Governance**: ALIS association oversight

---

## Development Status

- ✅ **Phase 1 Complete**: RLCF Core (v0.1.0)
- ✅ **Phase 2 Week 3 Complete**: KG Enrichment + Pipeline Integration (v0.2.0)
- ✅ **Week 6 Complete**: Orchestration Layer (v0.6.0)
- ✅ **Week 7 Complete**: Preprocessing Integration (v0.7.0)
- ✅ **Week 9 Complete**: OpenAPI Documentation (v0.9.0)
- ⏳ **In Progress**: Production deployment, advanced RLCF loops

---

## Further Reading

### Detailed Architecture

- **Preprocessing Layer**: [`docs/03-architecture/01-preprocessing-layer.md`](docs/03-architecture/01-preprocessing-layer.md)
- **Orchestration Layer**: [`docs/03-architecture/02-orchestration-layer.md`](docs/03-architecture/02-orchestration-layer.md)
- **Reasoning Layer**: [`docs/03-architecture/03-reasoning-layer.md`](docs/03-architecture/03-reasoning-layer.md)
- **Storage Layer**: [`docs/03-architecture/04-storage-layer.md`](docs/03-architecture/04-storage-layer.md)
- **Learning Layer**: [`docs/03-architecture/05-learning-layer.md`](docs/03-architecture/05-learning-layer.md)

### Methodology

- **RLCF Framework**: [`docs/02-methodology/rlcf/RLCF.md`](docs/02-methodology/rlcf/RLCF.md)
- **Knowledge Graphs**: [`docs/02-methodology/knowledge-graph.md`](docs/02-methodology/knowledge-graph.md)
- **Legal Reasoning**: [`docs/02-methodology/legal-reasoning.md`](docs/02-methodology/legal-reasoning.md)

### Implementation

- **Implementation Roadmap**: [`docs/IMPLEMENTATION_ROADMAP.md`](docs/IMPLEMENTATION_ROADMAP.md)
- **Technology Recommendations**: [`docs/TECHNOLOGY_RECOMMENDATIONS.md`](docs/TECHNOLOGY_RECOMMENDATIONS.md)
- **API Documentation**: [`docs/api/`](docs/api/)

---

**Last Updated**: November 14, 2025
**Version**: 0.9.0
**For Questions**: [support@alis.ai](mailto:support@alis.ai)
