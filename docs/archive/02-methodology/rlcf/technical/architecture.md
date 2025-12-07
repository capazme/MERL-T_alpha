# System Architecture

## Overview

The RLCF framework implements a layered, asynchronous architecture designed for high-performance legal AI evaluation and training. The system maps theoretical concepts directly to software components while maintaining academic rigor and production readiness.

## Architecture Diagram (Alpha 0.0.1)

```
┌─────────────────────────────────────────────────────────────────┐
│                       React Frontend Layer                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ TaskFormFactory │  │ EvaluationWizard│  │   UI Components │  │
│  │  (9 Task Types) │  │  (UX Enhanced)  │  │  (TailwindCSS)  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │ (HTTP/REST)
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Async Layer                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Dependencies  │  │      Main       │  │    Endpoints    │  │
│  │   (DI System)   │  │   (Routing)     │  │   (Handlers)    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Async Service Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Task Service   │  │ Post Processing │  │ OpenRouter AI   │  │
│  │  (Orchestration)│  │  (Consistency)  │  │   Service       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Core Algorithm Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Authority Module│  │ Aggregation     │  │ Task Handlers   │  │
│  │  (Safe Eval)    │  │   Engine        │  │  (Polymorphic)  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                  Async Database Layer                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   AsyncSession  │  │   Models        │  │   Config        │  │
│  │   (aiosqlite)   │  │ (SQLAlchemy)    │  │  (YAML/Pydantic)│  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Layer Descriptions

### 1. FastAPI Async Layer

**Purpose**: HTTP interface and request handling  
**Components**:
- `main.py` - FastAPI application and routing
- `dependencies.py` - Dependency injection system
- API endpoints organized by functional areas

**Key Features**:
- Automatic OpenAPI documentation generation
- CORS support for frontend integration
- API key-based authentication for admin endpoints
- Comprehensive error handling and logging

### 2. Async Service Layer

**Purpose**: Business logic orchestration and coordination  
**Components**:
- `services/task_service.py` - Task lifecycle management
- `post_processing.py` - Data consistency and validation
- `bias_analysis.py` - Multi-dimensional bias detection

**Key Features**:
- Atomic transaction handling
- Cross-service coordination
- Business rule enforcement
- Performance optimization

### 3. Core Algorithm Layer

**Purpose**: Implementation of RLCF mathematical framework  
**Components**:
- `authority_module.py` - Dynamic authority scoring
- `aggregation_engine.py` - Uncertainty-preserving aggregation
- `task_handlers/` - Polymorphic task processing

**Key Features**:
- Direct implementation of theoretical algorithms
- Safe mathematical expression evaluation
- Configurable parameters via YAML
- Academic-grade precision

### 4. Async Database Layer

**Purpose**: Data persistence and management  
**Components**:
- `database.py` - Async SQLAlchemy configuration
- `models.py` - Database schema definitions
- `config.py` - Configuration management

**Key Features**:
- Full async/await support
- Automatic schema migration
- JSON field support for flexible data
- Connection pooling optimization

## Key Design Patterns

### Strategy Pattern (Task Handlers)

The framework uses the Strategy pattern for task-specific logic:

```python
class BaseTaskHandler(ABC):
    @abstractmethod
    async def aggregate_feedback(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod 
    def calculate_consistency(self, feedback: Feedback, result: Dict) -> float:
        pass
```

**Benefits**:
- Extensible task type support
- Domain-specific optimization
- Consistent interface across implementations

### Dependency Injection

Centralized dependency management for:
- Database sessions
- Configuration objects  
- Service instances

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

def get_model_settings() -> ModelConfig:
    return load_model_config()
```

### Repository Pattern

Data access abstraction through SQLAlchemy ORM:
- Async query execution
- Relationship loading optimization
- Transaction management

## Configuration System

### Model Configuration (`model_config.yaml`)

Defines mathematical parameters:
- Authority weights (α, β, γ)
- Track record decay factor (λ)
- Disagreement threshold (τ)
- Credential scoring functions

### Task Configuration (`task_config.yaml`)

Defines task schemas:
- Input data structure
- Feedback data requirements
- Ground truth separation rules

### Dynamic Reconfiguration

Runtime configuration updates through REST API:
- Validation via Pydantic models
- Hot-reload capability
- Constitutional compliance checking

## Security Architecture

### API Security
- API key authentication for admin endpoints
- Input validation via Pydantic schemas
- SQL injection protection through ORM

### Mathematical Security
- Safe expression evaluation using `asteval`
- Timeout protection for formula evaluation
- Input sanitization for user-defined formulas

### Data Security
- Encrypted database connections
- Audit logging for all operations
- Constitutional governance validation

## Performance Optimizations

### Asynchronous Operations
- Non-blocking database operations
- Concurrent request handling
- Async/await throughout the stack

### Database Optimization
- Connection pooling
- Lazy loading strategies
- Query optimization via SQLAlchemy

### Caching Strategy
- LRU cache for authority calculations
- Redis support for distributed caching
- Configuration caching with hot-reload

## Scalability Considerations

### Horizontal Scaling
- Stateless API design
- Database connection pooling
- Load balancer compatibility

### Vertical Scaling
- Async processing for CPU-intensive operations
- Memory-efficient data structures
- Configurable resource limits

### Academic Scalability
- Multi-institution support
- Federated authority scoring
- Cross-jurisdiction validation

## Integration Points

### Frontend Integration
- React/TypeScript frontend support
- WebSocket for real-time updates
- RESTful API design

### External Services
- OpenRouter AI model integration
- Export compatibility (CSV, JSON, LaTeX)
- Academic database connectivity

### Research Tools
- Statistical analysis integration
- Experiment configuration management
- Publication-ready data export

## Monitoring and Observability

### Logging
- Structured logging with JSON format
- Multiple log levels and targets
- Performance timing information

### Metrics
- Authority score distributions
- Bias detection statistics
- Task completion rates

### Health Checks
- Database connectivity monitoring
- Configuration validation
- Service dependency checking

## Development Workflow

### Code Organization
- Modular component structure
- Clear separation of concerns
- Academic reference documentation

### Testing Strategy
- Unit tests for core algorithms
- Integration tests for workflows
- Performance benchmarking

### Documentation
- Inline code documentation
- API documentation generation
- Academic paper cross-references

---

**Next Steps:**
- [Database Schema](database-schema.md) - Detailed database structure
- [Configuration System](configuration.md) - Configuration management
- [Task Handler System](task-handlers.md) - Task processing architecture
