# Troubleshooting Guide

This guide provides systematic solutions for common issues encountered when using the RLCF framework. Solutions are organized by category with step-by-step diagnostic procedures.

## Installation Issues

### Python Version Compatibility

**Problem**: RLCF requires Python 3.8+ but system has older version.

**Symptoms**:
```bash
$ python --version
Python 3.7.9

$ pip install -r requirements.txt
ERROR: Package requires Python >=3.8
```

**Solution**:
```bash
# Option 1: Use pyenv to install Python 3.11
curl https://pyenv.run | bash
pyenv install 3.11.5
pyenv local 3.11.5

# Option 2: Use conda
conda create -n rlcf python=3.11
conda activate rlcf

# Option 3: System package manager (Ubuntu)
sudo apt update
sudo apt install python3.11 python3.11-venv
python3.11 -m venv venv
source venv/bin/activate
```

### Dependency Installation Failures

**Problem**: Package installation fails with compilation errors.

**Common Error**:
```
Building wheel for cryptography failed
Failed building wheel for sqlalchemy
```

**Solution**:
```bash
# Ubuntu/Debian: Install build dependencies
sudo apt update
sudo apt install build-essential python3-dev libffi-dev libssl-dev

# macOS: Install Xcode command line tools
xcode-select --install

# Alternative: Use pre-compiled wheels
pip install --only-binary=all -r requirements.txt

# If still failing, update pip and setuptools
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Virtual Environment Issues

**Problem**: Virtual environment not working correctly.

**Symptoms**:
- Commands not found after activation
- Wrong Python version in venv
- Package installations not isolated

**Solution**:
```bash
# Remove corrupted virtual environment
rm -rf venv

# Create new virtual environment
python3 -m venv venv

# Activate properly
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Verify activation
which python              # Should point to venv/bin/python
python --version          # Should be correct version

# Install dependencies
pip install -r requirements.txt
```

## Server Startup Issues

### Port Already in Use

**Problem**: Cannot start server on port 8000.

**Error Message**:
```
OSError: [Errno 48] Address already in use
```

**Diagnostic**:
```bash
# Check what's using port 8000
lsof -i :8000
netstat -tulnp | grep :8000
```

**Solutions**:
```bash
# Option 1: Kill process using port 8000
sudo kill -9 $(lsof -t -i:8000)

# Option 2: Use different port
uvicorn rlcf_framework.main:app --port 8001

# Option 3: Set port via environment
export PORT=8001
uvicorn rlcf_framework.main:app --host 0.0.0.0 --port $PORT
```

### Module Import Errors

**Problem**: Python cannot find RLCF modules.

**Error Message**:
```
ModuleNotFoundError: No module named 'rlcf_framework'
```

**Diagnostic**:
```bash
# Check current directory
pwd
ls -la

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Check if package is installed
pip list | grep rlcf
```

**Solutions**:
```bash
# Option 1: Run from project root directory
cd /path/to/RLCF
uvicorn rlcf_framework.main:app

# Option 2: Install package in development mode
pip install -e .

# Option 3: Add to Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/RLCF"
```

### Configuration File Errors

**Problem**: Invalid configuration causing startup failure.

**Error Message**:
```
ValidationError: authority_weights must sum to 1.0
yaml.scanner.ScannerError: found unexpected ':'
```

**Diagnostic**:
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('rlcf_framework/model_config.yaml'))"

# Validate configuration model
python -c "from rlcf_framework.config import load_model_config; load_model_config()"
```

**Solutions**:
```bash
# Check YAML syntax
yamllint rlcf_framework/model_config.yaml

# Reset to default configuration
git checkout rlcf_framework/model_config.yaml
git checkout rlcf_framework/task_config.yaml

# Validate authority weights sum to 1.0
python -c "
import yaml
config = yaml.safe_load(open('rlcf_framework/model_config.yaml'))
weights = config['authority_weights']
total = sum(weights.values())
print(f'Authority weights sum: {total}')
assert abs(total - 1.0) < 0.001, 'Weights must sum to 1.0'
"
```

## Database Issues

### Database File Permissions

**Problem**: Cannot access SQLite database file.

**Error Message**:
```
sqlite3.OperationalError: attempt to write a readonly database
PermissionError: [Errno 13] Permission denied: 'rlcf.db'
```

**Diagnostic**:
```bash
# Check file permissions
ls -la rlcf.db

# Check directory permissions
ls -ld .

# Check file ownership
stat rlcf.db
```

**Solutions**:
```bash
# Fix file permissions
chmod 664 rlcf.db

# Fix directory permissions
chmod 755 .

# Change ownership (if needed)
sudo chown $USER:$USER rlcf.db

# Remove and recreate database
rm rlcf.db
uvicorn rlcf_framework.main:app --reload
```

### Database Corruption

**Problem**: SQLite database is corrupted.

**Symptoms**:
- Random query failures
- Inconsistent data
- Database integrity check failures

**Diagnostic**:
```bash
# Check database integrity
sqlite3 rlcf.db "PRAGMA integrity_check;"

# Check for corruption patterns
sqlite3 rlcf.db ".schema" 2>&1 | grep -i error
```

**Solutions**:
```bash
# Option 1: Repair database
sqlite3 rlcf.db "
PRAGMA integrity_check;
.backup backup.db
.exit
"
mv rlcf.db rlcf_corrupted.db
mv backup.db rlcf.db

# Option 2: Export and reimport data
sqlite3 rlcf.db ".dump" > backup.sql
rm rlcf.db
sqlite3 rlcf.db ".read backup.sql"

# Option 3: Start fresh (WARNING: loses all data)
rm rlcf.db
uvicorn rlcf_framework.main:app --reload
```

### Schema Migration Errors

**Problem**: Database schema mismatch after updates.

**Error Message**:
```
sqlalchemy.exc.OperationalError: no such column: users.baseline_credential_score
```

**Solutions**:
```bash
# Check current schema
sqlite3 rlcf.db ".schema users"

# Apply migrations manually
sqlite3 rlcf.db "ALTER TABLE users ADD COLUMN baseline_credential_score REAL DEFAULT 0.0;"

# Or recreate database with new schema
mv rlcf.db rlcf_old.db
uvicorn rlcf_framework.main:app --reload

# Migrate data if needed
python migrate_data.py
```

## API Issues

### Authentication Failures

**Problem**: Admin endpoints returning 403 Forbidden.

**Error Message**:
```json
{"detail": "Could not validate credentials"}
```

**Diagnostic**:
```bash
# Check if API key is set
echo $ADMIN_API_KEY

# Test authentication
curl -H "X-API-KEY: $ADMIN_API_KEY" http://localhost:8000/config/model
```

**Solutions**:
```bash
# Set API key
export ADMIN_API_KEY="your-secret-key"

# Verify key in request
curl -v -H "X-API-KEY: your-secret-key" http://localhost:8000/config/model

# Check server logs for authentication attempts
tail -f rlcf_detailed.log | grep -i auth
```

### JSON Validation Errors

**Problem**: API requests failing with validation errors.

**Error Message**:
```json
{
  "detail": [
    {
      "loc": ["authority_weights"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Diagnostic**:
```bash
# Validate JSON syntax
echo '{"test": "value"}' | jq .

# Check request content type
curl -v -H "Content-Type: application/json" -d '{"test": "value"}' http://localhost:8000/users/
```

**Solutions**:
```bash
# Ensure proper headers
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "authority_score": 0.5,
    "track_record_score": 0.5,
    "baseline_credential_score": 0.0
  }'

# Use proper field names and types
curl -X PUT "http://localhost:8000/config/model" \
  -H "X-API-KEY: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "authority_weights": {
      "baseline_credentials": 0.3,
      "track_record": 0.5,
      "recent_performance": 0.2
    }
  }'
```

### Rate Limiting Issues

**Problem**: Requests being rate limited.

**Error Message**:
```json
{"detail": "Rate limit exceeded. Please try again later."}
```

**Solutions**:
```bash
# Wait before retrying requests
sleep 60

# Use exponential backoff
for i in {1..5}; do
  if curl -f http://localhost:8000/tasks/all; then
    break
  fi
  sleep $((2**i))
done

# Reduce request frequency
# Space out requests by at least 1 second
```

## Performance Issues

### Slow Database Queries

**Problem**: API responses are slow due to database performance.

**Diagnostic**:
```sql
-- Enable query logging
sqlite3 rlcf.db "PRAGMA compile_options;" | grep -i debug

-- Check slow queries
sqlite3 rlcf.db "EXPLAIN QUERY PLAN SELECT * FROM feedback JOIN users ON feedback.user_id = users.id;"
```

**Solutions**:
```sql
-- Add missing indexes
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_response_id ON feedback(response_id);
CREATE INDEX IF NOT EXISTS idx_legal_tasks_status ON legal_tasks(status);
CREATE INDEX IF NOT EXISTS idx_legal_tasks_task_type ON legal_tasks(task_type);

-- Optimize queries with LIMIT
SELECT * FROM legal_tasks ORDER BY created_at DESC LIMIT 50;

-- Use covering indexes
CREATE INDEX idx_tasks_status_created ON legal_tasks(status, created_at);
```

### Memory Usage Issues

**Problem**: High memory consumption during processing.

**Diagnostic**:
```bash
# Monitor memory usage
top -p $(pgrep -f "uvicorn.*rlcf")
htop

# Check Python memory usage
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

**Solutions**:
```python
# Use pagination for large datasets
@app.get("/tasks/all")
async def get_all_tasks(
    limit: int = Query(50, le=1000),  # Limit maximum results
    offset: int = Query(0, ge=0)
):
    query = select(LegalTask).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()

# Use streaming for large exports
@app.get("/export/tasks")
async def export_tasks():
    def generate():
        # Process data in chunks
        for chunk in get_data_chunks():
            yield json.dumps(chunk) + '\n'
    
    return StreamingResponse(generate(), media_type="application/json")

# Limit concurrent operations
semaphore = asyncio.Semaphore(10)  # Max 10 concurrent operations

async def process_with_limit():
    async with semaphore:
        # Process data
        pass
```

### Connection Pool Exhaustion

**Problem**: Database connection pool exhausted.

**Error Message**:
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 exceeded
```

**Solutions**:
```python
# Increase pool size
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,        # Increase from default 5
    max_overflow=30,     # Allow temporary connections
    pool_timeout=30,     # Wait time for connection
    pool_recycle=3600,   # Recycle connections after 1 hour
)

# Use proper session management
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()  # Ensure cleanup

# Check for session leaks
import gc
print(f"Active sessions: {len([obj for obj in gc.get_objects() if isinstance(obj, AsyncSession)])}")
```

## Authority Calculation Issues

### Incorrect Authority Scores

**Problem**: Authority scores don't match expected calculations.

**Diagnostic Process**:

1. **Verify Configuration**:
```bash
# Check authority weights
curl "http://localhost:8000/config/model" | jq '.authority_weights'

# Expected output:
{
  "baseline_credentials": 0.3,
  "track_record": 0.5,
  "recent_performance": 0.2
}
```

2. **Manual Calculation**:
```python
# Calculate expected authority score
baseline = 1.2  # User's baseline credential score
track_record = 0.8  # User's track record score
recent_performance = 0.9  # Recent performance input

# Formula: A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)
expected_authority = (0.3 * baseline + 
                     0.5 * track_record + 
                     0.2 * recent_performance)
print(f"Expected authority: {expected_authority}")
# Should be: 0.3*1.2 + 0.5*0.8 + 0.2*0.9 = 0.36 + 0.4 + 0.18 = 0.94
```

3. **Check User Data**:
```bash
curl "http://localhost:8000/users/1" | jq '{
  authority_score,
  baseline_credential_score,
  track_record_score
}'
```

**Common Solutions**:

1. **Credential Scoring Issues**:
```python
# Check credential scoring functions
def debug_credential_scoring(user_id):
    user = get_user(user_id)
    total_score = 0.0
    
    for credential in user.credentials:
        config = model_settings.baseline_credentials.types[credential.type]
        
        if config.scoring_function.type == "map":
            score = config.scoring_function.values.get(
                credential.value, 
                config.scoring_function.default
            )
        elif config.scoring_function.type == "formula":
            # Debug formula evaluation
            try:
                score = safe_eval(config.scoring_function.expression, 
                                {"value": float(credential.value)})
            except Exception as e:
                print(f"Formula error for {credential.type}: {e}")
                score = config.scoring_function.default
        
        weighted_score = config.weight * score
        total_score += weighted_score
        
        print(f"{credential.type}: {credential.value} -> {score} * {config.weight} = {weighted_score}")
    
    print(f"Total baseline score: {total_score}")
    return total_score
```

2. **Track Record Update Issues**:
```python
# Debug track record evolution
def debug_track_record_update(user_id, quality_score):
    user = get_user(user_id)
    current_track_record = user.track_record_score
    update_factor = model_settings.track_record.update_factor  # 1-λ = 0.05
    decay_factor = 1 - update_factor  # λ = 0.95
    
    # Formula: T_u(t) = λ·T_u(t-1) + (1-λ)·Q_u(t)
    new_track_record = (decay_factor * current_track_record + 
                       update_factor * quality_score)
    
    print(f"Track record update:")
    print(f"  Current: {current_track_record}")
    print(f"  Quality: {quality_score}")
    print(f"  Decay factor (λ): {decay_factor}")
    print(f"  Update factor (1-λ): {update_factor}")
    print(f"  New track record: {new_track_record}")
    
    return new_track_record
```

### Formula Evaluation Errors

**Problem**: Mathematical formulas in credential scoring fail.

**Error Message**:
```
asteval.AstEvalError: Expression evaluation failed
```

**Diagnostic**:
```python
# Test formula evaluation
from rlcf_framework.authority_module import create_safe_evaluator

evaluator = create_safe_evaluator()
evaluator.symtable["value"] = 5.0

try:
    result = evaluator.eval("0.5 + 0.2 * sqrt(value)")
    print(f"Formula result: {result}")
except Exception as e:
    print(f"Formula error: {e}")
```

**Solutions**:
```yaml
# Fix common formula syntax errors

# WRONG: Missing parentheses
expression: "sqrt value"

# CORRECT: Proper function call
expression: "sqrt(value)"

# WRONG: Undefined function
expression: "log10(value)"

# CORRECT: Use available functions
expression: "log(value)"

# WRONG: Division by zero
expression: "1 / value"

# CORRECT: Safe division
expression: "1 / max(value, 0.001)"
```

## Aggregation Issues

### Disagreement Calculation Errors

**Problem**: Disagreement scores don't match manual calculations.

**Diagnostic**:
```python
# Manual Shannon entropy calculation
def manual_disagreement_calculation(positions):
    import math
    
    # positions = {"position_a": 3.0, "position_b": 1.0}  # authority weights
    total_authority = sum(positions.values())
    probabilities = [weight / total_authority for weight in positions.values()]
    
    # Shannon entropy: H = -Σ p_i * log(p_i)
    entropy = -sum(p * math.log(p) for p in probabilities if p > 0)
    
    # Normalized entropy: δ = H / log(|P|)
    normalized_entropy = entropy / math.log(len(probabilities))
    
    print(f"Positions: {positions}")
    print(f"Total authority: {total_authority}")
    print(f"Probabilities: {probabilities}")
    print(f"Raw entropy: {entropy}")
    print(f"Normalized entropy: {normalized_entropy}")
    
    return normalized_entropy

# Test with known values
test_positions = {"correct": 3.0, "incorrect": 1.0}
manual_result = manual_disagreement_calculation(test_positions)
```

**Solutions**:
```python
# Fix position extraction issues
def debug_position_extraction(task_id):
    feedbacks = get_task_feedback(task_id)
    positions = {}
    
    for feedback in feedbacks:
        # Extract position based on task type
        if task.task_type == "QA":
            position = feedback.feedback_data.get("position", "unknown")
        elif task.task_type == "CLASSIFICATION":
            labels = feedback.feedback_data.get("validated_labels", [])
            position = tuple(sorted(labels))  # Convert to hashable type
        
        authority_weight = feedback.author.authority_score
        
        if position in positions:
            positions[position] += authority_weight
        else:
            positions[position] = authority_weight
    
    print(f"Extracted positions: {positions}")
    return positions
```

### Uncertainty Preservation Not Working

**Problem**: System always produces consensus output despite disagreement.

**Diagnostic**:
```python
# Check disagreement threshold
config = load_model_config()
threshold = config.thresholds.disagreement
print(f"Disagreement threshold: {threshold}")

# Check actual disagreement scores
task_disagreement = calculate_disagreement(positions)
print(f"Task disagreement: {task_disagreement}")
print(f"Above threshold: {task_disagreement > threshold}")
```

**Solutions**:
```yaml
# Adjust disagreement threshold if needed
thresholds:
  disagreement: 0.2  # Lower threshold = more uncertainty preservation

# Or check for single position dominance
positions_debug:
  single_position: 5.0  # All experts agree
  disagreement_score: 0.0  # No disagreement to preserve
```

## AI Service Issues

### OpenRouter API Failures

**Problem**: AI response generation fails.

**Error Messages**:
```json
{"error": "Invalid API key"}
{"error": "Rate limit exceeded"}
{"error": "Model not available"}
```

**Diagnostic**:
```bash
# Test API key directly
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
     -H "Content-Type: application/json" \
     https://openrouter.ai/api/v1/models

# Check available models
curl "http://localhost:8000/ai/models"
```

**Solutions**:
```bash
# Set correct API key
export OPENROUTER_API_KEY="sk-or-your-key-here"

# Use different model if current one fails
curl -X POST "http://localhost:8000/ai/generate_response" \
  -H "X-API-KEY: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "QA",
    "input_data": {"question": "test"},
    "model_config": {
      "name": "anthropic/claude-3-haiku",  # Faster, cheaper model
      "api_key": "'$OPENROUTER_API_KEY'",
      "temperature": 0.7
    }
  }'

# Handle rate limits with exponential backoff
for i in {1..5}; do
  if response=$(curl -s -X POST "http://localhost:8000/ai/generate_response" \
    -H "X-API-KEY: $ADMIN_API_KEY" \
    -H "Content-Type: application/json" \
    -d @request.json); then
    echo "$response"
    break
  else
    echo "Attempt $i failed, waiting..."
    sleep $((2**i))
  fi
done
```

## Logging and Debugging

### Enable Debug Logging

```python
# Add to main.py or as environment variable
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

# Enable specific module debugging
logging.getLogger("rlcf_framework.authority_module").setLevel(logging.DEBUG)
logging.getLogger("rlcf_framework.aggregation_engine").setLevel(logging.DEBUG)
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)  # SQL queries
```

### Common Log Patterns

```bash
# Monitor for errors
tail -f rlcf_detailed.log | grep -i error

# Watch authority calculations
tail -f debug.log | grep "authority_score"

# Monitor API requests
tail -f debug.log | grep -E "(POST|PUT|GET|DELETE)"

# Check database operations
tail -f debug.log | grep -i "sql"
```

### Performance Monitoring

```python
# Add timing decorators
import time
import functools

def timer(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        print(f"{func.__name__} took {duration:.3f} seconds")
        return result
    return wrapper

@timer
async def slow_function():
    # Function implementation
    pass
```

## Getting Additional Help

### Collecting Diagnostic Information

When reporting issues, include:

```bash
# System information
python --version
pip list | grep -E "(fastapi|sqlalchemy|pydantic)"
uname -a

# Configuration
curl -s "http://localhost:8000/config/model" | jq .
cat rlcf_framework/model_config.yaml

# Recent logs
tail -100 rlcf_detailed.log

# Database status
sqlite3 rlcf.db "PRAGMA integrity_check; SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM legal_tasks;"
```

### Community Resources

- **GitHub Issues**: https://github.com/[repo]/issues
- **Documentation**: Complete guides in `/docs` folder
- **Academic Papers**: Theoretical foundation references
- **Contribution Guidelines**: See [Contributing](../development/contributing.md)

### Professional Support

For academic institutions or research groups:
- Custom implementation consulting
- Training workshops
- Research collaboration opportunities
- Performance optimization services

---

**Remember**: Most issues can be resolved by:
1. Checking the configuration files
2. Verifying mathematical constraints
3. Reviewing log files for error details
4. Testing with minimal examples
5. Consulting the FAQ and documentation
