"""
Test Integration per BrocardiScraper
====================================

Test reali che chiamano Brocardi.it per verificare:
- Fetch enrichment articoli
- Estrazione massime giurisprudenziali
- Graceful degradation per articoli mancanti
"""

import pytest
from merlt.sources import BrocardiScraper
from merlt.sources.utils.norma import Norma, NormaVisitata


@pytest.fixture(scope="module")
def scraper():
    """BrocardiScraper con configurazione default."""
    return BrocardiScraper()


@pytest.mark.integration
class TestBrocardiEnrichment:
    """Test fetch enrichment da Brocardi."""

    @pytest.mark.asyncio
    async def test_get_info_codice_civile_art1(self, scraper):
        """
        Fetch enrichment Art. 1 Codice Civile.
        Dovrebbe avere position (breadcrumb) e info.
        """
        norma = Norma(tipo_atto="codice civile")
        nv = NormaVisitata(norma=norma, numero_articolo="1")

        position, info, url = await scraper.get_info(nv)

        # Position dovrebbe contenere gerarchia
        assert position is not None, "Position (breadcrumb) non trovata"
        assert "Libro" in position or "libro" in position.lower()

        # URL dovrebbe puntare a brocardi
        assert url is not None
        assert "brocardi" in url.lower()

        # Info dovrebbe essere un dict
        assert isinstance(info, dict)

    @pytest.mark.asyncio
    async def test_get_info_codice_civile_art1218(self, scraper):
        """
        Art. 1218 CC (responsabilita' debitore) - articolo molto commentato.
        Dovrebbe avere massime giurisprudenziali.
        """
        norma = Norma(tipo_atto="codice civile")
        nv = NormaVisitata(norma=norma, numero_articolo="1218")

        position, info, url = await scraper.get_info(nv)

        # Verifica che abbiamo dati
        assert position is not None
        assert url is not None

        # Art. 1218 e' molto commentato, dovrebbe avere contenuti
        # Ma non garantiamo quali campi specifici
        assert isinstance(info, dict)

    @pytest.mark.asyncio
    async def test_get_info_codice_penale_art52(self, scraper):
        """
        Art. 52 CP (legittima difesa) - molto commentato.
        """
        norma = Norma(tipo_atto="codice penale")
        nv = NormaVisitata(norma=norma, numero_articolo="52")

        position, info, url = await scraper.get_info(nv)

        assert position is not None or url is not None
        assert isinstance(info, dict)


@pytest.mark.integration
class TestBrocardiMassime:
    """Test estrazione massime giurisprudenziali."""

    @pytest.mark.asyncio
    async def test_massime_structure(self, scraper):
        """
        Verifica struttura massime (quando presenti).
        """
        # Art. 2043 CC (risarcimento danno) ha molte massime
        norma = Norma(tipo_atto="codice civile")
        nv = NormaVisitata(norma=norma, numero_articolo="2043")

        position, info, url = await scraper.get_info(nv)

        # Se ci sono massime, verifica struttura
        if "Massime" in info and info["Massime"]:
            massima = info["Massime"][0]
            # Massima puo' avere vari campi
            assert isinstance(massima, (dict, str))

            if isinstance(massima, dict):
                # Se dict, potrebbe avere autorita', numero, anno, massima
                assert "massima" in massima or "autorita" in massima or len(massima) > 0


@pytest.mark.integration
class TestBrocardiGracefulDegradation:
    """Test graceful degradation."""

    @pytest.mark.asyncio
    async def test_article_not_on_brocardi(self, scraper):
        """
        Articolo non presente su Brocardi.
        Dovrebbe ritornare gracefully, non crashare.
        """
        # Articolo che probabilmente non esiste su Brocardi
        norma = Norma(tipo_atto="codice civile")
        nv = NormaVisitata(norma=norma, numero_articolo="9999")

        position, info, url = await scraper.get_info(nv)

        # Graceful degradation: ritorna None/empty, non exception
        # Almeno uno di questi dovrebbe essere None/vuoto
        assert url is None or info == {} or position is None

    @pytest.mark.asyncio
    async def test_unknown_codice(self, scraper):
        """
        Codice sconosciuto a Brocardi.
        """
        norma = Norma(tipo_atto="codice_inventato_xyz")
        nv = NormaVisitata(norma=norma, numero_articolo="1")

        position, info, url = await scraper.get_info(nv)

        # Dovrebbe fallire gracefully
        assert url is None or info == {}


@pytest.mark.integration
class TestBrocardiContent:
    """Test contenuti estratti."""

    @pytest.mark.asyncio
    async def test_ratio_extraction(self, scraper):
        """
        Verifica estrazione ratio (quando presente).
        """
        # Art. 1 CC ha una ratio
        norma = Norma(tipo_atto="codice civile")
        nv = NormaVisitata(norma=norma, numero_articolo="1")

        position, info, url = await scraper.get_info(nv)

        # La ratio potrebbe essere presente
        if "Ratio" in info:
            ratio = info["Ratio"]
            assert isinstance(ratio, str)
            # Se presente, dovrebbe avere contenuto
            if ratio:
                assert len(ratio) > 10

    @pytest.mark.asyncio
    async def test_brocardi_massime_dottrinali(self, scraper):
        """
        Verifica estrazione brocardi (massime dottrinali).
        """
        norma = Norma(tipo_atto="codice civile")
        nv = NormaVisitata(norma=norma, numero_articolo="1")

        position, info, url = await scraper.get_info(nv)

        # I brocardi sono massime dottrinali latine
        if "Brocardi" in info and info["Brocardi"]:
            brocardi = info["Brocardi"]
            assert isinstance(brocardi, list)
            for b in brocardi:
                assert isinstance(b, str)


@pytest.mark.integration
class TestBrocardiRetry:
    """Test retry e rate limiting."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, scraper):
        """Test richieste concorrenti."""
        import asyncio

        norma = Norma(tipo_atto="codice civile")
        articles = ["1", "2", "3"]

        async def fetch(art):
            nv = NormaVisitata(norma=norma, numero_articolo=art)
            return await scraper.get_info(nv)

        # Fetch concorrenti (rate limited dal semaforo interno)
        results = await asyncio.gather(*[fetch(art) for art in articles])

        assert len(results) == 3
        for position, info, url in results:
            # Almeno uno dovrebbe avere contenuto
            assert position is not None or url is not None or info
