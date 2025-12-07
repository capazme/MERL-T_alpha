"""
Week 5 Day 5: Monitoring & Observability
=========================================

Provides comprehensive monitoring infrastructure for the pipeline:
- Prometheus metrics (latency, cache hit rate, error rate)
- Structured JSON logging with trace IDs
- Health check aggregation
- Alert thresholds

Features:
- Automatic metric collection per pipeline stage
- Cache performance tracking (hit/miss rate)
- Degradation mode detection
- Query understanding performance metrics
- OpenTelemetry-ready span tracking

Usage:
    from backend.preprocessing.monitoring import (
        PipelineMetrics,
        StructuredLogger,
        monitor_pipeline_stage
    )

    # Initialize metrics
    metrics = PipelineMetrics()

    # Track pipeline execution
    with monitor_pipeline_stage("query_understanding", trace_id="abc-123"):
        result = await query_understanding_function()

    # Log structured event
    logger = StructuredLogger("pipeline")
    logger.info("Pipeline completed", extra={
        "trace_id": "abc-123",
        "stages_completed": 5,
        "total_latency_ms": 990
    })
"""

import time
import logging
import json
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        Info,
        CollectorRegistry,
        generate_latest,
        CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Define dummy classes for when prometheus_client is not installed
    class Counter:
        def __init__(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self

    class Histogram:
        def __init__(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
        def time(self): return DummyTimer()

    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def dec(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self

    class Info:
        def __init__(self, *args, **kwargs): pass
        def info(self, *args, **kwargs): pass

    class CollectorRegistry:
        def __init__(self, *args, **kwargs): pass

    def generate_latest(*args, **kwargs): return b""
    CONTENT_TYPE_LATEST = "text/plain"

    class DummyTimer:
        def __enter__(self): return self
        def __exit__(self, *args): pass


# ==============================================
# Enums & Data Classes
# ==============================================

class PipelineStage(str, Enum):
    """Pipeline stage identifiers"""
    QUERY_UNDERSTANDING = "query_understanding"
    NER_EXTRACTION = "ner_extraction"
    INTENT_CLASSIFICATION = "intent_classification"
    KG_ENRICHMENT = "kg_enrichment"
    RLCF_PROCESSING = "rlcf_processing"
    FEEDBACK_PREPARATION = "feedback_preparation"


class MetricType(str, Enum):
    """Metric type identifiers"""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    INFO = "info"


@dataclass
class HealthStatus:
    """Health check status for a component"""
    component: str
    status: str  # healthy, degraded, unhealthy
    message: str
    timestamp: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MetricSnapshot:
    """Snapshot of metrics at a point in time"""
    timestamp: str
    pipeline_executions: int
    cache_hit_rate: float
    avg_latency_ms: float
    error_rate: float
    degraded_executions: int
    active_connections: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ==============================================
# Prometheus Metrics
# ==============================================

class PipelineMetrics:
    """
    Centralized Prometheus metrics for the pipeline.

    Tracks:
    - Pipeline execution counts (success/failure)
    - Stage latencies (per stage)
    - Cache hit/miss rates
    - Degradation events
    - Error counts by type
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()

        # Pipeline execution metrics
        self.pipeline_executions = Counter(
            'pipeline_executions_total',
            'Total number of pipeline executions',
            ['status'],  # success, failed, degraded
            registry=self.registry
        )

        self.pipeline_latency = Histogram(
            'pipeline_latency_seconds',
            'Pipeline execution latency in seconds',
            ['stage'],  # query_understanding, intent_classification, etc.
            buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0],
            registry=self.registry
        )

        # Cache metrics
        self.cache_operations = Counter(
            'cache_operations_total',
            'Total number of cache operations',
            ['operation', 'result'],  # operation: get/set, result: hit/miss/error
            registry=self.registry
        )

        self.cache_hit_rate = Gauge(
            'cache_hit_rate',
            'Cache hit rate (0.0-1.0)',
            registry=self.registry
        )

        # Query Understanding metrics
        self.query_understanding_confidence = Histogram(
            'query_understanding_confidence',
            'Query understanding confidence scores',
            buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0],
            registry=self.registry
        )

        self.entities_extracted = Histogram(
            'entities_extracted_count',
            'Number of entities extracted per query',
            buckets=[0, 1, 2, 5, 10, 20, 50],
            registry=self.registry
        )

        # KG Enrichment metrics
        self.kg_query_latency = Histogram(
            'kg_query_latency_seconds',
            'Neo4j query latency',
            ['query_type'],  # norms, sentenze, dottrina, contributions
            buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0],
            registry=self.registry
        )

        self.kg_results_count = Histogram(
            'kg_results_count',
            'Number of results returned from KG',
            ['result_type'],  # norms, sentenze, dottrina, contributions
            buckets=[0, 1, 5, 10, 20, 50, 100],
            registry=self.registry
        )

        # Degradation metrics
        self.degradation_events = Counter(
            'degradation_events_total',
            'Number of degradation events',
            ['component', 'reason'],  # component: neo4j/redis, reason: unavailable/timeout
            registry=self.registry
        )

        # Error metrics
        self.errors = Counter(
            'pipeline_errors_total',
            'Total number of errors',
            ['stage', 'error_type'],
            registry=self.registry
        )

        # Connection pool metrics
        self.active_connections = Gauge(
            'active_connections',
            'Number of active database connections',
            ['database'],  # neo4j, redis, postgres
            registry=self.registry
        )

        # System info
        self.system_info = Info(
            'pipeline_info',
            'Pipeline system information',
            registry=self.registry
        )
        self.system_info.info({
            'version': '2.0.0',
            'phase': 'phase2_week5',
            'prometheus_enabled': str(PROMETHEUS_AVAILABLE)
        })

    # Pipeline execution tracking
    def record_pipeline_execution(self, status: str) -> None:
        """Record a pipeline execution"""
        self.pipeline_executions.labels(status=status).inc()

    def record_stage_latency(self, stage: str, latency_seconds: float) -> None:
        """Record latency for a pipeline stage"""
        self.pipeline_latency.labels(stage=stage).observe(latency_seconds)

    # Cache tracking
    def record_cache_operation(self, operation: str, result: str) -> None:
        """
        Record a cache operation

        Args:
            operation: "get" or "set"
            result: "hit", "miss", "error"
        """
        self.cache_operations.labels(operation=operation, result=result).inc()

    def update_cache_hit_rate(self, hit_rate: float) -> None:
        """Update cache hit rate gauge"""
        self.cache_hit_rate.set(hit_rate)

    # Query Understanding tracking
    def record_query_understanding_confidence(self, confidence: float) -> None:
        """Record query understanding confidence score"""
        self.query_understanding_confidence.observe(confidence)

    def record_entities_extracted(self, count: int) -> None:
        """Record number of entities extracted"""
        self.entities_extracted.observe(count)

    # KG Enrichment tracking
    def record_kg_query_latency(self, query_type: str, latency_seconds: float) -> None:
        """Record Neo4j query latency"""
        self.kg_query_latency.labels(query_type=query_type).observe(latency_seconds)

    def record_kg_results_count(self, result_type: str, count: int) -> None:
        """Record number of KG results"""
        self.kg_results_count.labels(result_type=result_type).observe(count)

    # Degradation tracking
    def record_degradation_event(self, component: str, reason: str) -> None:
        """Record a degradation event"""
        self.degradation_events.labels(component=component, reason=reason).inc()

    # Error tracking
    def record_error(self, stage: str, error_type: str) -> None:
        """Record an error"""
        self.errors.labels(stage=stage, error_type=error_type).inc()

    # Connection tracking
    def set_active_connections(self, database: str, count: int) -> None:
        """Set active connection count"""
        self.active_connections.labels(database=database).set(count)

    def get_metrics_snapshot(self) -> MetricSnapshot:
        """Get a snapshot of current metrics"""
        # This is a simplified version - in production you'd query the registry
        return MetricSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            pipeline_executions=0,  # Would be computed from registry
            cache_hit_rate=0.0,
            avg_latency_ms=0.0,
            error_rate=0.0,
            degraded_executions=0,
            active_connections={}
        )


# Global metrics instance
_global_metrics: Optional[PipelineMetrics] = None


def get_metrics() -> PipelineMetrics:
    """Get the global metrics instance"""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = PipelineMetrics()
    return _global_metrics


# ==============================================
# Structured Logging
# ==============================================

class StructuredLogger:
    """
    Structured JSON logger with trace ID propagation.

    Logs are formatted as JSON with standard fields:
    - timestamp (ISO 8601)
    - level (INFO, WARNING, ERROR)
    - logger_name
    - message
    - trace_id (optional)
    - extra fields (component, stage, etc.)
    """

    def __init__(self, name: str, enable_json: bool = True):
        self.logger = logging.getLogger(name)
        self.enable_json = enable_json

        # Set up JSON formatter if enabled
        if self.enable_json and not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = JSONFormatter()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _log(
        self,
        level: int,
        message: str,
        trace_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """Internal log method"""
        log_data = {
            "trace_id": trace_id,
            **(extra or {})
        }

        self.logger.log(level, message, extra=log_data)

    def info(
        self,
        message: str,
        trace_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log info message"""
        self._log(logging.INFO, message, trace_id, extra)

    def warning(
        self,
        message: str,
        trace_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log warning message"""
        self._log(logging.WARNING, message, trace_id, extra)

    def error(
        self,
        message: str,
        trace_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: bool = False
    ) -> None:
        """Log error message"""
        if exc_info:
            extra = extra or {}
            extra["exc_info"] = True
        self._log(logging.ERROR, message, trace_id, extra)

    def debug(
        self,
        message: str,
        trace_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log debug message"""
        self._log(logging.DEBUG, message, trace_id, extra)


class JSONFormatter(logging.Formatter):
    """JSON log formatter"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add trace_id if present
        if hasattr(record, "trace_id") and record.trace_id:
            log_data["trace_id"] = record.trace_id

        # Add all extra fields
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", "funcName",
                          "levelname", "levelno", "lineno", "module", "msecs",
                          "message", "pathname", "process", "processName",
                          "relativeCreated", "thread", "threadName", "exc_info",
                          "exc_text", "stack_info", "trace_id"]:
                log_data[key] = value

        return json.dumps(log_data)


# Global logger instance
_global_logger: Optional[StructuredLogger] = None


def get_logger(name: str = "pipeline") -> StructuredLogger:
    """Get a structured logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger(name)
    return _global_logger


# ==============================================
# Context Managers for Monitoring
# ==============================================

@contextmanager
def monitor_pipeline_stage(
    stage: str,
    trace_id: Optional[str] = None,
    metrics: Optional[PipelineMetrics] = None
):
    """
    Context manager to monitor a pipeline stage.

    Automatically records:
    - Stage latency
    - Errors (if exception raised)
    - Structured logs

    Usage:
        with monitor_pipeline_stage("query_understanding", trace_id="abc"):
            result = await query_understanding()
    """
    metrics = metrics or get_metrics()
    logger = get_logger()

    start_time = time.time()
    logger.info(
        f"Stage started: {stage}",
        trace_id=trace_id,
        extra={"stage": stage, "event": "stage_start"}
    )

    try:
        yield
        # Success
        elapsed = time.time() - start_time
        metrics.record_stage_latency(stage, elapsed)
        logger.info(
            f"Stage completed: {stage}",
            trace_id=trace_id,
            extra={
                "stage": stage,
                "event": "stage_complete",
                "latency_ms": round(elapsed * 1000, 2)
            }
        )

    except Exception as e:
        # Error
        elapsed = time.time() - start_time
        metrics.record_error(stage, type(e).__name__)
        logger.error(
            f"Stage failed: {stage}",
            trace_id=trace_id,
            extra={
                "stage": stage,
                "event": "stage_error",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "latency_ms": round(elapsed * 1000, 2)
            },
            exc_info=True
        )
        raise


@asynccontextmanager
async def monitor_async_pipeline_stage(
    stage: str,
    trace_id: Optional[str] = None,
    metrics: Optional[PipelineMetrics] = None
):
    """
    Async context manager to monitor a pipeline stage.

    Usage:
        async with monitor_async_pipeline_stage("kg_enrichment", trace_id="abc"):
            result = await enrich_context()
    """
    metrics = metrics or get_metrics()
    logger = get_logger()

    start_time = time.time()
    logger.info(
        f"Async stage started: {stage}",
        trace_id=trace_id,
        extra={"stage": stage, "event": "stage_start"}
    )

    try:
        yield
        # Success
        elapsed = time.time() - start_time
        metrics.record_stage_latency(stage, elapsed)
        logger.info(
            f"Async stage completed: {stage}",
            trace_id=trace_id,
            extra={
                "stage": stage,
                "event": "stage_complete",
                "latency_ms": round(elapsed * 1000, 2)
            }
        )

    except Exception as e:
        # Error
        elapsed = time.time() - start_time
        metrics.record_error(stage, type(e).__name__)
        logger.error(
            f"Async stage failed: {stage}",
            trace_id=trace_id,
            extra={
                "stage": stage,
                "event": "stage_error",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "latency_ms": round(elapsed * 1000, 2)
            },
            exc_info=True
        )
        raise


# ==============================================
# Health Check Aggregation
# ==============================================

class HealthCheckAggregator:
    """
    Aggregates health checks from multiple components.

    Determines overall system health based on:
    - Neo4j availability
    - Redis availability
    - Pipeline orchestrator status
    - Error rates
    """

    def __init__(self):
        self.components: Dict[str, HealthStatus] = {}
        self.logger = get_logger("health_check")

    def register_component(
        self,
        component: str,
        status: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register a component health status"""
        health_status = HealthStatus(
            component=component,
            status=status,
            message=message,
            timestamp=datetime.utcnow().isoformat(),
            metadata=metadata or {}
        )
        self.components[component] = health_status

    def get_overall_status(self) -> str:
        """
        Get overall system health status.

        Returns:
            "healthy" - All components healthy
            "degraded" - Some components unhealthy but system functional
            "unhealthy" - Critical components down
        """
        if not self.components:
            return "unknown"

        statuses = [c.status for c in self.components.values()]

        # Critical components
        critical_components = ["orchestrator", "neo4j"]
        critical_statuses = [
            self.components[c].status
            for c in critical_components
            if c in self.components
        ]

        # If any critical component is unhealthy, system is unhealthy
        if "unhealthy" in critical_statuses:
            return "unhealthy"

        # If any component is degraded or unhealthy, system is degraded
        if "unhealthy" in statuses or "degraded" in statuses:
            return "degraded"

        # All healthy
        return "healthy"

    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        overall_status = self.get_overall_status()

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                name: status.to_dict()
                for name, status in self.components.items()
            },
            "summary": {
                "total_components": len(self.components),
                "healthy": sum(1 for c in self.components.values() if c.status == "healthy"),
                "degraded": sum(1 for c in self.components.values() if c.status == "degraded"),
                "unhealthy": sum(1 for c in self.components.values() if c.status == "unhealthy")
            }
        }


# Global health check aggregator
_global_health_aggregator: Optional[HealthCheckAggregator] = None


def get_health_aggregator() -> HealthCheckAggregator:
    """Get the global health check aggregator"""
    global _global_health_aggregator
    if _global_health_aggregator is None:
        _global_health_aggregator = HealthCheckAggregator()
    return _global_health_aggregator


# ==============================================
# Alert Thresholds
# ==============================================

@dataclass
class AlertThresholds:
    """Alert thresholds for monitoring"""
    # Latency thresholds (seconds)
    max_pipeline_latency: float = 2.0
    max_stage_latency: Dict[str, float] = None

    # Error rate thresholds
    max_error_rate: float = 0.05  # 5%

    # Cache performance thresholds
    min_cache_hit_rate: float = 0.60  # 60%

    # Degradation thresholds
    max_degraded_execution_rate: float = 0.10  # 10%

    # Connection pool thresholds
    max_connection_pool_usage: float = 0.80  # 80%

    def __post_init__(self):
        if self.max_stage_latency is None:
            self.max_stage_latency = {
                "query_understanding": 0.2,  # 200ms
                "intent_classification": 0.3,  # 300ms
                "kg_enrichment": 0.6,  # 600ms
                "rlcf_processing": 0.5,  # 500ms
                "feedback_preparation": 0.1  # 100ms
            }


class AlertManager:
    """
    Alert manager for threshold violations.

    Checks metrics against thresholds and logs alerts.
    """

    def __init__(
        self,
        thresholds: Optional[AlertThresholds] = None,
        metrics: Optional[PipelineMetrics] = None
    ):
        self.thresholds = thresholds or AlertThresholds()
        self.metrics = metrics or get_metrics()
        self.logger = get_logger("alerts")

    def check_latency_threshold(
        self,
        stage: str,
        latency_seconds: float,
        trace_id: Optional[str] = None
    ) -> None:
        """Check if stage latency exceeds threshold"""
        threshold = self.thresholds.max_stage_latency.get(stage)
        if threshold and latency_seconds > threshold:
            self.logger.warning(
                f"Stage latency threshold exceeded: {stage}",
                trace_id=trace_id,
                extra={
                    "alert_type": "latency_threshold_exceeded",
                    "stage": stage,
                    "latency_seconds": latency_seconds,
                    "threshold_seconds": threshold,
                    "overage_percent": round(
                        ((latency_seconds - threshold) / threshold) * 100,
                        2
                    )
                }
            )

    def check_cache_hit_rate(self, hit_rate: float) -> None:
        """Check if cache hit rate is below threshold"""
        if hit_rate < self.thresholds.min_cache_hit_rate:
            self.logger.warning(
                "Cache hit rate below threshold",
                extra={
                    "alert_type": "low_cache_hit_rate",
                    "hit_rate": hit_rate,
                    "threshold": self.thresholds.min_cache_hit_rate
                }
            )


# Global alert manager
_global_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get the global alert manager"""
    global _global_alert_manager
    if _global_alert_manager is None:
        _global_alert_manager = AlertManager()
    return _global_alert_manager


# ==============================================
# Exports
# ==============================================

__all__ = [
    # Metrics
    "PipelineMetrics",
    "get_metrics",
    "MetricSnapshot",

    # Logging
    "StructuredLogger",
    "get_logger",

    # Monitoring
    "monitor_pipeline_stage",
    "monitor_async_pipeline_stage",

    # Health checks
    "HealthCheckAggregator",
    "HealthStatus",
    "get_health_aggregator",

    # Alerts
    "AlertManager",
    "AlertThresholds",
    "get_alert_manager",

    # Enums
    "PipelineStage",
    "MetricType",

    # Constants
    "PROMETHEUS_AVAILABLE"
]
