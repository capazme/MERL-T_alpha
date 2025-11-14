# Contributing to MERL-T

First off, thank you for considering contributing to MERL-T! It's people like you that make MERL-T such a great tool for the legal AI community.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)
- [Testing](#testing)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

This project and everyone participating in it is governed by the [MERL-T Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [support@alis.ai](mailto:support@alis.ai).

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the [existing issues](https://github.com/ALIS-ai/MERL-T/issues) to avoid duplicates.

When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples** (code snippets, error messages)
- **Describe the behavior you observed** and what you expected
- **Include screenshots** if relevant
- **Note your environment** (OS, Python version, Docker version)

### Suggesting Enhancements

Enhancement suggestions are tracked as [GitHub issues](https://github.com/ALIS-ai/MERL-T/issues). When creating an enhancement suggestion, include:

- **Use a clear and descriptive title**
- **Provide a detailed description** of the proposed enhancement
- **Explain why this enhancement would be useful**
- **List any similar features** in other projects
- **Include mockups or examples** if applicable

### Your First Code Contribution

Unsure where to begin? You can start by looking through `good-first-issue` and `help-wanted` issues:

- **Good first issues** - Issues suitable for newcomers
- **Help wanted** - Issues that need attention from the community

### Pull Requests

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest tests/ -v`)
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Development Setup

### Prerequisites

- **Python**: 3.11+
- **Node.js**: 18+ (for frontend)
- **Docker**: 20+ (optional, for containerized development)
- **Git**: 2.30+

### Clone the Repository

```bash
git clone https://github.com/ALIS-ai/MERL-T.git
cd MERL-T
```

### Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Copy environment template
cp .env.template .env
# Edit .env with your API keys

# Run database migrations
python -m alembic upgrade head

# Start backend
cd backend/orchestration
uvicorn api.main:app --reload
```

### Frontend Setup

```bash
cd frontend/rlcf-web
npm install
npm run dev
```

### Docker Setup

```bash
# Start all services
docker-compose up -d

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

## Pull Request Process

### Before Submitting

- [ ] Code follows the project's style guidelines
- [ ] All tests pass (`pytest tests/ -v`)
- [ ] New tests added for new functionality
- [ ] Documentation updated (if applicable)
- [ ] CHANGELOG.md updated (for significant changes)
- [ ] No sensitive data committed (API keys, credentials)

### PR Description

Your PR description should include:

- **Summary**: Brief description of what the PR does
- **Motivation**: Why is this change needed?
- **Related Issues**: Link to related issues (e.g., "Closes #123")
- **Testing**: How has this been tested?
- **Screenshots**: If applicable
- **Breaking Changes**: List any breaking changes

### PR Template

See `.github/pull_request_template.md` for the complete template.

### Review Process

1. **Automated Checks**: GitHub Actions will run tests and linting
2. **Code Review**: At least one maintainer must approve
3. **Discussion**: Address review comments
4. **Merge**: Maintainers will merge once approved

## Style Guidelines

### Python Code Style

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some modifications:

- **Line Length**: 100 characters (not 79)
- **Imports**: Organized by standard library, third-party, local
- **Type Hints**: Use type hints for function signatures
- **Docstrings**: Google-style docstrings

```python
def calculate_authority_score(
    base_score: float,
    temporal_score: float,
    performance_score: float
) -> float:
    """
    Calculate user authority score using weighted formula.

    Args:
        base_score: Base authority from credentials (0.0-1.0)
        temporal_score: Recent performance score (0.0-1.0)
        performance_score: Task success rate (0.0-1.0)

    Returns:
        float: Weighted authority score (0.0-1.0)

    Raises:
        ValueError: If any score is outside [0.0, 1.0] range
    """
    # Implementation
```

### JavaScript/TypeScript Style

- **ESLint**: Follow project's `.eslintrc.json` configuration
- **Prettier**: Code is automatically formatted
- **TypeScript**: Prefer interfaces over types
- **React**: Functional components with hooks

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:

```
feat(api): add rate limiting middleware

Implement token bucket rate limiting with Redis backend.
Rate limits are configurable per API key tier.

Closes #42
```

```
fix(rlcf): correct authority score calculation

The temporal decay factor was not being applied correctly,
resulting in inflated authority scores for inactive users.

Fixes #78
```

## Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/orchestration/test_llm_router.py -v

# With coverage
pytest tests/ --cov=backend --cov-report=html

# Integration tests only
pytest tests/integration/ -v
```

### Writing Tests

- **Unit Tests**: Test individual functions/methods
- **Integration Tests**: Test component interactions
- **E2E Tests**: Test complete workflows

```python
import pytest
from backend.orchestration.llm_router import LLMRouter

def test_router_initialization():
    """Test LLM router initializes correctly."""
    router = LLMRouter(model="claude-3.5-sonnet")
    assert router.model == "claude-3.5-sonnet"

@pytest.mark.asyncio
async def test_router_generates_plan():
    """Test router generates valid execution plan."""
    router = LLMRouter()
    plan = await router.generate_plan("Sample legal query")

    assert plan.retrieval_agents is not None
    assert plan.reasoning_experts is not None
    assert len(plan.retrieval_agents) > 0
```

### Test Coverage

- Aim for **85%+ coverage** on new code
- Critical paths should have **100% coverage**
- Run coverage before submitting PR

## Documentation

### Code Documentation

- **Docstrings**: All public functions/classes must have docstrings
- **Type Hints**: Use type hints for better IDE support
- **Comments**: Explain "why", not "what"

### Project Documentation

- **README.md**: Keep up to date with setup instructions
- **Architecture Docs**: Update `docs/03-architecture/` for significant changes
- **API Docs**: Update OpenAPI schema for API changes
- **Changelog**: Add entry to CHANGELOG.md for user-facing changes

### Documentation Format

We use **Markdown** for all documentation:

- **Headings**: Use ATX-style (`#`, `##`, `###`)
- **Code Blocks**: Use fenced code blocks with language identifier
- **Links**: Use reference-style links for repeated URLs
- **Tables**: Use GFM tables

## Community

### Communication Channels

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: Questions, ideas, general discussion
- **Discord**: Real-time chat with the community
- **Email**: [support@alis.ai](mailto:support@alis.ai) for private inquiries

### Getting Help

- **Documentation**: Start with [docs/](docs/)
- **Examples**: Check [docs/api/API_EXAMPLES.md](docs/api/API_EXAMPLES.md)
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Post questions in GitHub Discussions

## Recognition

Contributors are recognized in:

- **CHANGELOG.md**: Credited for significant contributions
- **README.md**: Added to contributors section
- **Release Notes**: Mentioned in GitHub releases

## License

By contributing to MERL-T, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

Thank you for contributing to MERL-T! 🎉

For questions about contributing, contact [support@alis.ai](mailto:support@alis.ai).
