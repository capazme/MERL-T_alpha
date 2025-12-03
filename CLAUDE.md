# CLAUDE.md

> **Versione**: 3.0 | **Ultimo aggiornamento**: 2 Dicembre 2025

Questo file contiene le istruzioni operative per Claude Code. Per i dettagli tecnici, consulta `docs/`.

---

## Quick Start

**Prima di iniziare ogni sessione, leggi:**
1. `docs/claude-context/CURRENT_STATE.md` - Stato attuale e prossimi passi
2. `docs/claude-context/PROGRESS_LOG.md` - Cosa è stato fatto

**Reference tecnico:**
- `docs/SYSTEM_ARCHITECTURE.md` - Mappa completa del sistema
- `docs/02-methodology/rlcf/RLCF.md` - Paper teorico RLCF
- `docs/08-iteration/NEXT_STEPS.md` - Piano dettagliato

---

## Il Progetto in 30 Secondi

**MERL-T** = Sistema AI per ricerca giuridica con validazione comunitaria (RLCF)

```
Query → [Preprocessing] → [Router LLM] → [3 Agents] → [4 Experts] → [Synthesis] → Answer
                              │                │              │
                              ▼                ▼              ▼
                          OpenRouter      Neo4j/Qdrant    Claude/Gemini
                          (API key)       (❌ vuoti)      (API key)
```

**Stato**: 70% funzionante, ma database vuoti e mai testato end-to-end.

---

## Contesto Utente

| Aspetto | Valore |
|---------|--------|
| **Chi** | Studente di giurisprudenza (non programmatore) |
| **Cosa** | Tesi su "sociologia computazionale del diritto" |
| **Timeline** | 6 mesi full-time, estendibili a 1 anno |
| **Budget** | Limitato (~€200-500 totali per API) |
| **Stile coding** | "Vibe coder" con LLM |
| **Lingua** | Italiano per comunicazioni, inglese per codice |

---

## Metodologia di Lavoro

### 1. Inizio Sessione
```
1. Leggi CURRENT_STATE.md per capire dove siamo
2. Leggi PROGRESS_LOG.md per contesto recente
3. Chiedi conferma dell'obiettivo della sessione
```

### 2. Durante la Sessione
```
- Reality-check frequenti (non andare nel teorico)
- Documentare ogni passo significativo
- Test incrementali, mai big bang
- Se qualcosa non funziona: fermarsi, capire, documentare
```

### 3. Fine Sessione
```
1. Aggiorna CURRENT_STATE.md con nuovo stato
2. Aggiungi entry in PROGRESS_LOG.md
3. Commit con messaggio semantico (feat:, fix:, docs:)
```

### 4. Comunicazione
```
- Sii diretto e pratico, evita over-engineering
- Se vedi che vado nel teorico: fermami
- Proponi soluzioni concrete con effort stimato
- Domanda se qualcosa non è chiaro
```

---

## Pattern di Codice

### Import (CRITICI)
```python
# Dentro un package (backend/orchestration/)
from .models import QueryState      # RELATIVO

# Da tests/ o cross-package
from backend.orchestration.llm_router import RouterService  # ASSOLUTO
```

### Configurazione
```python
# MAI hardcodare
llm_model = config.router_model     # ✅ Da config

# MAI
llm_model = "gemini-2.5-flash"      # ❌ Hardcoded
```

### Test
```python
# Ogni feature deve avere test
def test_feature_basic_case():
    ...
def test_feature_edge_case():
    ...
```

---

## Formule RLCF (Non Modificare)

Queste formule sono il cuore accademico del progetto:

```
Authority Score:
A_u(t) = α·B_u + β·T_u(t-1) + γ·P_u(t)
dove α=0.3, β=0.5, γ=0.2

Shannon Entropy (disagreement):
H(X) = -Σ p(x) log p(x)
```

**File**: `backend/rlcf_framework/authority_module.py`, `aggregation_engine.py`

---

## Comandi Utili

```bash
# Setup
python3.11 -m venv venv && source venv/bin/activate
pip install -e .
cp .env.template .env

# Database
docker-compose -f docker-compose.dev.yml up -d

# Backend
uvicorn backend.orchestration.api.main:app --reload --port 8000

# Test
pytest tests/ -v
pytest tests/orchestration/ -v --cov=backend/orchestration
```

---

## Struttura docs/ (Single Source of Truth)

```
docs/
├── claude-context/          # 🤖 Per Claude
│   ├── CURRENT_STATE.md     # Stato attuale sessione
│   └── PROGRESS_LOG.md      # Log cronologico
│
├── 01-introduction/         # Vision e problem statement
├── 02-methodology/          # RLCF framework (paper teorico)
├── 03-architecture/         # 5 layer del sistema
├── 04-implementation/       # Dettagli implementativi
├── 05-governance/           # AI Act, GDPR, ALIS
├── 06-resources/            # Bibliografia, dataset
├── 07-guides/               # Setup locale, contributing
├── 08-iteration/            # Next steps, testing strategy
├── api/                     # API documentation
│
├── SYSTEM_ARCHITECTURE.md   # Mappa tecnica (reference)
├── IMPLEMENTATION_ROADMAP.md
└── TECHNOLOGY_RECOMMENDATIONS.md
```

---

## Cosa NON Fare

1. **Non duplicare info** - Se è in docs/, punta lì
2. **Non modificare formule RLCF** - Sono per pubblicazione accademica
3. **Non cambiare esempi legali** - Contesto italiano (Codice Civile, Cassazione)
4. **Non ridurre test coverage** - Mantenere 85%+
5. **Non fare big bang** - Sempre incrementale

---

## Checklist Pre-Commit

- [ ] Test passano (`pytest tests/ -v`)
- [ ] Nessun import rotto
- [ ] CURRENT_STATE.md aggiornato
- [ ] PROGRESS_LOG.md aggiornato (se sessione significativa)
- [ ] Commit message semantico

---

## Contatti e Risorse

- **Repo**: MERL-T_alpha (locale)
- **Documentazione RLCF**: `docs/02-methodology/rlcf/RLCF.md`
- **API Examples**: `docs/api/API_EXAMPLES.md`

