# Quick Start Guide

This guide will get you up and running with the RLCF framework in 15 minutes.

## Prerequisites

- Python 3.8 or higher
- Node.js 18+ and npm (for frontend)
- Git
- Basic familiarity with REST APIs and React

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd RLCF
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Activate on Linux/Mac
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the Backend API Server

```bash
uvicorn rlcf_framework.main:app --reload
```

The API will be available at `http://localhost:8000`

### 5. Start the Frontend (Optional)

For the full web interface experience:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`

## First Steps

### 1. Verify Installation

Open your browser and navigate to:
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

You should see the interactive OpenAPI documentation.

### 2. Create Your First User

```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "researcher_001",
    "authority_score": 0.5,
    "track_record_score": 0.5,
    "baseline_credential_score": 0.0
  }'
```

**Response:**
```json
{
  "id": 1,
  "username": "researcher_001",
  "authority_score": 0.5,
  "track_record_score": 0.5,
  "baseline_credential_score": 0.0,
  "credentials": []
}
```

### 3. Add Academic Credentials

```bash
curl -X POST "http://localhost:8000/users/1/credentials/" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "ACADEMIC_DEGREE",
    "value": "JD",
    "verified": true
  }'
```

### 4. Create Your First Legal Task

```bash
curl -X POST "http://localhost:8000/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "QA",
    "input_data": {
      "context": "Contract law requires offer, acceptance, and consideration for formation.",
      "question": "What are the three essential elements of contract formation?"
    }
  }'
```

**Response:**
```json
{
  "id": 1,
  "task_type": "QA",
  "input_data": {
    "context": "Contract law requires offer, acceptance, and consideration for formation.",
    "question": "What are the three essential elements of contract formation?"
  },
  "status": "BLIND_EVALUATION",
  "created_at": "2024-01-15T10:30:00Z",
  "responses": [
    {
      "id": 1,
      "output_data": {
        "message": "The three essential elements are: offer, acceptance, and consideration..."
      }
    }
  ]
}
```

### 5. Submit Feedback on the AI Response

```bash
curl -X POST "http://localhost:8000/feedback/" \
  -H "Content-Type: application/json" \
  -d '{
    "response_id": 1,
    "user_id": 1,
    "feedback_data": {
      "validated_answer": "The three essential elements of contract formation are: (1) offer, (2) acceptance, and (3) consideration.",
      "position": "correct",
      "reasoning": "The AI response correctly identified all three elements required for contract formation under traditional contract law doctrine."
    }
  }'
```

### 6. Run Aggregation and See Results

```bash
curl -X POST "http://localhost:8000/aggregation/run/1"
```

**Response:**
```json
{
  "task_id": 1,
  "aggregation_result": {
    "primary_answer": "The three essential elements are offer, acceptance, and consideration",
    "confidence_level": 0.95,
    "disagreement_score": 0.1
  },
  "bias_analysis": {
    "total_bias_score": 0.15,
    "bias_level": "low"
  }
}
```

## Understanding the Output

### Authority Score Calculation
Your user's authority score is calculated using:
- **Baseline Credentials** (30%): Academic degrees, experience
- **Track Record** (50%): Historical performance over time  
- **Recent Performance** (20%): Current evaluation quality

### Aggregation Results
- **Primary Answer**: Community consensus response
- **Confidence Level**: How certain the community is (1 - disagreement)
- **Disagreement Score**: Normalized Shannon entropy of positions

### Bias Analysis
The system automatically detects six types of bias:
- Demographic correlation
- Professional clustering
- Temporal drift
- Geographic concentration
- Confirmation bias
- Anchoring bias

## What's Next?

### For Researchers
1. Read the [Academic Research Guide](academic-research.md)
2. Explore [Research Scenarios](../examples/research-scenarios/)
3. Review the [Mathematical Framework](../theoretical/mathematical-framework.md)

### For Developers
1. Check the [System Architecture](../technical/architecture.md)
2. Review [API Endpoints](../api/endpoints.md)
3. Study [Task Handler System](../technical/task-handlers.md)

### For Advanced Users
1. Configure authority weights in [Configuration Guide](configuration.md)
2. Set up custom task types with [Custom Tasks Tutorial](../tutorials/custom-tasks.md)
3. Deploy using [Installation Guide](installation.md)

## Common Tasks

### View All Tasks
```bash
curl "http://localhost:8000/tasks/all?limit=10"
```

### Check User Authority Statistics
```bash
curl "http://localhost:8000/authority/stats"
```

### Export Data for Analysis
```bash
curl "http://localhost:8000/export/tasks?format=csv" > tasks.csv
```

### Get Configuration
```bash
curl "http://localhost:8000/config/model"
```

## Troubleshooting

### Server Won't Start
- Check Python version: `python --version`
- Verify dependencies: `pip list`
- Check logs for error messages

### API Calls Fail
- Ensure server is running on port 8000
- Check request Content-Type headers
- Validate JSON syntax

### Database Issues
- Database is automatically created on first startup
- Check file permissions in project directory
- Review logs in `rlcf_detailed.log`

## Getting Help

- **Documentation**: Browse the full [docs folder](../README.md)
- **API Reference**: Interactive docs at http://localhost:8000/docs
- **Examples**: Check [examples folder](../examples/)
- **Troubleshooting**: See [troubleshooting guide](../reference/troubleshooting.md)

## Optional: Gradio Interface

For a graphical interface, you can also run:

```bash
python app_interface.py
```

This provides a web UI at http://localhost:7860 for easier interaction with the system.

---

**Congratulations!** You've successfully set up and tested the RLCF framework. You're ready to start exploring advanced features and conducting legal AI research.
