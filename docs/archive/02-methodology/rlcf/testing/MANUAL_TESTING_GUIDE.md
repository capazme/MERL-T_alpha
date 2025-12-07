# Manual End-to-End Testing Guide - RLCF Framework

**Version**: Alpha 0.0.1  
**Date**: 2024-01-15  
**Prerequisites**: Server running on http://localhost:8000

## 🚀 Quick Setup

```bash
# 1. Start the server
cd /path/to/RLCF
python -m uvicorn rlcf_framework.main:app --reload --port 8000

# 2. Set API key for admin operations
export ADMIN_API_KEY=supersecretkey

# 3. Open interactive docs (optional)
open http://localhost:8000/docs
```

## 📋 Complete End-to-End Testing Sequence

### Phase 1: System Initialization & User Management

#### 1.1 Verify Server Health
```bash
# Basic health check
curl http://localhost:8000/docs
# Expected: Swagger UI loads successfully
```

#### 1.2 Create Test Users
```bash
# Create User 1 (Expert)
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"username": "expert_lawyer"}'

# Expected Response:
# {
#   "id": 1,
#   "username": "expert_lawyer", 
#   "authority_score": 0.0,
#   "track_record_score": 0.0,
#   "baseline_credential_score": 0.0,
#   "credentials": []
# }

# Create User 2 (Junior)
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"username": "junior_lawyer"}'

# Create User 3 (Senior)
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{"username": "senior_partner"}'

# Bulk create additional users
curl -X POST "http://localhost:8000/users/bulk" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: supersecretkey" \
  -d '{"usernames": ["test_user1", "test_user2", "test_user3"]}'
```

#### 1.3 Add Credentials to Users
```bash
# Add academic degree to expert
curl -X POST "http://localhost:8000/users/1/credentials/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "ACADEMIC_DEGREE",
    "value": "JD", 
    "weight": 0.3
  }'

# Add professional experience to expert
curl -X POST "http://localhost:8000/users/1/credentials/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "PROFESSIONAL_EXPERIENCE",
    "value": "15",
    "weight": 0.4
  }'

# Add credentials to other users
curl -X POST "http://localhost:8000/users/2/credentials/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "ACADEMIC_DEGREE", 
    "value": "Bachelor",
    "weight": 0.3
  }'

curl -X POST "http://localhost:8000/users/3/credentials/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "INSTITUTIONAL_ROLE",
    "value": "Partner", 
    "weight": 0.1
  }'
```

#### 1.4 Verify User Creation
```bash
# Get single user
curl "http://localhost:8000/users/1"

# Get all users
curl "http://localhost:8000/users/all"

# Expected: Users created with updated authority scores
```

### Phase 2: Task Management

#### 2.1 Create Legal Tasks

```bash
# Create STATUTORY_RULE_QA task
curl -X POST "http://localhost:8000/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "STATUTORY_RULE_QA",
    "input_data": {
      "question": "What are the requirements for a valid employment contract?",
      "rule_id": "employment_law_001",
      "context_full": "Employment law requires specific elements for contract validity including mutual consent, consideration, and legal capacity of parties.",
      "context_count": 1,
      "relevant_articles": "Article 15, Article 16 of Employment Code",
      "category": "Employment Law",
      "tags": "contract, employment, validity",
      "metadata_full": "{\"source\": \"employment_code\", \"jurisdiction\": \"federal\"}"
    }
  }'

# Create QA task  
curl -X POST "http://localhost:8000/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "QA",
    "input_data": {
      "question": "What is the statute of limitations for breach of contract?",
      "context": "In most jurisdictions, the statute of limitations for breach of contract claims varies between 3-6 years depending on the type of contract and jurisdiction."
    }
  }'

# Create CLASSIFICATION task
curl -X POST "http://localhost:8000/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "CLASSIFICATION", 
    "input_data": {
      "text": "This agreement shall be governed by the laws of California and any disputes shall be resolved through binding arbitration.",
      "unit": "clause"
    }
  }'

# Create SUMMARIZATION task
curl -X POST "http://localhost:8000/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "SUMMARIZATION",
    "input_data": {
      "document": "This comprehensive employment agreement establishes the terms and conditions of employment between Company ABC and Employee. The agreement includes salary provisions, benefit entitlements, confidentiality obligations, and termination procedures. The employee agrees to work exclusively for the company and maintain confidentiality of proprietary information."
    }
  }'
```

#### 2.2 Verify Task Creation & Get Tasks
```bash
# Get single task
curl "http://localhost:8000/tasks/1"

# Get all tasks
curl "http://localhost:8000/tasks/all"

# Get tasks with filters
curl "http://localhost:8000/tasks/all?status=BLIND_EVALUATION&limit=10"

# Get tasks by type
curl "http://localhost:8000/tasks/all?task_type=STATUTORY_RULE_QA"
```

#### 2.3 Task Assignment
```bash
# Assign task to user
curl -X POST "http://localhost:8000/tasks/1/assign" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: supersecretkey" \
  -d '{
    "user_id": 1,
    "role": "evaluator"
  }'

# Get task assignees
curl "http://localhost:8000/tasks/1/assignees"
```

### Phase 3: Feedback Submission & Management

#### 3.1 Submit Feedback for Different Task Types

```bash
# Get task responses first to get response_id
curl "http://localhost:8000/tasks/1"
# Note the response ID from the output (should be 1)

# Submit feedback for STATUTORY_RULE_QA task (response_id: 1)
curl -X POST "http://localhost:8000/responses/1/feedback/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "accuracy_score": 8.5,
    "utility_score": 8.0,
    "transparency_score": 9.0,
    "feedback_data": {
      "validated_answer": "A valid employment contract requires: 1) Mutual consent between employer and employee, 2) Consideration (salary/benefits for work), 3) Legal capacity of both parties, 4) Written documentation for certain types of employment, 5) Compliance with employment standards legislation.",
      "position": "correct",
      "reasoning": "The AI response correctly identified the core requirements but could have been more specific about statutory requirements.",
      "legal_accuracy": "high",
      "citation_quality": "good",
      "omitted_articles": "Article 17 regarding probationary periods",
      "citation_corrections": "None required"
    }
  }'

# Submit feedback from different user (user_id: 2) for same response
curl -X POST "http://localhost:8000/responses/1/feedback/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 2,
    "accuracy_score": 7.5,
    "utility_score": 7.8,
    "transparency_score": 8.0,
    "feedback_data": {
      "validated_answer": "Employment contracts need mutual agreement, payment terms, and must follow labor laws.",
      "position": "partially_correct", 
      "reasoning": "The answer is too brief and misses important details about written requirements.",
      "legal_accuracy": "medium",
      "citation_quality": "fair"
    }
  }'

# Submit feedback for QA task (assuming response_id: 2)
curl -X POST "http://localhost:8000/responses/2/feedback/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "accuracy_score": 9.0,
    "utility_score": 8.5,
    "transparency_score": 8.8,
    "feedback_data": {
      "validated_answer": "The statute of limitations for breach of contract is typically 4-6 years for written contracts and 2-3 years for oral contracts, varying by jurisdiction.",
      "position": "correct",
      "reasoning": "Accurate general statement with appropriate caveats about jurisdictional variations.",
      "source_accuracy": "high",
      "completeness": "good"
    }
  }'

# Submit feedback for CLASSIFICATION task (assuming response_id: 3)
curl -X POST "http://localhost:8000/responses/3/feedback/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "accuracy_score": 8.0,
    "utility_score": 8.2,
    "transparency_score": 7.5,
    "feedback_data": {
      "validated_labels": ["Governing Law Clause", "Arbitration Clause"],
      "reasoning": "Text contains both governing law and dispute resolution provisions.",
      "confidence_per_label": {
        "Governing Law Clause": 0.95,
        "Arbitration Clause": 0.90
      },
      "missed_labels": "None"
    }
  }'
```

#### 3.2 Rate Feedback
```bash
# Rate feedback quality (feedback_id should be 1 from previous responses)
curl -X POST "http://localhost:8000/feedback/1/rate/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 2,
    "helpfulness_score": 4
  }'

curl -X POST "http://localhost:8000/feedback/2/rate/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 3,
    "helpfulness_score": 3
  }'
```

#### 3.3 View Feedback Data
```bash
# Get all feedback
curl "http://localhost:8000/feedback/all"

# Get all feedback ratings
curl "http://localhost:8000/feedback_ratings/all"
```

### Phase 4: Task Aggregation & Results

#### 4.1 Update Task Status to Trigger Aggregation
```bash
# Update task status to AGGREGATED (this triggers aggregation)
curl -X PUT "http://localhost:8000/tasks/1/status" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: supersecretkey" \
  -d '{
    "status": "AGGREGATED"
  }'
```

#### 4.2 Get Task Results
```bash
# Get aggregated results for task 1
curl "http://localhost:8000/tasks/1/result/"

# Expected: Uncertainty-preserving aggregation result with:
# - primary_answer
# - confidence_level  
# - alternative_positions
# - expert_disagreement
# - transparency_metrics
```

### Phase 5: Devil's Advocate System

#### 5.1 Check Devil's Advocate Assignments
```bash
# Check if devils advocates are assigned to task
curl "http://localhost:8000/tasks/1/devils-advocate"

# Get critical prompts for task type
curl "http://localhost:8000/devils-advocate/prompts/STATUTORY_RULE_QA"
```

### Phase 6: AI Service Integration

#### 6.1 Test AI Response Generation (if API key available)
```bash
# Generate AI response (requires OpenRouter API key)
curl -X POST "http://localhost:8000/ai/generate_response" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: supersecretkey" \
  -d '{
    "task_type": "STATUTORY_RULE_QA",
    "input_data": {
      "question": "What constitutes employment discrimination?",
      "context_full": "Employment discrimination involves unfair treatment based on protected characteristics."
    },
    "model_config": {
      "name": "openai/gpt-3.5-turbo",
      "api_key": "your-openrouter-api-key",
      "temperature": 0.7,
      "max_tokens": 1000
    }
  }'

# Get available AI models
curl "http://localhost:8000/ai/models"
```

### Phase 7: Configuration Management

#### 7.1 Configuration Endpoints
```bash
# Get current model configuration
curl "http://localhost:8000/config/model"

# Get task configuration
curl "http://localhost:8000/config/tasks"

# Update model configuration (requires admin key)
curl -X PUT "http://localhost:8000/config/model" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: supersecretkey" \
  -d '{
    "authority_weights": {
      "baseline_credentials": 0.25,
      "track_record": 0.55,
      "recent_performance": 0.2
    },
    "track_record": {
      "update_factor": 0.05
    },
    "thresholds": {
      "disagreement": 0.35
    }
  }'
```

### Phase 8: Data Export

#### 8.1 Export Dataset
```bash
# Export dataset in JSONL format
curl -X POST "http://localhost:8000/export/dataset" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: supersecretkey" \
  -d '{
    "task_type": "STATUTORY_RULE_QA", 
    "export_format": "sft"
  }' \
  --output exported_dataset.jsonl
```

### Phase 9: Analytics & Metrics

#### 9.1 System Analytics
```bash
# Get system metrics
curl "http://localhost:8000/analytics/system"

# Get user leaderboard
curl "http://localhost:8000/analytics/leaderboard?limit=10"

# Get task distribution
curl "http://localhost:8000/analytics/task_distribution"
```

### Phase 10: Database Viewer Endpoints

#### 10.1 Administrative Data Access
```bash
# View all data tables
curl "http://localhost:8000/users/all"
curl "http://localhost:8000/tasks/all"
curl "http://localhost:8000/credentials/all"
curl "http://localhost:8000/responses/all"
curl "http://localhost:8000/feedback/all"
curl "http://localhost:8000/feedback_ratings/all"
curl "http://localhost:8000/bias_reports/all"
curl "http://localhost:8000/assignments/all"
```

### Phase 11: Batch Operations & Advanced Features

#### 11.1 Batch Task Operations
```bash
# Create tasks from YAML
curl -X POST "http://localhost:8000/tasks/batch_from_yaml/" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: supersecretkey" \
  -d '{
    "yaml_content": "tasks:\n  - task_type: QA\n    input_data:\n      question: Sample question?\n      context: Sample context\n  - task_type: CLASSIFICATION\n    input_data:\n      text: Sample text\n      unit: document"
  }'

# Bulk update task status
curl -X POST "http://localhost:8000/tasks/bulk_update_status" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: supersecretkey" \
  -d '{
    "task_ids": [2, 3, 4],
    "status": "CLOSED"
  }'

# Bulk delete tasks
curl -X POST "http://localhost:8000/tasks/bulk_delete" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: supersecretkey" \
  -d '{
    "task_ids": [5, 6]
  }'
```

#### 11.2 CSV Upload Test
```bash
# Create a test CSV file
cat > test_tasks.csv << EOF
question,context_full,rule_id,relevant_articles,category
"What is contract consideration?","Consideration is essential for contract validity","contract_001","Article 10","Contract Law"
"Define negligence in tort law","Negligence requires duty, breach, causation, damages","tort_002","Article 25","Tort Law"
EOF

# Upload CSV
curl -X POST "http://localhost:8000/tasks/upload_csv/" \
  -H "X-API-KEY: supersecretkey" \
  -F "file=@test_tasks.csv" \
  -F "task_type=STATUTORY_RULE_QA"
```

## ✅ Validation Checklist

### Phase 1: User Management ✓
- [ ] Users created successfully with auto-incremented IDs
- [ ] Credentials added and authority scores updated
- [ ] User retrieval works (single and bulk)
- [ ] Bulk user creation works

### Phase 2: Task Management ✓
- [ ] Tasks created for each major type
- [ ] Task status defaulted to BLIND_EVALUATION
- [ ] AI responses generated (placeholder or real)
- [ ] Task filtering and pagination work
- [ ] Task assignment system works

### Phase 3: Feedback System ✓
- [ ] Feedback submitted with task-specific schemas
- [ ] Multiple users can provide feedback per task
- [ ] Feedback rating system works
- [ ] Data validation prevents invalid submissions

### Phase 4: Aggregation ✓
- [ ] Task status update triggers aggregation
- [ ] Uncertainty-preserving results generated
- [ ] Disagreement scores calculated
- [ ] Alternative positions identified

### Phase 5: Devil's Advocate ✓
- [ ] Assignment check works
- [ ] Critical prompts retrieved by task type

### Phase 6: AI Integration ✓
- [ ] Model list retrieved
- [ ] AI generation works (if API key provided)
- [ ] Fallback responses work without API key

### Phase 7: Configuration ✓
- [ ] Configuration retrieval works
- [ ] Configuration updates persist
- [ ] Admin authentication required

### Phase 8: Export ✓
- [ ] Dataset export generates valid JSONL
- [ ] Export includes proper metadata

### Phase 9: Analytics ✓
- [ ] System metrics calculated correctly
- [ ] Leaderboard shows authority rankings
- [ ] Task distribution accurate

### Phase 10: Administrative ✓
- [ ] All database viewer endpoints work
- [ ] Data consistency across tables

### Phase 11: Advanced Features ✓
- [ ] YAML batch import works
- [ ] CSV upload and conversion works
- [ ] Bulk operations execute successfully

## 🚨 Error Testing

Test these common error scenarios:

```bash
# Invalid user ID
curl "http://localhost:8000/users/999"
# Expected: 404 Not Found

# Invalid task type
curl -X POST "http://localhost:8000/tasks/" \
  -H "Content-Type: application/json" \
  -d '{"task_type": "INVALID_TYPE", "input_data": {}}'
# Expected: 422 Validation Error

# Missing API key for admin endpoint
curl -X PUT "http://localhost:8000/config/model" \
  -H "Content-Type: application/json" \
  -d '{}'
# Expected: 403 Forbidden

# Feedback on non-existent response
curl -X POST "http://localhost:8000/responses/999/feedback/" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "accuracy_score": 8.0, "utility_score": 8.0, "transparency_score": 8.0, "feedback_data": {}}'
# Expected: 404 Not Found
```

## 📊 Success Criteria

The system passes end-to-end testing if:

1. **All API endpoints respond correctly** with expected status codes
2. **Data persistence works** - created data can be retrieved
3. **Authority scores update** when credentials are added
4. **Aggregation produces results** with uncertainty preservation
5. **Export generates valid data** in expected formats
6. **Error handling works** for invalid inputs
7. **Authentication enforced** for admin endpoints
8. **Performance acceptable** for all operations

## 🛠️ Troubleshooting

### Common Issues:
- **Server not responding**: Check if uvicorn is running on port 8000
- **403 Forbidden**: Verify ADMIN_API_KEY environment variable
- **422 Validation Error**: Check request body matches expected schema
- **Empty responses**: Verify database has been initialized
- **AI generation fails**: OpenRouter API key not configured (expected for placeholder responses)

### Debug Commands:
```bash
# Check server logs
tail -f rlcf_detailed.log

# Verify database state
sqlite3 rlcf.db ".tables"
sqlite3 rlcf.db "SELECT * FROM users;"

# Check OpenAPI docs
curl "http://localhost:8000/openapi.json" | jq
```

---

**Total Testing Time**: Approximately 30-45 minutes for complete end-to-end testing
**Automation Potential**: All curl commands can be scripted for automated testing
