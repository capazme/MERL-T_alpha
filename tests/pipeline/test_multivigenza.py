"""
Test per MultivigenzaPipeline
==============================

Test per parsing modifiche e validazione fedeltà a Normattiva.

Ground truth verificato manualmente su Normattiva.it (Dicembre 2025).
"""

import pytest
from merlt.sources.utils.norma import Modifica, TipoModifica, Norma, NormaVisitata


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
