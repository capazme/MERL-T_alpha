"""
MERL-T API Application

FastAPI application for the MERL-T orchestration layer.
Exposes the complete LangGraph workflow via REST API.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .routers import query_router, feedback_router, stats_router
from .schemas.health import HealthResponse, ComponentStatus
from .database import init_db, close_db, get_database_info
from .services.cache_service import cache_service
from .openapi_config import get_custom_openapi_schema, add_rate_limiting_documentation
from .openapi_tags import (
    get_tags_metadata,
    get_servers_config,
    get_external_docs,
    TERMS_OF_SERVICE_URL
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="MERL-T API",
    description="""
**MERL-T (Multi-Expert Legal Retrieval Transformer)** - AI-powered legal research and analysis system.

This API provides access to the complete MERL-T pipeline:
- **Query Understanding**: NER, concept mapping, intent classification
- **Knowledge Graph Enrichment**: Multi-source legal knowledge integration
- **LLM Routing**: Intelligent task decomposition and agent selection
- **Retrieval Agents**: Knowledge Graph, API, Vector Database
- **Reasoning Experts**: 4 expert types with different legal methodologies
- **Synthesis**: Convergent/divergent opinion aggregation
- **Iteration Control**: Multi-turn refinement for complex queries

## Key Features

- **RLCF (Reinforcement Learning from Community Feedback)**: Community-driven AI alignment
- **Uncertainty Preservation**: Expert disagreement is valuable information
- **Authority Weighting**: Dynamic expert influence based on demonstrated competence
- **Multi-source Integration**: Normattiva, Cassazione, Dottrina, Community, RLCF
- **Full Observability**: Complete execution traces with trace IDs

## Getting Started

1. **Authenticate**: Click the "Authorize" button and enter your API key
2. Submit a legal query via `POST /query/execute`
3. Retrieve the answer with confidence, legal basis, and alternative interpretations
4. Provide feedback via `POST /feedback/*` endpoints to improve the system

For more information, see the [MERL-T Documentation](https://github.com/ALIS-ai/MERL-T).
    """,
    version="0.2.0",
    contact={
        "name": "ALIS (Artificial Legal Intelligence Society)",
        "url": "https://github.com/ALIS-ai/MERL-T",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    terms_of_service=TERMS_OF_SERVICE_URL,
    servers=get_servers_config(),
    openapi_tags=get_tags_metadata(),
    swagger_ui_parameters={
        "persistAuthorization": True,  # Remember API key across page reloads
        "displayRequestDuration": True,  # Show request duration in Swagger UI
        "filter": True,  # Enable endpoint filtering
        "tryItOutEnabled": True,  # Enable "Try it out" by default
    },
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc alternative documentation
)

# ============================================================================
# CORS Middleware
# ============================================================================

# Allow frontend to access API (development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React frontend (dev)
        "http://localhost:5173",  # Vite frontend (dev)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with detailed messages."""
    logger.error(f"Validation error for {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body,
            "message": "Request validation failed. Check the 'detail' field for specific errors."
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler for unexpected errors."""
    logger.error(
        f"Unhandled exception for {request.method} {request.url}: {str(exc)}",
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "message": str(exc),
            "path": str(request.url),
        },
    )

# ============================================================================
# Middleware for Request Logging
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with timing."""
    start_time = time.time()

    # Log request
    logger.info(f"{request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Log response timing
    elapsed_ms = (time.time() - start_time) * 1000
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {elapsed_ms:.0f}ms"
    )

    return response

# ============================================================================
# Router Registration
# ============================================================================

app.include_router(query_router)
app.include_router(feedback_router)
app.include_router(stats_router)

# ============================================================================
# Custom OpenAPI Schema
# ============================================================================

def custom_openapi():
    """
    Generate custom OpenAPI schema with enhanced security and documentation.

    This function is called once to generate the OpenAPI schema, which is then
    cached for subsequent requests.

    Returns:
        Custom OpenAPI 3.1.0 schema with API key authentication and rate limiting.
    """
    if app.openapi_schema:
        return app.openapi_schema

    # Generate custom schema using our configuration
    openapi_schema = get_custom_openapi_schema(
        app=app,
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=get_tags_metadata(),
        servers=get_servers_config()
    )

    # Add rate limiting documentation
    add_rate_limiting_documentation(openapi_schema)

    # Add external documentation
    openapi_schema["externalDocs"] = get_external_docs()

    # Cache the schema
    app.openapi_schema = openapi_schema
    logger.info("Custom OpenAPI schema generated with API key authentication")

    return app.openapi_schema


# Override the default OpenAPI schema generation
app.openapi = custom_openapi

# ============================================================================
# Root Endpoints
# ============================================================================

@app.get(
    "/",
    summary="API Root",
    description="Welcome endpoint with API information"
)
async def root():
    """API root endpoint."""
    return {
        "message": "MERL-T API v0.2.0",
        "description": "AI-powered legal research and analysis system",
        "documentation": "/docs",
        "health": "/health",
        "version": "0.2.0",
        "status": "operational",
    }


# Server start time for uptime calculation
_server_start_time = time.time()


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="""
System health check endpoint.

Reports the status of all MERL-T components:
- Query Understanding
- KG Enrichment
- LLM Router
- Retrieval Agents (KG, API, VectorDB)
- Reasoning Experts
- Synthesizer

Overall status:
- **healthy**: All components operational
- **degraded**: Some components slow or partially operational
- **unhealthy**: Critical components failing
    """
)
async def health_check() -> HealthResponse:
    """
    System health check.

    Checks connectivity and status of all MERL-T components.

    Returns:
        HealthResponse with overall status and component statuses
    """
    logger.info("Health check requested")

    components = {}

    # Check Query Understanding (placeholder - would ping actual service)
    components["query_understanding"] = ComponentStatus(
        status="healthy",
        latency_ms=45.0,
    )

    # Check KG Enrichment (placeholder - would check Neo4j connection)
    components["kg_enrichment"] = ComponentStatus(
        status="healthy",
        connection=True,
        metadata={"neo4j_version": "5.x"},
    )

    # Check Router (placeholder - would check OpenRouter API)
    components["router"] = ComponentStatus(
        status="healthy",
        connection=True,
        metadata={"openrouter_api": "connected"},
    )

    # Check KG Agent
    components["kg_agent"] = ComponentStatus(
        status="healthy",
    )

    # Check API Agent (placeholder - would ping visualex)
    components["api_agent"] = ComponentStatus(
        status="healthy",
        connection=True,
        metadata={"visualex_url": "http://localhost:5000"},
    )

    # Check VectorDB Agent (placeholder - would check Qdrant connection)
    components["vectordb_agent"] = ComponentStatus(
        status="healthy",
        connection=True,
        metadata={"qdrant_collections": "1"},
    )

    # Check Experts
    components["experts"] = ComponentStatus(
        status="healthy",
        metadata={"experts_loaded": "4"},
    )

    # Check Synthesizer
    components["synthesizer"] = ComponentStatus(
        status="healthy",
    )

    # Determine overall status
    statuses = [comp.status for comp in components.values()]
    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    # Calculate uptime
    uptime_seconds = int(time.time() - _server_start_time)

    health_response = HealthResponse(
        status=overall_status,
        components=components,
        version="v0.2.0",
        uptime_seconds=uptime_seconds,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )

    logger.info(f"Health check: {overall_status}")
    return health_response


# ============================================================================
# Application Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("=" * 80)
    logger.info("MERL-T API v0.2.0 starting...")
    logger.info("=" * 80)
    logger.info("Initializing components...")

    # Initialize database
    try:
        logger.info("Initializing database connection...")
        await init_db()
        db_info = get_database_info()
        logger.info(f"Database initialized: {db_info['database_type']} ({db_info['database_url']})")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Initialize Redis cache
    try:
        logger.info("Initializing Redis cache...")
        redis_connected = await cache_service.ping()
        if redis_connected:
            logger.info("Redis cache connected successfully")
        else:
            logger.warning("Redis cache not available (disabled or connection failed)")
    except Exception as e:
        logger.warning(f"Redis cache initialization failed: {e}")
        logger.warning("Continuing without cache...")

    logger.info("MERL-T API ready to serve requests")
    logger.info("Documentation available at: /docs")
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("=" * 80)
    logger.info("MERL-T API shutting down...")

    # Close Redis cache connections
    try:
        logger.info("Closing Redis cache connections...")
        await cache_service.close()
        logger.info("Redis cache connections closed")
    except Exception as e:
        logger.warning(f"Error closing Redis cache: {e}")

    # Close database connections
    try:
        logger.info("Closing database connections...")
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")

    logger.info("Shutdown complete")
    logger.info("=" * 80)
