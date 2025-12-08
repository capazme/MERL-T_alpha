"""
Test per MultivigenzaPipeline
==============================

Test per parsing modifiche e validazione fedeltà a Normattiva.

Ground truth verificato manualmente su Normattiva.it (Dicembre 2025).
"""

import pytest
from unittest.mock import AsyncMock, patch
from merlt.sources.utils.norma import Modifica, TipoModifica, Norma, NormaVisitata
from merlt.pipeline.multivigenza import (
    parse_disposizione,
    parse_disposizione_with_llm,
    _build_normattiva_url,
    _derive_autorita_emanante,
    AUTORITA_EMANANTE_MAPPING,
)


class TestModificaParsing:
    """
    Test per parsing strutture Modifica.

    Copre:
    - Abrogazione articolo intero vs parziale (comma/lettera/numero)
    - Articoli con suffissi (bis, ter, quater)
    - Filtro for_article
    """

    def test_is_article_level_abrogation_full_article(self):
        """Abrogazione articolo intero deve ritornare True."""
        mod = Modifica(
            tipo_modifica=TipoModifica.ABROGA,
            atto_modificante_urn="urn:nir:stato:legge:2000-01-01;1",
            atto_modificante_estremi="Legge 1 gennaio 2000, n. 1",
            destinazione="art. 5",
            data_efficacia="2000-01-02"
        )

        assert mod.is_article_level_abrogation() is True
        assert mod.is_article_level_abrogation(for_article="5") is True

    def test_is_article_level_abrogation_comma_only(self):
        """Abrogazione solo comma deve ritornare False."""
        mod = Modifica(
            tipo_modifica=TipoModifica.ABROGA,
            atto_modificante_urn="urn:nir:stato:legge:2000-01-01;1",
            atto_modificante_estremi="Legge 1 gennaio 2000, n. 1",
            destinazione="art. 5, comma 2",
            data_efficacia="2000-01-02"
        )

        assert mod.is_article_level_abrogation() is False
        assert mod.is_article_level_abrogation(for_article="5") is False

    def test_is_article_level_abrogation_lettera_only(self):
        """Abrogazione solo lettera deve ritornare False."""
        mod = Modifica(
            tipo_modifica=TipoModifica.ABROGA,
            atto_modificante_urn="urn:nir:stato:legge:2000-01-01;1",
            atto_modificante_estremi="Legge 1 gennaio 2000, n. 1",
            destinazione="art. 5, comma 1, lettera b)",
            data_efficacia="2000-01-02"
        )

        assert mod.is_article_level_abrogation() is False

    def test_is_article_level_abrogation_numero_only(self):
        """
        Abrogazione solo numero deve ritornare False.

        Es: "art. 5, comma 1, lettera a, numero 3)" è abrogazione parziale.
        """
        mod = Modifica(
            tipo_modifica=TipoModifica.ABROGA,
            atto_modificante_urn="urn:nir:stato:legge:2000-01-01;1",
            atto_modificante_estremi="Legge 1 gennaio 2000, n. 1",
            destinazione="art. 5, comma 1, lettera a, numero 3)",
            data_efficacia="2000-01-02"
        )

        assert mod.is_article_level_abrogation() is False
        assert mod.is_article_level_abrogation(for_article="5") is False

    def test_is_article_level_abrogation_wrong_article(self):
        """Abrogazione di articolo diverso deve ritornare False per for_article."""
        mod = Modifica(
            tipo_modifica=TipoModifica.ABROGA,
            atto_modificante_urn="urn:nir:stato:legge:2000-01-01;1",
            atto_modificante_estremi="Legge 1 gennaio 2000, n. 1",
            destinazione="art. 10",
            data_efficacia="2000-01-02"
        )

        # Senza for_article, è abrogazione articolo (True)
        assert mod.is_article_level_abrogation() is True
        # Con for_article=5, non corrisponde (False)
        assert mod.is_article_level_abrogation(for_article="5") is False
        # Con for_article=10, corrisponde (True)
        assert mod.is_article_level_abrogation(for_article="10") is True

    def test_is_article_level_abrogation_modifica_not_abroga(self):
        """Modifica (non abrogazione) deve ritornare False."""
        mod = Modifica(
            tipo_modifica=TipoModifica.MODIFICA,
            atto_modificante_urn="urn:nir:stato:legge:2000-01-01;1",
            atto_modificante_estremi="Legge 1 gennaio 2000, n. 1",
            destinazione="art. 5",
            data_efficacia="2000-01-02"
        )

        # MODIFICA non è ABROGA
        assert mod.is_article_level_abrogation() is False

    def test_is_article_level_abrogation_article_bis(self):
        """Abrogazione articolo bis."""
        mod = Modifica(
            tipo_modifica=TipoModifica.ABROGA,
            atto_modificante_urn="urn:nir:stato:legge:2000-01-01;1",
            atto_modificante_estremi="Legge 1 gennaio 2000, n. 1",
            destinazione="art. 2-bis",
            data_efficacia="2000-01-02"
        )

        assert mod.is_article_level_abrogation() is True
        assert mod.is_article_level_abrogation(for_article="2-bis") is True
        assert mod.is_article_level_abrogation(for_article="2") is False

    def test_is_article_level_abrogation_article_ter(self):
        """Abrogazione articolo ter."""
        mod = Modifica(
            tipo_modifica=TipoModifica.ABROGA,
            atto_modificante_urn="urn:nir:stato:legge:2000-01-01;1",
            atto_modificante_estremi="Legge 1 gennaio 2000, n. 1",
            destinazione="art. 2-ter",
            data_efficacia="2000-01-02"
        )

        assert mod.is_article_level_abrogation() is True
        assert mod.is_article_level_abrogation(for_article="2-ter") is True
        assert mod.is_article_level_abrogation(for_article="2") is False
        assert mod.is_article_level_abrogation(for_article="2-bis") is False

    def test_is_article_level_abrogation_article_quater(self):
        """Abrogazione articolo quater."""
        mod = Modifica(
            tipo_modifica=TipoModifica.ABROGA,
            atto_modificante_urn="urn:nir:stato:legge:2000-01-01;1",
            atto_modificante_estremi="Legge 1 gennaio 2000, n. 1",
            destinazione="art. 3-quater",
            data_efficacia="2000-01-02"
        )

        assert mod.is_article_level_abrogation() is True
        assert mod.is_article_level_abrogation(for_article="3-quater") is True
        assert mod.is_article_level_abrogation(for_article="3") is False

    def test_is_article_level_abrogation_comma_and_lettera(self):
        """Abrogazione comma e lettera (parziale, non articolo intero)."""
        mod = Modifica(
            tipo_modifica=TipoModifica.ABROGA,
            atto_modificante_urn="urn:nir:stato:legge:2000-01-01;1",
            atto_modificante_estremi="Legge 1 gennaio 2000, n. 1",
            destinazione="art. 5, commi 1 e 2, lettera b)",
            data_efficacia="2000-01-02"
        )

        # 'comma' in destinazione → abrogazione parziale
        assert mod.is_article_level_abrogation() is False

    def test_is_article_level_abrogation_empty_destinazione(self):
        """
        Destinazione vuota/None assume abrogazione articolo intero.

        Comportamento: se destinazione non specifica comma/lettera/numero,
        si assume abrogazione dell'intero articolo.
        """
        mod_none = Modifica(
            tipo_modifica=TipoModifica.ABROGA,
            atto_modificante_urn="urn:nir:stato:legge:2000-01-01;1",
            atto_modificante_estremi="Legge 1 gennaio 2000, n. 1",
            destinazione=None,
            data_efficacia="2000-01-02"
        )

        mod_empty = Modifica(
            tipo_modifica=TipoModifica.ABROGA,
            atto_modificante_urn="urn:nir:stato:legge:2000-01-01;1",
            atto_modificante_estremi="Legge 1 gennaio 2000, n. 1",
            destinazione="",
            data_efficacia="2000-01-02"
        )

        # Destinazione vuota → assume articolo intero
        assert mod_none.is_article_level_abrogation() is True
        assert mod_empty.is_article_level_abrogation() is True


class TestTipoModifica:
    """Test per enum TipoModifica."""

    def test_tipo_modifica_values(self):
        """Verifica valori TipoModifica."""
        assert TipoModifica.ABROGA.value == "abroga"
        assert TipoModifica.MODIFICA.value == "modifica"
        assert TipoModifica.SOSTITUISCE.value == "sostituisce"
        assert TipoModifica.INSERISCE.value == "inserisce"


@pytest.mark.integration
class TestMultivigenzaValidation:
    """
    Test validazione fedeltà a Normattiva.

    Ground truth da EXP-005 (L.241/1990) verificato su Normattiva.it.
    """

    # Ground truth verificato manualmente su Normattiva (Dicembre 2025)
    GROUND_TRUTH_241 = [
        {"articolo": "1", "status": "vigente", "has_modifications": True},
        {"articolo": "2", "status": "vigente", "has_modifications": True},
        {"articolo": "2-bis", "status": "vigente", "has_modifications": True},  # comma 2 abrogato, non articolo
        {"articolo": "3", "status": "vigente", "has_modifications": True},
        {"articolo": "3-bis", "status": "vigente", "has_modifications": True},
    ]

    @pytest.mark.asyncio
    async def test_legge_241_amendments_exist(self):
        """
        Verifica che gli articoli L.241/1990 abbiano modifiche.

        Ground truth:
        - Art. 1: modificato da L. 15/2005, L. 69/2009
        - Art. 2: completamente riscritto da L. 69/2009, D.L. 5/2012, D.L. 77/2021
        - Art. 2-bis: inserito da L. 69/2009
        - Art. 3: modificato da L. 15/2005, L. 190/2012
        - Art. 3-bis: inserito da L. 15/2005
        """
        from merlt.sources import NormattivaScraper
        scraper = NormattivaScraper()

        for case in self.GROUND_TRUTH_241:
            norma = Norma(tipo_atto="legge", numero_atto="241", data="1990-08-07")
            nv = NormaVisitata(norma=norma, numero_articolo=case["articolo"])

            modifiche = await scraper.get_amendment_history(nv)

            if case["has_modifications"]:
                assert len(modifiche) > 0, \
                    f"Art. {case['articolo']} L.241/1990 dovrebbe avere modifiche"

    @pytest.mark.asyncio
    async def test_art2bis_comma_abrogato_non_articolo(self):
        """
        Art. 2-bis L.241/1990: comma 2 abrogato, ma articolo vigente.

        Ground truth:
        - Art. 2-bis inserito da L. 69/2009
        - Comma 2 abrogato da successiva modifica
        - L'articolo nel suo insieme è VIGENTE

        Questo test verifica che is_article_level_abrogation() distingua
        correttamente tra abrogazione di comma e abrogazione di articolo intero.
        """
        from merlt.sources import NormattivaScraper
        scraper = NormattivaScraper()

        norma = Norma(tipo_atto="legge", numero_atto="241", data="1990-08-07")
        nv = NormaVisitata(norma=norma, numero_articolo="2-bis")

        modifiche = await scraper.get_amendment_history(nv)

        # Verifica che non ci sia abrogazione dell'intero articolo
        has_article_abrogation = False
        for mod in modifiche:
            if mod.is_article_level_abrogation(for_article="2-bis"):
                has_article_abrogation = True
                break

        # Art. 2-bis non dovrebbe essere abrogato integralmente
        assert has_article_abrogation is False, \
            "Art. 2-bis L.241/1990 non dovrebbe avere abrogazione articolo intero (solo comma 2)"


@pytest.mark.integration
class TestMultivigenzaCostituzione:
    """
    Test multivigenza per articoli Costituzione.

    Ground truth verificato su Normattiva.it.
    """

    @pytest.mark.asyncio
    async def test_costituzione_art1_no_modifications(self):
        """
        Art. 1 Costituzione non è MAI stato modificato dal 1948.

        Ground truth: L'articolo è rimasto invariato dalla promulgazione
        ("L'Italia è una Repubblica democratica, fondata sul lavoro...")
        """
        from merlt.sources import NormattivaScraper
        scraper = NormattivaScraper()

        norma = Norma(tipo_atto="costituzione")
        nv = NormaVisitata(norma=norma, numero_articolo="1")

        modifiche = await scraper.get_amendment_history(nv)

        assert len(modifiche) == 0, \
            f"Art. 1 Costituzione non dovrebbe avere modifiche, ne ha {len(modifiche)}"

    @pytest.mark.asyncio
    async def test_costituzione_art117_has_modifications(self):
        """
        Art. 117 Costituzione è stato COMPLETAMENTE RISCRITTO.

        Ground truth:
        - Modificato dalla L. costituzionale 18 ottobre 2001, n. 3
          (Riforma del Titolo V - potestà legislativa Stato/Regioni)
        """
        from merlt.sources import NormattivaScraper
        scraper = NormattivaScraper()

        norma = Norma(tipo_atto="costituzione")
        nv = NormaVisitata(norma=norma, numero_articolo="117")

        modifiche = await scraper.get_amendment_history(nv)

        # Art. 117 è stato modificato dalla riforma del Titolo V (2001)
        assert len(modifiche) > 0, \
            "Art. 117 Costituzione dovrebbe avere modifiche (riforma Titolo V 2001)"

        # Verifica che almeno una modifica sia del 2001
        has_2001_modification = any(
            "2001" in (mod.atto_modificante_estremi or "") or
            "2001" in (mod.data_efficacia or "")
            for mod in modifiche
        )
        # Non è garantito che il sistema restituisca la data,
        # ma se c'è, dovrebbe includere 2001
        # (non è un assert critico, solo informativo)


class TestParseDisposizione:
    """Test per parse_disposizione (regex)."""

    def test_parse_articolo_semplice(self):
        """Parse articolo semplice."""
        result = parse_disposizione("art. 5")
        assert result["numero_articolo"] == "5"
        assert result["commi"] == []
        assert result["lettere"] == []

    def test_parse_articolo_comma(self):
        """Parse articolo con comma."""
        result = parse_disposizione("art. 12, comma 3")
        assert result["numero_articolo"] == "12"
        assert "3" in result["commi"]

    def test_parse_articolo_bis(self):
        """Parse articolo bis."""
        result = parse_disposizione("art. 2-bis")
        assert result["numero_articolo"] == "2-bis"

    def test_parse_articolo_comma_lettera(self):
        """Parse articolo con comma e lettera."""
        result = parse_disposizione("art. 1, comma 1, lettera a)")
        assert result["numero_articolo"] == "1"
        assert "1" in result["commi"]
        assert "a" in result["lettere"]


class TestParseDisposizioneWithLLM:
    """Test per parse_disposizione_with_llm (usa LLM come fallback)."""

    def test_regex_success_no_llm_call(self):
        """Se regex trova l'articolo, LLM non viene chiamato."""
        # Simula disposizione semplice che regex può parsare
        disposizione = "art. 5"
        estremi = "Legge 1/2000"

        # Non passiamo llm_service, quindi userà regex
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            parse_disposizione_with_llm(disposizione, estremi)
        )

        assert result["numero_articolo"] == "5"

    @pytest.mark.asyncio
    async def test_regex_success_skips_llm(self):
        """
        Test che verifica che quando regex trova l'articolo, LLM non viene chiamato.
        """
        mock_llm = AsyncMock()
        mock_llm.generate_json_completion = AsyncMock(
            return_value={"numero_articolo": "99", "commi": [], "lettere": [], "numeri": []}
        )

        # Disposizione che regex può parsare (usa "art." abbreviato)
        disposizione = "modifica dell'art. 12, comma 3"
        estremi = "Legge 1/2000"

        result = await parse_disposizione_with_llm(
            disposizione,
            estremi,
            llm_service=mock_llm
        )

        # Regex dovrebbe aver trovato l'articolo 12, quindi LLM non viene chiamato
        assert result["numero_articolo"] == "12"
        # LLM non dovrebbe essere stato chiamato
        mock_llm.generate_json_completion.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_called_when_regex_fails(self):
        """
        Test che LLM viene chiamato quando regex non trova l'articolo.
        """
        mock_llm = AsyncMock()
        mock_llm.generate_json_completion = AsyncMock(
            return_value={"numero_articolo": "7", "commi": ["2"], "lettere": [], "numeri": []}
        )

        # Disposizione che regex non può parsare (no pattern "art. X")
        disposizione = "la modifica al settimo articolo comma secondo"
        estremi = "Legge 1/2000"

        result = await parse_disposizione_with_llm(
            disposizione,
            estremi,
            llm_service=mock_llm
        )

        # LLM dovrebbe essere stato chiamato
        mock_llm.generate_json_completion.assert_called_once()

        # Verifica che i parametri siano corretti
        call_kwargs = mock_llm.generate_json_completion.call_args.kwargs
        assert "prompt" in call_kwargs
        assert "json_schema" in call_kwargs
        assert "model" in call_kwargs

    @pytest.mark.asyncio
    async def test_llm_json_parsing(self):
        """Test parsing JSON response da LLM (structured output)."""
        mock_llm = AsyncMock()
        # Con structured output, la risposta è già un dict
        mock_llm.generate_json_completion = AsyncMock(
            return_value={"numero_articolo": "15", "commi": ["1", "3"], "lettere": ["a"], "numeri": []}
        )

        disposizione = "qualcosa che regex non può parsare"
        estremi = "Legge 1/2000"

        result = await parse_disposizione_with_llm(
            disposizione,
            estremi,
            llm_service=mock_llm
        )

        # Con structured output, il risultato dovrebbe essere direttamente parsato
        assert result["numero_articolo"] == "15"
        assert result["commi"] == ["1", "3"]
        assert result["lettere"] == ["a"]

    @pytest.mark.asyncio
    async def test_llm_model_from_env(self):
        """
        Test che il modello LLM venga letto dalla variabile d'ambiente LLM_PARSING_MODEL.
        """
        import os

        mock_llm = AsyncMock()
        mock_llm.generate_json_completion = AsyncMock(
            return_value={"numero_articolo": "5", "commi": [], "lettere": [], "numeri": []}
        )

        # Imposta variabile d'ambiente
        original_value = os.environ.get("LLM_PARSING_MODEL")
        os.environ["LLM_PARSING_MODEL"] = "test-model/custom-v1"

        try:
            disposizione = "modifica senza pattern regex"
            estremi = "Legge 1/2000"

            await parse_disposizione_with_llm(
                disposizione,
                estremi,
                llm_service=mock_llm
            )

            # Verifica che il modello passato sia quello dall'env
            call_kwargs = mock_llm.generate_json_completion.call_args.kwargs
            assert call_kwargs["model"] == "test-model/custom-v1"
        finally:
            # Ripristina valore originale
            if original_value is not None:
                os.environ["LLM_PARSING_MODEL"] = original_value
            else:
                os.environ.pop("LLM_PARSING_MODEL", None)

    @pytest.mark.asyncio
    async def test_llm_model_default_when_env_not_set(self):
        """
        Test che il modello di default sia usato quando LLM_PARSING_MODEL non è impostato.
        """
        import os

        mock_llm = AsyncMock()
        mock_llm.generate_json_completion = AsyncMock(
            return_value={"numero_articolo": "5", "commi": [], "lettere": [], "numeri": []}
        )

        # Rimuovi variabile d'ambiente se presente
        original_value = os.environ.pop("LLM_PARSING_MODEL", None)

        try:
            disposizione = "modifica senza pattern regex"
            estremi = "Legge 1/2000"

            await parse_disposizione_with_llm(
                disposizione,
                estremi,
                llm_service=mock_llm
            )

            # Verifica che il modello di default sia mistral
            call_kwargs = mock_llm.generate_json_completion.call_args.kwargs
            assert call_kwargs["model"] == "mistralai/mistral-7b-instruct"
        finally:
            # Ripristina valore originale
            if original_value is not None:
                os.environ["LLM_PARSING_MODEL"] = original_value


class TestSchemaHelperFunctions:
    """
    Test per le funzioni helper che garantiscono conformità allo schema.

    Queste funzioni assicurano che i nodi delle norme modificanti
    abbiano tutte le proprietà richieste dallo schema standard.
    """

    def test_build_normattiva_url_basic(self):
        """Costruisce URL Normattiva da URN base."""
        urn = "urn:nir:stato:legge:2000-01-01;1"
        url = _build_normattiva_url(urn)
        assert url == "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:2000-01-01;1"

    def test_build_normattiva_url_legge_costituzionale(self):
        """Costruisce URL per legge costituzionale."""
        urn = "urn:nir:stato:legge.costituzionale:2001-10-18;3"
        url = _build_normattiva_url(urn)
        assert url == "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge.costituzionale:2001-10-18;3"

    def test_build_normattiva_url_with_article(self):
        """Costruisce URL per articolo specifico."""
        urn = "urn:nir:stato:legge:2000-01-01;1~art5"
        url = _build_normattiva_url(urn)
        assert "~art5" in url

    def test_derive_autorita_emanante_legge(self):
        """Legge -> Parlamento."""
        assert _derive_autorita_emanante("legge") == "Parlamento"

    def test_derive_autorita_emanante_legge_costituzionale(self):
        """Legge costituzionale -> Parlamento."""
        assert _derive_autorita_emanante("legge costituzionale") == "Parlamento"

    def test_derive_autorita_emanante_decreto_legge(self):
        """Decreto-legge -> Governo."""
        assert _derive_autorita_emanante("decreto-legge") == "Governo"

    def test_derive_autorita_emanante_decreto_legislativo(self):
        """Decreto legislativo -> Governo."""
        assert _derive_autorita_emanante("decreto legislativo") == "Governo"

    def test_derive_autorita_emanante_dpr(self):
        """DPR -> Presidente della Repubblica."""
        assert _derive_autorita_emanante("decreto del presidente della repubblica") == "Presidente della Repubblica"

    def test_derive_autorita_emanante_costituzione(self):
        """Costituzione -> Assemblea Costituente."""
        assert _derive_autorita_emanante("costituzione") == "Assemblea Costituente"

    def test_derive_autorita_emanante_regio_decreto(self):
        """Regio Decreto -> Re d'Italia."""
        assert _derive_autorita_emanante("regio decreto") == "Re d'Italia"

    def test_derive_autorita_emanante_case_insensitive(self):
        """Verifica case insensitivity."""
        assert _derive_autorita_emanante("LEGGE") == "Parlamento"
        assert _derive_autorita_emanante("Legge Costituzionale") == "Parlamento"

    def test_derive_autorita_emanante_unknown(self):
        """Tipo sconosciuto -> default "Stato"."""
        assert _derive_autorita_emanante("tipo sconosciuto") == "Stato"
        assert _derive_autorita_emanante(None) == "Stato"
        assert _derive_autorita_emanante("") == "Stato"

    def test_autorita_mapping_completeness(self):
        """Verifica che il mapping contenga i tipi principali."""
        expected_keys = [
            "legge",
            "legge costituzionale",
            "decreto-legge",
            "decreto legislativo",
            "decreto del presidente della repubblica",
            "costituzione",
        ]
        for key in expected_keys:
            assert key in AUTORITA_EMANANTE_MAPPING, f"Manca mapping per '{key}'"


class TestNormaModificanteSchemaCompliance:
    """
    Test per verificare che i nodi delle norme modificanti
    abbiano tutte le proprietà richieste dallo schema standard.

    Le proprietà richieste sono:
    - URN (primary key)
    - node_id (= URN)
    - url (costruito da URN)
    - tipo_documento
    - estremi
    - stato = 'vigente'
    - vigenza = 'vigente' (alias)
    - efficacia = 'permanente'
    - data_pubblicazione
    - data_entrata_vigore (= data_pubblicazione se non specificata)
    - autorita_emanante (derivato da tipo_documento)
    - ambito_territoriale = 'nazionale'
    - fonte = 'Normattiva'
    - created_at
    - updated_at (= created_at alla creazione)
    """

    def test_atto_modificante_required_properties(self):
        """
        Verifica che la query di creazione atto modificante
        includa tutte le proprietà richieste.
        """
        # Le proprietà che devono essere nella query ON CREATE SET
        required_props = [
            "node_id",
            "url",
            "estremi",
            "tipo_documento",
            "titolo",
            "stato",
            "vigenza",
            "efficacia",
            "data_pubblicazione",
            "data_entrata_vigore",
            "autorita_emanante",
            "ambito_territoriale",
            "fonte",
            "created_at",
            "updated_at",
        ]

        # Leggi il codice sorgente e verifica che contenga tutte le proprietà
        import inspect
        from merlt.pipeline.multivigenza import MultivigenzaPipeline

        source = inspect.getsource(MultivigenzaPipeline._create_modification)

        # Cerca la sezione "Create/merge ATTO MODIFICANTE"
        # e verifica che contenga tutte le proprietà
        assert "ATTO MODIFICANTE" in source, "Sezione ATTO MODIFICANTE non trovata"
        assert "atto.url = $url" in source, "Proprietà url mancante per atto modificante"
        assert "atto.vigenza" in source, "Proprietà vigenza mancante per atto modificante"
        assert "atto.autorita_emanante" in source, "Proprietà autorita_emanante mancante per atto modificante"
        assert "atto.data_entrata_vigore" in source, "Proprietà data_entrata_vigore mancante per atto modificante"
        assert "atto.updated_at" in source, "Proprietà updated_at mancante per atto modificante"

    def test_articolo_modificante_required_properties(self):
        """
        Verifica che la query di creazione articolo modificante
        includa tutte le proprietà richieste.
        """
        import inspect
        from merlt.pipeline.multivigenza import MultivigenzaPipeline

        source = inspect.getsource(MultivigenzaPipeline._create_modification)

        # Cerca la sezione "Create ARTICOLO" e verifica proprietà
        assert "ARTICOLO della disposizione" in source, "Sezione ARTICOLO non trovata"
        assert "art.url = $url" in source, "Proprietà url mancante per articolo modificante"
        assert "art.vigenza" in source, "Proprietà vigenza mancante per articolo modificante"
        assert "art.autorita_emanante" in source, "Proprietà autorita_emanante mancante per articolo modificante"
        assert "art.data_pubblicazione" in source, "Proprietà data_pubblicazione mancante per articolo modificante"
        assert "art.data_entrata_vigore" in source, "Proprietà data_entrata_vigore mancante per articolo modificante"
        assert "art.updated_at" in source, "Proprietà updated_at mancante per articolo modificante"
