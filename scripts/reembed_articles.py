#!/usr/bin/env python3
"""
Re-embed articoli con testo completo (article-level).

Questo script:
1. Cancella tutti i Norma da Qdrant
2. Cancella tutte le righe dalla Bridge Table
3. Legge tutti i 887 articoli da FalkorDB (source of truth)
4. Genera embedding con testo_vigente completo
5. Inserisce in Qdrant e Bridge Table

Risultato atteso: 887 embeddings (1 per articolo)
"""

import asyncio
import uuid
from datetime import datetime
from typing import List, Tuple

import asyncpg
from falkordb import FalkorDB
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, PointIdsList
from sentence_transformers import SentenceTransformer


# Config
FALKORDB_HOST = "localhost"
FALKORDB_PORT = 6380
FALKORDB_GRAPH = "merl_t_legal"

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "merl_t_chunks"

POSTGRES_DSN = "postgresql://dev:devpassword@localhost:5433/rlcf_dev"

EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
EMBEDDING_DIM = 1024
BATCH_SIZE = 32


async def main():
    print("=" * 70)
    print("RE-EMBEDDING ARTICLE-LEVEL")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")

    # 1. Connessioni
    print("\n1. Connessione ai servizi...")

    fb = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    graph = fb.select_graph(FALKORDB_GRAPH)
    print(f"   ✓ FalkorDB: {FALKORDB_GRAPH}")

    qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    print(f"   ✓ Qdrant: {QDRANT_COLLECTION}")

    pg = await asyncpg.connect(POSTGRES_DSN)
    print(f"   ✓ PostgreSQL: bridge_table")

    model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"   ✓ Embedding model: {EMBEDDING_MODEL}")

    # 2. Pulizia Qdrant Norma
    print("\n2. Pulizia Norma esistenti da Qdrant...")

    # Scroll e cancella tutti i Norma
    norma_ids = []
    offset = None
    while True:
        points, offset = qdrant.scroll(
            collection_name=QDRANT_COLLECTION,
            scroll_filter={"must": [{"key": "node_type", "match": {"value": "Norma"}}]},
            limit=1000,
            offset=offset,
            with_payload=False,
            with_vectors=False
        )
        norma_ids.extend([p.id for p in points])
        if offset is None:
            break

    if norma_ids:
        # Cancella in batch
        for i in range(0, len(norma_ids), 100):
            batch = norma_ids[i:i+100]
            qdrant.delete(
                collection_name=QDRANT_COLLECTION,
                points_selector=PointIdsList(points=batch)
            )
        print(f"   ✓ Eliminati {len(norma_ids)} punti Norma")
    else:
        print("   → Nessun Norma da eliminare")

    # 3. Pulizia Bridge Table
    print("\n3. Pulizia Bridge Table...")

    deleted = await pg.execute("DELETE FROM bridge_table")
    print(f"   ✓ {deleted}")

    # 4. Leggi articoli da FalkorDB
    print("\n4. Lettura articoli da FalkorDB...")

    result = graph.query("""
    MATCH (n:Norma)
    WHERE n.numero_articolo IS NOT NULL
    RETURN n.URN, n.numero_articolo, n.rubrica, n.testo_vigente
    ORDER BY toInteger(n.numero_articolo)
    """)

    articles: List[Tuple[str, str, str, str]] = []
    for row in result.result_set:
        urn, numero, rubrica, testo = row[0], row[1], row[2] or "", row[3] or ""
        if testo:  # Solo articoli con testo
            articles.append((urn, numero, rubrica, testo))

    print(f"   ✓ Trovati {len(articles)} articoli con testo")

    # 5. Genera embeddings
    print("\n5. Generazione embeddings...")

    # Prepara testi per embedding (formato E5)
    texts = []
    for urn, numero, rubrica, testo in articles:
        # Formato: "passage: <testo>"
        text = f"passage: Art. {numero}. {rubrica}\n{testo}"
        texts.append(text)

    # Genera in batch
    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i+BATCH_SIZE]
        embeddings = model.encode(batch, normalize_embeddings=True)
        all_embeddings.extend(embeddings)
        print(f"   Batch {i//BATCH_SIZE + 1}/{(len(texts)-1)//BATCH_SIZE + 1}: {len(batch)} articoli")

    print(f"   ✓ Generati {len(all_embeddings)} embeddings")

    # 6. Inserisci in Qdrant
    print("\n6. Inserimento in Qdrant...")

    points = []
    for i, (urn, numero, rubrica, testo) in enumerate(articles):
        point_id = str(uuid.uuid4())
        points.append(PointStruct(
            id=point_id,
            vector=all_embeddings[i].tolist(),
            payload={
                "urn": urn,
                "node_type": "Norma",
                "numero_articolo": numero,
                "rubrica": rubrica,
                "text_preview": testo[:500] if len(testo) > 500 else testo,
                "text_length": len(testo)
            }
        ))

    # Inserisci in batch
    for i in range(0, len(points), 100):
        batch = points[i:i+100]
        qdrant.upsert(collection_name=QDRANT_COLLECTION, points=batch)

    print(f"   ✓ Inseriti {len(points)} punti")

    # 7. Inserisci in Bridge Table
    print("\n7. Inserimento in Bridge Table...")

    # Prepara batch insert
    values = []
    for i, (urn, numero, rubrica, testo) in enumerate(articles):
        chunk_id = points[i].id
        chunk_text = texts[i][:1000]  # Testo usato per embedding (troncato per storage)
        values.append((chunk_id, urn, chunk_text, "Norma"))

    await pg.executemany(
        """
        INSERT INTO bridge_table (chunk_id, graph_node_urn, chunk_text, node_type)
        VALUES ($1, $2, $3, $4)
        """,
        values
    )

    print(f"   ✓ Inserite {len(values)} righe")

    # 8. Verifica finale
    print("\n" + "=" * 70)
    print("VERIFICA FINALE")
    print("=" * 70)

    # Qdrant
    norma_count = qdrant.count(
        collection_name=QDRANT_COLLECTION,
        count_filter={"must": [{"key": "node_type", "match": {"value": "Norma"}}]}
    ).count

    massime_count = qdrant.count(
        collection_name=QDRANT_COLLECTION,
        count_filter={"must": [{"key": "node_type", "match": {"value": "AttoGiudiziario"}}]}
    ).count

    # Bridge Table
    bridge_count = await pg.fetchval("SELECT COUNT(*) FROM bridge_table")

    print(f"\nQdrant:")
    print(f"  - Norma: {norma_count}")
    print(f"  - AttoGiudiziario: {massime_count}")
    print(f"  - Totale: {norma_count + massime_count}")

    print(f"\nBridge Table: {bridge_count}")

    # Art. 1284 check
    art_1284, _ = qdrant.scroll(
        collection_name=QDRANT_COLLECTION,
        scroll_filter={
            "must": [
                {"key": "node_type", "match": {"value": "Norma"}},
                {"key": "urn", "match": {"value": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~art1284"}}
            ]
        },
        limit=1,
        with_payload=True,
        with_vectors=False
    )

    if art_1284:
        print(f"\nArt. 1284 check:")
        print(f"  - ID: {art_1284[0].id}")
        print(f"  - Text length: {art_1284[0].payload.get('text_length', 'N/A')} chars")
        print(f"  - Preview: {art_1284[0].payload.get('text_preview', 'N/A')[:100]}...")

    await pg.close()

    print("\n" + "=" * 70)
    print("✅ RE-EMBEDDING COMPLETATO!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
