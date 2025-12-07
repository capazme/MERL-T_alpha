# Local Development Setup Guide

**Last Updated**: November 2025

---

## Overview

This guide provides comprehensive instructions for setting up a local MERL-T development environment. Whether you're contributing to the RLCF framework, implementing new retrieval agents, or improving the frontend, this guide will get you up and running.

**Estimated Setup Time**: 30-45 minutes (first-time setup)

---

## Prerequisites

Before starting, ensure you have the following software installed:

### Required Software

| Software | Minimum Version | Recommended Version | Purpose |
|----------|----------------|---------------------|----------|
| **Python** | 3.11 | 3.11+ | Backend runtime |
| **Node.js** | 18 | 20+ | Frontend tooling |
| **npm** | 9 | 10+ | Frontend package manager |
| **Git** | 2.30 | 2.40+ | Version control |
| **Docker** | 20 | 24+ | Database services (optional) |
| **Docker Compose** | 2.0 | 2.20+ | Multi-container orchestration |

### Optional Software

| Software | Version | Purpose |
|----------|---------|---------|
| **Memgraph** / **Neo4j** | Latest | Graph database (Phase 2+) |
| **Redis** | 7+ | Cache and rate limiting (Phase 2+) |
| **Qdrant** | 1.7+ | Vector database (Phase 3+) |

### Hardware Requirements

**Minimum**:
- 8 GB RAM
- 20 GB free disk space
- 2 CPU cores

**Recommended**:
- 16 GB RAM
- 50 GB free disk space (for databases and model files)
- 4+ CPU cores

---

## Installation Steps

### 1. Clone the Repository

```bash
# Clone the repository
git clone https://github.com/ALIS-Association/MERL-T.git
cd MERL-T
```

**Important**: Ensure you're on the correct branch:
- `main` - Stable releases
- `develop` - Latest development code
- `feature/*` - Specific feature branches

```bash
# Check current branch
git branch

# Switch to develop branch (for contributors)
git checkout develop
```

---

### 2. Backend Setup

#### 2.1 Create Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

**Note**: Your terminal prompt should now show `(venv)` prefix.

#### 2.2 Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install backend dependencies
pip install -r requirements.txt

# Install MERL-T in editable mode (for development)
pip install -e .
```

**Expected output**: ~120 packages installed (FastAPI, SQLAlchemy, LangGraph, etc.)

#### 2.3 Verify CLI Installation

```bash
# Verify rlcf-cli is installed
rlcf-cli --version

# Verify rlcf-admin is installed
rlcf-admin --version
```

If commands fail, ensure virtual environment is activated and `pip install -e .` completed successfully.

---

### 3. Environment Configuration

#### 3.1 Copy Environment Template

```bash
# Copy template to .env
cp .env.template .env
```

#### 3.2 Edit .env File

Open `.env` in your text editor and configure the following:

**Required Variables**:

```bash
# OpenRouter API Key (for LLM integration)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Admin API Key (for admin endpoints)
ADMIN_API_KEY=your_secure_admin_key_here
```

**Database URLs** (for production, optional for dev):

```bash
# PostgreSQL (default: SQLite for development)
DATABASE_URL=postgresql+asyncpg://merl_user:password@localhost:5432/merl_t

# Redis (Phase 2+)
REDIS_URL=redis://localhost:6379/0

# Qdrant (Phase 3+)
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Neo4j / Memgraph (Phase 2+)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

**RLCF Configuration** (optional, defaults in `model_config.yaml`):

```bash
# Authority score weights (α, β, γ)
AUTHORITY_ALPHA=0.4
AUTHORITY_BETA=0.3
AUTHORITY_GAMMA=0.3

# Thresholds
AUTHORITY_MIN_THRESHOLD=0.3
AUTHORITY_HIGH_THRESHOLD=0.7
```

**How to get API keys**:
- **OpenRouter**: Sign up at [openrouter.ai](https://openrouter.ai), create API key
- **Admin API Key**: Generate a secure random string (e.g., `openssl rand -hex 32`)

---

### 4. Database Setup

You have two options for database setup:

#### Option A: Docker Databases (Recommended for Development)

Start databases using Docker Compose:

```bash
# Start PostgreSQL only (development profile)
docker-compose -f docker-compose.dev.yml up -d postgres

# Start all databases (PostgreSQL, Redis, Qdrant, Memgraph)
docker-compose --profile phase2 --profile phase3 up -d
```

**Services started**:
- `postgres`: Port 5432 (PostgreSQL 16)
- `redis`: Port 6379 (Redis 7) - Phase 2+
- `qdrant`: Port 6333 (Qdrant 1.7) - Phase 3+
- `memgraph`: Port 7687 (Memgraph latest) - Phase 2+

**Verify databases are running**:

```bash
docker-compose ps
```

#### Option B: Native Databases (Advanced)

Install databases natively on your system:

**PostgreSQL**:
```bash
# macOS (Homebrew)
brew install postgresql@16
brew services start postgresql@16

# Ubuntu/Debian
sudo apt install postgresql-16
sudo systemctl start postgresql
```

**Redis** (Phase 2+):
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis
```

**Qdrant** (Phase 3+):
```bash
# Docker (recommended for Qdrant)
docker run -p 6333:6333 qdrant/qdrant
```

**Memgraph** (Phase 2+):
```bash
# Docker (recommended for Memgraph)
docker run -p 7687:7687 -p 7444:7444 memgraph/memgraph
```

---

### 5. Database Initialization

#### 5.1 Run Migrations

```bash
# Initialize database schema
rlcf-admin db migrate
```

**Expected output**: Tables created (users, legal_tasks, expert_feedback, etc.)

#### 5.2 Seed Test Data (Optional)

```bash
# Seed 5 users and 10 tasks for testing
rlcf-admin db seed --users 5 --tasks 10
```

**Expected output**: Demo data created with varying authority scores

---

### 6. Frontend Setup

#### 6.1 Install Node.js Dependencies

```bash
# Navigate to frontend directory
cd frontend/rlcf-web

# Install dependencies
npm install
```

**Expected output**: ~500+ packages installed (React 19, Vite, TanStack Query, etc.)

#### 6.2 Configure Frontend Environment

```bash
# Copy frontend environment template
cp .env.template .env
```

Edit `frontend/rlcf-web/.env`:

```bash
# Backend API URL
VITE_API_URL=http://localhost:8000

# API Key (if authentication enabled)
VITE_API_KEY=your_api_key_here
```

---

## Running the Application

### 1. Start Backend Server

#### Development Mode (Hot-Reload)

```bash
# From project root, with virtual environment activated
rlcf-admin server --reload
```

**Access**:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Logs**: Watch terminal for request logs, errors, and debug information

#### Production Mode (Multi-Worker)

```bash
# Production server with 4 workers
rlcf-admin server --host 0.0.0.0 --port 8080 --workers 4
```

**Note**: Hot-reload disabled in production mode

---

### 2. Start Frontend Server

In a **separate terminal**:

```bash
# Navigate to frontend directory
cd frontend/rlcf-web

# Start Vite dev server
npm run dev
```

**Access**: http://localhost:3000

**Hot-Reload**: Changes to React components automatically refresh in browser

---

### 3. Start Gradio Admin Interface (Optional)

In a **third terminal**:

```bash
# From project root, with virtual environment activated
python merlt/rlcf_framework/app_interface.py
```

**Access**: http://localhost:7860

**Features**:
- Task creation (YAML, CSV upload)
- AI response generation
- Aggregation visualization
- Bias analysis
- Configuration management

---

## Verification & Testing

### 1. Verify Backend API

```bash
# Health check
curl http://localhost:8000/health

# Expected: {"status":"healthy","version":"0.9.0"}

# List users
curl http://localhost:8000/users/

# Create test task
curl -X POST http://localhost:8000/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "QA",
    "input_data": {"question": "Test question"},
    "ground_truth_data": {"answer": "Test answer"}
  }'
```

### 2. Run Test Suite

```bash
# Run all RLCF tests
pytest tests/rlcf/ -v

# Run with coverage report
pytest tests/rlcf/ --cov=merlt/rlcf_framework --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

**Expected**: 200+ tests, 88-90% coverage

### 3. Test CLI Commands

```bash
# User commands
rlcf-cli users list
rlcf-cli tasks list --status OPEN

# Admin commands
rlcf-admin config show --type model
rlcf-admin db stats
```

---

## Common Issues & Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'backend'"

**Cause**: MERL-T not installed in editable mode

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install in editable mode
pip install -e .
```

---

### Issue: "sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file"

**Cause**: Database file permissions or path issue

**Solution**:
```bash
# Check database path in .env
cat .env | grep DATABASE_URL

# Ensure directory exists
mkdir -p data/

# Re-run migration
rlcf-admin db migrate
```

---

### Issue: "uvicorn: command not found"

**Cause**: FastAPI dependencies not installed

**Solution**:
```bash
# Reinstall requirements
pip install -r requirements.txt

# Or install uvicorn directly
pip install "uvicorn[standard]"
```

---

### Issue: "npm ERR! ENOENT: no such file or directory, open '.../package.json'"

**Cause**: Not in frontend directory

**Solution**:
```bash
# Navigate to frontend directory
cd frontend/rlcf-web

# Then run npm install
npm install
```

---

### Issue: "docker-compose: command not found"

**Cause**: Docker Compose not installed or old Docker version

**Solution**:
```bash
# Docker Compose v2 (included in Docker Desktop 20+)
docker compose version

# Use 'docker compose' instead of 'docker-compose'
docker compose up -d
```

---

### Issue: API returns 401 Unauthorized

**Cause**: Missing or invalid API key

**Solution**:
```bash
# Check .env file has ADMIN_API_KEY set
cat .env | grep ADMIN_API_KEY

# Include X-API-KEY header in requests
curl -H "X-API-KEY: your_admin_key" http://localhost:8000/config/model
```

---

### Issue: OpenRouter API errors

**Cause**: Invalid or missing OPENROUTER_API_KEY

**Solution**:
1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Generate API key
3. Add to `.env`:
```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxx
```
4. Restart backend server

---

### Issue: Slow database queries

**Cause**: Missing indexes or large dataset

**Solution**:
```bash
# Reset database and re-migrate
rlcf-admin db reset

# For production, use PostgreSQL instead of SQLite
# Edit .env:
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/merl_t
```

---

## Development Workflow

### Typical Development Session

1. **Start databases**:
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **Activate virtual environment**:
   ```bash
   source venv/bin/activate
   ```

3. **Start backend** (terminal 1):
   ```bash
   rlcf-admin server --reload
   ```

4. **Start frontend** (terminal 2):
   ```bash
   cd frontend/rlcf-web && npm run dev
   ```

5. **Make changes**, then:
   ```bash
   # Run tests
   pytest tests/rlcf/ -v

   # Check code formatting
   black merlt/rlcf_framework/
   isort merlt/rlcf_framework/
   ```

6. **Commit changes**:
   ```bash
   git add .
   git commit -m "feat(api): add new endpoint for X"
   ```

---

### Hot-Reload Behavior

**Backend** (FastAPI with `--reload`):
- Python code changes trigger automatic server restart
- **Does NOT reload**: `model_config.yaml`, `task_config.yaml` (use ConfigManager hot-reload)
- **Reloads**: `.py` files in `merlt/`

**Frontend** (Vite):
- React component changes trigger instant Hot Module Replacement (HMR)
- No full page reload needed
- State is preserved where possible

**Configuration** (YAML files):
- Changes detected via file watching (Python `watchdog` library)
- Automatic reload without server restart
- Backup created before applying changes

---

### Debugging Tips

**Backend Debugging**:
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint() (Python 3.7+)
breakpoint()

# Start server normally
rlcf-admin server --reload
```

**Frontend Debugging**:
- Open browser DevTools (F12)
- React DevTools extension recommended
- Check Console for errors
- Network tab for API calls

**Database Debugging**:
```bash
# SQLite (development)
sqlite3 data/merl_t.db
.tables
SELECT * FROM users;

# PostgreSQL (production)
psql -U merl_user -d merl_t
\dt  -- List tables
SELECT * FROM users;
```

---

## Next Steps

Now that your local environment is set up:

1. **Read the Contributing Guide**: [`CONTRIBUTING.md`](../../CONTRIBUTING.md)
2. **Explore the API**: http://localhost:8000/docs
3. **Run the Test Suite**: `pytest tests/rlcf/ -v`
4. **Read RLCF Documentation**: [`docs/02-methodology/rlcf/RLCF.md`](../02-methodology/rlcf/RLCF.md)
5. **Check Implementation Roadmap**: [`docs/IMPLEMENTATION_ROADMAP.md`](../IMPLEMENTATION_ROADMAP.md)

---

## Related Documentation

- **[Contributing Guide](../../CONTRIBUTING.md)** - Development workflow, coding standards, PR process
- **[README](../../README.md)** - Project overview and quick start
- **[Architecture](../03-architecture/)** - 5-layer system architecture
- **[RLCF Quick Start](../02-methodology/rlcf/guides/quick-start.md)** - RLCF framework usage guide
- **[Testing Strategy](../08-iteration/TESTING_STRATEGY.md)** - Testing procedures and coverage goals

---

## Getting Help

If you encounter issues not covered in this guide:

1. **Check existing issues**: [GitHub Issues](https://github.com/ALIS-Association/MERL-T/issues)
2. **Ask in Discussions**: [GitHub Discussions](https://github.com/ALIS-Association/MERL-T/discussions)
3. **Contact support**: support@alis.ai

---

**Document Version**: 1.0
**Last Updated**: November 2025
**Maintained By**: ALIS Technical Team
