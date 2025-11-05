// ===========================================
// MERL-T Knowledge Graph Schema
// ===========================================
//
// Initialization script for Memgraph/Neo4j graph database
// Defines nodes, relationships, constraints, and indexes
// for Italian legal knowledge graph
//
// Schema Version: 1.0.0
// Date: November 2025
// ===========================================

// ===========================================
// 1. NODE CONSTRAINTS (Uniqueness)
// ===========================================
// Neo4j 5.x syntax: CREATE CONSTRAINT FOR ... REQUIRE ...

// Primary legal entities
CREATE CONSTRAINT norma_id_unique IF NOT EXISTS FOR (n:Norma) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT articolo_id_unique IF NOT EXISTS FOR (a:Articolo) REQUIRE a.id IS UNIQUE;
CREATE CONSTRAINT sentenza_id_unique IF NOT EXISTS FOR (s:Sentenza) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT dottrina_id_unique IF NOT EXISTS FOR (d:Dottrina) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT concetto_id_unique IF NOT EXISTS FOR (c:Concetto) REQUIRE c.id IS UNIQUE;

// Contributing entities
CREATE CONSTRAINT contributo_id_unique IF NOT EXISTS FOR (co:Contributo) REQUIRE co.id IS UNIQUE;
CREATE CONSTRAINT utente_id_unique IF NOT EXISTS FOR (u:Utente) REQUIRE u.id IS UNIQUE;

// ===========================================
// 2. INDEXES (Performance)
// ===========================================

// Norma indexes
CREATE INDEX norma_tipo_index IF NOT EXISTS FOR (n:Norma) ON (n.tipo);
CREATE INDEX norma_stato_index IF NOT EXISTS FOR (n:Norma) ON (n.stato);
CREATE INDEX norma_vigore_index IF NOT EXISTS FOR (n:Norma) ON (n.data_entrata_vigore);
CREATE INDEX norma_abrogazione_index IF NOT EXISTS FOR (n:Norma) ON (n.data_abrogazione);

// Articolo indexes
CREATE INDEX articolo_numero_index IF NOT EXISTS FOR (a:Articolo) ON (a.numero);
CREATE INDEX articolo_norma_id_index IF NOT EXISTS FOR (a:Articolo) ON (a.norma_id);

// Sentenza indexes
CREATE INDEX sentenza_organo_index IF NOT EXISTS FOR (s:Sentenza) ON (s.organo);
CREATE INDEX sentenza_data_index IF NOT EXISTS FOR (s:Sentenza) ON (s.data);
CREATE INDEX sentenza_materia_index IF NOT EXISTS FOR (s:Sentenza) ON (s.materia);

// Dottrina indexes
CREATE INDEX dottrina_autore_index IF NOT EXISTS FOR (d:Dottrina) ON (d.autore);
CREATE INDEX dottrina_anno_index IF NOT EXISTS FOR (d:Dottrina) ON (d.anno_pubblicazione);
CREATE INDEX dottrina_fonte_index IF NOT EXISTS FOR (d:Dottrina) ON (d.fonte);

// Concetto indexes
CREATE INDEX concetto_dominio_index IF NOT EXISTS FOR (c:Concetto) ON (c.dominio);
CREATE INDEX concetto_nome_index IF NOT EXISTS FOR (c:Concetto) ON (c.nome);

// Contributo indexes (community)
CREATE INDEX contributo_stato_index IF NOT EXISTS FOR (co:Contributo) ON (co.stato);
CREATE INDEX contributo_data_index IF NOT EXISTS FOR (co:Contributo) ON (co.data_creazione);

// ===========================================
// 3. SAMPLE DATA (Optional - for testing)
// ===========================================

// Famous Italian legal norms for validation

// Codice Civile Art. 1321 (Definizione di contratto)
CREATE (n1:Norma {
    id: "cc",
    tipo: "codice",
    titolo: "Codice Civile",
    stato: "vigente",
    data_entrata_vigore: date("1942-04-21"),
    data_abrogazione: null
});

CREATE (a1321:Articolo {
    id: "cc_art_1321",
    numero: "1321",
    titolo: "Nozione di contratto",
    testo_vigente: "Il contratto è l'accordo di due o più parti per costituire, regolare o estinguere tra loro un rapporto giuridico patrimoniale.",
    stato: "vigente",
    data_entrata_vigore: date("1942-04-21"),
    norma_id: "cc"
});

CREATE (n1)-[:CONTIENE]->(a1321);

// Costituzione Art. 3 (Principio di eguaglianza)
CREATE (n2:Norma {
    id: "cost",
    tipo: "costituzione",
    titolo: "Costituzione della Repubblica Italiana",
    stato: "vigente",
    data_entrata_vigore: date("1948-01-01"),
    data_abrogazione: null
});

CREATE (a3:Articolo {
    id: "cost_art_3",
    numero: "3",
    titolo: "Principio di eguaglianza",
    testo_vigente: "Tutti i cittadini hanno pari dignità sociale e sono eguali davanti alla legge, senza distinzione di sesso, di razza, di lingua, di religione, di opinioni politiche, di condizioni personali e sociali.",
    stato: "vigente",
    data_entrata_vigore: date("1948-01-01"),
    norma_id: "cost"
});

CREATE (n2)-[:CONTIENE]->(a3);

// GDPR Art. 6 (Base giuridica del trattamento)
CREATE (n3:Norma {
    id: "gdpr",
    tipo: "regolamento_europeo",
    titolo: "Regolamento (UE) 2016/679 (GDPR)",
    stato: "vigente",
    data_entrata_vigore: date("2018-05-25"),
    data_abrogazione: null
});

CREATE (a6_gdpr:Articolo {
    id: "gdpr_art_6",
    numero: "6",
    titolo: "Liceità del trattamento",
    testo_vigente: "Il trattamento è lecito solo se e nella misura in cui ricorre almeno una delle seguenti condizioni: a) l'interessato ha espresso il consenso...",
    stato: "vigente",
    data_entrata_vigore: date("2018-05-25"),
    norma_id: "gdpr"
});

CREATE (n3)-[:CONTIENE]->(a6_gdpr);

// ===========================================
// 4. LEGAL CONCEPTS
// ===========================================

// Contract-related concepts
CREATE (c1:Concetto {
    id: "concetto_contratto",
    nome: "contratto",
    dominio: "diritto_civile",
    descrizione: "Accordo tra due o più parti per costituire, regolare o estinguere un rapporto giuridico patrimoniale"
});

CREATE (c2:Concetto {
    id: "concetto_consenso",
    nome: "consenso",
    dominio: "diritto_civile",
    descrizione: "Manifestazione di volontà delle parti per concludere un contratto"
});

CREATE (c3:Concetto {
    id: "concetto_capacita",
    nome: "capacità di agire",
    dominio: "diritto_civile",
    descrizione: "Idoneità del soggetto a compiere atti giuridici validi"
});

// GDPR concepts
CREATE (c4:Concetto {
    id: "concetto_privacy",
    nome: "privacy",
    dominio: "gdpr",
    descrizione: "Diritto alla protezione dei dati personali"
});

CREATE (c5:Concetto {
    id: "concetto_trattamento_dati",
    nome: "trattamento dati",
    dominio: "gdpr",
    descrizione: "Qualsiasi operazione o insieme di operazioni compiute su dati personali"
});

CREATE (c6:Concetto {
    id: "concetto_titolare",
    nome: "titolare del trattamento",
    dominio: "gdpr",
    descrizione: "Persona fisica o giuridica che determina le finalità e i mezzi del trattamento"
});

// Constitutional concepts
CREATE (c7:Concetto {
    id: "concetto_eguaglianza",
    nome: "eguaglianza",
    dominio: "diritto_costituzionale",
    descrizione: "Pari dignità sociale e eguaglianza davanti alla legge"
});

// ===========================================
// 5. CONCEPT RELATIONSHIPS
// ===========================================

// Link concepts to articles
CREATE (a1321)-[:TRATTA]->(c1);
CREATE (a1321)-[:TRATTA]->(c2);
CREATE (a1321)-[:TRATTA]->(c3);

CREATE (a6_gdpr)-[:TRATTA]->(c4);
CREATE (a6_gdpr)-[:TRATTA]->(c5);
CREATE (a6_gdpr)-[:TRATTA]->(c6);
CREATE (a6_gdpr)-[:TRATTA]->(c2);  // Consensus anche in GDPR

CREATE (a3)-[:TRATTA]->(c7);

// ===========================================
// 6. RELATIONSHIP TYPES (Documentation)
// ===========================================

// Node-to-Node relationships:
//
// (Norma)-[:CONTIENE]->(Articolo)
//   - Una norma contiene uno o più articoli
//
// (Articolo)-[:MODIFICA]->(Articolo)
//   - Un articolo modifica un altro articolo
//
// (Articolo)-[:ABROGATO_DA]->(Articolo)
//   - Un articolo è abrogato da un altro articolo
//
// (Articolo)-[:TRATTA]->(Concetto)
//   - Un articolo tratta un concetto giuridico
//
// (Sentenza)-[:APPLICA]->(Articolo)
//   - Una sentenza applica un articolo
//
// (Sentenza)-[:INTERPRETA]->(Articolo)
//   - Una sentenza interpreta un articolo
//
// (Dottrina)-[:COMMENTA]->(Articolo)
//   - Dottrina commenta un articolo
//
// (Contributo)-[:PROPONE_MODIFICA_A]->(Articolo)
//   - Community contribution proposes modification
//
// (Utente)-[:HA_CREATO]->(Contributo)
//   - User creates a contribution
//
// (Utente)-[:HA_VOTATO {voto: 1|-1}]->(Contributo)
//   - User votes on contribution

// ===========================================
// 7. VALIDATION QUERIES (Test after load)
// ===========================================

// Query 1: Count nodes by type
// MATCH (n) RETURN labels(n) AS type, count(*) AS count;

// Query 2: Verify Art. 1321 exists
// MATCH (a:Articolo {id: "cc_art_1321"}) RETURN a;

// Query 3: Find all concepts related to contracts
// MATCH (a:Articolo)-[:TRATTA]->(c:Concetto {dominio: "diritto_civile"})
// RETURN a.id, a.titolo, c.nome;

// Query 4: Find articles modified by others
// MATCH (a1:Articolo)-[:MODIFICA]->(a2:Articolo)
// RETURN a1.id, a2.id;

// Query 5: Temporal query - active norms
// MATCH (n:Norma)
// WHERE n.data_entrata_vigore <= date()
//   AND (n.data_abrogazione IS NULL OR n.data_abrogazione > date())
// RETURN n.id, n.titolo;

// ===========================================
// END OF SCHEMA
// ===========================================
//
// Notes:
// - This schema supports multi-source data (Normattiva, Cassazione, Dottrina, Community, RLCF)
// - Temporal versioning is supported through date fields
// - Provenance tracking is implicit through source field on nodes
// - All IDs follow convention: {source}_{type}_{identifier}
//   Examples: cc_art_1321, gdpr_art_6, cost_art_3
//
// Next steps after loading:
// 1. Run validation queries
// 2. Check indexes created successfully
// 3. Verify constraints enforced
// 4. Test performance of common queries
// ===========================================
