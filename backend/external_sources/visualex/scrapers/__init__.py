"""
VisualexAPI Scrapers
====================

Web scrapers for Italian and EU legal sources.

Available scrapers:
- normattiva_scraper: Normattiva.it (Italian legislation)
- brocardi_scraper: Brocardi.it (legal commentary)
- eurlex_scraper: EUR-Lex (EU legislation)
"""

from . import normattiva_scraper
from . import brocardi_scraper
from . import eurlex_scraper

__all__ = [
    "normattiva_scraper",
    "brocardi_scraper",
    "eurlex_scraper",
]
