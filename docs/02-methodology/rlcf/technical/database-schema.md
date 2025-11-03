# Database Schema

The RLCF framework uses a relational database design optimized for academic research, authority tracking, and bias analysis. The schema supports dynamic task types while maintaining referential integrity and performance.

## Schema Overview

```sql
-- Core entity relationships
Users (1:N) Credentials
Users (1:N) Feedback
LegalTasks (1:N) Responses (1:N) Feedback
LegalTasks (1:N) BiasReports
LegalTasks (1:N) DevilsAdvocateAssignments
Users (1:N) DevilsAdvocateAssignments
```

## Core Tables

### Users Table

Stores user information and dynamic authority scores.

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(100) UNIQUE NOT NULL,
    authority_score REAL DEFAULT 0.5,
    baseline_credential_score REAL DEFAULT 0.0,
    track_record_score REAL DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_authority_score ON users(authority_score);
```

**Field Descriptions:**
- `id`: Primary key, auto-incrementing
- `username`: Unique identifier for user (3-50 characters)
- `authority_score`: Current authority score [0.0, 2.0]
- `baseline_credential_score`: Credential-based score [0.0, 2.0]
- `track_record_score`: Historical performance [0.0, 1.0]
- `created_at`: User registration timestamp
- `updated_at`: Last authority score update

**Mathematical Relationships:**
```
authority_score = α·baseline_credential_score + β·track_record_score + γ·recent_performance
where α + β + γ = 1.0 (default: 0.3 + 0.5 + 0.2)
```

### Credentials Table

Flexible credential storage supporting multiple types and verification status.

```sql
CREATE TABLE credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL,
    value TEXT NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_credentials_user_id ON credentials(user_id);
CREATE INDEX idx_credentials_type ON credentials(type);
CREATE INDEX idx_credentials_verified ON credentials(verified);
```

**Credential Types (Enum):**
- `ACADEMIC_DEGREE`: Bachelor, LLM, JD, PhD
- `PROFESSIONAL_EXPERIENCE`: Years of practice (numeric)
- `PUBLICATION`: Number of publications (numeric)
- `INSTITUTIONAL_ROLE`: Junior, Senior, Partner
- `BAR_ADMISSION`: State_Bar, Federal_Bar, Supreme_Court_Bar
- `SPECIALIZATION`: Legal specialty areas

**Scoring Integration:**
```python
# Baseline credential calculation: B_u = Σ(w_i · f_i(c_{u,i}))
def calculate_baseline_score(credentials):
    total_score = 0.0
    for credential in credentials:
        weight = config.baseline_credentials.types[credential.type].weight
        scoring_func = config.baseline_credentials.types[credential.type].scoring_function
        
        if scoring_func.type == "map":
            score = scoring_func.values.get(credential.value, scoring_func.default)
        elif scoring_func.type == "formula":
            score = safe_eval(scoring_func.expression, {"value": float(credential.value)})
        
        total_score += weight * score
    
    return min(2.0, total_score)  # Cap at maximum score
```

### Legal Tasks Table

Dynamic task storage supporting multiple legal task types.

```sql
CREATE TABLE legal_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type VARCHAR(50) NOT NULL,
    input_data JSON NOT NULL,
    ground_truth_data JSON NULL,
    status VARCHAR(20) DEFAULT 'OPEN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_legal_tasks_type ON legal_tasks(task_type);
CREATE INDEX idx_legal_tasks_status ON legal_tasks(status);
CREATE INDEX idx_legal_tasks_created_at ON legal_tasks(created_at);
```

**Task Types (Enum):**
- `SUMMARIZATION`: Document summarization
- `CLASSIFICATION`: Text classification
- `QA`: Question answering
- `STATUTORY_RULE_QA`: Statutory interpretation
- `PREDICTION`: Legal outcome prediction
- `NLI`: Natural language inference
- `NER`: Named entity recognition
- `DRAFTING`: Legal document drafting
- `RISK_SPOTTING`: Compliance risk identification
- `DOCTRINE_APPLICATION`: Legal doctrine application

**Task Status (Enum):**
- `OPEN`: Available for AI response generation
- `BLIND_EVALUATION`: In blind evaluation phase
- `AGGREGATED`: Community feedback aggregated
- `CLOSED`: Evaluation complete

**Dynamic Schema Example:**
```json
{
  "input_data": {
    "question": "What are the requirements for contract formation?",
    "context_full": "Contract law principles...",
    "rule_id": "contract_001",
    "relevant_articles": "Article 1, Article 2"
  },
  "ground_truth_data": {
    "answer_text": "The three requirements are offer, acceptance, and consideration.",
    "confidence_level": "high",
    "source_citations": ["Restatement §1", "UCC §2-204"]
  }
}
```

### Responses Table

AI-generated responses to legal tasks.

```sql
CREATE TABLE responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    output_data JSON NOT NULL,
    model_version VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES legal_tasks(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_responses_task_id ON responses(task_id);
CREATE INDEX idx_responses_model_version ON responses(model_version);
CREATE INDEX idx_responses_created_at ON responses(created_at);
```

**Response Data Structure:**
```json
{
  "output_data": {
    "answer": "Contract formation requires offer, acceptance, and consideration...",
    "confidence": 0.85,
    "reasoning": "Based on fundamental contract law principles...",
    "sources": ["Restatement (Second) of Contracts §17", "UCC §2-204"],
    "model_metadata": {
      "temperature": 0.7,
      "max_tokens": 1000,
      "prompt_tokens": 150,
      "completion_tokens": 85
    }
  }
}
```

### Feedback Table

Community feedback on AI responses with dynamic schema support.

```sql
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    response_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    feedback_data JSON NOT NULL,
    accuracy_score REAL NULL,
    consistency_score REAL NULL,
    community_helpfulness_rating REAL NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (response_id) REFERENCES responses(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_feedback_response_id ON feedback(response_id);
CREATE INDEX idx_feedback_user_id ON feedback(user_id);
CREATE INDEX idx_feedback_submitted_at ON feedback(submitted_at);
CREATE INDEX idx_feedback_accuracy_score ON feedback(accuracy_score);
```

**Task-Specific Feedback Schemas:**

**QA Feedback:**
```json
{
  "feedback_data": {
    "validated_answer": "The three essential elements are offer, acceptance, and consideration.",
    "position": "correct",
    "reasoning": "The AI response correctly identifies all required elements...",
    "quality_rating": 4,
    "completeness_rating": 5
  }
}
```

**Statutory Rule QA Feedback:**
```json
{
  "feedback_data": {
    "validated_answer": "Under Section 2-204, contract formation requires...",
    "confidence": "high",
    "position": "partially_correct",
    "reasoning": "The response is accurate but misses important exceptions...",
    "sources_verified": true,
    "missing_citations": ["UCC §2-206"]
  }
}
```

**Classification Feedback:**
```json
{
  "feedback_data": {
    "validated_labels": ["Contract Law", "Commercial Law"],
    "reasoning": "The document clearly discusses contract formation and commercial transactions...",
    "confidence": "high",
    "alternative_labels": ["UCC"]
  }
}
```

## Analysis and Reporting Tables

### Bias Reports Table

Six-dimensional bias analysis results.

```sql
CREATE TABLE bias_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    demographic_bias REAL NOT NULL,
    professional_clustering REAL NOT NULL,
    temporal_drift REAL NOT NULL,
    geographic_concentration REAL NOT NULL,
    confirmation_bias REAL NOT NULL,
    anchoring_bias REAL NOT NULL,
    total_bias_score REAL NOT NULL,
    bias_level VARCHAR(10) NOT NULL,
    mitigation_recommendations JSON NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES legal_tasks(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_bias_reports_task_id ON bias_reports(task_id);
CREATE INDEX idx_bias_reports_total_bias_score ON bias_reports(total_bias_score);
CREATE INDEX idx_bias_reports_bias_level ON bias_reports(bias_level);
```

**Mathematical Formula:**
```
total_bias_score = √(demographic² + professional² + temporal² + geographic² + confirmation² + anchoring²)
```

**Bias Level Classification:**
- `low`: total_bias_score ≤ 0.5
- `medium`: 0.5 < total_bias_score ≤ 1.0
- `high`: total_bias_score > 1.0

### Devils Advocate Assignments Table

Critical evaluation assignment tracking.

```sql
CREATE TABLE devils_advocate_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    instructions TEXT NULL,
    assignment_probability REAL NOT NULL,
    effectiveness_score REAL NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    FOREIGN KEY (task_id) REFERENCES legal_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_devils_advocate_task_id ON devils_advocate_assignments(task_id);
CREATE INDEX idx_devils_advocate_user_id ON devils_advocate_assignments(user_id);
CREATE INDEX idx_devils_advocate_assigned_at ON devils_advocate_assignments(assigned_at);

-- Ensure unique assignment per task-user pair
CREATE UNIQUE INDEX idx_devils_advocate_unique ON devils_advocate_assignments(task_id, user_id);
```

**Assignment Probability Formula:**
```
P(advocate) = min(0.1, 3/|E|)
where |E| = number of eligible evaluators
```

### Aggregation Results Table

Stores consensus results and uncertainty metrics.

```sql
CREATE TABLE aggregation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    primary_answer TEXT NOT NULL,
    confidence_level REAL NOT NULL,
    disagreement_score REAL NOT NULL,
    consensus_data JSON NOT NULL,
    alternative_positions JSON NULL,
    expert_disagreement JSON NULL,
    epistemic_metadata JSON NULL,
    aggregated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES legal_tasks(id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX idx_aggregation_results_task_id ON aggregation_results(task_id);
CREATE INDEX idx_aggregation_results_confidence_level ON aggregation_results(confidence_level);
CREATE INDEX idx_aggregation_results_disagreement_score ON aggregation_results(disagreement_score);
```

**Consensus Data Structure:**
```json
{
  "consensus_data": {
    "method": "authority_weighted",
    "participant_count": 15,
    "authority_sum": 12.5,
    "dominant_position_support": 0.8
  },
  "alternative_positions": [
    {
      "position": "Alternative interpretation focusing on modern precedent...",
      "support": 0.2,
      "reasoning": "Recent case law suggests a different approach...",
      "authority_weight": 2.5
    }
  ],
  "expert_disagreement": {
    "consensus_areas": ["Basic contract requirements", "Offer and acceptance principles"],
    "contention_points": ["Role of consideration in modern contracts", "Digital contract formation"],
    "reasoning_patterns": ["Formalist vs functionalist approaches", "Traditional vs progressive interpretation"]
  },
  "epistemic_metadata": {
    "uncertainty_sources": ["Evolving case law", "Jurisdictional differences"],
    "suggested_research": ["Recent circuit court decisions", "State law variations"],
    "confidence_calibration": 0.85
  }
}
```

## Performance Optimization

### Database Indexes

```sql
-- Composite indexes for common query patterns
CREATE INDEX idx_feedback_response_user ON feedback(response_id, user_id);
CREATE INDEX idx_tasks_type_status ON legal_tasks(task_type, status);
CREATE INDEX idx_tasks_created_status ON legal_tasks(created_at, status);

-- JSON field indexes (SQLite 3.45+)
CREATE INDEX idx_legal_tasks_question ON legal_tasks(json_extract(input_data, '$.question'));
CREATE INDEX idx_responses_confidence ON responses(json_extract(output_data, '$.confidence'));

-- Partial indexes for active records
CREATE INDEX idx_active_tasks ON legal_tasks(id) WHERE status IN ('OPEN', 'BLIND_EVALUATION');
CREATE INDEX idx_verified_credentials ON credentials(user_id, type) WHERE verified = TRUE;
```

### Query Optimization Examples

```sql
-- Efficient authority score calculation query
SELECT 
    u.id,
    u.username,
    u.authority_score,
    COUNT(f.id) as feedback_count,
    AVG(f.accuracy_score) as avg_accuracy
FROM users u
LEFT JOIN feedback f ON u.id = f.user_id
WHERE u.authority_score > 0.5
GROUP BY u.id, u.username, u.authority_score
ORDER BY u.authority_score DESC
LIMIT 50;

-- Efficient bias analysis query
SELECT 
    lt.task_type,
    AVG(br.total_bias_score) as avg_bias,
    COUNT(*) as task_count
FROM legal_tasks lt
JOIN bias_reports br ON lt.id = br.task_id
WHERE lt.created_at >= DATE('now', '-30 days')
GROUP BY lt.task_type
ORDER BY avg_bias DESC;

-- Efficient disagreement analysis
SELECT 
    lt.id,
    json_extract(lt.input_data, '$.question') as question,
    ar.disagreement_score,
    ar.confidence_level
FROM legal_tasks lt
JOIN aggregation_results ar ON lt.id = ar.task_id
WHERE ar.disagreement_score > 0.4
ORDER BY ar.disagreement_score DESC;
```

## Data Integrity Constraints

### Foreign Key Constraints

```sql
-- Ensure referential integrity
PRAGMA foreign_keys = ON;

-- Cascade deletes for dependent data
ALTER TABLE credentials ADD CONSTRAINT fk_credentials_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE responses ADD CONSTRAINT fk_responses_task
    FOREIGN KEY (task_id) REFERENCES legal_tasks(id) ON DELETE CASCADE;

ALTER TABLE feedback ADD CONSTRAINT fk_feedback_response
    FOREIGN KEY (response_id) REFERENCES responses(id) ON DELETE CASCADE;

ALTER TABLE feedback ADD CONSTRAINT fk_feedback_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
```

### Check Constraints

```sql
-- Ensure score ranges
ALTER TABLE users ADD CONSTRAINT chk_authority_score
    CHECK (authority_score >= 0.0 AND authority_score <= 2.0);

ALTER TABLE users ADD CONSTRAINT chk_track_record_score
    CHECK (track_record_score >= 0.0 AND track_record_score <= 1.0);

ALTER TABLE users ADD CONSTRAINT chk_baseline_credential_score
    CHECK (baseline_credential_score >= 0.0 AND baseline_credential_score <= 2.0);

-- Ensure feedback scores are valid
ALTER TABLE feedback ADD CONSTRAINT chk_accuracy_score
    CHECK (accuracy_score IS NULL OR (accuracy_score >= 0.0 AND accuracy_score <= 1.0));

ALTER TABLE feedback ADD CONSTRAINT chk_consistency_score
    CHECK (consistency_score IS NULL OR (consistency_score >= 0.0 AND consistency_score <= 1.0));

-- Ensure disagreement scores are normalized
ALTER TABLE aggregation_results ADD CONSTRAINT chk_disagreement_score
    CHECK (disagreement_score >= 0.0 AND disagreement_score <= 1.0);

ALTER TABLE aggregation_results ADD CONSTRAINT chk_confidence_level
    CHECK (confidence_level >= 0.0 AND confidence_level <= 1.0);
```

## Database Migrations

### Version Control

```python
# migrations/001_initial_schema.py
"""Initial RLCF database schema"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

def upgrade():
    """Create initial tables."""
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(100), unique=True, nullable=False),
        sa.Column('authority_score', sa.Float(), default=0.5),
        sa.Column('baseline_credential_score', sa.Float(), default=0.0),
        sa.Column('track_record_score', sa.Float(), default=0.5),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Create indexes
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_authority_score', 'users', ['authority_score'])

def downgrade():
    """Drop initial tables."""
    op.drop_table('users')
```

### Schema Evolution

```python
# migrations/002_add_bias_analysis.py
"""Add bias analysis tables"""

def upgrade():
    """Add bias reports table."""
    op.create_table(
        'bias_reports',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('task_id', sa.Integer(), sa.ForeignKey('legal_tasks.id'), nullable=False),
        sa.Column('demographic_bias', sa.Float(), nullable=False),
        sa.Column('professional_clustering', sa.Float(), nullable=False),
        sa.Column('temporal_drift', sa.Float(), nullable=False),
        sa.Column('geographic_concentration', sa.Float(), nullable=False),
        sa.Column('confirmation_bias', sa.Float(), nullable=False),
        sa.Column('anchoring_bias', sa.Float(), nullable=False),
        sa.Column('total_bias_score', sa.Float(), nullable=False),
        sa.Column('bias_level', sa.String(10), nullable=False),
        sa.Column('mitigation_recommendations', sqlite.JSON()),
        sa.Column('generated_at', sa.DateTime(), server_default=sa.func.now())
    )
```

## Backup and Recovery

### Automated Backup Strategy

```bash
#!/bin/bash
# backup_database.sh

DB_PATH="/app/rlcf.db"
BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/rlcf_backup_$TIMESTAMP.db"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Create database backup
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

# Compress backup
gzip "$BACKUP_FILE"

# Clean up old backups (keep last 30 days)
find "$BACKUP_DIR" -name "rlcf_backup_*.db.gz" -mtime +30 -delete

echo "Database backup completed: $BACKUP_FILE.gz"
```

### Recovery Procedures

```bash
#!/bin/bash
# restore_database.sh

BACKUP_FILE="$1"
DB_PATH="/app/rlcf.db"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.db.gz>"
    exit 1
fi

# Stop application
systemctl stop rlcf-api

# Backup current database
mv "$DB_PATH" "$DB_PATH.pre_restore"

# Restore from backup
gunzip -c "$BACKUP_FILE" > "$DB_PATH"

# Verify database integrity
sqlite3 "$DB_PATH" "PRAGMA integrity_check;"

# Start application
systemctl start rlcf-api

echo "Database restored from: $BACKUP_FILE"
```

---

**Related Documentation:**
- [System Architecture](architecture.md) - Overall system design
- [Configuration System](configuration.md) - Model and task configuration
- [API Schemas](../api/schemas.md) - Data validation and structure
