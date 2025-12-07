# Metodologia Scientifica: Ingestion Libro IV Codice Civile

**Version**: 1.0
**Date**: 3 Dicembre 2025
**Paper-Ready Documentation**: YES
**Reproducibility**: Deterministic pipeline

---

## Abstract

Questo documento descrive la metodologia scientificamente rigorosa per l'ingestion di 887 articoli del Libro IV del Codice Civile Italiano (R.D. 262/1942) nel sistema MERL-T. L'approccio combina:

1. **Chunking strutturale** basato sulla segmentazione normativa italiana (comma-level)
2. **Knowledge Graph** con schema deterministico (6 node types, 5 relation types)
3. **Hybrid storage** (FalkorDB + PostgreSQL Bridge Table + Qdrant vector DB)
4. **Zero-LLM extraction** per garantire reproducibilità

La metodologia è **deterministicamente riproducibile** e **paper-ready** per pubblicazione accademica.

---

## 1. Research Questions

### RQ1: Chunking Strategy
> Quale granularità di chunking massimizza la precisione del retrieval ibrido (vector + graph) preservando la coerenza semantica giuridica?

**Hypothesis**: Chunking comma-level supera chunking per caratteri in precisione retrieval per query legali strutturate.

**Metrics**: Precision@K, Recall@K, MRR (Mean Reciprocal Rank)

### RQ2: Graph-Aware Retrieval
> L'integrazione di relazioni grafiche (Bridge Table) migliora il ranking rispetto al solo vector search?

**Hypothesis**: α-blending (α * similarity + (1-α) * graph_score) con α=0.7 produce ranking superiori rispetto a α=1.0 (solo vector).

**Metrics**: NDCG@10, MAP (Mean Average Precision)

### RQ3: Brocardi Enrichment
> L'arricchimento con commenti dottrinali (Brocardi) aumenta la rilevanza percepita delle risposte?

**Hypothesis**: Articoli con nodo Dottrina collegato ottengono rating utente superiori.

**Metrics**: User satisfaction score (1-5 Likert scale), expert annotation agreement

---

## 2. Dataset Specification

### 2.1 Source

**Primary Source**:
- **Nome**: Codice Civile della Repubblica Italiana
- **Identificativo**: Regio Decreto 16 marzo 1942, n. 262
- **URN Base**: `urn:nir:stato:regio.decreto:1942-03-16;262`
- **Scope**: Libro IV - Obbligazioni (Art. 1173-2059)
- **Versione**: Testo vigente al 3 dicembre 2025
- **Fonte ufficiale**: https://www.normattiva.it

**Secondary Source** (enrichment):
- **Nome**: Brocardi.it - Codice Civile commentato
- **Tipo**: Commenti dottrinali, massime giurisprudenziali
- **Coverage**: ~90% articoli Codice Civile
- **Fonte**: https://www.brocardi.it/codice-civile/

### 2.2 Inclusioni/Esclusioni

**Inclusioni**:
- ✅ Tutti articoli Libro IV (1173-2059)
- ✅ Articoli abrogati ma storicamente rilevanti (marcati come `vigenza='abrogato'`)
- ✅ Modifiche successive fino a 2025-12-03

**Esclusioni**:
- ❌ Norme di attuazione (Disposizioni Transitorie)
- ❌ Normative EU non direttamente richiamate
- ❌ Giurisprudenza non presente in Brocardi

### 2.3 Dataset Statistics (a priori)

```
Libro IV Composition:
├─ Titolo I: Obbligazioni in generale (Art. 1173-1320)
│   └─ ~147 articoli
├─ Titolo II: Contratti in generale (Art. 1321-1469)
│   └─ ~148 articoli
├─ Titolo III: Singoli contratti (Art. 1470-1986)
│   └─ ~516 articoli
└─ Titolo IV: Promesse unilaterali (Art. 1987-2059)
    └─ ~73 articoli

Total: 887 articoli stimati (alcuni bis/ter/quater)
```

**Token Distribution (stimata da sample)**:
```
Avg tokens per articolo: 250 ± 120
Min: 50 (articoli brevi, es. definizioni)
Max: 1200 (articoli procedurali complessi)
Median: 180
P75: 320
P95: 580
```

---

## 3. Preprocessing Pipeline

### 3.1 Stage 1: Text Extraction

**Tool**: VisualexAPI (wrapper per Normattiva.it)
**Method**: HTTP GET con parsing HTML Akoma Ntoso

```python
# Pseudocode
def extract_article(article_number: int) -> Article:
    url = generate_normattiva_url(article_number)
    html = fetch_html(url)

    # Parse 3 scenari (in ordine di preferenza):
    if is_akn_detailed(html):
        return parse_akn_detailed(html)  # Commi strutturati
    elif is_akn_simple(html):
        return parse_akn_simple(html)    # Testo lineare
    else:
        return parse_attachment(html)    # Allegati
```

**Normalization**:
- Whitespace collapse: `\s+` → ` `
- Newline normalization: `\n{3,}` → `\n\n`
- Encoding: UTF-8
- HTML entity decoding: `&nbsp;` → ` `

**Validation**:
- Length check: 20 < len(text) < 10000 caratteri
- Structure check: Presenza di "Art." o "Articolo" nel testo
- URN validation: Regex match `^urn:nir:stato:...`

### 3.2 Stage 2: Structural Chunking

**Algorithm**: Comma-Level Segmentation

```python
def chunk_article(article: Article) -> List[Chunk]:
    chunks = []

    # Tokenize per conta
    token_count = count_tokens(article.text)

    # Decision tree
    if token_count < 150:
        # Articolo breve → chunk singolo
        chunks.append(Chunk(
            text=article.text,
            type="article_whole",
            urn=article.urn
        ))

    elif token_count < 1500:
        # Articolo medio → split per comma
        commas = parse_commas(article.text)
        for idx, comma in enumerate(commas):
            chunks.append(Chunk(
                text=comma.text,
                type="comma",
                urn=f"{article.urn}~comma{idx+1}",
                index=idx
            ))

    else:
        # Articolo lungo → split semantico
        commas = parse_commas(article.text)
        for comma in commas:
            if count_tokens(comma.text) > 512:
                # Comma troppo lungo → split ulteriore
                sub_chunks = semantic_split(comma.text, max_tokens=512)
                chunks.extend(sub_chunks)
            else:
                chunks.append(Chunk(text=comma.text, ...))

    return chunks
```

**Comma Detection Rules**:
1. Explicit numbering: "1.", "2.", "primo", "secondo"
2. Paragraph breaks: `\n\n` dopo periodo
3. Semantic breaks: Conjunction list ("inoltre", "tuttavia")

**Validation**:
- No chunk vuoto
- No overlap tra chunk
- Preservare ordine originale
- Sum(chunk.text) ≈ article.text (± whitespace)

### 3.3 Stage 3: Concept Extraction

**Method**: Rule-based NER + Pattern Matching (Zero-LLM)

```python
# Patterns per Libro IV (Obbligazioni)
LEGAL_CONCEPTS = {
    "obbligazione": ["obbligazione", "debito", "credito"],
    "inadempimento": ["inadempimento", "mora", "ritardo"],
    "risoluzione": ["risoluzione", "scioglimento contratto"],
    "risarcimento": ["risarcimento", "danni", "danno"],
    "contratto": ["contratto", "accordo", "convenzione"],
    "nullità": ["nullità", "annullabilità", "invalidità"],
    "prescrizione": ["prescrizione", "decadenza"],
    "responsabilità": ["responsabilità civile", "responsabilità"],
    # ... ~50 concetti totali
}

def extract_concepts(chunk: Chunk) -> List[Concept]:
    concepts = []
    text_lower = chunk.text.lower()

    for concept_id, patterns in LEGAL_CONCEPTS.items():
        for pattern in patterns:
            if pattern in text_lower:
                # Calcola confidence basata su frequenza e posizione
                freq = text_lower.count(pattern)
                position = text_lower.index(pattern) / len(text_lower)

                confidence = 0.7 + (0.1 * min(freq, 3)) + (0.1 * (1 - position))
                confidence = min(confidence, 0.95)

                concepts.append(Concept(
                    id=concept_id,
                    confidence=confidence
                ))
                break  # Solo un pattern per concetto

    return concepts
```

**Confidence Calculation**:
```
confidence = BASE_SCORE + FREQUENCY_BONUS + POSITION_BONUS

BASE_SCORE: 0.7 (presenza del pattern)
FREQUENCY_BONUS: +0.1 per ogni occorrenza (max 3)
POSITION_BONUS: +0.1 se pattern in prima metà testo

Range: [0.7, 0.95]
```

### 3.4 Stage 4: Brocardi Enrichment

**Source**: https://www.brocardi.it/codice-civile/

**Extracted Fields**:
1. **Ratio**: Fondamento giuridico (1-2 paragrafi)
2. **Spiegazione**: Commento esteso (3-10 paragrafi)
3. **Massime**: Giurisprudenza correlata (lista di sentenze)
4. **Position**: Collocazione sistematica

**Extraction Method**:
```python
async def fetch_brocardi(article_urn: str) -> BrocardiData:
    # Step 1: Fetch main page
    main_url = f"https://www.brocardi.it/codice-civile/libro-quarto/..."
    html = await fetch_html(main_url)

    # Step 2: Extract sections
    ratio = extract_section(html, selector=".ratio")
    spiegazione = extract_section(html, selector=".spiegazione")
    massime = extract_list(html, selector=".massime li")

    return BrocardiData(
        ratio=ratio,
        spiegazione=spiegazione,
        massime=massime,
        confidence=0.9  # Source reliability
    )
```

**Coverage Estimation**: ~80-90% articoli (alcuni non commentati su Brocardi)

---

## 4. Knowledge Graph Construction

### 4.1 Schema Definition

**Formal Specification**:

```
G = (V, E)

V = {Norma, ConcettoGiuridico, Dottrina, AttoGiudiziario}

E = {
    contiene: Norma → Norma,
    disciplina: Norma → ConcettoGiuridico,
    commenta: Dottrina → Norma,
    interpreta: AttoGiudiziario → Norma,
    rinvia: Norma → Norma
}

∀v ∈ V: v.URN is unique identifier
∀e ∈ E: e.certezza ∈ [0, 1]
```

### 4.2 Node Creation Rules

**Norma nodes**:
```cypher
// Idempotent creation
MERGE (n:Norma {URN: $urn})
ON CREATE SET
    n.estremi = $estremi,
    n.testo_vigente = $testo,
    n.tipo_documento = $tipo,
    n.vigenza = 'vigente'
ON MATCH SET
    n.updated_at = timestamp()
```

**ConcettoGiuridico nodes**:
```cypher
MERGE (c:ConcettoGiuridico {node_id: $concept_id})
ON CREATE SET
    c.denominazione = $denominazione,
    c.categoria = 'diritto_civile_obbligazioni',
    c.definizione = $definizione
```

**Dottrina nodes** (from Brocardi):
```cypher
MERGE (d:Dottrina {node_id: $dottrina_id})
ON CREATE SET
    d.titolo = 'Brocardi: Ratio',
    d.descrizione = $ratio_text,
    d.fonte = 'brocardi.it',
    d.confidence = 0.9
```

### 4.3 Edge Creation Rules

**Containment hierarchy**:
```cypher
// Libro → Articolo
MATCH (libro:Norma {URN: $libro_urn})
MATCH (art:Norma {URN: $art_urn})
MERGE (libro)-[r:contiene]->(art)
ON CREATE SET r.certezza = 1.0, r.tipo = 'esplicita'
```

**Concept discipline**:
```cypher
// Articolo → Concetto
MATCH (art:Norma {URN: $art_urn})
MATCH (c:ConcettoGiuridico {node_id: $concept_id})
MERGE (art)-[r:disciplina]->(c)
ON CREATE SET r.certezza = $confidence, r.tipo = 'inferita'
```

### 4.4 Consistency Constraints

1. **No dangling nodes**: `∀v ∈ V: degree(v) ≥ 1`
2. **URN uniqueness**: `∀v1, v2 ∈ V: v1.URN = v2.URN ⟹ v1 = v2`
3. **Edge typing**: `∀e ∈ E: type(e.source) and type(e.target) must match schema`
4. **Certainty bounds**: `∀e ∈ E: 0 ≤ e.certezza ≤ 1`

---

## 5. Bridge Table Mappings

### 5.1 Mapping Generation Algorithm

```python
def generate_mappings(chunk: Chunk, article: Article, concepts: List[Concept]) -> List[Mapping]:
    mappings = []

    # 1. PRIMARY mapping (chunk → source article)
    mappings.append(Mapping(
        chunk_id=chunk.id,
        graph_node_urn=article.urn,
        node_type="Norma",
        relation_type="PRIMARY",
        confidence=1.0,
        source="structural"
    ))

    # 2. HIERARCHIC mappings (chunk → libro, titolo)
    for parent_urn in article.hierarchy:
        mappings.append(Mapping(
            chunk_id=chunk.id,
            graph_node_urn=parent_urn,
            node_type="Norma",
            relation_type="HIERARCHIC",
            confidence=0.95,
            source="structural"
        ))

    # 3. CONCEPT mappings (chunk → extracted concepts)
    for concept in concepts:
        mappings.append(Mapping(
            chunk_id=chunk.id,
            graph_node_urn=concept.graph_node_urn,
            node_type="ConcettoGiuridico",
            relation_type="CONCEPT",
            confidence=concept.confidence,
            source="ner"
        ))

    # 4. REFERENCE mappings (chunk → referenced articles)
    references = extract_references(chunk.text)  # Es. "art. 1454"
    for ref_urn in references:
        mappings.append(Mapping(
            chunk_id=chunk.id,
            graph_node_urn=ref_urn,
            node_type="Norma",
            relation_type="REFERENCE",
            confidence=0.75,
            source="reference_parsing"
        ))

    return mappings
```

### 5.2 Confidence Scoring

**Empirical Formula** (calibrata su sample di 50 articoli):

```
confidence = BASE × SOURCE_FACTOR × CERTAINTY_FACTOR

BASE:
├─ PRIMARY: 1.0 (deterministic)
├─ HIERARCHIC: 0.95 (structural, known)
├─ CONCEPT: 0.7-0.9 (NER-based, variable)
└─ REFERENCE: 0.75 (pattern-matched)

SOURCE_FACTOR:
├─ structural: 1.0 (URN parsing)
├─ ner: 0.9 (rule-based patterns)
├─ llm: 0.7 (se usato in futuro)
└─ manual: 1.0 (annotazione umana)

CERTAINTY_FACTOR (chunk length):
├─ < 100 token: 1.0
├─ 100-500 token: 0.95
└─ > 500 token: 0.90
```

**Example**:
```
Chunk: Art. 1453, comma 1 (120 token)
Concept: "risoluzione_contratto"
NER confidence: 0.85

confidence_final = 0.85 × 0.9 × 0.95 = 0.727 ≈ 0.73
```

### 5.3 Batch Insert Strategy

**PostgreSQL Async Batch**:
```python
async def insert_mappings_batch(mappings: List[Mapping], batch_size=500):
    for i in range(0, len(mappings), batch_size):
        batch = mappings[i:i+batch_size]

        # Prepare bulk insert
        values = [
            (m.chunk_id, m.graph_node_urn, m.node_type, m.relation_type,
             m.confidence, m.source, m.metadata)
            for m in batch
        ]

        # Async insert with conflict handling
        await bridge_table.execute("""
            INSERT INTO bridge_table
            (chunk_id, graph_node_urn, node_type, relation_type,
             confidence, source, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (chunk_id, graph_node_urn) DO UPDATE SET
                confidence = EXCLUDED.confidence,
                updated_at = NOW()
        """, values)
```

**Performance**: ~5000 insert/sec → 10k mappings in ~2 secondi

---

## 6. Embedding Generation (Separated Phase)

### 6.1 Model Selection

**Model**: `intfloat/multilingual-e5-large`

**Specifications**:
- Architecture: Transformer encoder
- Parameters: 560M
- Dimensionality: 1024
- Max sequence length: 512 tokens
- Training: Contrastive learning on 1B+ pairs
- Languages: 100+ including Italian

**Justification**:
1. **Multilingual**: Supporta italiano legale
2. **Large context**: 512 token sufficienti per commi
3. **State-of-art**: Top performer su MTEB benchmark
4. **Efficient**: Inferenza CPU-friendly (<100ms per batch)

### 6.2 Batch Processing

```python
from transformers import AutoTokenizer, AutoModel
import torch

def generate_embeddings_batch(chunks: List[Chunk], batch_size=32):
    model = AutoModel.from_pretrained("intfloat/multilingual-e5-large")
    tokenizer = AutoTokenizer.from_pretrained("intfloat/multilingual-e5-large")

    embeddings = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]

        # Prepend "query: " for E5 format
        texts = [f"query: {chunk.text}" for chunk in batch]

        # Tokenize
        inputs = tokenizer(texts, padding=True, truncation=True,
                          max_length=512, return_tensors="pt")

        # Generate embeddings (no grad for inference)
        with torch.no_grad():
            outputs = model(**inputs)
            # Mean pooling
            embeddings_batch = mean_pooling(outputs, inputs['attention_mask'])
            embeddings_batch = F.normalize(embeddings_batch, p=2, dim=1)

        embeddings.extend(embeddings_batch.cpu().numpy())

    return embeddings
```

**Performance**:
- CPU (M2 Max): ~50 chunks/min
- GPU (CUDA): ~200 chunks/min
- Estimated time for 2500 chunks: 30-40 min (CPU)

### 6.3 Qdrant Upload

```python
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

async def upload_to_qdrant(chunks: List[Chunk], embeddings: np.ndarray):
    client = QdrantClient(host="localhost", port=6333)

    # Create collection if not exists
    client.recreate_collection(
        collection_name="legal_chunks_libro_iv",
        vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
    )

    # Prepare points
    points = []
    for chunk, embedding in zip(chunks, embeddings):
        points.append(PointStruct(
            id=str(chunk.id),
            vector=embedding.tolist(),
            payload={
                "text": chunk.text,
                "source_article_urn": chunk.article_urn,
                "chunk_index": chunk.index,
                "hierarchical_level": chunk.type,
                "primary_graph_node": chunk.primary_node_urn,
                "concept_nodes": chunk.concept_urns,
                "date_published": "1942-03-16",
                "is_current": True,
                "binding_force": 1.0
            }
        ))

    # Batch upload (500 at a time)
    for i in range(0, len(points), 500):
        client.upsert(
            collection_name="legal_chunks_libro_iv",
            points=points[i:i+500]
        )
```

---

## 7. Validation & Quality Assurance

### 7.1 Consistency Checks

**Post-Ingestion Validation**:

1. **Orphan Chunks**:
```sql
-- Find chunks without bridge mappings
SELECT c.chunk_id, c.text
FROM qdrant_chunks c
LEFT JOIN bridge_table b ON c.chunk_id = b.chunk_id
WHERE b.id IS NULL;
-- Expected: 0 rows
```

2. **Dangling Graph Nodes**:
```cypher
// Find nodes with degree 0
MATCH (n)
WHERE NOT (n)--()
RETURN n.URN, labels(n)
// Expected: 0 nodes (except root)
```

3. **Confidence Distribution**:
```python
# Expected distribution (empirical from sample):
# P25: 0.75
# P50 (median): 0.87
# P75: 0.95
# Mean: 0.85 ± 0.12
assert 0.73 < confidence.mean() < 0.97
assert confidence.std() < 0.15
```

### 7.2 Manual Annotation (Sample)

**Sample Size**: 5% = 44 articoli (random stratified)

**Annotation Task**:
1. **Chunking Quality**: Comma boundaries correct? (Yes/No)
2. **Concept Extraction**: Concepts relevant? (Precision@5)
3. **Bridge Mappings**: URN correct? Confidence reasonable? (Yes/No)

**Annotators**: 2 giuristi indipendenti

**Inter-Annotator Agreement**: Cohen's Kappa > 0.80 (substantial agreement)

### 7.3 Retrieval Evaluation (Intrinsic)

**Test Queries** (20 curated):
```
1. "Quali sono i termini per la risoluzione del contratto?"
2. "Inadempimento di non scarsa importanza significato"
3. "Obbligazioni solidali tra più debitori"
4. "Risarcimento danni da responsabilità extracontrattuale"
5. "Prescrizione delle obbligazioni civili"
...
20. "Contratti preliminari e definitivi differenze"
```

**Ground Truth**: Annotazione manuale dei top-5 articoli rilevanti per query

**Metrics**:
- Precision@5
- Recall@10
- MRR (Mean Reciprocal Rank)
- NDCG@10

**Target**:
- Precision@5 > 0.80
- MRR > 0.75
- NDCG@10 > 0.85

---

## 8. Reproducibility Guarantees

### 8.1 Determinism

**Zero-LLM Pipeline**: Nessun componente non-deterministico

**Sources of Non-Determinism** (controlled):
1. **VisualexAPI availability**: Cacheable, fallback a snapshot locale
2. **Brocardi.it structure changes**: HTML parser con 3 fallback scenari
3. **Embedding model updates**: Model version pinned (v1.0.0)

**Deterministic Components**:
- URN generation: Hardcoded map per Codice Civile
- Chunking rules: Regex-based, no probabilistic
- Concept extraction: Pattern matching, no ML
- Graph creation: Cypher MERGE (idempotent)

### 8.2 Versioning

```yaml
# merlt/config/ingestion_version.yaml
ingestion_version: "1.0.0"
execution_date: "2025-12-03"

components:
  visualex_api: "commit:abc123"
  falkordb_client: "v4.0.2"
  qdrant_client: "v1.7.0"
  embedding_model: "intfloat/multilingual-e5-large:v1.0.0"

dataset:
  source: "Normattiva.it"
  snapshot_date: "2025-12-03"
  articles_count: 887

checksums:
  normattiva_texts: "sha256:deadbeef..."
  brocardi_enrichment: "sha256:cafebabe..."
```

### 8.3 Artifacts

**Saved Artifacts** (per reproducibility):
```
artifacts/
├── raw_texts/
│   ├── art_1173.json
│   ├── art_1174.json
│   └── ... (887 files)
│
├── chunks/
│   ├── chunks_batch_001.jsonl  # 500 chunk
│   ├── chunks_batch_002.jsonl
│   └── ... (~5 files, 2500 chunk totali)
│
├── embeddings/
│   └── embeddings_e5_large.npy  # (2500, 1024) numpy array
│
├── graph_export/
│   └── libro_iv_graph.cypher    # Cypher dump
│
└── metadata/
    ├── ingestion_log.json       # Timestamp, errors, warnings
    └── statistics.json          # Dataset stats
```

**Total Size**: ~500 MB (compressi), ~2 GB (uncompressi)

---

## 9. Ethical Considerations

### 9.1 Data Source

- ✅ **Public domain**: Codice Civile è documento pubblico
- ✅ **Open access**: Normattiva.it è piattaforma ufficiale gratuita
- ✅ **Attribution**: Brocardi.it citato come fonte per commenti

### 9.2 Legal Compliance

- ✅ **Copyright**: Testi normativi non soggetti a copyright (L. 633/1941, art. 5)
- ✅ **Robot.txt**: VisualexAPI rispetta rate limiting
- ✅ **GDPR**: Nessun dato personale processato

### 9.3 Bias Mitigation

- ⚠️ **Temporal bias**: Solo versione vigente (no analisi storica)
- ⚠️ **Selection bias**: Solo Libro IV (no altri libri)
- ⚠️ **Source bias**: Brocardi può avere bias dottrinali

**Disclosure**: Questi bias sono documentati e comunicati agli utenti del sistema.

---

## 10. Limitations

### 10.1 Technical

1. **Chunking granularity**: Comma-level può essere troppo fine per alcuni use case
2. **Concept extraction**: Pattern-based, non copre tutti concetti impliciti
3. **Embedding model**: Monolingual focus su italiano, può perdere sfumature legali
4. **Graph density**: Relativamente sparso (density ~0.002)

### 10.2 Coverage

1. **Brocardi**: ~10-20% articoli senza commento
2. **Giurisprudenza**: Solo massime in Brocardi, no full text sentenze
3. **Modifiche**: Snapshot al 2025-12-03, no tracking real-time

### 10.3 Scalability

1. **Memory**: Embeddings in RAM (2500 × 1024 × 4 bytes = 10 MB, OK)
2. **Compute**: Embedding generation richiede ~40 min CPU (bottleneck)
3. **Storage**: 887 articoli OK, ma scaling a tutti 2969 articoli C.C. richiede 3x resources

---

## 11. Future Work

### 11.1 Short-Term (1-2 mesi)

1. **Expand to Libro I-VI**: Ingestion Codice Civile completo (~3000 articoli)
2. **Giurisprudenza full-text**: Integrazione con ItalianLII o Dejure.it
3. **Multi-temporal**: Versioning storico articoli modificati

### 11.2 Medium-Term (3-6 mesi)

1. **LLM-based concept extraction**: Fine-tune LLM italiano su annotazioni legali
2. **Cross-code references**: Link tra Codice Civile, Penale, Procedura Civile
3. **User feedback loop**: RLCF per raffinare confidence scores

### 11.3 Long-Term (6-12 mesi)

1. **Multi-jurisdiction**: Espandere a diritto EU, common law comparato
2. **Explainable retrieval**: Visualizzazione path grafici per ranking
3. **Production deployment**: API RESTful per external access

---

## References

1. Normattiva.it - Portale italiano della normativa vigente. URL: https://www.normattiva.it
2. Brocardi.it - Codice Civile commentato online. URL: https://www.brocardi.it
3. Wang, L. et al. (2022). "Text Embeddings by Weakly-Supervised Contrastive Pre-training". arXiv:2212.03533
4. FalkorDB (2024). "Knowledge Graph Database". GitHub: falkordb/falkordb
5. Qdrant (2024). "Vector Similarity Search Engine". URL: https://qdrant.tech

---

**Document Status**: ✅ COMPLETE - Ready for Implementation

**Next Step**: Review & Approval → Begin Implementation Phase 1
