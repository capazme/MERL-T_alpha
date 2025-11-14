# RLCF API Documentation

**Status**: Reference documentation for RLCF API endpoints
**Last Updated**: November 2025

---

## Overview

The RLCF (Reinforcement Learning from Community Feedback) framework provides REST API endpoints for:
- User management with authority scoring
- Task creation and management
- Feedback submission and aggregation
- Configuration management

---

## API Documentation Location

**Complete API documentation** has been consolidated in the main API directory:

📚 **Primary API Documentation**: [`docs/api/`](../../../api/)

This directory contains:
- **[API_EXAMPLES.md](../../../api/API_EXAMPLES.md)** - Real-world usage examples with Italian legal scenarios
- **[AUTHENTICATION.md](../../../api/AUTHENTICATION.md)** - API key authentication, role-based access control
- **[RATE_LIMITING.md](../../../api/RATE_LIMITING.md)** - Rate limiting tiers, quotas, headers

---

## RLCF-Specific Endpoints

The RLCF framework (Phase 1) implements the following endpoint categories:

### User Management
- `POST /users/` - Create user
- `GET /users/{user_id}` - Get user by ID
- `GET /users/all` - List all users
- `POST /users/{user_id}/credentials/` - Add credential

**Authority Scoring**: Each user has dynamic authority score calculated as:
```
A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)
```
Where:
- B_u = Baseline credential score
- T_u(t-1) = Temporal track record score
- P_u(t) = Performance score

### Task Management
- `POST /tasks/` - Create legal task
- `GET /tasks/{task_id}` - Get task by ID
- `GET /tasks/` - List all tasks (with filtering)
- `PUT /tasks/{task_id}` - Update task

**Task Types**:
- LEGAL_RESEARCH: General legal research questions
- CASE_ANALYSIS: Specific case analysis
- REGULATORY_COMPLIANCE: Compliance verification
- RETRIEVAL_VALIDATION: Validate retrieval results (with authority-weighted aggregation)

### Feedback Management
- `POST /feedback/` - Submit feedback
- `GET /feedback/task/{task_id}` - Get feedback for task
- `POST /feedback/batch` - Batch feedback submission

**Aggregation**: Feedback is aggregated using:
- Authority-weighted voting
- Shannon entropy for uncertainty preservation
- Dynamic consensus thresholds by task type

### Configuration Management (Dynamic)
- `GET /config/task` - Get task configuration
- `GET /config/model` - Get model configuration
- `POST /config/task/type` - Create task type
- `PUT /config/task/type/{name}` - Update task type
- `DELETE /config/task/type/{name}` - Delete task type

**Hot-Reload**: Configuration changes applied without server restart.

---

## Orchestration API (Extended)

The full MERL-T system extends RLCF with orchestration endpoints:

### Query Execution
- `POST /query/execute` - Execute legal query (preprocessing → routing → retrieval → reasoning → synthesis)
- `GET /query/{trace_id}` - Get query result by trace ID
- `GET /query/{trace_id}/trace` - Get execution trace

### Feedback (Extended)
- `POST /feedback/submit` - Submit expert/user feedback
- `POST /feedback/ner-correction` - Submit NER correction for model training
- `GET /feedback/{feedback_id}` - Get feedback details

### Statistics & Analytics
- `GET /stats/queries` - Query execution statistics
- `GET /stats/users/{user_id}` - User performance statistics
- `GET /stats/system` - System health metrics

**See**: [`docs/api/API_EXAMPLES.md`](../../../api/API_EXAMPLES.md) for detailed usage examples.

---

## Authentication

All API endpoints use **API key authentication** with role-based access control.

**Roles**:
- `admin`: Full system access (unlimited rate limit)
- `user`: Standard access (100 req/hour)
- `guest`: Limited access (10 req/hour)

**Header**:
```http
X-API-Key: your-api-key-here
```

**See**: [`docs/api/AUTHENTICATION.md`](../../../api/AUTHENTICATION.md) for complete authentication guide.

---

## Rate Limiting

API requests are rate-limited by tier:

| Tier | Quota | Typical Role |
|------|-------|--------------|
| unlimited | 999,999/hour | admin |
| premium | 1,000/hour | user (paid) |
| standard | 100/hour | user (free) |
| limited | 10/hour | guest |

**Headers**:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699900800
```

**See**: [`docs/api/RATE_LIMITING.md`](../../../api/RATE_LIMITING.md) for rate limiting details.

---

## OpenAPI/Swagger Documentation

**Interactive API Documentation** available at:

```
http://localhost:8000/docs         # Swagger UI
http://localhost:8000/redoc        # ReDoc
http://localhost:8000/openapi.json # OpenAPI schema
```

---

## Code Location

**Implementation**:
- RLCF Core: `backend/rlcf_framework/main.py`, `routers/`
- Orchestration API: `backend/orchestration/api/main.py`, `routers/`
- Middleware: `backend/orchestration/api/middleware/auth.py`, `rate_limit.py`

**Tests**:
- RLCF Tests: `tests/rlcf/test_config_router.py`
- Orchestration Tests: `tests/orchestration/test_api_*.py`
- Authentication Tests: `tests/orchestration/test_auth*.py`

---

## Migration Note

**Legacy Documentation**: The files `authentication.md`, `endpoints.md`, and `schemas.md` in this directory have been archived. All API documentation is now maintained in `docs/api/` for consistency and ease of maintenance.

**Current Status**:
- ✅ `docs/api/` - Active, complete API documentation
- 🗄️ `docs/02-methodology/rlcf/api/` - This README serves as redirect

---

## Related Documentation

- **RLCF Framework Overview**: [`docs/02-methodology/rlcf/RLCF.md`](../RLCF.md)
- **Architecture**: [`docs/03-architecture/05-learning-layer.md`](../../../03-architecture/05-learning-layer.md)
- **Testing Guide**: [`docs/08-iteration/TESTING_STRATEGY.md`](../../../08-iteration/TESTING_STRATEGY.md)
- **Implementation Roadmap**: [`docs/IMPLEMENTATION_ROADMAP.md`](../../../IMPLEMENTATION_ROADMAP.md)

---

**Version**: 2.0 (Consolidated)
**Maintainer**: MERL-T Development Team
