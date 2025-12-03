"""
Test: First Batch Ingestion
============================

Test the complete ingestion pipeline with real articles from Codice Civile.

Articles to ingest: Art. 1453-1456 c.c. (Risoluzione del contratto)

Flow:
1. Generate URN using VisualexAPI urngenerator
2. Create FalkorDB nodes (Norma, ConcettoGiuridico, etc.)
3. Verify graph structure

This test uses embedded VisualexAPI tools (no external API calls).
"""

import asyncio
import pytest
import pytest_asyncio
import structlog
from backend.storage.falkordb.client import FalkorDBClient, FalkorDBConfig
from backend.external_sources.visualex.tools import urngenerator

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)

log = structlog.get_logger(__name__)


@pytest_asyncio.fixture(scope="function")
async def falkor_client():
    """Initialize FalkorDB client for testing."""
    config = FalkorDBConfig(
        host="localhost",
        port=6380,
        graph_name="merl_t_test"
    )
    client = FalkorDBClient(config)
    await client.connect()

    yield client

    # Cleanup: Delete test graph
    await client.query("MATCH (n) DETACH DELETE n")
    await client.close()


@pytest.mark.asyncio
async def test_urn_generation():
    """Test URN generation for Codice Civile articles."""
    log.info("Testing URN generation for Art. 1453-1456 c.c.")

    test_cases = [
        {
            "act_type": "codice civile",
            "date": "1942",
            "act_number": "262",
            "article": "1453",
        },
        {
            "act_type": "codice civile",
            "date": "1942",
            "act_number": "262",
            "article": "1454",
        },
        {
            "act_type": "codice civile",
            "date": "1942",
            "act_number": "262",
            "article": "1455",
        },
        {
            "act_type": "codice civile",
            "date": "1942",
            "act_number": "262",
            "article": "1456",
        },
    ]

    for test in test_cases:
        urn = urngenerator.generate_urn(
            act_type=test["act_type"],
            date=test["date"],
            act_number=test["act_number"],
            article=test["article"],
            urn_flag=True
        )

        log.info(f"Generated URN for Art. {test['article']}", urn=urn)

        # Verify URN format (should be Normattiva format, not ELI)
        assert urn is not None
        assert "normattiva.it" in urn
        assert "urn:nir:stato:" in urn
        assert f"art{test['article']}" in urn

        # Should NOT be ELI format
        assert not urn.startswith("/eli/")


@pytest.mark.asyncio
async def test_create_norma_nodes(falkor_client):
    """Test creating Norma nodes in FalkorDB."""
    log.info("Testing Norma node creation")

    # Generate URN for Art. 1453
    urn = urngenerator.generate_urn(
        act_type="codice civile",
        date="1942",
        act_number="262",
        article="1453",
        urn_flag=True
    )

    codice_urn = urngenerator.generate_urn(
        act_type="codice civile",
        date="1942",
        act_number="262",
        article=None,  # No article for root
        urn_flag=True
    )

    log.info("URNs generated", article_urn=urn, codice_urn=codice_urn)

    # Create Codice node
    await falkor_client.query(
        """
        MERGE (codice:Norma {URN: $codice_urn})
        ON CREATE SET
            codice.node_id = $codice_urn,
            codice.estremi = 'Codice Civile',
            codice.titolo = 'Codice Civile',
            codice.tipo_documento = 'codice',
            codice.data_pubblicazione = '1942-03-16',
            codice.stato = 'vigente',
            codice.efficacia = 'permanente',
            codice.ambito_territoriale = 'nazionale'
        """,
        {
            "codice_urn": codice_urn,
        }
    )

    # Create Article node
    await falkor_client.query(
        """
        MERGE (art:Norma {URN: $urn})
        ON CREATE SET
            art.node_id = $urn,
            art.estremi = 'Art. 1453 c.c.',
            art.titolo = 'Risoluzione per inadempimento',
            art.tipo_documento = 'articolo',
            art.testo_vigente = $testo,
            art.data_pubblicazione = '1942-03-16',
            art.versione = 'vigente',
            art.stato = 'vigente',
            art.ambito_territoriale = 'nazionale'
        """,
        {
            "urn": urn,
            "testo": "Nei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie le sue obbligazioni, l'altro può a sua scelta chiedere l'adempimento o la risoluzione del contratto, salvo, in ogni caso, il risarcimento del danno.",
        }
    )

    # Create 'contiene' relation
    await falkor_client.query(
        """
        MATCH (codice:Norma {URN: $codice_urn})
        MATCH (art:Norma {URN: $art_urn})
        MERGE (codice)-[r:contiene]->(art)
        ON CREATE SET
            r.data_decorrenza = '1942-03-16',
            r.certezza = 'esplicita',
            r.fonte_relazione = 'test'
        """,
        {
            "codice_urn": codice_urn,
            "art_urn": urn,
        }
    )

    log.info("Nodes and relation created")

    # Verify nodes exist
    results = await falkor_client.query(
        """
        MATCH (codice:Norma)-[r:contiene]->(art:Norma)
        WHERE codice.tipo_documento = 'codice'
        AND art.tipo_documento = 'articolo'
        RETURN codice.estremi AS codice_estremi,
               art.estremi AS art_estremi,
               type(r) AS relation
        """
    )

    log.info("Query results", results=results)

    assert len(results) == 1
    assert results[0]["codice_estremi"] == "Codice Civile"
    assert results[0]["art_estremi"] == "Art. 1453 c.c."
    assert results[0]["relation"] == "contiene"


@pytest.mark.asyncio
async def test_create_concetto_giuridico(falkor_client):
    """Test creating ConcettoGiuridico nodes with 'disciplina' relation."""
    log.info("Testing ConcettoGiuridico node creation")

    # Generate URN for Art. 1453
    art_urn = urngenerator.generate_urn(
        act_type="codice civile",
        date="1942",
        act_number="262",
        article="1453",
        urn_flag=True
    )

    # Create Article first (if not exists)
    await falkor_client.query(
        """
        MERGE (art:Norma {URN: $urn})
        ON CREATE SET
            art.estremi = 'Art. 1453 c.c.',
            art.tipo_documento = 'articolo'
        """,
        {"urn": art_urn}
    )

    # Create ConcettoGiuridico node (from Brocardi "Ratio")
    concetto_id = "contratto_risoluzione_inadempimento"
    await falkor_client.query(
        """
        MERGE (concetto:ConcettoGiuridico {node_id: $concetto_id})
        ON CREATE SET
            concetto.denominazione = 'Risoluzione del contratto per inadempimento',
            concetto.definizione = 'Rimedio contrattuale che consente alla parte adempiente di sciogliere il vincolo contrattuale in caso di inadempimento dell altra parte.',
            concetto.categoria = 'diritto_civile_contratti',
            concetto.fonte = 'brocardi.it'
        """,
        {"concetto_id": concetto_id}
    )

    # Create 'disciplina' relation (§3.2.1)
    await falkor_client.query(
        """
        MATCH (norma:Norma {URN: $norma_urn})
        MATCH (concetto:ConcettoGiuridico {node_id: $concetto_id})
        MERGE (norma)-[r:disciplina]->(concetto)
        ON CREATE SET
            r.data_decorrenza = '1942-03-16',
            r.certezza = 'diretta',
            r.fonte_relazione = 'brocardi'
        """,
        {
            "norma_urn": art_urn,
            "concetto_id": concetto_id,
        }
    )

    log.info("ConcettoGiuridico node and relation created")

    # Verify
    results = await falkor_client.query(
        """
        MATCH (norma:Norma)-[r:disciplina]->(concetto:ConcettoGiuridico)
        WHERE norma.estremi = 'Art. 1453 c.c.'
        RETURN norma.estremi AS norma_estremi,
               concetto.denominazione AS concetto_nome,
               type(r) AS relation
        """
    )

    log.info("Query results", results=results)

    assert len(results) == 1
    assert results[0]["norma_estremi"] == "Art. 1453 c.c."
    assert "Risoluzione" in results[0]["concetto_nome"]
    assert results[0]["relation"] == "disciplina"


@pytest.mark.asyncio
async def test_batch_ingestion_art_1453_1456(falkor_client):
    """
    Full test: Ingest Art. 1453-1456 c.c. with complete structure.

    This is the first batch ingestion test with real URNs.
    """
    log.info("=== FIRST BATCH INGESTION: Art. 1453-1456 c.c. ===")

    articles = [
        {
            "numero": "1453",
            "titolo": "Risoluzione per inadempimento",
            "testo": "Nei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie le sue obbligazioni, l'altro può a sua scelta chiedere l'adempimento o la risoluzione del contratto, salvo, in ogni caso, il risarcimento del danno.",
            "concetto": "Risoluzione del contratto per inadempimento",
        },
        {
            "numero": "1454",
            "titolo": "Diffida ad adempiere",
            "testo": "Alla parte inadempiente l'altra può intimare per iscritto di adempiere in un congruo termine, con dichiarazione che, decorso inutilmente detto termine, il contratto s'intenderà senz'altro risolto. Il termine non può essere inferiore a quindici giorni, salvo diversa pattuizione delle parti o salvo che, per la natura del contratto o per altre circostanze, risulti congruo un termine minore.",
            "concetto": "Diffida ad adempiere",
        },
        {
            "numero": "1455",
            "titolo": "Importanza dell'inadempimento",
            "testo": "Il contratto non si può risolvere se l'inadempimento di una delle parti ha scarsa importanza, avuto riguardo all'interesse dell'altra.",
            "concetto": "Importanza dell'inadempimento",
        },
        {
            "numero": "1456",
            "titolo": "Clausola risolutiva espressa",
            "testo": "I contraenti possono convenire espressamente che il contratto si risolva nel caso che una determinata obbligazione non sia adempiuta secondo le modalità stabilite. In questo caso, la risoluzione si verifica di diritto quando la parte interessata dichiara all'altra che intende valersi della clausola risolutiva.",
            "concetto": "Clausola risolutiva espressa",
        },
    ]

    # Generate codice URN (root)
    codice_urn = urngenerator.generate_urn(
        act_type="codice civile",
        date="1942",
        act_number="262",
        article=None,
        urn_flag=True
    )

    # Create Codice root node
    await falkor_client.query(
        """
        MERGE (codice:Norma {URN: $codice_urn})
        ON CREATE SET
            codice.node_id = $codice_urn,
            codice.estremi = 'Codice Civile',
            codice.titolo = 'Codice Civile',
            codice.tipo_documento = 'codice',
            codice.data_pubblicazione = '1942-03-16',
            codice.stato = 'vigente'
        """,
        {"codice_urn": codice_urn}
    )

    log.info("Codice root created", urn=codice_urn)

    # Ingest each article
    for article in articles:
        log.info(f"Ingesting Art. {article['numero']}", titolo=article['titolo'])

        # Generate URN
        art_urn = urngenerator.generate_urn(
            act_type="codice civile",
            date="1942",
            act_number="262",
            article=article["numero"],
            urn_flag=True
        )

        # Create Article node
        await falkor_client.query(
            """
            MERGE (art:Norma {URN: $urn})
            ON CREATE SET
                art.node_id = $urn,
                art.estremi = $estremi,
                art.titolo = $titolo,
                art.tipo_documento = 'articolo',
                art.testo_vigente = $testo,
                art.data_pubblicazione = '1942-03-16',
                art.stato = 'vigente'
            """,
            {
                "urn": art_urn,
                "estremi": f"Art. {article['numero']} c.c.",
                "titolo": article["titolo"],
                "testo": article["testo"],
            }
        )

        # Create 'contiene' relation
        await falkor_client.query(
            """
            MATCH (codice:Norma {URN: $codice_urn})
            MATCH (art:Norma {URN: $art_urn})
            MERGE (codice)-[r:contiene]->(art)
            ON CREATE SET r.certezza = 'esplicita'
            """,
            {"codice_urn": codice_urn, "art_urn": art_urn}
        )

        # Create ConcettoGiuridico
        concetto_id = f"concetto_art_{article['numero']}"
        await falkor_client.query(
            """
            MERGE (concetto:ConcettoGiuridico {node_id: $concetto_id})
            ON CREATE SET
                concetto.denominazione = $denominazione,
                concetto.categoria = 'diritto_civile_contratti'
            """,
            {
                "concetto_id": concetto_id,
                "denominazione": article["concetto"],
            }
        )

        # Create 'disciplina' relation
        await falkor_client.query(
            """
            MATCH (norma:Norma {URN: $norma_urn})
            MATCH (concetto:ConcettoGiuridico {node_id: $concetto_id})
            MERGE (norma)-[r:disciplina]->(concetto)
            ON CREATE SET r.certezza = 'diretta'
            """,
            {"norma_urn": art_urn, "concetto_id": concetto_id}
        )

        log.info(f"✓ Art. {article['numero']} ingested", urn=art_urn)

    # Verify complete structure
    results = await falkor_client.query(
        """
        MATCH (codice:Norma)-[:contiene]->(art:Norma)-[:disciplina]->(concetto:ConcettoGiuridico)
        WHERE codice.tipo_documento = 'codice'
        AND art.tipo_documento = 'articolo'
        RETURN codice.estremi AS codice,
               art.estremi AS articolo,
               concetto.denominazione AS concetto
        ORDER BY art.estremi
        """
    )

    log.info(f"✓ Total articles ingested: {len(results)}")
    for result in results:
        log.info(
            "Ingested",
            articolo=result["articolo"],
            concetto=result["concetto"]
        )

    assert len(results) == 4, f"Expected 4 articles, got {len(results)}"
    assert results[0]["articolo"] == "Art. 1453 c.c."
    assert results[1]["articolo"] == "Art. 1454 c.c."
    assert results[2]["articolo"] == "Art. 1455 c.c."
    assert results[3]["articolo"] == "Art. 1456 c.c."

    log.info("=== FIRST BATCH INGESTION COMPLETE ===")


if __name__ == "__main__":
    # Run tests manually
    asyncio.run(test_urn_generation())
