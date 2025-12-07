# 06. Task Queue & Background Workers

**Status**: Implementation Blueprint
**Layer**: Infrastructure / Background Processing
**Dependencies**: Database Schemas (03), Vector Search (04), Graph Queries (05)
**Key Libraries**: Celery 5.3+, RabbitMQ 3.12, Redis 7, Flower (monitoring)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Celery Configuration](#2-celery-configuration)
3. [RabbitMQ Setup](#3-rabbitmq-setup)
4. [Data Ingestion Pipeline](#4-data-ingestion-pipeline)
5. [Training Data Generation Tasks](#5-training-data-generation-tasks)
6. [Model Update Tasks](#6-model-update-tasks)
7. [Task Monitoring & Retries](#7-task-monitoring--retries)

---

## 1. Overview

MERL-T uses Celery + RabbitMQ for asynchronous background processing:
- **Data ingestion pipeline** (5 stages: Parse → Chunk → Embed → Enrich → Store)
- **Training data generation** (RLCF feedback → training examples)
- **Model updates** (scheduled weekly/monthly retraining)
- **Maintenance tasks** (cache cleanup, statistics aggregation)

### Task Queues

| Queue | Purpose | Priority | Workers | Avg Latency |
|-------|---------|----------|---------|-------------|
| **ingestion** | Document parsing, chunking, embedding | High | 3 | 2-5s per document |
| **training** | Training data generation from feedback | Medium | 2 | 1-2s per feedback |
| **model_update** | Model retraining (heavy) | Low | 1 | 30-60 min |
| **maintenance** | Cache cleanup, stats aggregation | Low | 1 | 1-10s |

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│ FastAPI Services                                        │
│   ↓ (publish tasks)                                     │
├─────────────────────────────────────────────────────────┤
│ RabbitMQ Broker                                         │
│   - Exchange: celery                                    │
│   - Queues: ingestion, training, model_update          │
├─────────────────────────────────────────────────────────┤
│ Celery Workers (3 replicas for ingestion queue)        │
│   ↓ (execute tasks)                                     │
├─────────────────────────────────────────────────────────┤
│ Storage (Neo4j, Weaviate, PostgreSQL)                  │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Celery Configuration

### 2.1 Celery App Factory

**File**: `src/tasks/celery_app.py`

```python
from celery import Celery
from kombu import Queue, Exchange
from .config import CelerySettings


def create_celery_app(settings: CelerySettings | None = None) -> Celery:
    """
    Create and configure Celery application.

    Args:
        settings: Optional Celery settings override

    Returns:
        Configured Celery app

    Example:
        >>> app = create_celery_app()
        >>> # Register tasks
        >>> from .ingestion_tasks import ingest_document
    """
    if settings is None:
        settings = CelerySettings()

    app = Celery(
        "merl_t",
        broker=settings.broker_url,
        backend=settings.result_backend,
    )

    # ===== Configuration =====
    app.conf.update(
        # Task routing
        task_routes={
            "src.tasks.ingestion_tasks.*": {"queue": "ingestion"},
            "src.tasks.training_tasks.*": {"queue": "training"},
            "src.tasks.model_update_tasks.*": {"queue": "model_update"},
            "src.tasks.maintenance_tasks.*": {"queue": "maintenance"},
        },

        # Task result expiration (1 hour)
        result_expires=3600,

        # Task serialization (JSON for simplicity, msgpack for performance)
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],

        # Timezone
        timezone="Europe/Rome",
        enable_utc=True,

        # Task acknowledgement (ack after task completion, not before)
        task_acks_late=True,

        # Worker prefetch (number of tasks to prefetch per worker)
        worker_prefetch_multiplier=4,

        # Task time limits
        task_soft_time_limit=600,  # 10 minutes (raises SoftTimeLimitExceeded)
        task_time_limit=660,  # 11 minutes (kills worker)

        # Task retries
        task_default_retry_delay=60,  # 1 minute
        task_max_retries=3,

        # Beat scheduler (for periodic tasks)
        beat_schedule=settings.beat_schedule,
    )

    # ===== Queue Declarations =====
    app.conf.task_queues = (
        Queue(
            "ingestion",
            Exchange("celery", type="direct"),
            routing_key="ingestion",
            priority=10,
        ),
        Queue(
            "training",
            Exchange("celery", type="direct"),
            routing_key="training",
            priority=5,
        ),
        Queue(
            "model_update",
            Exchange("celery", type="direct"),
            routing_key="model_update",
            priority=1,
        ),
        Queue(
            "maintenance",
            Exchange("celery", type="direct"),
            routing_key="maintenance",
            priority=1,
        ),
    )

    # ===== Import tasks (autodiscovery) =====
    app.autodiscover_tasks(["src.tasks"])

    return app


# ===== Global Celery App =====
app = create_celery_app()
```

### 2.2 Celery Settings

**File**: `src/tasks/config.py`

```python
from pydantic import Field
from pydantic_settings import BaseSettings
from celery.schedules import crontab


class CelerySettings(BaseSettings):
    """Celery configuration."""

    # ===== Broker & Backend =====
    broker_url: str = "amqp://admin:password@localhost:5672//"
    result_backend: str = "redis://localhost:6379/0"

    # ===== Worker Configuration =====
    worker_concurrency: int = 4  # Number of worker processes
    worker_max_tasks_per_child: int = 1000  # Restart worker after N tasks (prevent memory leaks)

    # ===== Beat Schedule (Periodic Tasks) =====
    beat_schedule: dict = Field(
        default_factory=lambda: {
            # Daily: Generate training data from unprocessed feedback
            "generate_training_data_daily": {
                "task": "src.tasks.training_tasks.generate_training_data_batch",
                "schedule": crontab(hour=2, minute=0),  # 02:00 AM daily
            },

            # Weekly: Light model updates (router, embeddings)
            "weekly_model_update": {
                "task": "src.tasks.model_update_tasks.weekly_update",
                "schedule": crontab(day_of_week=1, hour=3, minute=0),  # Monday 03:00 AM
            },

            # Monthly: Heavy model retraining
            "monthly_model_retrain": {
                "task": "src.tasks.model_update_tasks.monthly_retrain",
                "schedule": crontab(day_of_month=1, hour=4, minute=0),  # 1st of month, 04:00 AM
            },

            # Hourly: Cache cleanup
            "cleanup_expired_cache": {
                "task": "src.tasks.maintenance_tasks.cleanup_cache",
                "schedule": crontab(minute=0),  # Every hour
            },
        }
    )

    class Config:
        env_prefix = "CELERY_"
```

---

## 3. RabbitMQ Setup

### 3.1 RabbitMQ Configuration

**File**: `rabbitmq.conf`

```ini
# ===== Networking =====
listeners.tcp.default = 5672

# ===== Management Plugin =====
management.tcp.port = 15672
management.tcp.ip = 0.0.0.0

# ===== Memory & Disk =====
vm_memory_high_watermark.relative = 0.6
disk_free_limit.relative = 2.0

# ===== Queue Configuration =====
default_vhost = /
default_user = admin
default_pass = password

# ===== Message TTL (7 days) =====
message_ttl = 604800000

# ===== Logging =====
log.console = true
log.console.level = info
log.file.level = info
log.file = /var/log/rabbitmq/rabbitmq.log
```

### 3.2 RabbitMQ Queue Setup (Python)

**File**: `src/tasks/rabbitmq_setup.py`

```python
import pika


def setup_rabbitmq_queues(
    host: str = "localhost",
    port: int = 5672,
    username: str = "admin",
    password: str = "password",
):
    """
    Create RabbitMQ queues with priority support.

    Args:
        host: RabbitMQ host
        port: RabbitMQ port
        username: RabbitMQ username
        password: RabbitMQ password

    TODO:
        - Declare queues with max_priority=10
        - Set queue durability and auto-delete policies
    """
    credentials = pika.PlainCredentials(username, password)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=host,
            port=port,
            credentials=credentials,
        )
    )

    channel = connection.channel()

    # Declare queues with priority support
    queues = [
        ("ingestion", 10),  # Max priority 10
        ("training", 5),
        ("model_update", 1),
        ("maintenance", 1),
    ]

    for queue_name, max_priority in queues:
        channel.queue_declare(
            queue=queue_name,
            durable=True,  # Survive broker restart
            arguments={"x-max-priority": max_priority},
        )

    connection.close()
```

---

## 4. Data Ingestion Pipeline

### 4.1 Pipeline Overview

**5-Stage ETL Pipeline**:
1. **Parse**: Extract text from PDF/XML (Akoma Ntoso)
2. **Chunk**: Semantic chunking (article-level, similarity-based)
3. **Embed**: Generate embeddings (text-embedding-3-large)
4. **Enrich**: Link to KG concepts + NER
5. **Store**: Insert into Weaviate + PostgreSQL

### 4.2 Ingestion Task Chain

**File**: `src/tasks/ingestion_tasks.py`

```python
from celery import chain, group
from .celery_app import app
import logging


logger = logging.getLogger(__name__)


@app.task(bind=True, name="src.tasks.ingestion_tasks.ingest_document")
def ingest_document(
    self,
    document_url: str,
    document_type: str,  # "norm" | "jurisprudence" | "doctrine"
) -> str:
    """
    Orchestrate ingestion pipeline for a single document.

    Pipeline: Parse → Chunk → Embed → Enrich → Store

    Args:
        document_url: URL or file path to document
        document_type: Document type

    Returns:
        Document ID (UUID)

    Example:
        >>> result = ingest_document.delay(
        ...     document_url="https://www.normattiva.it/...",
        ...     document_type="norm",
        ... )
        >>> document_id = result.get()  # Blocks until task completes
    """
    try:
        # Create task chain (sequential execution)
        pipeline = chain(
            parse_document.s(document_url, document_type),
            chunk_document.s(),
            embed_chunks.s(),
            enrich_chunks.s(),
            store_chunks.s(),
        )

        # Execute pipeline
        result = pipeline.apply_async()

        # Wait for completion (in production, use .get(timeout=600))
        document_id = result.get()

        logger.info(f"Document ingested successfully: {document_id}")
        return document_id

    except Exception as e:
        logger.error(f"Ingestion failed for {document_url}: {e}")
        # Retry with exponential backoff
        self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@app.task(name="src.tasks.ingestion_tasks.parse_document")
def parse_document(document_url: str, document_type: str) -> dict:
    """
    Stage 1: Parse document from URL.

    Returns:
        Dict with {document_id, text, metadata}

    TODO:
        - If document_type == "norm": Parse Akoma Ntoso XML/JSON
        - If document_type == "jurisprudence": Parse PDF with pdfplumber
        - If document_type == "doctrine": Parse PDF or HTML
        - Extract metadata (title, date, author, etc.)
    """
    # TODO: Implement parsing logic
    logger.info(f"Parsing document: {document_url}")
    return {
        "document_id": "uuid-placeholder",
        "text": "Document text placeholder",
        "metadata": {},
    }


@app.task(name="src.tasks.ingestion_tasks.chunk_document")
def chunk_document(parsed_document: dict) -> dict:
    """
    Stage 2: Chunk document into semantic units.

    Chunking Strategies:
        - Norms: Article-level chunking (one chunk per article)
        - Jurisprudence: Section-based chunking (introduction, facts, reasoning, dispositivo)
        - Doctrine: Similarity-based chunking (semantic boundaries with threshold 0.72)

    Returns:
        Dict with {document_id, chunks: list[dict]}

    TODO:
        - Implement chunking strategies
        - Preserve metadata for each chunk
    """
    # TODO: Implement chunking logic
    logger.info(f"Chunking document: {parsed_document['document_id']}")
    return {
        "document_id": parsed_document["document_id"],
        "chunks": [
            {"text": "Chunk 1 text", "metadata": {}},
            {"text": "Chunk 2 text", "metadata": {}},
        ],
    }


@app.task(name="src.tasks.ingestion_tasks.embed_chunks")
def embed_chunks(chunked_document: dict) -> dict:
    """
    Stage 3: Generate embeddings for all chunks.

    TODO:
        - Call OpenAI embeddings API in batches (100 chunks/batch)
        - Handle rate limiting (max 3,000 RPM)
        - Add embeddings to chunks
    """
    # TODO: Implement embedding generation
    logger.info(f"Embedding chunks for document: {chunked_document['document_id']}")
    for chunk in chunked_document["chunks"]:
        chunk["embedding"] = [0.0] * 3072  # Placeholder

    return chunked_document


@app.task(name="src.tasks.ingestion_tasks.enrich_chunks")
def enrich_chunks(embedded_document: dict) -> dict:
    """
    Stage 4: Enrich chunks with KG links + NER.

    TODO:
        - Extract entities with BERT NER
        - Map entities to KG concepts
        - Add related_concept_ids, referenced_norm_ids to metadata
    """
    # TODO: Implement enrichment logic
    logger.info(f"Enriching chunks for document: {embedded_document['document_id']}")
    for chunk in embedded_document["chunks"]:
        chunk["metadata"]["related_concept_ids"] = []
        chunk["metadata"]["referenced_norm_ids"] = []

    return embedded_document


@app.task(name="src.tasks.ingestion_tasks.store_chunks")
def store_chunks(enriched_document: dict) -> str:
    """
    Stage 5: Store chunks in Weaviate + PostgreSQL.

    TODO:
        - Insert chunks into Weaviate (with vectors)
        - Insert metadata into PostgreSQL chunks table
        - Link to Neo4j nodes (if applicable)
    """
    # TODO: Implement storage logic
    logger.info(f"Storing chunks for document: {enriched_document['document_id']}")
    return enriched_document["document_id"]
```

### 4.3 Batch Ingestion

**File**: `src/tasks/batch_ingestion.py`

```python
from celery import group
from .ingestion_tasks import ingest_document
import logging


logger = logging.getLogger(__name__)


def batch_ingest_documents(
    document_urls: list[str],
    document_type: str,
) -> list[str]:
    """
    Ingest multiple documents in parallel.

    Args:
        document_urls: List of document URLs
        document_type: Document type (norm, jurisprudence, doctrine)

    Returns:
        List of document IDs

    Example:
        >>> urls = [
        ...     "https://www.normattiva.it/codice-civile/art-1",
        ...     "https://www.normattiva.it/codice-civile/art-2",
        ... ]
        >>> document_ids = batch_ingest_documents(urls, "norm")
    """
    # Create parallel task group
    job = group(
        ingest_document.s(url, document_type)
        for url in document_urls
    )

    # Execute in parallel
    result = job.apply_async()

    # Wait for all tasks to complete
    document_ids = result.get()

    logger.info(f"Batch ingestion completed: {len(document_ids)} documents")
    return document_ids
```

---

## 5. Training Data Generation Tasks

### 5.1 Generate Training Examples from Feedback

**File**: `src/tasks/training_tasks.py`

```python
from .celery_app import app
import logging


logger = logging.getLogger(__name__)


@app.task(name="src.tasks.training_tasks.generate_training_example")
def generate_training_example(feedback_id: str) -> str:
    """
    Generate training example from single feedback entry.

    Args:
        feedback_id: Feedback UUID from answer_feedback table

    Returns:
        Training example ID (UUID)

    TODO:
        - Query answer_feedback table
        - Determine example_type (router_decision, embedding_triplet, etc.)
        - Generate training example
        - Insert into training_examples table
        - Mark feedback as processed
    """
    # TODO: Implement training example generation
    logger.info(f"Generating training example for feedback: {feedback_id}")
    return "training_example_uuid_placeholder"


@app.task(name="src.tasks.training_tasks.generate_training_data_batch")
def generate_training_data_batch():
    """
    Batch generate training data from unprocessed feedback.

    Scheduled Task (Daily at 02:00 AM):
        - Query unprocessed feedback (processed=false)
        - Generate training examples for each feedback
        - Log statistics

    TODO:
        - Query PostgreSQL for unprocessed feedback
        - Call generate_training_example for each feedback_id
        - Aggregate statistics (total examples generated, by type)
    """
    # TODO: Implement batch generation
    logger.info("Batch training data generation started")
    # Placeholder logic
    unprocessed_feedback_ids = []  # Query from PostgreSQL

    for feedback_id in unprocessed_feedback_ids:
        generate_training_example.delay(feedback_id)

    logger.info(f"Batch training data generation completed: {len(unprocessed_feedback_ids)} examples generated")
```

---

## 6. Model Update Tasks

### 6.1 Weekly Light Update

**File**: `src/tasks/model_update_tasks.py`

```python
from .celery_app import app
import logging


logger = logging.getLogger(__name__)


@app.task(name="src.tasks.model_update_tasks.weekly_update")
def weekly_update():
    """
    Weekly light model update (Router prompt refinement, Embedding fine-tuning).

    Scheduled Task (Monday 03:00 AM):
        - Update Router system prompt with new examples
        - Fine-tune embeddings on new triplets (< 1000 examples)
        - Deploy updated models to staging
        - Initiate A/B test

    TODO:
        - Query training_examples (unused, created in last 7 days)
        - Update Router prompt template
        - Fine-tune embedding model (if >= 100 new triplets)
        - Register new model version in model_registry
        - Trigger A/B test
    """
    logger.info("Weekly model update started")

    # TODO: Implement weekly update logic

    logger.info("Weekly model update completed")


@app.task(name="src.tasks.model_update_tasks.monthly_retrain")
def monthly_retrain():
    """
    Monthly heavy model retraining (NER, Intent Classifier, Synthesizer).

    Scheduled Task (1st of month, 04:00 AM):
        - Retrain NER model on new annotations
        - Retrain Intent Classifier on corrected intents
        - Update Synthesizer examples
        - Full validation and deployment

    Duration: 30-60 minutes

    TODO:
        - Query training_examples (example_type = query_understanding_annotation)
        - Retrain NER model (transformers.Trainer)
        - Retrain Intent Classifier
        - Validate on held-out test set
        - Register models in model_registry
        - Deploy to production (if quality improves)
    """
    logger.info("Monthly model retraining started")

    # TODO: Implement monthly retraining logic

    logger.info("Monthly model retraining completed")
```

---

## 7. Task Monitoring & Retries

### 7.1 Task Failure Handling

**File**: `src/tasks/error_handling.py`

```python
from celery.signals import task_failure
import logging


logger = logging.getLogger(__name__)


@task_failure.connect
def handle_task_failure(sender, task_id, exception, args, kwargs, traceback, **kw):
    """
    Handle task failures globally.

    Actions:
        - Log error with full traceback
        - Send alert to monitoring system (Sentry)
        - Store failure in PostgreSQL for analysis

    Args:
        sender: Task instance
        task_id: Task UUID
        exception: Exception raised
        args: Task args
        kwargs: Task kwargs
        traceback: Exception traceback
    """
    logger.error(
        f"Task {sender.name} [{task_id}] failed: {exception}",
        exc_info=(type(exception), exception, traceback),
    )

    # TODO: Send to Sentry
    # sentry_sdk.capture_exception(exception)

    # TODO: Store in PostgreSQL task_failures table
```

### 7.2 Flower Monitoring

**Flower** is a real-time web-based monitoring tool for Celery.

**Start Flower**:
```bash
# Install Flower
pip install flower

# Start Flower web UI
celery -A src.tasks.celery_app flower --port=5555

# Access UI at http://localhost:5555
```

**Flower Features**:
- Real-time task monitoring (active, succeeded, failed)
- Task rate graphs
- Worker status and resource usage
- Task result inspection
- Task revocation

---

## Summary

This Task Queue implementation provides:

1. **Celery + RabbitMQ** setup with 4 queues (ingestion, training, model_update, maintenance)
2. **Data Ingestion Pipeline** (5-stage ETL: Parse → Chunk → Embed → Enrich → Store)
3. **Training Data Generation** (daily batch job converting feedback to training examples)
4. **Model Update Tasks** (weekly light updates, monthly heavy retraining)
5. **Task Monitoring** with Flower web UI and failure handling
6. **Scheduled Tasks** with Celery Beat (cron-based scheduling)

### Throughput Estimates

- **Ingestion**: 3,000 chunks/hour (1 worker) → 9,000 chunks/hour (3 workers)
- **Training Data Generation**: 1,000 examples/hour (2 workers)
- **Model Update**: 1 update/week (light), 1 retrain/month (heavy)

### Next Steps

1. Implement actual task logic (parsing, chunking, embedding, etc.)
2. Set up RabbitMQ with priority queues
3. Deploy Celery workers with Docker (3 replicas for ingestion queue)
4. Configure Flower monitoring dashboard
5. Implement error alerting with Sentry

### Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/tasks/celery_app.py` | Celery app factory | ~120 |
| `src/tasks/config.py` | Celery settings | ~80 |
| `src/tasks/rabbitmq_setup.py` | RabbitMQ queue setup | ~50 |
| `src/tasks/ingestion_tasks.py` | 5-stage ingestion pipeline | ~200 |
| `src/tasks/batch_ingestion.py` | Batch parallel ingestion | ~40 |
| `src/tasks/training_tasks.py` | Training data generation | ~60 |
| `src/tasks/model_update_tasks.py` | Model update tasks | ~80 |
| `src/tasks/error_handling.py` | Failure handling | ~30 |

**Total: ~660 lines** (target: ~650 lines) ✅
