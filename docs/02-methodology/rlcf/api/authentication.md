# API Authentication

The RLCF framework implements a tiered authentication system to secure admin operations while maintaining open access for research activities.

## Authentication Overview

### Security Model
- **Public Endpoints**: Open access for research and evaluation activities
- **Admin Endpoints**: API key authentication for system configuration
- **Database Operations**: Internal session-based authentication

### Security Principles
- **Principle of Least Privilege**: Users have minimal necessary access
- **Defense in Depth**: Multiple security layers
- **Audit Trail**: All admin operations logged
- **Constitutional Compliance**: Security measures align with transparency principles

## API Key Authentication

### Admin API Key Setup

1. **Environment Configuration**:
```bash
# Set admin API key
export ADMIN_API_KEY="your-secure-api-key-here"

# For production, use a cryptographically secure key
export ADMIN_API_KEY=$(openssl rand -hex 32)
```

2. **Key Security Best Practices**:
```bash
# Generate secure key (32 bytes = 64 hex characters)
python -c "import secrets; print(secrets.token_hex(32))"

# Example: 7f3c4e8a9b1d2e5f8c6a7b4e9d2c5f8a3b6c9e2f5a8b1c4d7e0a3f6b9c2e5f8a1b4
```

3. **Production Deployment**:
```yaml
# docker-compose.yml
version: '3.8'
services:
  rlcf-api:
    environment:
      - ADMIN_API_KEY_FILE=/run/secrets/admin_api_key
    secrets:
      - admin_api_key

secrets:
  admin_api_key:
    file: ./secrets/admin_api_key.txt
```

### Using API Keys

#### Request Headers
```bash
curl -X PUT "http://localhost:8000/config/model" \
  -H "X-API-KEY: your-api-key" \
  -H "Content-Type: application/json" \
  -d @config.json
```

#### Python SDK Example
```python
import requests

class RLCFClient:
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({"X-API-KEY": api_key})
    
    def update_model_config(self, config: dict):
        """Update model configuration (requires admin access)."""
        response = self.session.put(
            f"{self.base_url}/config/model",
            json=config
        )
        response.raise_for_status()
        return response.json()
    
    def get_tasks(self, limit: int = 50):
        """Get tasks (public access)."""
        response = self.session.get(
            f"{self.base_url}/tasks/all",
            params={"limit": limit}
        )
        response.raise_for_status()
        return response.json()

# Usage
client = RLCFClient("http://localhost:8000", api_key="your-key")
```

## Endpoint Access Control

### Public Endpoints (No Authentication Required)

#### Research Operations
```
GET  /tasks/all                 # View all tasks
GET  /tasks/{task_id}           # View specific task
POST /tasks/                    # Create new task
GET  /users/all                 # View all users
POST /users/                    # Create new user
POST /feedback/                 # Submit feedback
```

#### Data Access
```
GET  /authority/stats           # Authority statistics
GET  /bias/task/{task_id}/report # Bias analysis
GET  /aggregation/disagreement/{task_id} # Disagreement analysis
GET  /export/tasks              # Export task data
```

#### AI Service (Public with Rate Limiting)
```
GET  /ai/models                 # Available AI models
```

### Admin Endpoints (API Key Required)

#### Configuration Management
```
PUT  /config/model              # Update model configuration
PUT  /config/tasks              # Update task configuration
GET  /config/validate           # Validate configuration changes
```

#### AI Service Administration
```
POST /ai/generate_response      # Generate AI responses
PUT  /ai/models/config          # Configure AI models
```

#### System Administration
```
GET  /admin/system/health       # System health check
POST /admin/system/backup       # Create system backup
PUT  /admin/users/{id}/status   # Modify user status
DELETE /admin/tasks/{id}        # Delete tasks (admin only)
```

## Implementation Details

### FastAPI Security Integration

```python
# main.py
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
import os

# Security configuration
API_KEY = os.getenv("ADMIN_API_KEY", "development-key-change-in-production")
API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    """Validate API key for admin endpoints."""
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=403, 
            detail="Invalid API key. Admin access required."
        )

# Admin endpoint example
@app.put("/config/model", tags=["Admin"])
async def update_model_config(
    new_config: dict,
    api_key: str = Depends(get_api_key)  # Requires valid API key
):
    """Update model configuration (admin only)."""
    # Implementation here
    pass

# Public endpoint example
@app.get("/tasks/all", tags=["Public"])
async def get_all_tasks(limit: int = 50):
    """Get all tasks (public access)."""
    # No authentication required
    pass
```

### Security Middleware

```python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import time

# CORS configuration for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Host validation for production
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "your-api-domain.com"]
)

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    """Basic rate limiting for API endpoints."""
    start_time = time.time()
    
    # Check rate limits based on endpoint and IP
    if request.url.path.startswith("/ai/"):
        # Stricter limits for AI endpoints
        await check_rate_limit(request.client.host, limit=10, window=60)
    elif request.url.path.startswith("/admin/"):
        # Admin endpoint limits
        await check_rate_limit(request.client.host, limit=50, window=60)
    
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    return response
```

## Security Best Practices

### API Key Management

#### Development Environment
```bash
# Use .env file for development (never commit to git)
echo "ADMIN_API_KEY=development-key-123" > .env

# Load environment variables
export $(cat .env | xargs)
```

#### Production Environment
```bash
# Use secure secret management
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name "rlcf/admin-api-key" \
  --secret-string "your-secure-key"

# Kubernetes secrets
kubectl create secret generic rlcf-admin-key \
  --from-literal=api-key="your-secure-key"

# Docker secrets
echo "your-secure-key" | docker secret create admin_api_key -
```

#### Key Rotation
```python
# Automated key rotation example
import schedule
import time
from datetime import datetime

def rotate_api_key():
    """Rotate API key monthly for security."""
    new_key = secrets.token_hex(32)
    
    # Update key in secret management system
    update_secret("rlcf/admin-api-key", new_key)
    
    # Log rotation event
    logger.info(f"API key rotated at {datetime.now()}")
    
    # Notify administrators
    send_notification("API key has been rotated")

# Schedule monthly rotation
schedule.every().month.do(rotate_api_key)
```

### Input Validation and Sanitization

```python
from pydantic import BaseModel, validator
from typing import Dict, Any
import re

class ConfigurationUpdate(BaseModel):
    """Secure configuration update model."""
    
    authority_weights: Dict[str, float]
    thresholds: Dict[str, float]
    
    @validator('authority_weights')
    def validate_authority_weights(cls, v):
        """Ensure authority weights sum to 1.0 and are non-negative."""
        if abs(sum(v.values()) - 1.0) > 0.001:
            raise ValueError("Authority weights must sum to 1.0")
        
        if any(weight < 0 for weight in v.values()):
            raise ValueError("Authority weights must be non-negative")
        
        return v
    
    @validator('thresholds')
    def validate_thresholds(cls, v):
        """Ensure thresholds are within valid ranges."""
        for key, value in v.items():
            if key == "disagreement" and not 0.0 <= value <= 1.0:
                raise ValueError("Disagreement threshold must be in [0.0, 1.0]")
        
        return v
```

### SQL Injection Prevention

```python
# Safe database queries using SQLAlchemy ORM
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user_safely(db: AsyncSession, user_id: int):
    """Safe user lookup using parameterized queries."""
    # SQLAlchemy ORM automatically handles parameterization
    result = await db.execute(
        select(models.User).filter(models.User.id == user_id)
    )
    return result.scalar_one_or_none()

# NEVER do this (vulnerable to SQL injection):
# query = f"SELECT * FROM users WHERE id = {user_id}"  # DANGEROUS!

# Always use parameterized queries:
# SQLAlchemy handles this automatically
```

### Formula Evaluation Security

```python
# Safe mathematical expression evaluation
import asteval
from typing import Dict, Any

def create_safe_evaluator() -> asteval.Interpreter:
    """Create restricted evaluator for user-defined formulas."""
    evaluator = asteval.Interpreter()
    
    # Allow only safe mathematical functions
    safe_functions = {
        'sqrt': math.sqrt,
        'min': min,
        'max': max,
        'abs': abs,
        'round': round,
        'pow': pow,
        'log': math.log,
        'exp': math.exp
    }
    evaluator.symtable.update(safe_functions)
    
    # Disable dangerous operations
    evaluator.no_print = True
    evaluator.max_time = 1.0  # 1 second timeout
    evaluator.max_depth = 100  # Limit recursion depth
    
    # Remove access to built-in functions that could be dangerous
    del evaluator.symtable['__import__']
    del evaluator.symtable['eval']
    del evaluator.symtable['exec']
    del evaluator.symtable['open']
    
    return evaluator

def safe_formula_evaluation(expression: str, variables: Dict[str, float]) -> float:
    """Safely evaluate user-defined mathematical expressions."""
    evaluator = create_safe_evaluator()
    
    # Set variables in safe namespace
    for var_name, var_value in variables.items():
        if isinstance(var_value, (int, float)):
            evaluator.symtable[var_name] = float(var_value)
        else:
            raise ValueError(f"Invalid variable type: {type(var_value)}")
    
    try:
        result = evaluator.eval(expression)
        
        # Validate result
        if not isinstance(result, (int, float)):
            raise ValueError("Expression must evaluate to a number")
        
        if math.isnan(result) or math.isinf(result):
            raise ValueError("Expression resulted in NaN or infinity")
        
        return float(result)
    
    except Exception as e:
        raise ValueError(f"Formula evaluation error: {str(e)}")
```

## Monitoring and Logging

### Security Event Logging

```python
import logging
from datetime import datetime
from typing import Optional

# Configure security logger
security_logger = logging.getLogger("rlcf.security")
security_logger.setLevel(logging.INFO)

# Add secure log handler
handler = logging.FileHandler("security.log")
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
security_logger.addHandler(handler)

class SecurityAuditor:
    """Audit security-relevant events."""
    
    @staticmethod
    def log_admin_action(action: str, user_ip: str, success: bool, details: Optional[str] = None):
        """Log administrative actions."""
        status = "SUCCESS" if success else "FAILURE"
        message = f"Admin action: {action} | IP: {user_ip} | Status: {status}"
        
        if details:
            message += f" | Details: {details}"
        
        if success:
            security_logger.info(message)
        else:
            security_logger.warning(message)
    
    @staticmethod
    def log_authentication_attempt(ip: str, endpoint: str, success: bool):
        """Log authentication attempts."""
        status = "SUCCESS" if success else "FAILURE"
        message = f"Auth attempt: {endpoint} | IP: {ip} | Status: {status}"
        
        if success:
            security_logger.info(message)
        else:
            security_logger.warning(message)
    
    @staticmethod
    def log_suspicious_activity(activity: str, ip: str, details: str):
        """Log potentially suspicious activities."""
        message = f"Suspicious activity: {activity} | IP: {ip} | Details: {details}"
        security_logger.error(message)

# Usage in endpoints
@app.put("/config/model")
async def update_model_config(
    new_config: dict,
    request: Request,
    api_key: str = Depends(get_api_key)
):
    try:
        # Update configuration
        result = await perform_config_update(new_config)
        
        SecurityAuditor.log_admin_action(
            action="config_update",
            user_ip=request.client.host,
            success=True,
            details=f"Updated {len(new_config)} parameters"
        )
        
        return result
    
    except Exception as e:
        SecurityAuditor.log_admin_action(
            action="config_update",
            user_ip=request.client.host,
            success=False,
            details=str(e)
        )
        raise
```

### Rate Limiting Implementation

```python
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple

class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
        self.cleanup_interval = 300  # Clean up every 5 minutes
    
    async def check_rate_limit(self, identifier: str, limit: int, window: int) -> bool:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: Client identifier (IP, user ID, etc.)
            limit: Maximum requests allowed
            window: Time window in seconds
        
        Returns:
            True if request is allowed, False if rate limited
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=window)
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]
        
        # Check if under limit
        if len(self.requests[identifier]) < limit:
            self.requests[identifier].append(now)
            return True
        
        return False
    
    async def cleanup_old_requests(self):
        """Periodic cleanup of old request records."""
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        for identifier in list(self.requests.keys()):
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if req_time > cutoff_time
            ]
            
            if not self.requests[identifier]:
                del self.requests[identifier]

# Global rate limiter instance
rate_limiter = RateLimiter()

# Middleware integration
async def check_rate_limit(request: Request):
    """Rate limiting middleware."""
    client_ip = request.client.host
    
    # Different limits for different endpoints
    if request.url.path.startswith("/ai/"):
        allowed = await rate_limiter.check_rate_limit(client_ip, 10, 60)
    elif request.url.path.startswith("/admin/"):
        allowed = await rate_limiter.check_rate_limit(client_ip, 50, 60)
    else:
        allowed = await rate_limiter.check_rate_limit(client_ip, 100, 60)
    
    if not allowed:
        SecurityAuditor.log_suspicious_activity(
            activity="rate_limit_exceeded",
            ip=client_ip,
            details=f"Endpoint: {request.url.path}"
        )
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
```

## Error Handling and Security

### Secure Error Responses

```python
from fastapi import HTTPException
import traceback

class SecurityError(Exception):
    """Custom exception for security-related errors."""
    pass

@app.exception_handler(SecurityError)
async def security_error_handler(request: Request, exc: SecurityError):
    """Handle security errors without exposing sensitive information."""
    SecurityAuditor.log_suspicious_activity(
        activity="security_error",
        ip=request.client.host,
        details=str(exc)
    )
    
    # Return generic error message to prevent information leakage
    return JSONResponse(
        status_code=403,
        content={
            "detail": "Access denied",
            "error_code": "SECURITY_ERROR",
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions securely."""
    # Log full error details internally
    logger.error(f"Unhandled exception: {traceback.format_exc()}")
    
    # Return generic error response to client
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "timestamp": datetime.now().isoformat()
        }
    )
```

## Production Deployment Security

### HTTPS Configuration

```bash
# Use proper TLS certificates in production
# Let's Encrypt with certbot
certbot certonly --webroot -w /var/www/certbot -d api.yourdomain.com

# Nginx SSL configuration
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Environment Security

```dockerfile
# Dockerfile security best practices
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r rlcf && useradd -r -g rlcf rlcf

# Set secure file permissions
COPY --chown=rlcf:rlcf . /app
WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Switch to non-root user
USER rlcf

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "rlcf_framework.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

**Security Summary:**
- API key authentication for admin operations
- Input validation and sanitization
- SQL injection prevention via ORM
- Safe mathematical expression evaluation
- Comprehensive audit logging
- Rate limiting and DDoS protection
- Secure error handling
- Production-ready HTTPS configuration

**Next Steps:**
- [API Endpoints](endpoints.md) - Complete API reference
- [Data Schemas](schemas.md) - Request/response schemas
- [Quick Start Guide](../guides/quick-start.md) - Getting started with authentication
