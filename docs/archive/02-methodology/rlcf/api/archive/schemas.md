# Data Schemas

This document describes the data structures used throughout the RLCF API. All schemas are defined using Pydantic models for automatic validation and documentation generation.

**Last Updated**: Alpha 0.0.1 Release  
**Schema Version**: 1.0.0  
**Status**: Aligned with actual implementation

## User Management Schemas

### User
```json
{
  "id": 1,
  "username": "string",
  "authority_score": 0.75,
  "track_record_score": 0.8,
  "baseline_credential_score": 1.2,
  "credentials": []
}
```

**Field Descriptions:**
- `id`: Unique user identifier (auto-generated)
- `username`: Unique username (required)
- `authority_score`: Current authority score [0.0, 2.0+] (auto-calculated)
- `track_record_score`: Historical performance [0.0, 1.0] (auto-calculated)
- `baseline_credential_score`: Credential-based score [0.0, 2.0+] (auto-calculated)
- `credentials`: List of user credentials (empty in API responses to avoid lazy loading)

### UserCreate
```json
{
  "username": "string"
}
```

**Field Validation:**
- `username`: Must be unique, non-empty string

**Note**: Authority scores are auto-calculated, not provided during creation.

### Credential
```json
{
  "id": 1,
  "user_id": 1,
  "type": "ACADEMIC_DEGREE",
  "value": "JD",
  "weight": 0.3
}
```

**Credential Types:**
- `ACADEMIC_DEGREE`: Bachelor, LLM, JD, PhD
- `PROFESSIONAL_EXPERIENCE`: Years of experience (numeric string)
- `PUBLICATION`: Number of publications (numeric string)
- `INSTITUTIONAL_ROLE`: Junior, Senior, Partner
- `PROFESSIONAL_FIELD`: Area of specialization

### CredentialCreate
```json
{
  "type": "ACADEMIC_DEGREE",
  "value": "JD",
  "weight": 0.3
}
```

**Field Validation:**
- `type`: Must be valid credential type
- `value`: String value corresponding to credential type
- `weight`: Float value for credential importance

## Task Management Schemas

### LegalTask
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
  "created_at": "2024-01-15T10:30:00Z",
  "status": "BLIND_EVALUATION",
  "responses": []
}
```

**Task Types:**
- `STATUTORY_RULE_QA`: Statutory rule question answering
- `QA`: General question answering
- `CLASSIFICATION`: Document classification
- `SUMMARIZATION`: Document summarization
- `PREDICTION`: Outcome prediction
- `NLI`: Natural language inference
- `NER`: Named entity recognition
- `DRAFTING`: Legal drafting
- `RISK_SPOTTING`: Compliance risk spotting
- `DOCTRINE_APPLICATION`: Legal doctrine application

**Task Status:**
- `OPEN`: Newly created, not yet in evaluation
- `BLIND_EVALUATION`: Currently being evaluated by experts
- `AGGREGATED`: Evaluation complete, results aggregated
- `CLOSED`: Task completed and finalized

### LegalTaskCreate
```json
{
  "task_type": "STATUTORY_RULE_QA",
  "input_data": {
    "question": "string",
    "rule_id": "string",
    "context_full": "string",
    "context_count": 1,
    "relevant_articles": "string",
    "category": "string",
    "tags": "string",
    "metadata_full": "string"
  }
}
```

**Input Data Schemas by Task Type:**

#### STATUTORY_RULE_QA
```json
{
  "question": "string (required)",
  "rule_id": "string (required)",
  "context_full": "string (required)",
  "context_count": "integer (required)",
  "relevant_articles": "string (required)",
  "category": "string (required)",
  "tags": "string (required)",
  "metadata_full": "string (required)"
}
```

#### QA
```json
{
  "question": "string (required)",
  "context": "string (required)"
}
```

#### CLASSIFICATION
```json
{
  "text": "string (required)",
  "unit": "string (required)"
}
```

#### SUMMARIZATION
```json
{
  "document": "string (required)"
}
```

### TaskStatusUpdate
```json
{
  "status": "AGGREGATED"
}
```

## Response Management Schemas

### Response
```json
{
  "id": 1,
  "task_id": 1,
  "output_data": {
    "message": "AI response placeholder",
    "task_type": "STATUTORY_RULE_QA",
    "is_placeholder": true
  },
  "model_version": "placeholder-1.0",
  "generated_at": "2024-01-15T10:30:00Z",
  "feedback": []
}
```

**Field Descriptions:**
- `output_data`: Flexible JSON containing AI-generated response
- `model_version`: Version/name of the model that generated the response
- `feedback`: List of feedback objects (empty in API responses)

## Feedback Management Schemas

### Feedback
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
    "validated_answer": "Corrected response...",
    "position": "partially_correct",
    "reasoning": "The response was mostly accurate but...",
    "legal_accuracy": "high",
    "citation_quality": "good"
  },
  "community_helpfulness_rating": 0,
  "consistency_score": null,
  "correctness_score": null,
  "submitted_at": "2024-01-15T11:00:00Z"
}
```

### FeedbackCreate
```json
{
  "user_id": 1,
  "accuracy_score": 8.5,
  "utility_score": 7.8,
  "transparency_score": 9.0,
  "feedback_data": {
    "validated_answer": "string",
    "position": "correct|partially_correct|incorrect",
    "reasoning": "string",
    "legal_accuracy": "high|medium|low",
    "citation_quality": "good|fair|poor"
  },
  "metadata": null
}
```

**Feedback Data Schemas by Task Type:**

#### STATUTORY_RULE_QA
```json
{
  "validated_answer": "string (required)",
  "position": "string (required)",
  "reasoning": "string (required)",
  "legal_accuracy": "string (required)",
  "citation_quality": "string (required)",
  "omitted_articles": "string (optional)",
  "citation_corrections": "string (optional)"
}
```

#### QA
```json
{
  "validated_answer": "string (required)",
  "position": "string (required)",
  "reasoning": "string (required)",
  "source_accuracy": "string (required)",
  "completeness": "string (required)"
}
```

#### CLASSIFICATION
```json
{
  "validated_labels": ["string"] (required),
  "reasoning": "string (required)",
  "confidence_per_label": {"label": 0.9} (required),
  "missed_labels": "string (optional)"
}
```

### FeedbackRating
```json
{
  "id": 1,
  "user_id": 2,
  "feedback_id": 1,
  "helpfulness_score": 4,
  "created_at": "2024-01-15T11:30:00Z"
}
```

### FeedbackRatingCreate
```json
{
  "user_id": 2,
  "helpfulness_score": 4
}
```

**Field Validation:**
- `helpfulness_score`: Integer from 1 to 5

## Configuration Schemas

### ModelConfig
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

### TaskConfig
```json
{
  "task_types": {
    "QA": {
      "input_data": {
        "question": "str",
        "context": "str"
      },
      "feedback_data": {
        "validated_answer": "str",
        "position": "str",
        "reasoning": "str"
      },
      "ground_truth_keys": ["validated_answer"]
    }
  }
}
```

## Assignment & Administrative Schemas

### TaskAssignment
```json
{
  "id": 1,
  "task_id": 1,
  "user_id": 1,
  "role": "evaluator",
  "assigned_at": "2024-01-15T09:00:00Z"
}
```

### TaskAssignmentCreate
```json
{
  "user_id": 1,
  "role": "evaluator"
}
```

### BiasReport
```json
{
  "id": 1,
  "task_id": 1,
  "user_id": 1,
  "bias_type": "PROFESSIONAL_CLUSTERING",
  "bias_score": 0.23,
  "calculated_at": "2024-01-15T12:00:00Z"
}
```

## Export Schemas

### ExportRequest
```json
{
  "task_type": "STATUTORY_RULE_QA",
  "export_format": "sft"
}
```

**Export Formats:**
- `sft`: Supervised Fine-Tuning format
- `preference`: Preference learning format

## Analytics Schemas

### SystemMetrics
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

## Bulk Operations Schemas

### BulkUserCreate
```json
{
  "usernames": ["user1", "user2", "user3"]
}
```

### YamlContentRequest
```json
{
  "yaml_content": "tasks:\n  - task_type: QA\n    input_data:\n      question: ...\n      context: ..."
}
```

## AI Service Schemas

### AIModelConfig
```json
{
  "name": "openai/gpt-4",
  "api_key": "sk-...",
  "temperature": 0.7,
  "max_tokens": 1000
}
```

## Validation Rules

### General Rules
- All timestamps are in ISO 8601 format
- All IDs are positive integers
- All scores are floats between 0.0 and specified maximum
- All enum values must match exactly (case-sensitive)

### String Limits
- Usernames: 3-50 characters
- Feedback reasoning: 10-5000 characters
- Task questions: 10-2000 characters

### Score Ranges
- Authority scores: 0.0 to 2.0+ (unlimited upper bound)
- Feedback scores: 0.0 to 10.0
- Confidence scores: 0.0 to 1.0
- Helpfulness ratings: 1 to 5 (integer)

## Error Response Schema

```json
{
  "detail": "Error description",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Common Error Codes:**
- `VALIDATION_ERROR`: Schema validation failed
- `NOT_FOUND`: Resource not found
- `PERMISSION_DENIED`: API key required
- `CONFLICT`: Duplicate resource
- `INTERNAL_ERROR`: Server error

---

**Note**: All schemas are automatically validated by Pydantic. The actual implementation may include additional computed fields or omit certain fields for performance reasons (e.g., empty credential lists to avoid lazy loading).