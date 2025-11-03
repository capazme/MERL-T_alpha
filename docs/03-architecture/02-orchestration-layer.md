# Orchestration Layer Architecture

## 1. Introduction

The **Orchestration Layer** is the decision-making core of MERL-T, responsible for analyzing enriched query context and dynamically orchestrating retrieval agents to fetch relevant information. This layer consists of:

1. **LLM Router** (100% LLM-based decision engine)
2. **Retrieval Agent Framework** (KG Agent, API Agent, VectorDB Agent)

**Design Principles**:
- **LLM-Native**: Router uses LLM reasoning (NO hardcoded rules, NO traditional MoE gating)
- **Agent-Based**: Retrieval executed by autonomous agents with standard interfaces
- **Parallel Execution**: Agents run concurrently to minimize latency
- **Adaptive**: Router learns optimal strategies from RLCF feedback
- **Traceable**: Full execution plan logged with trace IDs

**Performance Targets**:
- Router decision: < 2s (LLM inference)
- Agent execution: < 300ms (parallel, dominated by VectorDB)
- Total orchestration: < 2.3s

**Reference**: See `docs/02-methodology/legal-reasoning.md` for theoretical foundation.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│         INPUT FROM PREPROCESSING LAYER                       │
│   QueryContext + EnrichedContext                             │
│   (entities, concepts, intent, norms, complexity)            │
└──────────────────────────┬───────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                    LLM ROUTER                                │
│              (100% LLM-based reasoning)                       │
│                                                              │
│  Input: QueryContext + EnrichedContext + System Prompt      │
│  Process: LLM analyzes context and generates execution plan │
│  Output: ExecutionPlan JSON (structured output)             │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ExecutionPlan:                                      │   │
│  │ • retrieval_plan (which agents to activate)         │   │
│  │ • reasoning_plan (which experts to call)            │   │
│  │ • iteration_strategy (stop criteria)                │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────┬───────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│              AGENT EXECUTION LAYER (parallel)                │
│                                                              │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐ │
│  │  KG Agent   │      │  API Agent  │      │ VectorDB    │ │
│  │             │      │             │      │ Agent       │ │
│  │ Graph       │      │ Akoma Ntoso │      │ Semantic    │ │
│  │ Expansion   │      │ Norm Text   │      │ Retrieval   │ │
│  └──────┬──────┘      └──────┬──────┘      └──────┬──────┘ │
│         │                    │                    │         │
│         │       (parallel execution)             │         │
│         └────────────────────┴────────────────────┘         │
└──────────────────────────┬───────────────────────────────────┘
                           ↓
              ┌────────────────────────┐
              │   RetrievalResult      │
              │   (aggregated data)    │
              └────────────┬───────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│               OUTPUT TO REASONING LAYER                       │
│   RetrievalResult → Experts → Synthesizer                    │
└──────────────────────────────────────────────────────────────┘
```

**Key Characteristics**:
- Router is **stateless** (no memory between requests)
- Agents execute **in parallel** (independent tasks)
- Router output is **structured JSON** (ExecutionPlan schema)
- All decisions **logged** for RLCF feedback loop

---

## 3. LLM Router

**Reference**: `docs/02-methodology/legal-reasoning.md` §3

The LLM Router is a **pure LLM reasoning engine** that analyzes query context and generates a structured execution plan. It is NOT a traditional Mixture-of-Experts (MoE) with gating network—it's an LLM that reasons freely about the optimal retrieval and reasoning strategy.

### 3.1 Router Interface

**Component Interface**:

```json
{
  "component": "llm_router",
  "type": "llm_based_decision_engine",
  "interface": {
    "input": {
      "query_context": "QueryContext object (from Preprocessing Layer)",
      "enriched_context": "EnrichedContext object (from Preprocessing Layer)",
      "conversation_history": "array (optional, for multi-turn)"
    },
    "output": {
      "execution_plan": {
        "retrieval_plan": {
          "kg_agent": "object | null",
          "api_agent": "object | null",
          "vectordb_agent": "object | null"
        },
        "reasoning_plan": {
          "experts": "array (selected expert types)",
          "synthesis_mode": "convergent | divergent"
        },
        "iteration_strategy": {
          "max_iterations": "integer",
          "stop_criteria": "object"
        }
      },
      "rationale": "string (LLM explanation of decisions)",
      "trace_id": "RTR-{timestamp}-{uuid}"
    }
  }
}
```

**Input Example**:

```json
{
  "query_context": {
    "original_query": "È valido un contratto firmato da un minorenne nel 2010?",
    "entities": [
      {"text": "contratto", "type": "LEGAL_OBJECT"},
      {"text": "minorenne", "type": "PERSON"},
      {"text": "2010", "type": "DATE"}
    ],
    "concepts": [
      {
        "concept_id": "capacità_agire",
        "label": "Capacità di agire",
        "related_norms": ["art_2_cc", "art_1425_cc"]
      }
    ],
    "intent": {
      "primary": "validità_atto",
      "confidence": {"validità_atto": 0.92}
    },
    "temporal_scope": {
      "type": "specific_date",
      "reference_date": "2010-01-01"
    },
    "complexity": {"score": 0.62, "level": "medium"}
  },
  "enriched_context": {
    "concepts_enriched": [
      {
        "concept_id": "capacità_agire",
        "mapped_norms": [
          {
            "norm_id": "art_2_cc",
            "article": "2",
            "source": "codice civile",
            "title": "Maggiore età. Capacità di agire"
          }
        ]
      }
    ]
  }
}
```

---

### 3.2 Decision Logic (100% LLM-Based)

**System Prompt Architecture**:

The Router uses a **structured system prompt** that guides the LLM to analyze the input and generate an ExecutionPlan.

```
SYSTEM PROMPT (simplified structure):

You are the MERL-T Legal Reasoning Router. Your role is to analyze a legal query
and generate an optimal execution plan for retrieval agents and reasoning experts.

## Input Context
You receive:
1. QueryContext: Parsed query with entities, concepts, intent, complexity
2. EnrichedContext: KG-enriched concepts with mapped norms and jurisprudence

## Your Task
Generate a structured ExecutionPlan JSON with 3 sections:

### 1. retrieval_plan
Decide which retrieval agents to activate:
- **kg_agent**: For graph expansion queries (related concepts, hierarchical context)
  - Activate when: Need to explore norm relationships, find related concepts
  - Skip when: EnrichedContext already provides sufficient norm mappings

- **api_agent**: For fetching full text of norms from Akoma Ntoso API
  - Activate when: Need complete article text (not just metadata)
  - Provide: List of norm IDs to fetch

- **vectordb_agent**: For semantic similarity search over legal corpus
  - Activate when: Query requires case law, doctrine, or semantic matching
  - Select retrieval pattern: P1-P6 based on query characteristics
  - Provide: Query string, filters, top_k, pattern

### 2. reasoning_plan
Select which reasoning experts to activate:
- **Literal_Interpreter**: For literal textual analysis (low complexity, validità_atto)
- **Systemic_Teleological**: For systematic interpretation (medium/high complexity)
- **Principles_Balancer**: For constitutional principle conflicts (bilanciamento_diritti)
- **Precedent_Analyst**: For case law analysis (evoluzione_giurisprudenziale)

Choose synthesis_mode:
- **convergent**: When experts likely to agree (simple query, clear norms)
- **divergent**: When multiple valid perspectives exist (complex, ambiguous)

### 3. iteration_strategy
Define stop criteria:
- **max_iterations**: Maximum retrieval-reasoning cycles (1-3)
- **stop_criteria**: Conditions to stop early (high confidence, norm clarity)

## Output Format
Return ONLY valid JSON matching ExecutionPlan schema. No markdown, no explanations outside JSON.

## Example Decision Logic

Query: "È valido un contratto firmato da un minorenne?"
Reasoning:
- Intent: validità_atto (validity check)
- Complexity: 0.4 (low-medium)
- Concepts: capacità_agire, validità_contratto
- Norms already mapped: art_2_cc, art_1425_cc

Decision:
- api_agent: Fetch art_2_cc full text (need exact wording)
- vectordb_agent: NOT needed (no case law required for clear rule)
- kg_agent: NOT needed (EnrichedContext sufficient)
- Experts: [Literal_Interpreter] (sufficient for low complexity validity check)
- Synthesis: convergent (single clear answer expected)
- Iterations: 1 (no ambiguity)
```

**LLM Prompt Template**:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "{SYSTEM_PROMPT}"
    },
    {
      "role": "user",
      "content": "QueryContext: {query_context_json}\n\nEnrichedContext: {enriched_context_json}\n\nGenerate ExecutionPlan:"
    }
  ],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "execution_plan",
      "schema": {
        "type": "object",
        "properties": {
          "retrieval_plan": {"type": "object"},
          "reasoning_plan": {"type": "object"},
          "iteration_strategy": {"type": "object"},
          "rationale": {"type": "string"}
        },
        "required": ["retrieval_plan", "reasoning_plan", "iteration_strategy", "rationale"]
      }
    }
  }
}
```

**Processing Flow**:

```
┌──────────────────────────────────────┐
│ 1. Receive QueryContext +            │
│    EnrichedContext                   │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 2. Construct LLM Prompt              │
│    - System prompt (role definition) │
│    - User message (context JSON)     │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 3. LLM Inference                     │
│    - Model: GPT-4o or Claude Sonnet │
│    - Structured output (JSON Schema) │
│    - Latency: ~1-2s                  │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 4. Validate ExecutionPlan            │
│    - Check JSON schema compliance    │
│    - Validate agent task parameters  │
└────────────┬─────────────────────────┘
             ↓
┌──────────────────────────────────────┐
│ 5. Log Decision + Rationale          │
│    - Store for RLCF feedback         │
│    - Trace ID propagation            │
└────────────┬─────────────────────────┘
             ↓
      ExecutionPlan Output
```

---

### 3.3 ExecutionPlan Schema

**Full Schema Definition**:

```json
{
  "execution_plan": {
    "trace_id": "RTR-20241103-abc123",
    "retrieval_plan": {
      "kg_agent": {
        "enabled": true,
        "priority": "high",
        "tasks": [
          {
            "task_type": "expand_related_concepts",
            "parameters": {
              "concept_ids": ["capacità_agire"],
              "depth": 2,
              "relationship_types": ["prerequisito", "conseguenza"]
            }
          },
          {
            "task_type": "hierarchical_traversal",
            "parameters": {
              "norm_ids": ["art_2_cc"],
              "direction": "upward",
              "max_depth": 3
            }
          }
        ]
      },
      "api_agent": {
        "enabled": true,
        "priority": "high",
        "tasks": [
          {
            "task_type": "fetch_norm_text",
            "parameters": {
              "norm_ids": ["art_2_cc", "art_1425_cc"],
              "version_date": "2010-01-01",
              "include_metadata": true
            }
          }
        ]
      },
      "vectordb_agent": {
        "enabled": false,
        "priority": "low",
        "tasks": []
      }
    },
    "reasoning_plan": {
      "experts": [
        {
          "expert_type": "Literal_Interpreter",
          "priority": "high",
          "context_sources": ["api_agent.norm_texts", "enriched_context.mapped_norms"]
        }
      ],
      "synthesis_mode": "convergent",
      "synthesis_parameters": {
        "require_consensus": true,
        "highlight_conflicts": false
      }
    },
    "iteration_strategy": {
      "max_iterations": 1,
      "stop_criteria": {
        "min_confidence": 0.85,
        "norm_ambiguity_threshold": 0.2,
        "expert_consensus": true
      },
      "iteration_conditions": {
        "low_confidence": "iterate_with_additional_retrieval",
        "high_norm_ambiguity": "activate_systemic_teleological_expert",
        "expert_divergence": "iterate_with_precedent_analyst"
      }
    },
    "rationale": "Query asks about contract validity for a minor in 2010. This is a straightforward legal rule (Art. 2 c.c. on capacity to act). EnrichedContext already mapped relevant concepts to norms. Strategy: (1) Fetch full text of Art. 2 c.c. via API Agent to get exact wording for 2010 version. (2) Use Literal Interpreter for textual analysis (sufficient for clear rule). (3) No VectorDB needed (no case law required). (4) Single iteration expected (no ambiguity)."
  }
}
```

**Schema Components**:

| Component | Description | Purpose |
|-----------|-------------|---------|
| **retrieval_plan** | Which agents to activate + their tasks | Orchestrate parallel data fetching |
| **retrieval_plan.{agent}.enabled** | Boolean flag | Quick check if agent should run |
| **retrieval_plan.{agent}.priority** | high/medium/low | Resource allocation (not used in Phase 1) |
| **retrieval_plan.{agent}.tasks[]** | Array of task objects | Specific work for each agent |
| **reasoning_plan** | Which experts to call + synthesis mode | Guide reasoning layer |
| **reasoning_plan.experts[]** | Array of expert configs | Expert selection + priority |
| **reasoning_plan.synthesis_mode** | convergent/divergent | How to combine expert outputs |
| **iteration_strategy** | When to stop, when to iterate | Control multi-turn execution |
| **iteration_strategy.max_iterations** | Integer (1-3) | Hard limit on retrieval cycles |
| **iteration_strategy.stop_criteria** | Object with thresholds | Early stopping conditions |
| **rationale** | String explanation | Human-readable decision rationale (for RLCF) |

---

### 3.4 RLCF Learning Integration

**Feedback Loop**:

```
┌────────────────────────────────────────────────────┐
│ 1. Router generates ExecutionPlan                  │
│    - Log: trace_id, query, plan, rationale         │
└──────────────────┬─────────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────────┐
│ 2. Pipeline executes plan → Final Answer           │
│    - Log: retrieval results, expert outputs        │
└──────────────────┬─────────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────────┐
│ 3. User/Expert provides feedback                   │
│    - Rating: 1-5 stars                             │
│    - Corrections: "Should have activated VectorDB" │
│    - Alternative plan: JSON with better strategy   │
└──────────────────┬─────────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────────┐
│ 4. RLCF Framework processes feedback               │
│    - Store: (query, context, plan, outcome, rating)│
│    - Generate training examples                    │
└──────────────────┬─────────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────────┐
│ 5. Weekly Router Prompt Evolution                  │
│    - Analyze low-rated plans                       │
│    - Update system prompt with learned patterns    │
│    - A/B test new prompt vs old prompt             │
└────────────────────────────────────────────────────┘
```

**Training Data Format**:

```json
{
  "training_example": {
    "id": "train_001",
    "query_context": {...},
    "enriched_context": {...},
    "generated_plan": {...},
    "actual_outcome": {
      "answer_quality": 4,
      "retrieval_sufficiency": 5,
      "expert_selection_appropriateness": 3
    },
    "expert_feedback": {
      "rating": 3,
      "correction": "Should have activated Precedent_Analyst for case law context",
      "improved_plan": {
        "reasoning_plan": {
          "experts": ["Literal_Interpreter", "Precedent_Analyst"]
        }
      }
    },
    "timestamp": "2024-11-03T10:30:00Z"
  }
}
```

**Prompt Evolution Strategy**:

1. **Pattern Extraction**: Analyze 100+ low-rated plans to find common mistakes
2. **Prompt Augmentation**: Add examples of good/bad decisions to system prompt
3. **Few-Shot Learning**: Include 3-5 example ExecutionPlans in prompt
4. **A/B Testing**: Deploy new prompt to 10% of traffic, measure improvement
5. **Gradual Rollout**: If metrics improve, gradually increase to 100%

**Metrics Tracked**:
- **Plan Effectiveness**: Correlation between plan and answer quality rating
- **Retrieval Efficiency**: Agents activated vs actually used in answer
- **Expert Appropriateness**: Expert selection vs intent classification match
- **Iteration Efficiency**: Actual iterations vs max_iterations (goal: minimize)

---

## 4. Agent Architecture

**Reference**: `docs/02-methodology/vector-database.md` §8 (Agent Interface Protocol)

All retrieval agents implement a **standard interface protocol** for task dispatch and result aggregation.

### 4.1 Abstract Agent Interface

**Agent Interface Specification**:

```json
{
  "agent_interface": {
    "endpoint": "{agent_base_url}/execute",
    "method": "POST",
    "headers": {
      "Content-Type": "application/json",
      "X-Trace-ID": "{trace_id}",
      "X-Request-Priority": "high | medium | low"
    },
    "request_body": {
      "agent_type": "kg_agent | api_agent | vectordb_agent",
      "tasks": [
        {
          "task_id": "uuid",
          "task_type": "string (agent-specific)",
          "parameters": "object (agent-specific)",
          "priority": "high | medium | low"
        }
      ],
      "context": {
        "query_context": "QueryContext object",
        "enriched_context": "EnrichedContext object"
      },
      "timeout_ms": 5000
    },
    "response_body": {
      "agent_type": "kg_agent | api_agent | vectordb_agent",
      "results": [
        {
          "task_id": "uuid (matches request)",
          "status": "success | error | timeout",
          "data": "object (agent-specific result)",
          "metadata": {
            "execution_time_ms": 125,
            "data_sources_accessed": ["neo4j", "redis_cache"]
          }
        }
      ],
      "trace_id": "{trace_id}",
      "total_execution_time_ms": 280
    }
  }
}
```

**Error Response**:

```json
{
  "agent_type": "vectordb_agent",
  "results": [
    {
      "task_id": "task_001",
      "status": "error",
      "error": {
        "code": "VDB_CONNECTION_FAILED",
        "message": "Failed to connect to vector database after 3 retries",
        "details": {
          "last_error": "Connection timeout",
          "retry_count": 3
        }
      },
      "metadata": {
        "execution_time_ms": 5000
      }
    }
  ],
  "trace_id": "RTR-20241103-abc123",
  "total_execution_time_ms": 5000
}
```

---

### 4.2 Task Schema Protocol

**KG Agent Task Types**:

| Task Type | Parameters | Output |
|-----------|-----------|--------|
| **expand_related_concepts** | concept_ids, depth, relationship_types | Related concepts with relationships |
| **hierarchical_traversal** | norm_ids, direction (upward/downward), max_depth | Parent/child norms in hierarchy |
| **jurisprudence_lookup** | norm_ids, courts, max_results | Sentenze linked to norms |
| **temporal_version_query** | norm_ids, reference_date | Norm versions valid at date |

**API Agent Task Types**:

| Task Type | Parameters | Output |
|-----------|-----------|--------|
| **fetch_norm_text** | norm_ids, version_date, include_metadata | Full norm texts with metadata |
| **fetch_jurisprudence_text** | sentenza_ids | Full sentenza texts |
| **search_norms_by_title** | title_query, source (codice civile, etc.) | Matching norms |

**VectorDB Agent Task Types**:

| Task Type | Parameters | Output |
|-----------|-----------|--------|
| **semantic_search** (P1) | query, top_k, filters | Top-k semantically similar chunks |
| **hybrid_search** (P2) | query, top_k, alpha, filters | Hybrid semantic + keyword results |
| **filtered_retrieval** (P3) | query, top_k, complex_filters | Filtered results by metadata |
| **reranked_retrieval** (P4) | query, candidate_k, top_k, filters | Cross-encoder reranked results |
| **multi_query_retrieval** (P5) | queries[], top_k_per_query, dedup | Results from multiple query variations |
| **cross_modal_retrieval** (P6) | query, kg_context, top_k, filters | VectorDB + KG enriched results |

---

### 4.3 Parallel Execution Model

**Orchestrator Implementation**:

```
┌───────────────────────────────────────────────────────┐
│ Router generates ExecutionPlan                        │
└────────────────────┬──────────────────────────────────┘
                     ↓
┌───────────────────────────────────────────────────────┐
│ Orchestrator parses retrieval_plan                    │
│ - Identifies enabled agents                           │
│ - Prepares task payloads for each agent               │
└────────────────────┬──────────────────────────────────┘
                     ↓
┌───────────────────────────────────────────────────────┐
│ Dispatch agents in parallel (async HTTP requests)     │
│                                                       │
│  ┌───────────────┐   ┌───────────────┐   ┌─────────┐ │
│  │ POST /execute │   │ POST /execute │   │ POST    │ │
│  │ to KG Agent   │   │ to API Agent  │   │ /execute│ │
│  │ (port 8010)   │   │ (port 8011)   │   │ to VDB  │ │
│  └───────┬───────┘   └───────┬───────┘   └────┬────┘ │
│          │                   │                 │      │
│          └───────────────────┴─────────────────┘      │
│                          ↓                            │
│                 Await all responses                   │
│                 (timeout: 5s per agent)               │
└────────────────────┬──────────────────────────────────┘
                     ↓
┌───────────────────────────────────────────────────────┐
│ Aggregate results                                     │
│ - Merge results from all agents                       │
│ - Handle partial failures (some agents timeout)       │
│ - Construct RetrievalResult object                    │
└────────────────────┬──────────────────────────────────┘
                     ↓
            RetrievalResult Output
```

**Timeout & Fallback Strategy**:

```json
{
  "timeout_config": {
    "kg_agent": {
      "timeout_ms": 1000,
      "fallback": "use_enriched_context"
    },
    "api_agent": {
      "timeout_ms": 3000,
      "fallback": "use_cached_norms"
    },
    "vectordb_agent": {
      "timeout_ms": 5000,
      "fallback": "skip_retrieval"
    }
  }
}
```

**Partial Failure Handling**:

- If **KG Agent** fails → Use EnrichedContext from Preprocessing Layer (already has mapped norms)
- If **API Agent** fails → Use norm metadata from KG (without full text)
- If **VectorDB Agent** fails → Skip semantic retrieval, proceed with norms only

**Result Aggregation**:

```json
{
  "retrieval_result": {
    "trace_id": "RET-20241103-abc123",
    "kg_results": {
      "status": "success",
      "data": {
        "related_concepts": [...],
        "hierarchical_context": [...]
      },
      "execution_time_ms": 45
    },
    "api_results": {
      "status": "success",
      "data": {
        "norm_texts": [
          {
            "norm_id": "art_2_cc",
            "text": "La maggiore età è fissata al compimento del diciottesimo anno...",
            "version_date": "2010-01-01"
          }
        ]
      },
      "execution_time_ms": 280
    },
    "vectordb_results": {
      "status": "skipped",
      "reason": "not_enabled_in_execution_plan"
    },
    "total_execution_time_ms": 280,
    "metadata": {
      "agents_dispatched": 2,
      "agents_succeeded": 2,
      "agents_failed": 0
    }
  }
}
```

---

## 5. KG Agent

**Reference**: `docs/02-methodology/knowledge-graph.md`

The KG Agent executes **graph expansion queries** beyond the initial KG Enrichment performed in the Preprocessing Layer.

### 5.1 Component Interface

```json
{
  "component": "kg_agent",
  "type": "graph_query_executor",
  "interface": {
    "endpoint": "http://kg-agent:8010/execute",
    "input": {
      "tasks": [
        {
          "task_id": "uuid",
          "task_type": "expand_related_concepts | hierarchical_traversal | jurisprudence_lookup | temporal_version_query",
          "parameters": "object (task-specific)"
        }
      ],
      "context": {
        "query_context": "QueryContext",
        "enriched_context": "EnrichedContext"
      }
    },
    "output": {
      "results": [
        {
          "task_id": "uuid",
          "status": "success | error",
          "data": "object (task-specific)",
          "metadata": {
            "execution_time_ms": 45,
            "cypher_queries_executed": 2,
            "nodes_traversed": 18
          }
        }
      ]
    }
  }
}
```

---

### 5.2 Graph Expansion Queries

**Task: expand_related_concepts**

```cypher
// Expand related concepts with multi-hop traversal
MATCH path = (c:ConcettoGiuridico {id: $concept_id})-[:RELAZIONE_CONCETTUALE*1..$depth]-(related:ConcettoGiuridico)
WHERE ALL(r IN relationships(path) WHERE r.relationship_type IN $relationship_types)
WITH related, path,
     reduce(strength = 1.0, r IN relationships(path) | strength * r.strength) AS path_strength
RETURN DISTINCT related.id AS concept_id,
       related.label AS label,
       related.definition AS definition,
       path_strength AS relevance_score,
       [r IN relationships(path) | r.relationship_type] AS relationship_chain
ORDER BY path_strength DESC
LIMIT 10
```

**Parameters**:
```json
{
  "concept_id": "validità_contratto",
  "depth": 2,
  "relationship_types": ["prerequisito", "conseguenza", "alternativa"]
}
```

**Output**:
```json
{
  "task_id": "task_001",
  "status": "success",
  "data": {
    "related_concepts": [
      {
        "concept_id": "capacità_agire",
        "label": "Capacità di agire",
        "definition": "Idoneità del soggetto a compiere atti giuridici...",
        "relevance_score": 0.95,
        "relationship_chain": ["prerequisito"]
      },
      {
        "concept_id": "consenso_parti",
        "label": "Consenso delle parti",
        "definition": "Accordo delle parti sui termini del contratto...",
        "relevance_score": 0.90,
        "relationship_chain": ["prerequisito"]
      }
    ]
  }
}
```

**Task: hierarchical_traversal**

```cypher
// Traverse hierarchical relationships (Costituzione → Legge → Regolamento)
MATCH path = (parent:Norma)-[:GERARCHIA_KELSENIANA*1..$max_depth]->(child:Norma {id: $norm_id})
WHERE $direction = 'upward'
WITH parent, path, length(path) AS distance
RETURN parent.id AS norm_id,
       parent.article AS article,
       parent.source AS source,
       parent.hierarchical_level AS level,
       parent.title AS title,
       distance
ORDER BY distance ASC
LIMIT 5

UNION

// If direction = 'downward'
MATCH path = (parent:Norma {id: $norm_id})-[:GERARCHIA_KELSENIANA*1..$max_depth]->(child:Norma)
WHERE $direction = 'downward'
WITH child, path, length(path) AS distance
RETURN child.id AS norm_id,
       child.article AS article,
       child.source AS source,
       child.hierarchical_level AS level,
       child.title AS title,
       distance
ORDER BY distance ASC
LIMIT 5
```

**Parameters**:
```json
{
  "norm_id": "art_1453_cc",
  "direction": "upward",
  "max_depth": 3
}
```

**Output**:
```json
{
  "task_id": "task_002",
  "status": "success",
  "data": {
    "hierarchical_norms": [
      {
        "norm_id": "art_24_cost",
        "article": "24",
        "source": "Costituzione",
        "level": "Costituzione",
        "title": "Diritto di difesa",
        "distance": 2
      }
    ]
  }
}
```

---

### 5.3 Performance Characteristics

| Query Type | Latency (avg) | Nodes Traversed | Optimization |
|-----------|---------------|-----------------|--------------|
| **expand_related_concepts** (depth=1) | 25ms | 5-10 | Index on concept_id + relationship_type |
| **expand_related_concepts** (depth=2) | 60ms | 20-50 | Limit relationship types |
| **hierarchical_traversal** (depth=3) | 35ms | 8-15 | Index on hierarchical_level |
| **jurisprudence_lookup** | 40ms | 10-20 | Index on court + date_published |
| **temporal_version_query** | 30ms | 5-10 | Index on date_effective |

**Caching Strategy**:
- Cache results for 1 hour (TTL: 3600s)
- Cache key: `kg:{task_type}:{parameters_hash}`
- Cache hit rate: ~60% (many queries repeat within 1 hour)

---

## 6. API Agent

**Reference**: `docs/02-methodology/legal-reasoning.md` §4.2

The API Agent fetches **full text of legal norms** from external Akoma Ntoso API (Italian Government official source).

### 6.1 Component Interface

```json
{
  "component": "api_agent",
  "type": "external_api_client",
  "interface": {
    "endpoint": "http://api-agent:8011/execute",
    "input": {
      "tasks": [
        {
          "task_id": "uuid",
          "task_type": "fetch_norm_text | fetch_jurisprudence_text | search_norms_by_title",
          "parameters": "object (task-specific)"
        }
      ]
    },
    "output": {
      "results": [
        {
          "task_id": "uuid",
          "status": "success | error",
          "data": "object (task-specific)",
          "metadata": {
            "execution_time_ms": 280,
            "api_calls_made": 2,
            "cache_hit": false
          }
        }
      ]
    }
  }
}
```

---

### 6.2 Akoma Ntoso Integration

**External API**: Italian Government Akoma Ntoso API
- Base URL: `https://www.normattiva.it/api/` (example)
- Format: XML (Akoma Ntoso standard) or JSON
- Authentication: None (public API)
- Rate Limit: 100 requests/minute

**Task: fetch_norm_text**

**API Call**:
```
GET https://www.normattiva.it/api/norm/{norm_id}?version={version_date}&format=json
```

**Parameters**:
```json
{
  "norm_ids": ["art_2_cc", "art_1425_cc"],
  "version_date": "2010-01-01",
  "include_metadata": true
}
```

**API Response (Akoma Ntoso JSON)**:
```json
{
  "norm_id": "art_2_cc",
  "article": "2",
  "source": "Codice Civile",
  "title": "Maggiore età. Capacità di agire",
  "version": {
    "date_effective": "1942-03-16",
    "date_end": null,
    "is_current": true
  },
  "text": {
    "full_text": "La maggiore età è fissata al compimento del diciottesimo anno. Con la maggiore età si acquista la capacità di compiere tutti gli atti per i quali non sia stabilita un'età diversa.",
    "structure": {
      "commas": [
        {
          "comma_num": 1,
          "text": "La maggiore età è fissata al compimento del diciottesimo anno."
        },
        {
          "comma_num": 2,
          "text": "Con la maggiore età si acquista la capacità di compiere tutti gli atti per i quali non sia stabilita un'età diversa."
        }
      ]
    }
  },
  "metadata": {
    "hierarchical_level": "Legge Ordinaria",
    "binding_force": 1.0,
    "citation_count": 1542
  }
}
```

**Agent Output**:
```json
{
  "task_id": "task_003",
  "status": "success",
  "data": {
    "norm_texts": [
      {
        "norm_id": "art_2_cc",
        "article": "2",
        "source": "Codice Civile",
        "title": "Maggiore età. Capacità di agire",
        "text": "La maggiore età è fissata al compimento del diciottesimo anno. Con la maggiore età si acquista la capacità di compiere tutti gli atti per i quali non sia stabilita un'età diversa.",
        "version_date": "1942-03-16",
        "is_current": true,
        "metadata": {
          "hierarchical_level": "Legge Ordinaria",
          "binding_force": 1.0
        }
      }
    ]
  },
  "metadata": {
    "execution_time_ms": 280,
    "api_calls_made": 2,
    "cache_hit": false
  }
}
```

---

### 6.3 Multivigenza Support

**Challenge**: Italian law has **multivigenza** (multiple valid versions of norms over time).

**Solution**: Version-aware retrieval using `version_date` parameter.

**Example**:
- Query asks: "Quali erano i requisiti nel 2010?" (What were the requirements in 2010?)
- Temporal Extraction Module detects: `reference_date = 2010-01-01`
- Router passes `version_date = 2010-01-01` to API Agent
- API Agent fetches norm version valid on 2010-01-01

**API Logic**:
```
IF version_date IS PROVIDED:
    Fetch norm version WHERE:
        date_effective <= version_date
        AND (date_end >= version_date OR date_end IS NULL)
ELSE:
    Fetch current version (is_current = true)
```

---

### 6.4 Caching Strategy

**Cache Layer**: Redis

**Cache Key**:
```
api:norm:{norm_id}:{version_date}
```

**Cache TTL**:
- Current version (`version_date = null`): 24 hours
- Historical version: 7 days (rarely changes)

**Cache Hit Rate**: ~85% (most queries ask for current law)

**Performance**:
- Cache miss: 280ms (API call + parsing)
- Cache hit: 5ms (Redis lookup)

**Cache Invalidation**:
- Manual invalidation when new law published
- Automatic TTL expiration

---

## 7. VectorDB Agent

**Reference**: `docs/02-methodology/vector-database.md`

The VectorDB Agent executes **semantic similarity search** over the legal corpus using 6 retrieval patterns (P1-P6).

### 7.1 Component Interface

```json
{
  "component": "vectordb_agent",
  "type": "semantic_retrieval_engine",
  "interface": {
    "endpoint": "http://vectordb-agent:8012/execute",
    "input": {
      "tasks": [
        {
          "task_id": "uuid",
          "task_type": "semantic_search | hybrid_search | filtered_retrieval | reranked_retrieval | multi_query_retrieval | cross_modal_retrieval",
          "parameters": "object (pattern-specific)"
        }
      ]
    },
    "output": {
      "results": [
        {
          "task_id": "uuid",
          "status": "success | error",
          "data": {
            "chunks": [
              {
                "chunk_id": "uuid",
                "text": "string",
                "score": 0.89,
                "metadata": "object"
              }
            ]
          },
          "metadata": {
            "execution_time_ms": 225,
            "pattern_used": "P4_reranked_retrieval",
            "candidates_retrieved": 50,
            "final_results": 10
          }
        }
      ]
    }
  }
}
```

---

### 7.2 Retrieval Pattern Catalog (P1-P6)

**Reference**: `docs/02-methodology/vector-database.md` §5

**P1: Semantic Search** (Basic vector similarity)

```json
{
  "task_type": "semantic_search",
  "parameters": {
    "query": "risoluzione per inadempimento",
    "top_k": 20,
    "filters": {
      "temporal_metadata.is_current": true,
      "classification.legal_area": "civil"
    }
  }
}
```

**Processing**:
1. Embed query → query_vector [3072 dims]
2. Apply metadata filters
3. HNSW approximate nearest neighbor search
4. Return top-k by cosine similarity

**Output**:
```json
{
  "chunks": [
    {
      "chunk_id": "uuid-1",
      "text": "Art. 1453 c.c. - Nei contratti con prestazioni corrispettive...",
      "score": 0.89,
      "metadata": {
        "document_type": "norm",
        "norm_id": "art_1453_cc",
        "source": "codice civile"
      }
    }
  ]
}
```

---

**P2: Hybrid Search** (Vector + Keyword)

```json
{
  "task_type": "hybrid_search",
  "parameters": {
    "query": "risoluzione per inadempimento",
    "top_k": 20,
    "alpha": 0.7,
    "filters": {
      "temporal_metadata.is_current": true
    }
  }
}
```

**Processing**:
1. Semantic search → vector_scores
2. BM25 keyword search → keyword_scores
3. Score fusion: `combined = alpha * vector + (1 - alpha) * keyword`
4. Rerank by combined score

**Alpha Parameter**:
- `alpha = 1.0`: Pure semantic (ignores keywords)
- `alpha = 0.7`: Balanced (default)
- `alpha = 0.3`: Keyword-heavy (for exact term matching)

---

**P3: Filtered Retrieval** (Complex metadata filtering)

```json
{
  "task_type": "filtered_retrieval",
  "parameters": {
    "query": "clausole vessatorie",
    "top_k": 15,
    "filters": {
      "temporal_metadata.reference_date": "2010-01-01",
      "classification.legal_area": "civil",
      "authority_metadata.hierarchical_level": ["Costituzione", "Legge Ordinaria"],
      "entities_extracted.norm_references": {"$contains": "art_1341_cc"}
    }
  }
}
```

**Filter Types**:
- **Temporal**: `is_current`, `reference_date`, `date_range`
- **Hierarchical**: `hierarchical_level` (filter by norm authority)
- **Domain**: `legal_area`, `legal_domain_tags`
- **Document Type**: `document_type` (norm, jurisprudence, doctrine)
- **Entity**: `norm_references`, `case_references` (contains specific entities)

---

**P4: Reranked Retrieval** (Two-stage: recall → precision)

```json
{
  "task_type": "reranked_retrieval",
  "parameters": {
    "query": "È valido un contratto firmato da un minorenne?",
    "candidate_k": 50,
    "top_k": 10,
    "reranker_model": "cross_encoder_bert",
    "filters": {
      "temporal_metadata.is_current": true
    }
  }
}
```

**Processing**:
1. **Stage 1 (Recall)**: Semantic search retrieves top-50 candidates (fast, HNSW)
2. **Stage 2 (Precision)**: Cross-encoder BERT reranks candidates pairwise (slow, accurate)
3. Return top-10 after reranking

**Cross-Encoder**:
- Model: `cross-encoder/ms-marco-MiniLM-L-6-v2` fine-tuned on Italian legal data
- Input: `[CLS] query [SEP] chunk_text [SEP]`
- Output: Relevance score 0.0-1.0
- Latency: ~2s for 50 pairs

---

**P5: Multi-Query Retrieval** (Query variations)

```json
{
  "task_type": "multi_query_retrieval",
  "parameters": {
    "queries": [
      "È valido un contratto firmato da un minorenne?",
      "Capacità di agire del minorenne nei contratti",
      "Requisiti di validità contratto minore età"
    ],
    "top_k_per_query": 15,
    "deduplication": true,
    "final_top_k": 20
  }
}
```

**Use Case**: When Router detects ambiguous query, generate multiple reformulations.

**Processing**:
1. Execute semantic search for each query variation
2. Collect results (3 queries × 15 results = 45 total)
3. Deduplicate by `chunk_id`
4. Rerank by max score across queries
5. Return top-20

---

**P6: Cross-Modal Retrieval** (VectorDB + KG enrichment)

```json
{
  "task_type": "cross_modal_retrieval",
  "parameters": {
    "query": "risoluzione contratto inadempimento",
    "kg_context": {
      "concepts": ["risoluzione_contratto", "inadempimento"],
      "related_norms": ["art_1453_cc", "art_1454_cc"]
    },
    "top_k": 20,
    "boost_kg_norms": 1.5
  }
}
```

**Processing**:
1. Semantic search for query
2. **Boost** chunks that mention norms in `kg_context.related_norms`
3. Apply boost factor: `boosted_score = score * 1.5` if chunk references KG norm
4. Rerank by boosted score

**Use Case**: When KG already identified relevant norms, prioritize chunks that cite those norms.

---

### 7.3 Hybrid Search Implementation

**Architecture**:

```
┌────────────────────────────────────────────────────┐
│ Query: "risoluzione per inadempimento"             │
└─────────────────┬──────────────────────────────────┘
                  ↓
    ┌─────────────┴─────────────┐
    │                           │
    ↓                           ↓
┌─────────────────┐   ┌─────────────────┐
│ Semantic Search │   │ Keyword Search  │
│ (HNSW Index)    │   │ (BM25 Index)    │
│                 │   │                 │
│ Embed query     │   │ Tokenize query  │
│ → vector search │   │ → BM25 scoring  │
└────────┬────────┘   └────────┬────────┘
         │                     │
         ↓                     ↓
    vector_scores         keyword_scores
         │                     │
         └──────────┬──────────┘
                    ↓
         ┌──────────────────────┐
         │ Score Fusion         │
         │ combined = alpha * V │
         │          + (1-α) * K │
         └──────────┬───────────┘
                    ↓
              Rerank by combined
                    ↓
             Top-k Results
```

**Score Fusion Formula**:

```
For each chunk i:
  vector_score_i = cosine_similarity(query_vector, chunk_vector_i)
  keyword_score_i = BM25(query_tokens, chunk_tokens_i)

  // Normalize scores to [0, 1]
  vector_score_norm_i = (vector_score_i - min_vector) / (max_vector - min_vector)
  keyword_score_norm_i = (keyword_score_i - min_keyword) / (max_keyword - min_keyword)

  // Fuse with alpha weighting
  combined_score_i = alpha * vector_score_norm_i + (1 - alpha) * keyword_score_norm_i

Sort chunks by combined_score_i descending
Return top_k
```

---

### 7.4 Reranking Pipeline

**Two-Stage Retrieval**:

```
Stage 1: RECALL (Fast, Lower Precision)
┌──────────────────────────────────────┐
│ Semantic Search (HNSW)               │
│ Retrieve top-50 candidates           │
│ Latency: ~100ms                      │
└────────────┬─────────────────────────┘
             ↓
      Top-50 Candidates
             ↓
Stage 2: PRECISION (Slow, Higher Precision)
┌──────────────────────────────────────┐
│ Cross-Encoder Reranking              │
│ Pairwise relevance scoring           │
│ For each candidate:                  │
│   Input: [CLS] query [SEP] chunk [SEP]│
│   Output: relevance_score (0.0-1.0) │
│ Latency: ~2s for 50 pairs            │
└────────────┬─────────────────────────┘
             ↓
   Rerank by relevance_score
             ↓
      Top-10 Final Results
```

**Cross-Encoder Model**:
- Base: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Fine-tuned on: 5,000 (query, chunk, relevance) triplets from RLCF feedback
- Input: Query + chunk text (max 512 tokens)
- Output: Relevance score 0.0-1.0
- Performance: ~40ms per pair (50 pairs = ~2s total)

**When to Use Reranking**:
- Query complexity > 0.6 (medium/high)
- Intent requires precision (e.g., `validità_atto`)
- User requests "accurate" results (explicit flag)

---

## 8. Technology Mapping

### 8.1 LLM Router

| Technology | Description | Rationale | Phase |
|-----------|-------------|-----------|-------|
| **GPT-4o** | OpenAI LLM with structured output | Best structured output support, JSON Schema validation | 2-3 |
| **Claude Sonnet 3.5** | Anthropic LLM | Alternative to GPT-4o, lower cost | 3+ |
| **Gemini 1.5 Pro** | Google LLM | Experimental alternative | 4+ |

**Key Requirement**: **Native JSON Schema support** for structured ExecutionPlan output.

---

### 8.2 Agent Infrastructure

| Component | Abstract Interface | Technology Options | Recommended | Rationale |
|-----------|-------------------|-------------------|------------|-----------|
| **Agent Framework** | REST API with JSON | • FastAPI<br>• Flask + Gunicorn<br>• Node.js Express | **FastAPI** | Async, auto docs, type hints |
| **Orchestrator** | Async HTTP client | • Python httpx<br>• aiohttp<br>• requests + ThreadPoolExecutor | **httpx** | Modern async HTTP, timeout support |
| **Task Queue** | Async job queue | • Celery + RabbitMQ<br>• Redis Queue<br>• AWS SQS | **Celery + RabbitMQ** | Mature, retry logic, monitoring |

---

### 8.3 VectorDB Agent

| Component | Abstract Interface | Technology Options | Recommended | Rationale |
|-----------|-------------------|-------------------|------------|-----------|
| **Vector Database** | Vector similarity + metadata filters | • Weaviate<br>• Qdrant<br>• Pinecone<br>• pgvector | **Weaviate** | Hybrid search native, GraphQL API, open-source option |
| **Embedding Model** | Text → vector (3072 dims) | • text-embedding-3-large (OpenAI)<br>• multilingual-e5-large<br>• Fine-tuned legal embeddings | **text-embedding-3-large** (Phase 1-2)<br>**Fine-tuned** (Phase 3+) | Best quality for Italian, legal domain |
| **Cross-Encoder** | Pairwise relevance scoring | • ms-marco-MiniLM-L-6-v2<br>• Legal-BERT fine-tuned<br>• Custom trained | **ms-marco-MiniLM fine-tuned** | Balance speed/accuracy |
| **BM25 Index** | Keyword search | • Elasticsearch<br>• Weaviate BM25<br>• Custom (Lucene) | **Weaviate BM25** | Integrated with vector DB, no separate service |

---

### 8.4 KG Agent & API Agent

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **KG Database** | Neo4j | Industry standard, best Cypher support |
| **API Client** | httpx (Python) | Async, timeout handling, retry logic |
| **Cache** | Redis | Fast, TTL support, persistent |

---

## 9. Docker Compose Architecture

### 9.1 Service Definitions

```yaml
version: '3.8'

services:
  # LLM Router Service
  router:
    build: ./services/router
    ports:
      - "8020:8000"
    environment:
      - LLM_PROVIDER=openai
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - PREPROCESSING_URL=http://query-understanding:8000
      - KG_AGENT_URL=http://kg-agent:8000
      - API_AGENT_URL=http://api-agent:8000
      - VECTORDB_AGENT_URL=http://vectordb-agent:8000
    depends_on:
      - query-understanding
      - kg-enrichment
      - kg-agent
      - api-agent
      - vectordb-agent
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # KG Agent
  kg-agent:
    build: ./services/kg-agent
    ports:
      - "8010:8000"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - REDIS_URI=redis://redis:6379
      - CACHE_TTL_SECONDS=3600
    depends_on:
      - neo4j
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # API Agent
  api-agent:
    build: ./services/api-agent
    ports:
      - "8011:8000"
    environment:
      - AKOMA_NTOSO_API_URL=https://www.normattiva.it/api
      - REDIS_URI=redis://redis:6379
      - CACHE_TTL_SECONDS=86400
      - REQUEST_TIMEOUT_MS=3000
      - MAX_RETRIES=3
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # VectorDB Agent
  vectordb-agent:
    build: ./services/vectordb-agent
    ports:
      - "8012:8000"
    environment:
      - WEAVIATE_URL=http://weaviate:8080
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - EMBEDDING_MODEL=text-embedding-3-large
      - CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
      - REDIS_URI=redis://redis:6379
    depends_on:
      - weaviate
      - redis
    volumes:
      - ./models:/models
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Weaviate Vector Database
  weaviate:
    image: semitechnologies/weaviate:1.22.4
    ports:
      - "8080:8080"
    environment:
      - AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true
      - PERSISTENCE_DATA_PATH=/var/lib/weaviate
      - DEFAULT_VECTORIZER_MODULE=none
      - ENABLE_MODULES=text2vec-openai,generative-openai
      - CLUSTER_HOSTNAME=node1
    volumes:
      - weaviate_data:/var/lib/weaviate
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/v1/.well-known/ready"]
      interval: 30s
      timeout: 10s
      retries: 5

  # Neo4j (from Preprocessing Layer)
  neo4j:
    image: neo4j:5.13-enterprise
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
    volumes:
      - neo4j_data:/data

  # Redis (from Preprocessing Layer)
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  # RabbitMQ (Message Queue)
  rabbitmq:
    image: rabbitmq:3.12-management
    ports:
      - "5672:5672"   # AMQP
      - "15672:15672" # Management UI
    environment:
      - RABBITMQ_DEFAULT_USER=admin
      - RABBITMQ_DEFAULT_PASS=${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  weaviate_data:
  neo4j_data:
  redis_data:
  rabbitmq_data:
```

---

### 9.2 Network Topology

```
┌────────────────────────────────────────────────────────────┐
│               Docker Bridge Network (merl-t-network)       │
│                                                            │
│  ┌──────────────┐                                         │
│  │   Router     │                                         │
│  │   :8020      │                                         │
│  └───────┬──────┘                                         │
│          │                                                │
│          ├────────────┬──────────────┬──────────────┐    │
│          │            │              │              │    │
│          ↓            ↓              ↓              ↓    │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────┐│
│  │ KG Agent   │ │ API Agent  │ │ VectorDB   │ │ Query  ││
│  │ :8010      │ │ :8011      │ │ Agent      │ │ Understand│
│  └──────┬─────┘ └──────┬─────┘ │ :8012      │ │ :8001  ││
│         │              │        └──────┬─────┘ └────┬───┘│
│         │              │               │             │    │
│         ↓              ↓               ↓             ↓    │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────┐│
│  │  Neo4j     │ │  Redis     │ │  Weaviate  │ │ Redis  ││
│  │  :7687     │ │  :6379     │ │  :8080     │ │ (cache)││
│  └────────────┘ └────────────┘ └────────────┘ └────────┘│
│                                                            │
└────────────────────────────────────────────────────────────┘

External Access:
- Router API: http://localhost:8020
- KG Agent: http://localhost:8010
- API Agent: http://localhost:8011
- VectorDB Agent: http://localhost:8012
- Weaviate: http://localhost:8080
```

---

## 10. Error Handling & Resilience

### 10.1 Router Error Handling

**LLM Inference Failures**:
- **Timeout**: Retry 3 times with exponential backoff (2s, 4s, 8s)
- **Invalid JSON**: Log error, return default ExecutionPlan (activate all agents, all experts)
- **Rate Limit**: Queue request, retry after rate limit window

**Default ExecutionPlan** (fallback):
```json
{
  "retrieval_plan": {
    "kg_agent": {"enabled": true},
    "api_agent": {"enabled": true},
    "vectordb_agent": {"enabled": true}
  },
  "reasoning_plan": {
    "experts": ["Literal_Interpreter", "Systemic_Teleological"],
    "synthesis_mode": "convergent"
  },
  "iteration_strategy": {
    "max_iterations": 1
  }
}
```

---

### 10.2 Agent Error Handling

**Agent Timeout**:
- Timeout per agent: 5s (configurable)
- If timeout → Mark agent as `status: "timeout"`, continue with other agents
- Partial results OK (2/3 agents succeed → proceed)

**Agent Connection Failure**:
- Retry 2 times with 500ms delay
- If all retries fail → Use fallback:
  - KG Agent fail → Use EnrichedContext from Preprocessing Layer
  - API Agent fail → Use norm metadata only (no full text)
  - VectorDB Agent fail → Skip semantic retrieval

**Partial Failure Strategy**:
```
If 0/3 agents succeed → CRITICAL ERROR, return error to user
If 1/3 agents succeed → WARNING, proceed with degraded context
If 2/3 agents succeed → INFO, proceed normally
If 3/3 agents succeed → SUCCESS
```

---

### 10.3 Circuit Breaker

**Per-Agent Circuit Breaker**:

```json
{
  "circuit_breaker_config": {
    "agent": "vectordb_agent",
    "failure_threshold": 5,
    "timeout_seconds": 10,
    "reset_timeout_seconds": 60,
    "half_open_requests": 1
  }
}
```

**States**:
- **CLOSED**: Normal, requests pass through
- **OPEN**: Failures exceed threshold → Reject requests immediately (return empty results)
- **HALF_OPEN**: After reset timeout → Allow 1 test request

---

## 11. Performance Characteristics

### 11.1 Latency Breakdown

```
Total Orchestration Latency: ~2.3s (P95)

┌─────────────────────────────────────────────────┐
│ Router Decision (LLM Inference): 1.8s           │
│ ├─ Prompt construction: 50ms                    │
│ ├─ LLM API call: 1.6s                           │
│ └─ JSON validation: 150ms                       │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Agent Execution (parallel): 300ms               │
│ ├─ KG Agent: 45ms                               │
│ ├─ API Agent: 280ms (bottleneck)                │
│ └─ VectorDB Agent: 225ms                        │
│                                                 │
│ (Parallel: max(45, 280, 225) = 280ms)          │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Result Aggregation: 20ms                        │
└─────────────────────────────────────────────────┘

Total: 1.8s + 0.3s + 0.02s = 2.12s (average)
       2.3s (P95, includes retry overhead)
```

---

### 11.2 Throughput

| Metric | Value | Conditions |
|--------|-------|-----------|
| **Requests/sec** | 3 req/s | Single Router instance (LLM bottleneck) |
| **Requests/sec** | 15 req/s | 5 Router instances (horizontal scaling) |
| **Agent requests/sec** | 50 req/s | Single agent instance (parallel execution helps) |

**Bottleneck**: LLM Router inference (~1.8s per request)

**Optimization**:
- **Batch requests**: Group multiple queries → Single LLM call with array (Phase 4+)
- **Cache ExecutionPlans**: Cache for identical QueryContext (TTL: 10 min)
- **Streaming**: Stream LLM response to start agent execution earlier (Phase 5+)

---

### 11.3 Resource Requirements

**Router Service**:
- CPU: 1 core (I/O bound, waiting on LLM)
- RAM: 512MB
- Storage: 100MB

**KG Agent**:
- CPU: 1 core
- RAM: 1GB
- Storage: 100MB

**API Agent**:
- CPU: 1 core
- RAM: 512MB
- Storage: 100MB

**VectorDB Agent**:
- CPU: 2 cores
- RAM: 4GB (cross-encoder model loaded)
- Storage: 3GB (embedding model + cross-encoder)

**Weaviate**:
- CPU: 4 cores
- RAM: 8GB
- Storage: 100GB (vector index)

---

## 12. Cross-References

### Section 02 Methodology
- **Legal Reasoning**: `docs/02-methodology/legal-reasoning.md`
  - §3: LLM Router (100% LLM-based, no hardcoded rules)
  - §4: Agent-Based Retrieval (KG Agent, API Agent, VectorDB Agent)
  - §5: ExecutionPlan schema and iteration strategy

- **Vector Database**: `docs/02-methodology/vector-database.md`
  - §5: Retrieval Pattern Catalog (P1-P6)
  - §8: Agent Interface Protocol (VectorDB Agent task schemas)

- **Knowledge Graph**: `docs/02-methodology/knowledge-graph.md`
  - §3: Graph Query Patterns (used by KG Agent)

### Section 03 Architecture
- **Preprocessing Layer**: `docs/03-architecture/01-preprocessing-layer.md`
  - Router consumes QueryContext + EnrichedContext from Preprocessing Layer

- **Reasoning Layer**: `docs/03-architecture/03-reasoning-layer.md` (next)
  - Reasoning Experts consume RetrievalResult from Orchestration Layer

### Section 04 Implementation
- **Router Service**: `docs/04-implementation/router-service.md` (future)
- **Agent Services**: `docs/04-implementation/agent-services.md` (future)

---

## 13. Appendices

### A. Observability

**Logging**:
- **Router**: Log ExecutionPlan + rationale + LLM latency
- **Agents**: Log task execution time + data sources accessed
- **Format**: JSON structured logs with trace_id propagation

**Metrics**:
- **Router**: LLM latency (P50, P95, P99), ExecutionPlan validation failures
- **Agents**: Task execution latency, cache hit rate, error rate
- **Orchestration**: Total latency, partial failure rate, agent timeout rate

**Tracing**:
- **OpenTelemetry**: Full distributed tracing across Router + 3 Agents
- **Trace ID**: Propagated via `X-Trace-ID` header
- **Spans**: Router (parent), Agent execution (children), nested agent tasks

---

### B. Security

**Authentication**:
- **Internal**: Mutual TLS between Router ↔ Agents
- **External**: JWT bearer tokens for Router API

**Authorization**:
- **Router**: Requires valid user JWT (user_id, role)
- **Agents**: Internal-only, not exposed externally

**Rate Limiting**:
- **Router**: 100 requests/minute per user
- **LLM API**: Respect OpenAI rate limits (10,000 requests/min for Tier 3)

---

### C. Scalability

**Horizontal Scaling**:
- **Router**: Stateless, scale to N instances behind load balancer
- **Agents**: Stateless, scale independently (e.g., 5x VectorDB Agent, 2x KG Agent)
- **Weaviate**: Horizontal scaling via sharding (Phase 4+)

**Auto-Scaling**:
- **Kubernetes HPA**: Scale based on CPU utilization (target: 70%)
- **Router**: Scale up if LLM queue > 10 requests
- **VectorDB Agent**: Scale up if avg latency > 500ms

---

**Document Version**: 1.0
**Last Updated**: 2024-11-03
**Status**: ✅ Complete
