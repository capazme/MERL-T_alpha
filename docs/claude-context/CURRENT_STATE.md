# MERL-T Current State

> **Aggiorna questo file alla fine di ogni sessione di lavoro**
> Claude legge questo file all'inizio di ogni conversazione

---

## Stato Attuale

| Campo | Valore |
|-------|--------|
| **Data ultimo aggiornamento** | 27 Dicembre 2025 |
| **Fase progetto** | **RLCF Loop Validation** |
| **Prossimo obiettivo** | Rieseguire EXP-021 con fix applicati |
| **Blocchi attivi** | Nessuno |

---

## Cosa Abbiamo Fatto (Sessione 27 Dic 2025)

### EXP-021 RLCF Simulator - 3 Bug Critici Corretti

Dopo l'esecuzione del primo esperimento RLCF con componenti reali, identificati e corretti 3 bug critici:

#### Bug 1: WeightStore Mock
**Problema**: `_get_current_weights()` chiamava metodo async senza await + `.to_dict()` inesistente.
**Impatto**: Tracking pesi mostrando sempre `{'mock': True}`.

**Fix** (`merlt/rlcf/simulator/experiment.py`):
```python
async def _get_current_weights(self) -> Dict[str, Any]:
    config = await self.weight_store.get_weights()  # await aggiunto
    return {
        "mock": False,
        "retrieval_alpha": config.retrieval.alpha.default,
        "expert_traversal": {...},
        "gating": {...},
    }
```

#### Bug 2: Authority Decrescente
**Problema**: `lambda=0.05` troppo basso + formula con pesi sbilanciati (track_record=0.5).
**Impatto**: Authority degli expert diminuiva invece di aumentare.

**Fix** (`merlt/rlcf/simulator/config.py`, `users.py`, `simulation.yaml`):
- Nuova classe `AuthorityModelConfig` con parametri configurabili via YAML
- Default: `lambda=0.15`, weights `0.40/0.35/0.25`
- Validazione: i pesi devono sommare a 1.0
- `track_record` inizializzato a `baseline_authority` (non 0.5)

```yaml
# simulation.yaml
authority_model:
  lambda_factor: 0.15
  weight_baseline: 0.40
  weight_track_record: 0.35
  weight_quality: 0.25
```

#### Bug 3: Zero Feedback in Iterazione 2
**Problema**: RNG globale consumato sequenzialmente entra in "zona morta".
**Impatto**: Iterazione 2 generava 0 feedback.

**Fix** (`merlt/rlcf/simulator/users.py`):
- RNG isolato per decisioni feedback (`_feedback_rng` in UserPool)
- Seed derivato con offset +1000 per separazione
- `should_provide_feedback()` usa RNG del pool

```python
class UserPool:
    _feedback_rng: random.Random = field(init=False)

    def __post_init__(self):
        feedback_seed = (self.random_seed + 1000) if self.random_seed else None
        self._feedback_rng = random.Random(feedback_seed)
```

### Documentazione EXP-021

Creati 4 file markdown dettagliati in `docs/experiments/EXP-021_rlcf_loop_validation/`:

| File | Contenuto |
|------|-----------|
| `ARCHITECTURE.md` | Diagrammi, componenti, data flow |
| `METHODOLOGY.md` | Protocollo scientifico, profili utente |
| `STATISTICS.md` | Test statistici (Bonferroni, Wilcoxon) |
| `CONFIGURATION.md` | CLI options, YAML config |

### Test Validazione

Tutti i fix validati con test:
- RNG: min feedback > 0 in 100 iterazioni ✓
- Authority: aumenta con feedback positivi ✓
- Async: `_get_current_weights` e `_record_weights` corretti ✓

---

## Cosa Abbiamo Fatto (Sessione 22 Dic 2025)

### ReAct Pattern - Integrazione Completa

Tutti e 4 gli Expert ora supportano il pattern ReAct (Reasoning + Acting):

```python
# Ogni expert può usare ReAct dinamico
expert = LiteralExpert(tools=tools, ai_service=ai, config={
    "use_react": True,
    "react_max_iterations": 5
})
```

**File modificati**:
- `merlt/experts/literal.py`
- `merlt/experts/systemic.py`
- `merlt/experts/principles.py`
- `merlt/experts/precedent.py`

### Fix Critici

1. **ReAct Response Parsing** (`react_mixin.py:311-333`)
   - `generate_response_async` restituisce stringa, non dict
   - Aggiunta gestione corretta per entrambi i tipi

2. **ExpertResponse Metadata** (`base.py:175`)
   - Aggiunto campo `metadata: Dict[str, Any]` al dataclass
   - Necessario per `react_metrics` e altri metadati

3. **Token Tracking** (`ai_service.py`, `expert_debugger.py`)
   - `OpenRouterService` ora salva `_last_usage` dopo ogni chiamata
   - `TracingAIService` recupera tokens reali o stima (~3 chars/token)
   - Costi per modello (Gemini Flash: $0.15/1M tokens)

### Streamlit Enhanced UI

Nuove funzionalità in `apps/expert_debugger.py`:

| Feature | Descrizione |
|---------|-------------|
| **Run Parameters** | Sidebar con tutti i parametri controllabili |
| **Token Tracking** | Tokens per expert + costo stimato |
| **RLCF Feedback** | Batch feedback + authority + weights |
| **Full Trace Tab** | Timeline, raw data, export multipli |

### RLCF Feedback Loop

UI completa per feedback con:
- Batch rating per tutti gli expert
- Authority score tracking (aumenta con feedback)
- Weight update suggestions
- Feedback Analytics (grafici per expert)
- Export feedback JSON

### Nuovo Esperimento EXP-021

Creato `docs/experiments/EXP-021_rlcf_loop_validation/`:
- Obiettivo: Validare loop RLCF end-to-end
- 3 fasi: Baseline → Training (10 query) → Post-Training
- Metriche: Authority convergence, Weight consistency, Response improvement

---

## Cosa Abbiamo Fatto (Sessione 21 Dic 2025 - SERA)

### ArticleFetchTool Integration

Aggiunto nuovo tool per recuperare articoli da Normattiva API quando non sono presenti nel database locale:

```python
from merlt.tools import ArticleFetchTool

tool = ArticleFetchTool()
result = await tool(tipo_atto="codice civile", numero_articolo="1453")
print(result.data["text"])  # Testo ufficiale dell'articolo
```

**Integrazione in Expert Debugger**: Il tool è ora disponibile per tutti gli Expert nel debugger Streamlit (`apps/expert_debugger.py`).

### Bug Fixes Critici

1. **FalkorDB shortestPath**: FalkorDB non supporta `shortestPath()` undirected. Implementato workaround a 3 step (direct → reverse → shared neighbor)

2. **Graph score computation**: Ora `linked_nodes` e `graph_score` vengono calcolati correttamente:
   ```
   Query: "Risoluzione ex art. 1453 c.c."
   ✓ Art. 1819: sim=0.874, graph=1.000, final=0.912, linked=10
   ✓ Art. 1810: sim=0.858, graph=1.000, final=0.901, linked=10
   ```

3. **Parameter name fix**: `start_node_urn` → `start_node` in `shortest_path()`

---

## Cosa Abbiamo Fatto (Sessione 21 Dic 2025 - MATTINA)

### SOURCE OF TRUTH - CRITICO

Implementato constraint rigoroso negli Expert: **DEVONO usare SOLO fonti recuperate dal database**.

**Problema risolto**: Gli Expert potevano "inventare" articoli o sentenze non presenti nel KG.

**Soluzione**: Aggiunto a tutti i prompt degli Expert:
```
## REGOLA FONDAMENTALE - SOURCE OF TRUTH

⚠️ DEVI usare ESCLUSIVAMENTE le fonti fornite nella sezione "TESTI NORMATIVI RECUPERATI".
⚠️ NON PUOI citare articoli, sentenze o dottrina che NON sono presenti in quella sezione.
⚠️ Se le fonti recuperate sono insufficienti, indica "source_availability" basso.
⚠️ Se nessuna fonte è rilevante, imposta confidence=0.1.
```

**Risultato**:
| Query | Fonti nel DB | Confidence |
|-------|-------------|------------|
| Art. 1218 c.c. (nel DB) | ✅ | **0.975** |
| Art. 52 c.p. (non nel DB) | ❌ | **0.35** |

### EXP-019 Rieseguito con Query Corrette

Query riscritte per Libro IV del Codice Civile (contenuto effettivo del database):
- 20/20 query processate
- Confidence media: 0.833
- Source Coverage: 90%
- Aggiunta categoria "teleological" al Router

---

## Cosa Abbiamo Fatto (Sessione 20 Dic 2025)

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
| `merlt/tools/search.py` | SemanticSearchTool, GraphSearchTool, **ArticleFetchTool** |

**ArticleFetchTool**: Recupera testo articoli da Normattiva API per articoli non presenti nel DB locale.

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

## Stato Database Corrente (Aggiornato: 21 Dicembre 2025)

| Storage | Nome Corretto | Contenuto |
|---------|---------------|-----------|
| **FalkorDB** | `merl_t_dev` | 27,740 nodi, 43,935 relazioni |
| **Qdrant** | `merl_t_dev_chunks` | 5,926 vectors (multi-source) |
| **PostgreSQL** | `rlcf_dev` | Database sviluppo |
| **Bridge Table** | `bridge_table` | 27,114 mappings chunk↔nodo |

**IMPORTANTE - Nomi da usare sempre:**
```python
# CORRETTO - Usa sempre questi nomi
config = MerltConfig(graph_name="merl_t_dev")
# Questo genera automaticamente: qdrant_collection="merl_t_dev_chunks"

# SBAGLIATO - Questi grafi sono vuoti!
# merl_t_test, merl_t_prod, merl_t_legal
```

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
