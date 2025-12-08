# Archived Orchestration Tests

**Data di archiviazione**: 7 Dicembre 2025

## Motivo dell'Archiviazione

Questi test facevano riferimento al vecchio layer di orchestrazione (`merlt.orchestration`) che è stato deprecato e spostato in `_archive/orchestration/`.

Il progetto è stato refactorizzato con una nuova architettura centrata su:
- `LegalKnowledgeGraph` in `merlt/core/` - Entry point principale
- Storage components in `merlt/storage/` - FalkorDB, Qdrant, Bridge Table
- Pipeline components in `merlt/pipeline/` - Ingestion, Multivigenza

## Test Archiviati

I seguenti test testano componenti che non esistono più nel codebase principale:

### API Tests
- `test_api_authentication_integration.py` - API authentication middleware
- `test_api_feedback.py` - RLCF feedback API endpoints
- `test_api_query.py` - Query API endpoints
- `test_api_stats.py` - Statistics API endpoints
- `test_auth_middleware.py` - Authentication middleware
- `test_rate_limit_middleware.py` - Rate limiting middleware

### Orchestration Tests
- `test_llm_router.py` - LLM-based execution plan router
- `test_intent_classifier.py` - Intent classification system
- `test_intent_router.py` - Intent routing logic
- `test_model_manager.py` - Model management system
- `test_iteration_controller.py` - Iteration control logic
- `test_experts.py` - Expert system components
- `test_vectordb_agent.py` - VectorDB agent (sostituito da GraphAwareRetriever)
- `test_graceful_degradation.py` - Graceful degradation logic
- `test_preprocessing_integration.py` - Preprocessing integration
- `test_workflow_with_preprocessing.py` - Workflow with preprocessing

### Supporting Files
- `conftest.py` - Shared fixtures for orchestration tests
- `__init__.py` - Package initialization
- `WEEK3_TEST_SUMMARY.md` - Week 3 test summary

## Nuova Architettura

I test per la nuova architettura si trovano in:

- **`tests/integration/test_core_integration.py`** - Test end-to-end per LegalKnowledgeGraph
- **`tests/storage/`** - Test per componenti storage (FalkorDB, Bridge, Retriever, Embeddings)
- **`tests/unit/`** - Test unitari per componenti individuali

## Test Mantenuti e Aggiornati

Il seguente test è stato **aggiornato e spostato**:

- `test_embedding_service.py` → `tests/storage/test_embedding_service.py`
  - Import path aggiornato: `merlt.orchestration.services.embedding_service` → `merlt.storage.vectors.embeddings`
  - Testa `EmbeddingService` che è ancora utilizzato nella nuova architettura

## Come Recuperare

Se hai bisogno di riferimento a questi test per la nuova implementazione:
1. Controlla prima `tests/integration/test_core_integration.py` per pattern simili
2. Adatta i test alla nuova API di `LegalKnowledgeGraph`
3. I test di storage sono già in `tests/storage/`

## Riferimenti

- Codice deprecato: `_archive/orchestration/`
- Nuova architettura: `merlt/core/legal_knowledge_graph.py`
- Documentazione: `docs/claude-context/CURRENT_STATE.md`
