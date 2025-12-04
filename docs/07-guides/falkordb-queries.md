# FalkorDB Query Reference

> Query utili per interrogare il knowledge graph legale in FalkorDB

## Connessione

**RedisInsight:**
- Host: `localhost`
- Port: `6380`
- Graph name: `merl_t_legal`

**CLI:**
```bash
redis-cli -p 6380
```

---

## Sintassi Base

FalkorDB usa la sintassi Redis `GRAPH.QUERY`:

```redis
GRAPH.QUERY merl_t_legal "MATCH (n) RETURN n LIMIT 10"
```

- `GRAPH.QUERY` = comando Redis per FalkorDB
- `merl_t_legal` = nome del grafo
- Query Cypher tra **virgolette doppie**

---

## Query di Esplorazione

### Statistiche Generali

```redis
# Conta tutti i nodi per tipo
GRAPH.QUERY merl_t_legal "MATCH (n) RETURN labels(n) AS type, count(n) AS count"

# Conta tutte le relazioni per tipo
GRAPH.QUERY merl_t_legal "MATCH ()-[r]->() RETURN type(r) AS relation, count(r) AS count"

# Overview completo
GRAPH.QUERY merl_t_legal "MATCH (n)-[r]->(m) RETURN labels(n)[0] AS from_type, type(r) AS relation, labels(m)[0] AS to_type, count(*) AS count"
```

### Visualizza Grafo

```redis
# Tutti i nodi e relazioni (limitato)
GRAPH.QUERY merl_t_legal "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50"

# Struttura completa (Codice -> Articoli -> Concetti)
GRAPH.QUERY merl_t_legal "MATCH (c:Norma)-[r1:contiene]->(a:Norma)-[r2:disciplina]->(con:ConcettoGiuridico) RETURN c, r1, a, r2, con"
```

---

## Query su Nodi Norma

### Lista Articoli

```redis
# Tutti gli articoli con titolo

"

# Articoli di un codice specifico
GRAPH.QUERY merl_t_legal "MATCH (c:Norma)-[:contiene]->(a:Norma) WHERE c.tipo_documento = 'codice' AND c.estremi = 'Codice Civile' RETURN a.estremi, a.titolo ORDER BY a.estremi"
```

### Testo Articolo

```redis
# Leggi testo completo di un articolo
GRAPH.QUERY merl_t_legal "MATCH (n:Norma {estremi: 'Art. 1453 c.c.'}) RETURN n.estremi, n.titolo, n.testo_vigente"

# Cerca articolo per URN
GRAPH.QUERY merl_t_legal "MATCH (n:Norma) WHERE n.URN CONTAINS 'art1453' RETURN n.estremi, n.titolo, n.testo_vigente"
```

---

## Query su ConcettoGiuridico

### Lista Concetti

```redis
# Tutti i concetti giuridici
GRAPH.QUERY merl_t_legal "MATCH (c:ConcettoGiuridico) RETURN c.denominazione, c.categoria, c.fonte"

# Concetti per categoria
GRAPH.QUERY merl_t_legal "MATCH (c:ConcettoGiuridico) WHERE c.categoria = 'diritto_civile_contratti' RETURN c.denominazione"
```

### Concetti legati a Norme

```redis
# Articoli che disciplinano un concetto
GRAPH.QUERY merl_t_legal "MATCH (a:Norma)-[r:disciplina]->(c:ConcettoGiuridico) RETURN a.estremi, c.denominazione, r.certezza"

# Concetti disciplinati da un articolo specifico
GRAPH.QUERY merl_t_legal "MATCH (a:Norma {estremi: 'Art. 1453 c.c.'})-[:disciplina]->(c:ConcettoGiuridico) RETURN c.denominazione, c.definizione"
```

---

## Query Strutturali

### Gerarchia Normativa

```redis
# Codice -> Articoli (struttura 'contiene')
GRAPH.QUERY merl_t_legal "MATCH (codice:Norma)-[r:contiene]->(art:Norma) WHERE codice.tipo_documento = 'codice' RETURN codice.estremi, art.estremi, art.titolo ORDER BY art.estremi"

# Profondità gerarchia
GRAPH.QUERY merl_t_legal "MATCH path = (root:Norma)-[:contiene*]->(leaf:Norma) WHERE root.tipo_documento = 'codice' RETURN length(path) AS depth, count(*) AS count"
```

### Relazioni Semantiche

```redis
# Tutte le relazioni 'disciplina'
GRAPH.QUERY merl_t_legal "MATCH (n:Norma)-[r:disciplina]->(c:ConcettoGiuridico) RETURN n.estremi, c.denominazione, r.certezza, r.fonte_relazione"

# Articoli correlati tramite concetto comune
GRAPH.QUERY merl_t_legal "MATCH (a1:Norma)-[:disciplina]->(c:ConcettoGiuridico)<-[:disciplina]-(a2:Norma) WHERE a1 <> a2 RETURN a1.estremi, c.denominazione, a2.estremi"
```

---

## Query Avanzate

### Ricerca Testuale

```redis
# Cerca nel testo vigente (case-insensitive con CONTAINS)
GRAPH.QUERY merl_t_legal "MATCH (n:Norma) WHERE n.testo_vigente CONTAINS 'inadempimento' RETURN n.estremi, n.titolo"

# Cerca per titolo
GRAPH.QUERY merl_t_legal "MATCH (n:Norma) WHERE n.titolo CONTAINS 'risoluzione' RETURN n.estremi, n.titolo"
```

### Shortest Path

```redis
# Percorso più breve tra due articoli
GRAPH.QUERY merl_t_legal "MATCH path = shortestPath((a1:Norma {estremi: 'Art. 1453 c.c.'})-[*..5]-(a2:Norma {estremi: 'Art. 1456 c.c.'})) RETURN path"

# Nodi raggiungibili entro N hop
GRAPH.QUERY merl_t_legal "MATCH (start:Norma {estremi: 'Art. 1453 c.c.'})-[*1..2]-(reachable) RETURN DISTINCT labels(reachable)[0] AS type, count(reachable) AS count"
```

### Graph Patterns

```redis
# Triangoli semantici (Norma1 -> Concetto <- Norma2)
GRAPH.QUERY merl_t_legal "MATCH (n1:Norma)-[:disciplina]->(c:ConcettoGiuridico)<-[:disciplina]-(n2:Norma) WHERE id(n1) < id(n2) RETURN n1.estremi, c.denominazione, n2.estremi"

# Norme con più concetti
GRAPH.QUERY merl_t_legal "MATCH (n:Norma)-[:disciplina]->(c:ConcettoGiuridico) WITH n, count(c) AS num_concetti WHERE num_concetti > 1 RETURN n.estremi, num_concetti ORDER BY num_concetti DESC"
```

---

## Query di Manutenzione

### Verifica Integrità

```redis
# Nodi senza relazioni (isolati)
GRAPH.QUERY merl_t_legal "MATCH (n) WHERE NOT (n)--() RETURN labels(n)[0] AS type, count(n) AS isolated_count"

# URN duplicati
GRAPH.QUERY merl_t_legal "MATCH (n:Norma) WITH n.URN AS urn, count(*) AS cnt WHERE cnt > 1 RETURN urn, cnt"

# Nodi senza proprietà obbligatorie
GRAPH.QUERY merl_t_legal "MATCH (n:Norma) WHERE n.estremi IS NULL OR n.tipo_documento IS NULL RETURN n"
```

### Pulizia

```redis
# Cancella tutto (ATTENZIONE!)
GRAPH.QUERY merl_t_legal "MATCH (n) DETACH DELETE n"

# Cancella solo test data
GRAPH.QUERY merl_t_legal "MATCH (n) WHERE n.fonte_relazione = 'test' DETACH DELETE n"
```

---

## Export/Backup

```bash
# Backup del grafo (Redis RDB)
redis-cli -p 6380 SAVE

# Export query results to JSON (con jq)
redis-cli -p 6380 GRAPH.QUERY merl_t_legal "MATCH (n:Norma) RETURN n.estremi, n.titolo" | jq
```

---

## Performance Tips

1. **Usa LIMIT** per query esplorative: `LIMIT 10` o `LIMIT 50`
2. **Filtra presto**: `WHERE` clause prima di `RETURN`
3. **Usa indici** (quando disponibili): `CREATE INDEX ON :Norma(URN)`
4. **Evita cartesian products**: specifica sempre il pattern di relazione

---

## Reference

- **FalkorDB Docs**: https://docs.falkordb.com/
- **Cypher Query Language**: https://neo4j.com/docs/cypher-manual/current/
- **Schema KG**: `docs/02-methodology/knowledge-graph.md`
