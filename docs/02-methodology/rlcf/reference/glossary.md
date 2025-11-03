# Glossary

## Core RLCF Concepts

### Authority Score

**Definition**: A dynamic measure of a user's expertise and credibility in legal evaluation tasks.
**Formula**: A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)
**Range**: [0.0, 2.0]
**Components**: Baseline credentials, track record, recent performance

### Aggregation Engine

**Definition**: The core algorithm that combines community feedback into consensus responses while preserving uncertainty.
**Reference**: Algorithm 1 in RLCF.md Section 3.1
**Implementation**: [`aggregation_engine.py`](../../rlcf_framework/aggregation_engine.py)

### Baseline Credentials

**Definition**: Static scoring based on education, experience, and institutional role.
**Formula**: B_u = Σ(w_i · f_i(c_{u,i}))
**Components**: Academic degrees, professional experience, publications, institutional role

### Bias Detection

**Definition**: Six-dimensional analysis framework for identifying systematic biases in community feedback.
**Dimensions**: Demographic, professional, temporal, geographic, confirmation, anchoring
**Formula**: B_total = √(Σ b_i²)

### Constitutional Governance

**Definition**: Algorithmic implementation of legal principles ensuring transparency, bias detection, and community benefit.
**Principles**: Four foundational principles from RLCF.md Section 1.2

## Mathematical Terms

### Disagreement Score (δ)

**Definition**: Normalized Shannon entropy measuring diversity of expert positions.
**Formula**: δ = -(1/log|P|) Σ ρ(p)log ρ(p)
**Range**: [0.0, 1.0]
**Threshold**: τ = 0.4 for uncertainty preservation

### Dynamic Authority

**Definition**: First foundational principle - authority earned through demonstrated competence, not credentials alone.
**Implementation**: Real-time authority score updates based on performance

### Exponential Smoothing

**Definition**: Mathematical technique for updating track record scores.
**Formula**: T_u(t) = λ·T_u(t-1) + (1-λ)·Q_u(t)
**Decay Factor**: λ = 0.95

### Preserved Uncertainty

**Definition**: Second foundational principle - maintaining disagreement as information rather than forcing consensus.
**Implementation**: Alternative positions preserved when disagreement > threshold

## Technical Terms

### Async/Await

**Definition**: Python concurrency model used throughout the framework for non-blocking operations.
**Benefit**: Enables high-performance database and API operations

### Constitutional Framework

**Definition**: Software implementation of constitutional AI principles ensuring ethical operation.
**Implementation**: [`main.py`](../../rlcf_framework/main.py) validation functions

### Devil's Advocate System

**Definition**: Mechanism for assigning critical evaluators to prevent groupthink.
**Assignment Probability**: P(advocate) = min(0.1, 3/|E|)
**Purpose**: Ensure dialectical preservation

### Pydantic Models

**Definition**: Data validation library used for schema definition and runtime validation.
**Usage**: All API schemas, configuration validation

### Task Handler

**Definition**: Polymorphic system for processing different legal task types.
**Pattern**: Strategy pattern with shared interface
**Types**: 9+ supported legal task types

## Legal AI Terms

### Artificial Legal Intelligence (ALI)

**Definition**: AI systems specifically designed for legal reasoning and decision support.
**Challenges**: Epistemic pluralism, dynamic authority, dialectical preservation

### Blind Evaluation

**Definition**: Evaluation phase where reviewers cannot see other evaluations to prevent anchoring bias.
**Implementation**: Task status management in database

### Epistemic Pluralism

**Definition**: Recognition that multiple valid interpretations can coexist in legal reasoning.
**Implementation**: Uncertainty-preserving aggregation

### Ground Truth Separation

**Definition**: Process of separating known answers from input data for evaluation purposes.
**Configuration**: Defined in task_config.yaml ground_truth_keys

### Legal Task Types

**Definition**: Categorization of different legal AI evaluation tasks.
**Examples**: QA, Classification, Prediction, Drafting, Risk Spotting

## System Architecture Terms

### FastAPI

**Definition**: Modern Python web framework for building APIs with automatic documentation.
**Features**: OpenAPI generation, dependency injection, async support

### SQLAlchemy ORM

**Definition**: Object-Relational Mapping library for database operations.
**Version**: Async SQLAlchemy for non-blocking database operations

### Dependency Injection

**Definition**: Design pattern for providing dependencies (database sessions, configuration) to functions.
**Implementation**: FastAPI Depends() system

### Hot Reload

**Definition**: Ability to update configuration without restarting the system.
**Scope**: Model parameters, task schemas, thresholds

## Research Terms

### A/B Testing

**Definition**: Experimental methodology for comparing different configurations.
**Support**: Multiple configuration management for parallel testing

### Academic Rigor

**Definition**: Adherence to scientific standards in implementation and documentation.
**Features**: Mathematical precision, reproducibility, peer review readiness

### Peer Review Ready

**Definition**: Code and documentation prepared for academic publication and review.
**Standards**: Citations, mathematical precision, reproducible experiments

### Reproducibility

**Definition**: Ability to replicate experimental results with identical configurations.
**Implementation**: YAML configuration versioning, deterministic algorithms

## API Terms

### OpenAPI Specification

**Definition**: Standard for describing REST APIs with interactive documentation.
**Access**: http://localhost:8000/docs

### REST API

**Definition**: Representational State Transfer - architectural style for web services.
**Implementation**: FastAPI with standard HTTP methods

### Schema Validation

**Definition**: Automatic validation of request/response data against defined schemas.
**Library**: Pydantic models with type checking

## Configuration Terms

### YAML Configuration

**Definition**: Human-readable configuration format for parameters and schemas.
**Files**: model_config.yaml, task_config.yaml

### Safe Evaluation

**Definition**: Secure execution of user-defined mathematical expressions.
**Implementation**: asteval library instead of eval()

### Runtime Reconfiguration

**Definition**: Ability to modify system parameters while running.
**Security**: API key protection, constitutional validation

## Quality Assurance Terms

### Anchoring Bias

**Definition**: Cognitive bias where early information disproportionately influences later decisions.
**Detection**: Analysis of response order effects
**Mitigation**: Blind evaluation, randomized presentation

### Confirmation Bias

**Definition**: Tendency to favor information confirming existing beliefs.
**Detection**: Analysis of position consistency patterns
**Formula**: Ratio of similar to total previous positions

### Track Record Score

**Definition**: Historical performance measure updated with exponential smoothing.
**Range**: [0.0, 1.0]
**Update**: After each evaluation with quality score

## Acronyms

- **ALI**: Artificial Legal Intelligence
- **API**: Application Programming Interface
- **CORS**: Cross-Origin Resource Sharing
- **HTTP**: Hypertext Transfer Protocol
- **JSON**: JavaScript Object Notation
- **NER**: Named Entity Recognition
- **NLI**: Natural Language Inference
- **ORM**: Object-Relational Mapping
- **QA**: Question Answering
- **REST**: Representational State Transfer
- **RLCF**: Reinforcement Learning from Community Feedback
- **RLHF**: Reinforcement Learning from Human Feedback
- **SQL**: Structured Query Language
- **UI**: User Interface
- **UUID**: Universally Unique Identifier
- **YAML**: YAML Ain't Markup Language

## Mathematical Symbols

- **α (alpha)**: Baseline credentials weight (default: 0.3)
- **β (beta)**: Track record weight (default: 0.5)
- **γ (gamma)**: Recent performance weight (default: 0.2)
- **δ (delta)**: Disagreement score [0,1]
- **λ (lambda)**: Decay factor (default: 0.95)
- **τ (tau)**: Disagreement threshold (default: 0.4)
- **ρ (rho)**: Authority-weighted probability
- **A_u(t)**: Authority score for user u at time t
- **B_u**: Baseline credentials score
- **T_u(t)**: Track record score at time t
- **P_u(t)**: Recent performance score
- **Q_u(t)**: Quality score at time t

---

**Related Documentation:**

- [Framework Overview](../theoretical/framework-overview.md) - Core concepts and principles
- [Mathematical Framework](../theoretical/mathematical-framework.md) - Detailed formulas
- [System Architecture](../technical/architecture.md) - Technical implementation
