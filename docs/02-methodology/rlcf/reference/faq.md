# Frequently Asked Questions (FAQ)

## General Framework Questions

### What is RLCF and how does it differ from RLHF?

**RLCF (Reinforcement Learning from Community Feedback)** is a novel AI alignment methodology specifically designed for Artificial Legal Intelligence (ALI) systems. Unlike traditional RLHF, RLCF addresses the unique epistemological challenges of the legal domain:

**Key Differences:**

- **Dynamic Authority**: Expertise evolves based on demonstrated competence rather than static credentials
- **Uncertainty Preservation**: Disagreement among experts is maintained as valuable information
- **Constitutional Governance**: Algorithmic implementation of legal principles ensures ethical operation
- **Six-Dimensional Bias Detection**: Comprehensive bias analysis beyond traditional demographic factors

**Mathematical Foundation:**

- Authority scoring: A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)
- Disagreement quantification: δ = -(1/log|P|) Σ ρ(p)log ρ(p)
- Bias analysis: B_total = √(Σ b_i²) across 6 dimensions

### Who should use the RLCF framework?

**Primary Users:**

- **Academic Researchers**: Studying AI alignment, legal AI, expert validation methodologies
- **Legal AI Developers**: Building systems requiring expert validation and bias detection
- **Legal Professionals**: Participating in AI evaluation and providing domain expertise
- **AI Safety Researchers**: Investigating constitutional AI and uncertainty preservation

**Use Cases:**

- Legal AI system evaluation and training
- Expert validation methodology research
- Bias detection and mitigation studies
- Constitutional AI implementation
- Cross-domain expert validation systems

### What are the four constitutional principles of RLCF?

1. **Dynamic Authority**: Authority earned through demonstrated competence
2. **Preserved Uncertainty**: Disagreement as information, not noise
3. **Transparent Process**: All validation steps auditable and reproducible
4. **Universal Expertise**: Domain boundaries are emergent, not prescribed

## Technical Questions

### What are the system requirements?

**Minimum Requirements:**

- Python 3.8 or higher
- 4GB RAM
- 10GB disk space
- SQLite support (included with Python)

**Recommended for Production:**

- Python 3.11+
- 8GB+ RAM
- 50GB+ disk space
- PostgreSQL or MySQL database
- Redis for caching
- Load balancer for high availability

**Supported Operating Systems:**

- Linux (Ubuntu 20.04+, CentOS 8+)
- macOS (10.15+)
- Windows 10+

### How do I configure authority weights for my research?

Authority weights control the relative importance of different expertise components:

```yaml
# model_config.yaml
authority_weights:
  baseline_credentials: 0.3  # α - Education, experience, role
  track_record: 0.5          # β - Historical performance
  recent_performance: 0.2    # γ - Current evaluation quality
```

**Research Scenarios:**

- **Credential-heavy**: α=0.6, β=0.3, γ=0.1 (traditional academic emphasis)
- **Performance-only**: α=0.0, β=0.7, γ=0.3 (pure meritocracy)
- **Balanced**: α=0.3, β=0.5, γ=0.2 (default RLCF configuration)

**Mathematical Constraint:** α + β + γ = 1.0

### How does the disagreement threshold work?

The disagreement threshold (τ) determines when to preserve uncertainty vs. generate consensus:

**Default:** τ = 0.4

- **δ ≤ 0.4**: Generate consensus output
- **δ > 0.4**: Generate uncertainty-preserving output with alternative positions
- **δ > 0.6**: Trigger structured discussion phase

**Research Applications:**

- **High uncertainty preservation**: τ = 0.2 (preserve more disagreement)
- **Consensus-focused**: τ = 0.6 (force consensus more often)

### What task types are supported?

**Core Legal Tasks:**

1. **QA**: Legal question answering
2. **STATUTORY_RULE_QA**: Statutory interpretation
3. **CLASSIFICATION**: Document categorization
4. **PREDICTION**: Legal outcome prediction
5. **SUMMARIZATION**: Legal document summarization
6. **NLI**: Natural language inference
7. **NER**: Named entity recognition
8. **DRAFTING**: Legal document drafting
9. **RISK_SPOTTING**: Compliance risk identification
10. **DOCTRINE_APPLICATION**: Legal principle application

**Adding Custom Tasks:**
Tasks are configured via `task_config.yaml` with dynamic schemas:

```yaml
CUSTOM_TASK:
  input_data:
    field1: str
    field2: List[str]
  ground_truth_keys:
    - expected_output
  feedback_data:
    validated_result: str
    reasoning: str
```

## Academic Research Questions

### How do I ensure reproducible experiments?

**Configuration Management:**

```bash
# Version control configurations
git add model_config.yaml task_config.yaml
git commit -m "Experiment A: High performance weight configuration"
git tag -a "exp_condition_A" -m "Authority weights: 0.2/0.3/0.5"
```

**Data Export:**

```bash
# Export complete dataset for analysis
curl "http://localhost:8000/export/dataset?format=scientific&experiment_id=study_2024" > data.json
```

**Documentation:**

- Document all parameter changes
- Include configuration files in publication supplements
- Share anonymized datasets when possible
- Provide statistical analysis code

### What sample sizes are recommended?

**Minimum Sample Sizes:**

- **Pilot studies**: 15-30 experts per condition
- **Full validation**: 100+ experts for statistical power
- **Cross-validation**: Multiple independent panels

**Power Analysis:**

```python
from statsmodels.stats.power import ttest_power

# Calculate required sample size for effect detection
effect_size = 0.5  # Medium effect size
alpha = 0.05       # Type I error rate
power = 0.8        # Statistical power

required_n = ttest_power(effect_size, power, alpha)
print(f"Required sample size per condition: {required_n}")
```

### How do I handle ethics?

**Human Subjects Considerations:**

- Informed consent with clear data usage explanation
- Privacy protection for expert evaluations
- Right to withdraw and data deletion

**Ethical Guidelines:**

- Fair compensation for expert time
- Academic credit where appropriate
- Data anonymization and aggregation
- Transparent research purposes

### How do I analyze bias in my results?

**Six-Dimensional Bias Analysis:**

```python
# Export bias reports
bias_data = requests.get("http://localhost:8000/bias/summary").json()

# Analyze bias correlations
bias_types = ['demographic', 'professional', 'temporal', 
              'geographic', 'confirmation', 'anchoring']

for bias_type in bias_types:
    correlation = stats.pearsonr(
        data[f'{bias_type}_bias'], 
        data['authority_scores']
    )
    print(f"{bias_type}: r={correlation[0]:.3f}, p={correlation[1]:.3f}")
```

**Interpretation:**

- **Total bias < 0.5**: Low bias level
- **Total bias 0.5-1.0**: Medium bias level
- **Total bias > 1.0**: High bias level

## Technical Issues

### The server won't start. What should I check?

**Common Issues:**

1. **Port already in use:**

```bash
# Check what's using port 8000
lsof -i :8000

# Use different port
uvicorn rlcf_framework.main:app --port 8001
```

2. **Missing dependencies:**

```bash
# Reinstall dependencies
pip install -r requirements.txt

# Check Python version
python --version  # Should be 3.8+
```

3. **Database issues:**

```bash
# Check database file permissions
ls -la rlcf.db

# Reset database (WARNING: loses data)
rm rlcf.db
uvicorn rlcf_framework.main:app --reload
```

4. **Configuration errors:**

```bash
# Validate configuration
python -c "from rlcf_framework.config import load_model_config; print(load_model_config())"
```

### API calls are failing. How do I debug?

**Check Request Format:**

```bash
# Ensure proper headers
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"username": "test_user"}'
```

**Enable Debug Logging:**

```python
import logging
logging.getLogger("rlcf_framework").setLevel(logging.DEBUG)
```

**Common HTTP Errors:**

- **400 Bad Request**: Check JSON syntax and required fields
- **403 Forbidden**: Admin endpoints require API key
- **422 Unprocessable Entity**: Pydantic validation error
- **500 Internal Server Error**: Check server logs

### How do I improve performance?

**Database Optimization:**

```sql
-- Add indexes for common queries
CREATE INDEX idx_feedback_task_user ON feedback(response_id, user_id);
CREATE INDEX idx_tasks_type_status ON legal_tasks(task_type, status);
```

**Async Optimization:**

```python
# Use async context managers
async with SessionLocal() as session:
    # Batch operations
    results = await session.execute(select(User).options(selectinload(User.credentials)))
```

**Caching:**

```python
# Enable Redis caching
REDIS_URL = "redis://localhost:6379"
cache = redis.Redis.from_url(REDIS_URL)
```

**Connection Pooling:**

```python
# Increase connection pool size
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10
)
```

## Configuration Questions

### How do I add new credential types?

Add to `model_config.yaml`:

```yaml
baseline_credentials:
  types:
    NEW_CREDENTIAL_TYPE:
      weight: 0.2
      scoring_function:
        type: map  # or "formula"
        values:
          Level1: 1.0
          Level2: 1.5
          Level3: 2.0
        default: 0.0
```

**Formula-based scoring:**

```yaml
YEARS_EXPERIENCE:
  weight: 0.3
  scoring_function:
    type: formula
    expression: "0.5 + 0.2 * sqrt(value)"
    default: 0.0
```

### How do I update configuration in production?

**Safe Configuration Updates:**

```bash
# 1. Backup current configuration
cp model_config.yaml model_config.backup.yaml

# 2. Test configuration locally
python -c "from rlcf_framework.config import ModelConfig; ModelConfig(**yaml.safe_load(open('new_config.yaml')))"

# 3. Update via API with admin key
curl -X PUT "http://production-server/config/model" \
  -H "X-API-KEY: $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d @new_config.json

# 4. Verify update
curl "http://production-server/config/model"
```

**Constitutional Validation:**
The system automatically validates changes against constitutional principles:

- Authority weights must sum to 1.0
- No single component can exceed 60% (preserves democratic oversight)
- Disagreement threshold cannot be below 0.1 (preserves dialectical nature)

### How do I create custom task handlers?

1. **Define Task Schema:**

```yaml
# task_config.yaml
MY_CUSTOM_TASK:
  input_data:
    document: str
    analysis_type: str
  ground_truth_keys:
    - expected_analysis
  feedback_data:
    validated_analysis: str
    quality_rating: int
    reasoning: str
```

2. **Implement Handler:**

```python
# task_handlers/my_custom_handler.py
from .base import BaseTaskHandler

class MyCustomTaskHandler(BaseTaskHandler):
    async def aggregate_feedback(self) -> Dict[str, Any]:
        # Custom aggregation logic
        pass
  
    def calculate_consistency(self, feedback: Feedback, result: Dict) -> float:
        # Custom consistency calculation
        pass
```

3. **Register Handler:**

```python
# task_handlers/__init__.py
from .my_custom_handler import MyCustomTaskHandler

TASK_HANDLERS = {
    "MY_CUSTOM_TASK": MyCustomTaskHandler,
    # ... other handlers
}
```

## Deployment Questions

### How do I deploy RLCF in production?

**Docker Deployment:**

```dockerfile
FROM python:3.11-slim

# Security: non-root user
RUN groupadd -r rlcf && useradd -r -g rlcf rlcf

COPY --chown=rlcf:rlcf . /app
WORKDIR /app

RUN pip install -r requirements.txt

USER rlcf
EXPOSE 8000

CMD ["uvicorn", "rlcf_framework.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Environment Variables:**

```bash
export DATABASE_URL="postgresql://user:pass@localhost/rlcf"
export ADMIN_API_KEY="your-secure-key"
export REDIS_URL="redis://localhost:6379"
export LOG_LEVEL="INFO"
```

**Nginx Configuration:**

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
  
    ssl_certificate /etc/ssl/certs/api.yourdomain.com.crt;
    ssl_certificate_key /etc/ssl/private/api.yourdomain.com.key;
  
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### How do I scale RLCF for high traffic?

**Horizontal Scaling:**

```yaml
# docker-compose.yml
version: '3.8'
services:
  rlcf-api-1:
    image: rlcf:latest
    ports:
      - "8001:8000"
  
  rlcf-api-2:
    image: rlcf:latest
    ports:
      - "8002:8000"
  
  load-balancer:
    image: nginx
    ports:
      - "80:80"
    depends_on:
      - rlcf-api-1
      - rlcf-api-2
```

**Database Scaling:**

- Use PostgreSQL with read replicas
- Implement connection pooling
- Add Redis for session storage and caching

**Monitoring:**

```python
# Add Prometheus metrics
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter('rlcf_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram('rlcf_request_duration_seconds', 'Request latency')
```

## Troubleshooting

### Authority scores seem incorrect

**Diagnostic Steps:**

1. **Check Configuration:**

```bash
curl "http://localhost:8000/config/model" | jq '.authority_weights'
```

2. **Verify Calculations:**

```python
# Manual calculation
baseline = 1.2  # From credentials
track_record = 0.8  # Historical performance
recent = 0.9  # Current performance

authority = 0.3 * baseline + 0.5 * track_record + 0.2 * recent
print(f"Expected authority: {authority}")
```

3. **Check User Data:**

```bash
curl "http://localhost:8000/users/1" | jq '.authority_score, .baseline_credential_score, .track_record_score'
```

### Disagreement scores don't match expectations

**Common Issues:**

- Insufficient feedback diversity
- Authority weighting skewing results
- Threshold configuration

**Debug Shannon Entropy:**

```python
import numpy as np

def calculate_disagreement_manual(positions):
    """Manual disagreement calculation for verification."""
    total_weight = sum(positions.values())
    probabilities = [w/total_weight for w in positions.values()]
  
    entropy = -sum(p * np.log(p) for p in probabilities if p > 0)
    normalized_entropy = entropy / np.log(len(probabilities))
  
    return normalized_entropy

# Example
positions = {"position_a": 0.7, "position_b": 0.3}
disagreement = calculate_disagreement_manual(positions)
print(f"Manual disagreement: {disagreement}")
```

### Getting help and support

**Community Resources:**

- GitHub Issues: Bug reports and feature requests
- Documentation: Comprehensive guides and examples
- Academic Papers: Theoretical foundation and validation studies

**Contribution Guidelines:**

- Follow [Contributing Guidelines](../development/contributing.md)
- Include mathematical validation for algorithm changes
- Provide academic references for theoretical contributions

**Professional Support:**

- Academic collaboration opportunities
- Custom implementation consulting
- Training and workshops for research teams

---

**Still Have Questions?**

Check the complete documentation:

- [Quick Start Guide](../guides/quick-start.md) - Get started quickly
- [Academic Research Guide](../guides/academic-research.md) - Research methodology
- [API Reference](../api/endpoints.md) - Complete API documentation
- [System Architecture](../technical/architecture.md) - Technical details
