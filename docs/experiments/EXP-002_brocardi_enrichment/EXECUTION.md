# EXP-002: Brocardi Enrichment - Execution Log

> **Status**: ABSORBED INTO EXP-001
> **Data**: 2025-12-04
> **Nota**: Esecuzione interrotta e integrata in EXP-001 Run 2

---

## NOTA: Esperimento Assorbito

Questo esperimento è stato **avviato ma non completato** come esperimento separato.

### Sequenza Eventi

1. **01:09**: Avviata esecuzione EXP-002 standalone
2. **~01:30**: Data loss Docker - chiusura accidentale Docker Desktop
3. **01:45**: Deciso di integrare Brocardi enrichment in EXP-001
4. **02:17**: Avviato EXP-001 Run 2 con Brocardi integrato
5. **02:24**: EXP-001 Run 2 completato con successo

### Motivo Integrazione

Dopo il data loss, anziché rieseguire due esperimenti separati (EXP-001 + EXP-002), abbiamo deciso di:
- Modificare `ingestion_pipeline_v2.py` per includere l'enrichment Brocardi
- Eseguire un singolo run che produce il risultato finale

### Documentazione Storica

Il resto di questo documento mostra il **tentativo iniziale** di esecuzione separata, mantenuto per riferimento.

---

## 1. Pre-Execution Checklist

- [x] Script `batch_enrich_brocardi.py` creato
- [x] MAPPING.md completato con mapping KG accurato
- [x] Test su subset (Art. 1285-1287): **PASSED**
- [x] FalkorDB connesso e funzionante
- [x] Verifica URN format: `https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~art{num}`

---

## 2. Test Run Results (Art. 1285-1287)

**Data**: 2025-12-04 00:57

**Comando**:
```bash
python scripts/batch_enrich_brocardi.py --start 1285 --end 1287
```

**Risultati**:
| Metrica | Valore |
|---------|--------|
| Articles attempted | 3 |
| Articles enriched | 2 |
| Articles failed | 1 (Broken pipe) |
| Relazioni Libro | 2 |
| Relazioni Codice | 2 |
| Ratio Legis | 2 |
| Dottrina created | 7 |
| AttoGiudiziario created | 30 |
| :cita relations | 24 |
| :commenta relations | 7 |
| :interpreta relations | 30 |

**Verifica Art. 1285**:
```
brocardi_url: https://brocardi.it/.../art1285.html ✅
relazione_libro: "La disciplina delle obbligazioni alternative..." ✅
paragrafo_libro: 41 ✅
relazione_codice: "Il nuovo codice presenta..." ✅
paragrafo_codice: 595 ✅
ratio_legis: "Il legislatore ha introdotto..." ✅
:cita relations: 4 (→Art.1286, 1287, 1349, ...) ✅
Dottrina nodes: 6 (1 Spiegazione + 5 brocardi) ✅
AttoGiudiziario: Cass. civ. n. 24819/2024, etc. ✅
```

---

## 3. Full Execution

**Data inizio**: 2025-12-04 01:09:15
**PID**: 56559

**Comando**:
```bash
# Background execution con nohup
nohup python scripts/batch_enrich_brocardi.py --output logs/exp002_stats.json > logs/exp002_output.log 2>&1 &

# Monitor progress
tail -f logs/exp002_output.log | grep -E "(Progress|COMPLETE|ERROR)"
```

**Parametri**:
- Start: 1173
- End: 2059
- Articles: 887
- Delay: 1.5s/article
- Batch pause: 30s ogni 50 articoli
- Tempo stimato: ~60-90 minuti
- Velocità osservata: ~4s/articolo

### 3.1 Progress Log

| Timestamp | Progress | Enriched | Failed | Notes |
|-----------|----------|----------|--------|-------|
| 01:09:15 | 0/887 | 0 | 0 | Start |
| 01:09:51 | ~8/887 | 8 | 0 | Art. 1173-1180 OK |

---

## 4. Known Issues

### 4.1 Broken Pipe Error
- **Causa**: Timeout connessione FalkorDB durante scritture lunghe
- **Frequenza**: ~1-5% articoli
- **Mitigazione**: Retry manuale degli articoli falliti
- **Impatto**: Basso - articoli possono essere ri-processati

### 4.2 Massime Parsing
- Alcune massime non matchano il regex pattern
- Creano nodi AttoGiudiziario con estremi vuoti
- **Impatto**: Basso - nodi comunque utili per relazioni

---

## 5. Post-Execution Queries

Da eseguire dopo il completamento:

```cypher
-- Coverage Relazioni
MATCH (n:Norma {tipo_documento: "articolo"})
WHERE n.relazione_libro_obbligazioni IS NOT NULL
   OR n.relazione_codice_civile IS NOT NULL
RETURN count(n) as con_relazione

-- Nuove relazioni cita
MATCH ()-[r:cita {fonte_relazione: 'relazione_guardasigilli_1942'}]->()
RETURN count(r) as citazioni_da_relazione

-- Dottrina create
MATCH (d:Dottrina {fonte: 'Brocardi.it'})
RETURN d.tipo, count(*) as count

-- AttoGiudiziario creati
MATCH (a:AttoGiudiziario {fonte: 'Brocardi.it'})
RETURN count(DISTINCT a) as massime_create
```

---

*Documento creato: 2025-12-04*
