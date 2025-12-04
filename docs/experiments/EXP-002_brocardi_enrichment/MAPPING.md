# EXP-002: Mapping Brocardi → Knowledge Graph

> **Riferimento**: `docs/02-methodology/knowledge-graph.md`
> **Obiettivo**: Mappatura accurata dati Brocardi → entità KG MERL-T

---

## 1. Dati Estratti da BrocardiScraper

```python
info = {
    'Position': str,           # Breadcrumb (Libro>Titolo>Capo>...)
    'Brocardi': List[str],     # Massime latine
    'Ratio': str,              # Ratio legis
    'Spiegazione': str,        # Commento dottrinale
    'Massime': List[str],      # Giurisprudenza (Cassazione, etc.)
    'Relazioni': [
        {
            'tipo': str,               # "libro_obbligazioni" | "codice_civile"
            'titolo': str,             # "Relazione al Codice Civile (1942)"
            'numero_paragrafo': str,   # "595"
            'testo': str,              # Testo completo della Relazione
            'articoli_citati': [
                {'numero': str, 'titolo': str, 'url': str}
            ]
        }
    ]
}
```

---

## 2. Mapping a Node Types (§2 knowledge-graph.md)

### 2.1 Norma (§2.A)

**Proprietà da aggiornare su nodi esistenti:**

| Campo Brocardi | Proprietà Norma | Note |
|----------------|-----------------|------|
| `Position` | Parsing → `libro`, `titolo`, `capo`, `sezione` | Gerarchia strutturale |
| `Relazioni[tipo=libro_obbligazioni].testo` | `relazione_libro_obbligazioni` | **NUOVO** - Relazione Guardasigilli 1941 |
| `Relazioni[tipo=codice_civile].testo` | `relazione_codice_civile` | **NUOVO** - Relazione Grandi 1942 |
| `Relazioni[*].numero_paragrafo` | `relazione_paragrafo` | **NUOVO** - Numero §595, §41 |
| `Ratio` | `ratio_legis` | **NUOVO** - Ratio dalla dottrina |
| - | `brocardi_url` | URL pagina Brocardi |
| - | `brocardi_enriched_at` | Timestamp enrichment |

**Cypher Update:**
```cypher
MERGE (n:Norma {URN: $urn})
SET n.relazione_libro_obbligazioni = $rel_libro,
    n.relazione_codice_civile = $rel_codice,
    n.relazione_paragrafo_libro = $paragrafo_libro,
    n.relazione_paragrafo_codice = $paragrafo_codice,
    n.ratio_legis = $ratio,
    n.brocardi_url = $url,
    n.brocardi_enriched_at = $timestamp
```

### 2.2 Dottrina (§2.E)

**Creare nodi Dottrina per:**

| Campo Brocardi | Mapping | Node Type |
|----------------|---------|-----------|
| `Spiegazione` | 1 nodo Dottrina | Commentario moderno |
| `Brocardi` (massime latine) | N nodi Dottrina | Brocardi classici |

**Proprietà Dottrina (da §2.E):**

```python
# Per Spiegazione
dottrina_spiegazione = {
    'node_id': f"dottrina:brocardi:spiegazione:{art_numero}",
    'titolo': f"Spiegazione Art. {art_numero} c.c.",
    'autore': "Brocardi.it",
    'descrizione': info['Spiegazione'][:500],  # Troncato
    'data_pubblicazione': None,  # Non disponibile
    'fonte': "Brocardi.it",
    'tipo': "commentario_online"  # Estensione
}

# Per Brocardi (massime latine)
for i, brocardo in enumerate(info['Brocardi']):
    dottrina_brocardo = {
        'node_id': f"dottrina:brocardo:{art_numero}:{i}",
        'titolo': brocardo[:50],  # Prima parte come titolo
        'autore': "Tradizione giuridica romana",
        'descrizione': brocardo,
        'fonte': "Brocardi.it",
        'tipo': "brocardo"  # Estensione
    }
```

### 2.3 Atto Giudiziario (§2.D)

**Creare nodi AttoGiudiziario per Massime:**

| Campo Brocardi | Mapping |
|----------------|---------|
| `Massime[i]` | 1 nodo AttoGiudiziario per massima |

**Parsing Massime:**
```python
# Input: "Cass. civ. n. 24819/2024 L'obbligazione alternativa presuppone..."
# Output:
atto = {
    'node_id': "atto:cass:civ:24819:2024",
    'estremi': "Cass. civ. n. 24819/2024",
    'descrizione': "L'obbligazione alternativa presuppone...",
    'organo_emittente': "Corte di Cassazione",  # Estratto da "Cass."
    'data': "2024",  # Anno estratto
    'tipologia': "sentenza",
    'materia': "Diritto civile",  # Da "civ."
    'sezione': None  # Se presente "Sez. Unite" etc.
}
```

**Regex per parsing:**
```python
MASSIMA_PATTERN = r'^(Cass\.?\s*(civ|pen|lav)?\.?\s*(Sez\.?\s*\w+)?\s*n\.?\s*(\d+)/(\d{4}))\s*(.+)$'
# Groups: 1=estremi, 2=materia, 3=sezione, 4=numero, 5=anno, 6=testo
```

---

## 3. Mapping a Relation Types (§3 knowledge-graph.md)

### 3.1 Relazione `cita` (§3.6, #24)

**Definizione KG:** "Explicit citation between legal documents"

**Da Brocardi:**
- `Relazioni[*].articoli_citati` → Crea relazioni `:cita`

```cypher
// Articolo cita altro articolo (dalla Relazione Guardasigilli)
MATCH (source:Norma {URN: $source_urn})
MATCH (target:Norma {URN: $target_urn})
MERGE (source)-[r:cita]->(target)
SET r.tipo_citazione = 'riferimento',
    r.fonte_relazione = $fonte,  // "relazione_guardasigilli_1942"
    r.paragrafo_riferimento = $paragrafo,
    r.certezza = 'esplicita',
    r.data_decorrenza = date('1942-04-04')
```

**Proprietà relazione (da §3.1):**
- `tipo_citazione`: `richiamo` | `riferimento` | `rinvio_recettizio`
- `fonte_relazione`: "relazione_guardasigilli_1941" | "relazione_guardasigilli_1942"
- `certezza`: `esplicita` (link nel testo)
- `paragrafo_riferimento`: Numero paragrafo Relazione (es. "§595")

### 3.2 Relazione `commenta` (§3.6, #26)

**Definizione KG:** "Doctrinal commentary on legal texts"

**Da Brocardi:**
- `Spiegazione` → Dottrina `:commenta` Norma
- `Brocardi` → Dottrina `:commenta` Norma

```cypher
// Spiegazione commenta articolo
MATCH (d:Dottrina {node_id: $dottrina_id})
MATCH (n:Norma {URN: $norma_urn})
MERGE (d)-[r:commenta]->(n)
SET r.fonte_relazione = 'Brocardi.it',
    r.certezza = 'esplicita'
```

### 3.3 Relazione `interpreta` (§3.6, #25)

**Definizione KG:** "Judicial or doctrinal interpretation of a norm"

**Da Brocardi:**
- `Massime` → AttoGiudiziario `:interpreta` Norma

```cypher
// Massima interpreta articolo
MATCH (a:AttoGiudiziario {node_id: $atto_id})
MATCH (n:Norma {URN: $norma_urn})
MERGE (a)-[r:interpreta]->(n)
SET r.tipo_interpretazione = 'giurisprudenziale',
    r.orientamento = $orientamento,  // Se deducibile
    r.fonte_relazione = 'Brocardi.it',
    r.certezza = 'esplicita'
```

---

## 4. Nuove Proprietà da Aggiungere allo Schema

Per supportare i dati Brocardi, propongo queste **estensioni** allo schema Norma:

```yaml
# Estensioni proprietà Norma per Brocardi
Norma:
  properties_brocardi:
    relazione_libro_obbligazioni:
      type: String
      description: "Testo Relazione Guardasigilli al Libro Obbligazioni (1941)"
    relazione_codice_civile:
      type: String
      description: "Testo Relazione Grandi al Codice Civile (1942)"
    relazione_paragrafo_libro:
      type: String
      description: "Numero paragrafo Relazione Libro (es. '41')"
    relazione_paragrafo_codice:
      type: String
      description: "Numero paragrafo Relazione Codice (es. '595')"
    ratio_legis:
      type: String
      description: "Ratio legis dalla dottrina"
    brocardi_url:
      type: String
      description: "URL pagina Brocardi.it"
    brocardi_enriched_at:
      type: DateTime
      description: "Timestamp ultimo enrichment Brocardi"
```

---

## 5. Flusso Enrichment Completo

```
Per ogni articolo URN in FalkorDB:
│
├─1. Fetch Brocardi data
│   └─ BrocardiScraper.get_info(norma_visitata)
│
├─2. Update Norma node
│   ├─ SET relazione_libro_obbligazioni
│   ├─ SET relazione_codice_civile
│   ├─ SET ratio_legis
│   └─ SET brocardi_url, brocardi_enriched_at
│
├─3. Create Dottrina nodes (se non esistono)
│   ├─ Spiegazione → Dottrina
│   └─ Brocardi[] → Dottrina (multiple)
│
├─4. Create AttoGiudiziario nodes (se non esistono)
│   └─ Massime[] → AttoGiudiziario (multiple)
│
├─5. Create Relations
│   ├─ articoli_citati → :cita (Norma→Norma)
│   ├─ Spiegazione → :commenta (Dottrina→Norma)
│   ├─ Brocardi → :commenta (Dottrina→Norma)
│   └─ Massime → :interpreta (AttoGiudiziario→Norma)
│
└─6. Update Bridge Table
    └─ Nuovi mappings per Dottrina e AttoGiudiziario
```

---

## 6. Validazione Mapping

### Query di Verifica Post-Enrichment

```cypher
// 1. Articoli con Relazione Guardasigilli
MATCH (n:Norma)
WHERE n.relazione_codice_civile IS NOT NULL
RETURN count(n) as articoli_con_relazione

// 2. Relazioni cita create
MATCH ()-[r:cita {fonte_relazione: 'relazione_guardasigilli_1942'}]->()
RETURN count(r) as citazioni_da_relazione

// 3. Dottrina create
MATCH (d:Dottrina {fonte: 'Brocardi.it'})
RETURN d.tipo, count(*) as count

// 4. AttoGiudiziario creati
MATCH (a:AttoGiudiziario)<-[:interpreta]-(n:Norma)
WHERE a.fonte = 'Brocardi.it'
RETURN count(DISTINCT a) as massime_create

// 5. Densità grafo post-enrichment
MATCH (n:Norma)-[r]->()
RETURN type(r) as relazione, count(*) as count
ORDER BY count DESC
```

---

## 7. Esempi Concreti

### Art. 1285 c.c. (Obbligazione Alternativa)

**Input Brocardi:**
```json
{
  "Relazioni": [
    {
      "tipo": "codice_civile",
      "numero_paragrafo": "595",
      "testo": "Il nuovo codice presenta, negli art. 1286 e 1287...",
      "articoli_citati": [
        {"numero": "1286", "titolo": "Facoltà di scelta"},
        {"numero": "1287", "titolo": "Decadenza dalla facoltà di scelta"},
        {"numero": "665", "titolo": "Scelta nel legato alternativo"}
      ]
    }
  ]
}
```

**Output Graph:**
```
(Art.1285:Norma)
  ├─[:cita {fonte: 'relazione_guardasigilli_1942', §: '595'}]→ (Art.1286:Norma)
  ├─[:cita {fonte: 'relazione_guardasigilli_1942', §: '595'}]→ (Art.1287:Norma)
  └─[:cita {fonte: 'relazione_guardasigilli_1942', §: '595'}]→ (Art.665:Norma)

Properties Art.1285:
  relazione_codice_civile: "Il nuovo codice presenta..."
  relazione_paragrafo_codice: "595"
```

---

*Documento creato: 2025-12-04*
*Riferimento: docs/02-methodology/knowledge-graph.md*
