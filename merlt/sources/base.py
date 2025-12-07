"""
Base Scraper Interface
======================

Interfaccia base per tutti gli scrapers di fonti giuridiche.
"""

import structlog
import aiohttp
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from typing import Any, Optional

from merlt.sources.utils.http import http_client

log = structlog.get_logger()


class BaseScraper(ABC):
    """
    Interfaccia base per scrapers di fonti giuridiche.

    Tutti gli scrapers (NormattivaScraper, BrocardiScraper, etc.)
    devono ereditare da questa classe.

    Example:
        >>> class MyCustomScraper(BaseScraper):
        ...     async def fetch_document(self, norma):
        ...         # Implementazione custom
        ...         pass
    """

    async def request_document(self, url: str) -> str:
        """
        Richiede un documento da una URL.

        Args:
            url: URL del documento da scaricare

        Returns:
            Contenuto HTML del documento

        Raises:
            ValueError: Se il download fallisce
        """
        log.info(f"Consulting source - URL: {url}")
        session = await http_client.get_session()
        try:
            async with session.get(url, timeout=30) as response:
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientError as e:
            log.error(f"Error during consultation: {e}")
            raise ValueError(f"Problem with download: {e}")

    def parse_document(self, html_content: str) -> BeautifulSoup:
        """
        Parsa contenuto HTML in BeautifulSoup.

        Args:
            html_content: Stringa HTML da parsare

        Returns:
            Oggetto BeautifulSoup per navigazione DOM
        """
        log.info("Parsing document content")
        return BeautifulSoup(html_content, 'html.parser')
