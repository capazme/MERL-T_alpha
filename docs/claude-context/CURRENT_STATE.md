# MERL-T Current State

> **Aggiorna questo file alla fine di ogni sessione di lavoro**
> Claude legge questo file all'inizio di ogni conversazione

---

## Stato Attuale

| Campo | Valore |
|-------|--------|
| **Data ultimo aggiornamento** | 20 Dicembre 2025 |
| **Fase progetto** | **Expert System Integration** - kg.interpret() implementato |
| **Prossimo obiettivo** | Esecuzione esperimenti con API key, documentazione finale |
| **Blocchi attivi** | Nessuno |

---

## Cosa Abbiamo Fatto (Sessione Corrente - 20 Dic 2025)

### Expert System - COMPLETATO

Implementazione completa del sistema multi-expert basato sui canoni ermeneutici delle Preleggi (artt. 12-14):

#### 4 Expert Specializzati

| Expert | Canone | Focus |
|--------|--------|-------|
| **LiteralExpert** | Art. 12, I | "significato proprio delle parole" |
| **SystemicExpert** | Art. 12, I + Art. 14 | "connessione di esse" + storico |
| **PrinciplesExpert** | Art. 12, II | "intenzione del legislatore" |
| **PrecedentExpert** | Prassi | Giurisprudenza applicativa |

#### File Creati

| File | Descrizione |
|------|-------------|
| `merlt/experts/base.py` | BaseExpert, ExpertContext, ExpertResponse |
| `merlt/experts/literal.py` | LiteralExpert |
| `merlt/experts/systemic.py` | SystemicExpert |
| `merlt/experts/principles.py` | PrinciplesExpert |
| `merlt/experts/precedent.py` | PrecedentExpert |
| `merlt/experts/router.py` | ExpertRouter per query classification |
| `merlt/experts/gating.py` | GatingNetwork per aggregazione risposte |
| `merlt/experts/orchestrator.py` | MultiExpertOrchestrator |
| `merlt/experts/config/experts.yaml` | Config Expert (weights, prompts) |

### Tool System - COMPLETATO

| File | Descrizione |
|------|-------------|
| `merlt/tools/base.py` | BaseTool, ToolResult, ToolChain |
| `merlt/tools/registry.py` | ToolRegistry, get_tool_registry() |
| `merlt/tools/search.py` | SemanticSearchTool, GraphSearchTool |

### kg.interpret() - COMPLETATO

Nuovo metodo in `LegalKnowledgeGraph` per interpretazione multi-expert:

```python
from merlt import LegalKnowledgeGraph, InterpretationResult

kg = LegalKnowledgeGraph()
await kg.connect()

# Interpretazione multi-expert
result = await kg.interpret("Cos'è la legittima difesa?")
print(result.synthesis)
print(f"Confidence: {result.confidence}")
print(f"Experts: {list(result.expert_contributions.keys())}")
```

#### InterpretationResult Fields

```python
@dataclass
class InterpretationResult:
    query: str
    synthesis: str
    expert_contributions: Dict[str, Dict[str, Any]]
    combined_legal_basis: List[Dict[str, Any]]
    confidence: float
    routing_decision: Optional[Dict[str, Any]]
    aggregation_method: str
    execution_time_ms: float
    trace_id: str
    errors: List[str]
```

### Esperimenti - CREATI

| Esperimento | Descrizione | Stato |
|-------------|-------------|-------|
| **EXP-018** | Expert Comparison (50 query) | Script creato, eseguito senza AI |
| **EXP-019** | E2E Pipeline (20 query) | Script creato, eseguito senza AI |

#### EXP-018 Risultati (senza API key)

- 50/50 query processate
- Routing accuracy: 74%
- 5 categorie: definitional, interpretive, procedural, constitutional, jurisprudential

#### EXP-019 Risultati (senza API key)

- 20/20 query processate
- Expert Utilization: literal, systemic, principles, precedent
- Pipeline success rate: 100%

### Test - 175 test passing

| Suite | Test |
|-------|------|
| `tests/experts/` | 99 test |
| `tests/tools/` | 61 test |
| `tests/core/test_interpret.py` | 15 test |

---

## Architettura Expert System

```
kg.interpret(query)
    │
    ├─1─> Pre-retrieval (SemanticSearch)
    │
    ├─2─> ExpertRouter
    │         └── Query classification (definitional, constitutional, etc.)
    │
    ├─3─> MultiExpertOrchestrator
    │         └── Parallel execution of selected Experts
    │             ├── LiteralExpert
    │             ├── SystemicExpert
    │             ├── PrinciplesExpert
    │             └── PrecedentExpert
    │
    ├─4─> GatingNetwork
    │         └── Response aggregation (weighted_average, best_confidence, ensemble)
    │
    └─5─> InterpretationResult
```

---

## Stato Database Corrente

| Storage | Nome | Contenuto |
|---------|------|-----------|
| **FalkorDB** | `merl_t_dev` | 27,740 nodi, 43,935 relazioni |
| **Qdrant** | `merl_t_dev` | 5,926 vectors (multi-source) |
| **Bridge Table** | `bridge_table` | 27,114 mappings |

---

## API Disponibili

```python
from merlt import LegalKnowledgeGraph, MerltConfig, InterpretationResult

kg = LegalKnowledgeGraph()
await kg.connect()

# Ingestion singolo articolo
result = await kg.ingest_norm("codice civile", "1453")

# Ingestion batch (ottimizzato)
result = await kg.ingest_batch(
    tipo_atto="codice civile",
    article_range=(1173, 2059),
    batch_size=15,
)

# Search
results = await kg.search("responsabilità contrattuale")

# Interpretazione multi-expert (NUOVO)
interpretation = await kg.interpret("Cos'è la legittima difesa?")
print(interpretation.synthesis)

# Enrichment LLM
config = EnrichmentConfig(...)
result = await kg.enrich(config)
```

---

## Prossimi Passi

### Priorità 1: Validazione con API

- [ ] Eseguire EXP-018 con OPENROUTER_API_KEY
- [ ] Eseguire EXP-019 con AI reale
- [ ] Valutare qualità risposte

### Priorità 2: Documentazione

- [x] Aggiornare CURRENT_STATE.md
- [ ] Aggiornare LIBRARY_ARCHITECTURE.md con interpret()
- [ ] Aggiornare experiments/INDEX.md

### Priorità 3: Test Integration

- [ ] Test con database popolati
- [ ] Benchmark latenza

---

## Quick Reference

```bash
# Avviare ambiente
cd /Users/gpuzio/Desktop/CODE/MERL-T_alpha
source .venv/bin/activate

# Database
docker-compose -f docker-compose.dev.yml up -d

# Test
pytest tests/ -v  # 700+ test

# Run Expert Comparison
python scripts/exp018_expert_comparison.py

# Run E2E Pipeline
python scripts/exp019_e2e_pipeline.py
```

---

## Decisioni Prese (Nuove)

| Data | Decisione | Motivazione |
|------|-----------|-------------|
| 2025-12-20 | 4 Expert basati su Preleggi | Mapping diretto ai canoni ermeneutici |
| 2025-12-20 | GatingNetwork con 4 metodi | Flessibilità aggregazione |
| 2025-12-20 | kg.interpret() come API | UX pulita, integrazione naturale |
| 2025-12-20 | InterpretationResult | Dataclass per output strutturato |

---

## Contesto per Claude

### Cosa devi sapere per riprendere:

- L'utente è uno studente di giurisprudenza (non programmatore)
- Sta facendo una tesi sulla "sociologia computazionale del diritto"
- **Expert System COMPLETATO**: 4 Expert + Router + Gating + Orchestrator
- **kg.interpret() implementato**: API pulita per interpretazione
- EXP-018 e EXP-019 pronti per esecuzione con API key
- Preferisce comunicare in italiano

### File chiave da leggere:

1. `CLAUDE.md` - Istruzioni generali progetto
2. `docs/claude-context/LIBRARY_VISION.md` - Principi guida
3. `merlt/experts/__init__.py` - Export Expert System
4. `merlt/core/legal_knowledge_graph.py` - interpret() method

### Pattern da seguire:

- Documentare prima di implementare
- Reality-check frequenti
- Test incrementali
- Comunicare in italiano, codice in inglese
