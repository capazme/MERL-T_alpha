"""
Enrichment Pipeline
===================

Orchestratore principale per la pipeline di enrichment.

Coordina:
- Fetch contenuti da fonti (Sources)
- Estrazione entità (Extractors)
- Linking e deduplicazione (Linkers)
- Scrittura nel grafo (Writers)

Esempio:
    from merlt.pipeline.enrichment import EnrichmentPipeline, EnrichmentConfig

    pipeline = EnrichmentPipeline(
        graph_client=falkordb_client,
        embedding_service=embedding_service,
        llm_service=llm_service,
        config=config,
    )

    result = await pipeline.run()
"""

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from merlt.pipeline.enrichment.checkpoint import CheckpointManager
from merlt.pipeline.enrichment.config import EnrichmentConfig
from merlt.pipeline.enrichment.models import (
    EnrichmentContent,
    EnrichmentResult,
    ExtractedEntity,
    LinkedEntity,
)

if TYPE_CHECKING:
    from merlt.storage.graph import FalkorDBClient
    from merlt.storage.vectors import EmbeddingService
    from merlt.sources.llm import OpenRouterService

logger = logging.getLogger(__name__)


class EnrichmentPipeline:
    """
    Pipeline di enrichment per estrarre entità strutturate.

    Riproducibile, scalabile, robusto.

    Attributes:
        graph: Client FalkorDB
        embeddings: Servizio embeddings
        llm: Servizio LLM per estrazione
        config: Configurazione enrichment

    Example:
        >>> pipeline = EnrichmentPipeline(graph, embeddings, llm, config)
        >>> result = await pipeline.run()
        >>> print(result.summary())
    """

    def __init__(
        self,
        graph_client: "FalkorDBClient",
        embedding_service: "EmbeddingService",
        llm_service: "OpenRouterService",
        config: EnrichmentConfig,
    ):
        """
        Inizializza la pipeline.

        Args:
            graph_client: Client FalkorDB per lettura/scrittura grafo
            embedding_service: Servizio per embeddings (dedup semantico)
            llm_service: Servizio LLM per estrazione entità
            config: Configurazione dell'enrichment
        """
        self.graph = graph_client
        self.embeddings = embedding_service
        self.llm = llm_service
        self.config = config

        # Componenti (inizializzati lazy)
        self._extractors = None
        self._linker = None
        self._writer = None

        # Checkpoint
        self.checkpoint = CheckpointManager(
            checkpoint_dir=config.checkpoint_dir,
            run_id=self._generate_run_id(),
        )

    def _generate_run_id(self) -> str:
        """Genera run_id basato su config."""
        # Hash della config per identificare esecuzioni equivalenti
        config_str = str(self.config.to_dict())
        config_hash = hashlib.md5(config_str.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"enrichment_{timestamp}_{config_hash}"

    def _config_hash(self) -> str:
        """Hash della config per validazione checkpoint."""
        config_str = str(self.config.to_dict())
        return hashlib.md5(config_str.encode()).hexdigest()

    async def _init_components(self) -> None:
        """Inizializza componenti lazy."""
        if self._extractors is None:
            from merlt.pipeline.enrichment.extractors import (
                ConceptExtractor,
                PrincipleExtractor,
                DefinitionExtractor,
            )
            from merlt.pipeline.enrichment.models import EntityType

            self._extractors = {}
            if EntityType.CONCETTO in self.config.entity_types:
                self._extractors[EntityType.CONCETTO] = ConceptExtractor(self.llm)
            if EntityType.PRINCIPIO in self.config.entity_types:
                self._extractors[EntityType.PRINCIPIO] = PrincipleExtractor(self.llm)
            if EntityType.DEFINIZIONE in self.config.entity_types:
                self._extractors[EntityType.DEFINIZIONE] = DefinitionExtractor(self.llm)

        if self._linker is None:
            from merlt.pipeline.enrichment.linkers import EntityLinker

            self._linker = EntityLinker(
                graph_client=self.graph,
                similarity_threshold=self.config.similarity_threshold,
                merge_strategy=self.config.merge_strategy,
            )

        if self._writer is None:
            from merlt.pipeline.enrichment.writers import EnrichmentGraphWriter

            self._writer = EnrichmentGraphWriter(
                graph_client=self.graph,
                schema_version=self.config.schema_version,
            )

    async def run(self) -> EnrichmentResult:
        """
        Esegue la pipeline di enrichment.

        Processa tutte le fonti configurate, estrae entità,
        deduplica e scrive nel grafo.

        Returns:
            EnrichmentResult con statistiche e errori

        Example:
            >>> result = await pipeline.run()
            >>> print(f"Creati {result.stats.total_entities_created} entità")
        """
        result = EnrichmentResult()
        result.started_at = datetime.now()

        # Inizializza componenti
        await self._init_components()

        # Inizia checkpoint
        self.checkpoint.start_run(self._config_hash())

        # Carica già processati
        processed = self.checkpoint.load()
        result.contents_skipped = len(processed)

        logger.info(
            f"Avvio enrichment: {len(self.config.sources)} fonti, "
            f"{len(processed)} già processati"
        )

        # Processa ogni fonte
        for source in self.config.sources:
            logger.info(f"Processing fonte: {source.source_name}")

            try:
                async for content in source.fetch(self.config.scope):
                    # Skip se già processato
                    if content.id in processed:
                        continue

                    # Processa content
                    await self._process_content(content, result)
                    result.contents_processed += 1

            except Exception as e:
                logger.error(f"Errore fonte {source.source_name}: {e}")
                result.add_error(
                    content_id=f"source:{source.source_name}",
                    phase="fetch",
                    error=e,
                )

        # Finalizza
        result.completed_at = datetime.now()
        self.checkpoint.finalize()

        logger.info(result.summary())
        return result

    async def _process_content(
        self,
        content: EnrichmentContent,
        result: EnrichmentResult,
    ) -> None:
        """
        Processa un singolo contenuto.

        Args:
            content: Contenuto da processare
            result: Risultato da aggiornare
        """
        try:
            # 1. Estrai entità
            entities = await self._extract_entities(content)

            if self.config.verbose:
                logger.debug(
                    f"Estratte {len(entities)} entità da {content.id}"
                )

            # 2. Link e dedup
            linked = await self._linker.link_batch(entities)

            # 3. Scrivi nel grafo (se non dry_run)
            if not self.config.dry_run:
                written = await self._writer.write_batch(linked, content)
                self._update_stats(result, written)
            else:
                # Dry run: simula scrittura
                for le in linked:
                    result.entities_created.append(le.node_id)

            # 4. Checkpoint
            self.checkpoint.mark_done(
                content.id,
                stats_update={"processed": 1}
            )

        except Exception as e:
            logger.error(f"Errore processing {content.id}: {e}")
            result.add_error(content.id, "processing", e)
            self.checkpoint.mark_error(content.id)

    async def _extract_entities(
        self,
        content: EnrichmentContent,
    ) -> List[ExtractedEntity]:
        """
        Estrae entità da un contenuto usando tutti gli extractor.

        Args:
            content: Contenuto da processare

        Returns:
            Lista di entità estratte
        """
        all_entities = []

        # Esegui extractors in parallelo
        tasks = []
        for entity_type, extractor in self._extractors.items():
            tasks.append(extractor.extract(content))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.warning(f"Extractor error: {res}")
                continue
            all_entities.extend(res)

        return all_entities

    def _update_stats(
        self,
        result: EnrichmentResult,
        written: List[LinkedEntity],
    ) -> None:
        """Aggiorna statistiche in base a entità scritte."""
        from merlt.pipeline.enrichment.models import EntityType

        for le in written:
            result.entities_created.append(le.node_id)

            if le.entity.tipo == EntityType.CONCETTO:
                if le.is_new:
                    result.stats.concepts_created += 1
                else:
                    result.stats.concepts_merged += 1
            elif le.entity.tipo == EntityType.PRINCIPIO:
                if le.is_new:
                    result.stats.principles_created += 1
                else:
                    result.stats.principles_merged += 1
            elif le.entity.tipo == EntityType.DEFINIZIONE:
                if le.is_new:
                    result.stats.definitions_created += 1
                else:
                    result.stats.definitions_merged += 1

    async def cleanup_existing_dottrina(self) -> int:
        """
        Cancella nodi Dottrina esistenti (pre-enrichment).

        ATTENZIONE: Operazione distruttiva!

        Returns:
            Numero di nodi cancellati
        """
        logger.warning("Cancellazione nodi Dottrina esistenti...")

        query = """
            MATCH (d:Dottrina)
            WITH d LIMIT 1000
            DETACH DELETE d
            RETURN count(d) as deleted
        """

        total_deleted = 0
        while True:
            result = await self.graph.query(query)
            deleted = result[0]["deleted"] if result else 0
            total_deleted += deleted

            if deleted < 1000:
                break

            logger.info(f"Cancellati {total_deleted} nodi Dottrina...")

        logger.info(f"Totale nodi Dottrina cancellati: {total_deleted}")
        return total_deleted
