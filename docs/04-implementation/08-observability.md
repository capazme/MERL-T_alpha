# 08. Observability & Monitoring

**Status**: Implementation Blueprint
**Layer**: Infrastructure / Observability
**Dependencies**: All services
**Key Libraries**: OpenTelemetry, Prometheus, Grafana, python-json-logger

---

## Table of Contents

1. [Overview](#1-overview)
2. [OpenTelemetry Tracing](#2-opentelemetry-tracing)
3. [Prometheus Metrics](#3-prometheus-metrics)
4. [Structured Logging](#4-structured-logging)
5. [Grafana Dashboards](#5-grafana-dashboards)

---

## 1. Overview

MERL-T implements comprehensive observability with:
- **Distributed Tracing** (OpenTelemetry) for request flow tracking
- **Metrics** (Prometheus) for performance monitoring
- **Structured Logging** (JSON) for debugging and auditing
- **Dashboards** (Grafana) for visualization

### Observability Stack

```
┌─────────────────────────────────────────────────────────┐
│ MERL-T Services (FastAPI, Celery)                      │
│   ↓ (traces, metrics, logs)                            │
├─────────────────────────────────────────────────────────┤
│ OpenTelemetry Collector                                 │
│   - Receives: traces (OTLP), metrics (Prometheus)      │
│   - Exports: Jaeger (traces), Prometheus (metrics)     │
├─────────────────────────────────────────────────────────┤
│ Storage & Visualization                                 │
│   - Jaeger: Distributed tracing UI                     │
│   - Prometheus: Time-series metrics DB                 │
│   - Grafana: Dashboards + alerts                       │
│   - Loki: Log aggregation (optional)                   │
└─────────────────────────────────────────────────────────┘
```

---

## 2. OpenTelemetry Tracing

### 2.1 OpenTelemetry Setup

**File**: `src/observability/tracing.py`

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from fastapi import FastAPI


def setup_tracing(
    service_name: str,
    otlp_endpoint: str = "http://localhost:4317",
) -> trace.Tracer:
    """
    Setup OpenTelemetry tracing for MERL-T service.

    Args:
        service_name: Service name (e.g., "merl-t-router", "merl-t-kg-agent")
        otlp_endpoint: OpenTelemetry Collector endpoint (gRPC)

    Returns:
        Tracer instance

    Example:
        >>> from src.observability.tracing import setup_tracing
        >>> tracer = setup_tracing(service_name="merl-t-api-gateway")
        >>> with tracer.start_as_current_span("my_operation"):
        ...     # Your code here
    """
    # Set up tracer provider
    provider = TracerProvider()
    trace.set_tracer_provider(provider)

    # Configure OTLP exporter (sends traces to Collector)
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True,  # Use TLS in production
    )

    # Add span processor (batches spans before export)
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)

    # Get tracer
    tracer = trace.get_tracer(service_name)

    return tracer


def instrument_fastapi(app: FastAPI):
    """
    Auto-instrument FastAPI application with OpenTelemetry.

    Automatically traces:
        - HTTP requests/responses
        - Request handlers
        - Exception tracking

    Args:
        app: FastAPI application

    Example:
        >>> app = FastAPI()
        >>> instrument_fastapi(app)
    """
    FastAPIInstrumentor.instrument_app(app)


def instrument_httpx():
    """
    Auto-instrument httpx HTTP client.

    Traces outgoing HTTP requests to other services.
    """
    HTTPXClientInstrumentor().instrument()


def instrument_celery():
    """
    Auto-instrument Celery task queue.

    Traces:
        - Task execution
        - Task failures
        - Task retries
    """
    CeleryInstrumentor().instrument()
```

### 2.2 Custom Span Creation

**File**: `src/observability/spans.py`

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from typing import Any
from contextvars import ContextVar


# Context variable for trace_id propagation
trace_id_context: ContextVar[str] = ContextVar("trace_id", default="")


def create_span(
    tracer: trace.Tracer,
    span_name: str,
    attributes: dict[str, Any] | None = None,
):
    """
    Create custom span with attributes.

    Args:
        tracer: OpenTelemetry tracer
        span_name: Span name (e.g., "router.generate_plan")
        attributes: Optional span attributes

    Returns:
        Context manager for span

    Example:
        >>> tracer = trace.get_tracer(__name__)
        >>> with create_span(tracer, "kg_agent.expand_concepts", {"depth": 2}):
        ...     # Your code here
    """
    span = tracer.start_as_current_span(span_name)

    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)

    return span


def record_exception_in_span(span: trace.Span, exception: Exception):
    """
    Record exception in current span.

    Args:
        span: Active span
        exception: Exception to record
    """
    span.record_exception(exception)
    span.set_status(Status(StatusCode.ERROR, str(exception)))


# Example: Router service with tracing
async def generate_execution_plan_traced(
    tracer: trace.Tracer,
    query_context: dict,
    enriched_context: dict,
) -> dict:
    """Example traced function."""

    with tracer.start_as_current_span("router.generate_execution_plan") as span:
        # Add attributes
        span.set_attribute("query.intent", query_context["intent"]["primary"])
        span.set_attribute("query.complexity", query_context["complexity"]["score"])

        try:
            # TODO: Call LLM to generate plan
            execution_plan = {}

            # Add result attributes
            span.set_attribute("plan.agents_count", len(execution_plan.get("retrieval_plan", {})))
            span.set_attribute("plan.experts_count", len(execution_plan.get("reasoning_plan", {}).get("experts", [])))

            return execution_plan

        except Exception as e:
            record_exception_in_span(span, e)
            raise
```

---

## 3. Prometheus Metrics

### 3.1 Metrics Setup

**File**: `src/observability/metrics.py`

```python
from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Callable
import time


# ===== Request Metrics =====
http_requests_total = Counter(
    "merl_t_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "merl_t_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)


# ===== LLM Metrics =====
llm_requests_total = Counter(
    "merl_t_llm_requests_total",
    "Total LLM API requests",
    ["component", "model", "status"],
)

llm_tokens_total = Counter(
    "merl_t_llm_tokens_total",
    "Total LLM tokens consumed",
    ["component", "model", "token_type"],
)

llm_cost_usd_total = Counter(
    "merl_t_llm_cost_usd_total",
    "Total LLM cost in USD",
    ["component", "model"],
)

llm_request_duration_seconds = Histogram(
    "merl_t_llm_request_duration_seconds",
    "LLM request latency",
    ["component", "model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)


# ===== Retrieval Metrics =====
retrieval_requests_total = Counter(
    "merl_t_retrieval_requests_total",
    "Total retrieval requests",
    ["pattern", "agent"],
)

retrieval_precision_at_10 = Histogram(
    "merl_t_retrieval_precision_at_10",
    "Retrieval precision@10",
    ["pattern", "agent"],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0],
)


# ===== RLCF Metrics =====
feedback_submissions_total = Counter(
    "merl_t_feedback_submissions_total",
    "Total feedback submissions",
    ["rating", "user_role"],
)

training_examples_generated_total = Counter(
    "merl_t_training_examples_generated_total",
    "Total training examples generated",
    ["example_type"],
)


# ===== System Metrics =====
active_connections = Gauge(
    "merl_t_active_connections",
    "Number of active connections",
    ["service"],
)

celery_task_duration_seconds = Histogram(
    "merl_t_celery_task_duration_seconds",
    "Celery task execution time",
    ["task_name", "status"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0],
)


# ===== Helper Functions =====
def track_llm_request(
    component: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    duration_seconds: float,
    status: str = "success",
):
    """
    Track LLM request metrics.

    Args:
        component: Component name (router, expert_literal, etc.)
        model: Model name (gpt-4o, claude-sonnet-3.5)
        input_tokens: Input token count
        output_tokens: Output token count
        cost_usd: Cost in USD
        duration_seconds: Request duration
        status: success | error

    Example:
        >>> track_llm_request(
        ...     component="router",
        ...     model="gpt-4o",
        ...     input_tokens=1000,
        ...     output_tokens=500,
        ...     cost_usd=0.0125,
        ...     duration_seconds=1.5,
        ... )
    """
    llm_requests_total.labels(component=component, model=model, status=status).inc()
    llm_tokens_total.labels(component=component, model=model, token_type="input").inc(input_tokens)
    llm_tokens_total.labels(component=component, model=model, token_type="output").inc(output_tokens)
    llm_cost_usd_total.labels(component=component, model=model).inc(cost_usd)
    llm_request_duration_seconds.labels(component=component, model=model).observe(duration_seconds)
```

### 3.2 Metrics Middleware

**File**: `src/api_gateway/middleware/metrics.py`

```python
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
import time
from ..observability.metrics import (
    http_requests_total,
    http_request_duration_seconds,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP request metrics.

    Tracks:
        - Request count by method, endpoint, status
        - Request duration histogram
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and record metrics."""

        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Record metrics
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)

        return response
```

---

## 4. Structured Logging

### 4.1 JSON Logger Setup

**File**: `src/observability/logging.py`

```python
import logging
import sys
from pythonjsonlogger import jsonlogger
from contextvars import ContextVar


# Context variable for trace_id
trace_id_context: ContextVar[str] = ContextVar("trace_id", default="")


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with trace_id injection.

    Adds fields:
        - timestamp
        - level
        - message
        - trace_id (from context)
        - service_name
        - pathname
        - lineno
    """

    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Add trace_id from context
        trace_id = trace_id_context.get()
        if trace_id:
            log_record["trace_id"] = trace_id

        # Add service name
        log_record["service"] = "merl-t"

        # Add timestamp
        log_record["timestamp"] = record.created


def setup_logging(
    log_level: str = "INFO",
    service_name: str = "merl-t",
) -> logging.Logger:
    """
    Setup structured JSON logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        service_name: Service name for log tagging

    Returns:
        Configured logger

    Example:
        >>> logger = setup_logging(log_level="INFO", service_name="merl-t-router")
        >>> logger.info("Router generated plan", extra={"plan_id": "abc123"})
        # Output: {"timestamp": 1699000000.0, "level": "INFO", "message": "Router generated plan", "plan_id": "abc123", "trace_id": "RTR-20241103-abc123"}
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Create handler (stdout)
    handler = logging.StreamHandler(sys.stdout)

    # Set JSON formatter
    formatter = CustomJsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s"
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


# Example usage
logger = setup_logging()

# Log with extra fields
logger.info(
    "Query processed successfully",
    extra={
        "query_id": "abc123",
        "latency_ms": 156,
        "user_id": "user_456",
    }
)
```

---

## 5. Grafana Dashboards

### 5.1 Prometheus Data Source Configuration

**File**: `grafana/datasources/prometheus.yaml`

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

### 5.2 MERL-T Overview Dashboard

**File**: `grafana/dashboards/merl-t-overview.json`

```json
{
  "dashboard": {
    "title": "MERL-T Overview",
    "panels": [
      {
        "id": 1,
        "title": "Request Rate (req/s)",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(merl_t_http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "P95 Latency (seconds)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(merl_t_http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "id": 3,
        "title": "LLM Cost (USD/hour)",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(merl_t_llm_cost_usd_total[1h]) * 3600",
            "legendFormat": "{{component}} - {{model}}"
          }
        ]
      },
      {
        "id": 4,
        "title": "Error Rate (%)",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(merl_t_http_requests_total{status_code=~\"5..\"}[5m]) / rate(merl_t_http_requests_total[5m]) * 100",
            "legendFormat": "{{endpoint}}"
          }
        ]
      }
    ]
  }
}
```

### 5.3 Alert Rules

**File**: `prometheus/alerts.yaml`

```yaml
groups:
  - name: merl_t_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: rate(merl_t_http_requests_total{status_code=~"5.."}[5m]) / rate(merl_t_http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} for endpoint {{ $labels.endpoint }}"

      # High latency
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(merl_t_http_request_duration_seconds_bucket[5m])) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P95 latency is {{ $value }}s for endpoint {{ $labels.endpoint }}"

      # High LLM cost
      - alert: HighLLMCost
        expr: rate(merl_t_llm_cost_usd_total[1h]) * 3600 > 50
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High LLM cost detected"
          description: "LLM cost is ${{ $value }}/hour for component {{ $labels.component }}"
```

---

## Summary

This Observability implementation provides:

1. **OpenTelemetry Tracing** with auto-instrumentation for FastAPI, httpx, Celery
2. **Prometheus Metrics** (HTTP, LLM, retrieval, RLCF, system)
3. **Structured JSON Logging** with trace_id propagation
4. **Grafana Dashboards** for visualization (overview, LLM costs, errors)
5. **Alert Rules** for high error rate, latency, and LLM costs

### Observability Targets

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| P95 Latency | < 10s | > 10s |
| Error Rate | < 1% | > 5% |
| LLM Cost | < $1000/day | > $50/hour |
| Uptime | > 99.5% | < 99% |

### Next Steps

1. Deploy OpenTelemetry Collector
2. Configure Jaeger for trace visualization
3. Set up Grafana dashboards
4. Configure alert channels (Slack, PagerDuty)
5. Implement log aggregation with Loki (optional)

### Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/observability/tracing.py` | OpenTelemetry setup | ~100 |
| `src/observability/spans.py` | Custom span creation | ~80 |
| `src/observability/metrics.py` | Prometheus metrics | ~150 |
| `src/api_gateway/middleware/metrics.py` | Metrics middleware | ~40 |
| `src/observability/logging.py` | Structured logging | ~80 |
| `grafana/dashboards/merl-t-overview.json` | Grafana dashboard | ~80 |
| `prometheus/alerts.yaml` | Alert rules | ~50 |

**Total: ~580 lines** (target: ~600 lines) ✅
