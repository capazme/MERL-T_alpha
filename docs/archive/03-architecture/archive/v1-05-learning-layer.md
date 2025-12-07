# Learning Layer Architecture (RLCF Framework)

**Implementation Status**: 🚧 **PARZIALMENTE IMPLEMENTATO**
**Current Version**: v0.1.0 (RLCF Core)
**Last Updated**: November 2025

**Implemented Components**:
- ✅ RLCF Core Framework: Authority scoring, feedback aggregation, bias detection (Phase 1)
- ✅ Authority Calculation: A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t) formula implemented
- ✅ Uncertainty Preservation: Shannon entropy-based disagreement quantification
- ✅ Dynamic Configuration: Hot-reload YAML configs, backup/restore
- ✅ Feedback API Endpoints: Submit feedback, batch feedback, NER corrections
- ✅ Test Suite: 68 tests for RLCF core (90%+ coverage)
- ⏳ Training Data Generator: Architecture defined, not yet implemented
- ⏳ Model Retraining Pipeline: Architecture defined, not yet automated
- ⏳ A/B Testing Framework: Architecture defined, not yet implemented
- ⏳ 4 Learning Loops: Planned for future implementation

**Code Location**: `merlt/rlcf_framework/`, `merlt/orchestration/api/routers/feedback.py`
**Tests**: `tests/rlcf/`, `tests/orchestration/test_api_feedback.py`

---

## 1. Introduction

The **Learning Layer** implements the **Reinforcement Learning from Community Feedback (RLCF)** framework, enabling MERL-T to continuously evolve based on real-world usage and expert validation. This layer consists of:

1. **Community Feedback Interface** (collect user/expert feedback)
2. **Training Data Generator** (convert feedback to training examples)
3. **Model Update Orchestrator** (retrain models, A/B test, deploy)
4. **4 Learning Loops** (Router, VectorDB Embeddings, Query Understanding, Synthesizer)

**Design Principles**:
- **Community-Driven**: Legal experts (ALIS community) drive system evolution
- **Dynamic Authority**: User authority weighted by track record (not static credentials)
- **Continuous Learning**: Weekly lightweight updates, monthly heavy retraining
- **A/B Testing**: New models deployed cautiously with performance monitoring
- **Transparent**: All feedback and model updates logged for audit

**Performance Targets**:
- Feedback collection: < 5s (user submission)
- Training data generation: < 1 hour (daily batch)
- Model retraining: < 24 hours (weekly cycle)
- A/B test duration: 7 days (10% traffic to new model)

**Reference**: See `docs/02-methodology/rlcf-framework.md` for theoretical foundation.

---

## 2. Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│              USER INTERACTION WITH MERL-T              │
│   Query → QueryContext → Router → Agents → Experts    │
│                  → Synthesizer → Final Answer          │
└──────────────────────┬─────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────────┐
│          COMMUNITY FEEDBACK INTERFACE                  │
│   User provides:                                       │
│   • Rating (1-5 stars)                                 │
│   • Corrections (structured)                           │
│   • Suggestions (free text)                            │
└──────────────────────┬─────────────────────────────────┘
                       ↓
              Feedback Record (PostgreSQL)
              (trace_id, rating, corrections, context)
                       ↓
┌────────────────────────────────────────────────────────┐
│          TRAINING DATA GENERATOR (daily batch)         │
│   Convert feedback → training examples:                │
│   • Router: (context, plan, outcome) → training       │
│   • VectorDB: (query, relevant_chunk, irrelevant_chunk) → triplet│
│   • Query Understanding: (query, entities, corrections) → annotation│
│   • Synthesizer: (expert_outputs, final_answer, rating) → training│
└──────────────────────┬─────────────────────────────────┘
                       ↓
         Training Examples Database (PostgreSQL)
                       ↓
┌────────────────────────────────────────────────────────┐
│       MODEL UPDATE ORCHESTRATOR (weekly/monthly)       │
│   • Trigger retraining when threshold met              │
│   • A/B test new model (10% traffic for 7 days)       │
│   • Monitor metrics (precision, recall, user ratings)  │
│   • Gradual rollout if metrics improve                │
└──────────────────────┬─────────────────────────────────┘
                       ↓
         ┌─────────────┴─────────────┐
         │                           │
         ↓                           ↓
┌──────────────────┐       ┌──────────────────┐
│ Updated Models   │       │ System Logs      │
│ (versioned)      │       │ (audit trail)    │
│                  │       │                  │
│ • Router prompt  │       │ • Model versions │
│ • Embeddings     │       │ • A/B results    │
│ • NER model      │       │ • Rollouts       │
│ • Synthesizer    │       │                  │
└──────────────────┘       └──────────────────┘
```

**Key Characteristics**:
- **Feedback-driven**: All learning triggered by community feedback
- **Multi-model**: 4 independent learning loops running in parallel
- **Gradual deployment**: A/B testing ensures stability
- **Traceable**: Full audit trail of model evolution

---

## 3. Community Feedback Interface

### 3.1 Feedback Collection UI

**User Journey**:

```
User receives MERL-T answer
         ↓
┌────────────────────────────────────────┐
│ Answer Display with Provenance         │
│ • Final answer text                    │
│ • Sources cited (norms, case law)      │
│ • Expert reasoning (expandable)        │
│ • Confidence indicator                 │
└──────────────┬─────────────────────────┘
               ↓
      User clicks "Provide Feedback"
               ↓
┌────────────────────────────────────────┐
│ Feedback Form                          │
│                                        │
│ 1. Rating: ⭐⭐⭐⭐⭐ (1-5 stars)        │
│                                        │
│ 2. Feedback Type (multi-select):      │
│    □ Risposta corretta                 │
│    □ Risposta incompleta               │
│    □ Fonti errate                      │
│    □ Ragionamento giuridico errato     │
│    □ Esperti sbagliati selezionati     │
│                                        │
│ 3. Corrections (optional):             │
│    [Text area for detailed corrections]│
│                                        │
│ 4. Suggested Sources (optional):      │
│    Add norm/case: [Art. ___]          │
│                                        │
│ 5. Submit Feedback                     │
└────────────┬───────────────────────────┘
             ↓
┌────────────────────────────────────────┐
│ Dynamic Authority Check                │
│ Calculate user_authority_score:        │
│ • User role (expert, lawyer, citizen)  │
│ • Historical accuracy of feedback      │
│ • Consensus with other experts         │
│ Output: authority_score (0.0-1.0)      │
└────────────┬───────────────────────────┘
             ↓
┌────────────────────────────────────────┐
│ Store Feedback in PostgreSQL           │
│ Table: answer_feedback                 │
│ Fields: trace_id, user_id, rating,     │
│         corrections, authority_score   │
└────────────────────────────────────────┘
```

**Feedback Form Schema**:

```json
{
  "feedback": {
    "trace_id": "SYN-20241103-abc123",
    "user_id": "uuid",
    "rating": 4,
    "feedback_types": ["risposta_incompleta", "fonti_errate"],
    "corrections": {
      "missing_sources": [
        {
          "source_type": "norm",
          "source_id": "art_1454_cc",
          "citation": "Art. 1454 c.c.",
          "relevance": "Regola complementare sulla diffida ad adempiere"
        }
      ],
      "wrong_interpretation": "L'Expert ha ignorato la distinzione tra risoluzione di diritto e risoluzione giudiziale",
      "suggested_answer": "La risposta dovrebbe distinguere tra risoluzione ex Art. 1453 (giudiziale) e Art. 1454 (di diritto)."
    },
    "suggested_sources": ["art_1454_cc"],
    "free_text_comments": "Buona risposta ma manca riferimento alla diffida ad adempiere (Art. 1454)",
    "timestamp": "2024-11-03T10:30:00Z"
  }
}
```

---

### 3.2 Dynamic Authority Calculator

**Purpose**: Weight feedback by user authority (not static credentials).

**Authority Formula**:

```
user_authority_score = (
    0.4 * role_weight +
    0.3 * historical_accuracy +
    0.2 * consensus_score +
    0.1 * reputation_score
)

Where:
- role_weight:
    • Legal expert (professor, judge, senior lawyer): 1.0
    • Practicing lawyer: 0.7
    • Law student: 0.4
    • Citizen: 0.2

- historical_accuracy:
    Count of validated feedback / Total feedback submitted
    (Feedback is "validated" when majority of experts agree)

- consensus_score:
    For this specific feedback, how many other experts agree?
    consensus_score = agreeing_experts / total_experts_who_reviewed

- reputation_score:
    Cumulative reputation from ALIS community
    (Upvotes on contributions, badges, etc.)

Output: user_authority_score ∈ [0.0, 1.0]
```

**Example Calculation**:

```
User: Maria Rossi, Avvocato (practicing lawyer)
- role_weight: 0.7
- historical_accuracy: 48 validated / 52 submitted = 0.923
- consensus_score: 3 agree / 4 reviewed this feedback = 0.75
- reputation_score: 850 points → 0.85 (normalized)

user_authority_score = 0.4 * 0.7 + 0.3 * 0.923 + 0.2 * 0.75 + 0.1 * 0.85
                     = 0.28 + 0.277 + 0.15 + 0.085
                     = 0.792
```

**Use of Authority Score**:
- **Training Data**: High authority feedback weighted more in training
- **Model Updates**: Low authority feedback requires more consensus before acting
- **Feedback Display**: Show authority score to help users assess feedback quality

---

### 3.3 Feedback Storage Schema

**PostgreSQL Table** (from Storage Layer):

```sql
CREATE TABLE answer_feedback (
    feedback_id UUID PRIMARY KEY,
    trace_id VARCHAR(100) NOT NULL,
    user_id UUID NOT NULL,
    user_authority_score FLOAT NOT NULL,

    -- Feedback content
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    feedback_types TEXT[], -- Array: ['risposta_incompleta', 'fonti_errate', ...]
    corrections JSONB,
    suggested_sources TEXT[],
    free_text_comments TEXT,

    -- Context (for training data generation)
    query_text TEXT NOT NULL,
    final_answer TEXT NOT NULL,
    execution_plan JSONB,
    expert_outputs JSONB,
    retrieval_result JSONB,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMP
);

CREATE INDEX idx_feedback_trace_id ON answer_feedback(trace_id);
CREATE INDEX idx_feedback_rating ON answer_feedback(rating);
CREATE INDEX idx_feedback_processed ON answer_feedback(processed);
CREATE INDEX idx_feedback_authority ON answer_feedback(user_authority_score);
```

---

## 4. Training Data Generator

**Purpose**: Convert feedback into training examples for model retraining.

**Processing Flow**:

```
Daily Batch Job (runs at 2 AM)
         ↓
┌────────────────────────────────────────┐
│ 1. Fetch Unprocessed Feedback          │
│    SELECT * FROM answer_feedback       │
│    WHERE processed = false             │
└──────────────┬─────────────────────────┘
               ↓
┌────────────────────────────────────────┐
│ 2. Generate Training Examples          │
│    For each feedback:                  │
│    - Router training (context → plan)  │
│    - VectorDB triplets (query, pos, neg)│
│    - Query Understanding annotations   │
│    - Synthesizer examples              │
└──────────────┬─────────────────────────┘
               ↓
┌────────────────────────────────────────┐
│ 3. Quality Filtering                   │
│    Filter by:                          │
│    - user_authority_score > 0.6        │
│    - rating != 3 (neutral)             │
│    - corrections not empty             │
└──────────────┬─────────────────────────┘
               ↓
┌────────────────────────────────────────┐
│ 4. Store Training Examples             │
│    INSERT INTO training_examples       │
└──────────────┬─────────────────────────┘
               ↓
┌────────────────────────────────────────┐
│ 5. Mark Feedback as Processed          │
│    UPDATE answer_feedback              │
│    SET processed = true                │
└────────────────────────────────────────┘
```

---

### 4.1 Router Training Data

**Purpose**: Improve Router's execution plan generation.

**Training Example Schema**:

```json
{
  "example_type": "router_decision",
  "input_data": {
    "query_context": {
      "original_query": "È valido un contratto firmato da un minorenne?",
      "entities": [...],
      "concepts": [...],
      "intent": {"primary": "validità_atto"},
      "complexity": {"score": 0.62}
    },
    "enriched_context": {
      "mapped_norms": [...]
    }
  },
  "expected_output": {
    "execution_plan": {
      "retrieval_plan": {
        "api_agent": {"enabled": true, ...},
        "vectordb_agent": {"enabled": false}
      },
      "reasoning_plan": {
        "experts": ["Literal_Interpreter", "Precedent_Analyst"]
      }
    }
  },
  "outcome": {
    "actual_plan_generated": {...},
    "final_answer_rating": 2,
    "expert_correction": "Should have activated Precedent_Analyst to cite case law"
  },
  "quality_score": 0.85,
  "source_feedback_id": "uuid"
}
```

**Training Strategy**:
- **Fine-tune system prompt**: Add examples of good/bad ExecutionPlans to few-shot prompt
- **Preference learning**: Train on (query, good_plan, bad_plan) triplets using RLHF techniques
- **Evaluation**: Test new prompt on held-out feedback, measure rating improvement

---

### 4.2 Embedding Training Data (Triplets)

**Purpose**: Fine-tune VectorDB embeddings for better retrieval.

**Training Example Schema** (Contrastive Learning):

```json
{
  "example_type": "embedding_triplet",
  "input_data": {
    "anchor": "È valido un contratto firmato da un minorenne?",
    "positive": "Art. 2 c.c. - La maggiore età è fissata al compimento del diciottesimo anno. Con la maggiore età si acquista la capacità di compiere tutti gli atti per i quali non sia stabilita un'età diversa.",
    "negative": "Art. 1350 c.c. - Devono farsi per atto pubblico o per scrittura privata, sotto pena di nullità: 1) i contratti che trasferiscono la proprietà di beni immobili..."
  },
  "expected_output": {
    "anchor_to_positive_distance": "< anchor_to_negative_distance"
  },
  "quality_score": 0.92,
  "source_feedback_id": "uuid",
  "derivation": "User said 'Art. 2 c.c. is the correct source' (positive), system retrieved Art. 1350 c.c. (negative)"
}
```

**Derivation Logic**:

```
Feedback: "Fonti errate - manca Art. 2 c.c."

Derivation:
1. anchor = original query
2. positive = Art. 2 c.c. (suggested by user as correct)
3. negative = Art. 1350 c.c. (was retrieved by system but user said it's wrong)

Training: Minimize distance(anchor, positive), maximize distance(anchor, negative)
```

**Training Strategy**:
- **Contrastive loss**: Triplet margin loss
- **Hard negative mining**: Find chunks semantically similar but legally distinct
- **Batch size**: 64 triplets per batch
- **Epochs**: 3-5 epochs on accumulated RLCF data

---

### 4.3 Query Understanding Training Data

**Purpose**: Improve entity extraction, intent classification, complexity scoring.

**Training Example Schema**:

```json
{
  "example_type": "query_understanding_annotation",
  "input_data": {
    "query": "È valido un contratto firmato da un minorenne nel 2010?"
  },
  "expected_output": {
    "entities": [
      {"text": "contratto", "type": "LEGAL_OBJECT", "start": 11, "end": 20},
      {"text": "minorenne", "type": "PERSON", "start": 35, "end": 44},
      {"text": "2010", "type": "DATE", "start": 49, "end": 53}
    ],
    "intent": {"primary": "validità_atto", "confidence": 0.92},
    "complexity": {"score": 0.62}
  },
  "outcome": {
    "system_output": {
      "entities": [...], // Missing "2010" entity
      "intent": {"primary": "validità_atto"},
      "complexity": {"score": 0.45} // Too low
    },
    "expert_correction": {
      "entities": "Missing DATE entity '2010'",
      "complexity": "Should be 0.62 (medium complexity) due to temporal reference"
    }
  },
  "quality_score": 0.88,
  "source_feedback_id": "uuid"
}
```

**Training Strategy**:
- **Entity extraction**: Add corrected annotations to NER fine-tuning dataset
- **Intent classification**: Retrain multi-label classifier on corrected labels
- **Complexity scoring**: Retrain Random Forest on corrected complexity scores

---

### 4.4 Synthesizer Training Data

**Purpose**: Improve answer synthesis quality (convergent vs divergent modes).

**Training Example Schema**:

```json
{
  "example_type": "synthesizer_training",
  "input_data": {
    "expert_outputs": [
      {
        "expert_type": "Literal_Interpreter",
        "interpretation": "...",
        "confidence": 0.95
      },
      {
        "expert_type": "Systemic_Teleological",
        "interpretation": "...",
        "confidence": 0.78
      }
    ],
    "synthesis_mode": "convergent",
    "query_context": {...}
  },
  "expected_output": {
    "final_answer": "Il contratto firmato da un minorenne è annullabile (Art. 1425 c.c.). [Improved version with better synthesis]",
    "provenance": [...]
  },
  "outcome": {
    "system_output": {
      "final_answer": "Il contratto è annullabile.", // Too brief
      "rating": 2
    },
    "expert_correction": "Answer should integrate both literal interpretation (Art. 1425) and systemic context (tutela del minore). Missing provenance for claims."
  },
  "quality_score": 0.80,
  "source_feedback_id": "uuid"
}
```

**Training Strategy**:
- **Prompt engineering**: Update synthesizer system prompt with examples of good synthesis
- **Preference learning**: Train on (expert_outputs, good_synthesis, bad_synthesis) triplets
- **Evaluation**: Measure answer quality (rating) and provenance completeness

---

## 5. Model Update Orchestrator

### 5.1 Weekly Update Cycle

**Schedule**:

```
WEEKLY CYCLE (Lightweight Updates):
┌────────────────────────────────────────────────────────┐
│ Monday 2 AM: Generate Training Data (daily batch)     │
│ ├─ Fetch unprocessed feedback from past week          │
│ ├─ Generate training examples                         │
│ └─ Store in training_examples table                   │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ Monday 10 AM: Trigger Model Updates (if threshold met)│
│ ├─ Check: New training examples > 100?                │
│ ├─ YES → Trigger retraining                           │
│ └─ NO  → Skip this week                               │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ Tuesday: Retraining (automated)                        │
│ ├─ Router: Update few-shot prompt with new examples   │
│ ├─ Query Understanding: Fine-tune NER on new annotations│
│ └─ Synthesizer: Update prompt with new synthesis examples│
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ Wednesday: A/B Test Deployment                         │
│ ├─ Deploy new models to 10% of traffic                │
│ ├─ Monitor metrics (precision, recall, user ratings)  │
│ └─ Continue A/B test for 7 days                       │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ Next Wednesday: Evaluate A/B Test                      │
│ ├─ Compare metrics: new model vs old model            │
│ ├─ IF new model improves → Gradual rollout (50%, 100%)│
│ └─ IF no improvement → Rollback to old model          │
└────────────────────────────────────────────────────────┘


MONTHLY CYCLE (Heavy Retraining):
┌────────────────────────────────────────────────────────┐
│ First Monday of Month: Heavy Retraining                │
│ ├─ VectorDB Embeddings: Full fine-tuning (3-5 epochs) │
│ │   on accumulated RLCF triplets (1,000-5,000 examples)│
│ │   Duration: ~12 hours                                │
│ ├─ Query Understanding: Full NER retraining            │
│ │   Duration: ~6 hours                                 │
│ └─ Complexity Model: Retrain Random Forest             │
│     Duration: ~1 hour                                  │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ Tuesday-Wednesday: A/B Test (same as weekly)           │
│ Next Tuesday: Evaluate & Rollout (same as weekly)      │
└────────────────────────────────────────────────────────┘
```

---

### 5.2 A/B Testing Strategy

**Test Configuration**:

```json
{
  "ab_test_config": {
    "test_id": "uuid",
    "model_component": "router_prompt | vectordb_embeddings | ner_model | synthesizer_prompt",
    "old_model_version": "v2.3",
    "new_model_version": "v2.4",
    "traffic_split": {
      "old_model": 0.9,
      "new_model": 0.1
    },
    "duration_days": 7,
    "start_date": "2024-11-04",
    "end_date": "2024-11-11",
    "metrics_tracked": [
      "answer_quality_rating",
      "retrieval_precision",
      "retrieval_recall",
      "latency_p95",
      "error_rate"
    ]
  }
}
```

**Traffic Routing**:

```
User Query arrives
       ↓
┌──────────────────────────────┐
│ A/B Test Router              │
│ hash(user_id) % 100          │
│   < 10  → new_model (10%)    │
│   >= 10 → old_model (90%)    │
└──────────┬───────────────────┘
           ↓
    Route to appropriate model
```

**Metrics Collection**:

```sql
CREATE TABLE ab_test_metrics (
    metric_id UUID PRIMARY KEY,
    test_id UUID NOT NULL,
    model_version VARCHAR(50) NOT NULL, -- 'v2.3' or 'v2.4'
    trace_id VARCHAR(100) NOT NULL,

    -- Metrics
    answer_quality_rating FLOAT, -- User rating (1-5)
    retrieval_precision FLOAT,   -- Relevant chunks / Retrieved chunks
    retrieval_recall FLOAT,      -- Relevant chunks / All relevant chunks
    latency_ms INTEGER,
    error_occurred BOOLEAN,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ab_test_version ON ab_test_metrics(test_id, model_version);
```

**Evaluation Query**:

```sql
-- Compare new vs old model
SELECT
    model_version,
    AVG(answer_quality_rating) AS avg_rating,
    AVG(retrieval_precision) AS avg_precision,
    AVG(latency_ms) AS avg_latency_ms,
    COUNT(*) AS sample_size
FROM ab_test_metrics
WHERE test_id = $test_id
GROUP BY model_version;
```

**Decision Logic**:

```
IF new_model.avg_rating > old_model.avg_rating + 0.1  (10% improvement)
   AND new_model.avg_latency_ms < old_model.avg_latency_ms * 1.2  (< 20% slowdown)
   AND new_model.error_rate < old_model.error_rate * 1.1  (< 10% more errors)
THEN
   Gradual rollout: 10% → 50% → 100% (over 3 days)
ELSE
   Rollback to old model
```

---

### 5.3 Model Versioning

**Versioning Schema**:

```
Model Version Format: v{major}.{minor}.{patch}

Examples:
- v2.3.0 = Major version 2, Minor 3, Patch 0
- v2.3.1 = Bug fix (patch)
- v2.4.0 = New features (minor)
- v3.0.0 = Breaking changes (major)

Version Increments:
- Weekly updates: Patch increment (v2.3.0 → v2.3.1)
- Monthly updates: Minor increment (v2.3.1 → v2.4.0)
- Architecture changes: Major increment (v2.4.0 → v3.0.0)
```

**Model Registry**:

```sql
CREATE TABLE model_registry (
    model_id UUID PRIMARY KEY,
    model_component VARCHAR(100) NOT NULL, -- 'router_prompt', 'vectordb_embeddings', etc.
    version VARCHAR(50) NOT NULL,
    model_artifact_url TEXT, -- S3/MinIO URL to model file
    training_data_size INTEGER,
    training_examples_ids TEXT[], -- Array of example UUIDs

    -- Performance
    validation_metrics JSONB, -- Precision, recall, etc.

    -- Deployment
    deployment_status VARCHAR(50), -- 'testing', 'deployed', 'deprecated'
    deployed_at TIMESTAMP,
    deprecated_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_version UNIQUE(model_component, version)
);

CREATE INDEX idx_model_component ON model_registry(model_component);
CREATE INDEX idx_model_status ON model_registry(deployment_status);
```

---

## 6. Learning Loops

### 6.1 Router Learning Loop

**Objective**: Improve Router's execution plan generation based on feedback.

**Learning Process**:

```
Feedback: "Esperti sbagliati selezionati"
Correction: "Should have activated Precedent_Analyst"

Training Data Generation:
┌────────────────────────────────────────┐
│ Input: QueryContext + EnrichedContext  │
│ Output (system): ExecutionPlan with    │
│         experts = [Literal_Interpreter]│
│ Expected (expert): ExecutionPlan with  │
│         experts = [Literal_Interpreter,│
│                    Precedent_Analyst]  │
└──────────────┬─────────────────────────┘
               ↓
         Few-Shot Prompt Update
         (Add example to system prompt)

System Prompt (updated):
"...
Example of good plan:
Query: 'È valido un contratto firmato da un minorenne?'
Context: complexity=0.62, intent=validità_atto
Correct Plan: Activate Literal_Interpreter + Precedent_Analyst
Rationale: Even for medium complexity, case law provides
           valuable context for validity checks.
..."
```

**Evaluation**:
- Metric: % of queries where expert selection matches expert expectations
- Target: > 85% agreement

---

### 6.2 VectorDB Embedding Loop

**Objective**: Fine-tune embeddings to improve retrieval precision/recall.

**Learning Process**:

```
Feedback: "Fonti errate - manca Art. 2 c.c."

Training Data Generation (Contrastive Triplet):
┌────────────────────────────────────────┐
│ anchor   = "È valido un contratto      │
│             firmato da un minorenne?"  │
│ positive = Art. 2 c.c. (user suggested)│
│ negative = Art. 1350 c.c. (system      │
│            retrieved but wrong)        │
└──────────────┬─────────────────────────┘
               ↓
    Accumulate 1,000-5,000 triplets/month
               ↓
┌────────────────────────────────────────┐
│ Monthly Fine-Tuning                    │
│ Model: multilingual-e5-large (Phase 2) │
│ Loss: Triplet margin loss              │
│ Epochs: 3-5                            │
│ Batch size: 64                         │
│ Duration: ~12 hours                    │
└──────────────┬─────────────────────────┘
               ↓
       Updated Embedding Model
       (v2.4 → v2.5)
               ↓
┌────────────────────────────────────────┐
│ Re-embed All Chunks (offline)          │
│ • Fetch all chunks from VectorDB       │
│ • Re-embed with new model              │
│ • Update vectors in VectorDB           │
│ Duration: ~48 hours (1M chunks)        │
└────────────────────────────────────────┘
```

**Evaluation**:
- Metric: Precision@10, Recall@10, MRR@10 (Mean Reciprocal Rank)
- Target: +5% improvement per monthly cycle

---

### 6.3 Query Understanding Loop

**Objective**: Improve entity extraction, intent classification, complexity scoring.

**Learning Process**:

```
Feedback: "Intent classification wrong"
Correction: "Should be 'interpretazione_norma' not 'validità_atto'"

Training Data Generation:
┌────────────────────────────────────────┐
│ Input: Query                           │
│ Output (system): intent = 'validità_atto' (confidence: 0.85)│
│ Expected (expert): intent = 'interpretazione_norma'│
└──────────────┬─────────────────────────┘
               ↓
    Accumulate 100-500 annotations/month
               ↓
┌────────────────────────────────────────┐
│ Monthly Fine-Tuning                    │
│ • NER Model: BERT fine-tuned on        │
│   corrected entity annotations         │
│ • Intent Classifier: Multi-label BERT  │
│   retrained on corrected intents       │
│ • Complexity Model: Random Forest      │
│   retrained on corrected scores        │
│ Duration: ~6 hours                     │
└────────────────────────────────────────┘
```

**Evaluation**:
- **NER**: F1 score on entity extraction
- **Intent**: Accuracy on intent classification
- **Complexity**: Mean absolute error (MAE) on complexity score
- Target: F1 > 0.90, Accuracy > 0.85, MAE < 0.1

---

### 6.4 Synthesizer Loop

**Objective**: Improve answer synthesis quality (convergent/divergent modes).

**Learning Process**:

```
Feedback: "Risposta troppo breve, manca contesto"
Rating: 2/5

Training Data Generation:
┌────────────────────────────────────────┐
│ Input: Expert outputs (2 experts)      │
│ Output (system): "Il contratto è       │
│         annullabile." (1 sentence)     │
│ Expected (expert): "Il contratto       │
│         firmato da un minorenne è      │
│         annullabile (Art. 1425 c.c.).  │
│         La norma prevede... [3 paragraphs]"│
└──────────────┬─────────────────────────┘
               ↓
    Accumulate 50-200 examples/month
               ↓
┌────────────────────────────────────────┐
│ Monthly Prompt Update                  │
│ • Add examples of good synthesis       │
│   to system prompt                     │
│ • Emphasize provenance completeness    │
│ • Provide counter-examples (bad        │
│   synthesis = too brief)               │
└────────────────────────────────────────┘
```

**Evaluation**:
- Metric: User rating (1-5), answer length, provenance completeness
- Target: Avg rating > 4.0, provenance completeness > 95%

---

## 7. Technology Mapping

### 7.1 RLCF Infrastructure

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Feedback Storage** | PostgreSQL | ACID compliance, JSONB for flexible schemas |
| **Training Data Processing** | Celery + RabbitMQ | Async task queue for batch jobs |
| **Model Training** | Python + PyTorch/Transformers | Standard ML stack for NLP |
| **A/B Testing** | Custom traffic router (Python) | Deterministic routing based on user_id hash |
| **Model Registry** | PostgreSQL + MinIO/S3 | Metadata in PostgreSQL, artifacts in object storage |

---

### 7.2 Model Training Tools

| Model | Training Framework | Infrastructure |
|-------|-------------------|---------------|
| **VectorDB Embeddings** | Sentence-Transformers (PyTorch) | GPU instance (A100, 24 hours) |
| **NER Model** | Hugging Face Transformers | GPU instance (V100, 6 hours) |
| **Intent Classifier** | Scikit-learn / Transformers | CPU instance (4 cores, 2 hours) |
| **Complexity Model** | Scikit-learn (Random Forest) | CPU instance (2 cores, 1 hour) |

---

## 8. Docker Compose Architecture

### 8.1 Service Definitions

```yaml
version: '3.8'

services:
  # RLCF Feedback API
  rlcf-feedback-api:
    build: ./services/rlcf-feedback-api
    ports:
      - "8040:8000"
    environment:
      - POSTGRES_URI=postgresql://merl_t:${POSTGRES_PASSWORD}@postgres:5432/merl_t
      - AUTH_SECRET_KEY=${AUTH_SECRET_KEY}
    depends_on:
      - postgres
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Training Data Generator (Celery Worker)
  training-data-generator:
    build: ./services/training-data-generator
    environment:
      - CELERY_BROKER_URL=amqp://rabbitmq:5672
      - POSTGRES_URI=postgresql://merl_t:${POSTGRES_PASSWORD}@postgres:5432/merl_t
    depends_on:
      - rabbitmq
      - postgres
    deploy:
      replicas: 2

  # Model Update Orchestrator (Celery Beat Scheduler)
  model-update-orchestrator:
    build: ./services/model-update-orchestrator
    environment:
      - CELERY_BROKER_URL=amqp://rabbitmq:5672
      - POSTGRES_URI=postgresql://merl_t:${POSTGRES_PASSWORD}@postgres:5432/merl_t
      - MODEL_REGISTRY_S3_BUCKET=merl-t-models
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    depends_on:
      - rabbitmq
      - postgres

  # A/B Test Router (Traffic Splitter)
  ab-test-router:
    build: ./services/ab-test-router
    ports:
      - "8041:8000"
    environment:
      - POSTGRES_URI=postgresql://merl_t:${POSTGRES_PASSWORD}@postgres:5432/merl_t
      - ROUTER_V2_3_URL=http://router-v2-3:8000
      - ROUTER_V2_4_URL=http://router-v2-4:8000
      - AB_TEST_CONFIG_TABLE=ab_test_config
    depends_on:
      - postgres

  # PostgreSQL (from Storage Layer)
  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_USER=merl_t
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=merl_t
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # RabbitMQ (from Storage Layer)
  rabbitmq:
    image: rabbitmq:3.12-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      - RABBITMQ_DEFAULT_USER=admin
      - RABBITMQ_DEFAULT_PASS=${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

volumes:
  postgres_data:
  rabbitmq_data:
```

---

## 9. Performance Characteristics

### 9.1 Latency

| Operation | Latency | Frequency |
|-----------|---------|-----------|
| **Feedback submission** | < 5s | Per user interaction |
| **Training data generation** | ~1 hour | Daily (batch) |
| **Weekly model update** | ~6 hours | Weekly |
| **Monthly embedding retraining** | ~12 hours | Monthly |
| **Re-embedding corpus** | ~48 hours | After embedding update |
| **A/B test evaluation** | ~10 minutes | Weekly |

---

### 9.2 Throughput

| Operation | Throughput | Conditions |
|-----------|-----------|-----------|
| **Feedback collection** | 1,000 submissions/day | Avg user base |
| **Training data generation** | 500 examples/hour | 2 Celery workers |
| **Model training** | 1 model/week | GPU instance |

---

## 10. Cross-References

### Section 02 Methodology
- **RLCF Framework**: `docs/02-methodology/rlcf-framework.md`
  - §2: Dynamic Authority Calculation
  - §3: Feedback Collection Interface
  - §4: Training Data Generation
  - §5: Model Update Orchestration

### Section 03 Architecture
- **All Layers**: RLCF feedback loop integrated across all components
  - Preprocessing Layer: Query Understanding evolution
  - Orchestration Layer: Router learning
  - Reasoning Layer: Expert/Synthesizer evolution
  - Storage Layer: Embedding fine-tuning

---

## 11. Appendices

### A. Feedback Quality Metrics

**Metrics Tracked**:
- **Feedback volume**: Submissions per day/week
- **Feedback distribution**: Rating distribution (1-5 stars)
- **Authority distribution**: User authority score distribution
- **Correction rate**: % of feedback with structured corrections
- **Consensus rate**: % of feedback validated by multiple experts

---

### B. Model Performance Tracking

**Metrics Dashboard**:
- **Router**: Plan effectiveness (correlation plan ↔ rating)
- **VectorDB**: Precision@10, Recall@10, MRR@10
- **Query Understanding**: NER F1, Intent accuracy, Complexity MAE
- **Synthesizer**: Avg user rating, Provenance completeness

**Alert Thresholds**:
- Rating drop > 0.5 → Alert dev team
- Precision drop > 10% → Rollback model
- Latency increase > 50% → Investigate bottleneck

---

**Document Version**: 1.0
**Last Updated**: 2024-11-03
**Status**: ✅ Complete
