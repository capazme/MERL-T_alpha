"""
OpenAPI Schema Customization for MERL-T API

This module provides custom OpenAPI schema generation with:
- API key authentication security scheme
- Rate limiting headers documentation
- Enhanced metadata and examples
- Security requirements per endpoint

Author: Week 9 Implementation
Date: November 2025
"""

from typing import Dict, Any, List
from fastapi.openapi.utils import get_openapi


def get_custom_openapi_schema(
    app,
    title: str,
    version: str,
    description: str,
    routes: List,
    tags: List[Dict[str, Any]],
    servers: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Generate custom OpenAPI schema with enhanced documentation.

    This function extends the default FastAPI OpenAPI schema with:
    - API key authentication security scheme
    - Rate limiting response headers
    - Security requirements on protected endpoints
    - Enhanced error responses

    Args:
        app: FastAPI application instance
        title: API title
        version: API version
        description: API description
        routes: List of API routes
        tags: List of tag metadata
        servers: List of server configurations

    Returns:
        Enhanced OpenAPI 3.1.0 schema dictionary
    """
    # Generate base OpenAPI schema
    openapi_schema = get_openapi(
        title=title,
        version=version,
        description=description,
        routes=routes,
        tags=tags,
        servers=servers,
    )

    # Add security schemes
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}

    # Define API Key authentication scheme
    openapi_schema["components"]["securitySchemes"]["ApiKeyAuth"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": """
**API Key Authentication**

All protected endpoints require authentication via API key.

**How to get an API key:**
1. Contact ALIS administrators for API key generation
2. Keys are hashed using SHA-256 before storage (secure)
3. Keys can have expiration dates and role-based permissions

**How to use:**
- Add `X-API-Key` header to your requests
- Example: `X-API-Key: your-api-key-here`

**Rate Limiting:**
- API keys are associated with rate limit tiers
- Check `X-RateLimit-*` headers in responses
- See Rate Limiting section for details

**Roles:**
- **admin**: Full access, unlimited rate limit
- **user**: Standard access, 100 requests/hour
- **guest**: Limited access, 10 requests/hour

**Security:**
- Never share your API key
- Store securely (environment variables, secrets manager)
- Rotate keys periodically
- Report compromised keys immediately
        """.strip()
    }

    # Add rate limiting response headers schema
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}

    # Define rate limit headers (for documentation)
    rate_limit_headers = {
        "X-RateLimit-Limit": {
            "description": "Maximum requests allowed in the time window (e.g., 100 for standard tier)",
            "schema": {"type": "integer", "example": 100}
        },
        "X-RateLimit-Remaining": {
            "description": "Remaining requests in current time window",
            "schema": {"type": "integer", "example": 87}
        },
        "X-RateLimit-Reset": {
            "description": "Unix timestamp when the rate limit resets",
            "schema": {"type": "integer", "example": 1699725600}
        },
        "X-RateLimit-Used": {
            "description": "Requests consumed in current time window",
            "schema": {"type": "integer", "example": 13}
        },
        "Retry-After": {
            "description": "Seconds to wait before retrying (only on 429 responses)",
            "schema": {"type": "integer", "example": 3600}
        }
    }

    # Add security requirements to protected endpoints
    for path, path_item in openapi_schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in ["get", "post", "put", "delete", "patch"]:
                continue

            # Skip public endpoints (health, root)
            if path in ["/", "/health"]:
                continue

            # Add security requirement for all other endpoints
            if "security" not in operation:
                operation["security"] = [{"ApiKeyAuth": []}]

            # Add rate limit headers to all responses
            if "responses" in operation:
                for status_code, response in operation["responses"].items():
                    if "headers" not in response:
                        response["headers"] = {}

                    # Add rate limit headers to successful responses
                    if status_code.startswith("2"):
                        response["headers"].update(rate_limit_headers)

                # Add 401 Unauthorized response if not present
                if "401" not in operation["responses"]:
                    operation["responses"]["401"] = {
                        "description": "Unauthorized - Missing or invalid API key",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "detail": {
                                            "type": "string",
                                            "example": "Missing API key. Provide X-API-Key header."
                                        }
                                    }
                                },
                                "examples": {
                                    "missing_key": {
                                        "summary": "Missing API key",
                                        "value": {
                                            "detail": "Missing API key. Provide X-API-Key header."
                                        }
                                    },
                                    "invalid_key": {
                                        "summary": "Invalid API key",
                                        "value": {
                                            "detail": "Invalid API key"
                                        }
                                    },
                                    "expired_key": {
                                        "summary": "Expired API key",
                                        "value": {
                                            "detail": "API key expired on 2025-01-15T10:30:00Z. Request new key."
                                        }
                                    },
                                    "inactive_key": {
                                        "summary": "Inactive API key",
                                        "value": {
                                            "detail": "API key is inactive. Contact administrator."
                                        }
                                    }
                                }
                            }
                        }
                    }

                # Add 403 Forbidden response for endpoints with role requirements
                if path.startswith("/admin") or "admin" in operation.get("summary", "").lower():
                    if "403" not in operation["responses"]:
                        operation["responses"]["403"] = {
                            "description": "Forbidden - Insufficient permissions",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "detail": {
                                                "type": "string",
                                                "example": "Insufficient permissions. Admin role required."
                                            }
                                        }
                                    }
                                }
                            }
                        }

                # Add 429 Too Many Requests response
                if "429" not in operation["responses"]:
                    operation["responses"]["429"] = {
                        "description": "Too Many Requests - Rate limit exceeded",
                        "headers": {
                            "X-RateLimit-Limit": rate_limit_headers["X-RateLimit-Limit"],
                            "X-RateLimit-Remaining": {
                                "description": "Remaining requests (0 when rate limited)",
                                "schema": {"type": "integer", "example": 0}
                            },
                            "X-RateLimit-Reset": rate_limit_headers["X-RateLimit-Reset"],
                            "X-RateLimit-Used": {
                                "description": "Requests consumed (equals quota when rate limited)",
                                "schema": {"type": "integer", "example": 100}
                            },
                            "Retry-After": rate_limit_headers["Retry-After"]
                        },
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {"type": "string"},
                                        "quota": {"type": "integer"},
                                        "detail": {"type": "string"},
                                        "reset_at": {"type": "string", "format": "date-time"}
                                    }
                                },
                                "example": {
                                    "error": "Rate limit exceeded",
                                    "quota": 100,
                                    "detail": "Rate limit exceeded. Limit: 100 requests per hour. Current usage: 100 requests. Reset at: 2025-01-15T14:30:00Z",
                                    "reset_at": "2025-01-15T14:30:00Z"
                                }
                            }
                        }
                    }

    return openapi_schema


# Rate limiting tiers documentation
RATE_LIMIT_TIERS = {
    "unlimited": {
        "quota": 999999,
        "description": "Unlimited requests (admin tier)",
        "typical_role": "admin"
    },
    "premium": {
        "quota": 1000,
        "description": "1,000 requests per hour",
        "typical_role": "premium user"
    },
    "standard": {
        "quota": 100,
        "description": "100 requests per hour",
        "typical_role": "user"
    },
    "limited": {
        "quota": 10,
        "description": "10 requests per hour",
        "typical_role": "guest"
    }
}


def add_rate_limiting_documentation(openapi_schema: Dict[str, Any]) -> None:
    """
    Add comprehensive rate limiting documentation to OpenAPI schema.

    Adds a reusable component with rate limiting information.
    """
    if "x-rate-limiting" not in openapi_schema:
        openapi_schema["x-rate-limiting"] = {
            "description": """
## Rate Limiting

The MERL-T API implements rate limiting to ensure fair usage and system stability.

### How It Works

- **Algorithm**: Sliding window (1-hour window)
- **Storage**: Redis for distributed rate limiting
- **Granularity**: Per API key
- **Headers**: All responses include rate limit information

### Tiers

| Tier | Quota | Typical Role |
|------|-------|--------------|
| Unlimited | 999,999/hour | Admin |
| Premium | 1,000/hour | Premium User |
| Standard | 100/hour | User |
| Limited | 10/hour | Guest |

### Response Headers

Every API response includes rate limit headers:

- `X-RateLimit-Limit`: Maximum requests per hour for your tier
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when the window resets
- `X-RateLimit-Used`: Requests consumed in current window

### Handling Rate Limits

When you exceed your quota:
1. **HTTP 429** response with `Retry-After` header
2. Wait for the time specified in `Retry-After` (seconds)
3. Or wait until `X-RateLimit-Reset` timestamp
4. Then retry your request

**Example Response:**
```json
{
  "error": "Rate limit exceeded",
  "quota": 100,
  "detail": "Rate limit exceeded. Limit: 100 requests per hour. ...",
  "reset_at": "2025-01-15T14:30:00Z"
}
```

### Best Practices

1. **Monitor headers**: Check `X-RateLimit-Remaining` before making requests
2. **Implement backoff**: Use exponential backoff when approaching limits
3. **Cache results**: Avoid redundant API calls
4. **Request upgrade**: Contact ALIS for higher tier access if needed
5. **Handle 429 gracefully**: Don't retry immediately, respect `Retry-After`

### Graceful Degradation

If Redis is unavailable:
- Rate limiting is disabled temporarily
- Headers show: `X-RateLimit-Used: 0`, `X-RateLimit-Remaining: <quota>`
- No 429 errors during this time
- Normal operation resumes when Redis reconnects
            """.strip(),
            "tiers": RATE_LIMIT_TIERS
        }
