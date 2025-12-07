"""
MERL-T Sources
==============

Scrapers per fonti giuridiche italiane.

Scrapers disponibili:
- NormattivaScraper: Testi ufficiali da Normattiva.it
- BrocardiScraper: Enrichment (massime, spiegazioni, ratio)

Esempio:
    from merlt.sources import NormattivaScraper, BrocardiScraper

    scraper = NormattivaScraper()
    text, url = await scraper.fetch_document(norma_visitata)
"""

from merlt.sources.normattiva import NormattivaScraper
from merlt.sources.brocardi import BrocardiScraper
from merlt.sources.base import BaseScraper

__all__ = [
    "NormattivaScraper",
    "BrocardiScraper",
    "BaseScraper",
]
