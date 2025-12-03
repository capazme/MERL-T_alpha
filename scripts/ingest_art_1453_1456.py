#!/usr/bin/env python3
"""
Ingest Art. 1453-1456 c.c. into FalkorDB
========================================

Standalone script to populate the database with first batch of articles.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage.falkordb.client import FalkorDBClient, FalkorDBConfig
from backend.external_sources.visualex.tools import urngenerator

print("🚀 Starting ingestion of Art. 1453-1456 c.c.")

async def main():
    # Initialize FalkorDB
    config = FalkorDBConfig(
        host="localhost",
        port=6380,
        graph_name="merl_t_legal"
    )
    client = FalkorDBClient(config)
    await client.connect()
    print("✓ Connected to FalkorDB")

    # Articles data
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

    # Generate codice URN
    codice_urn = urngenerator.generate_urn(
        act_type="codice civile",
        date="1942",
        act_number="262",
        article=None,
        urn_flag=True
    )

    # Create Codice root
    await client.query(
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
    print(f"✓ Codice Civile root created: {codice_urn[:60]}...")

    # Ingest each article
    for article in articles:
        print(f"  Ingesting Art. {article['numero']}...")

        # Generate URN
        art_urn = urngenerator.generate_urn(
            act_type="codice civile",
            date="1942",
            act_number="262",
            article=article["numero"],
            urn_flag=True
        )

        # Create Article node
        await client.query(
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
        await client.query(
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
        await client.query(
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
        await client.query(
            """
            MATCH (norma:Norma {URN: $norma_urn})
            MATCH (concetto:ConcettoGiuridico {node_id: $concetto_id})
            MERGE (norma)-[r:disciplina]->(concetto)
            ON CREATE SET r.certezza = 'diretta'
            """,
            {"norma_urn": art_urn, "concetto_id": concetto_id}
        )

        print(f"    ✓ Art. {article['numero']} - {article['titolo']}")

    await client.close()

    print("\n✅ Ingestion complete!")
    print("\nVerify with:")
    print("  redis-cli -p 6380 GRAPH.QUERY merl_t_legal \"MATCH (n) RETURN count(n)\"")
    print("  redis-cli -p 6380 GRAPH.QUERY merl_t_legal \"MATCH (c:Norma)-[:contiene]->(a:Norma) RETURN c.estremi, a.estremi LIMIT 5\"")

if __name__ == "__main__":
    asyncio.run(main())
