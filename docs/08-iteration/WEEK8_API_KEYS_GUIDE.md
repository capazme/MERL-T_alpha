# API Key Authentication & Rate Limiting Guide

**Week 8 Day 4 Implementation**
**Date**: November 6, 2025
**Status**: ✅ Complete

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [API Key Tiers](#api-key-tiers)
4. [Using API Keys](#using-api-keys)
5. [Generating New API Keys](#generating-new-api-keys)
6. [Rate Limiting](#rate-limiting)
7. [Protected Endpoints](#protected-endpoints)
8. [Error Responses](#error-responses)
9. [Administration](#administration)

---

## Overview

The MERL-T Orchestration API uses **API key authentication** with **role-based access control** (RBAC) and **Redis-based rate limiting**.

### Key Features

- ✅ **SHA-256 hashed keys** (never stores plaintext)
- ✅ **Role-based access control** (admin, user, guest)
- ✅ **Rate limiting tiers** (unlimited, premium, standard, limited)
- ✅ **Sliding window algorithm** for accurate rate limiting
- ✅ **Graceful degradation** (works without Redis)
- ✅ **Usage tracking** for analytics
- ✅ **API key expiration** support

---

## Architecture

### Components

```
┌─────────────────────────────────────────────┐
│         FastAPI Request                      │
│  Header: X-API-Key: merl-t-user-key-dev-only │
└────────────────┬────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────┐
│  Middleware: verify_api_key()                  │
│  1. Extract key from X-API-Key header          │
│  2. Hash key with SHA-256                      │
│  3. Query PostgreSQL for api_keys              │
│  4. Verify: active, not expired                │
└────────────────┬───────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────┐
│  Middleware: check_rate_limit()                │
│  1. Query Redis sorted set (sliding window)    │
│  2. Check: current_count < quota               │
│  3. Add current request timestamp              │
│  4. Return 429 if quota exceeded               │
└────────────────┬───────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────┐
│  Protected Endpoint Handler                    │
│  - Access to api_key model (role, tier, etc)   │
│  - Rate limit headers added to response        │
└────────────────────────────────────────────────┘
```

### Database Tables

**api_keys**:
```sql
CREATE TABLE api_keys (
    key_id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(100),
    api_key_hash VARCHAR(64) UNIQUE,  -- SHA-256 hash
    role VARCHAR(20),                  -- admin, user, guest
    rate_limit_tier VARCHAR(20),       -- unlimited, premium, standard, limited
    is_active BOOLEAN,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    ...
);
```

**api_usage**:
```sql
CREATE TABLE api_usage (
    usage_id VARCHAR(36) PRIMARY KEY,
    key_id VARCHAR(36) REFERENCES api_keys,
    endpoint VARCHAR(255),
    method VARCHAR(10),
    response_status INTEGER,
    response_time_ms NUMERIC(10, 2),
    ip_address VARCHAR(45),
    timestamp TIMESTAMP,
    ...
);
```

---

## API Key Tiers

### Tier Comparison

| Tier | Quota (req/hour) | Typical Role | Use Case |
|------|------------------|--------------|----------|
| **unlimited** | 999,999 | admin | Internal services, admin tools |
| **premium** | 1,000 | user (paid) | High-volume production users |
| **standard** | 100 | user (free) | Default tier for registered users |
| **limited** | 10 | guest | Trial users, public demos |

### Role Permissions

| Role | Can Access | Typical Tier |
|------|------------|--------------|
| **admin** | All endpoints (including admin-only) | unlimited |
| **user** | Query execution, feedback submission | standard or premium |
| **guest** | Read-only endpoints | limited |

---

## Using API Keys

### HTTP Header

Include your API key in the `X-API-Key` header:

```bash
curl -X POST https://api.merl-t.com/query/execute \
  -H "X-API-Key: merl-t-user-key-dev-only" \
  -H "Content-Type: application/json" \
  -d '{"query": "Che dice l'\''art. 2043 c.c.?"}'
```

### Python Example

```python
import requests

API_KEY = "merl-t-user-key-dev-only"
BASE_URL = "http://localhost:8000"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

response = requests.post(
    f"{BASE_URL}/query/execute",
    headers=headers,
    json={"query": "Che dice l'art. 2043 c.c.?"}
)

print(response.json())
```

### JavaScript/TypeScript Example

```typescript
const API_KEY = "merl-t-user-key-dev-only";
const BASE_URL = "http://localhost:8000";

const response = await fetch(`${BASE_URL}/query/execute`, {
  method: "POST",
  headers: {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    query: "Che dice l'art. 2043 c.c.?",
  }),
});

const data = await response.json();
console.log(data);
```

---

## Generating New API Keys

### Step 1: Generate Random Key

```bash
# Generate a secure random API key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Output**: `Zx3Kj9mN_pQr8sT5vW2yA1bC4dE7fG0hI-jK6lM`

### Step 2: Hash the Key

```bash
# Hash the key with SHA-256
python -c "import hashlib; key='Zx3Kj9mN_pQr8sT5vW2yA1bC4dE7fG0hI-jK6lM'; print(hashlib.sha256(key.encode()).hexdigest())"
```

**Output**: `a1b2c3d4e5f6...` (64 character hex string)

### Step 3: Insert into Database

```sql
INSERT INTO api_keys (
    key_id,
    api_key_hash,
    role,
    rate_limit_tier,
    is_active,
    description,
    created_by
) VALUES (
    uuid_generate_v4()::text,
    'a1b2c3d4e5f6...',  -- Hash from Step 2
    'user',
    'standard',
    TRUE,
    'Production user key for client XYZ',
    'admin@merl-t.com'
);
```

### Step 4: Provide Key to User

⚠️ **SECURITY WARNING**: The plaintext key (`Zx3Kj9mN_pQr8sT5vW2yA1bC4dE7fG0hI-jK6lM`) should be:
- Sent to the user **ONE TIME ONLY** (e.g., via secure email)
- **NEVER** stored in database
- **NEVER** logged
- User should store it securely (e.g., password manager, environment variable)

---

## Rate Limiting

### Sliding Window Algorithm

Uses Redis sorted sets with timestamps:

```
Redis Key: rate_limit:<key_id>
Sorted Set:
  {timestamp1: score1, timestamp2: score2, ...}

Algorithm:
1. Remove entries older than window_start (current_time - 3600 seconds)
2. Count remaining entries
3. If count >= quota: DENY (HTTP 429)
4. Else: ALLOW and add current timestamp
```

### Rate Limit Headers

Every response includes rate limit headers:

```
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1699300800
X-RateLimit-Used: 13
```

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Total quota for your tier |
| `X-RateLimit-Remaining` | Requests remaining in current window |
| `X-RateLimit-Reset` | Unix timestamp when window resets (UTC) |
| `X-RateLimit-Used` | Requests used so far in current window |

### HTTP 429 Response

When rate limit exceeded:

```json
{
  "detail": {
    "error": "Rate limit exceeded",
    "message": "You have exceeded your standard tier quota of 100 requests per hour.",
    "current_usage": 101,
    "quota": 100,
    "tier": "standard",
    "retry_after": 3600,
    "reset_at": "2025-11-06T22:40:00Z"
  }
}
```

Headers:
```
HTTP/1.1 429 Too Many Requests
Retry-After: 3600
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1699300800
```

---

## Protected Endpoints

### Endpoints Requiring Authentication

All orchestration API endpoints require authentication:

| Endpoint | Method | Required Role | Rate Limited |
|----------|--------|---------------|--------------|
| `/query/execute` | POST | user or admin | ✅ |
| `/query/retrieve/{trace_id}` | GET | user or admin | ✅ |
| `/query/history` | GET | user or admin | ✅ |
| `/feedback/submit` | POST | user or admin | ✅ |
| `/stats/usage` | GET | user or admin | ✅ |
| `/stats/performance` | GET | admin | ✅ |
| `/health` | GET | (public) | ❌ |

### Applying Authentication in Code

```python
from fastapi import Depends
from backend.orchestration.api.middleware import verify_api_key, require_role, check_rate_limit
from backend.orchestration.api.models import ApiKey

# Basic authentication
@router.post("/query/execute")
async def execute_query(
    request: QueryRequest,
    api_key: ApiKey = Depends(verify_api_key),  # Authenticate
    _rate_limit: None = Depends(check_rate_limit)  # Rate limit
):
    # api_key.role, api_key.rate_limit_tier available here
    ...

# Admin-only endpoint
@router.get("/stats/performance")
async def get_performance(
    api_key: ApiKey = Depends(require_role("admin")),  # Admin only
    _rate_limit: None = Depends(check_rate_limit)
):
    ...

# Multiple roles allowed
@router.get("/feedback/list")
async def list_feedback(
    api_key: ApiKey = Depends(require_role(["admin", "user"]))
):
    ...
```

---

## Error Responses

### 401 Unauthorized

**Missing API Key**:
```json
{
  "detail": "Missing API key. Provide X-API-Key header."
}
```

**Invalid API Key**:
```json
{
  "detail": "Invalid API key"
}
```

**Inactive API Key**:
```json
{
  "detail": "API key is inactive. Contact administrator."
}
```

**Expired API Key**:
```json
{
  "detail": "API key expired on 2025-10-01T00:00:00Z. Request new key."
}
```

### 403 Forbidden

**Insufficient Permissions**:
```json
{
  "detail": "Insufficient permissions. Required role: admin"
}
```

### 429 Too Many Requests

See [Rate Limiting](#http-429-response) section above.

---

## Administration

### View All API Keys

```sql
SELECT
    key_id,
    user_id,
    role,
    rate_limit_tier,
    is_active,
    created_at,
    expires_at,
    last_used_at,
    description
FROM api_keys
ORDER BY created_at DESC;
```

### Deactivate API Key

```sql
UPDATE api_keys
SET is_active = FALSE
WHERE key_id = 'user-key-001';
```

### Extend Expiration

```sql
UPDATE api_keys
SET expires_at = NOW() + INTERVAL '1 year'
WHERE key_id = 'user-key-001';
```

### View Usage Statistics

```sql
SELECT
    k.key_id,
    k.role,
    k.rate_limit_tier,
    COUNT(u.usage_id) AS total_requests,
    AVG(u.response_time_ms) AS avg_response_time_ms,
    MAX(u.timestamp) AS last_request_at
FROM api_keys k
LEFT JOIN api_usage u ON k.key_id = u.key_id
WHERE u.timestamp > NOW() - INTERVAL '24 hours'
GROUP BY k.key_id, k.role, k.rate_limit_tier
ORDER BY total_requests DESC;
```

### Monitor Rate Limit Status

```sql
-- Requests in last hour per key
SELECT
    key_id,
    COUNT(*) AS requests_last_hour
FROM api_usage
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY key_id
ORDER BY requests_last_hour DESC;
```

---

## Migration Instructions

### Apply Migration

```bash
# Using Docker PostgreSQL
docker exec -i merl-t-postgres-orchestration psql -U merl_t -d orchestration_db < migrations/002_create_auth_tables.sql

# Native PostgreSQL
psql -U merl_t -d orchestration_db -f migrations/002_create_auth_tables.sql
```

### Verify Migration

```sql
-- Check tables created
\dt

-- Check seed data
SELECT key_id, role, rate_limit_tier, description FROM api_keys;

-- Test rate limit function
SELECT get_rate_limit_quota('premium');  -- Should return 1000
```

---

## Development Keys

⚠️ **WARNING**: Change these in production!

### Admin Key

```
Plaintext: merl-t-admin-key-dev-only-change-in-production
Hash: 8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92
Role: admin
Tier: unlimited
```

### User Key

```
Plaintext: merl-t-user-key-dev-only
Hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
Role: user
Tier: standard
```

---

## Security Best Practices

1. ✅ **Never commit API keys** to version control
2. ✅ **Use environment variables** for keys in production
3. ✅ **Rotate keys** regularly (every 90 days recommended)
4. ✅ **Set expiration dates** for all keys
5. ✅ **Monitor usage logs** for suspicious activity
6. ✅ **Use HTTPS only** in production
7. ✅ **Implement key rotation** before expiration
8. ✅ **Audit API key access** monthly
9. ✅ **Revoke unused keys** immediately
10. ✅ **Use different keys** per environment (dev, staging, prod)

---

## Troubleshooting

### Rate Limiting Not Working

**Symptom**: Requests never return HTTP 429
**Cause**: Redis not available or `REDIS_ENABLED=false`
**Solution**:
```bash
# Check Redis connection
docker ps | grep redis

# Enable Redis in .env
REDIS_ENABLED=true

# Restart services
docker-compose restart
```

### API Key Not Found

**Symptom**: Always returns "Invalid API key"
**Cause**: Key not in database or wrong hash
**Solution**:
```sql
-- Verify key exists
SELECT key_id, role, is_active FROM api_keys
WHERE api_key_hash = 'your-hash-here';

-- Check if inactive
SELECT * FROM api_keys WHERE is_active = FALSE;
```

### High Response Times

**Symptom**: Slow authentication
**Cause**: Database query performance
**Solution**:
```sql
-- Verify indexes exist
\di

-- Create missing index
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(api_key_hash);
```

---

## Future Enhancements

- [ ] API key management UI
- [ ] Webhook notifications for rate limit events
- [ ] Dynamic tier upgrades/downgrades
- [ ] IP whitelisting per API key
- [ ] JWT token support (in addition to API keys)
- [ ] OAuth2 integration
- [ ] Multi-factor authentication for admin keys
- [ ] Automatic key rotation

---

**Document Version**: 1.0
**Last Updated**: November 6, 2025
**Author**: Claude Code
