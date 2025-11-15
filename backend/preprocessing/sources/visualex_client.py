# =============================================================================
# Visualex API Client - Integration with MERL-T Ingestion Pipeline
# =============================================================================
#
# This client integrates the visualex API (Quart-based legal document scraper)
# with the MERL-T ingestion pipeline for importing Italian legal norms into Neo4j.
#
# Visualex API Endpoints:
#   POST /fetch_article_text - Fetch single or multiple articles
#   POST /stream_article_text - Stream articles progressively
#   POST /fetch_norma_data - Get norm metadata without text
#
# Data Flow:
#   1. Client requests article from visualex (tipo_atto, numero_articolo)
#   2. Visualex scrapes Normattiva/EUR-Lex
#   3. Returns cleaned text + metadata
#   4. Client converts to Neo4j entities (Norma nodes)
#   5. Sends to unified ingestion pipeline
#
# =============================================================================

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import structlog

log = structlog.get_logger(__name__)


# =============================================================================
# Data Models (Mirror visualex models)
# =============================================================================

@dataclass
class BrocardiInfo:
    """
    Doctrinal and jurisprudential data from Brocardi.it.
    """
    position: Optional[str] = None  # Position in code (e.g., "Libro VI - Tutela dei diritti")
    brocardi: Optional[List[str]] = None  # Latin maxims/legal principles
    ratio: Optional[str] = None  # Ratio legis (purpose/foundation of the norm)
    spiegazione: Optional[str] = None  # Detailed explanation
    massime: Optional[List[str]] = None  # Case law maxims (jurisprudence)
    link: Optional[str] = None  # Link to Brocardi.it page

    def to_neo4j_relationships(self, article_urn: str) -> List[Dict[str, Any]]:
        """
        Convert BrocardiInfo to Neo4j relationships.

        Returns:
            List of relationship dicts for Neo4j ingestion
        """
        relationships = []

        # Brocardi (legal principles) as separate nodes
        if self.brocardi:
            for brocardo in self.brocardi:
                relationships.append({
                    'type': 'HA_PRINCIPIO',
                    'source_urn': article_urn,
                    'target_node': {
                        'entity_type': 'PrincipioGiuridico',
                        'properties': {
                            'nome': brocardo,
                            'tipo': 'brocardo_latino',
                            'source': 'brocardi.it'
                        }
                    }
                })

        # Massime (case law) as separate nodes
        if self.massime:
            for massima in self.massime:
                relationships.append({
                    'type': 'CITATO_IN',
                    'source_urn': article_urn,
                    'target_node': {
                        'entity_type': 'Massima',
                        'properties': {
                            'testo': massima,
                            'fonte': 'giurisprudenza',
                            'source': 'brocardi.it'
                        }
                    }
                })

        return relationships


@dataclass
class NormaData:
    """
    Mirrors visualex NormaVisitata output.
    Represents a single article from a legal norm.
    """
    tipo_atto: str  # e.g., "codice civile", "decreto legge"
    numero_articolo: str  # e.g., "2043"
    data: Optional[str] = None  # e.g., "16 marzo 1942"
    numero_atto: Optional[str] = None  # e.g., "262"
    versione: Optional[str] = None
    data_versione: Optional[str] = None
    allegato: Optional[str] = None
    url: Optional[str] = None
    urn: Optional[str] = None
    article_text: Optional[str] = None  # Full text content
    brocardi_info: Optional[BrocardiInfo] = None  # Doctrinal/jurisprudential data
    error: Optional[str] = None  # Error message if fetch failed

    def to_neo4j_entity(self) -> Dict[str, Any]:
        """
        Convert to Neo4j entity format for ingestion pipeline.

        Returns:
            Dict with entity properties for Neo4j node creation + relationships
        """
        # Extract article number and title from article_text
        title = None
        if self.article_text:
            lines = self.article_text.split('\n')
            if len(lines) >= 2:
                title = lines[1].strip()  # Second line is usually the title

        # Base entity
        entity = {
            'entity_type': 'Norma',
            'properties': {
                'tipo_atto': self.tipo_atto,
                'numero_articolo': self.numero_articolo,
                'numero_atto': self.numero_atto,
                'data': self.data,
                'titolo': title,
                'testo_completo': self.article_text,
                'urn': self.urn,
                'url': self.url,
                'versione': self.versione,
                'data_versione': self.data_versione,
                'source': 'visualex',
                'import_timestamp': datetime.utcnow().isoformat(),
            },
            'confidence': 1.0,  # Structured data from official source
            'provenance': {
                'source': 'visualex',
                'source_url': self.url,
                'urn': self.urn,
                'scraper': 'Normattiva' if 'normattiva' in (self.url or '') else 'Unknown'
            }
        }

        # Add BrocardiInfo properties if available
        if self.brocardi_info:
            entity['properties']['brocardi_position'] = self.brocardi_info.position
            entity['properties']['brocardi_ratio'] = self.brocardi_info.ratio
            entity['properties']['brocardi_spiegazione'] = self.brocardi_info.spiegazione
            entity['properties']['brocardi_link'] = self.brocardi_info.link

            # Add relationships (principles, case law)
            entity['relationships'] = self.brocardi_info.to_neo4j_relationships(self.urn)

        return entity


@dataclass
class VisualeExResponse:
    """Wrapper for visualex API response."""
    success: bool
    data: List[NormaData] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_fetched: int = 0
    total_errors: int = 0


# =============================================================================
# Visualex Client
# =============================================================================

class VisualeXClient:
    """
    Async HTTP client for visualex API integration.

    Features:
    - Batch article fetching (multiple articles in one request)
    - Rate limiting (respects visualex rate limits)
    - Retry logic with exponential backoff
    - Progress tracking for large batches
    - Streaming support for incremental processing
    """

    def __init__(
        self,
        base_url: str = "http://localhost:5000",
        timeout: int = 120,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize visualex client.

        Args:
            base_url: Base URL of visualex API (default: http://localhost:5000)
            timeout: Request timeout in seconds (default: 120)
            max_retries: Max retry attempts for failed requests (default: 3)
            retry_delay: Initial retry delay in seconds (default: 1.0)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session: Optional[aiohttp.ClientSession] = None

        log.info(
            "VisualeXClient initialized",
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self):
        """Ensure aiohttp session is created."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
            log.debug("Created new aiohttp session")

    async def close(self):
        """Close aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            log.debug("Closed aiohttp session")

    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint path
            json_data: JSON payload for POST requests

        Returns:
            Response JSON data

        Raises:
            aiohttp.ClientError: If request fails after max retries
        """
        await self._ensure_session()
        url = f"{self.base_url}{endpoint}"
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                log.debug(
                    "Making HTTP request",
                    method=method,
                    url=url,
                    attempt=attempt + 1,
                    max_retries=self.max_retries
                )

                async with self.session.request(
                    method,
                    url,
                    json=json_data
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    log.debug("Request successful", status=response.status)
                    return data

            except aiohttp.ClientError as e:
                last_exception = e
                log.warning(
                    "Request failed",
                    error=str(e),
                    attempt=attempt + 1,
                    max_retries=self.max_retries
                )

                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    delay = self.retry_delay * (2 ** attempt)
                    log.debug(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    log.error("Max retries exceeded", error=str(e))
                    raise

        # Should not reach here, but if it does, raise last exception
        if last_exception:
            raise last_exception

    async def fetch_articles(
        self,
        tipo_atto: str,
        articoli: List[str],
        data: Optional[str] = None,
        numero_atto: Optional[str] = None,
        versione: Optional[str] = None,
        data_versione: Optional[str] = None,
        allegato: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> VisualeXResponse:
        """
        Fetch multiple articles from a single legal norm.

        Args:
            tipo_atto: Type of legal act (e.g., "codice civile", "decreto legge")
            articoli: List of article numbers (e.g., ["2043", "2044", "2045"])
            data: Date of the act (e.g., "16 marzo 1942")
            numero_atto: Act number (e.g., "262")
            versione: Specific version identifier
            data_versione: Version date
            allegato: Annex identifier
            progress_callback: Optional callback for progress updates (called per article)

        Returns:
            VisualeXResponse with fetched articles and errors

        Example:
            >>> async with VisualeXClient() as client:
            ...     response = await client.fetch_articles(
            ...         tipo_atto="codice civile",
            ...         articoli=["2043", "2044", "2045"]
            ...     )
            ...     print(f"Fetched {response.total_fetched} articles")
        """
        log.info(
            "Fetching articles",
            tipo_atto=tipo_atto,
            articoli_count=len(articoli),
            data=data,
            numero_atto=numero_atto
        )

        # Prepare request payload (visualex format)
        payload = {
            'act_type': tipo_atto,
            'article': ','.join(articoli),  # Comma-separated article numbers
        }

        if data:
            payload['date'] = data
        if numero_atto:
            payload['act_number'] = numero_atto
        if versione:
            payload['version'] = versione
        if data_versione:
            payload['version_date'] = data_versione
        if allegato:
            payload['annex'] = allegato

        try:
            # Call visualex API
            response_data = await self._request_with_retry(
                method='POST',
                endpoint='/fetch_article_text',
                json_data=payload
            )

            # Parse response
            norma_data_list = []
            errors = []

            # visualex returns list of article results
            if isinstance(response_data, list):
                for idx, article_result in enumerate(response_data):
                    if 'error' in article_result:
                        error_msg = article_result['error']
                        errors.append(error_msg)
                        log.warning(
                            "Article fetch failed",
                            article=articoli[idx] if idx < len(articoli) else None,
                            error=error_msg
                        )
                    else:
                        # Successful fetch
                        norma_data = NormaData(
                            tipo_atto=article_result.get('norma_data', {}).get('tipo_atto', tipo_atto),
                            numero_articolo=article_result.get('norma_data', {}).get('numero_articolo'),
                            data=article_result.get('norma_data', {}).get('data', data),
                            numero_atto=article_result.get('norma_data', {}).get('numero_atto', numero_atto),
                            versione=article_result.get('norma_data', {}).get('versione', versione),
                            data_versione=article_result.get('norma_data', {}).get('data_versione', data_versione),
                            allegato=article_result.get('norma_data', {}).get('allegato', allegato),
                            url=article_result.get('url'),
                            urn=article_result.get('norma_data', {}).get('urn'),
                            article_text=article_result.get('article_text')
                        )
                        norma_data_list.append(norma_data)
                        log.debug(
                            "Article fetched successfully",
                            numero_articolo=norma_data.numero_articolo,
                            text_length=len(norma_data.article_text) if norma_data.article_text else 0
                        )

                    # Progress callback
                    if progress_callback:
                        await progress_callback(idx + 1, len(articoli))

            return VisualeXResponse(
                success=len(errors) == 0,
                data=norma_data_list,
                errors=errors,
                total_fetched=len(norma_data_list),
                total_errors=len(errors)
            )

        except Exception as e:
            log.error("Failed to fetch articles", error=str(e), exc_info=True)
            return VisualeXResponse(
                success=False,
                errors=[str(e)],
                total_errors=1
            )

    async def fetch_brocardi_info(
        self,
        tipo_atto: str,
        articoli: List[str],
        **kwargs
    ) -> Dict[str, BrocardiInfo]:
        """
        Fetch BrocardiInfo (doctrinal/jurisprudential data) for articles.

        Args:
            tipo_atto: Type of legal act
            articoli: List of article numbers
            **kwargs: Additional arguments (data, numero_atto, etc.)

        Returns:
            Dict mapping article_number → BrocardiInfo

        Example:
            >>> async with VisualeXClient() as client:
            ...     brocardi_data = await client.fetch_brocardi_info(
            ...         tipo_atto="codice civile",
            ...         articoli=["2043", "2044"]
            ...     )
        """
        log.info("Fetching BrocardiInfo", tipo_atto=tipo_atto, articoli_count=len(articoli))

        # Prepare payload
        payload = {
            'act_type': tipo_atto,
            'article': ','.join(articoli),
        }
        for key, value in kwargs.items():
            if key in ['date', 'act_number', 'version', 'version_date', 'annex']:
                payload[key] = value

        try:
            response_data = await self._request_with_retry(
                method='POST',
                endpoint='/fetch_brocardi_info',
                json_data=payload
            )

            # Parse response
            brocardi_map = {}
            if isinstance(response_data, list):
                for result in response_data:
                    if 'error' not in result and result.get('brocardi_info'):
                        info = result['brocardi_info']
                        article_num = result.get('norma_data', {}).get('numero_articolo')

                        if article_num:
                            brocardi_map[article_num] = BrocardiInfo(
                                position=info.get('position'),
                                brocardi=info.get('Brocardi'),
                                ratio=info.get('Ratio'),
                                spiegazione=info.get('Spiegazione'),
                                massime=info.get('Massime'),
                                link=info.get('link')
                            )

            log.info("BrocardiInfo fetched", count=len(brocardi_map))
            return brocardi_map

        except Exception as e:
            log.error("Failed to fetch BrocardiInfo", error=str(e), exc_info=True)
            return {}

    async def fetch_articles_with_brocardi(
        self,
        tipo_atto: str,
        articoli: List[str],
        progress_callback: Optional[callable] = None,
        **kwargs
    ) -> VisualeXResponse:
        """
        Fetch articles WITH BrocardiInfo enrichment.

        This makes 2 API calls:
        1. /fetch_article_text - Get article text
        2. /fetch_brocardi_info - Get doctrinal/jurisprudential data

        Then merges the results.

        Args:
            tipo_atto: Type of legal act
            articoli: List of article numbers
            progress_callback: Optional callback(current, total)
            **kwargs: Additional arguments (data, numero_atto, etc.)

        Returns:
            VisualeXResponse with NormaData enriched with BrocardiInfo
        """
        log.info(
            "Fetching articles WITH BrocardiInfo",
            tipo_atto=tipo_atto,
            articoli_count=len(articoli)
        )

        # Fetch article text
        articles_response = await self.fetch_articles(
            tipo_atto=tipo_atto,
            articoli=articoli,
            progress_callback=progress_callback,
            **kwargs
        )

        # Fetch BrocardiInfo
        brocardi_map = await self.fetch_brocardi_info(
            tipo_atto=tipo_atto,
            articoli=articoli,
            **kwargs
        )

        # Merge BrocardiInfo into NormaData
        for norma_data in articles_response.data:
            if norma_data.numero_articolo in brocardi_map:
                norma_data.brocardi_info = brocardi_map[norma_data.numero_articolo]
                log.debug(
                    "Enriched with BrocardiInfo",
                    article=norma_data.numero_articolo,
                    has_brocardi=bool(norma_data.brocardi_info.brocardi),
                    has_massime=bool(norma_data.brocardi_info.massime)
                )

        return articles_response

    async def fetch_codice_civile_batch(
        self,
        start_article: int,
        end_article: int,
        batch_size: int = 50,
        include_brocardi: bool = True,
        progress_callback: Optional[callable] = None
    ) -> VisualeXResponse:
        """
        Fetch a batch of Codice Civile articles.

        Convenience method for importing sequential articles from Codice Civile.

        Args:
            start_article: Starting article number (e.g., 1)
            end_article: Ending article number (inclusive, e.g., 2969)
            batch_size: Number of articles per API request (default: 50)
            include_brocardi: Include BrocardiInfo enrichment (default: True)
            progress_callback: Optional callback(current, total)

        Returns:
            VisualeXResponse with all fetched articles

        Example:
            >>> # Import articles 1-100 from Codice Civile with BrocardiInfo
            >>> async with VisualeXClient() as client:
            ...     response = await client.fetch_codice_civile_batch(
            ...         1, 100, include_brocardi=True
            ...     )
            ...     print(f"Imported {response.total_fetched} articles")
        """
        log.info(
            "Fetching Codice Civile batch",
            start_article=start_article,
            end_article=end_article,
            batch_size=batch_size,
            include_brocardi=include_brocardi
        )

        all_data = []
        all_errors = []
        total_articles = end_article - start_article + 1

        # Process in batches
        for batch_start in range(start_article, end_article + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, end_article)
            batch_articles = [str(i) for i in range(batch_start, batch_end + 1)]

            log.debug(
                "Fetching batch",
                batch_start=batch_start,
                batch_end=batch_end,
                batch_count=len(batch_articles)
            )

            # Fetch batch (with or without BrocardiInfo)
            if include_brocardi:
                response = await self.fetch_articles_with_brocardi(
                    tipo_atto="codice civile",
                    articoli=batch_articles,
                    progress_callback=None  # Use outer progress callback instead
                )
            else:
                response = await self.fetch_articles(
                    tipo_atto="codice civile",
                    articoli=batch_articles,
                    progress_callback=None
                )

            all_data.extend(response.data)
            all_errors.extend(response.errors)

            # Update progress
            if progress_callback:
                current_progress = batch_end - start_article + 1
                await progress_callback(current_progress, total_articles)

            # Brief pause between batches to respect rate limits
            if batch_end < end_article:
                await asyncio.sleep(0.5)

        log.info(
            "Batch fetch complete",
            total_fetched=len(all_data),
            total_errors=len(all_errors)
        )

        return VisualeXResponse(
            success=len(all_errors) == 0,
            data=all_data,
            errors=all_errors,
            total_fetched=len(all_data),
            total_errors=len(all_errors)
        )


# =============================================================================
# Utility Functions
# =============================================================================

async def fetch_and_convert_to_neo4j(
    client: VisualeXClient,
    tipo_atto: str,
    articoli: List[str],
    **kwargs
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Fetch articles and convert to Neo4j entity format.

    Args:
        client: VisualeXClient instance
        tipo_atto: Type of legal act
        articoli: List of article numbers
        **kwargs: Additional arguments for fetch_articles()

    Returns:
        Tuple of (neo4j_entities, errors)

    Example:
        >>> async with VisualeXClient() as client:
        ...     entities, errors = await fetch_and_convert_to_neo4j(
        ...         client, "codice civile", ["2043", "2044"]
        ...     )
        ...     # entities is ready for Neo4j ingestion
    """
    response = await client.fetch_articles(tipo_atto, articoli, **kwargs)

    neo4j_entities = [
        norma_data.to_neo4j_entity()
        for norma_data in response.data
    ]

    return neo4j_entities, response.errors


# =============================================================================
# CLI Entry Point (for testing)
# =============================================================================

async def main():
    """Test visualex client with sample Codice Civile articles."""
    import sys

    # Configure logging for CLI
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ]
    )

    log.info("Testing VisualeXClient with Codice Civile articles")

    async with VisualeXClient() as client:
        # Test 1: Fetch single article
        log.info("Test 1: Fetching Art. 2043")
        response = await client.fetch_articles(
            tipo_atto="codice civile",
            articoli=["2043"]
        )

        if response.success and response.data:
            article = response.data[0]
            log.info(
                "Article fetched",
                numero_articolo=article.numero_articolo,
                text_preview=article.article_text[:100] if article.article_text else None
            )
        else:
            log.error("Fetch failed", errors=response.errors)

        # Test 2: Batch fetch
        log.info("Test 2: Batch fetching articles 1-10")

        def progress(current, total):
            print(f"\rProgress: {current}/{total}", end='')

        response = await client.fetch_codice_civile_batch(
            start_article=1,
            end_article=10,
            batch_size=5,
            progress_callback=progress
        )

        print()  # Newline after progress
        log.info(
            "Batch fetch complete",
            total_fetched=response.total_fetched,
            total_errors=response.total_errors
        )

        # Test 3: Convert to Neo4j format
        if response.data:
            log.info("Test 3: Converting to Neo4j entities")
            neo4j_entity = response.data[0].to_neo4j_entity()
            log.info("Sample Neo4j entity", entity=neo4j_entity)


if __name__ == "__main__":
    asyncio.run(main())
