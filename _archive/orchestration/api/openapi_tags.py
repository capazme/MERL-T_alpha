"""
OpenAPI Tags Metadata for MERL-T API

Defines comprehensive metadata for API endpoint tags including:
- Detailed descriptions
- External documentation links
- Use case explanations

Author: Week 9 Implementation
Date: November 2025
"""

from typing import List, Dict, Any


# OpenAPI tags with enhanced metadata
OPENAPI_TAGS_METADATA: List[Dict[str, Any]] = [
    {
        "name": "Query Execution",
        "description": """
Execute legal queries through the complete MERL-T pipeline.

The Query Execution endpoints provide the core functionality of MERL-T, allowing users to:
- Submit legal questions in natural language (Italian)
- Track query execution in real-time
- Retrieve complete results with legal reasoning
- Access query history for analysis

### Pipeline Stages

Each query flows through these stages:
1. **Preprocessing**: Query understanding, NER, intent classification
2. **Routing**: LLM Router generates execution plan
3. **Retrieval**: Knowledge Graph, API, and Vector DB retrieval
4. **Reasoning**: 4 expert agents analyze from different perspectives
5. **Synthesis**: Combine expert opinions into final answer
6. **Iteration**: Multi-turn refinement if needed

### Use Cases

- **Legal research**: "Quali sono i requisiti per la cittadinanza italiana?"
- **Compliance checks**: "Il mio contratto rispetta il GDPR?"
- **Jurisprudence lookup**: "Quali sentenze riguardano l'art. 1372 c.c.?"
- **Doctrine analysis**: "Cosa dice la dottrina sulla responsabilità precontrattuale?"

### Response Format

Queries return comprehensive answers including:
- Primary answer with confidence score
- Legal basis (norms, articles, jurisprudence)
- Alternative interpretations
- Uncertainty preservation (when experts disagree)
- Sources consulted
- Execution trace for transparency
        """.strip(),
        "externalDocs": {
            "description": "MERL-T Architecture Documentation",
            "url": "https://github.com/ALIS-ai/MERL-T/blob/main/docs/03-architecture/02-orchestration-layer.md"
        }
    },
    {
        "name": "Feedback",
        "description": """
Submit feedback to improve MERL-T through community validation.

The Feedback system implements **RLCF (Reinforcement Learning from Community Feedback)**,
a novel approach for aligning legal AI with expert knowledge.

### Feedback Types

**1. User Feedback**
- Rate answer quality (1-5 stars)
- Report issues (incorrect, incomplete, irrelevant)
- Suggest improvements
- Provide corrections

**2. RLCF Expert Feedback**
- Expert validation of AI responses
- Authority-weighted voting system
- Uncertainty preservation (disagreement is valuable)
- Corrections with legal references

**3. NER Corrections**
- Fix entity recognition errors
- Improve legal entity extraction
- Train NER model with corrections
- 4 correction types: missing, spurious, wrong boundary, wrong type

### Authority Scoring

RLCF uses dynamic authority scores based on:
- **Base Authority** (α): Professional credentials, experience
- **Temporal Authority** (β): Recent accuracy of feedback
- **Performance Authority** (γ): Historical success rate

Formula: `A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)`

### Feedback Loop

1. User/Expert submits feedback
2. System weights by authority score
3. Aggregation preserves uncertainty
4. Model fine-tuning (periodic)
5. Continuous improvement

### Impact

Your feedback directly improves:
- Answer quality
- Legal reasoning accuracy
- Entity recognition
- Query understanding
- Expert model performance
        """.strip(),
        "externalDocs": {
            "description": "RLCF Methodology",
            "url": "https://github.com/ALIS-ai/MERL-T/blob/main/docs/02-methodology/rlcf/RLCF.md"
        }
    },
    {
        "name": "Statistics & Analytics",
        "description": """
Access system performance metrics and usage analytics.

The Statistics endpoints provide comprehensive insights into:
- Pipeline performance (latency, success rate)
- Expert model usage and accuracy
- Feedback statistics and trends
- System health and reliability

### Pipeline Statistics

Monitor MERL-T performance:
- **Total queries**: Processed since deployment
- **Success rate**: Percentage of successful executions
- **Average latency**: Per pipeline stage
- **Expert usage**: Which experts are most utilized
- **Intent distribution**: Types of queries received

### Feedback Statistics

Track community engagement:
- **Total feedback**: User and RLCF submissions
- **Average ratings**: Answer quality metrics
- **Issue reports**: Common problems identified
- **NER corrections**: Entity recognition improvements
- **Expert participation**: RLCF expert activity

### Use Cases

- **System monitoring**: Track performance over time
- **Capacity planning**: Understand usage patterns
- **Quality assurance**: Identify areas for improvement
- **Research**: Analyze legal query trends
- **Reporting**: Generate usage reports for stakeholders

### Metrics Breakdown

**Stage Performance:**
- Preprocessing: query understanding, NER, KG enrichment
- Routing: LLM Router decision time
- Retrieval: KG, API, VectorDB latency
- Reasoning: Expert analysis time
- Synthesis: Opinion aggregation time
- Iteration: Multi-turn refinement time

**Expert Statistics:**
- Usage count per expert type
- Average confidence scores
- Agreement/disagreement rates
- Execution time distribution
        """.strip(),
        "externalDocs": {
            "description": "MERL-T Performance Metrics",
            "url": "https://github.com/ALIS-ai/MERL-T/blob/main/docs/04-implementation/monitoring.md"
        }
    },
    {
        "name": "System",
        "description": """
System health and informational endpoints.

Basic endpoints for system status monitoring and API information.

### Endpoints

- **Root (/)**: API welcome with version and features
- **Health (/health)**: Component health check

### Health Check

The `/health` endpoint verifies:
- ✅ API server status
- ✅ Database connectivity (PostgreSQL)
- ✅ Cache availability (Redis)
- ✅ LLM service status
- ✅ Overall system health

Returns HTTP 200 if all components healthy, 503 if any component fails.

### Use Cases

- **Monitoring**: Automated health checks
- **Load balancer**: Readiness probes
- **Deployment**: Verify successful deployment
- **Debugging**: Identify failing components
        """.strip(),
        "externalDocs": {
            "description": "Health Check Documentation",
            "url": "https://github.com/ALIS-ai/MERL-T/blob/main/docs/04-implementation/health-checks.md"
        }
    }
]


def get_tags_metadata() -> List[Dict[str, Any]]:
    """
    Get OpenAPI tags metadata.

    Returns:
        List of tag metadata dictionaries with name, description, and externalDocs.
    """
    return OPENAPI_TAGS_METADATA


# Servers configuration for different environments
SERVERS_CONFIG: List[Dict[str, str]] = [
    {
        "url": "http://localhost:8000",
        "description": "Development server (local)"
    },
    {
        "url": "http://localhost:8080",
        "description": "Development server (Docker)"
    },
    {
        "url": "https://staging-api.merl-t.alis.ai",
        "description": "Staging environment"
    },
    {
        "url": "https://api.merl-t.alis.ai",
        "description": "Production environment"
    }
]


def get_servers_config() -> List[Dict[str, str]]:
    """
    Get servers configuration for OpenAPI schema.

    Returns:
        List of server configurations (URL + description).
    """
    return SERVERS_CONFIG


# Terms of Service
TERMS_OF_SERVICE_URL = "https://alis.ai/terms"


# External documentation
EXTERNAL_DOCS = {
    "description": "Complete MERL-T Documentation",
    "url": "https://github.com/ALIS-ai/MERL-T"
}


def get_external_docs() -> Dict[str, str]:
    """
    Get external documentation configuration.

    Returns:
        Dictionary with description and URL for external docs.
    """
    return EXTERNAL_DOCS
