# REST API Endpoints

## Overview

The RLCF framework provides a comprehensive REST API for managing users, tasks, feedback, and system configuration. All endpoints support JSON request/response format and include detailed OpenAPI documentation.

**Note**: This documentation reflects the actual implementation as of Alpha 0.0.1. Some endpoints may require API key authentication for admin operations.

## Base URL

```
http://localhost:8000
```

## Authentication

### Admin Endpoints
Some endpoints require API key authentication:

```bash
curl -H "X-API-KEY: your-api-key" http://localhost:8000/admin/endpoint
```

Set the API key via environment variable:
```bash
export ADMIN_API_KEY=your-secret-key
```

## User Management

### Create User
```http
POST /users/
```

**Request Body:**
```json
{
  "username": "john_doe"
}
```

**Response:**
```json
{
  "id": 1,
  "username": "john_doe",
  "authority_score": 0.0,
  "track_record_score": 0.0,
  "baseline_credential_score": 0.0,
  "credentials": []
}
```

### Get User
```http
GET /users/{user_id}
```

**Response:**
```json
{
  "id": 1,
  "username": "john_doe",
  "authority_score": 0.75,
  "track_record_score": 0.8,
  "baseline_credential_score": 1.2,
  "credentials": []
}
```

**Note**: Credentials are returned as empty array to avoid async loading issues in current implementation.

### List All Users
```http
GET /users/all
```

**Response:**
```json
[
  {
    "id": 1,
    "username": "john_doe",
    "authority_score": 0.75,
    "track_record_score": 0.8,
    "baseline_credential_score": 1.2,
    "credentials": []
  }
]
```

### Add Credential to User
```http
POST /users/{user_id}/credentials/
```

**Request Body:**
```json
{
  "type": "ACADEMIC_DEGREE",
  "value": "JD",
  "weight": 0.3
}
```

**Response:** Returns updated User object.

### Bulk Create Users
```http
POST /users/bulk
```
**Requires API Key**

**Request Body:**
```json
{
  "usernames": ["user1", "user2", "user3"]
}
```

## Task Management

### Create Legal Task
```http
POST /tasks/
```

**Request Body:**
```json
{
  "task_type": "STATUTORY_RULE_QA",
  "input_data": {
    "question": "What are the requirements for contract formation?",
    "rule_id": "contract_law_001",
    "context_full": "Legal context here...",
    "context_count": 1,
    "relevant_articles": "Article 1, Article 2",
    "category": "Contract Law",
    "tags": "formation, requirements",
    "metadata_full": "{}"
  }
}
```

**Response:**
```json
{
  "id": 1,
  "task_type": "STATUTORY_RULE_QA",
  "input_data": {
    "question": "What are the requirements for contract formation?",
    "rule_id": "contract_law_001",
    "context_full": "Legal context here...",
    "context_count": 1,
    "relevant_articles": "Article 1, Article 2",
    "category": "Contract Law",
    "tags": "formation, requirements", 
    "metadata_full": "{}"
  },
  "ground_truth_data": null,
  "status": "BLIND_EVALUATION",
  "created_at": "2024-01-15T10:30:00Z",
  "responses": []
}
```

### Get Task Details
```http
GET /tasks/{task_id}
```

### List All Tasks
```http
GET /tasks/all?limit=50&status=BLIND_EVALUATION&task_type=QA&offset=0
```

**Query Parameters:**
- `limit` - Number of results
- `offset` - Pagination offset
- `status` - Filter by task status (OPEN, BLIND_EVALUATION, AGGREGATED, CLOSED)
- `task_type` - Filter by task type
- `user_id` - Filter by user ID

**Response:**
```json
[
  {
    "id": 1,
    "task_type": "STATUTORY_RULE_QA",
    "input_data": {...},
    "ground_truth_data": null,
    "status": "BLIND_EVALUATION",
    "created_at": "2024-01-15T10:30:00Z",
    "responses": []
  }
]
```

### Update Task
```http
PUT /tasks/{task_id}
```
**Requires API Key**

### Update Task Status (Admin)
```http
PUT /tasks/{task_id}/status
```
**Requires API Key**

**Request Body:**
```json
{
  "status": "AGGREGATED"
}
```

### Delete Task
```http
DELETE /tasks/{task_id}
```
**Requires API Key**

### Bulk Operations
```http
POST /tasks/bulk_delete
POST /tasks/bulk_update_status
```
**Requires API Key**

### Task Assignment
```http
POST /tasks/{task_id}/assign
GET /tasks/{task_id}/assignees
```
**Requires API Key**

### Batch Create from YAML
```http
POST /tasks/batch_from_yaml/
```
**Requires API Key**

**Request Body:**
```json
{
  "yaml_content": "tasks:\n  - task_type: QA\n    input_data:\n      question: ...\n      context: ..."
}
```

### CSV Upload
```http
POST /tasks/upload_csv/
```
**Requires API Key**

Upload CSV file with automatic task type detection and conversion.

### CSV to YAML Conversion
```http
POST /tasks/csv_to_yaml/
```
**Requires API Key**

Convert CSV to YAML format without creating tasks.

### Get Task Result
```http
GET /tasks/{task_id}/result/
```

**Response:**
```json
{
  "primary_answer": "Contract formation requires offer, acceptance, and consideration...",
  "confidence_level": 0.85,
  "alternative_positions": [
    {
      "position": "Alternative interpretation...",
      "support": "15.0%",
      "supporters": ["expert1", "expert2"],
      "reasoning": "Minority view based on..."
    }
  ],
  "expert_disagreement": {
    "consensus_areas": ["Offer and acceptance required"],
    "contention_points": [...],
    "reasoning_patterns": {...}
  },
  "transparency_metrics": {
    "evaluator_count": 5,
    "total_authority_weight": 3.2,
    "disagreement_score": 0.235
  }
}
```

## Feedback Management

### Submit Feedback
```http
POST /responses/{response_id}/feedback/
```

**Request Body:**
```json
{
  "user_id": 1,
  "accuracy_score": 8.5,
  "utility_score": 7.8,
  "transparency_score": 9.0,
  "feedback_data": {
    "validated_answer": "Corrected AI response...",
    "position": "partially_correct",
    "reasoning": "The AI response was mostly accurate but missed key details...",
    "legal_accuracy": "high",
    "citation_quality": "good"
  }
}
```

**Response:**
```json
{
  "id": 1,
  "user_id": 1,
  "response_id": 1,
  "is_blind_phase": true,
  "accuracy_score": 8.5,
  "utility_score": 7.8,
  "transparency_score": 9.0,
  "feedback_data": {
    "validated_answer": "Corrected AI response...",
    "position": "partially_correct",
    "reasoning": "The AI response was mostly accurate but missed key details...",
    "legal_accuracy": "high",
    "citation_quality": "good"
  },
  "community_helpfulness_rating": 0,
  "consistency_score": null,
  "correctness_score": null,
  "submitted_at": "2024-01-15T11:00:00Z"
}
```

### Rate Feedback
```http
POST /feedback/{feedback_id}/rate/
```

**Request Body:**
```json
{
  "user_id": 2,
  "helpfulness_score": 4
}
```

### List All Feedback (Database Viewer)
```http
GET /feedback/all
```

### List All Feedback Ratings
```http
GET /feedback_ratings/all
```

#TODO: Add endpoints for filtered feedback queries
#TODO: GET /feedback/task/{task_id} - Get all feedback for a specific task
#TODO: GET /feedback/user/{user_id} - Get all feedback from a specific user

## Configuration Management

### Get Current Model Configuration
```http
GET /config/model
```

**Response:**
```json
{
  "authority_weights": {
    "baseline_credentials": 0.3,
    "track_record": 0.5,
    "recent_performance": 0.2
  },
  "track_record": {
    "update_factor": 0.05
  },
  "thresholds": {
    "disagreement": 0.4
  },
  "baseline_credentials": {
    "types": {
      "ACADEMIC_DEGREE": {
        "weight": 0.3,
        "scoring_function": {
          "type": "map",
          "values": {
            "Bachelor": 1.0,
            "LLM": 1.1,
            "JD": 1.2,
            "PhD": 1.5
          },
          "default": 0.0
        }
      },
      "PROFESSIONAL_EXPERIENCE": {
        "weight": 0.4,
        "scoring_function": {
          "type": "formula",
          "expression": "0.5 + 0.2 * sqrt(value)",
          "default": 0.0
        }
      }
    }
  }
}
```

### Update Model Configuration
```http
PUT /config/model
```
**Requires API Key**

### Get Task Configuration
```http
GET /config/tasks
```

### Update Task Configuration
```http
PUT /config/tasks
```
**Requires API Key**

## Devil's Advocate System

### Get Advocate Assignments for Task
```http
GET /tasks/{task_id}/devils-advocate
```

**Response:**
```json
{
  "assigned": true,
  "advocates": [
    {
      "user_id": 5,
      "instructions": "Your role is to critically evaluate this response...",
      "assigned_at": "2024-01-15T09:00:00Z"
    }
  ],
  "count": 1
}
```

### Get Critical Prompts by Task Type
```http
GET /devils-advocate/prompts/{task_type}
```

**Response:**
```json
{
  "task_type": "STATUTORY_RULE_QA",
  "prompts": [
    "What are the potential weaknesses in this reasoning?",
    "Are there alternative interpretations that weren't considered?",
    "What important statutory nuances or exceptions are missing?"
  ],
  "count": 8
}
```

## AI Service Integration

### Generate AI Response
```http
POST /ai/generate_response
```
**Requires API Key**

**Request Body:**
```json
{
  "task_type": "STATUTORY_RULE_QA",
  "input_data": {
    "question": "What constitutes a valid contract?",
    "context_full": "Legal context..."
  },
  "model_config": {
    "name": "openai/gpt-4",
    "api_key": "sk-...",
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

**Response:**
```json
{
  "success": true,
  "response_data": {
    "answer": "A valid contract requires...",
    "confidence": "high",
    "reasoning": "Based on fundamental contract law principles...",
    "model_name": "openai/gpt-4"
  },
  "model_used": "openai/gpt-4"
}
```

### Get Available AI Models
```http
GET /ai/models
```

**Response:**
```json
{
  "models": [
    {
      "id": "openai/gpt-4",
      "name": "GPT-4",
      "description": "Most capable OpenAI model",
      "recommended_for": ["complex_legal_analysis", "statutory_interpretation"]
    },
    {
      "id": "anthropic/claude-3-sonnet",
      "name": "Claude 3 Sonnet", 
      "description": "Excellent for legal reasoning and analysis",
      "recommended_for": ["legal_reasoning", "risk_assessment", "drafting"]
    }
  ]
}
```

## Data Export

### Export Dataset (JSONL)
```http
POST /export/dataset
```
**Requires API Key**

**Request Body:**
```json
{
  "task_type": "STATUTORY_RULE_QA",
  "export_format": "sft"
}
```

Returns JSONL file for supervised fine-tuning or preference learning.

## Analytics & Metrics

### Get System Metrics
```http
GET /analytics/system
```

**Response:**
```json
{
  "totalTasks": 150,
  "totalUsers": 25,
  "totalFeedback": 450,
  "averageConsensus": 0.72,
  "activeEvaluations": 12,
  "completionRate": 0.85
}
```

### Get Leaderboard
```http
GET /analytics/leaderboard?limit=10
```

### Get Task Distribution
```http
GET /analytics/task_distribution
```

**Response:**
```json
{
  "STATUTORY_RULE_QA": 45,
  "QA": 38,
  "CLASSIFICATION": 25,
  "SUMMARIZATION": 18
}
```

## Database Viewer Endpoints

The following endpoints provide access to all data for debugging and administrative purposes:

- `GET /users/all` - All users
- `GET /tasks/all` - All tasks
- `GET /credentials/all` - All credentials
- `GET /responses/all` - All responses  
- `GET /feedback/all` - All feedback
- `GET /feedback_ratings/all` - All feedback ratings
- `GET /bias_reports/all` - All bias reports
- `GET /assignments/all` - All task assignments

## Missing Endpoints (TODO)

The following endpoints are referenced in research documentation but not yet implemented:

#TODO: Authority Management
#TODO: POST /authority/calculate/{user_id} - Calculate user authority score
#TODO: GET /authority/stats - Get authority statistics and distribution

#TODO: Aggregation & Analysis  
#TODO: POST /aggregation/run/{task_id} - Manually trigger task aggregation
#TODO: GET /aggregation/disagreement/{task_id} - Get disagreement analysis
#TODO: GET /bias/task/{task_id}/report - Get comprehensive bias report

#TODO: Advanced Export
#TODO: GET /export/tasks - Export tasks with filtering options
#TODO: GET /export/scientific - Export in academic publication format

## Error Handling

### Standard Error Response
```json
{
  "detail": "Error description",
  "error_code": "VALIDATION_ERROR", 
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Common HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `401` - Unauthorized
- `403` - Forbidden (API key required)
- `404` - Not Found
- `422` - Unprocessable Entity (schema validation)
- `500` - Internal Server Error

## Rate Limiting

API endpoints may be rate-limited in production:
- Standard endpoints: 100 requests/minute
- Admin endpoints: 50 requests/minute  
- AI generation endpoints: 10 requests/minute

## OpenAPI Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

**Next Steps:**
- [Data Schemas](schemas.md) - Request/response schema definitions
- [Authentication](authentication.md) - Detailed authentication setup