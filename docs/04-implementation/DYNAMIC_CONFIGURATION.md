# Dynamic Configuration System

**Status:** ✅ Implemented (Phase 1+)
**Component:** Configuration Management
**Dependencies:** ConfigManager, File Watching, Backup System
**Technologies:** Python, Pydantic, watchdog, YAML, FastAPI

---

## Overview

The RLCF framework implements a **hot-reload configuration system** that allows administrators to modify task types and system parameters **without restarting the server**. This enables:

- **Dynamic task type creation**: Add new legal task types on-the-fly
- **Schema evolution**: Update input/feedback schemas as requirements change
- **Live configuration**: Changes take effect immediately across all workers
- **Safe updates**: Automatic validation and backup before any modification
- **Rollback support**: Restore previous configurations from timestamped backups

This system is critical for adapting the RLCF framework to new legal domains and evolving requirements without service interruption.

---

## Architecture

### Components

```
┌──────────────────────────────────────────────────────────┐
│                   ConfigManager                          │
│  (Singleton, Thread-Safe, Hot-Reload Enabled)            │
├──────────────────────────────────────────────────────────┤
│  - ModelConfig (in-memory, live)                         │
│  - TaskConfig (in-memory, live)                          │
│  - File Watchers (model_config.yaml, task_config.yaml)  │
│  - Backup Manager (automatic versioning)                 │
│  - Validation Engine (Pydantic schemas)                  │
└──────────────────────────────────────────────────────────┘
                         ↓
        ┌────────────────┴────────────────┐
        │                                  │
        ↓                                  ↓
┌─────────────────┐             ┌─────────────────┐
│  File System    │             │  FastAPI        │
│  (YAML files)   │             │  (Endpoints)    │
│                 │             │                 │
│  - Manual edit  │             │  - CRUD API     │
│  - Auto-reload  │             │  - Validation   │
│  - Backups      │             │  - UI support   │
└─────────────────┘             └─────────────────┘
```

### Key Features

1. **Thread-Safe Access**
   - Uses `threading.RLock` for concurrent read/write operations
   - Safe for Uvicorn workers and multi-threaded deployment

2. **File Watching**
   - `watchdog` library monitors YAML file changes
   - Debounced reloading (1 second) to avoid rapid triggers
   - Automatic notification on successful reload

3. **Backup System**
   - Timestamped backups: `task_config_YYYYMMDD_HHMMSS.yaml`
   - Created before every configuration update
   - Stored in `backend/rlcf_framework/config_backups/`
   - List and restore via API

4. **Validation**
   - Pydantic models validate all configuration changes
   - Type checking for task schemas
   - Rollback on validation failure

---

## Configuration Files

### `task_config.yaml`

Defines all task types and their schemas:

```yaml
task_types:
  QA:
    input_data:
      question: str
      context: str
    feedback_data:
      validated_answer: str
      position: str
      reasoning: str
    ground_truth_keys: ["validated_answer"]

  CUSTOM_ANALYSIS:  # Example: dynamically added task type
    input_data:
      legal_text: str
      analysis_type: str
    feedback_data:
      analysis_result: str
      confidence: float
      references: List[str]
    ground_truth_keys: ["analysis_result"]
```

**Schema Fields:**
- `input_data`: Task input schema (what goes into `LegalTask.input_data`)
- `feedback_data`: Expected feedback structure (what goes into `Feedback.feedback_data`)
- `ground_truth_keys`: Fields to separate as ground truth for validation

### `model_config.yaml`

Defines authority scoring, thresholds, AI model settings:

```yaml
authority_weights:
  alpha: 0.3  # Baseline credentials weight
  beta: 0.5   # Track record weight
  gamma: 0.2  # Recent performance weight

track_record:
  consistency_weight: 0.6
  accuracy_weight: 0.4

thresholds:
  min_evaluators: 3
  bias_threshold: 0.5
  devils_advocate_probability: 0.1

baseline_credentials:
  types:
    ACADEMIC_DEGREE:
      weight: 0.3
      scoring_function:
        type: map
        values:
          Bachelor: 0.3
          LLM: 0.6
          PhD: 1.0
        default: 0.0

ai_model:
  name: "openai/gpt-4o-mini"
  temperature: 0.7
  max_tokens: 1000
  top_p: 0.9
  api_key_env: "OPENROUTER_API_KEY"
```

---

## API Reference

All endpoints require admin authentication (`X-API-KEY` header).

### Task Configuration Endpoints

#### **GET `/config/task`**
Get current task configuration.

**Response:**
```json
{
  "task_types": {
    "QA": {
      "input_data": {"question": "str", "context": "str"},
      "feedback_data": {"validated_answer": "str", ...},
      "ground_truth_keys": ["validated_answer"]
    },
    ...
  }
}
```

#### **POST `/config/task/type`**
Create a new task type dynamically.

**Request Body:**
```json
{
  "task_type_name": "CONTRACT_REVIEW",
  "schema": {
    "input_data": {
      "contract_text": "str",
      "review_criteria": "List[str]"
    },
    "feedback_data": {
      "review_result": "str",
      "issues_found": "List[str]",
      "severity": "int"
    },
    "ground_truth_keys": ["review_result", "issues_found"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Task type 'CONTRACT_REVIEW' created successfully",
  "task_type_name": "CONTRACT_REVIEW"
}
```

**Effects:**
- Task type added to `task_config.yaml`
- Backup created automatically
- Configuration reloaded immediately
- New task type available for creating tasks

#### **PUT `/config/task/type/{task_type_name}`**
Update an existing task type schema.

**Warning:** Changing schemas may break validation for existing tasks of this type.

#### **DELETE `/config/task/type/{task_type_name}`**
Delete a task type from configuration.

**Warning:** Does NOT delete existing tasks of this type from the database, only prevents creating new ones.

#### **GET `/config/task/types`**
List all configured task type names.

**Response:**
```json
[
  "QA",
  "STATUTORY_RULE_QA",
  "RETRIEVAL_VALIDATION",
  "CLASSIFICATION",
  ...
]
```

#### **GET `/config/task/type/{task_type_name}`**
Get schema definition for a specific task type.

### Model Configuration Endpoints

#### **GET `/config/model`**
Get current model configuration.

#### **PUT `/config/model`**
Update model configuration (authority weights, thresholds, AI settings).

### Backup Management Endpoints

#### **GET `/config/backups?config_type=all`**
List all configuration backups.

**Query Parameters:**
- `config_type`: "model", "task", or "all" (default: "all")

**Response:**
```json
{
  "backups": [
    {
      "filename": "task_config_20250105_143052.yaml",
      "type": "task",
      "timestamp": 1736087452.0,
      "size_bytes": 2456,
      "formatted_date": "2025-01-05 14:30:52"
    },
    ...
  ],
  "total_count": 12
}
```

#### **POST `/config/backups/restore`**
Restore a configuration from backup.

**Request Body:**
```json
{
  "backup_filename": "task_config_20250105_143052.yaml"
}
```

**Effects:**
- Current config backed up before restoration
- Specified backup restored and validated
- Configuration reloaded immediately

### Status & Health

#### **GET `/config/status`**
Get configuration system status.

**Response:**
```json
{
  "status": "active",
  "file_watching_enabled": true,
  "task_types_count": 11,
  "task_types": ["QA", "STATUTORY_RULE_QA", ...],
  "config_files": {
    "model_config": "model_config.yaml",
    "task_config": "task_config.yaml"
  },
  "backup_directory": "config_backups"
}
```

---

## Usage Examples

### Example 1: Add a New Task Type via API

```bash
# Add a custom "COMPLIANCE_CHECK" task type
curl -X POST http://localhost:8000/config/task/type \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: $ADMIN_API_KEY" \
  -d '{
    "task_type_name": "COMPLIANCE_CHECK",
    "schema": {
      "input_data": {
        "regulation": "str",
        "company_data": "str"
      },
      "feedback_data": {
        "is_compliant": "bool",
        "violations": "List[str]",
        "recommendations": "str"
      },
      "ground_truth_keys": ["is_compliant", "violations"]
    }
  }'

# Response:
# {
#   "success": true,
#   "message": "Task type 'COMPLIANCE_CHECK' created successfully",
#   "task_type_name": "COMPLIANCE_CHECK"
# }
```

**What happens:**
1. API validates the schema with Pydantic
2. Current `task_config.yaml` backed up to `config_backups/task_config_20250105_145623.yaml`
3. New task type added to YAML file
4. File watcher detects change
5. ConfigManager reloads configuration
6. New task type immediately available

**Create a task of the new type:**
```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "COMPLIANCE_CHECK",
    "input_data": {
      "regulation": "GDPR Article 6",
      "company_data": "Our company processes personal data for..."
    }
  }'
```

### Example 2: Hot-Reload via Manual YAML Edit

1. **Edit `task_config.yaml` directly:**
```yaml
# Add a new task type manually
CUSTOM_ANALYSIS:
  input_data:
    legal_text: str
    analysis_type: str
  feedback_data:
    analysis_result: str
    confidence: float
  ground_truth_keys: ["analysis_result"]
```

2. **Save the file**

3. **Watch the logs:**
```
[ConfigManager] Hot-reloaded: task_config.yaml
[RLCF] Configuration updated successfully
```

4. **Verify:**
```bash
curl http://localhost:8000/config/task/types

# Response includes:
# ["QA", "STATUTORY_RULE_QA", ..., "CUSTOM_ANALYSIS"]
```

No server restart required!

### Example 3: Restore from Backup

```bash
# List backups
curl -X GET http://localhost:8000/config/backups?config_type=task \
  -H "X-API-KEY: $ADMIN_API_KEY"

# Restore a specific backup
curl -X POST http://localhost:8000/config/backups/restore \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: $ADMIN_API_KEY" \
  -d '{
    "backup_filename": "task_config_20250105_143052.yaml"
  }'
```

---

## Implementation Details

### ConfigManager Class

**Location:** `backend/rlcf_framework/config_manager.py`

**Key Methods:**
```python
# Get singleton instance
config_manager = ConfigManager.get_instance()

# Get current configurations (thread-safe)
model_config = config_manager.get_model_config()
task_config = config_manager.get_task_config()

# Update configurations with validation
success, error = config_manager.update_task_config(config_dict)

# CRUD operations for task types
success, error = config_manager.add_task_type(name, schema)
success, error = config_manager.update_task_type(name, schema)
success, error = config_manager.delete_task_type(name)

# Backup management
backups = config_manager.list_backups(config_type="task")
success, error = config_manager.restore_backup(filename)

# File watching
config_manager.start_watching()  # Auto-started on initialization
config_manager.stop_watching()   # Called on server shutdown
```

### Thread Safety

ConfigManager uses `threading.RLock` for all configuration access:

```python
with self._task_lock:
    # Thread-safe configuration access
    return self._task_config
```

This ensures safe concurrent access from:
- Multiple FastAPI workers
- File watcher threads
- API request handlers

### File Watching Implementation

Uses `watchdog.observers.Observer` to monitor file system events:

```python
class ConfigFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path == self.config_file_path:
            # Debounce: ignore rapid-fire events
            if time.time() - self.last_modified > 1.0:
                self.reload_callback()
```

**Debouncing:** Prevents multiple reloads when editors save files with multiple write operations.

---

## Testing

### Manual Testing Procedure

1. **Start the server:**
```bash
cd backend
uvicorn rlcf_framework.main:app --reload
```

2. **Check initial configuration:**
```bash
curl http://localhost:8000/config/status
```

3. **Add a task type via API:**
```bash
curl -X POST http://localhost:8000/config/task/type \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: supersecretkey" \
  -d '{"task_type_name": "TEST_TASK", "schema": {...}}'
```

4. **Edit YAML manually:**
```bash
# Edit backend/rlcf_framework/task_config.yaml
# Add or modify a task type
```

5. **Watch for hot-reload message:**
```
[ConfigManager] Hot-reloaded: task_config.yaml
```

6. **Verify change:**
```bash
curl http://localhost:8000/config/task/types
```

### Automated Testing

**Location:** `tests/rlcf/test_config_manager.py` (to be created)

```python
import pytest
from backend.rlcf_framework.config_manager import ConfigManager

@pytest.mark.asyncio
async def test_add_task_type():
    """Test adding a new task type dynamically."""
    manager = ConfigManager.get_instance()

    success, error = manager.add_task_type(
        "TEST_TASK",
        {
            "input_data": {"field1": "str"},
            "feedback_data": {"result": "str"},
            "ground_truth_keys": ["result"]
        }
    )

    assert success is True
    assert error is None

    # Verify it's in the config
    config = manager.get_task_config()
    assert "TEST_TASK" in config.task_types
```

---

## Best Practices

### 1. Always Use Backups

Before major configuration changes:

```bash
# Manual backup
cp backend/rlcf_framework/task_config.yaml task_config_backup_$(date +%Y%m%d_%H%M%S).yaml
```

API automatically creates backups, but manual backups are useful for major changes.

### 2. Validate Schemas Before Adding

Test your schema with Pydantic before adding to configuration:

```python
from pydantic import BaseModel, create_model

# Validate your schema can be parsed
try:
    DynamicModel = create_model(
        "TestSchema",
        **{"field_name": (str, ...)}
    )
    print("Schema valid!")
except Exception as e:
    print(f"Schema invalid: {e}")
```

### 3. Consider Existing Tasks

When modifying task type schemas:
- Check if tasks of this type exist in the database
- Consider backward compatibility
- Test validation with existing data

### 4. Use Gradual Rollout

For production systems:
1. Add new task type to configuration
2. Create test tasks to verify schema
3. Run validation on test data
4. Enable for production use

### 5. Monitor Logs

Watch for configuration reload messages:

```bash
tail -f rlcf_detailed.log | grep -i config
```

---

## Security Considerations

### Authentication

All configuration endpoints require admin API key:

```python
@router.post("/config/task/type")
async def create_task_type(
    request: TaskTypeCreateRequest,
    api_key: str = Depends(get_api_key)  # ← Admin auth required
):
```

**Set your API key:**
```bash
export ADMIN_API_KEY="your-secure-key-here"
```

### Validation

Pydantic validates all configuration changes before applying:

```python
try:
    new_config = TaskConfig(**config_dict)
except ValidationError as e:
    return False, f"Validation failed: {str(e)}"
```

Invalid configurations are rejected and not written to files.

### Rollback Safety

Every update creates a backup, enabling safe rollback:

```bash
# If something goes wrong, restore immediately
curl -X POST http://localhost:8000/config/backups/restore \
  -H "X-API-KEY: $ADMIN_API_KEY" \
  -d '{"backup_filename": "task_config_20250105_143052.yaml"}'
```

---

## Troubleshooting

### Issue: Configuration not reloading

**Symptoms:** Edit YAML file but changes don't take effect.

**Solutions:**
1. Check file watching is enabled:
   ```bash
   curl http://localhost:8000/config/status
   # Check: "file_watching_enabled": true
   ```

2. Check logs for errors:
   ```bash
   tail -f rlcf_detailed.log | grep ConfigManager
   ```

3. Restart server:
   ```bash
   # Ctrl+C to stop
   uvicorn rlcf_framework.main:app --reload
   ```

### Issue: Validation errors when adding task type

**Symptoms:** API returns "Validation failed: ..."

**Solutions:**
1. Check schema syntax:
   ```json
   {
     "input_data": {
       "field_name": "str"  # ← Must be Python type as string
     }
   }
   ```

2. Valid types: `str`, `int`, `float`, `bool`, `List[str]`, `Dict[str, float]`, etc.

3. Ensure all required fields present:
   - `input_data`
   - `feedback_data`
   - `ground_truth_keys` (can be empty list)

### Issue: Backup restoration failed

**Symptoms:** "Backup file not found" or "Restore failed"

**Solutions:**
1. List available backups:
   ```bash
   curl http://localhost:8000/config/backups \
     -H "X-API-KEY: $ADMIN_API_KEY"
   ```

2. Use exact filename from list

3. Check backup file is valid YAML:
   ```bash
   python -c "import yaml; yaml.safe_load(open('config_backups/filename.yaml'))"
   ```

---

## Future Enhancements

### Planned Features

1. **UI Admin Panel** (Phase 2)
   - Visual task type editor
   - Schema builder with drag-and-drop
   - Backup browser with diff viewer

2. **Configuration Versioning** (Phase 2)
   - Git-style version history
   - Diff between configurations
   - Rollback to any version

3. **Multi-Environment Support** (Phase 3)
   - Development/staging/production configs
   - Environment-specific task types
   - Configuration promotion workflow

4. **Schema Migration System** (Phase 3)
   - Automatic migration of existing tasks to new schemas
   - Backward compatibility layer
   - Migration rollback support

---

## Related Documentation

- [Configuration System](../02-methodology/rlcf/technical/configuration.md) - Original design
- [Database Schema](../02-methodology/rlcf/technical/database-schema.md) - Task types in DB
- [API Reference](../02-methodology/rlcf/api/endpoints.md) - All API endpoints
- [RLCF.md](../02-methodology/rlcf/RLCF.md) - Core framework documentation

---

**Implementation Status:** ✅ Complete
**Testing Status:** ⚠️ Manual testing required
**Documentation Status:** ✅ Complete
**Last Updated:** 2025-01-05
