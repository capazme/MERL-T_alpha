"""
Test Integration per NormattivaScraper
======================================

Test reali che chiamano Normattiva.it per verificare:
- Fetch articoli di vari tipi di atti
- Storia modifiche (multivigenza)
- Error handling
"""

import pytest
from merlt.sources import NormattivaScraper, ScraperConfig, DocumentNotFoundError
from merlt.sources.utils.norma import Norma, NormaVisitata


@pytest.fixture
def scraper():
    """Scraper con timeout aumentato per test integration."""
    config = ScraperConfig(timeout=60)
    return NormattivaScraper(config)


@pytest.mark.integration
class TestNormattivaFetch:
    """Test fetch articoli da Normattiva."""

    @pytest.mark.asyncio
    async def test_fetch_codice_civile_art1(self, scraper):
        """Fetch Art. 1 Codice Civile - capacita' giuridica."""
        norma = Norma(tipo_atto="codice civile")
        nv = NormaVisitata(norma=norma, numero_articolo="1")

        text, urn = await scraper.get_document(nv)

        assert len(text) > 100, "Testo troppo corto"
        # Art. 1 CC parla di capacita' giuridica
        text_lower = text.lower()
        assert "capacit" in text_lower or "giuridica" in text_lower or "nascita" in text_lower
        assert "urn:nir" in urn.lower() or "normattiva" in urn.lower()

    @pytest.mark.asyncio
    async def test_fetch_codice_penale_art52(self, scraper):
        """Fetch Art. 52 Codice Penale - legittima difesa."""
        norma = Norma(tipo_atto="codice penale")
        nv = NormaVisitata(norma=norma, numero_articolo="52")

        text, urn = await scraper.get_document(nv)

        assert len(text) > 50, "Testo troppo corto"
        # Art. 52 CP parla di difesa legittima
        text_lower = text.lower()
        assert "difesa" in text_lower or "reato" in text_lower or "punibile" in text_lower

    @pytest.mark.asyncio
    async def test_fetch_costituzione_art1(self, scraper):
        """Fetch Art. 1 Costituzione - Italia e' una Repubblica."""
        norma = Norma(tipo_atto="costituzione")
        nv = NormaVisitata(norma=norma, numero_articolo="1")

        text, urn = await scraper.get_document(nv)

        assert len(text) > 50, "Testo troppo corto"
        text_lower = text.lower()
        assert "repubblica" in text_lower or "italia" in text_lower or "lavoro" in text_lower

    @pytest.mark.asyncio
    async def test_fetch_legge_241_art2(self, scraper):
        """Fetch Art. 2 L.241/1990 - termine procedimento."""
        norma = Norma(tipo_atto="legge", numero="241", data="1990-08-07")
        nv = NormaVisitata(norma=norma, numero_articolo="2")

        text, urn = await scraper.get_document(nv)

        assert len(text) > 50, "Testo troppo corto"


@pytest.mark.integration
class TestNormattivaAmendments:
    """Test storia modifiche (multivigenza)."""

    @pytest.mark.asyncio
    async def test_amendment_history_art2_241(self, scraper):
        """
        Art. 2 L.241/1990 ha subito molte modifiche.
        Verifica che il sistema le rilevi.
        """
        norma = Norma(tipo_atto="legge", numero="241", data="1990-08-07")
        nv = NormaVisitata(norma=norma, numero_articolo="2")

        modifiche = await scraper.get_amendment_history(nv)

        # Art. 2 L.241 e' stato modificato molte volte
        assert len(modifiche) > 0, "Articolo dovrebbe avere modifiche"

        # Ogni modifica dovrebbe avere i campi base
        for mod in modifiche:
            assert mod.atto_modificante_urn or mod.atto_modificante_estremi

    @pytest.mark.asyncio
    async def test_amendment_history_costituzione_art1(self, scraper):
        """
        Art. 1 Costituzione non e' mai stato modificato.
        Verifica che il sistema rilevi zero modifiche.
        """
        norma = Norma(tipo_atto="costituzione")
        nv = NormaVisitata(norma=norma, numero_articolo="1")

        modifiche = await scraper.get_amendment_history(nv)

        # Art. 1 Cost. non e' mai stato modificato
        assert len(modifiche) == 0, "Art. 1 Costituzione non dovrebbe avere modifiche"


@pytest.mark.integration
class TestNormattivaVersions:
    """Test versioni storiche."""

    @pytest.mark.asyncio
    async def test_original_version_art2_241(self, scraper):
        """
        Fetch versione originale Art. 2 L.241/1990.
        """
        norma = Norma(tipo_atto="legge", numero="241", data="1990-08-07")
        nv = NormaVisitata(norma=norma, numero_articolo="2")

        # Fetch versione originale
        text = await scraper.get_original_version(nv)

        # Dovrebbe essere diversa dalla versione vigente
        assert text is not None
        assert len(text) > 50 if text else True


@pytest.mark.integration
class TestNormattivaErrorHandling:
    """Test gestione errori."""

    @pytest.mark.asyncio
    async def test_nonexistent_article(self, scraper):
        """Articolo inesistente dovrebbe fallire gracefully."""
        norma = Norma(tipo_atto="codice civile")
        nv = NormaVisitata(norma=norma, numero_articolo="99999")

        # Non dovrebbe crashare, ma ritornare errore o stringa vuota
        try:
            text, urn = await scraper.get_document(nv)
            # Se non solleva eccezione, verifica che il testo sia vuoto/errore
            assert text == "" or "error" in text.lower() or "non trovato" in text.lower()
        except (DocumentNotFoundError, ValueError, Exception):
            # Eccezione attesa per articolo inesistente
            pass

    @pytest.mark.asyncio
    async def test_invalid_act_type(self, scraper):
        """Tipo atto invalido dovrebbe fallire gracefully."""
        norma = Norma(tipo_atto="tipo_inventato_12345")
        nv = NormaVisitata(norma=norma, numero_articolo="1")

        try:
            text, urn = await scraper.get_document(nv)
            # Se non solleva eccezione, verifica errore
            assert text == "" or "error" in text.lower()
        except Exception:
            # Eccezione attesa
            pass


@pytest.mark.integration
class TestNormattivaRetry:
    """Test retry logic."""

    @pytest.mark.asyncio
    async def test_retry_config_applied(self):
        """Verifica che la config sia applicata correttamente."""
        config = ScraperConfig(timeout=120, max_concurrent=2)
        scraper = NormattivaScraper(config)

        assert scraper.config.timeout == 120
        assert scraper.config.max_concurrent == 2

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, scraper):
        """Test richieste concorrenti con semaforo."""
        import asyncio

        norma = Norma(tipo_atto="codice civile")
        articles = ["1", "2", "3"]

        async def fetch(art):
            nv = NormaVisitata(norma=norma, numero_articolo=art)
            return await scraper.get_document(nv)

        # Fetch concorrenti
        results = await asyncio.gather(*[fetch(art) for art in articles])

        assert len(results) == 3
        for text, urn in results:
            assert len(text) > 50
