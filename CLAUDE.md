# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MERL-T (Multi-Expert Legal Retrieval Transformer)** is an AI-powered architecture for legal research, compliance monitoring, and regulatory analysis. This repository contains **comprehensive technical documentation** for the system, which is sponsored by ALIS (Artificial Legal Intelligence Society).

**Important**: This is a **documentation-only repository**. There is no implementation code here - only architectural specifications, technical designs, and research documentation for the MERL-T system.

## Repository Structure

The documentation is organized into 6 main sections:

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

**Backend**: FastAPI (async/await), SQLAlchemy 2.0, Pydantic 2.5
**Databases**: PostgreSQL, Neo4j (graph), ChromaDB/Weaviate (vectors), Redis (cache)
**Frontend**: React, Next.js, TypeScript, TailwindCSS
**AI/ML**: LangChain (orchestration), OpenRouter (LLM provider), spaCy, PyTorch
**Infrastructure**: Docker, Kubernetes, Helm, GitHub Actions

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

1. **This is documentation only** - No implementation code exists yet (see IMPLEMENTATION_ROADMAP.md for build plan)
2. **Preserve mathematical rigor** - RLCF formulas and algorithms are academically grounded
3. **Maintain cross-references** - When updating one document, check for references in others
4. **Respect Italian legal context** - Examples use Italian law (Codice Civile, Costituzione)
5. **Version tracking** - Documents include version numbers and last updated dates
6. **Academic style** - Documentation is intended for peer review and publication
7. **Technology choices** - Refer to TECHNOLOGY_RECOMMENDATIONS.md for 2025 state-of-the-art stack

## Key Files to Understand the System

### For Understanding the Vision & Theory
Start with these files in order:
1. `docs/01-introduction/executive-summary.md` - High-level overview
2. `docs/02-methodology/rlcf/README.md` - RLCF framework navigation
3. `docs/02-methodology/rlcf/RLCF.md` - Core theoretical paper (mathematical foundations)
4. `docs/03-architecture/02-orchestration-layer.md` - Most detailed architecture doc (100+ pages)
5. `docs/02-methodology/rlcf/guides/quick-start.md` - Practical usage guide

### For Implementation & Building the System
**Essential reading before coding**:
1. `docs/IMPLEMENTATION_ROADMAP.md` - **START HERE**: Complete 42-week build plan
2. `docs/TECHNOLOGY_RECOMMENDATIONS.md` - Modern tech stack with benchmarks (2025)
3. `docs/04-implementation/07-rlcf-pipeline.md` - RLCF implementation blueprint
4. `docs/02-methodology/rlcf/testing/MANUAL_TESTING_GUIDE.md` - Testing procedures
