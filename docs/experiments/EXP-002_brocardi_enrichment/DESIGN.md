# EXP-002: Brocardi Enrichment - Libro IV

> **Status**: ABSORBED INTO EXP-001
> **Data**: 2025-12-04
> **Autore**: Guglielmo Puzio
> **Nota**: Questo esperimento è stato integrato direttamente nel Run 2 di EXP-001

---

## NOTA IMPORTANTE

Questo esperimento **non è stato eseguito come esperimento separato**.

Durante la preparazione, abbiamo deciso di integrare l'enrichment Brocardi direttamente nella pipeline di ingestion (EXP-001 Run 2). I motivi:

1. **Efficienza**: Un singolo pass sui dati invece di due
2. **Consistenza**: Nodi creati già con tutti i dati disponibili
3. **Semplicità**: Meno complessità operativa

### Risultati Ottenuti (in EXP-001 Run 2)

I risultati che sarebbero stati prodotti da EXP-002 sono stati raggiunti in EXP-001:

| Metrica Target EXP-002 | Target | Risultato EXP-001 |
|------------------------|--------|-------------------|
| Coverage Relazioni | >80% | ~92% (Dottrina) |
| Nuovi link :cita | >2000 | 23,056 :interpreta |
| Error rate | <5% | 0% |
| Tempo | <90 min | 7 min (cache) |

### Documentazione Storica

Il resto di questo documento è mantenuto per **riferimento storico** e mostra il design originale dell'esperimento prima dell'integrazione.

---

## Design Originale (Pre-Integrazione)

---

## 1. Overview

### 1.1 Obiettivo

Arricchire i **888 nodi Norma** esistenti (Libro IV) con dati da Brocardi.it:
- **Relazioni storiche** (Guardasigilli 1941/1942)
- **Ratio Legis** e **Spiegazione**
- **Massime giurisprudenziali**
- **Articoli citati** nelle Relazioni (link nel graph)

### 1.2 Research Questions

- [ ] **RQ3**: L'enrichment Brocardi aggiunge valore informativo misurabile?
  - Metrica: % articoli con Relazione, % con Ratio, coverage ratio

- [ ] **RQ3b**: I link tra articoli citati nelle Relazioni migliorano la navigabilità del graph?
  - Metrica: Densità del grafo pre/post enrichment, path medi

### 1.3 Background

EXP-001 ha completato l'ingestion strutturale:
- 888 articoli (1173-2059)
- 2546 chunks
- 2559 bridge mappings

Ma **zero Brocardi** perché il BrocardiScraper richiede lookup live.
Nella sessione 4 Dic 2025 abbiamo ampliato lo scraper per estrarre:
- `Relazioni` (Guardasigilli 1941/1942)
- `articoli_citati` (link interni)

---

## 2. Target Data

### 2.1 Dati da Estrarre per Articolo

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| Relazione Libro Obbligazioni | text | Relazione Guardasigilli 1941 |
| Relazione Codice Civile | text | Relazione Grandi 1942 |
| Articoli citati | list | Link ad altri articoli |
| Ratio | text | Ratio legis |
| Spiegazione | text | Commento dottrinale |
| Massime | list | Giurisprudenza |
| Brocardi | list | Massime latine |
| Position | text | Breadcrumb (Libro>Titolo>Capo>...) |

### 2.2 Stima Dimensioni

| Metrica | Stima | Note |
|---------|-------|------|
| Articoli da arricchire | 888 | Libro IV completo |
| Articoli con Relazione | ~800 | Non tutti hanno Relazione |
| Articoli citati medi | ~5/articolo | Dalle Relazioni |
| Nuove relazioni graph | ~4000 | `cita` tra articoli |
| Tempo stimato | ~60 min | ~4 sec/articolo |

---

## 3. Architettura Enrichment

### 3.1 Flusso

```
Per ogni articolo in FalkorDB:
  1. Costruisci NormaVisitata da URN
  2. Chiama BrocardiScraper.get_info()
  3. Aggiorna nodo con MERGE:
     - relazione_libro, relazione_codice, ratio, spiegazione
  4. Crea relazioni `cita` verso articoli_citati
  5. Crea/aggiorna nodi Dottrina (se presenti)
```

### 3.2 Schema Graph Update

```cypher
// Aggiorna proprietà articolo
MERGE (a:Norma {URN: $urn})
SET a.relazione_libro = $rel_libro,
    a.relazione_codice = $rel_codice,
    a.ratio = $ratio,
    a.spiegazione = $spiegazione,
    a.brocardi_url = $url,
    a.brocardi_enriched_at = $timestamp

// Crea relazione cita
MATCH (a:Norma {URN: $source_urn})
MATCH (b:Norma {URN: $target_urn})
MERGE (a)-[:cita {fonte: 'relazione_guardasigilli'}]->(b)
```

### 3.3 Rate Limiting

- **Brocardi delay**: 1.5 sec/request (più conservativo)
- **Batch size**: 50 articoli, poi pausa 30 sec
- **Totale stimato**: ~60 minuti

---

## 4. Success Criteria

| ID | Criterio | Target | Metrica |
|----|----------|--------|---------|
| C1 | Coverage Relazioni | >80% | % articoli con almeno una Relazione |
| C2 | Nuovi link cita | >2000 | COUNT di relazioni :cita create |
| C3 | Error rate | <5% | % articoli falliti |
| C4 | Tempo esecuzione | <90 min | Tempo totale |
| C5 | Nessuna regressione | 0 | Nodi/relazioni non modificati involontariamente |

---

## 5. Rischi e Mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| Rate limiting Brocardi | Media | Alto | Delay conservativo, retry |
| Articoli senza Brocardi | Media | Basso | Log e skip, non errore |
| Inconsistenza URN | Bassa | Medio | Verifica mapping pre-run |
| Timeout | Media | Medio | Retry con exponential backoff |

---

## 6. Script Enrichment

File: `scripts/batch_enrich_brocardi.py`

```python
# Pseudocodice
async def enrich_article(urn: str, scraper: BrocardiScraper):
    norma_visitata = urn_to_norma_visitata(urn)
    position, info, brocardi_url = await scraper.get_info(norma_visitata)

    if not info:
        return {"status": "skipped", "reason": "no_brocardi"}

    # Update node properties
    await falkordb.query(UPDATE_QUERY, {
        "urn": urn,
        "rel_libro": info.get("Relazioni", [{}])[0].get("testo"),
        "rel_codice": info.get("Relazioni", [{}])[1].get("testo") if len(info.get("Relazioni", [])) > 1 else None,
        "ratio": info.get("Ratio"),
        "spiegazione": info.get("Spiegazione"),
        ...
    })

    # Create cita relations
    for rel in info.get("Relazioni", []):
        for art in rel.get("articoli_citati", []):
            target_urn = build_urn_from_article_number(art["numero"])
            await create_cita_relation(urn, target_urn)

    return {"status": "success", "relations_created": len(articoli_citati)}
```

---

## 7. Validazione

### 7.1 Query Post-Enrichment

```cypher
-- Coverage Relazioni
MATCH (n:Norma {tipo_documento: "articolo"})
WHERE n.relazione_libro IS NOT NULL OR n.relazione_codice IS NOT NULL
RETURN count(n) as con_relazione,
       count(n) * 100.0 / 888 as percentuale

-- Nuove relazioni cita
MATCH ()-[r:cita]->()
RETURN count(r) as total_cita

-- Articoli più citati
MATCH (a:Norma)<-[r:cita]-()
RETURN a.numero_articolo, count(r) as citazioni
ORDER BY citazioni DESC
LIMIT 10
```

---

## 8. Timeline

| Fase | Durata | Descrizione |
|------|--------|-------------|
| Sviluppo script | 30 min | Adattamento da EXP-001 |
| Test su 10 articoli | 15 min | Verifica funzionamento |
| Esecuzione completa | 60 min | 888 articoli |
| Validazione | 15 min | Query verifica |
| Documentazione | 15 min | RESULTS.md |

**Totale stimato**: ~2 ore

---

*Documento creato: 2025-12-04*
