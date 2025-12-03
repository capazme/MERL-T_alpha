"""
Ingestion Pipeline v2 - Comma-Level Chunking
=============================================

Extended pipeline that integrates:
- CommaParser: Parse article_text into structured components
- StructuralChunker: Create comma-level chunks with URN extensions
- Bridge Table: Prepare mappings for chunk → graph node linking

IMPORTANT: This module USES but does NOT modify:
- urngenerator.py (used by agent in real-time)
- visualex_client.py (used by agent in real-time)
- visualex_ingestion.py (existing pipeline still works)

Schema: docs/08-iteration/SCHEMA_DEFINITIVO_API_GRAFO.md

Usage:
    pipeline = IngestionPipelineV2(falkordb_client, bridge_table)
    results = await pipeline.ingest_article(visualex_article)
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from .comma_parser import CommaParser, ArticleStructure, parse_article
from .structural_chunker import StructuralChunker, Chunk, chunk_article
from .visualex_ingestion import VisualexArticle, NormaMetadata

logger = logging.getLogger(__name__)


@dataclass
class BridgeMapping:
    """
    Prepared mapping for Bridge Table insertion.

    Attributes:
        chunk_id: UUID of the chunk (for Qdrant)
        graph_node_urn: URN of the linked graph node
        mapping_type: Type of mapping (PRIMARY, HIERARCHIC, CONCEPT, REFERENCE)
        confidence: Confidence score [0-1]
        metadata: Additional context
    """
    chunk_id: UUID
    graph_node_urn: str
    mapping_type: str  # PRIMARY, HIERARCHIC, CONCEPT, REFERENCE
    confidence: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class IngestionResult:
    """
    Result of ingesting a single article.

    Attributes:
        article_urn: URN of the ingested article
        article_url: External URL (for frontend linking)
        chunks: List of created chunks
        bridge_mappings: Prepared Bridge Table mappings
        nodes_created: List of graph nodes created
        relations_created: List of graph relations created
        brocardi_enriched: Whether Brocardi data was available
    """
    article_urn: str
    article_url: str
    chunks: List[Chunk]
    bridge_mappings: List[BridgeMapping]
    nodes_created: List[str]
    relations_created: List[str]
    brocardi_enriched: bool = False

    def summary(self) -> Dict[str, Any]:
        """Return summary for logging."""
        return {
            "article_urn": self.article_urn,
            "chunks": len(self.chunks),
            "bridge_mappings": len(self.bridge_mappings),
            "nodes": len(self.nodes_created),
            "relations": len(self.relations_created),
            "brocardi": self.brocardi_enriched,
        }


class IngestionPipelineV2:
    """
    Extended ingestion pipeline with comma-level chunking.

    This pipeline:
    1. Parses article_text into commas (CommaParser)
    2. Creates chunks per comma (StructuralChunker)
    3. Creates graph nodes with full schema properties
    4. Prepares Bridge Table mappings

    Does NOT handle:
    - Embedding generation (separate batch process)
    - Qdrant insertion (separate batch process)
    - Bridge Table insertion (caller's responsibility)

    Usage:
        pipeline = IngestionPipelineV2(falkordb_client)
        result = await pipeline.ingest_article(article)

        # Caller handles bridge insertions
        for mapping in result.bridge_mappings:
            await bridge_table.add_mapping(...)
    """

    def __init__(
        self,
        falkordb_client=None,
        comma_parser: Optional[CommaParser] = None,
        chunker: Optional[StructuralChunker] = None,
    ):
        """
        Initialize pipeline.

        Args:
            falkordb_client: FalkorDB client for graph operations
            comma_parser: Optional custom parser (default: CommaParser())
            chunker: Optional custom chunker (default: StructuralChunker())
        """
        self.falkordb = falkordb_client
        self.parser = comma_parser or CommaParser()
        self.chunker = chunker or StructuralChunker()

        logger.info("IngestionPipelineV2 initialized")

    async def ingest_article(
        self,
        article: VisualexArticle,
        create_graph_nodes: bool = True,
    ) -> IngestionResult:
        """
        Ingest a single article with comma-level chunking.

        Args:
            article: VisualexArticle from API
            create_graph_nodes: Whether to create graph nodes (default True)

        Returns:
            IngestionResult with chunks, mappings, and graph info
        """
        meta = article.metadata

        # Get URNs from existing urngenerator (DO NOT MODIFY urngenerator!)
        article_urn = meta.to_urn()
        article_url = article.url  # Already correct from API
        codice_urn = meta.to_codice_urn()

        logger.info(f"Ingesting article: {article_urn}")

        # Step 1: Parse article text into commas
        article_structure = self.parser.parse(article.article_text)

        # Step 2: Get Brocardi position for context
        brocardi_position = None
        if article.brocardi_info:
            brocardi_position = article.brocardi_info.get("Position")

        # Step 3: Create chunks (one per comma)
        chunks = self.chunker.chunk_article(
            article_structure=article_structure,
            article_urn=article_urn,
            article_url=article_url,
            brocardi_position=brocardi_position,
        )

        # Step 4: Prepare bridge mappings
        bridge_mappings = self._prepare_bridge_mappings(
            chunks=chunks,
            article_urn=article_urn,
            codice_urn=codice_urn,
            brocardi_position=brocardi_position,
        )

        # Initialize result
        result = IngestionResult(
            article_urn=article_urn,
            article_url=article_url,
            chunks=chunks,
            bridge_mappings=bridge_mappings,
            nodes_created=[],
            relations_created=[],
            brocardi_enriched=bool(article.brocardi_info),
        )

        # Step 5: Create graph nodes (if enabled and client available)
        if create_graph_nodes and self.falkordb:
            await self._create_graph_structure(
                article=article,
                article_structure=article_structure,
                result=result,
            )

        logger.info(f"Ingestion complete: {result.summary()}")
        return result

    def _prepare_bridge_mappings(
        self,
        chunks: List[Chunk],
        article_urn: str,
        codice_urn: str,
        brocardi_position: Optional[str],
    ) -> List[BridgeMapping]:
        """
        Prepare Bridge Table mappings for all chunks.

        Mapping types:
        - PRIMARY: chunk → parent article (confidence 1.0)
        - HIERARCHIC: chunk → libro/titolo (confidence 0.95)
        - CONCEPT: chunk → extracted concepts (confidence varies)
        - REFERENCE: chunk → referenced articles (confidence 0.75)
        """
        mappings = []

        # Extract libro/titolo URNs from position if available
        libro_urn, titolo_urn = self._extract_hierarchy_urns(
            codice_urn, brocardi_position
        )

        for chunk in chunks:
            # PRIMARY: chunk → article (always 1.0)
            mappings.append(BridgeMapping(
                chunk_id=chunk.chunk_id,
                graph_node_urn=article_urn,
                mapping_type="PRIMARY",
                confidence=1.0,
                metadata={"comma_numero": chunk.metadata.comma_numero},
            ))

            # HIERARCHIC: chunk → libro (if available)
            if libro_urn:
                mappings.append(BridgeMapping(
                    chunk_id=chunk.chunk_id,
                    graph_node_urn=libro_urn,
                    mapping_type="HIERARCHIC",
                    confidence=0.95,
                ))

            # HIERARCHIC: chunk → titolo (if available)
            if titolo_urn:
                mappings.append(BridgeMapping(
                    chunk_id=chunk.chunk_id,
                    graph_node_urn=titolo_urn,
                    mapping_type="HIERARCHIC",
                    confidence=0.95,
                ))

        return mappings

    def _extract_hierarchy_urns(
        self,
        codice_urn: str,
        brocardi_position: Optional[str],
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract libro and titolo URNs from Brocardi position.

        Example:
            Position: "Libro IV - Delle obbligazioni, Titolo II - ..."
            codice_urn: "https://...;262:2"

            Returns:
                libro_urn: "https://...;262:2~libro4"
                titolo_urn: "https://...;262:2~libro4~tit2"
        """
        if not brocardi_position:
            return None, None

        libro_urn = None
        titolo_urn = None

        # Extract libro number
        libro_match = re.search(r'Libro\s+([IVX]+)', brocardi_position, re.IGNORECASE)
        if libro_match:
            libro_num = self._roman_to_arabic(libro_match.group(1))
            libro_urn = f"{codice_urn}~libro{libro_num}"

            # Extract titolo number
            titolo_match = re.search(r'Titolo\s+([IVX]+)', brocardi_position, re.IGNORECASE)
            if titolo_match:
                titolo_num = self._roman_to_arabic(titolo_match.group(1))
                titolo_urn = f"{libro_urn}~tit{titolo_num}"

        return libro_urn, titolo_urn

    def _roman_to_arabic(self, roman: str) -> int:
        """Convert Roman numeral to Arabic number."""
        roman_values = {
            'I': 1, 'V': 5, 'X': 10, 'L': 50,
            'C': 100, 'D': 500, 'M': 1000
        }
        result = 0
        prev = 0
        for char in reversed(roman.upper()):
            curr = roman_values.get(char, 0)
            if curr < prev:
                result -= curr
            else:
                result += curr
            prev = curr
        return result

    async def _create_graph_structure(
        self,
        article: VisualexArticle,
        article_structure: ArticleStructure,
        result: IngestionResult,
    ) -> None:
        """
        Create graph nodes and relations per schema definitivo.

        Schema: docs/08-iteration/SCHEMA_DEFINITIVO_API_GRAFO.md
        """
        meta = article.metadata
        article_urn = result.article_urn
        codice_urn = meta.to_codice_urn()

        # Create Norma (codice) - root document
        await self._create_norma_codice(meta, codice_urn, result)

        # Create hierarchy nodes (libro, titolo) if Brocardi available
        if article.brocardi_info:
            await self._create_hierarchy_nodes(
                codice_urn=codice_urn,
                brocardi_position=article.brocardi_info.get("Position"),
                result=result,
            )

        # Create Norma (articolo) with full properties
        await self._create_norma_articolo(
            article=article,
            article_structure=article_structure,
            result=result,
        )

        # Create Brocardi enrichment nodes
        if article.brocardi_info:
            await self._create_brocardi_enrichment(
                article=article,
                article_urn=article_urn,
                result=result,
            )

    async def _create_norma_codice(
        self,
        meta: NormaMetadata,
        codice_urn: str,
        result: IngestionResult,
    ) -> None:
        """Create Norma node for codice (root document)."""
        await self.falkordb.query(
            """
            MERGE (codice:Norma {URN: $urn})
            ON CREATE SET
                codice.node_id = $urn,
                codice.url = $url,
                codice.tipo_documento = 'codice',
                codice.titolo = $titolo,
                codice.autorita_emanante = $autorita,
                codice.data_pubblicazione = $data,
                codice.vigenza = 'vigente',
                codice.efficacia = 'permanente',
                codice.ambito_territoriale = 'nazionale',
                codice.fonte = 'VisualexAPI',
                codice.created_at = datetime()
            """,
            {
                "urn": codice_urn,
                "url": codice_urn,  # Codice URL = URN
                "titolo": meta.tipo_atto.title(),
                "autorita": "Regio Decreto" if "regio" in codice_urn.lower() else "Parlamento",
                "data": meta.data,
            }
        )
        result.nodes_created.append(f"Norma(codice):{codice_urn}")

    async def _create_hierarchy_nodes(
        self,
        codice_urn: str,
        brocardi_position: Optional[str],
        result: IngestionResult,
    ) -> None:
        """Create Norma nodes for libro and titolo."""
        if not brocardi_position:
            return

        libro_urn, titolo_urn = self._extract_hierarchy_urns(codice_urn, brocardi_position)

        # Extract titles from position
        libro_titolo = self._extract_libro_titolo(brocardi_position)
        titolo_titolo = self._extract_titolo_titolo(brocardi_position)

        if libro_urn:
            await self.falkordb.query(
                """
                MERGE (libro:Norma {URN: $urn})
                ON CREATE SET
                    libro.node_id = $urn,
                    libro.tipo_documento = 'libro',
                    libro.titolo = $titolo,
                    libro.vigenza = 'vigente',
                    libro.fonte = 'Brocardi',
                    libro.created_at = datetime()
                """,
                {"urn": libro_urn, "titolo": libro_titolo or ""}
            )
            result.nodes_created.append(f"Norma(libro):{libro_urn}")

            # Relation: codice -[contiene]-> libro
            await self.falkordb.query(
                """
                MATCH (codice:Norma {URN: $codice_urn})
                MATCH (libro:Norma {URN: $libro_urn})
                MERGE (codice)-[r:contiene]->(libro)
                ON CREATE SET r.certezza = 1.0, r.tipo = 'esplicita'
                """,
                {"codice_urn": codice_urn, "libro_urn": libro_urn}
            )
            result.relations_created.append(f"contiene:{codice_urn}->{libro_urn}")

        if titolo_urn and libro_urn:
            await self.falkordb.query(
                """
                MERGE (titolo:Norma {URN: $urn})
                ON CREATE SET
                    titolo.node_id = $urn,
                    titolo.tipo_documento = 'titolo',
                    titolo.titolo = $titolo,
                    titolo.vigenza = 'vigente',
                    titolo.fonte = 'Brocardi',
                    titolo.created_at = datetime()
                """,
                {"urn": titolo_urn, "titolo": titolo_titolo or ""}
            )
            result.nodes_created.append(f"Norma(titolo):{titolo_urn}")

            # Relation: libro -[contiene]-> titolo
            await self.falkordb.query(
                """
                MATCH (libro:Norma {URN: $libro_urn})
                MATCH (titolo:Norma {URN: $titolo_urn})
                MERGE (libro)-[r:contiene]->(titolo)
                ON CREATE SET r.certezza = 1.0, r.tipo = 'esplicita'
                """,
                {"libro_urn": libro_urn, "titolo_urn": titolo_urn}
            )
            result.relations_created.append(f"contiene:{libro_urn}->{titolo_urn}")

    def _extract_libro_titolo(self, position: str) -> Optional[str]:
        """Extract libro title from Brocardi position."""
        match = re.search(r'Libro\s+[IVX]+\s*[-–]\s*([^,]+)', position, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_titolo_titolo(self, position: str) -> Optional[str]:
        """Extract titolo title from Brocardi position."""
        match = re.search(r'Titolo\s+[IVX]+\s*[-–]\s*([^,]+)', position, re.IGNORECASE)
        return match.group(1).strip() if match else None

    async def _create_norma_articolo(
        self,
        article: VisualexArticle,
        article_structure: ArticleStructure,
        result: IngestionResult,
    ) -> None:
        """Create Norma node for articolo with full 21 properties."""
        meta = article.metadata

        await self.falkordb.query(
            """
            MERGE (art:Norma {URN: $urn})
            ON CREATE SET
                art.node_id = $urn,
                art.url = $url,
                art.tipo_documento = 'articolo',
                art.estremi = $estremi,
                art.numero_articolo = $numero_articolo,
                art.rubrica = $rubrica,
                art.testo_vigente = $testo,
                art.titolo = $estremi,
                art.fonte = 'VisualexAPI',
                art.autorita_emanante = $autorita,
                art.data_pubblicazione = $data,
                art.vigenza = 'vigente',
                art.stato = 'vigente',
                art.efficacia = 'permanente',
                art.ambito_territoriale = 'nazionale',
                art.created_at = datetime(),
                art.updated_at = datetime()
            """,
            {
                "urn": result.article_urn,
                "url": result.article_url,
                "estremi": meta.to_estremi(),
                "numero_articolo": article_structure.numero_articolo,
                "rubrica": article_structure.rubrica or "",
                "testo": article.article_text,
                "autorita": "Regio Decreto" if "regio" in result.article_urn.lower() else "Parlamento",
                "data": meta.data,
            }
        )
        result.nodes_created.append(f"Norma(articolo):{result.article_urn}")

        # Relation: titolo/libro/codice -[contiene]-> articolo
        # Find closest parent (titolo > libro > codice)
        codice_urn = meta.to_codice_urn()
        libro_urn, titolo_urn = self._extract_hierarchy_urns(
            codice_urn,
            article.brocardi_info.get("Position") if article.brocardi_info else None
        )

        parent_urn = titolo_urn or libro_urn or codice_urn
        await self.falkordb.query(
            """
            MATCH (parent:Norma {URN: $parent_urn})
            MATCH (art:Norma {URN: $art_urn})
            MERGE (parent)-[r:contiene]->(art)
            ON CREATE SET r.certezza = 1.0, r.tipo = 'esplicita'
            """,
            {"parent_urn": parent_urn, "art_urn": result.article_urn}
        )
        result.relations_created.append(f"contiene:{parent_urn}->{result.article_urn}")

    async def _create_brocardi_enrichment(
        self,
        article: VisualexArticle,
        article_urn: str,
        result: IngestionResult,
    ) -> None:
        """Create Dottrina and AttoGiudiziario nodes from Brocardi."""
        brocardi = article.brocardi_info
        estremi = article.metadata.to_estremi()

        # Ratio → Dottrina (tipo: ratio)
        if brocardi.get("Ratio"):
            dottrina_id = f"dottrina_brocardi_{article_urn.split('~')[-1]}_ratio"
            await self.falkordb.query(
                """
                MERGE (d:Dottrina {node_id: $id})
                ON CREATE SET
                    d.titolo = $titolo,
                    d.descrizione = $descrizione,
                    d.tipo_dottrina = 'ratio',
                    d.fonte = 'Brocardi.it',
                    d.autore = 'Brocardi.it',
                    d.confidence = 0.9,
                    d.created_at = datetime()
                """,
                {
                    "id": dottrina_id,
                    "titolo": f"Ratio {estremi}",
                    "descrizione": brocardi["Ratio"],
                }
            )
            result.nodes_created.append(f"Dottrina:{dottrina_id}")

            # Relation: Dottrina -[commenta]-> Norma
            await self.falkordb.query(
                """
                MATCH (d:Dottrina {node_id: $d_id})
                MATCH (art:Norma {URN: $art_urn})
                MERGE (d)-[r:commenta]->(art)
                ON CREATE SET r.certezza = 0.9, r.tipo = 'esplicita', r.fonte = 'Brocardi.it'
                """,
                {"d_id": dottrina_id, "art_urn": article_urn}
            )
            result.relations_created.append(f"commenta:{dottrina_id}->{article_urn}")

        # Spiegazione → Dottrina (tipo: spiegazione)
        if brocardi.get("Spiegazione"):
            dottrina_id = f"dottrina_brocardi_{article_urn.split('~')[-1]}_spiegazione"
            await self.falkordb.query(
                """
                MERGE (d:Dottrina {node_id: $id})
                ON CREATE SET
                    d.titolo = $titolo,
                    d.descrizione = $descrizione,
                    d.tipo_dottrina = 'spiegazione',
                    d.fonte = 'Brocardi.it',
                    d.autore = 'Brocardi.it',
                    d.confidence = 0.9,
                    d.created_at = datetime()
                """,
                {
                    "id": dottrina_id,
                    "titolo": f"Spiegazione {estremi}",
                    "descrizione": brocardi["Spiegazione"],
                }
            )
            result.nodes_created.append(f"Dottrina:{dottrina_id}")

            await self.falkordb.query(
                """
                MATCH (d:Dottrina {node_id: $d_id})
                MATCH (art:Norma {URN: $art_urn})
                MERGE (d)-[r:commenta]->(art)
                ON CREATE SET r.certezza = 0.9, r.tipo = 'esplicita', r.fonte = 'Brocardi.it'
                """,
                {"d_id": dottrina_id, "art_urn": article_urn}
            )
            result.relations_created.append(f"commenta:{dottrina_id}->{article_urn}")

        # Massime → AttoGiudiziario (multiple)
        massime = brocardi.get("Massime", [])
        if isinstance(massime, list):
            for i, massima in enumerate(massime):
                await self._create_atto_giudiziario(
                    massima=massima,
                    article_urn=article_urn,
                    index=i,
                    result=result,
                )

    async def _create_atto_giudiziario(
        self,
        massima: Dict[str, Any],
        article_urn: str,
        index: int,
        result: IngestionResult,
    ) -> None:
        """Create AttoGiudiziario node from a single massima."""
        corte = massima.get("corte", "Cassazione")
        numero = massima.get("numero", f"unknown_{index}")
        estratto = massima.get("estratto", "")

        # Parse numero for year
        anno = ""
        numero_sentenza = numero
        if "/" in numero:
            parts = numero.split("/")
            numero_sentenza = parts[0]
            anno = parts[1] if len(parts) > 1 else ""

        atto_id = f"massima_{corte.lower().replace(' ', '_')}_{numero.replace('/', '_')}"

        await self.falkordb.query(
            """
            MERGE (a:AttoGiudiziario {node_id: $id})
            ON CREATE SET
                a.estremi = $estremi,
                a.organo_emittente = $organo,
                a.numero_sentenza = $numero,
                a.anno = $anno,
                a.massima = $massima,
                a.tipo_atto = 'sentenza',
                a.fonte = 'Brocardi.it',
                a.confidence = 0.9,
                a.created_at = datetime()
            """,
            {
                "id": atto_id,
                "estremi": f"{corte} {numero}",
                "organo": corte,
                "numero": numero_sentenza,
                "anno": anno,
                "massima": estratto,
            }
        )
        result.nodes_created.append(f"AttoGiudiziario:{atto_id}")

        # Relation: AttoGiudiziario -[interpreta]-> Norma
        await self.falkordb.query(
            """
            MATCH (a:AttoGiudiziario {node_id: $a_id})
            MATCH (art:Norma {URN: $art_urn})
            MERGE (a)-[r:interpreta]->(art)
            ON CREATE SET
                r.certezza = 0.9,
                r.tipo_interpretazione = 'giurisprudenziale',
                r.fonte = 'Brocardi.it'
            """,
            {"a_id": atto_id, "art_urn": article_urn}
        )
        result.relations_created.append(f"interpreta:{atto_id}->{article_urn}")


# Convenience function
async def ingest_article_v2(
    article: VisualexArticle,
    falkordb_client=None,
    create_graph: bool = True,
) -> IngestionResult:
    """
    Convenience function to ingest an article with v2 pipeline.

    Args:
        article: VisualexArticle from API
        falkordb_client: Optional FalkorDB client
        create_graph: Whether to create graph nodes

    Returns:
        IngestionResult with chunks and mappings
    """
    pipeline = IngestionPipelineV2(falkordb_client=falkordb_client)
    return await pipeline.ingest_article(article, create_graph_nodes=create_graph)


__all__ = [
    "IngestionPipelineV2",
    "IngestionResult",
    "BridgeMapping",
    "ingest_article_v2",
]
