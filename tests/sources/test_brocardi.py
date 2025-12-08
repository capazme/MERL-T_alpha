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


class TestMassimaParsing:
    """
    Test unitari per parsing massime giurisprudenziali.

    Verifica che _parse_massima supporti tutte le autorità giudiziarie italiane.
    """

    @pytest.fixture
    def scraper(self):
        return BrocardiScraper()

    @pytest.fixture
    def make_html(self):
        """Factory per creare HTML di test."""
        from bs4 import BeautifulSoup
        def _make(header_text, massima_text):
            html = f'''
            <div class="sentenza corpoDelTesto">
                <p><strong>{header_text}</strong></p>
                <p>{massima_text}</p>
            </div>
            '''
            return BeautifulSoup(html, 'html.parser').find('div')
        return _make

    def test_parse_cassazione_civile(self, scraper, make_html):
        """Test parsing Cass. civ."""
        div = make_html("Cass. civ. n. 36918/2021", "Testo della massima")
        result = scraper._parse_massima(div)

        assert result is not None
        assert result['autorita'] == "Cass. civ."
        assert result['numero'] == "36918"
        assert result['anno'] == "2021"
        assert "massima" in result['massima'].lower()

    def test_parse_cassazione_penale(self, scraper, make_html):
        """Test parsing Cass. pen."""
        div = make_html("Cass. pen. n. 12345/2020", "Massima penale")
        result = scraper._parse_massima(div)

        assert result is not None
        assert result['autorita'] == "Cass. pen."
        assert result['numero'] == "12345"
        assert result['anno'] == "2020"

    def test_parse_cassazione_sezioni_unite(self, scraper, make_html):
        """Test parsing Cass. sez. un."""
        div = make_html("Cass. sez. un. n. 100/2022", "Massima sezioni unite")
        result = scraper._parse_massima(div)

        assert result is not None
        assert "sez" in result['autorita'].lower() or "Cass" in result['autorita']
        assert result['numero'] == "100"
        assert result['anno'] == "2022"

    def test_parse_corte_costituzionale(self, scraper, make_html):
        """Test parsing Corte cost. - NUOVA AUTORITA'."""
        div = make_html("Corte cost. n. 242/2019", "La Corte dichiara l'illegittimita'...")
        result = scraper._parse_massima(div)

        assert result is not None
        assert result['autorita'] is not None
        assert "cost" in result['autorita'].lower() or "Corte" in result['autorita']
        assert result['numero'] == "242"
        assert result['anno'] == "2019"

    def test_parse_corte_costituzionale_abbreviata(self, scraper, make_html):
        """Test parsing C. cost."""
        div = make_html("C. cost. n. 1/2021", "Sentenza costituzionale")
        result = scraper._parse_massima(div)

        assert result is not None
        assert result['numero'] == "1"
        assert result['anno'] == "2021"

    def test_parse_consiglio_stato(self, scraper, make_html):
        """Test parsing Cons. St."""
        div = make_html("Cons. St. n. 5678/2023", "Decisione amministrativa")
        result = scraper._parse_massima(div)

        assert result is not None
        assert result['autorita'] is not None
        assert result['numero'] == "5678"
        assert result['anno'] == "2023"

    def test_parse_tar_lazio(self, scraper, make_html):
        """Test parsing TAR Lazio."""
        div = make_html("TAR Lazio n. 1234/2022", "Sentenza TAR")
        result = scraper._parse_massima(div)

        assert result is not None
        assert result['autorita'] is not None
        assert "TAR" in result['autorita']
        assert result['numero'] == "1234"
        assert result['anno'] == "2022"

    def test_parse_tar_lombardia(self, scraper, make_html):
        """Test parsing TAR Lombardia."""
        div = make_html("TAR Lombardia n. 999/2021", "Sentenza TAR Milano")
        result = scraper._parse_massima(div)

        assert result is not None
        assert result['numero'] == "999"
        assert result['anno'] == "2021"

    def test_parse_corte_conti(self, scraper, make_html):
        """Test parsing Corte conti."""
        div = make_html("Corte conti n. 50/2020", "Sentenza contabile")
        result = scraper._parse_massima(div)

        assert result is not None
        assert result['autorita'] is not None
        assert result['numero'] == "50"
        assert result['anno'] == "2020"

    def test_parse_corte_appello(self, scraper, make_html):
        """Test parsing App. (Corte d'Appello)."""
        div = make_html("App. n. 300/2019", "Sentenza d'appello")
        result = scraper._parse_massima(div)

        assert result is not None
        assert result['numero'] == "300"
        assert result['anno'] == "2019"

    def test_parse_tribunale(self, scraper, make_html):
        """Test parsing Trib."""
        div = make_html("Trib. n. 150/2021", "Sentenza di primo grado")
        result = scraper._parse_massima(div)

        assert result is not None
        assert result['numero'] == "150"
        assert result['anno'] == "2021"

    def test_parse_cgue(self, scraper, make_html):
        """Test parsing CGUE (Corte di Giustizia UE)."""
        div = make_html("CGUE n. 123/2020", "Sentenza europea")
        result = scraper._parse_massima(div)

        assert result is not None
        assert result['numero'] == "123"
        assert result['anno'] == "2020"

    def test_parse_cedu(self, scraper, make_html):
        """Test parsing CEDU."""
        div = make_html("CEDU n. 456/2018", "Violazione art. 6")
        result = scraper._parse_massima(div)

        assert result is not None
        assert result['numero'] == "456"
        assert result['anno'] == "2018"

    def test_fallback_unknown_autorita(self, scraper, make_html):
        """Test fallback per autorita' sconosciuta."""
        div = make_html("Autorita' Sconosciuta n. 789/2021", "Testo")
        result = scraper._parse_massima(div)

        assert result is not None
        # Dovrebbe comunque estrarre numero/anno
        assert result['numero'] == "789"
        assert result['anno'] == "2021"
        # Autorita' sconosciuta: il fallback estrae cosa c'e' prima di "n."
        # Puo' essere None se non matcha nessun pattern
        # L'importante e' che il parsing non fallisca completamente


@pytest.mark.integration
class TestBrocardiRelazioni:
    """Test estrazione Relazioni storiche (Costituzione e Codice Civile)."""

    @pytest.mark.asyncio
    async def test_relazione_costituzione(self, scraper):
        """
        Art. 1 Costituzione deve avere la Relazione al Progetto della Costituzione
        di Meuccio Ruini (1947).
        """
        norma = Norma(tipo_atto="costituzione")
        nv = NormaVisitata(norma=norma, numero_articolo="1")

        position, info, url = await scraper.get_info(nv)

        # Deve avere RelazioneCostituzione
        assert "RelazioneCostituzione" in info, "RelazioneCostituzione non trovata per Art. 1 Cost."

        rel = info["RelazioneCostituzione"]
        assert rel["titolo"] == "Relazione al Progetto della Costituzione"
        assert rel["autore"] == "Meuccio Ruini"
        assert rel["anno"] == 1947
        assert len(rel["testo"]) > 100, "Testo Relazione troppo corto"
        assert "Repubblica" in rel["testo"] or "democratica" in rel["testo"].lower()

    @pytest.mark.asyncio
    async def test_relazione_costituzione_multiple_articles(self, scraper):
        """
        Verifica che la Relazione sia estratta per diversi articoli della Costituzione.
        """
        import asyncio

        norma = Norma(tipo_atto="costituzione")
        articles = ["1", "48", "75"]

        async def fetch(art):
            nv = NormaVisitata(norma=norma, numero_articolo=art)
            return art, await scraper.get_info(nv)

        results = await asyncio.gather(*[fetch(art) for art in articles])

        for art, (position, info, url) in results:
            # Ogni articolo della Costituzione dovrebbe avere la Relazione
            assert "RelazioneCostituzione" in info, f"RelazioneCostituzione mancante per Art. {art} Cost."

    @pytest.mark.asyncio
    async def test_relazione_guardasigilli_codice_civile(self, scraper):
        """
        Art. 1453 CC (risoluzione contratto) deve avere la Relazione del Guardasigilli
        al Codice Civile (1942).
        """
        norma = Norma(tipo_atto="codice civile")
        nv = NormaVisitata(norma=norma, numero_articolo="1453")

        position, info, url = await scraper.get_info(nv)

        # Deve avere Relazioni (caricata via AJAX)
        assert "Relazioni" in info, "Relazioni (Guardasigilli) non trovate per Art. 1453 CC"
        assert len(info["Relazioni"]) > 0, "Nessuna Relazione trovata"

        rel = info["Relazioni"][0]
        assert "Codice Civile" in rel["titolo"]
        assert len(rel["testo"]) > 50, "Testo Relazione troppo corto"
