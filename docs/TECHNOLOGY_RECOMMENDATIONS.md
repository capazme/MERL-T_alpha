# MERL-T: Raccomandazioni Tecnologiche 2025

**Versione**: 1.0
**Data**: 3 Novembre 2025
**Aggiornato con**: Ricerche tecnologie state-of-the-art 2025

---

## Indice

1. [Introduzione](#introduzione)
2. [Stack Tecnologico Consigliato](#stack-tecnologico-consigliato)
3. [LLM Orchestration](#llm-orchestration)
4. [Vector Databases](#vector-databases)
5. [Graph Databases](#graph-databases)
6. [Backend Framework](#backend-framework)
7. [Embedding Models](#embedding-models)
8. [NLP Models (Legal Italian)](#nlp-models-legal-italian)
9. [RLHF Framework](#rlhf-framework)
10. [Observability Stack](#observability-stack)
11. [Confronto Costi](#confronto-costi)
12. [Decision Matrix](#decision-matrix)

---

## Introduzione

Questo documento fornisce raccomandazioni tecnologiche aggiornate per l'implementazione di MERL-T, basate su:
- Ricerche sulle tecnologie più avanzate disponibili nel 2025
- Performance benchmarks pubblicati
- Considerazioni su costi, scalabilità e maturità dell'ecosistema
- Requisiti specifici del dominio legal AI

**Filosofia**: Bilanciare **innovazione** (tecnologie cutting-edge) con **stabilità** (ecosistemi maturi e supporto).

---

## Stack Tecnologico Consigliato

### Architettura Generale

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER                           │
│  React + Next.js + TypeScript + TailwindCSS                 │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                   ORCHESTRATION                             │
│  LangGraph (stato complesso) | DSPy (reasoning pipelines)   │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND SERVICES                          │
│  Litestar (high-perf) | FastAPI (ecosystem)                 │
│  + SQLAlchemy 2.0 + Pydantic 2.5                           │
└─────────────────────┬───────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                   STORAGE LAYER                             │
│  PostgreSQL (relational) | Memgraph (graph, real-time)      │
│  Qdrant (vectors) | Redis (cache)                           │
└─────────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                   AI/ML LAYER                               │
│  Embeddings: Voyage Multilingual 2 | multilingual-e5       │
│  NLP: ITALIAN-LEGAL-BERT                                    │
│  LLM: OpenRouter (multi-provider)                           │
└─────────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────────┐
│                   OBSERVABILITY                             │
│  OpenTelemetry + SigNoz (open-source) | Datadog (enterprise)│
└─────────────────────────────────────────────────────────────┘
```

---

## LLM Orchestration

### Raccomandazioni

**Option A: LangGraph** (Consigliato per MERL-T)
- **Pro**:
  - Gestione stato complessa (perfect fit per iteration controller)
  - Supporto cicli e feedback loops (RLCF)
  - Controllo granulare su agent workflow
  - Built on LangChain (ecosistema maturo)
- **Contro**:
  - Learning curve più ripida
  - Più verboso di DSPy
- **Use case MERL-T**: LLM Router con multi-iteration, ExecutionPlan con conditional branching

**Option B: DSPy** (Alternativa per reasoning pipelines)
- **Pro**:
  - Performance eccellente (fast inference)
  - Design model-centric (meno prompt engineering)
  - Forte su eval-driven development
- **Contro**:
  - Meno trasparenza nei logs
  - No native OpenAI message compatibility
- **Use case MERL-T**: Expert reasoning pipelines (se si vuole ottimizzare prompt via eval automatico)

**Option C: LangChain** (Baseline, ma superato)
- **Pro**: Ecosistema vastissimo, documentazione
- **Contro**: Performance inferiore, meno controllo su stato complesso
- **Verdict**: OK per prototyping, ma passare a LangGraph per production

### Implementazione Consigliata

**Fase 1-2 (MVP)**: LangChain per rapidità
**Fase 3+ (Orchestration)**: Migrazione a **LangGraph**
**Fase 4 (Reasoning)**: Considerare **DSPy** per expert prompts se si vuole auto-ottimizzazione

**Codice esempio LangGraph per MERL-T Router**:
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence
import operator

class RouterState(TypedDict):
    query_context: dict
    enriched_context: dict
    execution_plan: dict
    retrieval_result: dict
    expert_outputs: Annotated[Sequence[dict], operator.add]
    final_answer: dict
    iteration_count: int

# Define graph
workflow = StateGraph(RouterState)

# Add nodes
workflow.add_node("router", generate_execution_plan)
workflow.add_node("kg_agent", execute_kg_agent)
workflow.add_node("api_agent", execute_api_agent)
workflow.add_node("vectordb_agent", execute_vectordb_agent)
workflow.add_node("experts", run_experts_parallel)
workflow.add_node("synthesizer", synthesize_answer)
workflow.add_node("should_iterate", iteration_controller)

# Define edges (flow control)
workflow.set_entry_point("router")
workflow.add_edge("router", "kg_agent")
workflow.add_edge("router", "api_agent")
workflow.add_edge("router", "vectordb_agent")
workflow.add_edge(["kg_agent", "api_agent", "vectordb_agent"], "experts")
workflow.add_edge("experts", "synthesizer")

# Conditional branching
workflow.add_conditional_edges(
    "should_iterate",
    lambda state: "router" if state["iteration_count"] < 3 and state["final_answer"]["confidence"] < 0.85 else END,
    {
        "router": "router",
        END: END
    }
)

app = workflow.compile()
```

### Decision: **LangGraph** per MERL-T

---

## Vector Databases

### Benchmark Comparison (1M vectors, 768-dim)

| Database  | P95 Latency | Throughput (QPS) | Memory  | Hybrid Search | Cost (self-hosted) |
|-----------|-------------|------------------|---------|---------------|-------------------|
| **Qdrant**   | 30-40 ms    | 8,000-15,000     | ~3GB    | Yes           | €€                |
| **Milvus**   | 50-80 ms    | 10,000-20,000    | ~4GB    | Yes           | €€€               |
| **Weaviate** | 50-70 ms    | 3,000-8,000      | ~3.5GB  | Native        | €€                |

### Raccomandazione per MERL-T: **Qdrant**

**Rationale**:
1. **Latency critica**: MERL-T target P95 < 300ms per VectorDB Agent → Qdrant vince
2. **Cost-effective**: Self-hosted su K8s, licensing open-source (Apache 2.0)
3. **Hybrid search**: Supportato (vector + BM25), essenziale per pattern P2
4. **Filtering**: Advanced metadata filtering per pattern P3 (temporal, hierarchical)
5. **Quantization**: Supporto product quantization → riduce memory footprint
6. **API**: Python client maturo, async/await compatible

**Alternative considerate**:
- **Milvus**: Se si prevede >50M vectors in futuro (attualmente overkill)
- **Weaviate**: Se si vuole GraphQL API nativa (non necessario per MERL-T)

**Implementazione**:
```yaml
# docker-compose.yml
qdrant:
  image: qdrant/qdrant:v1.7.4
  ports:
    - "6333:6333"  # HTTP API
    - "6334:6334"  # gRPC (optional)
  volumes:
    - qdrant_storage:/qdrant/storage
  environment:
    - QDRANT__SERVICE__GRPC_PORT=6334
```

```python
# backend/orchestration/agents/vectordb_agent.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

client = QdrantClient(host="localhost", port=6333)

# Create collection
client.create_collection(
    collection_name="legal_corpus",
    vectors_config=VectorParams(
        size=3072,  # text-embedding-3-large
        distance=Distance.COSINE
    )
)

# Hybrid search (P2)
results = client.search(
    collection_name="legal_corpus",
    query_vector=query_embedding,
    query_filter={
        "must": [
            {"key": "document_type", "match": {"value": "norm"}},
            {"key": "temporal_metadata.is_current", "match": {"value": True}}
        ]
    },
    limit=20,
    with_payload=True
)
```

### Decision: **Qdrant**

---

## Graph Databases

### Benchmark Comparison

| Database    | Storage     | Write Perf       | Read Perf        | Best For                    | Cost      |
|-------------|-------------|------------------|------------------|-----------------------------|-----------|
| **Memgraph**| In-memory   | 120x vs Neo4j    | 10-25x vs Neo4j  | Real-time, high-frequency   | €€        |
| **Neo4j**   | On-disk     | Baseline         | Baseline         | Large datasets, persistence | €€€       |
| **TypeDB**  | On-disk     | Moderate         | Moderate         | Typed schemas, inference    | €€€       |

### Raccomandazione per MERL-T: **Memgraph** (con fallback a Neo4j)

**Rationale per Memgraph**:
1. **Performance critica**: KG Agent deve rispondere in <100ms → Memgraph 10-25x più veloce
2. **Real-time queries**: Graph expansion multi-hop richiede bassa latency
3. **Cypher compatibility**: 100% compatible con Neo4j syntax → facile migration
4. **Streaming**: Supporto Kafka streams per live updates (futuro use case: jurisprudence ingestion)
5. **Cost**: Open-source (BSL license, free for self-hosted <1M nodes)

**Quando usare Neo4j invece**:
- Dataset >10M nodi (Memgraph in-memory potrebbe diventare costoso in RAM)
- Requirement di persistence robusta (Memgraph richiede snapshot regolari)
- Enterprise support necessario (Neo4j ha supporto professionale consolidato)

**Strategia consigliata**:
- **Fase 1-3**: Memgraph (10K-1M norme, performance massima)
- **Fase 4+**: Se dataset cresce >5M nodi, valutare Neo4j con tuning avanzato

**Implementazione**:
```yaml
# docker-compose.yml
memgraph:
  image: memgraph/memgraph:2.15.0
  ports:
    - "7687:7687"  # Bolt (same as Neo4j)
  volumes:
    - memgraph_data:/var/lib/memgraph
  environment:
    - MEMGRAPH="--log-level=WARNING"
  command: ["--storage-snapshot-interval-sec=300"]  # Auto-snapshot every 5 min
```

```python
# backend/preprocessing/kg_enrichment.py
from gqlalchemy import Memgraph

memgraph = Memgraph(host="127.0.0.1", port=7687)

# Identical Cypher syntax to Neo4j
query = """
MATCH (c:ConcettoGiuridico {id: $concept_id})-[:REGOLA*1..2]-(n:Norma)
RETURN n.id AS norm_id, n.title AS title
LIMIT 10
"""
results = memgraph.execute_and_fetch(query, {"concept_id": "capacità_agire"})
```

**Migration path da Memgraph a Neo4j** (se necessario):
1. Export Memgraph snapshot
2. Convert con `neo4j-admin import` (Cypher compatible)
3. Minimal code changes (solo connection string)

### Decision: **Memgraph** (Phase 1-3), valutare Neo4j se >5M nodes

---

## Backend Framework

### Benchmark Comparison (requests/sec, latency P95)

| Framework   | Throughput (req/s) | P95 Latency | Async | Ecosystem | Maturity |
|-------------|-------------------|-------------|-------|-----------|----------|
| **Litestar**   | 15,000-20,000     | 15-25ms     | Yes   | Growing   | New      |
| **Robyn**      | 18,000-25,000     | 10-20ms     | Yes   | Small     | Emerging |
| **FastAPI**    | 8,000-12,000      | 30-50ms     | Yes   | Largest   | Mature   |
| **Sanic**      | 10,000-15,000     | 25-40ms     | Yes   | Moderate  | Mature   |

### Raccomandazione per MERL-T: **FastAPI** (Fase 1-2), **Litestar** (Fase 3+)

**Strategia incrementale**:

**Fase 1-2 (MVP, RLCF core)**:
- **FastAPI**: Ecosistema maturo, documentazione, testing utilities
- Priorità: Velocity di sviluppo > Performance assoluta
- Team familiarity (FastAPI è lo standard de facto)

**Fase 3+ (Orchestration, Production)**:
- **Migrazione a Litestar**: 2x throughput, lower latency
- Compatibilità: Litestar è "FastAPI-like" (starlette-based)
- Costo migration: ~2-3 giorni di refactoring

**Perché non Robyn**:
- Ecosystem troppo piccolo (rischio su maintenance)
- Rust dependency potrebbe complicare deployment
- Performance gain non giustifica rischio per MERL-T

**Codice comparison**:

**FastAPI**:
```python
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

@app.post("/query/preprocess")
async def preprocess_query(
    query: str,
    db: AsyncSession = Depends(get_db)
):
    result = await preprocessing_pipeline(query, db)
    return result
```

**Litestar** (quasi identico):
```python
from litestar import Litestar, post
from litestar.di import Provide
from sqlalchemy.ext.asyncio import AsyncSession

@post("/query/preprocess")
async def preprocess_query(
    query: str,
    db: AsyncSession
) -> dict:
    result = await preprocessing_pipeline(query, db)
    return result

app = Litestar(
    route_handlers=[preprocess_query],
    dependencies={"db": Provide(get_db)}
)
```

**Migration effort**: Minimal (API design pressoché identico)

### Decision: **FastAPI** (MVP) → **Litestar** (Production)

---

## Embedding Models

### Benchmark Comparison (Multilingual, incl. Italian)

| Model                        | Dimensions | Languages | MTEB Score | Cost (1M tokens) | Latency   |
|------------------------------|-----------|-----------|------------|------------------|-----------|
| **Voyage Multilingual 2**       | 1024      | 27        | **0.715**  | $0.12            | ~50ms     |
| **text-embedding-3-large**      | 3072      | 100+      | 0.648      | $0.13            | ~80ms     |
| **multilingual-e5-large**       | 1024      | 100+      | 0.656      | Free (self-host) | ~30ms     |
| **Cohere Multilingual v3**      | 1024      | 100+      | 0.642      | $0.10            | ~40ms     |

### Raccomandazione per MERL-T: **Voyage Multilingual 2** (Production), **multilingual-e5** (Development)

**Production (Fase 3+)**:
- **Voyage Multilingual 2**:
  - SOTA per multilingual (Italian included)
  - 5.6% better than competitors
  - Ottimo su legal domain (verified by benchmarks on French/German legal corpora)
  - Costo ragionevole ($0.12/1M tokens, ~$60 per 10M chunks one-time)

**Development (Fase 1-2)**:
- **multilingual-e5-large-instruct**:
  - Open-source, self-hosted (no API costs)
  - 560M params (runnable su GPU T4, ~$0.35/h on GCP)
  - Performance eccellente per prototipazione
  - Deploy con HuggingFace Text Embeddings Inference

**Implementazione**:

**Voyage (production)**:
```python
import voyageai

vo = voyageai.Client(api_key="your-api-key")

embeddings = vo.embed(
    texts=["È valido un contratto firmato da minorenne?"],
    model="voyage-multilingual-2",
    input_type="document"  # or "query"
)

# Returns: [[0.123, -0.456, ...]] (1024-dim)
```

**E5 (development, self-hosted)**:
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('intfloat/multilingual-e5-large-instruct')

# Instruction prefix for better performance
query = "query: È valido un contratto firmato da minorenne?"
doc = "passage: Art. 2 c.c. - La maggiore età..."

query_emb = model.encode(query)
doc_emb = model.encode(doc)

# Cosine similarity
similarity = util.cos_sim(query_emb, doc_emb)
```

**Cost analysis** (10M chunks, one-time embedding):
- Voyage: 10M * 50 tokens avg * $0.12/1M = **$60**
- OpenAI 3-large: 10M * 50 * $0.13/1M = **$65**
- E5 self-hosted: ~10h GPU T4 = **$3.50** (+ setup effort)

### Decision: **Voyage Multilingual 2** (production), **E5** (dev/testing)

---

## NLP Models (Legal Italian)

### Raccomandazione: **ITALIAN-LEGAL-BERT**

**Disponibile su HuggingFace**: `nlpaueb/italian-legal-bert` (verificare exact model name)

**Caratteristiche**:
- Pre-trained su corpus legale italiano (sentenze, codici)
- Base: `dbmdz/bert-base-italian-xxl-cased`
- Performance superiore su:
  - NER legale (entità: NORM, LEGAL_CONCEPT, DATE)
  - Classification (intent classification)
  - Semantic similarity (legal document matching)

**Implementazione NER**:
```python
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline

tokenizer = AutoTokenizer.from_pretrained("nlpaueb/italian-legal-bert")
model = AutoModelForTokenClassification.from_pretrained(
    "nlpaueb/italian-legal-bert",
    num_labels=9  # B-NORM, I-NORM, B-CONCEPT, I-CONCEPT, etc.
)

# Fine-tune on custom dataset (500 annotated legal queries)
# ... training loop ...

# Inference
nlp = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")
result = nlp("È valido un contratto firmato da un minorenne nel 2010?")
# Output: [
#   {"entity_group": "LEGAL_CONCEPT", "word": "contratto", ...},
#   {"entity_group": "PERSON", "word": "minorenne", ...},
#   {"entity_group": "DATE", "word": "2010", ...}
# ]
```

**Alternative considerata**:
- **spaCy + custom NER**: Più veloce (10x) ma meno accurato
- **Strategy**: Usa spaCy in dev, ITALIAN-LEGAL-BERT in production

**Fine-tuning dataset**:
- Annotare 500-1000 query legali italiane con entities
- Tool: Prodigy (licenza €390), Label Studio (open-source)
- Effort: 2 settimane (1 legal expert + 1 ML engineer)

### Decision: **ITALIAN-LEGAL-BERT** fine-tuned

---

## RLHF Framework

### Comparison

| Tool        | Type         | Features                                    | Cost      | Maturity  |
|-------------|--------------|---------------------------------------------|-----------|-----------|
| **TRLX**       | Open-source  | Full RLHF pipeline, PPO, reward modeling    | Free      | Mature    |
| **RL4LMs**     | Open-source  | Modular, multiple RL algorithms             | Free      | Growing   |
| **Labellerr**  | Commercial   | End-to-end platform, UI, analytics          | €€€       | Mature    |
| **Scale AI**   | Commercial   | Managed feedback collection, high quality   | €€€€      | Mature    |

### Raccomandazione per MERL-T: **Custom RLCF Implementation** + **TRLX** (se serve RL training)

**Rationale**:
1. **RLCF ≠ RLHF tradizionale**: MERL-T ha requisiti unici (dynamic authority, aggregation)
2. **Custom pipeline più adatto**:
   - Feedback collection: Custom FastAPI endpoints (già in docs)
   - Authority scoring: Custom algorithm (formule in docs)
   - Aggregation: Custom logic (weighted voting, consensus)
3. **TRLX solo se necessario**: Per fine-tuning LLM basato su reward model (Fase 7+)

**Implementazione RLCF Custom**:
```python
# backend/rlcf_framework/feedback_pipeline.py
from typing import List
from .authority_module import calculate_authority_score
from .aggregation_engine import aggregate_feedback

async def process_feedback_batch(task_id: int, db: AsyncSession):
    """
    Nightly batch job per aggregare feedback.
    """
    # 1. Fetch all feedback for task
    feedbacks = await db.execute(
        select(Feedback).where(Feedback.task_id == task_id)
    )

    # 2. Calculate authority scores
    scored_feedback = []
    for f in feedbacks:
        authority = await calculate_authority_score(f.user_id, db)
        scored_feedback.append({
            "user_id": f.user_id,
            "rating": f.rating,
            "corrections": f.corrections_json,
            "authority": authority
        })

    # 3. Aggregate with weighted voting
    aggregated = aggregate_feedback(scored_feedback, mode="weighted_average")

    # 4. Store result
    result = AggregatedResult(
        task_id=task_id,
        final_result_json=aggregated,
        confidence=aggregated["confidence"],
        consensus_score=aggregated["consensus"]
    )
    db.add(result)
    await db.commit()

    return result
```

**TRLX integration** (opzionale, Fase 7+):
```python
# Se si vuole fine-tuning LLM Router basato su RLCF feedback
import trlx
from trlx.data.configs import TRLConfig

# Define reward model (trained on RLCF feedback)
def reward_fn(samples: List[str], outputs: List[str], **kwargs) -> List[float]:
    """
    Reward = Authority-weighted feedback score
    """
    # Query database per feedback su simili ExecutionPlans
    # Return reward scores
    pass

config = TRLConfig(
    train=TrainConfig(
        batch_size=8,
        learning_rate=1e-5,
        ...
    ),
    method=PPOConfig(...)
)

trainer = trlx.train(
    model_path="gpt-3.5-turbo",  # or local model
    reward_fn=reward_fn,
    prompts=training_prompts,
    config=config
)
```

**Feedback Collection UI**:
- Custom React form (non serve piattaforma enterprise)
- Fields: rating (1-5 stars), corrections (JSON editor), free text
- Tool open-source: React Hook Form + Zod validation

### Decision: **Custom RLCF implementation**, TRLX solo se fine-tuning necessario

---

## Observability Stack

### Comparison

| Stack               | Type         | Features                              | Cost       | Ease of Setup |
|---------------------|--------------|---------------------------------------|------------|---------------|
| **SigNoz**             | Open-source  | Logs + Metrics + Traces, unified      | Free       | Medium        |
| **Uptrace**            | Open-source  | APM, OpenTelemetry-native, ClickHouse | Free       | Medium        |
| **Datadog**            | Commercial   | Full-suite, AI anomaly detection      | €€€€       | Easy          |
| **Grafana + Prom**     | Open-source  | Mature, modular, requires assembly    | Free       | Hard          |
| **New Relic**          | Commercial   | User-based pricing, deep OTel support | €€€        | Easy          |

### Raccomandazione per MERL-T: **SigNoz** (self-hosted) o **Datadog** (managed, se budget)

**Production (self-hosted, budget-conscious)**:
- **SigNoz**:
  - Unified logs/metrics/traces (no tool sprawl)
  - OpenTelemetry-native (future-proof)
  - ClickHouse backend (fast queries)
  - UI moderno (React, simile a Datadog)
  - Self-hosted su K8s: ~€100/mese infra cost

**Production (managed, premium)**:
- **Datadog**:
  - Zero setup effort
  - AI-driven anomaly detection
  - Cost: ~€500-1000/mese per MERL-T workload
  - ROI: Se team piccolo (no dedicated DevOps)

**Implementazione SigNoz**:
```yaml
# kubernetes/observability/signoz.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: observability
---
# Helm install
helm repo add signoz https://charts.signoz.io
helm install signoz signoz/signoz -n observability
```

**Instrumentazione codice**:
```python
# backend/shared/telemetry.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup OpenTelemetry
trace.set_tracer_provider(TracerProvider())
otlp_exporter = OTLPSpanExporter(endpoint="http://signoz-otel-collector:4317")
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

tracer = trace.get_tracer(__name__)

# Usage in code
@tracer.start_as_current_span("preprocess_query")
async def preprocess_query(query: str):
    with tracer.start_as_current_span("ner_extraction"):
        entities = await ner_module.extract(query)

    with tracer.start_as_current_span("kg_enrichment"):
        enriched = await kg_enrichment.enrich(entities)

    return QueryContext(entities=entities, enriched=enriched)
```

**Dashboards SigNoz**:
1. **System Health**: Latency P50/P95/P99, error rate, throughput
2. **LLM Costs**: Tracks OpenAI/Anthropic API calls, token usage, $ spent
3. **RLCF Metrics**: Feedback submission rate, authority score distribution
4. **Agent Performance**: KG/API/VectorDB agent latency, cache hit rates

### Decision: **SigNoz** (cost-effective, modern), Datadog se enterprise budget

---

## Confronto Costi

### Costi Mensili Stimati (100 utenti attivi, 1000 query/giorno)

| Componente          | Tech Stack            | Costo/mese (self-hosted) | Costo/mese (managed) |
|---------------------|-----------------------|--------------------------|----------------------|
| **Compute**            | GKE 6 nodes           | €800                     | €800                 |
| **Vector DB**          | Qdrant self-hosted    | Incluso in compute       | Qdrant Cloud: €200   |
| **Graph DB**           | Memgraph self-hosted  | Incluso in compute       | Memgraph Cloud: €150 |
| **Relational DB**      | PostgreSQL (managed)  | -                        | €100                 |
| **LLM API**            | OpenAI/Anthropic      | €1,500                   | €1,500               |
| **Embeddings**         | Voyage AI             | €50 (one-time €60)       | €50                  |
| **Observability**      | SigNoz self-hosted    | €50 (storage)            | Datadog: €800        |
| **CI/CD**              | GitHub Actions        | €50                      | €50                  |
| **Total (self-hosted)**|                       | **€2,450/mese**          | -                    |
| **Total (managed)**    |                       | -                        | **€3,650/mese**      |

**Ottimizzazioni**:
- LLM caching (Redis): Riduce LLM costs del 30% → €1,050/mese
- Self-hosted embeddings (E5 invece di Voyage): Risparmio €50/mese (ma +1 GPU cost €200)
- Qdrant quantization: Riduce memoria del 40% → downsize 1 node → risparmio €130/mese

**Budget-conscious stack** (€1,800/mese):
- Self-hosted tutto (GKE, Memgraph, Qdrant, PostgreSQL, SigNoz)
- E5 embeddings self-hosted
- Aggressive LLM caching
- Free tier LLMs (via OpenRouter: Mistral, Llama)

---

## Decision Matrix

### Framework Decisions

| Layer               | Technology                  | Rationale                                                      |
|---------------------|-----------------------------|----------------------------------------------------------------|
| **Orchestration**      | LangGraph                   | Stato complesso, iteration loops, production-grade             |
| **Backend**            | FastAPI → Litestar          | Ecosistema (MVP) → Performance (Prod)                          |
| **Vector DB**          | Qdrant                      | Latency, cost, hybrid search                                   |
| **Graph DB**           | Memgraph                    | 10x faster, real-time, Cypher compatible                       |
| **Embeddings**         | Voyage Multilingual 2       | SOTA multilingual, Italian strong                              |
| **Legal NLP**          | ITALIAN-LEGAL-BERT          | Domain-specific, fine-tunable                                  |
| **Observability**      | SigNoz                      | Open-source, unified, modern UI                                |
| **RLCF**               | Custom implementation       | RLCF requirements unique, no off-the-shelf fit                 |

### Phase-by-Phase Stack Evolution

**Fase 1-2 (MVP, Weeks 1-14)**:
- FastAPI + PostgreSQL + SQLAlchemy
- Neo4j Community Edition (familiarità, docs)
- OpenAI embeddings (semplicity)
- No vector DB ancora
- Prometheus + Grafana (manual setup)

**Fase 3 (Orchestration, Weeks 15-22)**:
- **Migrate to**:
  - LangGraph orchestration
  - Memgraph (performance boost)
  - Qdrant vector DB
  - Voyage embeddings
- Keep: FastAPI (migration a Litestar in Fase 5)

**Fase 4-5 (Reasoning & Integration, Weeks 23-36)**:
- **Migrate to**:
  - Litestar (2x throughput)
  - SigNoz observability (unified stack)
  - ITALIAN-LEGAL-BERT fine-tuned
- Optimize: LLM caching, prompt compression

**Fase 6+ (Production, Weeks 37+)**:
- Production-hardened stack
- Consider: Datadog se enterprise support necessario
- Consider: Managed services (Qdrant Cloud, Memgraph Cloud) se team < 3

---

## Prossimi Passi

### Week 1: Technology Validation

1. **Proof-of-concept**:
   - [ ] Memgraph vs Neo4j benchmark (stesso dataset 10K norme)
   - [ ] Qdrant setup + test 1M vectors
   - [ ] LangGraph hello-world (simple router)
   - [ ] ITALIAN-LEGAL-BERT inference test

2. **Cost validation**:
   - [ ] Voyage API trial (1000 embeddings)
   - [ ] OpenRouter setup (test 5 LLM providers)
   - [ ] SigNoz local install (Docker Compose)

3. **Team training**:
   - [ ] LangGraph tutorial (4h workshop)
   - [ ] Qdrant documentation review
   - [ ] OpenTelemetry basics (2h session)

### Week 2: Architecture Decisions Finalized

- [ ] Present questo documento al team
- [ ] Votazione su tech stack (consensus)
- [ ] Setup development environment con stack scelto
- [ ] Update `IMPLEMENTATION_ROADMAP.md` con tecnologie finali

---

## Risorse di Apprendimento

### LangGraph
- Docs: https://python.langgraph.com/
- Tutorial: "Building Stateful Agents with LangGraph" (YouTube)
- Example: Legal research agent (community examples)

### Qdrant
- Quickstart: https://qdrant.tech/documentation/quick-start/
- Hybrid Search Guide: https://qdrant.tech/documentation/guides/hybrid-search/
- Benchmarks: https://qdrant.tech/benchmarks/

### Memgraph
- Memgraph vs Neo4j: https://memgraph.com/memgraph-vs-neo4j
- Cypher Manual: https://memgraph.com/docs/cypher-manual
- Streaming tutorial: Kafka + Memgraph

### Voyage AI
- API Docs: https://docs.voyageai.com/
- Multilingual guide: https://blog.voyageai.com/multilingual-embeddings/

### ITALIAN-LEGAL-BERT
- HuggingFace: https://huggingface.co/nlpaueb/italian-legal-bert
- Fine-tuning guide: HuggingFace NER tutorial
- Paper: "Legal-BERT: The Muppets straight out of Law School"

### SigNoz
- Installation: https://signoz.io/docs/install/
- OpenTelemetry integration: https://signoz.io/docs/instrumentation/
- ClickHouse optimization: https://signoz.io/docs/operate/clickhouse/

---

## Conclusioni

### Stack Finale Raccomandato

**MERL-T Production Stack (2025)**:
```
Frontend:     React + Next.js + TypeScript
Orchestration: LangGraph
Backend:      Litestar (FastAPI per MVP)
Databases:    PostgreSQL + Memgraph + Qdrant + Redis
AI/ML:        Voyage Multilingual 2 + ITALIAN-LEGAL-BERT
LLM:          OpenRouter (multi-provider)
Observability: SigNoz + OpenTelemetry
Infra:        Kubernetes + Docker + GitHub Actions
```

**Filosofia**:
- **Innovativo ma stabile**: Tecnologie cutting-edge con community attiva
- **Cost-conscious**: Self-hosting dove possibile, managed services dove giustificato
- **Performance-first**: Latency e throughput prioritari (legal AI richiede speed)
- **Future-proof**: OpenTelemetry, OpenRouter (no vendor lock-in)

**ROI Atteso**:
- Performance: 2-3x vs stack "standard" (FastAPI + Neo4j + Weaviate)
- Cost: 30% risparmio vs stack completamente managed
- Maintenance: OpenTelemetry standard → facilita debugging

---

**Buona implementazione! 🚀**

*Aggiorna questo documento man mano che le tecnologie evolvono. Revisione trimestrale consigliata.*
