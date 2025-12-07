# Schema Definitivo: API → Knowledge Graph

**Version**: 1.0 - FINALE
**Date**: 3 Dicembre 2025
**Status**: 🔒 LOCKED - Non modificare senza approval

---

## ⚠️ IMPORTANTE: Decisioni Una Tantum

Questo schema è **definitivo**. Modifiche future richiedono:
1. Migrazione dati esistenti
2. Aggiornamento documentazione
3. Re-test completo

**Principle**: Decidiamo ora tutte le properties, poi no-touch.

---

## 1. Output VisualexAPI - Spec Completa

### 1.1 API Endpoint

```http
GET http://localhost:8080/get-all-data
Params:
  - act_type: "codice civile"
  - article: "1453"
  - date: "1942"         (optional, ma per CC è hardcoded)
  - act_number: "262"    (optional, ma per CC è hardcoded)
  - version: null        (optional, per multivigenza futura)
  - version_date: null   (optional)
```

### 1.2 Response JSON - Completa

```json
{
  "norma_data": {
    "norma": {
      "tipo_atto": "codice civile",
      "data": "1942-03-16",
      "numero_atto": "262",
      "titolo": "Codice Civile",
      "autorita_emanante": "Regio Decreto"
    },
    "numero_articolo": "1453",
    "versione": null,
    "data_versione": null,
    "allegato": null
  },

  "article_text": "Articolo 1453\nRisoluzione per inadempimento\n\nNei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie le sue obbligazioni, l'altro può a sua scelta chiedere l'adempimento o la risoluzione del contratto, salvo, in ogni caso, il risarcimento del danno.\n\nLa risoluzione può essere domandata anche quando il giudizio è stato promosso per ottenere l'adempimento; ma non può più chiedersi l'adempimento quando è stata domandata la risoluzione.",

  "url": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262~art1453",

  // ⚠️ NOTA: URL non include allegato! Dobbiamo aggiungerlo noi basandoci su tipo_atto
  // URL corretto per CC: ...;262:2~art1453

  "brocardi_info": {
    "Position": "Libro IV - Delle obbligazioni, Titolo II - Dei contratti in generale, Capo XIV - Della risoluzione del contratto",

    "Ratio": "Fondamento normativo del rimedio risolutorio nei contratti con prestazioni corrispettive. Tutela la parte adempiente offrendo alternative: adempimento forzato o scioglimento del vincolo contrattuale.",

    "Spiegazione": "L'articolo disciplina la risoluzione per inadempimento nei contratti sinallagmatici. Il contraente non inadempiente ha diritto di scelta tra:\n1) Azione di adempimento (art. 2930 c.c.)\n2) Azione di risoluzione\n\nLa giurisprudenza richiede che l'inadempimento sia di \"non scarsa importanza\" (art. 1455 c.c.) per giustificare la risoluzione.",

    "Massime": [
      {
        "corte": "Cassazione",
        "numero": "15353/2020",
        "estratto": "La domanda di risoluzione e quella di adempimento sono alternative e incompatibili; la scelta è riservata alla parte non inadempiente."
      },
      {
        "corte": "Cassazione",
        "numero": "8524/2019",
        "estratto": "Il passaggio dalla domanda di adempimento a quella di risoluzione è sempre possibile, mentre il contrario non è ammesso se la risoluzione è già stata richiesta."
      }
    ],

    "Brocardi": [
      "Pacta sunt servanda",
      "Exceptio non adimpleti contractus"
    ]
  }
}
```

**Campo chiave**: `article_text` → **testo NON parsato**, dobbiamo farlo noi!

---

## 2. Comma Parser - Nostro Compito

### 2.1 Input

```
Articolo 1453
Risoluzione per inadempimento

Nei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie le sue obbligazioni, l'altro può a sua scelta chiedere l'adempimento o la risoluzione del contratto, salvo, in ogni caso, il risarcimento del danno.

La risoluzione può essere domandata anche quando il giudizio è stato promosso per ottenere l'adempimento; ma non può più chiedersi l'adempimento quando è stata domandata la risoluzione.
```

### 2.2 Parsing Rules

```python
def parse_article_structure(article_text: str) -> ArticleStructure:
    """
    Parse articolo in: titolo, rubrica, commi.

    Format atteso:
    Articolo NNNN
    [Rubrica]

    [Comma 1]

    [Comma 2]
    ...
    """
    lines = article_text.strip().split('\n')

    # 1. Extract numero articolo (prima riga)
    # Pattern: "Articolo 1453" o "Art. 1453" o "1453."
    numero_match = re.search(r'(?:Articolo|Art\.?)\s+(\d+(?:[\s\-]?(?:bis|ter|quater)?)?)', lines[0], re.I)
    numero_articolo = numero_match.group(1) if numero_match else None

    # 2. Extract rubrica (seconda riga non vuota)
    rubrica = None
    comma_start_idx = 1
    for i, line in enumerate(lines[1:], start=1):
        if line.strip():
            rubrica = line.strip()
            comma_start_idx = i + 1
            break

    # 3. Extract commi (paragrafi separati da \n\n)
    text_after_rubrica = '\n'.join(lines[comma_start_idx:])

    # Split su doppio newline o paragraph breaks
    raw_commas = re.split(r'\n\n+', text_after_rubrica.strip())

    # Pulisci e numera
    commas = []
    for idx, comma_text in enumerate(raw_commas, start=1):
        cleaned = comma_text.strip()
        if cleaned and len(cleaned) > 10:  # Skip linee troppo corte
            commas.append(Comma(
                numero=idx,
                testo=cleaned,
                token_count=count_tokens(cleaned)
            ))

    return ArticleStructure(
        numero_articolo=numero_articolo,
        rubrica=rubrica,
        commas=commas
    )
```

### 2.3 Output Atteso per Art. 1453

```python
ArticleStructure(
    numero_articolo="1453",
    rubrica="Risoluzione per inadempimento",
    commas=[
        Comma(
            numero=1,
            testo="Nei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie le sue obbligazioni, l'altro può a sua scelta chiedere l'adempimento o la risoluzione del contratto, salvo, in ogni caso, il risarcimento del danno.",
            token_count=45
        ),
        Comma(
            numero=2,
            testo="La risoluzione può essere domandata anche quando il giudizio è stato promosso per ottenere l'adempimento; ma non può più chiedersi l'adempimento quando è stata domandata la risoluzione.",
            token_count=35
        )
    ]
)
```

---

## 3. Knowledge Graph Schema - DEFINITIVO

### 3.1 Node Types (6 tipi)

#### A. Norma (Node Type Primario)

**Subtypes** (via property `tipo_documento`):
- `codice`: Root document (es. Codice Civile)
- `libro`: Libro del codice (es. Libro IV)
- `titolo`: Titolo interno (es. Titolo II)
- `articolo`: Articolo specifico

**Properties COMPLETE** (21 properties):

```cypher
(:Norma {
  // Identifiers (PRIMARY KEY: URN)
  URN: string,                    // UNIQUE, es. "urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453~comma1"
                                  // Con :2 (allegato CC) + comma per granularità interna
  node_id: string,                // Deprecato ma kept per compatibility = URN
  url: string,                    // URL Normattiva SENZA comma: "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453"
                                  // Per linking frontend al sito ufficiale (include :2 allegato)

  // Classification
  tipo_documento: string,         // "codice" | "libro" | "titolo" | "articolo"
  estremi: string,                // "Art. 1453 c.c." (human-readable)
  numero_articolo: string,        // "1453" (solo per tipo=articolo)
  numero_libro: string,           // "IV" (solo per tipo=libro)
  numero_titolo: string,          // "II" (solo per tipo=titolo)

  // Content
  rubrica: string,                // "Risoluzione per inadempimento"
  testo_vigente: string,          // Full text (per articolo) o null (per codice/libro/titolo)
  titolo: string,                 // "Codice Civile" (per codice), "Obbligazioni" (per libro)

  // Metadata
  fonte: string,                  // "VisualexAPI" | "Normattiva" | "Manual"
  autorita_emanante: string,      // "Regio Decreto" | "Parlamento" | etc.
  data_pubblicazione: date,       // "1942-03-16"
  data_entrata_vigore: date,      // Di solito = data_pubblicazione (o null)

  // Status
  vigenza: string,                // "vigente" | "abrogato" | "modificato"
  stato: string,                  // Alias di vigenza (kept per compatibility)
  efficacia: string,              // "permanente" | "temporanea"

  // Hierarchy
  ambito_territoriale: string,    // "nazionale" | "regionale" | "comunale"

  // Timestamps
  created_at: datetime,           // Auto-populated
  updated_at: datetime            // Auto-populated
})
```

**Constraints**:
- `URN`: UNIQUE (con allegato + comma per granularità: `;262:2~art1453~comma1`)
- `url`: NOT NULL per articoli (con allegato, senza comma: `;262:2~art1453`)
- `tipo_documento`: NOT NULL
- `vigenza`: NOT NULL, DEFAULT "vigente"

**Note su Allegati**:
- Il Codice Civile è l'**Allegato 2** (`:2`) del R.D. 262/1942
- Le Preleggi sono l'**Allegato 1** (`:1`) dello stesso R.D.
- Formato URN completo: `urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453`
  - `262` = numero atto
  - `:2` = allegato (Codice Civile)
  - `~art1453` = articolo

---

#### B. ConcettoGiuridico

**Properties COMPLETE** (9 properties):

```cypher
(:ConcettoGiuridico {
  // Identifiers (PRIMARY KEY: node_id)
  node_id: string,                // UNIQUE, es. "concetto_risoluzione_contratto"

  // Content
  denominazione: string,          // "Risoluzione del contratto"
  definizione: string,            // Definizione estesa (opzionale)
  categoria: string,              // "diritto_civile_obbligazioni" | "diritto_penale" | etc.

  // Classification
  tipo_concetto: string,          // "istituto" | "principio" | "nozione" | "rimedio"
  area_giuridica: string,         // "civile" | "penale" | "amministrativo" | etc.

  // Metadata
  fonte: string,                  // "NER" | "Brocardi" | "Manual"

  // Timestamps
  created_at: datetime,
  updated_at: datetime
})
```

**Naming Convention**:
```python
# Format: concetto_{denominazione_snake_case}
# Examples:
"concetto_risoluzione_contratto"
"concetto_inadempimento"
"concetto_obbligazione_solidale"
"concetto_responsabilita_extracontrattuale"
```

---

#### C. Dottrina (Commenti da Brocardi)

**Properties COMPLETE** (10 properties):

```cypher
(:Dottrina {
  // Identifiers (PRIMARY KEY: node_id)
  node_id: string,                // UNIQUE, es. "dottrina_brocardi_art1453"

  // Content
  titolo: string,                 // "Brocardi: Ratio Art. 1453"
  descrizione: string,            // Full text da brocardi_info.Ratio o .Spiegazione
  tipo_dottrina: string,          // "ratio" | "spiegazione" | "commento"

  // Source
  fonte: string,                  // "Brocardi.it" | "Dottrina manuale" | etc.
  autore: string,                 // "Brocardi.it" (generico) o nome autore se disponibile
  url_fonte: string,              // URL Brocardi (se disponibile)

  // Metadata
  lingua: string,                 // "it" (italiano)
  confidence: float,              // 0.9 (alta per Brocardi, lower per altre fonti)

  // Timestamps
  created_at: datetime,
  updated_at: datetime
})
```

**Naming Convention**:
```python
# Format: dottrina_{fonte}_{article_ref}_{tipo}
# Examples:
"dottrina_brocardi_art1453_ratio"
"dottrina_brocardi_art1453_spiegazione"
```

---

#### D. AttoGiudiziario (Sentenze/Massime)

**Properties COMPLETE** (14 properties):

```cypher
(:AttoGiudiziario {
  // Identifiers (PRIMARY KEY: node_id)
  node_id: string,                // UNIQUE, es. "massima_cass_15353_2020"

  // Identification
  estremi: string,                // "Cass. 15353/2020"
  organo_emittente: string,       // "Cassazione" | "Corte Costituzionale" | "TAR" | etc.
  numero_sentenza: string,        // "15353"
  anno: string,                   // "2020"

  // Content
  massima: string,                // Estratto breve (da Brocardi)
  testo_completo: string,         // Full text (se disponibile, altrimenti null)

  // Classification
  tipo_atto: string,              // "sentenza" | "ordinanza" | "decreto"
  sezione: string,                // "Sezione Civile", "Sezione Penale", etc.

  // Source
  fonte: string,                  // "Brocardi.it" | "ItalianLII" | etc.
  url_fonte: string,              // URL della sentenza

  // Metadata
  confidence: float,              // 0.9 per Brocardi

  // Timestamps
  data_pubblicazione: date,       // Data sentenza (se disponibile)
  created_at: datetime,
  updated_at: datetime
})
```

**Naming Convention**:
```python
# Format: massima_{organo}_{numero}_{anno}
# Examples:
"massima_cass_15353_2020"
"massima_cortecost_234_2021"
```

---

### 3.2 Relation Types (5 tipi)

#### A. contiene (Hierarchical)

```cypher
(:Norma)-[:contiene {
  certezza: float,                // 1.0 (sempre esplicita per gerarchia strutturale)
  tipo: string,                   // "esplicita" (hardcoded)
  created_at: datetime
}]->(:Norma)
```

**Usage**:
- `Codice` -[:contiene]-> `Libro`
- `Libro` -[:contiene]-> `Titolo`
- `Titolo` -[:contiene]-> `Articolo`
- `Articolo` -[:contiene]-> `Comma` (se commi modellati come nodi)

---

#### B. disciplina (Normative → Concept)

```cypher
(:Norma)-[:disciplina {
  certezza: float,                // 0.7-0.95 (da NER confidence)
  tipo: string,                   // "diretta" | "inferita"
  fonte: string,                  // "NER" | "Brocardi" | "Manual"
  created_at: datetime
}]->(:ConcettoGiuridico)
```

**Usage**:
- `Art. 1453` -[:disciplina {certezza: 0.95}]-> `risoluzione_contratto`

---

#### C. commenta (Doctrine → Norm)

```cypher
(:Dottrina)-[:commenta {
  certezza: float,                // 0.9 (alta per Brocardi)
  tipo: string,                   // "esplicita"
  fonte: string,                  // "Brocardi.it"
  created_at: datetime
}]->(:Norma)
```

**Usage**:
- `Dottrina(ratio)` -[:commenta]-> `Art. 1453`

---

#### D. interpreta (Jurisprudence → Norm)

```cypher
(:AttoGiudiziario)-[:interpreta {
  certezza: float,                // 0.9 (Brocardi link esplicito)
  tipo_interpretazione: string,   // "giurisprudenziale" | "costituzionale"
  fonte: string,                  // "Brocardi.it"
  created_at: datetime
}]->(:Norma)
```

**Usage**:
- `Massima(Cass. 15353/2020)` -[:interpreta]-> `Art. 1453`

---

#### E. rinvia (Norm → Norm reference)

```cypher
(:Norma)-[:rinvia {
  certezza: float,                // 0.75 (pattern-matched)
  tipo_rinvio: string,            // "esplicito" | "implicito"
  testo_riferimento: string,      // "come previsto dall'art. 1455"
  created_at: datetime
}]->(:Norma)
```

**Usage**:
- `Art. 1453` -[:rinvia]-> `Art. 1455` (se testo menziona "art. 1455")

---

## 4. Mapping API → Knowledge Graph

### 4.1 Flow Dettagliato

```
VisualexAPI Response
        ↓
[1. Parse Commas]
    ├─ numero_articolo
    ├─ rubrica
    └─ List<Comma>
        ↓
[2. Create Nodes]
    ├─ Norma(Codice) - 1x per batch
    ├─ Norma(Libro) - 1x per batch
    ├─ Norma(Titolo) - 1x per batch
    ├─ Norma(Articolo) - 1x per article
    ├─ ConcettoGiuridico - N per article (NER extraction)
    ├─ Dottrina - 0-2 per article (Ratio, Spiegazione)
    └─ AttoGiudiziario - 0-M per article (Massime)
        ↓
[3. Create Relations]
    ├─ Codice -[contiene]-> Libro
    ├─ Libro -[contiene]-> Titolo
    ├─ Titolo -[contiene]-> Articolo
    ├─ Articolo -[disciplina]-> Concetti
    ├─ Dottrina -[commenta]-> Articolo
    ├─ AttoGiudiziario -[interpreta]-> Articolo
    └─ Articolo -[rinvia]-> Altri Articoli (se presenti nel testo)
        ↓
[4. Chunking]
    For each Comma:
        ├─ Create Chunk (text, URN with ~comma{N})
        ├─ Generate embedding (E5-large, post-ingestion)
        └─ Store in Qdrant
        ↓
[5. Bridge Table]
    For each Chunk:
        ├─ PRIMARY: chunk_id → articolo_urn (1.0 confidence)
        ├─ HIERARCHIC: chunk_id → libro_urn (0.95)
        ├─ HIERARCHIC: chunk_id → titolo_urn (0.95)
        ├─ CONCEPT: chunk_id → concept_urn (0.7-0.9)
        └─ REFERENCE: chunk_id → referenced_art_urn (0.75)
```

### 4.2 Property Mapping Table

| API Field | Node Type | Property | Transform | Example |
|-----------|-----------|----------|-----------|---------|
| `norma_data.norma.tipo_atto` | Norma | - | Used for URN generation | "codice civile" |
| `norma_data.norma.data` | Norma | `data_pubblicazione` | ISO date | "1942-03-16" |
| `norma_data.norma.numero_atto` | Norma | - | Used for URN generation | "262" |
| `norma_data.norma.titolo` | Norma(codice) | `titolo` | Direct | "Codice Civile" |
| `norma_data.norma.autorita_emanante` | Norma | `autorita_emanante` | Direct | "Regio Decreto" |
| `norma_data.numero_articolo` | Norma(articolo) | `numero_articolo` | Direct | "1453" |
| `article_text` | Norma(articolo) | `testo_vigente` | Direct (full text) | "Articolo 1453..." |
| `article_text` (parsed) | Norma(articolo) | `rubrica` | Extract via regex | "Risoluzione per inadempimento" |
| `url` | Norma(articolo) | `url` | Extract URN + add annex :2 (from map.py) | "https://www.normattiva.it/...;262:2~art1453" |
| `url` | Norma(articolo) | `URN` | Extract URN + add annex :2 + ~comma{N} | "urn:nir:...;262:2~art1453~comma1" |
| `norma_data.allegato` | Norma(articolo) | - | Used for URN construction (if present) | "2" |
| `brocardi_info.Position` | Norma(libro/titolo) | `titolo` | Parse hierarchy | "Libro IV - Obbligazioni" |
| `brocardi_info.Ratio` | Dottrina | `descrizione` | Direct | "Fondamento normativo..." |
| `brocardi_info.Spiegazione` | Dottrina | `descrizione` | Direct | "L'articolo disciplina..." |
| `brocardi_info.Massime[].corte` | AttoGiudiziario | `organo_emittente` | Direct | "Cassazione" |
| `brocardi_info.Massime[].numero` | AttoGiudiziario | `numero_sentenza` | Extract | "15353/2020" → "15353", "2020" |
| `brocardi_info.Massime[].estratto` | AttoGiudiziario | `massima` | Direct | "La domanda di risoluzione..." |

---

## 5. Decisioni Chiave Motivate

### 5.1 Perché `URN` come PRIMARY KEY?

- ✅ **Standardizzato**: Format NIR (Normattiva Italiana)
- ✅ **Globally unique**: Identifica univocamente ogni norma (anche a livello comma)
- ✅ **Stable**: Non cambia nel tempo (a differenza di node_id custom)
- ✅ **Granular**: Supporta comma-level tracking con `~comma{N}` extension

### 5.2 Perché Separare `URN` (interno) e `url` (esterno)?

- ⚠️ **Limitazione Normattiva**: Il sito ufficiale non supporta comma negli URL
- ✅ **URN interno** (`;262:2~art1453~comma1`): Include allegato `:2` + comma per granularità
- ✅ **URL esterno** (`;262:2~art1453`): Include allegato `:2`, truncato ad articolo (no comma)
- ✅ **Dual-track**: Massima precisione interna + usabilità frontend
- 📌 **Example Codice Civile**:
  - URN: `urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453~comma1`
  - URL: `https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453`
- 📌 **Note Allegati**:
  - Allegato 1 (`:1`) = Preleggi
  - Allegato 2 (`:2`) = Codice Civile

### 5.3 Perché Separare `tipo_documento`?

- ✅ **Query efficient**: `MATCH (n:Norma {tipo_documento: 'articolo'})` più veloce di label separati
- ✅ **Schema flexibility**: Possiamo aggiungere "capo", "sezione" senza schema migration
- ✅ **Unified model**: Tutte le norme condividono properties comuni

### 5.4 Perché `certezza` invece di `confidence`?

- ✅ **Domain-specific**: Terminologia giuridica (certezza esplicita vs inferita)
- ✅ **Interpretability**: Più chiaro per giuristi
- ⚠️ **Però usiamo `confidence` nei nodi** per consistency con ML (es. NER confidence)

### 5.5 Perché `node_id` = `URN` per Norma?

- ⚠️ **Deprecato** ma mantenuto per backward compatibility
- Future: Usare solo `URN` come identifier, eliminare `node_id`

---

## 6. Validazione Schema

### 6.1 Consistency Checks

```cypher
// Check 1: All Norma nodes have URN
MATCH (n:Norma)
WHERE n.URN IS NULL
RETURN count(n) AS missing_urn
// Expected: 0

// Check 2: All articolo have testo_vigente
MATCH (n:Norma {tipo_documento: 'articolo'})
WHERE n.testo_vigente IS NULL OR n.testo_vigente = ''
RETURN count(n) AS missing_text
// Expected: 0

// Check 3: All certezza in valid range
MATCH ()-[r]->()
WHERE r.certezza IS NOT NULL AND (r.certezza < 0 OR r.certezza > 1)
RETURN type(r), r.certezza
// Expected: 0 rows

// Check 4: All ConcettoGiuridico have denominazione
MATCH (c:ConcettoGiuridico)
WHERE c.denominazione IS NULL OR c.denominazione = ''
RETURN count(c)
// Expected: 0
```

### 6.2 Property Coverage (Target)

| Node Type | Min Properties | Critical Properties |
|-----------|---------------|---------------------|
| Norma(codice) | 10 | URN, titolo, tipo_documento, data_pubblicazione |
| Norma(articolo) | 12 | URN, numero_articolo, rubrica, testo_vigente, estremi |
| ConcettoGiuridico | 6 | node_id, denominazione, categoria |
| Dottrina | 7 | node_id, titolo, descrizione, fonte |
| AttoGiudiziario | 9 | node_id, estremi, organo_emittente, massima |

---

## 7. Esempio Concreto: Art. 1453

### Input (VisualexAPI)

```json
{
  "norma_data": {...},
  "article_text": "Articolo 1453\nRisoluzione per inadempimento\n\nNei contratti...",
  "url": "...",
  "brocardi_info": {...}
}
```

### Output (Knowledge Graph)

**Nodes Created (9)**:
1. `Norma` (codice): URN=`urn:nir:stato:regio.decreto:1942-03-16;262:2`, titolo="Codice Civile"
2. `Norma` (libro): URN=`urn:nir:stato:regio.decreto:1942-03-16;262:2~libro4`, titolo="Obbligazioni"
3. `Norma` (titolo): URN=`urn:nir:stato:regio.decreto:1942-03-16;262:2~libro4~tit2`, titolo="Contratti in generale"
4. `Norma` (articolo):
   - URN=`urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453`
   - url=`https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453`
   - numero_articolo="1453", rubrica="Risoluzione per inadempimento"
5. `ConcettoGiuridico`: node_id="concetto_risoluzione_contratto"
6. `ConcettoGiuridico`: node_id="concetto_inadempimento"
7. `Dottrina`: node_id="dottrina_brocardi_art1453_ratio"
8. `AttoGiudiziario`: node_id="massima_cass_15353_2020"
9. `AttoGiudiziario`: node_id="massima_cass_8524_2019"

**Relations Created (11)**:
1. codice -[contiene {certezza:1.0}]-> libro
2. libro -[contiene {certezza:1.0}]-> titolo
3. titolo -[contiene {certezza:1.0}]-> articolo
4. articolo -[disciplina {certezza:0.95}]-> risoluzione_contratto
5. articolo -[disciplina {certezza:0.90}]-> inadempimento
6. dottrina_ratio -[commenta {certezza:0.9}]-> articolo
7. massima_15353 -[interpreta {certezza:0.9}]-> articolo
8. massima_8524 -[interpreta {certezza:0.9}]-> articolo
9. articolo -[rinvia {certezza:0.75}]-> art1455 (da testo "art. 1455")
10. articolo -[rinvia {certezza:0.75}]-> art2930 (da Brocardi "art. 2930")
11. articolo -[rinvia {certezza:0.75}]-> art1454 (inferito da struttura)

**Chunks Created (2)**:
1. Chunk(comma1):
   - URN=`urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453~comma1`
   - text="Nei contratti con prestazioni corrispettive..."
2. Chunk(comma2):
   - URN=`urn:nir:stato:regio.decreto:1942-03-16;262:2~art1453~comma2`
   - text="La risoluzione può essere domandata..."

**Bridge Mappings Created (10)**:
- chunk1 (`;262:2~art1453~comma1`) → `urn:...;262:2~art1453` (PRIMARY, conf=1.0)
- chunk1 → `urn:...;262:2~libro4` (HIERARCHIC, conf=0.95)
- chunk1 → `urn:...;262:2~libro4~tit2` (HIERARCHIC, conf=0.95)
- chunk1 → `concetto_risoluzione_contratto` (CONCEPT, conf=0.95)
- chunk1 → `concetto_inadempimento` (CONCEPT, conf=0.90)
- chunk2 (`;262:2~art1453~comma2`) → `urn:...;262:2~art1453` (PRIMARY, conf=1.0)
- chunk2 → `urn:...;262:2~libro4` (HIERARCHIC, conf=0.95)
- chunk2 → `urn:...;262:2~libro4~tit2` (HIERARCHIC, conf=0.95)
- chunk2 → `concetto_risoluzione_contratto` (CONCEPT, conf=0.85)
- chunk2 → `urn:...;262:2~art1455` (REFERENCE, conf=0.75)

---

## 8. Migration Path (Futuro)

Se servono modifiche:

1. **Adding property**: OK, null-safe
2. **Removing property**: Requires data migration
3. **Renaming property**: Create new + copy data + delete old
4. **Changing type**: Complex migration needed

**Recommendation**: Design now, no touch later.

---

**Status**: 🔒 **LOCKED & APPROVED**

Next: Implementation di comma parser + structural chunker.
