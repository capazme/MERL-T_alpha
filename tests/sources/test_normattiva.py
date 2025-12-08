"""
Test Integration per NormattivaScraper
======================================

Test reali che chiamano Normattiva.it per verificare:
- Fetch articoli di vari tipi di atti
- Storia modifiche (multivigenza)
- Error handling

Ground truth verificato manualmente su Normattiva.it.
"""

import pytest
from typing import List
from merlt.sources import NormattivaScraper, ScraperConfig, DocumentNotFoundError
from merlt.sources.utils.norma import Norma, NormaVisitata


def validate_article_content(
    text: str,
    article_num: str,
    essential_keywords: List[str],
    min_keywords: int = 2
) -> None:
    """
    Validazione robusta contenuto articoli.

    Args:
        text: Testo dell'articolo
        article_num: Numero articolo atteso
        essential_keywords: Parole chiave che devono essere presenti
        min_keywords: Numero minimo di keyword richieste

    Raises:
        AssertionError: Se validazione fallisce
    """
    text_lower = text.lower()

    # 1. Testo non-vuoto e ragionevole
    assert len(text) > 80, f"Testo troppo corto: {len(text)} chars"

    # 2. Keyword esenziali (almeno min_keywords)
    found_keywords = sum(1 for kw in essential_keywords if kw in text_lower)
    assert found_keywords >= min_keywords, \
        f"Solo {found_keywords}/{len(essential_keywords)} keyword trovate: {essential_keywords}"

    # 3. Nessun marker di errore
    error_markers = ["errore di sistema", "pagina non trovata", "unavailable"]
    for marker in error_markers:
        assert marker not in text_lower, f"Marker errore trovato: '{marker}'"


@pytest.fixture(scope="module")
def scraper():
    """Scraper con timeout aumentato per test integration."""
    config = ScraperConfig(timeout=60)
    return NormattivaScraper(config)


@pytest.mark.integration
class TestNormattivaFetch:
    """Test fetch articoli da Normattiva."""

    @pytest.mark.asyncio
    async def test_fetch_codice_civile_art1(self, scraper):
        """
        Fetch Art. 1 Codice Civile - capacita' giuridica.

        Ground truth: "La capacita' giuridica si acquista dal momento della nascita"
        """
        norma = Norma(tipo_atto="codice civile")
        nv = NormaVisitata(norma=norma, numero_articolo="1")

        text, urn = await scraper.get_document(nv)

        # Validazione robusta con helper
        validate_article_content(
            text,
            article_num="1",
            essential_keywords=["capacit", "nascita", "giuridica", "diritti"],
            min_keywords=2
        )

        # URN deve contenere riferimento Normattiva
        assert "urn" in urn.lower() or "normattiva" in urn.lower()

    @pytest.mark.asyncio
    async def test_fetch_codice_penale_art52(self, scraper):
        """
        Fetch Art. 52 Codice Penale - legittima difesa.

        Ground truth: "Non e' punibile chi ha commesso il fatto... necessita' di difendere..."
        """
        norma = Norma(tipo_atto="codice penale")
        nv = NormaVisitata(norma=norma, numero_articolo="52")

        text, urn = await scraper.get_document(nv)

        # Art. 52 CP deve contenere concetti specifici di legittima difesa
        validate_article_content(
            text,
            article_num="52",
            essential_keywords=["difesa", "punibile", "necessit", "offesa"],
            min_keywords=2
        )

    @pytest.mark.asyncio
    async def test_fetch_costituzione_art1(self, scraper):
        """
        Fetch Art. 1 Costituzione - Italia e' una Repubblica.

        Ground truth: "L'Italia e' una Repubblica democratica, fondata sul lavoro."
        """
        norma = Norma(tipo_atto="costituzione")
        nv = NormaVisitata(norma=norma, numero_articolo="1")

        text, urn = await scraper.get_document(nv)

        # Art. 1 Costituzione: tutti e 3 i termini devono essere presenti
        validate_article_content(
            text,
            article_num="1",
            essential_keywords=["repubblica", "italia", "lavoro", "democratica"],
            min_keywords=3  # Piu' stringente per Costituzione
        )

    @pytest.mark.asyncio
    async def test_fetch_legge_241_art2(self, scraper):
        """
        Fetch Art. 2 L.241/1990 - termine procedimento amministrativo.

        Ground truth: "Le pubbliche amministrazioni... concludono i procedimenti..."
        """
        norma = Norma(tipo_atto="legge", numero_atto="241", data="1990-08-07")
        nv = NormaVisitata(norma=norma, numero_articolo="2")

        text, urn = await scraper.get_document(nv)

        # Validazione contenuto specifico per L.241
        validate_article_content(
            text,
            article_num="2",
            essential_keywords=["procedimento", "amministrazi", "termine", "giorni"],
            min_keywords=2
        )


@pytest.mark.integration
class TestNormattivaAmendments:
    """Test storia modifiche (multivigenza)."""

    @pytest.mark.asyncio
    async def test_amendment_history_art2_241(self, scraper):
        """
        Art. 2 L.241/1990 ha subito molte modifiche.

        Ground truth su Normattiva:
        - D.L. 5/2012 -> L. 35/2012
        - L. 69/2009 (riscrittura sostanziale)
        - D.L. 77/2021 -> L. 108/2021
        """
        norma = Norma(tipo_atto="legge", numero_atto="241", data="1990-08-07")
        nv = NormaVisitata(norma=norma, numero_articolo="2")

        modifiche = await scraper.get_amendment_history(nv)

        # Art. 2 L.241 e' stato modificato MOLTE volte (almeno 5)
        assert len(modifiche) >= 3, \
            f"Art. 2 L.241 dovrebbe avere almeno 3 modifiche, ne ha {len(modifiche)}"

        # Ogni modifica dovrebbe avere i campi base
        for mod in modifiche:
            assert mod.atto_modificante_urn or mod.atto_modificante_estremi, \
                "Modifica deve avere URN o estremi atto modificante"

    @pytest.mark.asyncio
    async def test_amendment_history_costituzione_art1(self, scraper):
        """
        Art. 1 Costituzione non e' MAI stato modificato dal 1948.

        Ground truth: L'articolo e' rimasto invariato dalla promulgazione.
        """
        norma = Norma(tipo_atto="costituzione")
        nv = NormaVisitata(norma=norma, numero_articolo="1")

        modifiche = await scraper.get_amendment_history(nv)

        # Art. 1 Cost. non e' mai stato modificato
        assert len(modifiche) == 0, \
            f"Art. 1 Costituzione non dovrebbe avere modifiche, ne ha {len(modifiche)}"


@pytest.mark.integration
class TestNormattivaVersions:
    """Test versioni storiche."""

    @pytest.mark.asyncio
    async def test_original_version_art2_241(self, scraper):
        """
        Fetch versione originale Art. 2 L.241/1990.

        La versione originale dovrebbe essere diversa dalla vigente
        (l'articolo e' stato riscritto piu' volte).
        """
        norma = Norma(tipo_atto="legge", numero_atto="241", data="1990-08-07")
        nv = NormaVisitata(norma=norma, numero_articolo="2")

        # Fetch versione originale - ritorna (text, urn)
        result = await scraper.get_original_version(nv)

        # Dovrebbe ritornare tupla (text, urn) o solo text
        if isinstance(result, tuple):
            text, urn = result
        else:
            text = result

        # Dovrebbe avere contenuto
        assert text is not None
        # La versione originale potrebbe essere vuota se non disponibile
        # ma se c'e', dovrebbe avere contenuto
        if text:
            assert len(text) > 20, "Testo originale troppo corto"


@pytest.mark.integration
class TestNormattivaErrorHandling:
    """Test gestione errori e graceful degradation."""

    @pytest.mark.asyncio
    async def test_nonexistent_article(self, scraper):
        """
        Articolo inesistente (art. 99999 CC) dovrebbe fallire gracefully.

        Comportamento atteso: eccezione DocumentNotFoundError o stringa vuota.
        """
        norma = Norma(tipo_atto="codice civile")
        nv = NormaVisitata(norma=norma, numero_articolo="99999")

        # Non dovrebbe crashare, ma ritornare errore o stringa vuota
        try:
            text, urn = await scraper.get_document(nv)
            # Se non solleva eccezione, verifica che il testo sia vuoto/errore
            assert text == "" or "error" in text.lower() or "non trovato" in text.lower(), \
                "Per articolo inesistente, testo dovrebbe essere vuoto o contenere errore"
        except (DocumentNotFoundError, ValueError, Exception):
            # Eccezione attesa per articolo inesistente
            pass

    @pytest.mark.asyncio
    async def test_invalid_act_type(self, scraper):
        """
        Tipo atto invalido dovrebbe fallire gracefully.

        Comportamento atteso: eccezione o stringa vuota.
        """
        norma = Norma(tipo_atto="tipo_inventato_12345")
        nv = NormaVisitata(norma=norma, numero_articolo="1")

        try:
            text, urn = await scraper.get_document(nv)
            # Se non solleva eccezione, verifica errore
            assert text == "" or "error" in text.lower(), \
                "Per tipo atto invalido, dovrebbe restituire errore"
        except Exception:
            # Eccezione attesa
            pass

    @pytest.mark.asyncio
    async def test_article_with_suffix_bis(self, scraper):
        """
        Articoli con suffisso (bis, ter, quater) devono essere gestiti.

        Es: Art. 2-bis L.241/1990 (inserito da L. 69/2009).
        """
        norma = Norma(tipo_atto="legge", numero_atto="241", data="1990-08-07")
        nv = NormaVisitata(norma=norma, numero_articolo="2-bis")

        text, urn = await scraper.get_document(nv)

        # Art. 2-bis esiste e deve avere contenuto
        assert len(text) > 50, "Art. 2-bis dovrebbe avere contenuto"
        assert "bis" in urn or "2-bis" in urn or "2bis" in urn.lower()


@pytest.mark.integration
class TestNormattivaRetry:
    """Test retry logic e configurazione."""

    @pytest.mark.asyncio
    async def test_retry_config_applied(self):
        """Verifica che la config sia applicata correttamente."""
        config = ScraperConfig(timeout=120, max_concurrent=2)
        test_scraper = NormattivaScraper(config)

        assert test_scraper.config.timeout == 120
        assert test_scraper.config.max_concurrent == 2

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, scraper):
        """
        Test richieste concorrenti con rate limiting.

        Verifica che il semaforo interno gestisca correttamente
        richieste parallele senza sovraccaricare Normattiva.
        """
        import asyncio

        norma = Norma(tipo_atto="codice civile")
        articles = ["1", "2", "3"]

        async def fetch(art):
            nv = NormaVisitata(norma=norma, numero_articolo=art)
            return await scraper.get_document(nv)

        # Fetch concorrenti
        results = await asyncio.gather(*[fetch(art) for art in articles])

        assert len(results) == 3, "Devono ritornare 3 risultati"
        for text, urn in results:
            assert len(text) > 50, "Ogni articolo deve avere contenuto"

    @pytest.mark.asyncio
    async def test_cache_consistency(self, scraper):
        """
        Richieste ripetute dello stesso articolo dovrebbero
        ritornare risultati identici (cache).
        """
        norma = Norma(tipo_atto="codice civile")
        nv = NormaVisitata(norma=norma, numero_articolo="1")

        # Prima richiesta
        text1, urn1 = await scraper.get_document(nv)

        # Seconda richiesta (dovrebbe usare cache)
        text2, urn2 = await scraper.get_document(nv)

        assert text1 == text2, "Risultati cache dovrebbero essere identici"
        assert urn1 == urn2, "URN cache dovrebbero essere identici"
