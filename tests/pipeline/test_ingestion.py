"""
Test per IngestionPipelineV2
============================

Test unitari per le funzioni di normalizzazione e processamento.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock


class TestMassimaNormalization:
    """
    Test unitari per _normalize_massima().

    Verifica che tutte le autorità giudiziarie italiane ed europee
    siano correttamente mappate.
    """

    @pytest.fixture
    def pipeline(self):
        """
        Crea un'istanza minima della pipeline per testare _normalize_massima().
        """
        from merlt.pipeline.ingestion import IngestionPipelineV2

        # Mock delle dipendenze
        pipeline = IngestionPipelineV2.__new__(IngestionPipelineV2)
        pipeline.falkordb = MagicMock()
        pipeline.embedding_service = MagicMock()
        pipeline.normattiva = MagicMock()
        pipeline.brocardi = MagicMock()
        pipeline.bridge_table = MagicMock()
        pipeline.ai_service = MagicMock()
        return pipeline

    # === Corte Costituzionale ===

    def test_normalize_corte_costituzionale(self, pipeline):
        """Test normalizzazione Corte cost."""
        massima = {
            "autorita": "Corte cost.",
            "numero": "242",
            "anno": "2019",
            "massima": "La Corte dichiara l'illegittimita'..."
        }
        result = pipeline._normalize_massima(massima, 0)

        assert result["corte"] == "Corte Costituzionale"
        assert result["numero"] == "242/2019"
        assert "illegittimita" in result["estratto"]

    def test_normalize_c_cost(self, pipeline):
        """Test normalizzazione C. cost."""
        massima = {
            "autorita": "C. cost.",
            "numero": "1",
            "anno": "2021",
            "massima": "Sentenza costituzionale"
        }
        result = pipeline._normalize_massima(massima, 0)

        assert result["corte"] == "Corte Costituzionale"

    def test_normalize_corte_costituzionale_full(self, pipeline):
        """Test normalizzazione nome completo."""
        massima = {
            "autorita": "Corte Costituzionale",
            "numero": "50",
            "anno": "2020",
            "massima": "Test"
        }
        result = pipeline._normalize_massima(massima, 0)

        assert result["corte"] == "Corte Costituzionale"

    # === Cassazione ===

    def test_normalize_cassazione_civile(self, pipeline):
        """Test normalizzazione Cass. civ."""
        massima = {
            "autorita": "Cass. civ.",
            "numero": "36918",
            "anno": "2021",
            "massima": "Massima civile"
        }
        result = pipeline._normalize_massima(massima, 0)

        assert result["corte"] == "Cassazione civile"
        assert result["numero"] == "36918/2021"

    def test_normalize_cassazione_penale(self, pipeline):
        """Test normalizzazione Cass. pen."""
        massima = {
            "autorita": "Cass. pen.",
            "numero": "12345",
            "anno": "2020",
            "massima": "Massima penale"
        }
        result = pipeline._normalize_massima(massima, 0)

        assert result["corte"] == "Cassazione penale"

    def test_normalize_cassazione_sezioni_unite(self, pipeline):
        """Test normalizzazione Cass. sez. un."""
        massima = {
            "autorita": "Cass. sez. un.",
            "numero": "100",
            "anno": "2022",
            "massima": "Massima sezioni unite"
        }
        result = pipeline._normalize_massima(massima, 0)

        assert result["corte"] == "Cassazione Sezioni Unite"

    def test_normalize_cassazione_lavoro(self, pipeline):
        """Test normalizzazione Cass. lav."""
        massima = {
            "autorita": "Cass. lav.",
            "numero": "500",
            "anno": "2021",
            "massima": "Massima lavoro"
        }
        result = pipeline._normalize_massima(massima, 0)

        assert result["corte"] == "Cassazione lavoro"

    # === Giustizia Amministrativa ===

    def test_normalize_tar_lazio(self, pipeline):
        """Test normalizzazione TAR Lazio."""
        massima = {
            "autorita": "TAR Lazio",
            "numero": "1234",
            "anno": "2022",
            "massima": "Sentenza TAR"
        }
        result = pipeline._normalize_massima(massima, 0)

        # TAR mantiene la regione
        assert "TAR" in result["corte"]
        assert result["numero"] == "1234/2022"

    def test_normalize_tar_lombardia(self, pipeline):
        """Test normalizzazione TAR Lombardia."""
        massima = {
            "autorita": "TAR Lombardia",
            "numero": "999",
            "anno": "2021",
            "massima": "Sentenza TAR Milano"
        }
        result = pipeline._normalize_massima(massima, 0)

        assert "TAR" in result["corte"]

    def test_normalize_consiglio_stato(self, pipeline):
        """Test normalizzazione Cons. St."""
        massima = {
            "autorita": "Cons. St.",
            "numero": "5678",
            "anno": "2023",
            "massima": "Decisione amministrativa"
        }
        result = pipeline._normalize_massima(massima, 0)

        assert result["corte"] == "Consiglio di Stato"

    # === Altre Corti ===

    def test_normalize_corte_conti(self, pipeline):
        """Test normalizzazione Corte conti."""
        massima = {
            "autorita": "Corte conti",
            "numero": "50",
            "anno": "2020",
            "massima": "Sentenza contabile"
        }
        result = pipeline._normalize_massima(massima, 0)

        assert result["corte"] == "Corte dei Conti"

    def test_normalize_corte_appello(self, pipeline):
        """Test normalizzazione App."""
        massima = {
            "autorita": "App.",
            "numero": "300",
            "anno": "2019",
            "massima": "Sentenza d'appello"
        }
        result = pipeline._normalize_massima(massima, 0)

        assert result["corte"] == "Corte d'Appello"

    def test_normalize_tribunale(self, pipeline):
        """Test normalizzazione Trib."""
        massima = {
            "autorita": "Trib.",
            "numero": "150",
            "anno": "2021",
            "massima": "Sentenza di primo grado"
        }
        result = pipeline._normalize_massima(massima, 0)

        assert result["corte"] == "Tribunale"

    # === Corti Europee ===

    def test_normalize_cgue(self, pipeline):
        """Test normalizzazione CGUE."""
        massima = {
            "autorita": "CGUE",
            "numero": "123",
            "anno": "2020",
            "massima": "Sentenza europea"
        }
        result = pipeline._normalize_massima(massima, 0)

        assert result["corte"] == "CGUE"

    def test_normalize_cedu(self, pipeline):
        """Test normalizzazione CEDU."""
        massima = {
            "autorita": "CEDU",
            "numero": "456",
            "anno": "2018",
            "massima": "Violazione art. 6"
        }
        result = pipeline._normalize_massima(massima, 0)

        assert result["corte"] == "CEDU"

    # === Edge Cases ===

    def test_normalize_empty_autorita(self, pipeline):
        """Test con autorita vuota - default a Cassazione."""
        massima = {
            "numero": "100",
            "anno": "2020",
            "massima": "Testo"
        }
        result = pipeline._normalize_massima(massima, 0)

        assert result["corte"] == "Cassazione"

    def test_normalize_without_anno(self, pipeline):
        """Test senza anno."""
        massima = {
            "autorita": "Cass. civ.",
            "numero": "123",
            "massima": "Testo"
        }
        result = pipeline._normalize_massima(massima, 0)

        assert result["numero"] == "123"  # Senza /anno

    def test_normalize_unknown_autorita(self, pipeline):
        """Test con autorita sconosciuta - mantiene l'originale."""
        massima = {
            "autorita": "Autorita Sconosciuta",
            "numero": "789",
            "anno": "2021",
            "massima": "Testo"
        }
        result = pipeline._normalize_massima(massima, 0)

        # Mantiene l'originale
        assert result["corte"] == "Autorita Sconosciuta"


class TestExtractNumberFromURN:
    """
    Test unitari per _extract_number_from_urn().

    Verifica che i numeri vengano estratti correttamente dai suffissi URN
    per tutti i livelli gerarchici (libro, parte, titolo, capo, sezione).
    """

    def test_extract_libro_number(self):
        """Test estrazione numero libro."""
        from merlt.pipeline.ingestion import _extract_number_from_urn

        urn = "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~libro4"
        assert _extract_number_from_urn(urn, 'libro') == 4

    def test_extract_parte_number(self):
        """Test estrazione numero parte (Costituzione)."""
        from merlt.pipeline.ingestion import _extract_number_from_urn

        urn = "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:costituzione~parte1"
        assert _extract_number_from_urn(urn, 'parte') == 1

    def test_extract_titolo_number(self):
        """Test estrazione numero titolo."""
        from merlt.pipeline.ingestion import _extract_number_from_urn

        urn = "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~libro4~tit2"
        assert _extract_number_from_urn(urn, 'titolo') == 2

    def test_extract_capo_number(self):
        """Test estrazione numero capo."""
        from merlt.pipeline.ingestion import _extract_number_from_urn

        urn = "https://...~libro4~tit2~capo14"
        assert _extract_number_from_urn(urn, 'capo') == 14

    def test_extract_sezione_number(self):
        """Test estrazione numero sezione."""
        from merlt.pipeline.ingestion import _extract_number_from_urn

        urn = "https://...~libro4~tit2~capo14~sez1"
        assert _extract_number_from_urn(urn, 'sezione') == 1

    def test_extract_from_full_hierarchy(self):
        """Test estrazione da URN con gerarchia completa."""
        from merlt.pipeline.ingestion import _extract_number_from_urn

        urn = "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262:2~libro4~tit2~capo14~sez1"
        assert _extract_number_from_urn(urn, 'libro') == 4
        assert _extract_number_from_urn(urn, 'titolo') == 2
        assert _extract_number_from_urn(urn, 'capo') == 14
        assert _extract_number_from_urn(urn, 'sezione') == 1

    def test_extract_nonexistent_level(self):
        """Test estrazione livello non presente - deve tornare None."""
        from merlt.pipeline.ingestion import _extract_number_from_urn

        urn = "https://...~libro4~tit2"
        assert _extract_number_from_urn(urn, 'capo') is None
        assert _extract_number_from_urn(urn, 'sezione') is None

    def test_extract_from_none_urn(self):
        """Test con URN None."""
        from merlt.pipeline.ingestion import _extract_number_from_urn

        assert _extract_number_from_urn(None, 'libro') is None

    def test_extract_from_empty_urn(self):
        """Test con URN vuoto."""
        from merlt.pipeline.ingestion import _extract_number_from_urn

        assert _extract_number_from_urn("", 'libro') is None

    def test_extract_unknown_level(self):
        """Test con livello sconosciuto."""
        from merlt.pipeline.ingestion import _extract_number_from_urn

        urn = "https://...~libro4"
        assert _extract_number_from_urn(urn, 'unknown') is None

    def test_extract_case_insensitive(self):
        """Test estrazione case-insensitive."""
        from merlt.pipeline.ingestion import _extract_number_from_urn

        urn = "https://...~LIBRO4~TIT2"
        assert _extract_number_from_urn(urn, 'libro') == 4
        assert _extract_number_from_urn(urn, 'titolo') == 2

    def test_extract_double_digit_numbers(self):
        """Test numeri a doppia cifra."""
        from merlt.pipeline.ingestion import _extract_number_from_urn

        urn = "https://...~libro12~tit25~capo99"
        assert _extract_number_from_urn(urn, 'libro') == 12
        assert _extract_number_from_urn(urn, 'titolo') == 25
        assert _extract_number_from_urn(urn, 'capo') == 99

    def test_extract_parte_fallback_from_libro(self):
        """Test fallback: estrae numero parte da ~libro se ~parte non presente.

        La Costituzione usa ~libro1 nell'URN per la Parte I.
        Quando chiamiamo _extract_number_from_urn con level='parte',
        deve cercare prima ~parte, poi ~libro come fallback.
        """
        from merlt.pipeline.ingestion import _extract_number_from_urn

        # URN reale della Costituzione che usa ~libro invece di ~parte
        urn = "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:costituzione~libro1"
        assert _extract_number_from_urn(urn, 'parte') == 1

        # Se c'è ~parte esplicito, usa quello
        urn_with_parte = "https://...~parte2"
        assert _extract_number_from_urn(urn_with_parte, 'parte') == 2

        # libro rimane indipendente
        assert _extract_number_from_urn(urn, 'libro') == 1
