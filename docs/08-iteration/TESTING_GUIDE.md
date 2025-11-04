# Testing Guide - Dynamic Configuration & RETRIEVAL_VALIDATION

**Status**: Completed
**Date**: January 2025
**Implementation Phase**: Phase 1 - Testing & Validation

## Overview

This guide documents the comprehensive test suite implemented for the dynamic configuration system and RETRIEVAL_VALIDATION handler. The test suite includes **3 new test modules** with **50+ test cases** covering unit tests, integration tests, and API endpoint tests.

## Test Files Created

### 1. `tests/rlcf/test_config_manager.py`

**Purpose**: Unit tests for the ConfigManager singleton and dynamic configuration system

**Test Classes**:
- `TestConfigManagerSingleton` - Singleton pattern and thread-safety (3 tests)
- `TestConfigManagerLoading` - Configuration loading and reloading (4 tests)
- `TestConfigManagerBackup` - Backup creation, listing, and restoration (5 tests)
- `TestConfigManagerTaskTypeManagement` - Task type CRUD operations (6 tests)
- `TestConfigManagerThreadSafety` - Concurrent access tests (1 test)
- `TestConfigFileHandler` - File watching and debouncing (2 tests)
- `TestConfigManagerWatching` - Observer pattern implementation (3 tests)

**Total**: 24 test cases

**Key Coverage**:
- ✅ Singleton instance management with thread-safety
- ✅ Configuration loading from YAML files
- ✅ Hot-reload mechanism with file watching
- ✅ Backup/restore functionality with timestamps
- ✅ Task type CRUD (Create, Read, Update, Delete)
- ✅ Concurrent read access validation
- ✅ Event debouncing (1-second window)

**Example Test**:
```python
def test_singleton_thread_safety(self):
    """Test that singleton initialization is thread-safe."""
    instances = []
    def get_instance():
        instances.append(ConfigManager.get_instance())

    threads = [threading.Thread(target=get_instance) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # All instances should be the same
    assert all(inst is instances[0] for inst in instances)
```

---

### 2. `tests/rlcf/test_config_router.py`

**Purpose**: API endpoint tests for the configuration management REST API

**Test Classes**:
- `TestGetTaskConfiguration` - GET /config/task endpoint (2 tests)
- `TestGetModelConfiguration` - GET /config/model endpoint (2 tests)
- `TestCreateTaskType` - POST /config/task/type endpoint (4 tests)
- `TestUpdateTaskType` - PUT /config/task/type/{name} endpoint (2 tests)
- `TestDeleteTaskType` - DELETE /config/task/type/{name} endpoint (3 tests)
- `TestListTaskTypes` - GET /config/task/types endpoint (1 test)
- `TestBackupManagement` - Backup endpoints (3 tests)
- `TestConfigurationStatus` - GET /config/status endpoint (2 tests)
- `TestValidationEndpoint` - Config validation endpoint (2 tests)
- `TestRateLimiting` - Rate limiting behavior (1 test)

**Total**: 22 test cases

**Key Coverage**:
- ✅ All REST API endpoints (10+ endpoints)
- ✅ Authentication/authorization with X-API-Key header
- ✅ Request/response validation (Pydantic models)
- ✅ Error handling (400, 404, 422 status codes)
- ✅ Backup management via API
- ✅ Configuration status monitoring

**Example Test**:
```python
def test_create_task_type_success(self, client, admin_headers, temp_config_dir):
    """Test successfully creating a new task type."""
    request_data = {
        "task_type_name": "NEW_LEGAL_ANALYSIS",
        "schema": {
            "input_data": {"case_text": "str", "jurisdiction": "str"},
            "feedback_data": {"analysis": "str", "confidence": "float"},
            "ground_truth_keys": ["analysis"]
        }
    }

    response = client.post(
        "/config/task/type",
        json=request_data,
        headers=admin_headers
    )

    assert response.status_code == 200
    assert data["success"] is True
```

---

### 3. `tests/rlcf/test_retrieval_validation_handler.py`

**Purpose**: Unit tests for the RETRIEVAL_VALIDATION task handler

**Test Classes**:
- `TestRetrievalValidationHandlerInitialization` - Handler setup (1 test)
- `TestAggregateFeedback` - Authority-weighted aggregation (5 tests)
- `TestCalculateConsistency` - Jaccard similarity calculations (4 tests)
- `TestCalculateCorrectness` - F1 score calculations (5 tests)
- `TestFormatForExport` - SFT and Preference Learning formatting (4 tests)
- `TestEdgeCases` - Error handling and edge cases (3 tests)

**Total**: 22 test cases

**Key Coverage**:
- ✅ Feedback aggregation with authority weighting (A_u(t) formula)
- ✅ Consensus determination for validated/irrelevant/missing items
- ✅ Consistency calculation using Jaccard similarity
- ✅ Correctness calculation using precision/recall/F1 score
- ✅ Export formatting for SFT and Preference Learning
- ✅ Edge cases (malformed data, single evaluator, empty sets)

**Example Test**:
```python
@pytest.mark.asyncio
async def test_aggregate_feedback_authority_weighting(self, mock_task):
    """Test that authority scores properly weight votes."""
    # High authority expert (0.95) disagrees with low authority experts (0.2 + 0.2)
    fb_high = create_feedback(authority=0.95, validated=["item1"])
    fb_low1 = create_feedback(authority=0.2, validated=["item2"])
    fb_low2 = create_feedback(authority=0.2, validated=["item2"])

    handler.get_feedbacks = AsyncMock(return_value=[fb_high, fb_low1, fb_low2])
    result = await handler.aggregate_feedback()

    # High authority should outweigh two low authority experts
    assert "item1" in result["consensus_validated_items"]
```

---

## Test Execution Instructions

### Prerequisites

1. **Python Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-asyncio pytest-cov httpx
   ```

### Running Tests

#### Run All New Tests
```bash
# All 3 new test modules
pytest tests/rlcf/test_config_manager.py \
       tests/rlcf/test_config_router.py \
       tests/rlcf/test_retrieval_validation_handler.py -v
```

#### Run Individual Test Modules
```bash
# ConfigManager tests only
pytest tests/rlcf/test_config_manager.py -v

# Config Router API tests only
pytest tests/rlcf/test_config_router.py -v

# RETRIEVAL_VALIDATION handler tests only
pytest tests/rlcf/test_retrieval_validation_handler.py -v
```

#### Run Specific Test Class
```bash
# Example: Only test singleton pattern
pytest tests/rlcf/test_config_manager.py::TestConfigManagerSingleton -v

# Example: Only test aggregation
pytest tests/rlcf/test_retrieval_validation_handler.py::TestAggregateFeedback -v
```

#### Run Full Regression Suite
```bash
# All RLCF tests (existing + new)
pytest tests/rlcf/ -v

# With coverage report
pytest tests/rlcf/ -v --cov=backend/rlcf_framework --cov-report=html
```

### Coverage Analysis

#### Generate Coverage Report
```bash
pytest tests/rlcf/ --cov=backend/rlcf_framework --cov-report=html --cov-report=term
```

**Coverage Targets**:
- Overall: ≥ 85% (Phase 1 requirement)
- ConfigManager: ≥ 90% (new critical component)
- Config Router: ≥ 85% (API endpoints)
- RetrievalValidationHandler: ≥ 90% (core RLCF logic)

#### View HTML Coverage Report
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

## Test Fixtures & Utilities

### Shared Fixtures (from `conftest.py`)

All tests inherit these fixtures:

```python
@pytest_asyncio.fixture
async def db():
    """Async database session (SQLite in-memory)"""

@pytest.fixture
def mock_user():
    """Mock user with authority score"""

@pytest.fixture
def mock_task():
    """Mock legal task"""

@pytest.fixture
def mock_feedback():
    """Mock feedback with ratings"""

@pytest.fixture
def mock_model_settings():
    """Mock ModelConfig"""

@pytest.fixture
def mock_task_settings():
    """Mock TaskConfig"""
```

### New Fixtures for Config Tests

```python
@pytest.fixture
def temp_config_dir():
    """Temporary directory for config file testing"""

@pytest.fixture
def admin_headers():
    """Admin API key headers for authenticated requests"""

@pytest.fixture
def client():
    """FastAPI TestClient"""
```

### New Fixtures for Handler Tests

```python
@pytest.fixture
def mock_task():
    """RETRIEVAL_VALIDATION task with retrieval metadata"""

@pytest.fixture
def mock_feedback_list():
    """List of 3 feedback objects with different authority scores"""
```

---

## Testing Strategy

### 1. Unit Tests
- **Isolated component testing** without external dependencies
- **Mock database sessions** using AsyncMock
- **Pure function testing** (calculate_consistency, calculate_correctness)

### 2. Integration Tests
- **API endpoint testing** with FastAPI TestClient
- **File I/O testing** with temporary directories
- **Database operations** with SQLite in-memory

### 3. Thread-Safety Tests
- **Concurrent access** testing with multiple threads
- **Singleton pattern** validation
- **Lock mechanism** verification

### 4. Edge Case Tests
- **Empty data sets** (no feedback, no ground truth)
- **Malformed data** (wrong types, missing fields)
- **Boundary conditions** (single evaluator, tied votes)

---

## Expected Test Results

### Success Criteria

When all tests pass, you should see:

```
tests/rlcf/test_config_manager.py::TestConfigManagerSingleton::test_singleton_instance PASSED
tests/rlcf/test_config_manager.py::TestConfigManagerSingleton::test_singleton_thread_safety PASSED
tests/rlcf/test_config_manager.py::TestConfigManagerLoading::test_get_model_config PASSED
tests/rlcf/test_config_manager.py::TestConfigManagerLoading::test_get_task_config PASSED
...
tests/rlcf/test_config_router.py::TestGetTaskConfiguration::test_get_task_configuration_success PASSED
tests/rlcf/test_config_router.py::TestCreateTaskType::test_create_task_type_success PASSED
...
tests/rlcf/test_retrieval_validation_handler.py::TestAggregateFeedback::test_aggregate_feedback_with_consensus PASSED
tests/rlcf/test_retrieval_validation_handler.py::TestCalculateConsistency::test_calculate_consistency_perfect_match PASSED
...

======================== 68 passed in X.XXs ========================
```

### Coverage Report Example

```
Name                                        Stmts   Miss  Cover
---------------------------------------------------------------
backend/rlcf_framework/config_manager.py      243     21    91%
backend/rlcf_framework/routers/config_router.py  187     15    92%
backend/rlcf_framework/task_handlers/retrieval_validation_handler.py  158     12    92%
---------------------------------------------------------------
TOTAL                                        2891    245    91%
```

---

## Known Issues & Notes

### 1. Authentication in Tests

The `test_config_router.py` tests use a test API key:
```python
admin_headers = {"X-API-Key": "test-admin-key-12345"}
```

**Note**: You may need to configure the actual API key in your test environment or mock the authentication dependency.

### 2. File Watching Tests

The file watching tests (`TestConfigManagerWatching`) may be sensitive to filesystem latency. If they fail intermittently:
- Increase debounce wait time from 1.1s to 2.0s
- Run tests on local filesystem (not network mount)

### 3. Async Test Warnings

If you see deprecation warnings about `event_loop` fixture:
```bash
# Use pytest-asyncio mode=auto
pytest tests/rlcf/ -v --asyncio-mode=auto
```

### 4. Database Connection Pooling

Some tests create temporary config files. Ensure cleanup:
```python
try:
    # Test code
finally:
    manager._task_config_path = original_path  # Restore
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'backend'"

**Solution**: Install package in editable mode:
```bash
pip install -e .
```

### Issue: "httpx not installed"

**Solution**: Install test dependencies:
```bash
pip install httpx  # For FastAPI TestClient
```

### Issue: "watchdog not installed"

**Solution**: Install file watching dependency:
```bash
pip install watchdog>=3.0.0
```

### Issue: Tests timeout or hang

**Possible causes**:
- File observer not stopped properly
- Async tasks not awaited
- Thread locks not released

**Solution**: Check test cleanup and use `pytest -v -s` for verbose output.

---

## Next Steps

After tests pass successfully:

1. **Verify Coverage**: Ensure ≥ 85% overall coverage
2. **Integration Testing**: Run manual tests with `scripts/test_dynamic_config.sh`
3. **Performance Testing**: Load test with 100+ concurrent requests
4. **Documentation Update**: Update README with test results
5. **Commit**: Commit all test files with detailed message

---

## File Locations

```
tests/rlcf/
├── conftest.py                                 # Shared fixtures (existing)
├── test_authority_module.py                    # Existing tests
├── test_aggregation_engine.py                  # Existing tests
├── test_bias_analysis.py                       # Existing tests
├── test_export_dataset.py                      # Existing tests
├── test_models.py                              # Existing tests
├── test_config_manager.py                      # ✨ NEW (24 tests)
├── test_config_router.py                       # ✨ NEW (22 tests)
└── test_retrieval_validation_handler.py        # ✨ NEW (22 tests)
```

**Total New Tests**: 68 test cases
**Estimated Coverage Increase**: +5-7% overall

---

## References

- `docs/02-methodology/rlcf/testing/MANUAL_TESTING_GUIDE.md` - Manual testing procedures
- `docs/04-implementation/DYNAMIC_CONFIGURATION.md` - Configuration system architecture
- `scripts/test_dynamic_config.sh` - Automated API testing script
- `backend/rlcf_framework/config_manager.py` - ConfigManager implementation
- `backend/rlcf_framework/routers/config_router.py` - API router implementation
- `backend/rlcf_framework/task_handlers/retrieval_validation_handler.py` - Handler implementation
