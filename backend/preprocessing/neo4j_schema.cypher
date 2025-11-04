// MERL-T Neo4j Knowledge Graph Schema
// Implementation of docs/02-methodology/knowledge-graph.md
// Defines 23 node types and 65+ relationship types for Italian legal domain

// ============================================================================
// CONSTRAINTS AND UNIQUE PROPERTIES
// ============================================================================

// URN constraints (unique per node)
CREATE CONSTRAINT norma_urn_unique IF NOT EXISTS
  FOR (n:Norma) REQUIRE n.urn IS UNIQUE;

CREATE CONSTRAINT direttiva_urn_unique IF NOT EXISTS
  FOR (d:DirettivalUE) REQUIRE d.urn IS UNIQUE;

CREATE CONSTRAINT regolamento_urn_unique IF NOT EXISTS
  FOR (r:RegolamentoUE) REQUIRE r.urn IS UNIQUE;

// ID constraints
CREATE CONSTRAINT node_id_unique IF NOT EXISTS
  FOR (n:Entity) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT edge_id_unique IF NOT EXISTS
  FOR (e:Relationship) REQUIRE e.id IS UNIQUE;

// ============================================================================
// INDEXES FOR FAST LOOKUP
// ============================================================================

// Norma (Legal Norm) indexes
CREATE INDEX norma_id IF NOT EXISTS FOR (n:Norma) ON (n.node_id);
CREATE INDEX norma_article IF NOT EXISTS FOR (n:Norma) ON (n.article_number);
CREATE INDEX norma_title IF NOT EXISTS FOR (n:Norma) ON (n.titolo);
CREATE INDEX norma_status IF NOT EXISTS FOR (n:Norma) ON (n.stato);
CREATE INDEX norma_efficacia IF NOT EXISTS FOR (n:Norma) ON (n.efficacia);

// Concetto Giuridico (Legal Concept) indexes
CREATE INDEX concept_nome IF NOT EXISTS FOR (c:ConcettoGiuridico) ON (c.nome);
CREATE INDEX concept_applicazione IF NOT EXISTS FOR (c:ConcettoGiuridico) ON (c.ambito_di_applicazione);

// Versione (Version) indexes
CREATE INDEX version_numero IF NOT EXISTS FOR (v:Versione) ON (v.numero_versione);
CREATE INDEX version_inizio IF NOT EXISTS FOR (v:Versione) ON (v.data_inizio_validita);

// Atto Giudiziario (Judicial Act) indexes
CREATE INDEX atto_date IF NOT EXISTS FOR (a:AttoGiudiziario) ON (a.data);
CREATE INDEX atto_organo IF NOT EXISTS FOR (a:AttoGiudiziario) ON (a.organo_emittente);

// Generic indexes for validation and confidence
CREATE INDEX validation_status IF NOT EXISTS FOR (n) ON (n.validation_status);
CREATE INDEX confidence_score IF NOT EXISTS FOR (n) ON (n.confidence);

// Full-text search indexes for content search
CREATE INDEX norma_text IF NOT EXISTS FOR (n:Norma) ON (n.testo_vigente);
CREATE INDEX concept_definizione IF NOT EXISTS FOR (c:ConcettoGiuridico) ON (c.definizione);

// ============================================================================
// STRUCTURAL ELEMENTS (Support for temporal versioning)
// ============================================================================

// Create indexes for clause-level granularity
CREATE INDEX comma_posizione IF NOT EXISTS FOR (c:Comma) ON (c.posizione);
CREATE INDEX lettera_posizione IF NOT EXISTS FOR (l:Lettera) ON (l.posizione);
CREATE INDEX numero_posizione IF NOT EXISTS FOR (n:Numero) ON (n.posizione);

// ============================================================================
// RELATIONSHIP TYPE INDEXES
// ============================================================================

// Index relationship properties for efficient traversal
CREATE INDEX disciplina_rel IF NOT EXISTS FOR ()-[r:DISCIPLINA]-() ON (r.confidence);
CREATE INDEX contiene_rel IF NOT EXISTS FOR ()-[r:CONTIENE]-() ON (r.data_decorrenza);
CREATE INDEX cita_rel IF NOT EXISTS FOR ()-[r:CITA]-() ON (r.confidence);
CREATE INDEX modifica_rel IF NOT EXISTS FOR ()-[r:MODIFICA]-() ON (r.data_efficacia);
CREATE INDEX abroga_rel IF NOT EXISTS FOR ()-[r:ABROGA]-() ON (r.data_efficacia);

// ============================================================================
// OPTIONAL: Create supporting reference nodes
// These help with organizing and querying the graph
// ============================================================================

// Create system root nodes for taxonomy and hierarchies
CREATE (legal_system:LegalSystem {
  name: "Italian Legal System",
  language: "it",
  jurisdiction: "Italy",
  created_at: datetime()
});

// Create document type classifications
CREATE (statuti:Categoria {
  name: "Statuti",
  tipo: "source_classification",
  description: "Statutory legislation"
});

CREATE (case_law:Categoria {
  name: "Giurisprudenza",
  tipo: "source_classification",
  description: "Case law and judicial decisions"
});

CREATE (doctrine:Categoria {
  name: "Dottrina",
  tipo: "source_classification",
  description: "Legal doctrine and scholarship"
});

// ============================================================================
// NOTES FOR SCHEMA USAGE
// ============================================================================

// Node Types Implemented:
// 1. Norma (Legal Norm/Article)
// 2. ConcettoGiuridico (Legal Concept)
// 3. Soggetto (Legal Subject)
// 4. AttoGiudiziario (Judicial Act)
// 5. Dottrina (Doctrine/Commentary)
// 6. Procedura (Procedure)
// 7. Comma/Lettera/Numero (Clauses - granular)
// 8. Versione (Temporal Version)
// 9. DirettivalUE (EU Directive)
// 10. OrganoGiurisdizionale (Jurisdictional Body)
// 11. Caso (Case/Fact)
// 12. Termine (Term/Deadline)
// 13. Sanzione (Penalty)
// 14. DefinizioneLegale (Legal Definition)
// 15. ModalitaGiuridica (Legal Modality)
// 16. Responsabilita (Responsibility)
// 17. DrittoSoggettivo (Subjective Right)
// 18. InteresseLegittimo (Legitimate Interest)
// 19. PrincipioGiuridico (Legal Principle)
// 20. FattoGiuridico (Legal Fact)
// 21. RuoloGiuridico (Legal Role)
// 22. Regola (Rule)
// 23. ProposizioneGiuridica (Legal Proposition)

// Relationship Types Implemented (Top 20 of 65):
// Structural: CONTIENE, PARTE_DI, VERSIONE_PRECEDENTE, VERSIONE_SUCCESSIVA, HA_VERSIONE
// Modification: SOSTITUISCE, INSERISCE, ABROGA_TOTALMENTE, ABROGA_PARZIALMENTE, SOSPENDE, PROROGA, INTEGRA, DEROGA_A, CONSOLIDA
// Semantic: DISCIPLINA, APPLICA_A, DEFINISCE, PREVEDE_SANZIONE, STABILISCE_TERMINE, PREVEDE
// Dependency: DIPENDE_DA, PRESUPPONE, SPECIES
// Citation: CITA, INTERPRETA, COMMENTA
// European: ATTUA, RECEPISCE, CONFORME_A
// Institutional: EMESSO_DA, HA_COMPETENZA_SU, GERARCHICAMENTE_SUPERIORE
// Case-based: RIGUARDA, APPLICA_NORMA_A_CASO, PRECEDENTE_DI
// Classification: FONTE, CLASSIFICA_IN
// LKIF-aligned: IMPONE, CONFERISCE, TITOLARE_DI, RIVESTE_RUOLO, ATTRIBUISCE_RESPONSABILITA, RESPONSABILE_PER, ESPRIME_PRINCIPIO, CONFORMA_A, DEROGA_PRINCIPIO, BILANCIA_CON
// Fact-based: PRODUCE_EFFETTO, PRESUPPOSTO_DI, COSTITUTIVO_DI, ESTINGUE, MODIFICA_EFFICACIA
// Logical: APPLICA_REGOLA, IMPLICA, CONTRADICE, GIUSTIFICA, LIMITA, TUTELA, VIOLA, COMPATIBILE_CON, INCOMPATIBILE_CON, SPECIFICA, ESEMPLIFICA, CAUSA_DI, CONDIZIONE_DI

// For Phase 2 MVP: Focus on these core relationships
// 1. DISCIPLINA (norm → concept)
// 2. CONTIENE (norm → clause)
// 3. PARTE_DI (clause → norm)
// 4. CITA (norm → norm)
// 5. MODIFICA (norm → norm)
// 6. ABROGA_TOTALMENTE / ABROGA_PARZIALMENTE
// 7. HA_VERSIONE (norm → version)
// 8. APPLICA_A (norm → subject)
// 9. PREVEDE_SANZIONE (norm → penalty)
// 10. EMESSO_DA (act → body)

// ============================================================================
// USAGE IN MERL-T PREPROCESSING PIPELINE
// ============================================================================

// Query 1: Find all norms governing a legal concept
// MATCH (c:ConcettoGiuridico {nome: $concept})-[:DISCIPLINA]-(n:Norma)
// RETURN n

// Query 2: Find norms related via citations
// MATCH (n1:Norma)-[:CITA*1..3]-(n2:Norma)
// WHERE n1.id = $norm_id
// RETURN n2

// Query 3: Get hierarchical structure of a norm
// MATCH (n:Norma {article_number: $article})-[:CONTIENE]->(c:Comma)
// RETURN n, collect(c)

// Query 4: Find modifications and amendments
// MATCH (modifier)-[:MODIFICA|ABROGA_TOTALMENTE|ABROGA_PARZIALMENTE]->(n:Norma)
// RETURN modifier, n

// Query 5: Get temporal versions of a norm
// MATCH (n:Norma)-[:HA_VERSIONE]->(v:Versione)
// WHERE n.article_number = $article
// ORDER BY v.data_inizio_validita DESC
// RETURN n, v
