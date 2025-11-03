# Data Ingestion and Preprocessing

## 1. Introduction

This document describes the data ingestion and preprocessing architecture for MERL-T, covering the complete pipeline from raw legal documents to structured, searchable knowledge stored in both a Vector Database and a Knowledge Graph.

### 1.1 Objectives

The data ingestion system aims to:

1. **Acquire** legal documents from authoritative Italian sources (government APIs, courts, academic publishers)
2. **Parse** diverse document formats (Akoma Ntoso XML/JSON, PDF, structured text)
3. **Extract** structured information (entities, metadata, relationships)
4. **Transform** raw text into semantically coherent chunks optimized for retrieval
5. **Populate** dual storage systems:
   - **Vector Database**: Semantic search over document chunks with rich metadata
   - **Knowledge Graph**: Structured representation of legal entities and relationships
6. **Validate** data quality and ensure consistency across systems
7. **Monitor** ingestion pipelines for performance and errors

### 1.2 Three Primary Pipelines

The system processes three distinct types of legal documents:

1. **Norme (Legislation)**: Laws, decrees, regulations from Italian government APIs
2. **Sentenze (Jurisprudence)**: Court decisions from various judicial sources
3. **Dottrina (Doctrine)**: Legal scholarship, manuals, treatises, academic commentary

Each pipeline has specialized processing logic tailored to the document structure and content characteristics.

### 1.3 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                 │
├─────────────────────────────────────────────────────────────────────┤
│  • Government API (Akoma Ntoso)                                     │
│  • Court websites (PDF)                                              │
│  • Academic publishers (PDF)                                         │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DOCUMENT TYPE ROUTER                              │
│              (Norm / Jurisprudence / Doctrine)                       │
└────────────────┬────────────────────────────────────────────────────┘
                 │
        ┌────────┴────────┬────────────────┐
        ▼                 ▼                ▼
┌───────────────┐  ┌──────────────┐  ┌────────────────┐
│  Norm Parser  │  │ PDF Processor│  │ Doctrine Parser│
│ (Akoma Ntoso) │  │  (Sentenze)  │  │   (Manuali)    │
└───────┬───────┘  └──────┬───────┘  └────────┬───────┘
        │                 │                    │
        └─────────────────┴────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   TEXT NORMALIZATION                                 │
│  • Whitespace cleanup                                                │
│  • Encoding standardization                                          │
│  • Section identification                                            │
└────────────────┬────────────────────────────────────────────────────┘
                 │
        ┌────────┴─────────┐
        ▼                  ▼
┌──────────────────┐  ┌────────────────────┐
│ Entity Extraction│  │ Relation Extraction│
│  (NER + LLM)     │  │  (Pattern + LLM)   │
└──────┬───────────┘  └──────┬─────────────┘
       │                     │
       └──────────┬──────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    METADATA ENRICHMENT                               │
│  • Temporal metadata                                                 │
│  • Hierarchical classification                                       │
│  • Authority scoring                                                 │
│  • Cross-references                                                  │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│              SEMANTIC CHUNKING                                       │
│  • Article-level (Norme)                                            │
│  • Section-based (Sentenze)                                         │
│  • Similarity-based (Dottrina)                                      │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│              EMBEDDING GENERATION                                    │
│  Phase 1: Generic multilingual (e5, text-embedding-3)              │
│  Phase 3+: Fine-tuned legal domain embeddings                       │
└────────────────┬────────────────────────────────────────────────────┘
                 │
        ┌────────┴─────────┐
        ▼                  ▼
┌──────────────────┐  ┌────────────────────┐
│  VECTOR DATABASE │  │  KNOWLEDGE GRAPH   │
│  (Chunks +       │  │  (Nodes +          │
│   Metadata)      │  │   Relations)       │
└──────────────────┘  └────────────────────┘
```

### 1.4 Batch vs. Streaming

- **Initial Load (Batch)**: Historical corpus of norms, jurisprudence, and doctrine processed in large batches with parallelization
- **Incremental Updates (Streaming)**: New legislation, recent court decisions ingested as they become available
- **On-Demand (Manual)**: Doctrinal works uploaded and processed as needed

### 1.5 Error Handling Strategy

- **Retry Logic**: Exponential backoff for transient failures (API rate limits, network issues)
- **Dead Letter Queue**: Failed documents routed to manual review queue with error diagnostics
- **Graceful Degradation**: Partial processing allowed (e.g., document ingested without full entity extraction if NER fails)
- **Idempotency**: Re-processing same document produces identical result (hash-based deduplication)

---

## 2. Pipeline 1: Norme (Legislation)

### 2.1 Data Acquisition

**Primary Source**: Italian Government API providing legislation in Akoma Ntoso format

**Document Types Covered**:
- Costituzione (Constitution)
- Leggi ordinarie (Ordinary laws)
- Decreti-legge (Decree-laws - emergency legislation)
- Decreti legislativi (Legislative decrees - delegated legislation)
- Regolamenti (Regulations)
- Decreti ministeriali (Ministerial decrees)

**Acquisition Strategy**:
```python
# Pseudocode for norm acquisition
def acquire_norms(source_api, start_date, end_date):
    """
    Fetch norms from government API within date range
    """
    norms = []
    for date in date_range(start_date, end_date):
        # Incremental daily fetch
        response = api.get_norms_by_date(date, format="akoma_ntoso")

        # Handle pagination
        while response.has_next_page():
            norms.extend(response.items)
            response = response.next_page()

        # Rate limiting: respect API quotas
        sleep(api.rate_limit_delay)

    return norms
```

**Crawling Strategy**:
- **Initial Load**: Fetch all norms from specific codes (Codice Civile, Codice Penale, etc.)
- **Incremental**: Daily checks for newly published norms (Gazzetta Ufficiale monitoring)
- **Priority Queue**: Frequently cited norms prioritized for processing

### 2.2 Parsing Akoma Ntoso

**Akoma Ntoso Structure**:
Akoma Ntoso is an XML/JSON standard for legal documents following FRBR levels:
- **Work**: Abstract legal work (e.g., "Codice Civile")
- **Expression**: Specific version at a point in time (e.g., "Codice Civile as of 01/01/2020")
- **Manifestation**: Specific format (e.g., PDF, HTML, XML)
- **Item**: Physical/digital instance

**XML Structure Example**:
```xml
<akomaNtoso>
  <act name="legge">
    <meta>
      <identification>
        <FRBRWork>
          <FRBRthis value="/akn/it/act/legge/1942/262"/>
          <FRBRdate date="1942-03-16" name="generation"/>
        </FRBRWork>
        <FRBRExpression>
          <FRBRthis value="/akn/it/act/legge/1942/262/ita@2020-01-01"/>
          <FRBRdate date="2020-01-01" name="expression"/>
        </FRBRExpression>
      </identification>
      <publication date="1942-04-04" name="GazzettaUfficiale" number="79"/>
      <lifecycle>
        <eventRef date="1942-04-21" type="generation" source="#ro1"/>
        <eventRef date="2005-10-10" type="amendment" source="#ro2"/>
      </lifecycle>
    </meta>
    <body>
      <book id="libro1">
        <num>Libro Primo</num>
        <heading>Delle persone e della famiglia</heading>
        <title id="titolo1">
          <num>Titolo I</num>
          <heading>Delle persone fisiche</heading>
          <chapter id="capo1">
            <article id="art1">
              <num>1</num>
              <heading>Capacità giuridica</heading>
              <paragraph>
                <content>
                  <p>La capacità giuridica si acquista dal momento della nascita...</p>
                </content>
              </paragraph>
            </article>
          </chapter>
        </title>
      </book>
    </body>
  </act>
</akomaNtoso>
```

**Parsing Logic**:
```python
def parse_akoma_ntoso(xml_document):
    """
    Extract structured data from Akoma Ntoso XML
    """
    doc = parse_xml(xml_document)

    # Extract metadata
    metadata = {
        "frbrwork_uri": doc.xpath("//FRBRWork/FRBRthis/@value")[0],
        "frbrexpression_uri": doc.xpath("//FRBRExpression/FRBRthis/@value")[0],
        "generation_date": doc.xpath("//FRBRWork/FRBRdate/@date")[0],
        "expression_date": doc.xpath("//FRBRExpression/FRBRdate/@date")[0],
        "publication_date": doc.xpath("//publication/@date")[0],
        "publication_source": doc.xpath("//publication/@name")[0],
        "publication_number": doc.xpath("//publication/@number")[0]
    }

    # Extract lifecycle events (modifications, amendments)
    lifecycle = []
    for event in doc.xpath("//lifecycle/eventRef"):
        lifecycle.append({
            "date": event.get("date"),
            "type": event.get("type"),
            "source": event.get("source")
        })

    # Extract structural elements
    articles = []
    for article in doc.xpath("//article"):
        articles.append({
            "id": article.get("id"),
            "number": article.xpath("num/text()")[0],
            "heading": article.xpath("heading/text()")[0] if article.xpath("heading") else None,
            "text": " ".join(article.xpath(".//content//text()")),
            "parent_chapter": article.getparent().get("id"),
            "parent_title": article.getparent().getparent().get("id"),
            "parent_book": article.getparent().getparent().getparent().get("id")
        })

    return {
        "metadata": metadata,
        "lifecycle": lifecycle,
        "articles": articles
    }
```

### 2.3 Metadata Extraction

**Temporal Metadata**:
- `data_pubblicazione`: Publication date (Gazzetta Ufficiale)
- `vigente_dal`: Effective start date (when norm enters into force)
- `vigente_al`: Effective end date (when norm ceases to be in force) - `null` if still active
- `data_ultima_modifica`: Date of last amendment

**Hierarchical Metadata**:
- `tipo_norma`: Type of norm (Costituzione, Legge, DL, D.Lgs, Regolamento, etc.)
- `livello_gerarchico`: Hierarchical level (1-5):
  - 1: Constitutional norms
  - 2: Constitutional laws
  - 3: Primary legislation (Leggi, DL, D.Lgs)
  - 4: Secondary legislation (Regolamenti)
  - 5: Ministerial decrees

**Structural Metadata**:
- `codice`: Code identifier (e.g., "cc" for Codice Civile, "cp" for Codice Penale)
- `numero`: Norm number
- `anno`: Year of enactment
- `articolo`: Article number
- `comma`: Paragraph number (optional)
- `libro`: Book number (for codes with book structure)
- `titolo`: Title number
- `capo`: Chapter number
- `sezione`: Section number

**Thematic Metadata**:
- `area_legale`: Legal area (civil, criminal, administrative, constitutional, tax, labor, commercial)
- `classificazione_tematica`: Thematic tags (array of keywords: ["contratti", "obbligazioni", "responsabilità"])
- `materia`: Subject matter (more granular than area_legale)

**Relational Metadata** (extracted):
- `riferimenti_normativi_uscenti`: Outgoing references to other norms (extracted via regex + NER)
  - Pattern: "Art. 1234 c.c.", "L. 234/1999", "D.Lgs. 81/2008"
- `riferimenti_normativi_entranti`: Incoming references (populated during cross-linking phase)

**Extraction Algorithm**:
```python
def extract_norm_metadata(parsed_document, article):
    """
    Extract comprehensive metadata for a single article
    """
    metadata = {}

    # Temporal
    metadata["data_pubblicazione"] = parsed_document["metadata"]["publication_date"]
    metadata["vigente_dal"] = parsed_document["metadata"]["expression_date"]
    metadata["vigente_al"] = infer_end_date(parsed_document["lifecycle"])

    # Hierarchical
    metadata["tipo_norma"] = infer_norm_type(parsed_document["metadata"]["frbrwork_uri"])
    metadata["livello_gerarchico"] = HIERARCHY_MAP[metadata["tipo_norma"]]

    # Structural
    uri_parts = parse_frbrwork_uri(parsed_document["metadata"]["frbrwork_uri"])
    metadata["codice"] = uri_parts["code"]
    metadata["numero"] = uri_parts["number"]
    metadata["anno"] = uri_parts["year"]
    metadata["articolo"] = article["number"]
    metadata["libro"] = article.get("parent_book")
    metadata["titolo"] = article.get("parent_title")
    metadata["capo"] = article.get("parent_chapter")

    # Thematic
    metadata["area_legale"] = classify_legal_area(article["text"], metadata["codice"])
    metadata["classificazione_tematica"] = extract_keywords(article["text"])

    # Relational
    metadata["riferimenti_normativi_uscenti"] = extract_norm_references(article["text"])

    return metadata
```

### 2.4 Temporal Tracking and Multivigenza

**Multivigenza Concept**:
Italian law uniquely allows multiple versions of the same norm to be simultaneously valid for different legal relationships established at different times. A contract signed under version A of a norm remains governed by version A even after the norm is amended to version B.

**Timeline Reconstruction**:
```python
def reconstruct_norm_timeline(norm_id, lifecycle_events):
    """
    Build complete temporal history of a norm with all versions
    """
    versions = []

    # Sort lifecycle events chronologically
    events = sorted(lifecycle_events, key=lambda e: e["date"])

    current_version = {
        "version_number": 1,
        "vigente_dal": events[0]["date"],  # Initial publication
        "vigente_al": None,
        "modificata_da": None,
        "tipo_modifica": "originale"
    }

    for event in events[1:]:
        if event["type"] in ["amendment", "repeal", "substitution"]:
            # Close current version
            current_version["vigente_al"] = event["date"]
            versions.append(current_version)

            if event["type"] != "repeal":
                # Open new version
                current_version = {
                    "version_number": len(versions) + 1,
                    "vigente_dal": event["date"],
                    "vigente_al": None,
                    "modificata_da": event["source"],
                    "tipo_modifica": event["type"]
                }

    # Add final version (still active)
    if current_version["vigente_al"] is None:
        versions.append(current_version)

    return versions
```

**Relationship Inference**:
From lifecycle events and text analysis, infer relationships:
- `modifica`: Norm A modifies Norm B (partial change)
- `abroga`: Norm A repeals Norm B (complete elimination)
- `sostituisce`: Norm A substitutes Norm B (replacement)
- `deroga`: Norm A derogates Norm B (creates exception)

**Temporal Query Support**:
```python
def get_norm_version_at_date(norm_id, query_date):
    """
    Retrieve the version of a norm applicable at a specific date
    """
    versions = get_all_versions(norm_id)

    for version in versions:
        if version["vigente_dal"] <= query_date and \
           (version["vigente_al"] is None or version["vigente_al"] >= query_date):
            return version

    # No version active at query date
    return None
```

### 2.5 Chunking Strategy for Norms

**Primary Strategy: Article-Level Chunking**
```python
def chunk_norm_article_level(parsed_document):
    """
    Create one chunk per article (default for most norms)
    """
    chunks = []

    for article in parsed_document["articles"]:
        chunk = {
            "chunk_text": article["text"],
            "chunk_type": "article",
            "chunk_id": f"{article['id']}_art_{article['number']}",
            "structural_context": {
                "articolo": article["number"],
                "heading": article["heading"],
                "libro": article.get("parent_book"),
                "titolo": article.get("parent_title"),
                "capo": article.get("parent_chapter")
            }
        }
        chunks.append(chunk)

    return chunks
```

**Secondary Strategy: Comma-Level for Long Articles**
```python
def chunk_norm_comma_level(article):
    """
    Split very long articles into comma-level chunks
    """
    # Heuristic: if article > 1024 tokens, split by commas
    if estimate_tokens(article["text"]) <= 1024:
        return [article["text"]]  # Keep as single chunk

    # Parse commas (paragraphs)
    commas = split_by_commas(article["text"])

    chunks = []
    for i, comma in enumerate(commas):
        chunk = {
            "chunk_text": comma,
            "chunk_type": "comma",
            "chunk_id": f"{article['id']}_art_{article['number']}_comma_{i+1}",
            "comma_number": i + 1,
            "parent_article": article["number"]
        }
        chunks.append(chunk)

    return chunks
```

**Metadata Propagation**:
All metadata extracted at the norm/article level is propagated to each chunk:
```python
def enrich_chunks_with_metadata(chunks, article_metadata, norm_metadata):
    """
    Attach metadata to each chunk
    """
    for chunk in chunks:
        chunk["metadata"] = {
            **norm_metadata,  # Norm-level metadata
            **article_metadata,  # Article-level metadata
            "chunk_level": chunk["chunk_type"]
        }

    return chunks
```

---

## 3. Pipeline 2: Sentenze (Jurisprudence)

### 3.1 Data Acquisition

**Future Primary Source**: Italian Government API for court decisions (not yet available)

**Current Fallback Sources**:
- **Corte di Cassazione**: Supreme Court decisions (cassazione.it)
- **Corte Costituzionale**: Constitutional Court decisions (cortecostituzionale.it)
- **giustizia.it**: Ministry of Justice database
- **TAR (Tribunali Amministrativi Regionali)**: Regional administrative courts
- **European Court of Human Rights**: ECHR decisions involving Italy

**Document Format**: Primarily PDF (structured and scanned)

**Acquisition Strategy**:
```python
def acquire_jurisprudence(source, start_date, end_date, court_level):
    """
    Fetch court decisions from various sources
    """
    decisions = []

    if source.has_api():
        # Preferred: Use API
        decisions = source.api.get_decisions(
            date_from=start_date,
            date_to=end_date,
            court=court_level
        )
    else:
        # Fallback: Web scraping
        decisions = scrape_court_website(
            source.url,
            date_range=(start_date, end_date),
            filters={"court": court_level}
        )

    # Download PDFs
    for decision in decisions:
        pdf_path = download_pdf(decision["url"], storage_path)
        decision["local_path"] = pdf_path

    return decisions
```

**Priority Criteria**:
1. **Binding precedent**: Sezioni Unite della Cassazione, Corte Costituzionale (highest priority)
2. **Persuasive precedent**: Individual Cassation chambers, Courts of Appeal
3. **Recent decisions**: Last 5 years prioritized
4. **Frequently cited**: Decisions with many downstream citations

### 3.2 PDF Processing

**Challenge**: Court decisions are often scanned PDFs with variable layout, requiring robust extraction.

**Step 1: Layout Analysis**
```python
def analyze_pdf_layout(pdf_path):
    """
    Identify document structure: header, body sections, dispositivo (ruling)
    """
    document = load_pdf(pdf_path)

    # Detect header section (first page, typically)
    header = extract_header(document.pages[0])

    # Detect body sections using common markers
    sections = {
        "fatto": find_section(document, markers=["FATTO", "Svolgimento del processo"]),
        "diritto": find_section(document, markers=["DIRITTO", "Motivi della decisione"]),
        "dispositivo": find_section(document, markers=["P.Q.M.", "Dispositivo"])
    }

    return {
        "header": header,
        "sections": sections
    }
```

**Step 2: Text Extraction**
```python
def extract_text_from_pdf(pdf_path, layout_info):
    """
    Extract text with OCR if necessary
    """
    document = load_pdf(pdf_path)

    # Check if PDF is text-based or scanned
    if is_text_based_pdf(document):
        text = extract_text_directly(document)
    else:
        # OCR required
        text = ocr_with_tesseract(document, lang="ita")
        text = post_process_ocr_text(text)  # Fix common OCR errors

    # Clean extracted text
    text = remove_headers_footers(text, layout_info)
    text = normalize_whitespace(text)

    return text
```

**Step 3: Section Segmentation**
```python
def segment_decision_sections(text, layout_info):
    """
    Split decision into logical sections
    """
    sections = {}

    # Extract header metadata section
    sections["header"] = text[layout_info["header"]["start"]:layout_info["header"]["end"]]

    # Extract main body sections
    sections["fatto"] = text[layout_info["sections"]["fatto"]["start"]:layout_info["sections"]["fatto"]["end"]]
    sections["diritto"] = text[layout_info["sections"]["diritto"]["start"]:layout_info["sections"]["diritto"]["end"]]
    sections["dispositivo"] = text[layout_info["sections"]["dispositivo"]["start"]:layout_info["sections"]["dispositivo"]["end"]]

    return sections
```

### 3.3 Entity Extraction from Jurisprudence

**Header Parsing** (structured metadata extraction):
```python
def parse_decision_header(header_text):
    """
    Extract structured metadata from decision header
    """
    metadata = {}

    # Court identification
    metadata["tribunale"] = extract_court_name(header_text)
    # Patterns: "CORTE DI CASSAZIONE", "CORTE D'APPELLO DI MILANO", "TRIBUNALE DI ROMA"

    metadata["sezione"] = extract_section(header_text)
    # Patterns: "Sezione II civile", "Sezione penale", "Sezioni Unite"

    # Decision identification
    metadata["numero_sentenza"] = extract_decision_number(header_text)
    # Pattern: "Sentenza n. 12345/2020", "n. 12345", "12345/2020"

    metadata["anno"] = extract_year(metadata["numero_sentenza"])

    # Dates
    metadata["data_decisione"] = extract_decision_date(header_text)
    # Pattern: "Depositata il 15/03/2020", "Roma, 15 marzo 2020"

    metadata["data_pubblicazione"] = extract_publication_date(header_text)

    # Parties
    metadata["presidente"] = extract_judge_name(header_text, role="Presidente")
    metadata["relatore"] = extract_judge_name(header_text, role="Relatore")
    metadata["parti"] = extract_parties(header_text)
    # Structure: {"ricorrente": "...", "resistente": "...", "terzi": [...]}

    return metadata
```

**Body Analysis** (content extraction):
```python
def extract_entities_from_decision_body(sections):
    """
    Extract entities and references from decision text
    """
    entities = {
        "riferimenti_normativi": [],
        "riferimenti_giurisprudenziali": [],
        "legal_concepts": [],
        "persons": [],
        "legal_entities": [],
        "amounts": [],
        "dates": []
    }

    # Combine all sections for entity extraction
    full_text = sections["fatto"] + " " + sections["diritto"] + " " + sections["dispositivo"]

    # ML-based entity extraction (same models as query-understanding)
    # These models handle polymorphic legal text robustly

    # Norm references (NER + relation extraction)
    # Uses LegalNormReferenceExtractor from query-understanding
    norm_extractor = LegalNormReferenceExtractor()
    entities["riferimenti_normativi"] = norm_extractor.extract_norm_references(full_text)

    # Jurisprudence references (specialized NER for case citations)
    juris_extractor = JurisprudenceReferenceExtractor()
    entities["riferimenti_giurisprudenziali"] = juris_extractor.extract_case_references(full_text)
    # Handles polymorphic citations:
    # - "Cass. civ. sez. I n. 12345/2020"
    # - "Cassazione civile, sezione prima, sentenza 12345 del 2020"
    # - "Corte Cost. 123/2020"

    # Legal concepts (NER + semantic classification)
    entities["legal_concepts"] = extract_legal_concepts_ner(full_text)

    # Persons and legal entities (domain-adapted NER)
    legal_entity_extractor = LegalEntityExtractor()
    extracted_entities = legal_entity_extractor.extract_parties_and_entities(full_text)
    entities["persons"] = extracted_entities["persons"]
    entities["legal_entities"] = extracted_entities["organizations"]

    # Amounts (NER for numeric entities + classification)
    # Handles: "€ 10.000", "diecimila euro", "10k EUR"
    numeric_extractor = NumericEntityExtractor()
    numeric_entities = numeric_extractor.extract(full_text)
    entities["amounts"] = [
        e for e in numeric_entities
        if e["type"] == "monetary_amount"
    ]

    # Dates (temporal NER from query-understanding)
    temporal_extractor = TemporalEntityExtractor()
    _, extracted_dates = temporal_extractor.standardize_dates(full_text)
    entities["dates"] = extracted_dates

    return entities

class JurisprudenceReferenceExtractor:
    """
    NER model specialized for case law citations

    Handles polymorphic jurisprudence references:
    - Court name variations
    - Section/chamber descriptions
    - Decision number formats
    - Date formats
    """

    def __init__(self):
        self.ner_model = load_finetuned_ner("legal-juris-citation-ner-it")

    def extract_case_references(self, text: str) -> List[Dict]:
        """
        Extract case law citations using NER

        Examples:
        - "Cass. civ. sez. I n. 12345/2020"
        - "Corte Costituzionale sentenza n. 123 del 15 luglio 2020"
        - "TAR Lazio, sez. II, n. 5678/2021"
        """

        # Run NER to identify citation spans
        citation_spans = self.ner_model.extract(text)

        # Parse each citation into structured format
        references = []
        for span in citation_spans:
            parsed = self.parse_citation(span["text"])
            if parsed:
                references.append(parsed)

        return references

    def parse_citation(self, citation_text: str) -> Dict:
        """
        Parse citation into structured components

        Uses sequence-to-structure model trained on legal citations
        """

        parsed = self.ner_model.parse_citation(citation_text)
        # Model learned to extract:
        # - Court name (normalized)
        # - Section/chamber
        # - Decision number
        # - Year
        # - Decision type (sentenza, ordinanza, etc.)

        return {
            "court": parsed.get("court"),
            "section": parsed.get("section"),
            "number": parsed.get("number"),
            "year": parsed.get("year"),
            "decision_type": parsed.get("type", "sentenza"),
            "original_text": citation_text
        }

class NumericEntityExtractor:
    """
    Extract and classify numeric entities

    Handles polymorphic number representations:
    - Written numbers: "diecimila euro"
    - Numeric: "10.000 €"
    - Abbreviated: "10k EUR"
    """

    def __init__(self):
        self.ner_model = load_finetuned_ner("numeric-entity-ner-it")

    def extract(self, text: str) -> List[Dict]:
        """
        Extract all numeric entities and classify by type

        Types: monetary_amount, percentage, cardinal_number, age, duration
        """

        numeric_entities = self.ner_model.extract(text)

        # Classify each by context
        classified = []
        for entity in numeric_entities:
            entity_type = self.classify_numeric_type(entity, text)
            entity["type"] = entity_type
            classified.append(entity)

        return classified

    def classify_numeric_type(self, entity: Dict, context: str) -> str:
        """
        Classify numeric entity using context

        Context indicators:
        - "euro", "€", "dollari" → monetary_amount
        - "%", "percento", "percentuale" → percentage
        - "anni", "età" → age
        - "giorni", "mesi" → duration
        """

        context_window = self.get_context(entity, context, window=5)
        return self.ner_model.classify_type(entity, context_window)
```

**Classification**:
```python
def classify_decision(metadata, entities, sections):
    """
    Classify decision along multiple dimensions
    """
    classification = {}

    # Binding force
    if metadata["tribunale"] == "Corte Costituzionale":
        classification["forza_vincolante"] = "vincolante"
    elif "Sezioni Unite" in metadata["sezione"]:
        classification["forza_vincolante"] = "vincolante"
    elif metadata["tribunale"] == "Corte di Cassazione":
        classification["forza_vincolante"] = "persuasiva"
    else:
        classification["forza_vincolante"] = "esemplificativa"

    # Decision type (from dispositivo)
    dispositivo_lower = sections["dispositivo"].lower()
    if "accoglie" in dispositivo_lower:
        classification["tipo_decisione"] = "accoglimento"
    elif "rigetta" in dispositivo_lower:
        classification["tipo_decisione"] = "rigetto"
    elif "accoglie parzialmente" in dispositivo_lower or "rigetta parzialmente" in dispositivo_lower:
        classification["tipo_decisione"] = "parziale"
    else:
        classification["tipo_decisione"] = "altro"

    # Legal area (from legal concepts and norm references)
    classification["area_legale"] = infer_legal_area(
        entities["legal_concepts"],
        entities["riferimenti_normativi"]
    )

    return classification
```

### 3.4 Metadata Schema for Jurisprudence

```json
{
  "doc_id": "sentenza_cass_12345_2020",
  "document_type": "jurisprudence",

  "court_metadata": {
    "tribunale": "Corte di Cassazione",
    "sezione": "Sezione II civile",
    "numero_sentenza": "12345",
    "anno": 2020,
    "presidente": "Mario Rossi",
    "relatore": "Luigi Bianchi"
  },

  "temporal_metadata": {
    "data_decisione": "2020-03-15",
    "data_pubblicazione": "2020-03-20",
    "data_deposito": "2020-03-18"
  },

  "parties": {
    "ricorrente": "Alfa S.p.A.",
    "resistente": "Beta S.r.l.",
    "terzi": []
  },

  "classification": {
    "forza_vincolante": "persuasiva",
    "tipo_decisione": "accoglimento",
    "area_legale": "civil",
    "materia": "contratti"
  },

  "entities_extracted": {
    "riferimenti_normativi": [
      {"law_name": "c.c.", "article": "1418", "comma": null},
      {"law_name": "L. 194/1978", "article": "9", "comma": "5"}
    ],
    "riferimenti_giurisprudenziali": [
      {"court": "Cass. civ.", "section": "II", "number": "10000", "year": "2018"}
    ],
    "legal_concepts": ["nullità", "simulazione", "vizio di forma"]
  },

  "authority_score": 0.85
}
```

### 3.5 Chunking Strategy for Jurisprudence

**Primary Strategy: Section-Based Chunking**
```python
def chunk_decision_section_based(sections, metadata):
    """
    Create separate chunks for main decision sections
    """
    chunks = []

    # Chunk 1: Fatto (statement of facts)
    if sections["fatto"]:
        chunks.append({
            "chunk_text": sections["fatto"],
            "chunk_type": "fatto",
            "chunk_id": f"{metadata['doc_id']}_fatto",
            "section_name": "Svolgimento del processo"
        })

    # Chunk 2: Diritto (legal reasoning) - may be split if very long
    diritto_text = sections["diritto"]
    if estimate_tokens(diritto_text) <= 1024:
        chunks.append({
            "chunk_text": diritto_text,
            "chunk_type": "diritto",
            "chunk_id": f"{metadata['doc_id']}_diritto",
            "section_name": "Motivi della decisione"
        })
    else:
        # Split diritto into paragraphs
        paragraphs = split_by_paragraphs(diritto_text)
        for i, para in enumerate(paragraphs):
            chunks.append({
                "chunk_text": para,
                "chunk_type": "diritto_paragraph",
                "chunk_id": f"{metadata['doc_id']}_diritto_p{i+1}",
                "paragraph_number": i + 1
            })

    # Chunk 3: Dispositivo (ruling)
    if sections["dispositivo"]:
        chunks.append({
            "chunk_text": sections["dispositivo"],
            "chunk_type": "dispositivo",
            "chunk_id": f"{metadata['doc_id']}_dispositivo",
            "section_name": "P.Q.M."
        })

    return chunks
```

**Massima Extraction** (if present):
```python
def extract_massima(decision_text, metadata):
    """
    Extract 'massima' (headnote) - concise summary of legal principle

    Uses document structure classification instead of regex
    to handle polymorphic massima formatting:
    - "Massima:", "Massima di redazione:", "Principio di diritto:"
    - Implicit massima (summary without explicit marker)
    - Multiple massime in complex decisions
    """

    # Use document structure understanding model
    structure_model = DocumentStructureClassifier()

    # Identify massima section
    sections = structure_model.identify_sections(decision_text)

    massima_sections = [s for s in sections if s["type"] == "massima"]

    if massima_sections:
        # Take first massima (primary legal principle)
        massima = massima_sections[0]

        return {
            "chunk_text": massima["text"],
            "chunk_type": "massima",
            "chunk_id": f"{metadata['doc_id']}_massima",
            "is_summary": True,
            "confidence": massima["confidence"]
        }

    return None
```

---

## 4. Pipeline 3: Dottrina (Legal Doctrine)

### 4.1 Data Acquisition

**Sources**:
- Academic publishers (e.g., Giuffrè, CEDAM, Zanichelli)
- University legal repositories
- Professional legal publishers
- Law journal articles
- Legal commentaries and treatises

**Document Formats**: Primarily PDF (books, articles, treatises)

**Acquisition Strategy**:
- **Manual upload**: Legal professionals upload doctrinal works for ingestion
- **Batch import**: Institutional agreements for bulk access to publisher catalogs
- **On-demand processing**: Documents processed as needed based on citation frequency

### 4.2 PDF Processing for Doctrine

**Challenges**:
- Variable layout (single-column, two-column, footnotes)
- Complex typography (italics for citations, bold for emphasis)
- Footnotes and endnotes (valuable citations but disrupt text flow)
- Multi-language documents (Italian with Latin legal terms, foreign citations)

**Processing Pipeline**:
```python
def process_doctrinal_pdf(pdf_path):
    """
    Extract and clean text from doctrinal PDF
    """
    # Step 1: Extract metadata from filename or first page
    metadata = extract_doctrinal_metadata(pdf_path)
    # Expected: author, title, publisher, year, edition

    # Step 2: Extract full text
    raw_text = extract_text_from_pdf_with_ocr(pdf_path)

    # Step 3: Identify and separate footnotes
    main_text, footnotes = separate_footnotes(raw_text)

    # Step 4: Clean text
    clean_text = normalize_whitespace(main_text)
    clean_text = remove_page_numbers(clean_text)
    clean_text = remove_running_headers(clean_text)

    # Step 5: Detect structural divisions
    sections = detect_document_sections(clean_text)
    # Typical sections: Introduzione, Capitoli, Conclusioni, Bibliografia

    return {
        "metadata": metadata,
        "text": clean_text,
        "footnotes": footnotes,
        "sections": sections
    }
```

### 4.3 Semantic Chunking for Doctrine

**Challenge**: Doctrinal texts do not have rigid structure like norms (articles) or decisions (fatto/diritto/dispositivo). Need intelligent chunking that preserves conceptual coherence.

**Semantic Chunking Algorithm**:

**Step 1: Sentence Segmentation**
```python
def split_into_sentences(text):
    """
    Split text into sentences using NLP-based segmentation

    Uses spaCy's sentence segmenter trained on Italian
    Handles legal text complexities:
    - Abbreviations: "art.", "c.c.", "es.", "cfr."
    - Numbered lists and enumerations
    - Citations with internal punctuation
    - Legal Latin phrases: "ex lege", "de facto"
    """

    # Use spaCy's dependency parser with sentence boundaries
    # spaCy uses ML model (not regex) for sentence segmentation
    doc = nlp(text)

    # Extract sentences with filtering
    sentences = []
    for sent in doc.sents:
        sent_text = sent.text.strip()

        # Filter out very short fragments (< 15 characters)
        if len(sent_text) > 15:
            sentences.append(sent_text)

    return sentences

# Alternative: use Italian-specific sentence segmenter
def split_into_sentences_advanced(text):
    """
    Advanced sentence segmentation for legal Italian

    Uses fine-tuned model on legal corpus
    Better handles:
    - Legal abbreviations ("d.lgs.", "c.d.", "v.")
    - Complex citations spanning multiple lines
    - Footnote markers and references
    """

    segmenter = LegalSentenceSegmenter(language="it")
    sentences = segmenter.segment(text)

    return sentences
```

**Step 2: Embedding Generation for Sentences**
```python
async def generate_sentence_embeddings(sentences, embedding_model):
    """
    Generate embedding vectors for each sentence
    """
    # Batch processing for efficiency
    batch_size = 16
    all_embeddings = []

    for i in range(0, len(sentences), batch_size):
        batch = sentences[i:i+batch_size]
        embeddings = await embedding_model.embed_documents(batch)
        all_embeddings.extend(embeddings)

    return all_embeddings
```

**Step 3: Incremental Chunk Construction with Similarity Threshold**
```python
def semantic_chunking_similarity_based(sentences, embeddings,
                                       similarity_threshold=0.72,
                                       max_chunk_tokens=1024,
                                       min_chunk_tokens=256):
    """
    Build chunks by incrementally adding sentences with high semantic similarity
    to the current chunk's conceptual center (mean embedding)
    """
    chunks = []
    current_chunk_sentences = [sentences[0]]
    current_chunk_embeddings = [embeddings[0]]
    current_tokens = estimate_tokens(sentences[0])

    for i in range(1, len(sentences)):
        sentence = sentences[i]
        sentence_embedding = embeddings[i]
        sentence_tokens = estimate_tokens(sentence)

        # Calculate mean embedding of current chunk (conceptual center)
        mean_chunk_embedding = calculate_average_embedding(current_chunk_embeddings)

        # Calculate similarity between sentence and chunk center
        similarity = cosine_similarity(mean_chunk_embedding, sentence_embedding)

        # Decision: add to current chunk or start new chunk
        would_exceed_max = (current_tokens + sentence_tokens) > max_chunk_tokens

        if similarity >= similarity_threshold and not would_exceed_max:
            # Add to current chunk
            current_chunk_sentences.append(sentence)
            current_chunk_embeddings.append(sentence_embedding)
            current_tokens += sentence_tokens
        else:
            # Finalize current chunk if it meets minimum size
            if current_tokens >= min_chunk_tokens:
                chunk_text = " ".join(current_chunk_sentences)
                internal_similarity = calculate_internal_coherence(current_chunk_embeddings)
                chunks.append({
                    "text": chunk_text,
                    "internal_similarity": internal_similarity,
                    "token_count": current_tokens
                })

            # Start new chunk
            current_chunk_sentences = [sentence]
            current_chunk_embeddings = [sentence_embedding]
            current_tokens = sentence_tokens

    # Add final chunk
    if current_tokens >= min_chunk_tokens:
        chunk_text = " ".join(current_chunk_sentences)
        internal_similarity = calculate_internal_coherence(current_chunk_embeddings)
        chunks.append({
            "text": chunk_text,
            "internal_similarity": internal_similarity,
            "token_count": current_tokens
        })

    return chunks

def calculate_average_embedding(embeddings):
    """
    Compute normalized mean vector (conceptual center)
    """
    if not embeddings:
        return None

    vector_length = len(embeddings[0])
    sum_vector = [0] * vector_length

    # Sum all vectors
    for vec in embeddings:
        for i in range(vector_length):
            sum_vector[i] += vec[i]

    # Average
    avg_vector = [val / len(embeddings) for val in sum_vector]

    # Normalize (unit vector)
    magnitude = math.sqrt(sum(val ** 2 for val in avg_vector))
    if magnitude > 0:
        avg_vector = [val / magnitude for val in avg_vector]

    return avg_vector

def calculate_internal_coherence(embeddings):
    """
    Measure how semantically coherent a chunk is
    (average similarity of each sentence to the chunk's mean embedding)
    """
    if len(embeddings) <= 1:
        return 1.0

    mean_embedding = calculate_average_embedding(embeddings)
    similarities = [cosine_similarity(mean_embedding, emb) for emb in embeddings]

    return sum(similarities) / len(similarities)
```

**Key Insight**: This algorithm builds chunks where all sentences are semantically related to the **central concept** of the chunk (represented by the mean embedding), rather than just being similar to the previous sentence. This produces more coherent, topically-focused chunks.

### 4.4 Entity Extraction for Doctrine

**Extraction Schema** (comprehensive):
```python
def extract_entities_from_doctrinal_chunk(chunk_text, llm_extractor):
    """
    Extract rich entity set from doctrinal text using NER + LLM
    """
    entities = {
        "natural_persons": [],      # Authors, judges, legal scholars cited
        "legal_entities": [],        # Organizations, companies, institutions
        "legal_references": [],      # Norm citations
        "courts": [],                 # Court names mentioned
        "case_numbers": [],           # Jurisprudence citations
        "dates": [],                  # Publication dates, historical references
        "amounts": [],                # Monetary values mentioned
        "locations": [],              # Geographical references
        "legal_concepts": []          # Key legal concepts discussed
    }

    # Step 1: NER-based extraction (fast, for common entities)
    ner_results = apply_ner(chunk_text, model="legal_italian_ner")
    entities["natural_persons"] = ner_results["PER"]
    entities["legal_entities"] = ner_results["ORG"]
    entities["locations"] = ner_results["LOC"]

    # Step 2: Regex-based extraction (for structured patterns)
    entities["legal_references"] = extract_norm_references(chunk_text)
    entities["case_numbers"] = extract_case_references(chunk_text)
    entities["dates"] = extract_dates(chunk_text)
    entities["amounts"] = extract_amounts(chunk_text)

    # Step 3: LLM-based extraction (for complex entities and concepts)
    llm_prompt = f"""
    Extract the following entities from this legal text:
    - Legal concepts (e.g., "responsabilità extracontrattuale", "simulazione")
    - Court names (e.g., "Corte di Cassazione", "TAR Lazio")
    - Any additional relevant legal entities not captured by standard NER

    Text: {chunk_text}

    Return JSON with keys: legal_concepts, courts, additional_entities
    """

    llm_entities = llm_extractor.extract(llm_prompt)
    entities["legal_concepts"] = llm_entities.get("legal_concepts", [])
    entities["courts"].extend(llm_entities.get("courts", []))

    return entities
```

**Example Entity Extraction Output**:
```json
{
  "natural_persons": [
    {"name": "Bianca", "role": "author", "title": "Professor"},
    {"name": "Trabucchi", "role": "cited_scholar"}
  ],
  "legal_entities": [
    {"name": "Corte di Cassazione", "type": "court"},
    {"name": "Università di Bologna", "type": "institution"}
  ],
  "legal_references": [
    {"law_name": "c.c.", "article": "1418", "law_number": null},
    {"law_name": "L. 194/1978", "article": "9", "law_number": "194/1978"}
  ],
  "courts": [
    {"name": "Corte di Cassazione", "level": "supreme", "location": null},
    {"name": "TAR Lazio", "level": "administrative", "location": "Lazio"}
  ],
  "case_numbers": [
    {"number": "12345", "type": "civil", "year": "2020"}
  ],
  "dates": [
    {"date": "2020-03-15", "type": "publication", "description": "Decision date"},
    {"date": "1942", "type": "enactment", "description": "Codice Civile"}
  ],
  "amounts": [
    {"amount": "10000", "currency": "EUR", "type": "damages"}
  ],
  "locations": [
    {"location": "Roma", "type": "city"}
  ],
  "legal_concepts": [
    "nullità contrattuale",
    "simulazione relativa",
    "vizio di forma",
    "responsabilità precontrattuale"
  ]
}
```

### 4.5 Chunk Enrichment

**Summarization**:
```python
async def summarize_doctrinal_chunk(chunk_text, summarization_llm):
    """
    Generate concise summary of chunk (max 3 sentences)
    """
    prompt = f"""
    Create a concise summary of this legal text in maximum 3 sentences,
    focusing on key concepts and main arguments:

    Text: {chunk_text}

    Summary (Italian):
    """

    summary = await summarization_llm.generate(prompt)
    return summary.strip()
```

**Metadata Enhancement Proposals**:
```python
def enhance_doctrinal_metadata(chunk, document_metadata):
    """
    Add comprehensive metadata to each doctrinal chunk
    """
    enhanced_metadata = {
        **document_metadata,  # author, title, year, publisher, edition

        # Authority scoring
        "fonte_autorita": calculate_author_authority(document_metadata["author"]),
        # 0.0-1.0 based on author reputation (academic citations, judicial citations)

        # Publication metadata
        "anno_pubblicazione": document_metadata["year"],
        "edizione": document_metadata.get("edition", 1),
        "page_number": chunk.get("page_number"),

        # Content classification
        "tipo_contenuto": classify_chunk_content_type(chunk["text"]),
        # Options: "definition", "explanation", "commentary", "criticism", "case_analysis"

        # Alignment with jurisprudence
        "allineamento_giurisprudenza": assess_jurisprudential_alignment(chunk),
        # Options: "maggioritario", "minoritario", "innovativo", "critico"

        # Thematic classification
        "legal_domain_tags": chunk["entities"]["legal_concepts"],
        "primary_legal_area": infer_legal_area_from_concepts(chunk["entities"]["legal_concepts"])
    }

    return enhanced_metadata

def calculate_author_authority(author_name):
    """
    Score author authority based on academic/judicial reputation
    """
    # Heuristic: could be enhanced with citation database lookup
    prestigious_authors = {
        "Bianca": 0.95,
        "Trabucchi": 0.90,
        "Galgano": 0.92,
        "Rescigno": 0.88
        # etc.
    }

    return prestigious_authors.get(author_name, 0.5)  # Default: moderate authority

def classify_chunk_content_type(text):
    """
    Classify the type of doctrinal content
    """
    # Heuristic: keyword-based classification
    if any(keyword in text.lower() for keyword in ["si definisce", "per definizione", "è definito"]):
        return "definition"
    elif any(keyword in text.lower() for keyword in ["in altre parole", "ciò significa", "spiegazione"]):
        return "explanation"
    elif any(keyword in text.lower() for keyword in ["secondo la dottrina", "la giurisprudenza ha stabilito"]):
        return "commentary"
    elif any(keyword in text.lower() for keyword in ["tuttavia", "critica", "non si può accettare"]):
        return "criticism"
    elif any(keyword in text.lower() for keyword in ["nel caso", "la corte ha deciso", "sentenza"]):
        return "case_analysis"
    else:
        return "explanation"  # default

def assess_jurisprudential_alignment(chunk):
    """
    Assess whether doctrine aligns with majority/minority jurisprudence
    """
    # Heuristic: based on language used
    text_lower = chunk["text"].lower()

    if "orientamento consolidato" in text_lower or "giurisprudenza maggioritaria" in text_lower:
        return "maggioritario"
    elif "orientamento minoritario" in text_lower or "tesi isolata" in text_lower:
        return "minoritario"
    elif "proposta innovativa" in text_lower or "nuova interpretazione" in text_lower:
        return "innovativo"
    elif "critica" in text_lower and "giurisprudenza" in text_lower:
        return "critico"
    else:
        return "neutrale"
```

---

## 5. Unified Metadata Schema for Vector Database

### 5.1 Core Metadata (Common to All Document Types)

All chunks in the Vector Database share a common core schema, with source-specific extensions.

```json
{
  "chunk_id": "uuid-v4-string",
  "doc_id": "hash-of-source-document",
  "document_type": "norm | jurisprudence | doctrine",

  "text": "The actual chunk text content...",
  "token_count": 512,
  "chunk_index": 0,
  "total_chunks": 5,

  "temporal_metadata": {
    "date_published": "2020-03-15T00:00:00Z",
    "date_effective": "2020-03-17T00:00:00Z",
    "date_end": null
  },

  "classification": {
    "legal_area": "civil",
    "legal_domain_tags": ["contratti", "obbligazioni", "nullità"],
    "materia": "diritto_civile_contratti"
  },

  "authority_metadata": {
    "hierarchical_level": 2,
    "binding_force": "persuasive",
    "authority_score": 0.75
  },

  "entities_extracted": {
    "norm_references": [
      {"law_name": "c.c.", "article": "1418", "comma": null}
    ],
    "case_references": [
      {"court": "Cass. civ.", "section": "II", "number": "12345", "year": "2020"}
    ],
    "legal_concepts": ["nullità", "simulazione", "vizio di forma"],
    "persons": ["Bianca", "Trabucchi"],
    "legal_entities": ["Corte di Cassazione"]
  },

  "chunk_quality": {
    "internal_similarity": 0.82,
    "embedding_model": "text-embedding-3-large",
    "processing_timestamp": "2024-03-15T10:30:00Z"
  },

  "source_metadata": {
    // Flexible object for source-specific metadata
    // See sections 5.2, 5.3, 5.4 for type-specific schemas
  }
}
```

### 5.2 Source-Specific Metadata: Norms

```json
{
  "source_metadata": {
    "source_type": "norm",

    "norm_identification": {
      "codice": "cc",
      "numero": "262",
      "anno": 1942,
      "articolo": "1418",
      "comma": null,
      "libro": "IV",
      "titolo": "II",
      "capo": "XII",
      "sezione": null
    },

    "norm_type": "codice_civile",
    "norm_title": "Cause di nullità del contratto",

    "version_info": {
      "version_number": 2,
      "version_date": "2020-01-01",
      "modified_by": "L. 234/2019",
      "modification_type": "amendment"
    },

    "publication_info": {
      "gazzetta_ufficiale": "GU n. 79 del 04/04/1942",
      "publication_date": "1942-04-04"
    }
  }
}
```

### 5.3 Source-Specific Metadata: Jurisprudence

```json
{
  "source_metadata": {
    "source_type": "jurisprudence",

    "court_info": {
      "tribunale": "Corte di Cassazione",
      "sezione": "Sezione II civile",
      "numero_sentenza": "12345",
      "anno": 2020,
      "presidente": "Mario Rossi",
      "relatore": "Luigi Bianchi"
    },

    "parties": {
      "ricorrente": "Alfa S.p.A.",
      "resistente": "Beta S.r.l.",
      "terzi": []
    },

    "decision_metadata": {
      "data_decisione": "2020-03-15",
      "data_pubblicazione": "2020-03-20",
      "data_deposito": "2020-03-18",
      "tipo_decisione": "accoglimento",
      "has_massima": true
    },

    "chunk_section": "diritto"
  }
}
```

### 5.4 Source-Specific Metadata: Doctrine

```json
{
  "source_metadata": {
    "source_type": "doctrine",

    "publication_info": {
      "author": "Cesare Massimo Bianca",
      "title": "Diritto Civile - Il Contratto",
      "publisher": "Giuffrè Editore",
      "year": 2019,
      "edition": 3,
      "isbn": "978-88-14-24567-8",
      "page_number": 245
    },

    "content_metadata": {
      "tipo_contenuto": "explanation",
      "chapter": "Capitolo V - Invalidità del contratto",
      "section": "5.2 La nullità",
      "allineamento_giurisprudenza": "maggioritario"
    },

    "chunk_summary": "Discussione delle cause di nullità del contratto secondo l'art. 1418 c.c., con distinzione tra nullità testuale e nullità virtuale."
  }
}
```

### 5.5 Compatibility with Knowledge Graph

**Alignment Strategy**: Vector Database metadata are a **flexible superset** of Knowledge Graph node properties.

**Mapping Principles**:
1. **Core entities** in VectorDB metadata map to KG node IDs:
   - `norm_references[i]` → link to `Norma` nodes in KG
   - `case_references[i]` → link to `Sentenza` nodes in KG
   - `legal_concepts[i]` → link to `Concetto` nodes in KG

2. **VectorDB chunks maintain their own metadata** independently of KG:
   - Allows rich, flexible metadata without rigid KG schema
   - Enables fast filtering during retrieval without KG queries

3. **KG provides structured relationships**, VectorDB provides semantic search:
   - VectorDB: "Find chunks semantically similar to user query + filter by metadata"
   - KG: "Traverse relationships to find related norms, principles, jurisprudence"

**Cross-Linking**:
```python
def link_vectordb_to_kg(chunk, knowledge_graph):
    """
    Add KG node IDs to chunk metadata for cross-referencing
    """
    kg_links = {
        "norm_nodes": [],
        "case_nodes": [],
        "concept_nodes": []
    }

    # Link norm references
    for norm_ref in chunk["entities_extracted"]["norm_references"]:
        # Search KG for matching norm node
        kg_node = knowledge_graph.find_norm(
            law_name=norm_ref["law_name"],
            article=norm_ref["article"]
        )
        if kg_node:
            kg_links["norm_nodes"].append(kg_node.id)

    # Link case references
    for case_ref in chunk["entities_extracted"]["case_references"]:
        kg_node = knowledge_graph.find_sentenza(
            court=case_ref["court"],
            number=case_ref["number"],
            year=case_ref["year"]
        )
        if kg_node:
            kg_links["case_nodes"].append(kg_node.id)

    # Link legal concepts
    for concept in chunk["entities_extracted"]["legal_concepts"]:
        kg_node = knowledge_graph.find_concept(name=concept)
        if kg_node:
            kg_links["concept_nodes"].append(kg_node.id)
        else:
            # Concept not in KG yet - flag for creation
            kg_links["concept_nodes"].append({"name": concept, "needs_creation": True})

    chunk["kg_links"] = kg_links
    return chunk
```

---

## 6. Knowledge Graph Population

### 6.1 Initial Automated Population

**Objective**: Automatically create KG nodes and relationships from processed documents.

**Node Creation Logic**:
```python
def populate_kg_from_documents(processed_documents, knowledge_graph):
    """
    Create KG nodes from ingested documents
    """
    for doc in processed_documents:
        if doc["document_type"] == "norm":
            create_norm_nodes(doc, knowledge_graph)
        elif doc["document_type"] == "jurisprudence":
            create_jurisprudence_nodes(doc, knowledge_graph)
        elif doc["document_type"] == "doctrine":
            create_doctrine_nodes(doc, knowledge_graph)

        # Extract and create concept nodes
        create_concept_nodes(doc["entities_extracted"]["legal_concepts"], knowledge_graph)

def create_norm_nodes(norm_doc, kg):
    """
    Create Norma and Versione nodes
    """
    # Create Norma node
    norma_node = kg.create_node("Norma", {
        "node_id": norm_doc["doc_id"],
        "codice": norm_doc["source_metadata"]["norm_identification"]["codice"],
        "articolo": norm_doc["source_metadata"]["norm_identification"]["articolo"],
        "numero": norm_doc["source_metadata"]["norm_identification"]["numero"],
        "anno": norm_doc["source_metadata"]["norm_identification"]["anno"],
        "titolo": norm_doc["source_metadata"]["norm_title"],
        "area_legale": norm_doc["classification"]["legal_area"],
        "livello_gerarchico": norm_doc["authority_metadata"]["hierarchical_level"]
    })

    # Create Versione nodes if multivigenza
    if norm_doc["source_metadata"].get("version_info"):
        versione_node = kg.create_node("Versione", {
            "versione_numero": norm_doc["source_metadata"]["version_info"]["version_number"],
            "vigente_dal": norm_doc["temporal_metadata"]["date_effective"],
            "vigente_al": norm_doc["temporal_metadata"]["date_end"],
            "modificata_da": norm_doc["source_metadata"]["version_info"]["modified_by"],
            "testo_versione": norm_doc["text"]
        })

        # Create relation: Norma -[:ha_versione]-> Versione
        kg.create_relationship(norma_node, "ha_versione", versione_node)

    return norma_node

def create_jurisprudence_nodes(juris_doc, kg):
    """
    Create Sentenza node
    """
    sentenza_node = kg.create_node("Sentenza", {
        "node_id": juris_doc["doc_id"],
        "numero_sentenza": juris_doc["source_metadata"]["court_info"]["numero_sentenza"],
        "anno": juris_doc["source_metadata"]["court_info"]["anno"],
        "tribunale": juris_doc["source_metadata"]["court_info"]["tribunale"],
        "sezione": juris_doc["source_metadata"]["court_info"]["sezione"],
        "data_decisione": juris_doc["source_metadata"]["decision_metadata"]["data_decisione"],
        "forza_vincolante": juris_doc["authority_metadata"]["binding_force"],
        "area_legale": juris_doc["classification"]["legal_area"]
    })

    return sentenza_node

def create_doctrine_nodes(doctrine_doc, kg):
    """
    Create Dottrina node
    """
    dottrina_node = kg.create_node("Dottrina", {
        "node_id": doctrine_doc["doc_id"],
        "autore": doctrine_doc["source_metadata"]["publication_info"]["author"],
        "titolo": doctrine_doc["source_metadata"]["publication_info"]["title"],
        "anno_pubblicazione": doctrine_doc["source_metadata"]["publication_info"]["year"],
        "editore": doctrine_doc["source_metadata"]["publication_info"]["publisher"],
        "area_legale": doctrine_doc["classification"]["legal_area"],
        "autorita": doctrine_doc["authority_metadata"]["authority_score"]
    })

    return dottrina_node

def create_concept_nodes(legal_concepts, kg):
    """
    Create Concetto nodes for legal concepts
    """
    concept_nodes = []

    for concept in legal_concepts:
        # Check if concept already exists
        existing_node = kg.find_node("Concetto", {"nome": concept})

        if not existing_node:
            # Create new concept node
            concept_node = kg.create_node("Concetto", {
                "node_id": generate_concept_id(concept),
                "nome": concept,
                "tipo": "concetto_giuridico"
            })
            concept_nodes.append(concept_node)
        else:
            concept_nodes.append(existing_node)

    return concept_nodes
```

### 6.2 Automatic Relation Extraction

**From Explicit Metadata**:
```python
def create_relations_from_metadata(doc, doc_node, kg):
    """
    Create relationships based on extracted references
    """
    # Norm references → create "cita" or "applica" relations
    for norm_ref in doc["entities_extracted"]["norm_references"]:
        target_norm = kg.find_node("Norma", {
            "codice": norm_ref["law_name"],
            "articolo": norm_ref["article"]
        })

        if target_norm:
            if doc["document_type"] == "jurisprudence":
                kg.create_relationship(doc_node, "applica", target_norm)
            else:
                kg.create_relationship(doc_node, "cita", target_norm)

    # Case references → create "cita" relations
    for case_ref in doc["entities_extracted"]["case_references"]:
        target_case = kg.find_node("Sentenza", {
            "numero_sentenza": case_ref["number"],
            "anno": case_ref["year"]
        })

        if target_case:
            kg.create_relationship(doc_node, "cita", target_case)

    # Legal concepts → create "riguarda" relations
    for concept in doc["entities_extracted"]["legal_concepts"]:
        concept_node = kg.find_node("Concetto", {"nome": concept})
        if concept_node:
            kg.create_relationship(doc_node, "riguarda", concept_node)
```

**From Textual Patterns**:
```python
def extract_relations_from_text(text, source_norm_id, kg):
    """
    Infer relationships from textual patterns in norm text
    """
    relations = []

    # Pattern 1: "modifica l'art. X"
    modification_pattern = r"modifica\s+l'art(?:icolo|\.)?\s+(\d+)\s+(c\.c\.|c\.p\.)"
    matches = re.findall(modification_pattern, text, re.IGNORECASE)
    for match in matches:
        article, code = match
        target_norm = kg.find_norm(code=code, article=article)
        if target_norm:
            relations.append({
                "source": source_norm_id,
                "type": "modifica",
                "target": target_norm.id
            })

    # Pattern 2: "in deroga a..."
    derogation_pattern = r"in deroga\s+a(?:ll'art(?:icolo|\.)?)?\s+(\d+)\s+(c\.c\.|c\.p\.)"
    matches = re.findall(derogation_pattern, text, re.IGNORECASE)
    for match in matches:
        article, code = match
        target_norm = kg.find_norm(code=code, article=article)
        if target_norm:
            relations.append({
                "source": source_norm_id,
                "type": "deroga",
                "target": target_norm.id
            })

    # Pattern 3: "ai sensi di..." (reference/rinvio)
    reference_pattern = r"ai sensi\s+de(?:ll'art(?:icolo|\.)?)?\s+(\d+)\s+(c\.c\.|c\.p\.)"
    matches = re.findall(reference_pattern, text, re.IGNORECASE)
    for match in matches:
        article, code = match
        target_norm = kg.find_norm(code=code, article=article)
        if target_norm:
            relations.append({
                "source": source_norm_id,
                "type": "rinvia",
                "target": target_norm.id
            })

    # Pattern 4: "abroga l'art. X"
    repeal_pattern = r"abrog[ao]\s+l'art(?:icolo|\.)?\s+(\d+)\s+(c\.c\.|c\.p\.)"
    matches = re.findall(repeal_pattern, text, re.IGNORECASE)
    for match in matches:
        article, code = match
        target_norm = kg.find_norm(code=code, article=article)
        if target_norm:
            relations.append({
                "source": source_norm_id,
                "type": "abroga",
                "target": target_norm.id
            })

    return relations
```

**Temporal Relationships**:
```python
def create_temporal_relationships(versions, kg):
    """
    Create temporal sequence relationships between versions
    """
    sorted_versions = sorted(versions, key=lambda v: v["vigente_dal"])

    for i in range(len(sorted_versions) - 1):
        current_version = sorted_versions[i]
        next_version = sorted_versions[i + 1]

        # Create precede/succede relationships
        kg.create_relationship(
            current_version.node,
            "precede",
            next_version.node,
            properties={"gap_days": calculate_days_between(current_version["vigente_al"], next_version["vigente_dal"])}
        )

        kg.create_relationship(
            next_version.node,
            "succede",
            current_version.node
        )
```

### 6.3 RLCF-Driven Refinement

**Community Validation**:
```python
class KGValidationInterface:
    """
    Interface for community validation of KG nodes and relations
    """
    def submit_node_validation(self, user, node_id, validation_type, corrections=None):
        """
        User validates or corrects a KG node
        """
        feedback = {
            "user_id": user.id,
            "user_role": user.role,  # judge, lawyer, professor, etc.
            "user_authority": calculate_authority(user),
            "node_id": node_id,
            "validation_type": validation_type,  # confirm, correct, reject
            "timestamp": datetime.now()
        }

        if validation_type == "correct":
            feedback["corrections"] = corrections
            # Example: {"property": "area_legale", "old_value": "civil", "new_value": "criminal"}

        # Store feedback
        self.feedback_db.store(feedback)

        # Apply correction if high-authority user
        if user.authority >= 0.85 and validation_type == "correct":
            self.apply_correction_immediately(node_id, corrections)
        else:
            # Queue for consensus review
            self.queue_for_review(feedback)

    def submit_relation_annotation(self, user, source_node, relation_type, target_node, confidence):
        """
        User adds a new relationship not detected automatically
        """
        annotation = {
            "user_id": user.id,
            "user_authority": calculate_authority(user),
            "source_node": source_node,
            "relation_type": relation_type,
            "target_node": target_node,
            "confidence": confidence,  # user's confidence in this relation
            "timestamp": datetime.now()
        }

        # Store annotation
        self.annotation_db.store(annotation)

        # If multiple high-authority users agree, add to KG
        if self.check_consensus(annotation):
            self.kg.create_relationship(source_node, relation_type, target_node)
```

**Progressive Annotation Workflow**:
```python
def rlcf_annotation_workflow(kg, feedback_db):
    """
    Continuous loop for incorporating community feedback
    """
    while True:
        # 1. Retrieve pending validations
        pending_validations = feedback_db.get_pending_validations()

        # 2. Check for consensus
        for validation_group in group_by_node(pending_validations):
            consensus = calculate_consensus(validation_group)

            if consensus["agreement"] >= 0.75:  # 75% agreement threshold
                # Apply consensus correction
                apply_correction_to_kg(kg, validation_group.node_id, consensus["correction"])
                mark_as_resolved(validation_group)

        # 3. Retrieve new relation annotations
        new_annotations = feedback_db.get_new_annotations()

        # 4. Filter by authority and confidence
        for annotation in new_annotations:
            if annotation["user_authority"] >= 0.80 and annotation["confidence"] >= 0.75:
                # High-authority, high-confidence annotation → add immediately
                kg.create_relationship(
                    annotation["source_node"],
                    annotation["relation_type"],
                    annotation["target_node"],
                    properties={"added_by": "rlcf", "confidence": annotation["confidence"]}
                )
            else:
                # Queue for multi-user validation
                queue_for_validation(annotation)

        # 5. Sleep and repeat
        time.sleep(3600)  # Run hourly
```

**Authority Weighting Algorithm** (see [rlcf/RLCF.md](rlcf/RLCF.md) for complete mathematical treatment):
```python
def calculate_authority(user):
    """
    Dynamic authority weighting based on role and track record
    """
    # Base authority by role
    role_weights = {
        "judge": 1.0,
        "lawyer": 0.85,
        "law_professor": 0.95,
        "legal_scholar": 0.90,
        "law_student": 0.60,
        "citizen": 0.50
    }
    base_weight = role_weights.get(user.role, 0.50)

    # Track record multiplier (agreement with consensus)
    track_record = get_track_record(user.id)
    agreement_rate = track_record["agreements"] / track_record["total_feedbacks"]
    track_record_multiplier = 0.8 + (agreement_rate * 0.4)  # Range: 0.8-1.2

    # Specialization bonus (if feedback in user's area of expertise)
    specialization_bonus = 0.0
    if user.specialization and is_in_specialization_area(user.specialization, feedback_context):
        specialization_bonus = 0.05

    final_authority = base_weight * track_record_multiplier + specialization_bonus
    return min(final_authority, 1.0)  # Cap at 1.0
```

### 6.4 Entity Linking: VectorDB ↔ KG

**Automatic Linking During Ingestion**:
```python
def link_entities_during_ingestion(chunk, kg):
    """
    Attempt to link extracted entities to existing KG nodes
    """
    linking_results = {
        "norm_links": [],
        "case_links": [],
        "concept_links": [],
        "unresolved": []
    }

    # Link norm references
    for norm_ref in chunk["entities_extracted"]["norm_references"]:
        kg_node = kg.find_norm(
            code=norm_ref["law_name"],
            article=norm_ref["article"]
        )

        if kg_node:
            linking_results["norm_links"].append({
                "reference": norm_ref,
                "kg_node_id": kg_node.id,
                "confidence": 1.0  # Exact match
            })
        else:
            # Norm not in KG yet
            linking_results["unresolved"].append({
                "entity_type": "norm",
                "reference": norm_ref,
                "action": "create_kg_node"
            })

    # Link case references
    for case_ref in chunk["entities_extracted"]["case_references"]:
        kg_node = kg.find_sentenza(
            court=case_ref["court"],
            number=case_ref["number"],
            year=case_ref["year"]
        )

        if kg_node:
            linking_results["case_links"].append({
                "reference": case_ref,
                "kg_node_id": kg_node.id,
                "confidence": 1.0
            })
        else:
            linking_results["unresolved"].append({
                "entity_type": "case",
                "reference": case_ref,
                "action": "create_kg_node"
            })

    # Link legal concepts (fuzzy matching)
    for concept in chunk["entities_extracted"]["legal_concepts"]:
        kg_node = kg.find_concept_fuzzy(concept)  # Allows for variations

        if kg_node:
            linking_results["concept_links"].append({
                "concept": concept,
                "kg_node_id": kg_node.id,
                "confidence": kg_node.match_score
            })
        else:
            # New concept
            linking_results["unresolved"].append({
                "entity_type": "concept",
                "reference": concept,
                "action": "create_kg_node"
            })

    # Store linking results in chunk metadata
    chunk["kg_links"] = linking_results

    return chunk
```

**Manual Correction via RLCF**:
```python
def correct_entity_linking(user, chunk_id, entity_ref, correct_kg_node_id):
    """
    User corrects an incorrect entity link
    """
    correction = {
        "user_id": user.id,
        "user_authority": calculate_authority(user),
        "chunk_id": chunk_id,
        "entity_reference": entity_ref,
        "incorrect_link": chunk["kg_links"]["norm_links"][entity_ref]["kg_node_id"],
        "correct_link": correct_kg_node_id,
        "timestamp": datetime.now()
    }

    # Store correction
    feedback_db.store_entity_link_correction(correction)

    # Apply correction immediately if high authority
    if user.authority >= 0.85:
        vectordb.update_chunk_metadata(chunk_id, {
            f"kg_links.norm_links.{entity_ref}.kg_node_id": correct_kg_node_id
        })

    # Update linking model for future predictions
    update_linking_model(correction)
```

---

## 7. Quality Assurance and Validation

### 7.1 Validation Rules

**Completeness Checks**:
```python
def validate_completeness(document, document_type):
    """
    Ensure all required fields are present
    """
    validation_errors = []

    if document_type == "norm":
        required_fields = [
            "codice", "articolo", "data_pubblicazione", "vigente_dal", "text"
        ]
        for field in required_fields:
            if not document.get(field):
                validation_errors.append(f"Missing required field: {field}")

    elif document_type == "jurisprudence":
        required_fields = [
            "tribunale", "numero_sentenza", "anno", "data_decisione", "text"
        ]
        for field in required_fields:
            if not document.get(field):
                validation_errors.append(f"Missing required field: {field}")

    elif document_type == "doctrine":
        required_fields = [
            "author", "title", "year", "text"
        ]
        for field in required_fields:
            if not document.get(field):
                validation_errors.append(f"Missing required field: {field}")

    return validation_errors
```

**Consistency Checks**:
```python
def validate_consistency(document):
    """
    Check for logical inconsistencies in metadata
    """
    validation_errors = []

    # Temporal consistency
    if document.get("vigente_dal") and document.get("vigente_al"):
        if document["vigente_dal"] > document["vigente_al"]:
            validation_errors.append("vigente_dal cannot be after vigente_al")

    if document.get("data_pubblicazione") and document.get("vigente_dal"):
        if document["data_pubblicazione"] > document["vigente_dal"]:
            validation_errors.append("data_pubblicazione should not be after vigente_dal")

    # Hierarchical level consistency
    if document.get("tipo_norma") and document.get("livello_gerarchico"):
        expected_level = HIERARCHY_MAP[document["tipo_norma"]]
        if document["livello_gerarchico"] != expected_level:
            validation_errors.append(f"Inconsistent hierarchical level for {document['tipo_norma']}")

    # Reference validation (references should exist or be flagged)
    if document.get("riferimenti_normativi_uscenti"):
        for ref in document["riferimenti_normativi_uscenti"]:
            if not validate_norm_reference(ref):
                validation_errors.append(f"Invalid norm reference: {ref}")

    return validation_errors
```

**Quality Metrics**:
```python
def calculate_quality_metrics(document, chunks):
    """
    Calculate quality metrics for ingested document
    """
    metrics = {}

    # Entity extraction coverage
    total_chunks = len(chunks)
    chunks_with_entities = sum(1 for c in chunks if len(c["entities_extracted"]["legal_concepts"]) >= 3)
    metrics["entity_coverage"] = chunks_with_entities / total_chunks if total_chunks > 0 else 0

    # Chunk size distribution
    token_counts = [c["token_count"] for c in chunks]
    metrics["avg_chunk_size"] = sum(token_counts) / len(token_counts) if token_counts else 0
    metrics["chunk_size_variance"] = calculate_variance(token_counts)
    metrics["chunks_in_optimal_range"] = sum(1 for t in token_counts if 256 <= t <= 1024) / len(token_counts)

    # Metadata richness
    metadata_fields_populated = sum(1 for k, v in document["metadata"].items() if v is not None)
    total_metadata_fields = len(document["metadata"])
    metrics["metadata_richness"] = metadata_fields_populated / total_metadata_fields

    # Temporal coverage (for norms with versions)
    if document["document_type"] == "norm" and document.get("versions"):
        metrics["temporal_coverage"] = len(document["versions"]) > 1  # Has multiple versions
        metrics["has_complete_timeline"] = all(v.get("vigente_al") is not None for v in document["versions"][:-1])

    return metrics
```

### 7.2 Error Handling

**Retry Logic**:
```python
def ingest_document_with_retry(document_path, max_retries=3):
    """
    Ingest document with exponential backoff retry
    """
    retry_count = 0
    backoff_delay = 1  # Start with 1 second

    while retry_count < max_retries:
        try:
            # Attempt ingestion
            result = ingest_document(document_path)
            return result

        except TransientError as e:
            # Transient error (network, API rate limit, etc.)
            retry_count += 1
            if retry_count >= max_retries:
                raise

            logger.warning(f"Transient error: {e}. Retrying in {backoff_delay}s... (Attempt {retry_count}/{max_retries})")
            time.sleep(backoff_delay)
            backoff_delay *= 2  # Exponential backoff

        except PermanentError as e:
            # Permanent error (malformed document, invalid format)
            logger.error(f"Permanent error: {e}. Moving to dead letter queue.")
            move_to_dead_letter_queue(document_path, error=str(e))
            raise
```

**Dead Letter Queue**:
```python
def move_to_dead_letter_queue(document_path, error):
    """
    Move failed document to manual review queue
    """
    dlq_entry = {
        "document_path": document_path,
        "error_message": error,
        "timestamp": datetime.now(),
        "retry_count": 0,
        "status": "pending_review"
    }

    dead_letter_queue.add(dlq_entry)

    # Notify administrators
    send_alert(f"Document failed ingestion: {document_path}", error)
```

**Manual Review Interface**:
```python
class ManualReviewInterface:
    """
    Interface for administrators to review failed documents
    """
    def get_pending_reviews(self):
        """Get all documents in dead letter queue"""
        return dead_letter_queue.get_all(status="pending_review")

    def review_document(self, dlq_entry_id, action, corrections=None):
        """
        Administrator reviews and decides action
        """
        if action == "retry":
            # Retry ingestion after manual corrections
            document_path = dlq_entry["document_path"]
            if corrections:
                apply_manual_corrections(document_path, corrections)
            retry_ingestion(document_path)

        elif action == "skip":
            # Mark as skipped, do not ingest
            dead_letter_queue.update_status(dlq_entry_id, "skipped")

        elif action == "manual_ingest":
            # Manually create KG nodes and VectorDB entries
            manual_ingest_document(dlq_entry["document_path"], corrections)
            dead_letter_queue.update_status(dlq_entry_id, "manually_resolved")
```

### 7.3 Monitoring

**Real-Time Metrics**:
```python
class IngestionMonitor:
    """
    Monitor ingestion pipeline performance
    """
    def __init__(self):
        self.metrics = {
            "throughput": Gauge("documents_per_minute"),
            "latency": Histogram("ingestion_latency_seconds"),
            "error_rate": Counter("ingestion_errors"),
            "queue_size": Gauge("pending_documents")
        }

    def record_success(self, document_type, duration):
        """Record successful ingestion"""
        self.metrics["throughput"].inc()
        self.metrics["latency"].observe(duration)
        logger.info(f"Successfully ingested {document_type} in {duration:.2f}s")

    def record_error(self, document_type, error_type):
        """Record ingestion error"""
        self.metrics["error_rate"].inc()
        logger.error(f"Failed to ingest {document_type}: {error_type}")

    def check_anomalies(self):
        """Check for anomalous behavior"""
        # Error rate too high
        if self.metrics["error_rate"].value > 0.05:  # > 5% error rate
            send_alert("High error rate detected in ingestion pipeline")

        # Queue backing up
        if self.metrics["queue_size"].value > 10000:
            send_alert("Ingestion queue size exceeding threshold")

        # Latency too high
        if self.metrics["latency"].percentile(0.95) > 60:  # p95 > 60 seconds
            send_alert("Ingestion latency degraded")
```

**Dashboard Metrics**:
- **Throughput**: Documents ingested per hour/day
- **Latency**: p50, p95, p99 ingestion time
- **Error Rate**: Percentage of failed ingestions by type
- **Quality Metrics**: Average entity coverage, metadata richness
- **Queue Depth**: Pending documents in ingestion queue
- **Storage Growth**: VectorDB and KG size over time

**Alerting Rules**:
```python
ALERTING_RULES = [
    {
        "name": "High Error Rate",
        "condition": lambda metrics: metrics["error_rate"] > 0.05,
        "severity": "critical",
        "action": "send_email_and_slack"
    },
    {
        "name": "Ingestion Latency Degraded",
        "condition": lambda metrics: metrics["latency_p95"] > 60,
        "severity": "warning",
        "action": "send_slack"
    },
    {
        "name": "Dead Letter Queue Growing",
        "condition": lambda metrics: metrics["dlq_size"] > 100,
        "severity": "warning",
        "action": "send_email"
    },
    {
        "name": "Low Quality Documents",
        "condition": lambda metrics: metrics["avg_quality_score"] < 0.7,
        "severity": "info",
        "action": "send_slack"
    }
]
```

---

## 8. Implementation Architecture

### 8.1 Technology Stack Proposal

**Orchestration**:
- **Airflow** or **Prefect**: Workflow scheduling, DAG management, monitoring
  - DAGs for batch ingestion (daily norm updates, weekly jurisprudence crawls)
  - Task dependencies (parse → extract → chunk → embed → dual-write)
  - Retry logic and error handling built-in

**Processing Framework**:
- **Python 3.11+**: Core language
- **LangChain**: Document loaders, text splitters, embeddings, LLM integration
- **Pydantic**: Data validation and serialization
- **asyncio**: Asynchronous processing for I/O-bound tasks

**Entity Extraction**:
- **spaCy 3.x**: Base NER framework
  - Custom trained model on Italian legal corpus
  - Entity types: PER, ORG, LAW, COURT, CASE_NUM, LEGAL_CONCEPT
- **Regex Patterns**: Structured entity extraction (norm references, case numbers)
- **LLM Fallback**: Gemini 2.5 Flash Lite (via OpenRouter) for complex extractions
  - Use when NER confidence < 0.7
  - Use for abstract legal concepts, complex relationships

**Embedding Models**:
- **Phase 1** (0-3 months): Generic multilingual models
  - `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
  - `OpenAI text-embedding-3-large`
- **Phase 3+** (3-6 months): Fine-tuned legal domain embeddings
  - Fine-tune on Italian legal corpus (norms + jurisprudence + doctrine)
  - Contrastive learning: similar legal concepts should have similar embeddings

**Vector Database**:
- **Weaviate** (preferred): Open-source, hybrid search, schema flexibility
  - Alternative: **Qdrant** (high performance, metadata filtering)
  - Alternative: **Pinecone** (managed, serverless, excellent performance)

**Graph Database**:
- **Neo4j**: Property graph model, Cypher query language, APOC procedures
  - Excellent for relationship traversal (multivigenza, norm modifications)
  - Rich visualization tools (Neo4j Bloom)

**Message Queue**:
- **Redis** or **RabbitMQ**: Async task queue for decoupling ingestion stages
  - Producer: Document fetcher
  - Consumers: Parser, entity extractor, embedder, indexer

**Storage**:
- **Object Storage** (S3, MinIO): Raw documents (PDFs, XMLs)
- **PostgreSQL**: Metadata store, dead letter queue, monitoring logs

### 8.2 Processing Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     INGESTION ORCHESTRATOR (Airflow)                 │
└────────────┬────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: Document Acquisition                                       │
│  ├─ Fetch from API (norms, future jurisprudence)                    │
│  ├─ Web scraping (current jurisprudence sources)                    │
│  ├─ Manual upload (doctrine)                                         │
│  └─ Store raw documents in Object Storage                           │
└────────────┬────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 2: Document Type Routing                                     │
│  └─ Classify: Norm / Jurisprudence / Doctrine                       │
└────────────┬────────────────────────────────────────────────────────┘
             │
        ┌────┴─────┬──────────────┐
        ▼          ▼              ▼
  ┌──────────┐ ┌──────────┐ ┌──────────────┐
  │  Norm    │ │  Juris   │ │  Doctrine    │
  │  Parser  │ │  Parser  │ │  Parser      │
  └────┬─────┘ └────┬─────┘ └──────┬───────┘
       │            │               │
       └────────────┴───────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 3: Text Normalization                                        │
│  ├─ Whitespace cleanup                                              │
│  ├─ Encoding standardization (UTF-8)                                │
│  └─ Section identification                                          │
└────────────┬────────────────────────────────────────────────────────┘
             │
        ┌────┴─────┐
        ▼          ▼
  ┌──────────┐ ┌──────────────┐
  │  Entity  │ │  Relation    │
  │  Extract │ │  Extraction  │
  │ (NER+LLM)│ │ (Pattern+LLM)│
  └────┬─────┘ └──────┬───────┘
       │              │
       └──────┬───────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 4: Metadata Enrichment                                       │
│  ├─ Temporal metadata                                               │
│  ├─ Hierarchical classification                                     │
│  ├─ Authority scoring                                               │
│  └─ Cross-references                                                │
└────────────┬────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 5: Chunking                                                  │
│  ├─ Article-level (Norms)                                           │
│  ├─ Section-based (Jurisprudence)                                   │
│  └─ Semantic similarity-based (Doctrine)                            │
└────────────┬────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 6: Embedding Generation                                      │
│  └─ Batch embedding generation (async, rate-limited)                │
└────────────┬────────────────────────────────────────────────────────┘
             │
        ┌────┴─────┐
        ▼          ▼
  ┌──────────┐ ┌──────────────┐
  │ VectorDB │ │ Knowledge    │
  │ Ingestion│ │ Graph        │
  │          │ │ Population   │
  └──────────┘ └──────────────┘
```

### 8.3 Batch vs. Streaming Architecture

**Batch Processing** (Initial Load + Historical Corpus):
```python
# Airflow DAG for batch norm ingestion
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'merl-t',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 3,
    'retry_delay': timedelta(minutes=5)
}

dag = DAG(
    'batch_norm_ingestion',
    default_args=default_args,
    description='Batch ingestion of Italian norms',
    schedule_interval='@daily',  # Run daily
    catchup=False
)

fetch_norms_task = PythonOperator(
    task_id='fetch_norms_from_api',
    python_callable=fetch_norms_from_government_api,
    op_kwargs={'date': '{{ ds }}'},  # Airflow execution date
    dag=dag
)

parse_norms_task = PythonOperator(
    task_id='parse_akoma_ntoso',
    python_callable=parse_batch_norms,
    dag=dag
)

extract_entities_task = PythonOperator(
    task_id='extract_entities',
    python_callable=extract_entities_batch,
    dag=dag
)

chunk_and_embed_task = PythonOperator(
    task_id='chunk_and_embed',
    python_callable=chunk_and_generate_embeddings,
    dag=dag
)

dual_write_task = PythonOperator(
    task_id='write_to_vectordb_and_kg',
    python_callable=dual_write_to_stores,
    dag=dag
)

# Define task dependencies
fetch_norms_task >> parse_norms_task >> extract_entities_task >> chunk_and_embed_task >> dual_write_task
```

**Streaming Architecture** (Incremental Updates):
```python
# Real-time ingestion with message queue
import asyncio
from redis import Redis
from rq import Queue

# Setup
redis_conn = Redis(host='localhost', port=6379)
ingestion_queue = Queue('ingestion', connection=redis_conn)

async def stream_new_documents():
    """
    Monitor for new documents and enqueue for processing
    """
    while True:
        # Check for new norms published
        new_norms = await check_for_new_norms()
        for norm in new_norms:
            ingestion_queue.enqueue(ingest_document, norm, document_type="norm")

        # Check for new court decisions
        new_decisions = await check_for_new_decisions()
        for decision in new_decisions:
            ingestion_queue.enqueue(ingest_document, decision, document_type="jurisprudence")

        # Sleep for 1 hour
        await asyncio.sleep(3600)

# Worker processes consume from queue
def ingest_document(document, document_type):
    """
    Process single document through full pipeline
    """
    try:
        parsed = parse_document(document, document_type)
        entities = extract_entities(parsed)
        chunks = chunk_document(parsed, document_type)
        embeddings = generate_embeddings(chunks)
        write_to_vectordb(chunks, embeddings, entities)
        populate_kg(parsed, entities)
        return {"status": "success", "doc_id": parsed["doc_id"]}
    except Exception as e:
        logger.error(f"Failed to ingest {document}: {e}")
        move_to_dead_letter_queue(document, error=str(e))
        raise
```

### 8.4 Scalability Considerations

**Horizontal Scaling**:
```python
# Parallel processing with task distribution
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

def parallel_document_processing(documents, num_workers=None):
    """
    Process documents in parallel across multiple CPU cores
    """
    if num_workers is None:
        num_workers = multiprocessing.cpu_count()

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Map documents to workers
        futures = [executor.submit(ingest_document, doc) for doc in documents]

        # Collect results
        results = [future.result() for future in futures]

    return results
```

**Caching and Deduplication**:
```python
import hashlib

def calculate_document_hash(document):
    """
    Generate deterministic hash of document content
    """
    content = document["text"] + document["metadata"]["doc_id"]
    return hashlib.sha256(content.encode()).hexdigest()

def check_if_already_processed(doc_hash, cache):
    """
    Check if document was already processed
    """
    return cache.exists(doc_hash)

def ingest_with_deduplication(document, cache):
    """
    Skip ingestion if document already processed
    """
    doc_hash = calculate_document_hash(document)

    if check_if_already_processed(doc_hash, cache):
        logger.info(f"Document {doc_hash} already processed. Skipping.")
        return {"status": "skipped", "reason": "duplicate"}

    # Process document
    result = ingest_document(document)

    # Mark as processed
    cache.set(doc_hash, result, ex=86400 * 30)  # Cache for 30 days

    return result
```

**Incremental Indexing**:
```python
def incremental_update_vectordb(new_chunks, vectordb):
    """
    Add only new chunks to VectorDB without full reindex
    """
    # Filter out chunks that already exist
    existing_chunk_ids = vectordb.get_all_chunk_ids()
    new_chunks_filtered = [c for c in new_chunks if c["chunk_id"] not in existing_chunk_ids]

    if not new_chunks_filtered:
        logger.info("No new chunks to index")
        return

    # Index only new chunks
    vectordb.upsert(new_chunks_filtered)
    logger.info(f"Indexed {len(new_chunks_filtered)} new chunks")

def incremental_update_kg(new_nodes, new_relations, kg):
    """
    Add only new nodes and relations to KG
    """
    # Check for existing nodes
    for node in new_nodes:
        if not kg.node_exists(node["node_id"]):
            kg.create_node(node["type"], node["properties"])

    # Check for existing relations
    for relation in new_relations:
        if not kg.relation_exists(relation["source"], relation["type"], relation["target"]):
            kg.create_relationship(relation["source"], relation["type"], relation["target"])
```

---

## 9. Production Deployment Roadmap

### 9.1 Phase 1: MVP (Months 0-3)

**Scope**:
- Ingest **subset** of high-priority legal content:
  - 100 key norms from Codice Civile (Articles 1-100, key contract law articles)
  - 50 landmark court decisions (Cassazione binding precedent)
  - 10 doctrinal manuals (most cited treatises)

**Infrastructure**:
- **Single-machine deployment** (16-core, 64GB RAM, 1TB SSD)
- **Manual ingestion pipeline**: Python scripts + n8n-like workflow
- **VectorDB**: Weaviate (single-node, Docker)
- **KG**: Neo4j Community Edition (single-node, Docker)
- **Monitoring**: Basic logging to files

**Quality Validation**:
- **Manual review** of all ingested content
- **Sample-based entity extraction validation** (human review of 10% of chunks)
- **Basic quality metrics**: entity coverage, chunk size distribution

**Goals**:
- Validate ingestion pipeline works end-to-end
- Tune chunking parameters (similarity threshold, chunk size)
- Identify common parsing/extraction errors
- Establish baseline quality metrics

### 9.2 Phase 2: Automation (Months 3-6)

**Scope**:
- Expand to **500 norms**, **200 decisions**, **30 manuals**
- Automate ingestion with Airflow orchestration
- Implement RLCF feedback loop for community validation

**Infrastructure**:
- **Cluster deployment**:
  - 3 worker nodes for parallel processing
  - Separate VectorDB cluster (3-node Weaviate)
  - Separate KG cluster (3-node Neo4j Enterprise)
- **Airflow** for workflow orchestration (DAGs for batch and streaming)
- **Redis** for message queue
- **PostgreSQL** for metadata store and dead letter queue
- **Grafana + Prometheus** for monitoring

**Automation**:
- **Daily batch ingestion** of new norms (Gazzetta Ufficiale monitoring)
- **Weekly jurisprudence crawling** (court websites)
- **On-demand doctrine ingestion** (manual upload interface)

**RLCF Integration**:
- **Feedback collection interface** launched
- **Community validation workflow** for KG nodes and relations
- **Initial feedback accumulation**: target 1000 feedback samples

**Quality Improvements**:
- **Automated validation rules** (completeness, consistency checks)
- **Entity extraction improvements** based on Phase 1 error analysis
- **Custom NER model training** on Italian legal corpus

### 9.3 Phase 3: Scale (Months 6-12)

**Scope**:
- **Full ingestion**:
  - All norms from Codice Civile (2969 articles)
  - All norms from Codice Penale (734 articles)
  - Key special laws (L. 194/1978, L. 300/1970, D.Lgs. 81/2008, etc.)
  - 5000+ court decisions (last 10 years)
  - 100+ doctrinal works

**Infrastructure**:
- **Cloud-native architecture** (AWS, GCP, or Azure):
  - Auto-scaling worker pools (10-50 nodes based on load)
  - Managed VectorDB (Pinecone or Weaviate Cloud)
  - Managed Neo4j (AuraDB)
  - Airflow on Kubernetes (auto-scaling executors)
- **Advanced monitoring**: Real-time dashboards, alerting, SLA tracking

**KG Maturity**:
- **10,000+ validated nodes** via RLCF
- **50,000+ validated relationships**
- **Temporal coverage**: 80% of norms have complete multivigenza timeline
- **Entity linking accuracy**: 95%+

**Performance Optimization**:
- **Embedding model fine-tuning**: Train on 10K+ Italian legal documents
- **Caching layer**: Redis cache for frequently accessed norms/decisions
- **Query optimization**: Index tuning for VectorDB and KG

**Quality Targets**:
- **Entity extraction coverage**: 90%+ of chunks have ≥3 entities
- **Metadata richness**: 95%+ of fields populated
- **Dead letter queue**: <1% of documents fail ingestion

### 9.4 Phase 4: Production (Year 2+)

**Scope**:
- **Comprehensive legal corpus**:
  - All primary Italian legislation (20,000+ norms)
  - Complete jurisprudence coverage (50,000+ decisions)
  - Extensive doctrinal library (500+ works)
  - Regional and administrative law integration

**Infrastructure**:
- **Multi-region deployment** for high availability
- **Disaster recovery**: Automated backups, point-in-time recovery
- **Performance**: <100ms Vector search, <500ms KG queries at p95

**Advanced Features**:
- **Real-time streaming ingestion**: New norms and decisions indexed within 1 hour of publication
- **Advanced entity linking**: Deep learning model for cross-document entity resolution
- **Multi-source federation**: Integration with European legal databases (EUR-Lex, ECHR)
- **Automated relationship inference**: ML model to predict missing KG relationships

**Continuous Improvement**:
- **Monthly RLCF-driven updates**: Fine-tune extraction models based on community feedback
- **Quarterly KG expansion**: Add new node types and relations based on user annotations
- **Annual architecture review**: Evaluate new technologies, optimize costs

**Success Metrics**:
- **Coverage**: 99% of cited norms/decisions in corpus
- **Quality**: 98% citation accuracy, 4.5/5 user satisfaction
- **Performance**: 99.9% uptime, <2s average query response time
- **Cost**: <$0.01 per query (optimized via fine-tuned small models)

---

## Appendix A: Sample Metadata Schemas

### Norm Metadata (Complete Example)
```json
{
  "chunk_id": "cc_art_1418_chunk_0",
  "doc_id": "hash_cc_art_1418",
  "document_type": "norm",
  "text": "Il contratto è nullo quando è contrario a norme imperative, salvo che la legge disponga diversamente. Producono nullità del contratto la mancanza di uno dei requisiti indicati dall'articolo 1325, l'illiceità della causa, l'illiceità dei motivi nel caso indicato dall'articolo 1345 e la mancanza nell'oggetto dei requisiti stabiliti dall'articolo 1346.",
  "token_count": 78,
  "chunk_index": 0,
  "total_chunks": 1,
  "temporal_metadata": {
    "date_published": "1942-04-04",
    "date_effective": "1942-04-21",
    "date_end": null
  },
  "classification": {
    "legal_area": "civil",
    "legal_domain_tags": ["contratti", "nullità", "invalidità", "requisiti"],
    "materia": "diritto_civile_contratti_invalidita"
  },
  "authority_metadata": {
    "hierarchical_level": 3,
    "binding_force": null,
    "authority_score": 1.0
  },
  "entities_extracted": {
    "norm_references": [
      {"law_name": "c.c.", "article": "1325", "comma": null},
      {"law_name": "c.c.", "article": "1345", "comma": null},
      {"law_name": "c.c.", "article": "1346", "comma": null}
    ],
    "case_references": [],
    "legal_concepts": ["nullità", "norme imperative", "causa illecita", "motivi illeciti", "requisiti essenziali"],
    "persons": [],
    "legal_entities": []
  },
  "chunk_quality": {
    "internal_similarity": null,
    "embedding_model": "text-embedding-3-large",
    "processing_timestamp": "2024-03-15T10:00:00Z"
  },
  "source_metadata": {
    "source_type": "norm",
    "norm_identification": {
      "codice": "cc",
      "numero": "262",
      "anno": 1942,
      "articolo": "1418",
      "comma": null,
      "libro": "IV",
      "titolo": "II",
      "capo": "XII",
      "sezione": null
    },
    "norm_type": "codice_civile",
    "norm_title": "Cause di nullità del contratto",
    "version_info": {
      "version_number": 1,
      "version_date": "1942-04-21",
      "modified_by": null,
      "modification_type": "originale"
    },
    "publication_info": {
      "gazzetta_ufficiale": "GU n. 79 del 04/04/1942",
      "publication_date": "1942-04-04"
    }
  },
  "kg_links": {
    "norm_nodes": ["kg_node_cc_art_1325", "kg_node_cc_art_1345", "kg_node_cc_art_1346"],
    "case_nodes": [],
    "concept_nodes": ["kg_node_concept_nullita", "kg_node_concept_causa_illecita"]
  }
}
```

---

**Document Version**: 1.0
**Last Updated**: 2024-03-15
**Authors**: MERL-T Architecture Team
**Status**: Framework Documentation
