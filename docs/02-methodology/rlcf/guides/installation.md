# Installation Guide

This comprehensive guide covers all installation scenarios for the RLCF framework, from development setup to production deployment.

## System Requirements

### Minimum Requirements
- **Python**: 3.8 or higher
- **RAM**: 4GB minimum
- **Storage**: 10GB free space
- **Operating System**: Linux, macOS, or Windows

### Recommended Requirements
- **Python**: 3.11+ (latest stable)
- **RAM**: 8GB or more
- **Storage**: 50GB+ for production use
- **Database**: PostgreSQL or MySQL for production
- **Cache**: Redis for improved performance

### Supported Platforms
- **Linux**: Ubuntu 20.04+, CentOS 8+, RHEL 8+
- **macOS**: 10.15 (Catalina) or later
- **Windows**: Windows 10/11 with WSL2 recommended

## Quick Installation

### Standard Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/RLCF.git
cd RLCF

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# 4. Install dependencies
pip install -r requirements.txt

# 5. Start the server
uvicorn rlcf_framework.main:app --reload

# 6. Verify installation
curl http://localhost:8000/docs
```

The API documentation should be available at `http://localhost:8000/docs`.

### Development Installation

For contributors and researchers who need development tools:

```bash
# Install development dependencies
pip install -r dev-requirements.txt

# Install pre-commit hooks
pre-commit install

# Run tests to verify installation
pytest tests/

# Check code quality
black --check .
ruff check .
```

## Detailed Installation Instructions

### Step 1: Python Environment Setup

#### Option A: System Python (Simplest)

```bash
# Check Python version
python --version
# Should be 3.8 or higher

# Install pip if missing
sudo apt install python3-pip  # Ubuntu/Debian
brew install python3          # macOS
```

#### Option B: pyenv (Recommended for Development)

```bash
# Install pyenv
curl https://pyenv.run | bash

# Add to shell profile
echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc

# Reload shell
source ~/.bashrc

# Install Python 3.11
pyenv install 3.11.5
pyenv local 3.11.5
```

#### Option C: Conda (Cross-platform)

```bash
# Create conda environment
conda create -n rlcf python=3.11
conda activate rlcf

# Verify environment
which python
python --version
```

### Step 2: Virtual Environment Setup

**Why Virtual Environments?**
- Isolate project dependencies
- Prevent conflicts with system packages
- Enable reproducible installations

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Verify activation
which python    # Should point to venv/bin/python
pip list        # Should show minimal packages
```

### Step 3: Repository Setup

```bash
# Clone repository
git clone https://github.com/your-org/RLCF.git
cd RLCF

# Check repository structure
ls -la
# Should see: rlcf_framework/, tests/, docs/, requirements.txt, etc.

# Optional: Switch to specific version
git checkout v1.0.0  # Use stable release
```

### Step 4: Dependency Installation

#### Core Dependencies

```bash
# Install main dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep -E "(fastapi|sqlalchemy|pydantic)"
```

#### Development Dependencies (Optional)

```bash
# For contributors and researchers
pip install -r dev-requirements.txt

# Verify development tools
black --version
ruff --version
pytest --version
```

#### Optional Dependencies

```bash
# For PostgreSQL support
pip install psycopg2-binary

# For Redis caching
pip install redis

# For enhanced AI features
pip install openai anthropic
```

### Step 5: Configuration Setup

#### Basic Configuration

```bash
# Create environment file (optional)
cp .env.example .env

# Edit configuration
nano .env
```

**.env file example:**
```bash
# Database
DATABASE_URL=sqlite:///./rlcf.db

# API Security
ADMIN_API_KEY=your-secure-api-key-here

# AI Services (optional)
OPENROUTER_API_KEY=your-openrouter-key

# Logging
LOG_LEVEL=INFO
```

#### Model Configuration

The framework includes default configurations that work out of the box:

```yaml
# rlcf_framework/model_config.yaml (default)
authority_weights:
  baseline_credentials: 0.3
  track_record: 0.5
  recent_performance: 0.2

track_record:
  update_factor: 0.05

thresholds:
  disagreement: 0.4
```

You can modify these settings for your research needs.

### Step 6: Database Setup

#### SQLite (Default - No Setup Required)

The framework automatically creates an SQLite database on first run:

```bash
# Start server (creates database automatically)
uvicorn rlcf_framework.main:app --reload

# Verify database creation
ls -la rlcf.db
```

#### PostgreSQL (Production Recommended)

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib  # Ubuntu
brew install postgresql                         # macOS

# Start PostgreSQL service
sudo systemctl start postgresql  # Ubuntu
brew services start postgresql   # macOS

# Create database and user
sudo -u postgres psql
CREATE DATABASE rlcf;
CREATE USER rlcf_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE rlcf TO rlcf_user;
\q

# Update configuration
export DATABASE_URL="postgresql://rlcf_user:secure_password@localhost/rlcf"
```

### Step 7: Verification

#### Start the Server

```bash
# Development server with auto-reload
uvicorn rlcf_framework.main:app --reload

# Production server
uvicorn rlcf_framework.main:app --host 0.0.0.0 --port 8000
```

#### Test Basic Functionality

```bash
# Test API health
curl http://localhost:8000/docs

# Create test user
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "authority_score": 0.5
  }'

# Create test task
curl -X POST "http://localhost:8000/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "QA",
    "input_data": {
      "context": "Legal context here",
      "question": "Test question?"
    }
  }'
```

#### Run Test Suite

```bash
# Run all tests
pytest tests/

# Run specific test categories
pytest tests/test_authority_module.py -v
pytest tests/test_aggregation_engine.py -v

# Run with coverage
pytest --cov=rlcf_framework tests/
```

## Platform-Specific Instructions

### Ubuntu/Debian Linux

```bash
# Update package list
sudo apt update

# Install system dependencies
sudo apt install -y python3 python3-pip python3-venv git curl build-essential

# Install database (optional)
sudo apt install -y postgresql postgresql-contrib redis-server

# Clone and setup
git clone https://github.com/your-org/RLCF.git
cd RLCF
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start services
sudo systemctl start postgresql redis-server

# Run RLCF
uvicorn rlcf_framework.main:app --reload
```

### CentOS/RHEL

```bash
# Install EPEL repository
sudo yum install -y epel-release

# Install dependencies
sudo yum install -y python3 python3-pip git gcc gcc-c++ make

# Install PostgreSQL (optional)
sudo yum install -y postgresql postgresql-server postgresql-contrib

# Setup PostgreSQL
sudo postgresql-setup initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Continue with standard installation
git clone https://github.com/your-org/RLCF.git
cd RLCF
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### macOS

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 git postgresql redis

# Start services
brew services start postgresql
brew services start redis

# Clone and setup
git clone https://github.com/your-org/RLCF.git
cd RLCF
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run RLCF
uvicorn rlcf_framework.main:app --reload
```

### Windows

#### Option A: WSL2 (Recommended)

```bash
# Install WSL2 and Ubuntu
wsl --install
wsl --set-default-version 2

# Inside WSL2, follow Ubuntu instructions
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl

# Continue with standard Linux installation
```

#### Option B: Native Windows

```powershell
# Install Python from python.org or Microsoft Store
# Install Git from git-scm.com

# Clone repository
git clone https://github.com/your-org/RLCF.git
cd RLCF

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run RLCF
uvicorn rlcf_framework.main:app --reload
```

## Docker Installation

### Quick Docker Setup

```bash
# Clone repository
git clone https://github.com/your-org/RLCF.git
cd RLCF

# Build Docker image
docker build -t rlcf:latest .

# Run container
docker run -p 8000:8000 rlcf:latest

# Access application
curl http://localhost:8000/docs
```

### Docker Compose (Recommended)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  rlcf-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://rlcf_user:password@db:5432/rlcf
      - REDIS_URL=redis://redis:6379
      - ADMIN_API_KEY=your-secure-key
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=rlcf
      - POSTGRES_USER=rlcf_user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f rlcf-api

# Stop services
docker-compose down
```

## Production Deployment

### Environment Preparation

```bash
# Create dedicated user
sudo useradd -m -s /bin/bash rlcf
sudo usermod -aG sudo rlcf

# Setup directories
sudo mkdir -p /opt/rlcf
sudo chown rlcf:rlcf /opt/rlcf

# Switch to rlcf user
sudo su - rlcf
cd /opt/rlcf
```

### Application Setup

```bash
# Clone and setup
git clone https://github.com/your-org/RLCF.git .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create production configuration
cp rlcf_framework/model_config.yaml model_config.prod.yaml
cp .env.example .env.prod

# Edit production settings
nano .env.prod
```

### Database Setup

```bash
# PostgreSQL production setup
sudo -u postgres createdb rlcf_prod
sudo -u postgres createuser --pwprompt rlcf_prod_user

# Apply proper permissions
sudo -u postgres psql
GRANT ALL PRIVILEGES ON DATABASE rlcf_prod TO rlcf_prod_user;
\q

# Update configuration
echo "DATABASE_URL=postgresql://rlcf_prod_user:password@localhost/rlcf_prod" >> .env.prod
```

### Systemd Service

Create `/etc/systemd/system/rlcf.service`:

```ini
[Unit]
Description=RLCF API Server
After=network.target postgresql.service

[Service]
Type=exec
User=rlcf
Group=rlcf
WorkingDirectory=/opt/rlcf
Environment=PATH=/opt/rlcf/venv/bin
EnvironmentFile=/opt/rlcf/.env.prod
ExecStart=/opt/rlcf/venv/bin/uvicorn rlcf_framework.main:app --host 0.0.0.0 --port 8000
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable rlcf
sudo systemctl start rlcf

# Check status
sudo systemctl status rlcf
journalctl -u rlcf -f
```

### Reverse Proxy (Nginx)

```bash
# Install Nginx
sudo apt install nginx

# Create configuration
sudo nano /etc/nginx/sites-available/rlcf
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/rlcf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL/TLS Setup

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Verify renewal
sudo certbot renew --dry-run
```

## Troubleshooting Installation

### Common Issues

#### Permission Errors
```bash
# Fix virtual environment permissions
sudo chown -R $USER:$USER venv/

# Fix database permissions
sudo chmod 664 rlcf.db
sudo chown $USER:$USER rlcf.db
```

#### Package Compilation Errors
```bash
# Install build dependencies
sudo apt install build-essential python3-dev libffi-dev libssl-dev

# Use pre-compiled wheels
pip install --only-binary=all -r requirements.txt
```

#### Port Conflicts
```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill process
sudo kill -9 $(lsof -t -i:8000)

# Use alternative port
uvicorn rlcf_framework.main:app --port 8001
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U rlcf_user -d rlcf

# Reset SQLite database
rm rlcf.db
uvicorn rlcf_framework.main:app --reload
```

### Getting Help

If you encounter issues:

1. **Check Logs**: Review `rlcf_detailed.log` for error messages
2. **Verify Configuration**: Ensure all configuration files are valid
3. **Test Dependencies**: Run `pip check` to verify package compatibility
4. **Consult Documentation**: See [Troubleshooting Guide](../reference/troubleshooting.md)
5. **Community Support**: Open an issue on GitHub

## Next Steps

After successful installation:

1. **Configure Authority Weights**: Customize for your research needs
2. **Import Users**: Add expert evaluators to the system
3. **Create Tasks**: Start with sample legal evaluation tasks
4. **Run Tests**: Verify system functionality with test data
5. **Monitor Performance**: Set up logging and monitoring

**Recommended Reading:**
- [Quick Start Guide](quick-start.md) - Get familiar with basic operations
- [Configuration Guide](configuration.md) - Customize the system
- [Academic Research Guide](academic-research.md) - Use RLCF for research
- [API Reference](../api/endpoints.md) - Complete API documentation

---

**Installation Complete!** You're now ready to start using the RLCF framework for legal AI evaluation and research.
