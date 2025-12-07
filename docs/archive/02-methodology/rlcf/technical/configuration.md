# Configuration System

The RLCF framework implements a dynamic, YAML-based configuration system that allows researchers to modify mathematical parameters, task schemas, and AI model settings without code changes. This enables rapid experimentation and academic research.

## Configuration Architecture

```
rlcf_framework/
├── model_config.yaml      # Mathematical parameters
├── task_config.yaml       # Task type definitions
├── config.py             # Configuration loading & validation
└── dependencies.py       # Configuration injection
```

## Model Configuration (`model_config.yaml`)

This file contains all mathematical parameters for the RLCF algorithm implementation, directly corresponding to the formulas in the theoretical framework.

### Authority Weights

**Mathematical Reference**: Section 2.1 - Dynamic Authority Scoring Model

```yaml
authority_weights:
  baseline_credentials: 0.3  # α parameter
  track_record: 0.5          # β parameter  
  recent_performance: 0.2    # γ parameter
```

**Formula Implementation**:
```
A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)
```

**Constraints**:
- All weights must be non-negative
- Sum must equal 1.0 (α + β + γ = 1)
- Validated at runtime via Pydantic

### Track Record Evolution

**Mathematical Reference**: Section 2.3 - Track Record Evolution Model

```yaml
track_record:
  update_factor: 0.05  # (1-λ) parameter
```

**Formula Implementation**:
```
T_u(t) = λ·T_u(t-1) + (1-λ)·Q_u(t)
where λ = 1 - update_factor = 0.95
```

**Rationale**: The 95% decay factor ensures historical stability while allowing adaptation to recent performance changes.

### Disagreement Thresholds

**Mathematical Reference**: Section 3.2 - Disagreement Quantification

```yaml
thresholds:
  disagreement: 0.4  # τ parameter
```

**Algorithm Behavior**:
- δ ≤ 0.4: Generate consensus output
- δ > 0.4: Generate uncertainty-preserving output with alternative positions
- δ > 0.6: Trigger structured discussion phase

### Baseline Credentials System

**Mathematical Reference**: Section 2.2 - Dynamic Baseline Credentials System

```yaml
baseline_credentials:
  types:
    ACADEMIC_DEGREE:
      weight: 0.3
      scoring_function:
        type: map
        values:
          Bachelor: 1.0
          LLM: 1.1
          JD: 1.2
          PhD: 1.5
        default: 0.0
    
    PROFESSIONAL_EXPERIENCE:
      weight: 0.4
      scoring_function:
        type: formula
        expression: "0.5 + 0.2 * sqrt(value)"
        default: 0.0
    
    PUBLICATION:
      weight: 0.2
      scoring_function:
        type: formula
        expression: "min(0.8 + 0.1 * value, 1.4)"
        default: 0.0
    
    INSTITUTIONAL_ROLE:
      weight: 0.1
      scoring_function:
        type: map
        values:
          Junior: 0.7
          Senior: 1.1
          Partner: 1.4
        default: 0.0
```

**Formula Implementation**:
```
B_u = Σ(w_i · f_i(c_{u,i}))
```

**Scoring Function Types**:

1. **Map Functions**: Discrete value mapping
   - Direct lookup from predefined values
   - Fallback to default for unknown values

2. **Formula Functions**: Mathematical expressions
   - Safe evaluation using `asteval` library
   - Supports mathematical functions: `sqrt`, `min`, `max`, `abs`, `round`, `pow`
   - 1-second timeout for safety

**Security Features**:
- No `eval()` or `exec()` - uses restricted `asteval`
- Whitelist of allowed mathematical functions
- Input sanitization and validation
- Timeout protection against infinite loops

### AI Model Configuration

```yaml
ai_models:
  - name: gpt-3.5-turbo-openrouter
    type: openrouter
    api_key_env: OPENROUTER_API_KEY
    route: openai/gpt-3.5-turbo
  
  - name: llama-2-7b-chat-local
    type: local
    endpoint: http://localhost:8000/v1/completions
  
  - name: mock-model
    type: local
    path: /path/to/local/model_weights
```

## Task Configuration (`task_config.yaml`)

Defines schemas for all supported legal task types, enabling dynamic task creation and validation.

### Task Type Structure

```yaml
task_types:
  TASK_NAME:
    input_data:
      field1: str
      field2: List[str]
    ground_truth_keys:
      - truth_field1
      - truth_field2
    feedback_data:
      validated_field: str
      position: Literal["option1", "option2"]
      reasoning: str
```

### Supported Task Types

#### Question Answering (QA)
```yaml
QA:
  input_data:
    context: str
    question: str
  ground_truth_keys:
    - answers
  feedback_data:
    validated_answer: str
    position: Literal["correct", "incorrect"]
    reasoning: str
```

#### Statutory Rule QA
```yaml
STATUTORY_RULE_QA:
  input_data:
    id: str
    question: str
    rule_id: str
    context_full: str
    context_count: int
    relevant_articles: str
    tags: str
    category: str
    metadata_full: str
  ground_truth_keys:
    - answer_text
  feedback_data:
    validated_answer: str
    confidence: Literal["high", "medium", "low"]
    position: Literal["correct", "partially_correct", "incorrect"]
    reasoning: str
    sources_verified: bool
```

#### Classification
```yaml
CLASSIFICATION:
  input_data:
    text: str
    unit: str
  ground_truth_keys:
    - labels
  feedback_data:
    validated_labels: List[str]
    reasoning: str
```

#### Legal Prediction
```yaml
PREDICTION:
  input_data:
    facts: str
  ground_truth_keys:
    - outcome
  feedback_data:
    chosen_outcome: Literal["violation", "no_violation"]
    reasoning: str
```

### Dynamic Schema Validation

The system automatically validates feedback against task-specific schemas:

```python
def validate_feedback_against_schema(feedback_data: dict, task_type: str) -> bool:
    """
    Validates feedback data against dynamically loaded task schema.
    
    Returns:
        bool: True if feedback conforms to expected schema
    """
    schema = task_settings.task_types[task_type].feedback_data
    return validate_against_schema(feedback_data, schema)
```

## Configuration Loading & Management

### Automatic Loading

Configuration is loaded automatically at startup and can be hot-reloaded:

```python
# config.py
def load_model_config() -> ModelConfig:
    """Loads and validates configuration with Pydantic models."""
    config_path = os.path.join(os.path.dirname(__file__), "model_config.yaml")
    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)
    return ModelConfig(**config_data)

# Global configuration instance - hot-reloadable
model_settings = load_model_config()
```

### Dependency Injection

Configuration is injected into API endpoints via FastAPI dependencies:

```python
# dependencies.py
def get_model_settings() -> ModelConfig:
    """Dependency that provides current model configuration."""
    return model_settings

def get_task_settings() -> TaskConfig:
    """Dependency that provides current task configuration."""
    return task_settings

# Usage in endpoints
@app.get("/some-endpoint")
async def endpoint(model_config: ModelConfig = Depends(get_model_settings)):
    # Use model_config.authority_weights, etc.
    pass
```

## Runtime Configuration Updates

### API Endpoints for Configuration Management

```python
@app.put("/config/model")
async def update_model_config(
    new_config: dict,
    api_key: str = Depends(get_api_key)
):
    """Update model configuration at runtime with validation."""
    try:
        validated_config = ModelConfig(**new_config)
        # Constitutional compliance check
        is_valid, reason = await validate_configuration_change(new_config)
        if not is_valid:
            raise HTTPException(status_code=400, detail=reason)
        
        # Write to file and reload global settings
        save_config_to_yaml(validated_config)
        global model_settings
        model_settings = validated_config
        return {"status": "success", "message": "Configuration updated"}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/config/tasks")  
async def update_task_config(
    new_config: dict,
    api_key: str = Depends(get_api_key)
):
    """Update task schema configuration dynamically."""
    validated_config = TaskConfig(**new_config)
    save_task_config_to_yaml(validated_config)
    return {"status": "success"}
```

### Constitutional Governance Integration

Configuration changes are validated against constitutional principles:

```python
async def validate_configuration_change(proposal: dict) -> Tuple[bool, str]:
    """Ensures configuration changes comply with constitutional principles."""
    framework = ConstitutionalFramework()
    
    # Check against core principles
    if proposal.get("authority_weights", {}).get("baseline_credentials", 0) > 0.6:
        return False, "Violation: Excessive credential weighting reduces democratic oversight"
    
    if proposal.get("thresholds", {}).get("disagreement", 1.0) < 0.1:
        return False, "Violation: Threshold too low, suppresses dialectical preservation"
    
    return framework.validate_decision(proposal)
```

## Configuration Examples

### Research Scenario: Credential-Heavy Weighting

For studying the impact of credentials vs. performance:

```yaml
authority_weights:
  baseline_credentials: 0.6  # Increase credential importance
  track_record: 0.3
  recent_performance: 0.1
```

### Research Scenario: Performance-Only Weighting

For pure performance-based authority:

```yaml
authority_weights:
  baseline_credentials: 0.0  # Ignore credentials
  track_record: 0.7
  recent_performance: 0.3
```

### Research Scenario: High Uncertainty Preservation

For studying disagreement in complex cases:

```yaml
thresholds:
  disagreement: 0.2  # Lower threshold = more uncertainty preservation
```

### Custom Credential Scoring

For jurisdiction-specific legal qualifications:

```yaml
baseline_credentials:
  types:
    BAR_ADMISSION:
      weight: 0.4
      scoring_function:
        type: map
        values:
          State_Bar: 1.0
          Federal_Bar: 1.3
          Supreme_Court_Bar: 1.8
        default: 0.0
    
    SPECIALIZATION:
      weight: 0.3
      scoring_function:
        type: formula
        expression: "1.0 + 0.1 * value"  # value = years in specialty
        default: 1.0
```

## Best Practices

### Academic Research Configuration

1. **Version Control**: Track configuration changes with git
2. **Experimentation**: Use branches for different parameter sets
3. **Documentation**: Comment configuration rationale
4. **Validation**: Test edge cases and boundary conditions

### Production Configuration

1. **Security**: Protect API keys and sensitive settings
2. **Monitoring**: Log configuration changes
3. **Rollback**: Maintain known-good configurations
4. **Testing**: Validate configurations in staging environment

### Parameter Tuning

1. **Start Conservative**: Begin with proven default values
2. **Single Variable**: Change one parameter at a time
3. **Measure Impact**: Track key metrics during changes
4. **Statistical Significance**: Ensure adequate sample sizes

## Troubleshooting

### Common Configuration Errors

**Authority weights don't sum to 1.0:**
```yaml
authority_weights:
  baseline_credentials: 0.3
  track_record: 0.5
  recent_performance: 0.3  # Error: 0.3+0.5+0.3 = 1.1
```

**Invalid formula syntax:**
```yaml
scoring_function:
  type: formula
  expression: "sqrt value"  # Error: Missing parentheses
  # Correct: "sqrt(value)"
```

**Unsupported mathematical function:**
```yaml
scoring_function:
  type: formula
  expression: "import os; os.system('rm -rf /')"  # Security violation
  # Only mathematical functions allowed
```

### Validation Debugging

Enable detailed logging to debug configuration issues:

```python
import logging
logging.getLogger("rlcf_framework.config").setLevel(logging.DEBUG)
```

### Performance Monitoring

Monitor configuration change impact:

```bash
# Check authority score distribution after changes
curl "http://localhost:8000/authority/stats"

# Monitor bias levels
curl "http://localhost:8000/bias/summary"

# Track aggregation quality
curl "http://localhost:8000/metrics/aggregation_quality"
```

---

**Next Steps:**
- [Task Handler System](task-handlers.md) - Understanding task processing
- [Database Schema](database-schema.md) - Data persistence layer
- [Configuration Guide](../guides/configuration.md) - Practical configuration setup
