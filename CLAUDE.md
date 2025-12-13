# CLAUDE.md

> **Versione**: 4.0 | **Ultimo aggiornamento**: 7 Dicembre 2025

---

## MISSIONE PRINCIPALE

**Stai costruendo `merlt`**: la libreria Python di riferimento per l'informatica giuridica italiana.

Ogni riga di codice che scrivi sarà usata da giuristi-programmatori per costruire il codice civile digitale del futuro. Scrivi come se stessi creando `pandas` o `requests` - API chiare, documentazione eccellente, zero duplicazioni.

---

## Prima di Ogni Sessione

**Leggi in ordine:**
1. `docs/claude-context/LIBRARY_VISION.md` - **Principi guida della libreria**
2. `docs/claude-context/CURRENT_STATE.md` - Stato attuale
3. `docs/claude-context/PROGRESS_LOG.md` - Contesto recente

---

## API Target della Libreria

```python
# Questo è ciò che l'utente finale deve poter fare:
from merlt import LegalKnowledgeGraph

kg = LegalKnowledgeGraph()
await kg.connect()

# Una riga per ingestion
article = await kg.ingest("codice penale", "52")

# Una riga per ricerca
results = await kg.search("legittima difesa")

# Tutto il resto (grafo, vettori, bridge, multivigenza) è automatico
```

Se un'operazione comune richiede più di 3 righe, **ripensa l'API**.

---

## Principi di Sviluppo

### 1. ZERO DUPLICAZIONI

```python
# PRIMA di scrivere qualsiasi funzione:
# 1. Cerca se esiste già in merlt/
# 2. Se esiste, riutilizzala
# 3. Se non esiste, creala nel posto giusto (non negli scripts)

# MAI così:
def my_custom_scraper():  # ❌ Duplica NormattivaScraper
    ...

# SEMPRE così:
from merlt.sources import NormattivaScraper  # ✅ Riusa
```

### 2. COMPOSABILITÀ

```python
# Ogni componente DEVE funzionare da solo:
from merlt.sources import NormattivaScraper
scraper = NormattivaScraper()
text = await scraper.fetch("codice civile", "1453")  # ✅ Funziona isolato

# Ma anche insieme:
from merlt import LegalKnowledgeGraph  # ✅ Orchestrazione automatica
```

### 3. MAI LOGICA NEGLI SCRIPTS

```python
# scripts/ sono SOLO entry points:

# scripts/ingest_cp.py - CORRETTO
from merlt import LegalKnowledgeGraph

async def main():
    kg = LegalKnowledgeGraph()
    await kg.ingest_batch("codice penale", libro="I")

# scripts/ingest_cp.py - SBAGLIATO
async def main():
    # 200 righe di logica custom ❌
    for article in articles:
        text = await scraper.fetch(...)
        parsed = parse_article(text)
        # ... altro codice che dovrebbe essere in merlt/
```

### 4. DOCUMENTAZIONE ITALIANA

```python
async def cerca(query: str, top_k: int = 5) -> List[Risultato]:
    """
    Cerca nel knowledge graph giuridico.

    Args:
        query: Domanda in linguaggio naturale
               (es. "Cos'è la legittima difesa?")
        top_k: Numero massimo di risultati

    Returns:
        Lista di Risultato con articoli e contesto

    Example:
        >>> risultati = await kg.cerca("responsabilità del debitore")
        >>> print(risultati[0].articolo)
        "Art. 1218 c.c."
    """
```

---

## Struttura Package

```
merlt/                           # Package principale
├── __init__.py                  # API pubblica: LegalKnowledgeGraph, MerltConfig
├── config/                      # ⚙️ Configurazione
│   └── environments.py          # TEST_ENV, PROD_ENV
│
├── core/                        # 🎯 Orchestrazione (entry point)
│   └── legal_knowledge_graph.py # LegalKnowledgeGraph, MerltConfig
│
├── sources/                     # 📥 Fonti dati
│   ├── base.py                  # BaseScraper (interfaccia)
│   ├── normattiva.py            # NormattivaScraper
│   ├── brocardi.py              # BrocardiScraper
│   └── utils/                   # Utilities (norma, urn, tree, text, http)
│
├── storage/                     # 🗄️ Persistence
│   ├── graph/                   # FalkorDB client
│   ├── vectors/                 # EmbeddingService
│   ├── bridge/                  # Bridge Table (chunk ↔ nodo)
│   └── retriever/               # GraphAwareRetriever
│
├── pipeline/                    # ⚙️ Processing
│   ├── ingestion.py             # IngestionPipelineV2
│   ├── parsing.py               # CommaParser
│   ├── chunking.py              # StructuralChunker
│   └── multivigenza.py          # MultivigenzaPipeline
│
├── rlcf/                        # 🧠 RLCF Framework
│   ├── authority.py             # AuthorityModule
│   └── aggregation.py           # AggregationEngine
│
├── models/                      # 📦 Data models
└── utils/                       # 🔧 Utilities
```

---

## Pattern di Codice

### Async First

```python
# Tutte le operazioni I/O sono async
async def ingest(self, tipo_atto: str, articolo: str) -> IngestionResult:
    ...
```

### Type Hints Sempre

```python
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class IngestionResult:
    article_urn: str
    nodes_created: List[str]
    errors: List[str]
```

### Error Handling Graceful

```python
# Mai fallire completamente, degradare gracefully
result = await kg.ingest("codice penale", "52")
if result.errors:
    logger.warning(f"Completato con warning: {result.errors}")
# L'operazione continua per il resto
```

---

## Contesto Utente

| Aspetto | Valore |
|---------|--------|
| **Chi** | Studente di giurisprudenza (non programmatore) |
| **Cosa** | Tesi su "sociologia computazionale del diritto" |
| **Obiettivo** | Creare libreria di riferimento per informatica giuridica IT |
| **Lingua** | Italiano per documentazione, inglese per codice |

---

## Checklist Pre-Commit

- [ ] Nessuna duplicazione di codice
- [ ] Logica nel package, non negli scripts
- [ ] Type hints completi
- [ ] Docstring in italiano
- [ ] Test per funzioni pubbliche
- [ ] CURRENT_STATE.md aggiornato

---

## Comandi Utili

```bash
# Ambiente
source .venv/bin/activate

# Database
docker-compose -f docker-compose.dev.yml up -d

# Test
pytest tests/ -v

# Importa libreria
python -c "from merlt import LegalKnowledgeGraph; print('OK')"
```

---

## File Chiave

| File | Scopo |
|------|-------|
| `docs/claude-context/LIBRARY_VISION.md` | Principi guida libreria |
| `docs/claude-context/CURRENT_STATE.md` | Stato attuale |
| `docs/claude-context/LIBRARY_ARCHITECTURE.md` | Architettura componenti |
| `merlt/core/legal_knowledge_graph.py` | Entry point principale |

---

## Cosa NON Fare

1. **MAI duplicare codice** - Cerca prima, riusa sempre
2. **MAI logica negli scripts** - Solo entry points
3. **MAI hardcodare valori** - Usa config
4. **MAI ignorare errori** - Gestisci gracefully
5. **MAI dimenticare type hints** - Sempre

---

*Questa è la libreria dell'informatica giuridica italiana. Ogni riga conta.*
- ricordiamoci di aggiungere test in CI/CD per tutto senza mock
- salva sempre i log nella cartella logs/ non in tmp
- DObbiamo irrobustire il parsing per gestire tutti i possibili casi presenti su normattiva. Quindi man mano che troviamo nuovi casi dobbiamo aggiungerli per un'estrazione robusta
- quando viene aggiunta una feature o un fix, aggiungilo ai test per evitare regression
- esternalizziamo sempre i modelli nell'env in modo da poter usare sempre il migliore per il caso d'uso specifico
- **CONVENZIONE DATABASE**: ogni database deve avere versione `_dev` e `_prod`. FalkorDB usa `merl_t_dev` per sviluppo e `merl_t_prod` per produzione. Stessa logica per Redis e altri storage.
- esternalizziamo sempre i prompt e i parametri di ogni elemento della pipeline in file yaml di config