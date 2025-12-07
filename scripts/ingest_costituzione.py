#!/usr/bin/env python3
"""
EXP-004: Ingestion Costituzione Italiana

Script che utilizza il BrocardiScraper esistente per l'ingestion
della Costituzione italiana.
"""

import asyncio
import sys
sys.path.insert(0, '/Users/gpuzio/Desktop/CODE/MERL-T_alpha')

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import structlog

# Riutilizzo BrocardiScraper esistente
from merlt.external_sources.visualex.scrapers.brocardi_scraper import BrocardiScraper
from merlt.external_sources.visualex.tools.norma import NormaVisitata, Norma

log = structlog.get_logger()

# Struttura Costituzione su Brocardi (139 articoli)
CONSTITUTION_STRUCTURE = {
    "principi-fondamentali": list(range(1, 13)),
    "parte-i/titolo-i": list(range(13, 29)),
    "parte-i/titolo-ii": list(range(29, 35)),
    "parte-i/titolo-iii": list(range(35, 48)),
    "parte-i/titolo-iv": list(range(48, 55)),
    "parte-ii/titolo-i/sezione-i": list(range(55, 70)),
    "parte-ii/titolo-i/sezione-ii": list(range(70, 83)),
    "parte-ii/titolo-ii": list(range(83, 92)),
    "parte-ii/titolo-iii/sezione-i": list(range(92, 97)),
    "parte-ii/titolo-iii/sezione-ii": list(range(97, 99)),
    "parte-ii/titolo-iii/sezione-iii": list(range(99, 101)),
    "parte-ii/titolo-iv/sezione-i": list(range(101, 111)),
    "parte-ii/titolo-iv/sezione-ii": list(range(111, 114)),
    "parte-ii/titolo-v": list(range(114, 134)),
    "parte-ii/titolo-vi": list(range(134, 140)),
}


@dataclass
class ArticoloCostituzione:
    """Rappresenta un articolo della Costituzione."""
    numero: int
    dispositivo: str = ""
    spiegazione: str = ""
    ratio: str = ""
    massime: List[Dict[str, Any]] = None
    brocardi_url: str = ""
    position: str = ""

    def __post_init__(self):
        if self.massime is None:
            self.massime = []

    @property
    def urn(self) -> str:
        return f"urn:nir:stato:costituzione~art{self.numero}"


def get_all_article_numbers() -> List[int]:
    """Restituisce tutti i numeri di articolo."""
    all_nums = []
    for articoli in CONSTITUTION_STRUCTURE.values():
        all_nums.extend(articoli)
    return sorted(all_nums)


async def scrape_article(scraper: BrocardiScraper, art_num: int) -> Optional[ArticoloCostituzione]:
    """Scarica un articolo usando BrocardiScraper."""
    try:
        # Crea NormaVisitata per la Costituzione
        norma = Norma(tipo_atto="costituzione")  # tipo_atto, non tipo_atto_str
        norma_visitata = NormaVisitata(norma=norma, numero_articolo=str(art_num))

        # Usa BrocardiScraper per ottenere info
        position, info, url = await scraper.get_info(norma_visitata)

        if not url:
            log.warning(f"Art. {art_num}: URL non trovato")
            return None

        articolo = ArticoloCostituzione(
            numero=art_num,
            brocardi_url=url,
            position=position or ""
        )

        # Estrai contenuti
        if 'Spiegazione' in info:
            articolo.spiegazione = info['Spiegazione']

        if 'Ratio' in info:
            articolo.ratio = info['Ratio']

        if 'Massime' in info:
            articolo.massime = info['Massime']

        # Per il dispositivo devo fare fetch separato (non incluso in get_info)
        # Lo recupereremo direttamente dalla pagina

        return articolo

    except Exception as e:
        log.error(f"Art. {art_num}: Errore - {e}")
        return None


async def fetch_dispositivo(scraper: BrocardiScraper, articolo: ArticoloCostituzione) -> str:
    """Recupera il dispositivo di un articolo."""
    import aiohttp
    from bs4 import BeautifulSoup

    if not articolo.brocardi_url:
        return ""

    try:
        from merlt.external_sources.visualex.tools.http_client import http_client
        session = await http_client.get_session()

        async with session.get(articolo.brocardi_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return ""
            html = await resp.text()

        soup = BeautifulSoup(html, 'html.parser')
        dispositivo_div = soup.find('div', class_='corpoDelTesto dispositivo')
        if dispositivo_div:
            import re
            text = dispositivo_div.get_text()
            return re.sub(r'\s+', ' ', text).strip()

    except Exception as e:
        log.warning(f"Art. {articolo.numero}: Errore dispositivo - {e}")

    return ""


async def scrape_constitution() -> List[ArticoloCostituzione]:
    """Scarica tutti gli articoli della Costituzione."""
    scraper = BrocardiScraper()
    articoli = []
    all_nums = get_all_article_numbers()

    print(f"Scaricando {len(all_nums)} articoli...")

    # Batch processing
    batch_size = 5
    for i in range(0, len(all_nums), batch_size):
        batch = all_nums[i:i+batch_size]
        tasks = [scrape_article(scraper, num) for num in batch]
        results = await asyncio.gather(*tasks)

        for result in results:
            if result:
                # Recupera dispositivo
                result.dispositivo = await fetch_dispositivo(scraper, result)
                articoli.append(result)

        ok_count = len([r for r in results if r])
        log.info(f"Batch {i//batch_size + 1}: {ok_count}/{len(batch)} articoli OK")

        if i + batch_size < len(all_nums):
            await asyncio.sleep(1)  # Rate limiting

    return sorted(articoli, key=lambda a: a.numero)


async def store_to_falkordb(articoli: List[ArticoloCostituzione]):
    """Salva gli articoli in FalkorDB."""
    from falkordb import FalkorDB

    db = FalkorDB(host='localhost', port=6380)  # FalkorDB è su 6380, Redis su 6379
    graph = db.select_graph('merl_t_legal')  # Stesso grafo del Libro IV

    stats = {'norma': 0, 'dottrina': 0, 'massime': 0}

    for art in articoli:
        # Crea nodo Norma
        graph.query("""
        MERGE (n:Norma {urn: $urn})
        SET n.tipo_atto = 'Costituzione',
            n.numero_articolo = $numero,
            n.testo_vigente = $dispositivo,
            n.data_versione = date('1948-01-01'),
            n.url_brocardi = $url,
            n.posizione_struttura = $position
        RETURN n
        """, {
            'urn': art.urn,
            'numero': str(art.numero),
            'dispositivo': art.dispositivo,
            'url': art.brocardi_url,
            'position': art.position
        })
        stats['norma'] += 1

        # Dottrina (spiegazione)
        if art.spiegazione:
            dottrina_urn = f"{art.urn}~dottrina~spiegazione"
            graph.query("""
            MERGE (d:Dottrina {urn: $urn})
            SET d.tipo = 'spiegazione', d.contenuto = $contenuto, d.fonte = 'Brocardi'
            WITH d
            MATCH (n:Norma {urn: $art_urn})
            MERGE (d)-[:commenta]->(n)
            """, {'urn': dottrina_urn, 'contenuto': art.spiegazione, 'art_urn': art.urn})
            stats['dottrina'] += 1

        # Massime
        for idx, massima in enumerate(art.massime):
            if massima.get('numero') and massima.get('anno'):
                massima_urn = f"urn:nir:it:cassazione:sentenza:{massima['anno']};{massima['numero']}"
            else:
                massima_urn = f"{art.urn}~massima~{idx}"

            graph.query("""
            MERGE (m:AttoGiudiziario {urn: $urn})
            SET m.autorita = $autorita, m.numero = $numero, m.anno = $anno, m.massima = $massima
            WITH m
            MATCH (n:Norma {urn: $art_urn})
            MERGE (m)-[:interpreta]->(n)
            """, {
                'urn': massima_urn,
                'autorita': massima.get('autorita', ''),
                'numero': massima.get('numero', ''),
                'anno': massima.get('anno', ''),
                'massima': massima.get('massima', ''),
                'art_urn': art.urn
            })
            stats['massime'] += 1

    # Crea gerarchia
    graph.query("""
    MERGE (c:Norma {urn: 'urn:nir:stato:costituzione'})
    SET c.tipo_atto = 'Costituzione',
        c.rubrica = 'Costituzione della Repubblica Italiana',
        c.data_versione = date('1948-01-01')
    """)

    for art in articoli:
        graph.query("""
        MATCH (root:Norma {urn: 'urn:nir:stato:costituzione'})
        MATCH (art:Norma {urn: $art_urn})
        MERGE (root)-[:contiene]->(art)
        """, {'art_urn': art.urn})

    return stats


async def generate_embeddings(articoli: List[ArticoloCostituzione]):
    """Genera embeddings per articoli e massime."""
    import asyncpg
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct
    import uuid

    from merlt.orchestration.services.embedding_service import EmbeddingService

    embedding_service = EmbeddingService()
    qdrant = QdrantClient(host="localhost", port=6333)
    pg = await asyncpg.connect("postgresql://dev:devpassword@localhost:5433/rlcf_dev")

    # Embeddings articoli
    log.info("Generando embeddings articoli...")
    article_points = []
    bridge_values = []

    for art in articoli:
        if not art.dispositivo:
            continue

        text = f"Art. {art.numero} Costituzione\n\n{art.dispositivo}"
        if art.spiegazione:
            text += f"\n\nSpiegazione: {art.spiegazione[:1000]}"

        embedding = await embedding_service.get_embedding(text)
        point_id = str(uuid.uuid4())

        article_points.append(PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "urn": art.urn,
                "tipo": "Norma",
                "text_preview": art.dispositivo[:500],
                "numero_articolo": str(art.numero),
                "fonte": "Costituzione"
            }
        ))
        bridge_values.append((point_id, art.urn, text[:2000], "Norma"))

    if article_points:
        qdrant.upsert(collection_name="merl_t_chunks", points=article_points)
        log.info(f"Inseriti {len(article_points)} embeddings articoli")

    # Embeddings massime
    log.info("Generando embeddings massime...")
    massima_points = []

    for art in articoli:
        for idx, massima in enumerate(art.massime):
            if not massima.get('massima'):
                continue

            if massima.get('numero') and massima.get('anno'):
                massima_urn = f"urn:nir:it:cassazione:sentenza:{massima['anno']};{massima['numero']}"
            else:
                massima_urn = f"{art.urn}~massima~{idx}"

            text = massima['massima']
            embedding = await embedding_service.get_embedding(text)
            point_id = str(uuid.uuid4())

            massima_points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "urn": massima_urn,
                    "tipo": "AttoGiudiziario",
                    "autorita": massima.get('autorita', ''),
                    "text_preview": text[:500],
                    "articolo_riferimento": art.urn
                }
            ))

    if massima_points:
        qdrant.upsert(collection_name="merl_t_chunks", points=massima_points)
        log.info(f"Inseriti {len(massima_points)} embeddings massime")

    # Bridge table
    if bridge_values:
        await pg.executemany("""
            INSERT INTO bridge_table (chunk_id, graph_node_urn, chunk_text, node_type)
            VALUES ($1, $2, $3, $4) ON CONFLICT (chunk_id) DO NOTHING
        """, bridge_values)

    await pg.close()
    return {'articoli': len(article_points), 'massime': len(massima_points)}


async def main():
    """Main entry point."""
    print("=" * 60)
    print("EXP-004: Ingestion Costituzione Italiana")
    print("Utilizzando BrocardiScraper esistente")
    print("=" * 60)

    # Fase 1: Scraping
    print("\n[1/3] Scraping articoli...")
    articoli = await scrape_constitution()
    print(f"   Articoli scaricati: {len(articoli)}/139")

    total_massime = sum(len(a.massime) for a in articoli)
    total_spiegazioni = sum(1 for a in articoli if a.spiegazione)
    print(f"   Massime trovate: {total_massime}")
    print(f"   Spiegazioni trovate: {total_spiegazioni}")

    if len(articoli) == 0:
        print("\nNessun articolo scaricato. Verificare connettività.")
        return

    # Fase 2: Store to FalkorDB
    print("\n[2/3] Salvataggio in FalkorDB...")
    try:
        stats = await store_to_falkordb(articoli)
        print(f"   Nodi Norma: {stats['norma']}")
        print(f"   Nodi Dottrina: {stats['dottrina']}")
        print(f"   Nodi Massime: {stats['massime']}")
    except Exception as e:
        print(f"   ERRORE FalkorDB: {e}")
        print("   Verificare che FalkorDB sia attivo (non solo Redis)")
        return

    # Fase 3: Embeddings
    print("\n[3/3] Generazione embeddings...")
    try:
        emb_stats = await generate_embeddings(articoli)
        print(f"   Embeddings articoli: {emb_stats['articoli']}")
        print(f"   Embeddings massime: {emb_stats['massime']}")
    except Exception as e:
        print(f"   ERRORE Embeddings: {e}")
        return

    print("\n" + "=" * 60)
    print("INGESTION COMPLETATA")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
