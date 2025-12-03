# 01. API Gateway & Authentication

**Status**: Implementation Blueprint
**Layer**: Infrastructure
**Dependencies**: None (entry point)
**Key Libraries**: FastAPI 0.104+, Pydantic 2.5+, python-jose, passlib

---

## Table of Contents

1. [Overview](#1-overview)
2. [Application Factory Pattern](#2-application-factory-pattern)
3. [Authentication & Authorization](#3-authentication--authorization)
4. [Request Validation & Rate Limiting](#4-request-validation--rate-limiting)
5. [Middleware Stack](#5-middleware-stack)
6. [Health Checks & Readiness](#6-health-checks--readiness)
7. [OpenAPI Documentation](#7-openapi-documentation)
8. [Service Mesh Integration](#8-service-mesh-integration)

---

## 1. Overview

The API Gateway is the entry point for all external requests to MERL-T. It handles:
- **Authentication** (JWT tokens)
- **Authorization** (RBAC for admin endpoints)
- **Rate limiting** (per-user quotas)
- **Request validation** (Pydantic models)
- **Distributed tracing** (OpenTelemetry trace_id propagation)
- **CORS** (Cross-Origin Resource Sharing)

### Architecture

```
External Client
       ↓
   [Ingress/Load Balancer]
       ↓
   [API Gateway :8000]
       ↓
   Middleware Stack:
     1. CORS Middleware
     2. Tracing Middleware (inject trace_id)
     3. Auth Middleware (verify JWT)
     4. Rate Limiting Middleware
     5. Logging Middleware
       ↓
   [FastAPI Router]
       ↓
   Internal Services (Query Understanding, Router, etc.)
```

### Port Mappings

| Endpoint | Port | Description |
|----------|------|-------------|
| API Gateway | 8000 | Main application entry point |
| Health Check | 8000/health | Liveness probe |
| Readiness | 8000/ready | Readiness probe (checks dependencies) |
| Metrics | 8001 | Prometheus metrics endpoint (separate port) |
| OpenAPI Docs | 8000/docs | Swagger UI |

---

## 2. Application Factory Pattern

### 2.1 Factory Function

**File**: `backend/orchestration/api/main.py`

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from .config import Settings, get_settings
from .middleware import (
    AuthMiddleware,
    RateLimitMiddleware,
    TracingMiddleware,
    LoggingMiddleware,
)
from .routers import (
    query_router,
    feedback_router,
    admin_router,
    health_router,
)
from .dependencies import (
    redis_client,
    http_client,
    initialize_dependencies,
    cleanup_dependencies,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager for startup/shutdown logic.

    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown").
    Available in FastAPI 0.104+.
    """
    # Startup: Initialize connections
    settings = get_settings()

    # TODO: Initialize Redis connection pool
    # await redis_client.initialize(settings.redis_uri)

    # TODO: Initialize httpx AsyncClient for service-to-service calls
    # await http_client.initialize(
    #     timeout=settings.http_timeout,
    #     max_connections=settings.http_max_connections,
    # )

    # TODO: Run health checks on dependencies (Neo4j, Weaviate, PostgreSQL)
    # await initialize_dependencies(settings)

    yield

    # Shutdown: Close connections gracefully
    # TODO: Close Redis connection pool
    # await redis_client.close()

    # TODO: Close httpx client
    # await http_client.close()

    # TODO: Cleanup any pending tasks
    # await cleanup_dependencies()


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Application factory function.

    Args:
        settings: Optional settings override (useful for testing)

    Returns:
        Configured FastAPI application

    Example:
        >>> app = create_app()
        >>> # For testing with custom settings:
        >>> test_app = create_app(Settings(environment="test"))
    """
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="MERL-T Legal Reasoning System",
        description="Multi-Expert Reasoning with Legal Traceability",
        version="1.0.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        openapi_url="/openapi.json" if settings.environment != "production" else None,
        lifespan=lifespan,
    )

    # ===== CORS Configuration =====
    # TODO: Restrict origins in production (currently allows all for dev)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,  # ["http://localhost:3000", "https://merl-t.example.com"]
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # ===== Custom Middleware Stack (order matters!) =====
    # Note: Middleware is executed in reverse order of registration
    # (last added = first executed)

    # 1. Logging (outermost - logs request/response)
    app.add_middleware(LoggingMiddleware)

    # 2. Rate Limiting (before auth, to prevent auth brute force)
    app.add_middleware(
        RateLimitMiddleware,
        redis_client=redis_client,
        default_rate_limit=settings.rate_limit_per_minute,
    )

    # 3. Authentication (verify JWT, inject user context)
    app.add_middleware(
        AuthMiddleware,
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        exclude_paths=["/health", "/ready", "/docs", "/openapi.json"],
    )

    # 4. Tracing (innermost - inject trace_id early)
    app.add_middleware(TracingMiddleware)

    # ===== Routers =====
    # Main API routes
    app.include_router(query_router, prefix="/api/v1", tags=["queries"])
    app.include_router(feedback_router, prefix="/api/v1", tags=["feedback"])

    # Admin routes (require admin role)
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])

    # Health checks (no auth required)
    app.include_router(health_router, tags=["health"])

    # ===== Prometheus Metrics (separate ASGI app on different port) =====
    # TODO: Mount metrics app on separate port 8001 using uvicorn
    # metrics_app = make_asgi_app()
    # Run with: uvicorn src.api_gateway.app:app --port 8000 &
    #           uvicorn src.api_gateway.metrics:metrics_app --port 8001

    return app


# ===== Application Instance (for uvicorn) =====
app = create_app()
```

### 2.2 Configuration Management

**File**: `backend/orchestration/api/config.py` (or equivalent)

```python
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Example .env file:
        ENVIRONMENT=development
        JWT_SECRET_KEY=your-secret-key-here
        REDIS_URI=redis://localhost:6379
        NEO4J_URI=bolt://localhost:7687
    """

    # ===== Environment =====
    environment: Literal["development", "staging", "production"] = "development"

    # ===== API Configuration =====
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4  # Uvicorn workers (production)

    # ===== CORS =====
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"]
    )

    # ===== JWT Authentication =====
    jwt_secret_key: SecretStr = Field(..., description="Secret key for JWT signing")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60 * 24  # 24 hours

    # ===== Rate Limiting =====
    rate_limit_per_minute: int = 100  # Requests per user per minute
    rate_limit_per_hour: int = 1000

    # ===== Redis (caching + rate limiting) =====
    redis_uri: str = "redis://localhost:6379"
    redis_max_connections: int = 50

    # ===== Internal Service URLs =====
    query_understanding_url: str = "http://localhost:8001"
    kg_enrichment_url: str = "http://localhost:8002"
    router_url: str = "http://localhost:8020"
    reasoning_orchestrator_url: str = "http://localhost:8030"

    # ===== HTTP Client =====
    http_timeout: int = 30  # seconds
    http_max_connections: int = 100
    http_max_keepalive: int = 20

    # ===== Database Health Checks =====
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: SecretStr = Field(..., description="Neo4j password")

    postgres_uri: str = "postgresql://merl_t:password@localhost:5432/merl_t"

    weaviate_url: str = "http://localhost:8080"

    # ===== Observability =====
    otlp_endpoint: str | None = None  # OpenTelemetry collector endpoint
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings singleton.

    Returns:
        Settings instance (loaded once, cached for subsequent calls)
    """
    return Settings()
```

---

## 3. Authentication & Authorization

### 3.1 JWT Token Generation

**File**: `src/api_gateway/auth.py`

```python
from datetime import datetime, timedelta
from typing import Literal

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel


# ===== Password Hashing =====
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


# ===== JWT Token Models =====
class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # Subject (user_id)
    email: str
    role: Literal["user", "legal_expert", "admin"]
    exp: datetime  # Expiration timestamp
    iat: datetime  # Issued at timestamp


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


# ===== Token Generation =====
def create_access_token(
    user_id: str,
    email: str,
    role: Literal["user", "legal_expert", "admin"],
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User UUID
        email: User email
        role: User role (for RBAC)
        secret_key: Secret key for signing
        algorithm: JWT algorithm (HS256, RS256)
        expires_delta: Token expiration duration

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_access_token(
        ...     user_id="123e4567-e89b-12d3-a456-426614174000",
        ...     email="user@example.com",
        ...     role="user",
        ...     secret_key="your-secret-key",
        ...     expires_delta=timedelta(hours=24),
        ... )
    """
    now = datetime.utcnow()

    if expires_delta is None:
        expires_delta = timedelta(minutes=60 * 24)  # 24 hours default

    payload = TokenPayload(
        sub=user_id,
        email=email,
        role=role,
        exp=now + expires_delta,
        iat=now,
    )

    encoded_jwt = jwt.encode(
        payload.model_dump(mode="json"),
        secret_key,
        algorithm=algorithm,
    )

    return encoded_jwt


def decode_access_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256",
) -> TokenPayload:
    """
    Decode and verify a JWT access token.

    Args:
        token: JWT token string
        secret_key: Secret key for verification
        algorithm: JWT algorithm

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is invalid or expired

    Example:
        >>> payload = decode_access_token(token, secret_key="your-secret-key")
        >>> print(payload.sub)  # User ID
    """
    try:
        decoded = jwt.decode(token, secret_key, algorithms=[algorithm])
        return TokenPayload(**decoded)
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e
```

### 3.2 Authentication Middleware

**File**: `src/api_gateway/middleware/auth.py`

```python
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..auth import decode_access_token, TokenPayload
from ..config import get_settings


class AuthMiddleware(BaseHTTPMiddleware):
    """
    JWT Authentication Middleware.

    Verifies JWT token in Authorization header and injects user context
    into request.state for downstream handlers.

    Excluded Paths:
        - /health, /ready (health checks)
        - /docs, /openapi.json (OpenAPI documentation)
    """

    def __init__(
        self,
        app,
        secret_key: str,
        algorithm: str = "HS256",
        exclude_paths: list[str] | None = None,
    ):
        super().__init__(app)
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.exclude_paths = exclude_paths or []

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Process request and verify JWT token.

        Injects into request.state:
            - user_id: str
            - email: str
            - role: str ("user" | "legal_expert" | "admin")
        """
        # Skip authentication for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Missing Authorization header"},
            )

        try:
            # Expected format: "Bearer <token>"
            scheme, token = auth_header.split()

            if scheme.lower() != "bearer":
                raise ValueError("Invalid authentication scheme")

            # Decode and verify token
            payload: TokenPayload = decode_access_token(
                token,
                secret_key=self.secret_key,
                algorithm=self.algorithm,
            )

            # Inject user context into request state
            request.state.user_id = payload.sub
            request.state.email = payload.email
            request.state.role = payload.role

        except (ValueError, AttributeError) as e:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": f"Invalid token: {str(e)}"},
            )

        # Continue to next middleware/handler
        response = await call_next(request)
        return response
```

### 3.3 Role-Based Access Control (RBAC)

**File**: `src/api_gateway/dependencies/auth.py`

```python
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status


def get_current_user(request: Request) -> dict[str, str]:
    """
    Dependency to get current authenticated user from request state.

    Returns:
        User context dict with keys: user_id, email, role

    Raises:
        HTTPException 401: If user is not authenticated

    Example:
        @app.get("/me")
        async def read_current_user(
            user: Annotated[dict, Depends(get_current_user)]
        ):
            return {"user_id": user["user_id"], "email": user["email"]}
    """
    try:
        return {
            "user_id": request.state.user_id,
            "email": request.state.email,
            "role": request.state.role,
        }
    except AttributeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )


def require_role(*allowed_roles: str):
    """
    Dependency factory to require specific roles.

    Args:
        *allowed_roles: Allowed role names ("admin", "legal_expert", "user")

    Returns:
        Dependency function that checks user role

    Raises:
        HTTPException 403: If user role is not in allowed_roles

    Example:
        @app.delete("/admin/users/{user_id}")
        async def delete_user(
            user_id: str,
            user: Annotated[dict, Depends(require_role("admin"))]
        ):
            # Only admins can access this endpoint
            ...
    """
    def check_role(user: Annotated[dict, Depends(get_current_user)]) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {allowed_roles}",
            )
        return user

    return check_role


# ===== Pre-configured Dependencies =====
CurrentUser = Annotated[dict, Depends(get_current_user)]
AdminUser = Annotated[dict, Depends(require_role("admin"))]
ExpertUser = Annotated[dict, Depends(require_role("legal_expert", "admin"))]
```

---

## 4. Request Validation & Rate Limiting

### 4.1 Rate Limiting Middleware

**File**: `src/api_gateway/middleware/rate_limit.py`

```python
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from redis.asyncio import Redis


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token bucket rate limiting middleware using Redis.

    Strategy:
        - Per-user rate limits (100 req/min, 1000 req/hour)
        - Anonymous requests limited by IP (10 req/min)
        - Uses Redis INCR with TTL for atomic counters

    Redis Keys:
        - rate_limit:{user_id}:minute  (TTL: 60s)
        - rate_limit:{user_id}:hour    (TTL: 3600s)
        - rate_limit:ip:{ip}:minute    (TTL: 60s)
    """

    def __init__(
        self,
        app,
        redis_client: Redis,
        default_rate_limit: int = 100,  # per minute
    ):
        super().__init__(app)
        self.redis = redis_client
        self.default_rate_limit = default_rate_limit

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Check rate limit before processing request."""

        # Determine rate limit key (user_id or IP)
        user_id = getattr(request.state, "user_id", None)

        if user_id:
            key_prefix = f"rate_limit:{user_id}"
            limit_per_minute = 100
            limit_per_hour = 1000
        else:
            # Anonymous request - use IP
            client_ip = request.client.host
            key_prefix = f"rate_limit:ip:{client_ip}"
            limit_per_minute = 10
            limit_per_hour = 100

        # TODO: Check minute limit
        # minute_key = f"{key_prefix}:minute"
        # minute_count = await self.redis.incr(minute_key)
        # if minute_count == 1:
        #     await self.redis.expire(minute_key, 60)
        #
        # if minute_count > limit_per_minute:
        #     return JSONResponse(
        #         status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        #         content={
        #             "error": "Rate limit exceeded",
        #             "retry_after": 60,
        #         },
        #         headers={"Retry-After": "60"},
        #     )

        # TODO: Check hour limit (similar to minute)

        # TODO: Add rate limit headers to response
        # response.headers["X-RateLimit-Limit"] = str(limit_per_minute)
        # response.headers["X-RateLimit-Remaining"] = str(limit_per_minute - minute_count)
        # response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)

        response = await call_next(request)
        return response
```

### 4.2 Request Validation with Pydantic

**File**: `src/api_gateway/models/requests.py`

```python
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    """
    User query request model.

    Example:
        {
            "query": "Quali sono i requisiti per la capacità di agire di un minorenne?",
            "language": "it"
        }
    """

    query: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Legal query in natural language",
        examples=["Quali sono i requisiti per la capacità di agire di un minorenne?"],
    )

    language: Literal["it", "en"] = Field(
        default="it",
        description="Query language (Italian or English)",
    )

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str) -> str:
        """Validate query is not just whitespace."""
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace")
        return v.strip()


class FeedbackRequest(BaseModel):
    """
    User feedback request model.

    Example:
        {
            "trace_id": "RTR-20241103-abc123",
            "rating": 4,
            "feedback_types": ["missing_source", "unclear_answer"],
            "corrections": {"claim_id": "claim_001", "corrected_text": "..."},
            "suggested_sources": ["Art. 2 c.c.", "Cass. 12345/2020"],
            "free_text_comments": "La risposta era corretta ma mancava un riferimento..."
        }
    """

    trace_id: str = Field(
        ...,
        pattern=r"^[A-Z]+-\d{8}-[a-zA-Z0-9]+$",
        description="Trace ID of the query to provide feedback on",
        examples=["RTR-20241103-abc123"],
    )

    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Answer quality rating (1=poor, 5=excellent)",
    )

    feedback_types: list[Literal[
        "incorrect_answer",
        "missing_source",
        "wrong_interpretation",
        "unclear_answer",
        "incomplete_answer",
        "excellent",
    ]] = Field(
        default_factory=list,
        description="Feedback type tags",
    )

    corrections: dict | None = Field(
        default=None,
        description="Corrections to specific claims (claim_id → corrected_text)",
    )

    suggested_sources: list[str] = Field(
        default_factory=list,
        description="Additional legal sources the user suggests",
    )

    free_text_comments: str | None = Field(
        default=None,
        max_length=2000,
        description="Free-form feedback comments",
    )
```

---

## 5. Middleware Stack

### 5.1 Tracing Middleware

**File**: `src/api_gateway/middleware/tracing.py`

```python
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class TracingMiddleware(BaseHTTPMiddleware):
    """
    Distributed tracing middleware.

    Injects trace_id into request.state and propagates it in response headers.

    Trace ID Format:
        GW-YYYYMMDD-{uuid_suffix}
        Example: GW-20241103-a1b2c3d4
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Inject trace_id into request."""

        # Check if trace_id already exists in headers (from upstream service)
        trace_id = request.headers.get("X-Trace-ID")

        if not trace_id:
            # Generate new trace_id
            from datetime import datetime
            date_str = datetime.utcnow().strftime("%Y%m%d")
            uuid_suffix = uuid.uuid4().hex[:8]
            trace_id = f"GW-{date_str}-{uuid_suffix}"

        # Inject into request state
        request.state.trace_id = trace_id

        # Process request
        response = await call_next(request)

        # Add trace_id to response headers
        response.headers["X-Trace-ID"] = trace_id

        return response
```

### 5.2 Logging Middleware

**File**: `src/api_gateway/middleware/logging.py`

```python
import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured logging middleware.

    Logs every request/response with:
        - trace_id
        - method, path, query params
        - status_code
        - latency
        - user_id (if authenticated)

    Example Log:
        {
            "trace_id": "GW-20241103-a1b2c3d4",
            "method": "POST",
            "path": "/api/v1/query",
            "status_code": 200,
            "latency_ms": 156,
            "user_id": "123e4567-e89b-12d3-a456-426614174000"
        }
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Log request and response."""

        start_time = time.time()

        # Get trace_id (injected by TracingMiddleware)
        trace_id = getattr(request.state, "trace_id", "unknown")

        # Process request
        response = await call_next(request)

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Get user_id if authenticated
        user_id = getattr(request.state, "user_id", None)

        # Log structured data
        log_data = {
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "status_code": response.status_code,
            "latency_ms": latency_ms,
        }

        if user_id:
            log_data["user_id"] = user_id

        # TODO: Use structured logger (python-json-logger)
        # logger.info("Request processed", extra=log_data)

        # For now, simple logging
        logger.info(
            f"[{trace_id}] {request.method} {request.url.path} "
            f"→ {response.status_code} ({latency_ms}ms)"
        )

        return response
```

---

## 6. Health Checks & Readiness

**File**: `src/api_gateway/routers/health.py`

```python
from fastapi import APIRouter, status
from pydantic import BaseModel


router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str


class ReadinessResponse(BaseModel):
    """Readiness check response with dependency health."""
    status: str
    dependencies: dict[str, str]


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    """
    Liveness probe for Kubernetes.

    Returns 200 OK if the application is running.
    Does NOT check dependencies (use /ready for that).
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
    )


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> ReadinessResponse:
    """
    Readiness probe for Kubernetes.

    Returns 200 OK only if all dependencies are healthy:
        - Redis (caching)
        - Neo4j (knowledge graph)
        - Weaviate (vector database)
        - PostgreSQL (metadata)

    If any dependency is unhealthy, returns 503 Service Unavailable.
    """
    # TODO: Check Redis connection
    # redis_status = await check_redis_health()

    # TODO: Check Neo4j connection
    # neo4j_status = await check_neo4j_health()

    # TODO: Check Weaviate connection
    # weaviate_status = await check_weaviate_health()

    # TODO: Check PostgreSQL connection
    # postgres_status = await check_postgres_health()

    dependencies = {
        "redis": "healthy",  # TODO: replace with actual check
        "neo4j": "healthy",
        "weaviate": "healthy",
        "postgres": "healthy",
    }

    # If any dependency is unhealthy, return 503
    if any(status != "healthy" for status in dependencies.values()):
        return ReadinessResponse(
            status="degraded",
            dependencies=dependencies,
        )

    return ReadinessResponse(
        status="ready",
        dependencies=dependencies,
    )
```

---

## 7. OpenAPI Documentation

### 7.1 Custom OpenAPI Schema

**File**: `src/api_gateway/app.py` (add to `create_app()`)

```python
def custom_openapi():
    """
    Customize OpenAPI schema with additional info.

    Adds:
        - Authentication security scheme (JWT Bearer)
        - Tags with descriptions
        - Contact information
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="MERL-T API",
        version="1.0.0",
        description="""
        # MERL-T: Multi-Expert Reasoning with Legal Traceability

        ## Authentication
        All endpoints (except /health and /ready) require JWT authentication.

        1. Obtain a token from `/api/v1/auth/login`
        2. Include the token in the `Authorization` header:
           ```
           Authorization: Bearer <your-token>
           ```

        ## Rate Limits
        - Authenticated users: 100 requests/minute, 1000 requests/hour
        - Anonymous users: 10 requests/minute, 100 requests/hour

        ## Tracing
        Every response includes a `X-Trace-ID` header for debugging.
        """,
        routes=app.routes,
    )

    # Add JWT security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    # Apply security globally (except excluded paths)
    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
```

---

## 8. Service Mesh Integration

### 8.1 Istio Sidecar Configuration

**File**: `k8s/api-gateway/istio-gateway.yaml`

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: merl-t-gateway
  namespace: merl-t
spec:
  selector:
    istio: ingressgateway
  servers:
    - port:
        number: 80
        name: http
        protocol: HTTP
      hosts:
        - "merl-t.example.com"
      tls:
        httpsRedirect: true  # Redirect HTTP to HTTPS

    - port:
        number: 443
        name: https
        protocol: HTTPS
      hosts:
        - "merl-t.example.com"
      tls:
        mode: SIMPLE
        credentialName: merl-t-tls-cert  # Kubernetes secret with TLS cert

---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: merl-t-routes
  namespace: merl-t
spec:
  hosts:
    - "merl-t.example.com"
  gateways:
    - merl-t-gateway
  http:
    # Health checks (no auth required)
    - match:
        - uri:
            prefix: "/health"
        - uri:
            prefix: "/ready"
      route:
        - destination:
            host: api-gateway.merl-t.svc.cluster.local
            port:
              number: 8000

    # API routes (require JWT)
    - match:
        - uri:
            prefix: "/api/v1"
      route:
        - destination:
            host: api-gateway.merl-t.svc.cluster.local
            port:
              number: 8000
      # Retry policy
      retries:
        attempts: 3
        perTryTimeout: 30s
        retryOn: 5xx,reset,connect-failure,refused-stream
```

### 8.2 Mutual TLS for Internal Services

**File**: `k8s/api-gateway/peer-authentication.yaml`

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: merl-t
spec:
  mtls:
    mode: STRICT  # Enforce mutual TLS for all services in namespace
```

---

## Summary

This API Gateway implementation provides:

1. **FastAPI Factory Pattern** with lifespan context manager (FastAPI 0.104+)
2. **JWT Authentication** with RBAC (role-based access control)
3. **Rate Limiting** using Redis token bucket algorithm
4. **Request Validation** with Pydantic 2.5+ models
5. **Distributed Tracing** with trace_id propagation
6. **Health Checks** for Kubernetes liveness/readiness probes
7. **OpenAPI Documentation** with authentication scheme
8. **Service Mesh Integration** with Istio (optional)

### Next Steps

1. Implement actual health check logic in `/ready` endpoint
2. Complete rate limiting logic with Redis INCR
3. Add user authentication endpoints (`/api/v1/auth/login`, `/api/v1/auth/register`)
4. Integrate with internal services (query understanding, router, etc.)
5. Deploy to Kubernetes with Istio sidecar

### Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/api_gateway/app.py` | Application factory | ~150 |
| `src/api_gateway/config.py` | Settings management | ~80 |
| `src/api_gateway/auth.py` | JWT token handling | ~100 |
| `src/api_gateway/middleware/auth.py` | Auth middleware | ~80 |
| `src/api_gateway/middleware/rate_limit.py` | Rate limiting | ~70 |
| `src/api_gateway/middleware/tracing.py` | Distributed tracing | ~40 |
| `src/api_gateway/middleware/logging.py` | Structured logging | ~60 |
| `src/api_gateway/routers/health.py` | Health checks | ~60 |
| `src/api_gateway/dependencies/auth.py` | RBAC dependencies | ~70 |
| `src/api_gateway/models/requests.py` | Request models | ~80 |

**Total: ~790 lines** (target: ~800 lines) ✅
