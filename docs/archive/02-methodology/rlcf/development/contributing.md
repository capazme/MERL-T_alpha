# Contributing to RLCF Framework

Thank you for your interest in contributing to the Reinforcement Learning from Community Feedback (RLCF) framework! This guide provides comprehensive information for researchers, developers, and domain experts who want to contribute to the project.

## Types of Contributions

### 🔬 Academic Research Contributions
- **Theoretical extensions**: New mathematical formulations or algorithmic improvements
- **Empirical studies**: Research papers using RLCF for legal AI evaluation
- **Comparative analyses**: Studies comparing RLCF with other alignment methods
- **Domain adaptations**: Extensions to non-legal domains

### 💻 Technical Contributions
- **Core algorithm improvements**: Performance optimizations or mathematical precision enhancements
- **New task handlers**: Support for additional legal task types
- **API enhancements**: New endpoints or improved functionality
- **Documentation improvements**: Code documentation, tutorials, or examples

### 📚 Documentation Contributions
- **Knowledge base updates**: Improvements to this documentation
- **Tutorial creation**: Step-by-step guides for specific use cases
- **Example scenarios**: Real-world usage examples and configurations
- **Translation**: Documentation in additional languages

### 🧪 Testing and Quality Assurance
- **Test coverage expansion**: Additional unit and integration tests
- **Bug reports**: Detailed issue reporting with reproducible examples
- **Performance testing**: Benchmarking and optimization opportunities
- **Security auditing**: Security analysis and vulnerability reporting

## Getting Started

### Development Environment Setup

1. **Fork and clone the repository**:
```bash
git clone https://github.com/your-username/RLCF.git
cd RLCF
```

2. **Create a development environment**:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

pip install -r requirements.txt
pip install -r dev-requirements.txt
```

3. **Verify installation**:
```bash
pytest tests/
uvicorn rlcf_framework.main:app --reload
```

### Project Structure

```
RLCF/
├── rlcf_framework/           # Core framework code
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── models.py            # Database models
│   ├── schemas.py           # Pydantic schemas
│   ├── authority_module.py   # Authority scoring algorithms
│   ├── aggregation_engine.py # Core aggregation logic
│   ├── bias_analysis.py     # Bias detection framework
│   ├── task_handlers/       # Task-specific logic
│   └── services/            # Business logic services
├── tests/                   # Test suite
├── docs/                    # Documentation (this folder)
├── frontend/                # React frontend (if applicable)
├── datasets/                # Example datasets
└── examples/                # Usage examples
```

## Contribution Guidelines

### Code Style

We follow strict coding standards to maintain academic-grade code quality:

#### Python Code Style

**Formatter**: Black (line length: 88 characters)
```bash
black .
```

**Linter**: Ruff for static analysis
```bash
ruff check . --fix
```

**Type Hints**: Required for all functions
```python
from typing import List, Dict, Optional, Tuple

async def calculate_authority_score(
    user_id: int, 
    recent_performance: float,
    db: AsyncSession
) -> Tuple[float, Dict[str, float]]:
    """
    Calculate user authority score with component breakdown.
    
    References:
        RLCF.md Section 2.1 - Dynamic Authority Scoring Model
    
    Args:
        user_id: Database ID of the user
        recent_performance: Current performance score [0.0, 1.0]
        db: Async database session
    
    Returns:
        Tuple of (new_authority_score, component_breakdown)
    """
    # Implementation here
    pass
```

#### Documentation Standards

**Academic References**: All functions must reference corresponding sections in RLCF.md
```python
def aggregate_with_uncertainty(feedbacks: List[Feedback]) -> AggregationResult:
    """
    Implements Algorithm 1 from RLCF.md Section 3.1.
    
    Mathematical Reference:
        δ = -(1/log|P|) Σ ρ(p)log ρ(p)
        where P is the set of distinct positions
    
    Constitutional Principle:
        Preserved Uncertainty (Incertitudo Conservata)
    """
```

**Mathematical Precision**: Include formula references
```python
# Formula from RLCF.md Section 2.1: A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)
new_authority = (
    weights["baseline_credentials"] * baseline_score +
    weights["track_record"] * track_record +
    weights["recent_performance"] * recent_performance
)
```

### Testing Requirements

#### Unit Test Coverage
All new code must include comprehensive unit tests:

```python
# tests/test_authority_module.py
import pytest
from unittest.mock import AsyncMock
from rlcf_framework.authority_module import calculate_authority_score

@pytest.mark.asyncio
async def test_authority_score_calculation_basic():
    """Test basic authority score calculation with known inputs."""
    mock_db = AsyncMock()
    
    # Test data with expected mathematical result
    user_id = 1
    recent_performance = 0.8
    expected_authority = 0.3 * 1.2 + 0.5 * 0.7 + 0.2 * 0.8  # α·B + β·T + γ·P
    
    result = await calculate_authority_score(user_id, recent_performance, mock_db)
    
    assert abs(result[0] - expected_authority) < 0.001
    assert "baseline_credentials" in result[1]
    assert "track_record" in result[1]
    assert "recent_performance" in result[1]

@pytest.mark.asyncio
async def test_authority_score_edge_cases():
    """Test edge cases and boundary conditions."""
    # Test with zero values
    # Test with maximum values
    # Test with invalid inputs
    pass
```

#### Integration Tests
Test complete workflows:

```python
@pytest.mark.asyncio
async def test_complete_task_evaluation_workflow():
    """Test full task evaluation from creation to aggregation."""
    # Create task
    # Submit multiple feedback items
    # Run aggregation
    # Verify results match expected mathematical outcomes
    pass
```

#### Academic Validation Tests
Verify mathematical implementations:

```python
def test_shannon_entropy_calculation():
    """Verify disagreement calculation matches mathematical definition."""
    positions = {"position_a": 0.7, "position_b": 0.3}
    calculated_entropy = calculate_disagreement(positions)
    
    # Manual calculation of normalized Shannon entropy
    p_a, p_b = 0.7, 0.3
    expected_entropy = -(p_a * np.log(p_a) + p_b * np.log(p_b)) / np.log(2)
    
    assert abs(calculated_entropy - expected_entropy) < 0.001
```

### Commit Message Format

Use conventional commit format for clear history:

```
type(scope): brief description

Detailed explanation of what and why, not how.

Mathematical/Academic Context:
- References RLCF.md Section X.Y
- Implements formula Z
- Addresses constitutional principle W

Breaking Change: [if applicable]
```

**Types**:
- `feat`: New feature or algorithm
- `fix`: Bug fix or correction
- `docs`: Documentation changes
- `test`: Test additions or modifications
- `refactor`: Code reorganization without behavior change
- `perf`: Performance improvements
- `academic`: Academic paper or research updates

**Examples**:
```
feat(authority): implement baseline credentials with safe formula evaluation

Add configurable credential scoring system using asteval for security.
Supports both discrete mappings and mathematical formulas as defined
in model_config.yaml.

Mathematical Context:
- Implements B_u = Σ(w_i · f_i(c_{u,i})) from RLCF.md Section 2.2
- Supports safe evaluation of user-defined scoring functions
- Maintains constitutional compliance with transparency principle

feat(aggregation): add uncertainty-preserving output generation

Implements structured output for high-disagreement scenarios with
alternative positions and reasoning analysis.

Academic Context:
- References RLCF.md Section 3.3 - Uncertainty-Preserving Output Structure
- Supports Principle of Preserved Uncertainty (Incertitudo Conservata)
- Enables dialectical preservation in legal reasoning
```

## Research Contribution Process

### Academic Paper Integration

1. **Theoretical Contributions**:
   - Submit mathematical proofs or extensions as issues
   - Include formal mathematical notation
   - Reference existing literature
   - Propose implementation approach

2. **Empirical Studies**:
   - Share experimental designs and hypotheses
   - Provide anonymized datasets when possible
   - Include statistical analysis code
   - Document replication procedures

3. **Peer Review Process**:
   - All mathematical changes reviewed by academic contributors
   - Code review for implementation correctness
   - Constitutional compliance validation
   - Performance impact assessment

### Publication Guidelines

**Open Access Commitment**:
- All research using RLCF should be published in open access venues
- Share preprints for community review
- Provide supplementary materials for reproducibility

**Citation Requirements**:
```bibtex
@article{rlcf2024,
  title={Reinforcement Learning from Community Feedback: A Novel Framework for Artificial Legal Intelligence},
  author={[Authors]},
  journal={[Journal]},
  year={2024},
  note={Framework implementation available at: https://github.com/[repo]}
}
```

**Data Sharing**:
- Anonymized datasets encouraged for replication
- Configuration files must be shared
- Statistical analysis code should be public

## Technical Contribution Process

### Algorithm Improvements

1. **Mathematical Validation**:
   - Provide mathematical proof or justification
   - Include convergence analysis where applicable
   - Demonstrate constitutional compliance
   - Show performance characteristics

2. **Implementation Requirements**:
   - Maintain API compatibility
   - Include comprehensive tests
   - Document performance implications
   - Preserve academic referencing

3. **Review Process**:
   - Academic review for mathematical correctness
   - Technical review for implementation quality
   - Performance benchmarking
   - Constitutional framework validation

### New Task Handler Development

Template for new task handlers:

```python
from .base import BaseTaskHandler
from typing import Dict, Any

class NewTaskHandler(BaseTaskHandler):
    """
    Handler for [TASK_TYPE] legal tasks.
    
    Implements domain-specific aggregation logic for [legal domain]
    following the Strategy pattern from RLCF.md Section 3.6.
    
    Academic Context:
        - Supports [specific legal reasoning type]
        - Optimized for [legal domain characteristics]
        - Addresses [specific challenges in legal AI]
    """
    
    async def aggregate_feedback(self) -> Dict[str, Any]:
        """
        Aggregate feedback with domain-specific logic.
        
        Returns:
            Dict containing consensus and uncertainty information
        """
        # Implementation specific to new task type
        pass
    
    def calculate_consistency(self, feedback: Feedback, result: Dict) -> float:
        """
        Calculate consistency with domain-specific metrics.
        
        Args:
            feedback: Individual feedback item
            result: Aggregated consensus result
            
        Returns:
            Consistency score [0.0, 1.0]
        """
        # Domain-specific consistency calculation
        pass
```

### Performance Optimization Guidelines

1. **Async/Await Usage**:
   - All database operations must be async
   - Use proper async context managers
   - Avoid blocking operations in async functions

2. **Database Optimization**:
   - Use efficient query patterns
   - Implement proper indexing
   - Consider query result caching

3. **Mathematical Efficiency**:
   - Use numpy for numerical computations
   - Profile mathematical operations
   - Consider approximation algorithms for large datasets

## Issue Reporting

### Bug Reports

Use this template for bug reports:

```markdown
## Bug Description
Brief description of the issue

## Mathematical Context
- Which algorithm or formula is affected?
- Reference to RLCF.md section
- Constitutional principle implications

## Reproduction Steps
1. Configuration used
2. Input data
3. Expected mathematical result
4. Actual result

## Environment
- Python version
- Package versions
- Operating system

## Academic Impact
- Does this affect research reproducibility?
- Potential impact on published results
```

### Feature Requests

```markdown
## Academic Motivation
Why is this feature needed for research?

## Mathematical Foundation
- Theoretical basis for the feature
- References to academic literature
- Proposed mathematical formulation

## Implementation Approach
High-level implementation strategy

## Constitutional Compliance
How does this align with RLCF principles?

## Research Applications
Example use cases in academic research
```

## Review Process

### Code Review Checklist

**Mathematical Accuracy**:
- [ ] Formulas match RLCF.md specifications exactly
- [ ] Edge cases and boundary conditions handled
- [ ] Numerical stability considerations
- [ ] Constitutional principle compliance

**Code Quality**:
- [ ] Type hints for all functions
- [ ] Comprehensive docstrings with academic references
- [ ] Unit tests with >90% coverage
- [ ] Integration tests for workflows

**Academic Standards**:
- [ ] Proper citation of theoretical foundations
- [ ] Reproducible experimental procedures
- [ ] Clear documentation for peer review
- [ ] Performance characteristics documented

### Merge Requirements

All contributions must meet these requirements before merging:

1. **Passing CI/CD**:
   - All tests pass
   - Code formatting (Black)
   - Linting (Ruff)
   - Type checking (mypy)

2. **Academic Review**:
   - Mathematical correctness verified
   - Constitutional compliance confirmed
   - Academic documentation complete

3. **Technical Review**:
   - Code quality standards met
   - Performance impact assessed
   - API compatibility maintained

## Recognition and Attribution

### Contributor Recognition

- Contributors listed in project README
- Academic contributors included in research paper acknowledgments
- Significant algorithmic contributions warrant co-authorship consideration

### Academic Credit

- Theoretical contributions: Academic paper co-authorship
- Substantial code contributions: Software paper authorship
- Documentation improvements: Acknowledgment in publications

## Community Guidelines

### Academic Collaboration

- Respect for diverse theoretical perspectives
- Constructive peer review practices
- Open sharing of research results
- Collaborative problem-solving approach

### Professional Conduct

- Respectful communication in all interactions
- Acknowledgment of intellectual contributions
- Transparency about potential conflicts of interest
- Commitment to reproducible research practices

---

**Ready to Contribute?**

1. Join our community discussions
2. Review the [Quick Start Guide](../guides/quick-start.md)
3. Explore [Research Scenarios](../examples/configurations/research-scenarios.yaml)
4. Check current [Issues](https://github.com/[repo]/issues) for contribution opportunities

Thank you for helping advance the field of AI alignment for legal reasoning!
