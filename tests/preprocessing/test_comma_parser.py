"""
Tests for Comma Parser
======================

Tests the comma_parser module for extracting structured components
from VisualexAPI article text.
"""

import pytest
from merlt.pipeline.parsing import (
    CommaParser,
    ArticleStructure,
    Comma,
    Lettera,
    parse_article,
    count_tokens,
)


class TestCountTokens:
    """Test token counting functionality."""

    def test_empty_string(self):
        assert count_tokens("") == 0

    def test_none_returns_zero(self):
        assert count_tokens(None) == 0

    def test_simple_text(self):
        tokens = count_tokens("Ciao mondo")
        assert tokens > 0
        assert tokens < 10  # Should be ~2-3 tokens

    def test_legal_text(self):
        text = "Nei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie le sue obbligazioni"
        tokens = count_tokens(text)
        assert tokens > 10
        assert tokens < 50


class TestComma:
    """Test Comma dataclass."""

    def test_auto_token_count(self):
        comma = Comma(numero=1, testo="Questo è un testo di prova")
        assert comma.token_count > 0

    def test_explicit_token_count(self):
        comma = Comma(numero=1, testo="Test", token_count=100)
        assert comma.token_count == 100

    def test_empty_text(self):
        comma = Comma(numero=1, testo="")
        assert comma.token_count == 0


class TestArticleStructure:
    """Test ArticleStructure dataclass."""

    def test_auto_total_tokens(self):
        commas = [
            Comma(numero=1, testo="Primo comma del testo"),
            Comma(numero=2, testo="Secondo comma del testo"),
        ]
        structure = ArticleStructure(
            numero_articolo="1453",
            rubrica="Test",
            commas=commas
        )
        assert structure.total_tokens == sum(c.token_count for c in commas)

    def test_empty_commas(self):
        structure = ArticleStructure(
            numero_articolo="1453",
            rubrica="Test",
            commas=[]
        )
        assert structure.total_tokens == 0


class TestCommaParserExtractNumero:
    """Test article number extraction."""

    def test_standard_format(self):
        parser = CommaParser()
        assert parser._extract_numero_articolo("Articolo 1453") == "1453"

    def test_abbreviated_format(self):
        parser = CommaParser()
        assert parser._extract_numero_articolo("Art. 1453") == "1453"

    def test_bis_format(self):
        parser = CommaParser()
        assert parser._extract_numero_articolo("Articolo 1453-bis") == "1453-bis"

    def test_bis_with_space(self):
        parser = CommaParser()
        result = parser._extract_numero_articolo("Articolo 1453 bis")
        assert "1453" in result
        assert "bis" in result.lower()

    def test_ter_format(self):
        parser = CommaParser()
        assert parser._extract_numero_articolo("Art. 2054-ter") == "2054-ter"

    def test_quater_format(self):
        parser = CommaParser()
        assert parser._extract_numero_articolo("Articolo 844 quater") in ["844 quater", "844-quater"]

    def test_lowercase_articolo(self):
        parser = CommaParser()
        assert parser._extract_numero_articolo("articolo 1453") == "1453"

    def test_number_only_fallback(self):
        parser = CommaParser()
        result = parser._extract_numero_articolo("1453.")
        assert "1453" in result


class TestCommaParserExtractRubrica:
    """Test rubrica extraction."""

    def test_standard_rubrica(self):
        parser = CommaParser()
        lines = [
            "Articolo 1453",
            "Risoluzione per inadempimento",
            "",
            "Nei contratti con prestazioni corrispettive..."
        ]
        rubrica, idx = parser._extract_rubrica(lines)
        assert rubrica == "Risoluzione per inadempimento"
        assert idx == 2

    def test_rubrica_with_empty_lines(self):
        parser = CommaParser()
        lines = [
            "Articolo 1453",
            "",
            "Risoluzione per inadempimento",
            "",
            "Nei contratti..."
        ]
        rubrica, idx = parser._extract_rubrica(lines)
        assert rubrica == "Risoluzione per inadempimento"

    def test_no_rubrica_content_starts_immediately(self):
        parser = CommaParser()
        lines = [
            "Articolo 1453",
            "Il contratto si risolve automaticamente quando..."
        ]
        rubrica, idx = parser._extract_rubrica(lines)
        # Should detect this as content, not rubrica
        assert rubrica is None or idx == 1

    def test_single_line_article(self):
        parser = CommaParser()
        lines = ["Articolo 1453"]
        rubrica, idx = parser._extract_rubrica(lines)
        assert rubrica is None


class TestCommaParserExtractCommas:
    """Test comma extraction."""

    def test_two_commas(self):
        parser = CommaParser()
        content = """Nei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie le sue obbligazioni, l'altro può a sua scelta chiedere l'adempimento o la risoluzione del contratto, salvo, in ogni caso, il risarcimento del danno.

La risoluzione può essere domandata anche quando il giudizio è stato promosso per ottenere l'adempimento; ma non può più chiedersi l'adempimento quando è stata domandata la risoluzione."""

        commas = parser._extract_commas(content)
        assert len(commas) == 2
        assert commas[0].numero == 1
        assert commas[1].numero == 2
        assert "contratti con prestazioni corrispettive" in commas[0].testo
        assert "risoluzione può essere domandata" in commas[1].testo

    def test_single_comma(self):
        parser = CommaParser()
        content = "Questo è un singolo comma sufficientemente lungo per essere valido."
        commas = parser._extract_commas(content)
        assert len(commas) == 1
        assert commas[0].numero == 1

    def test_filters_short_paragraphs(self):
        parser = CommaParser(min_comma_length=20)
        content = """Primo comma valido con testo sufficientemente lungo.

Corto.

Secondo comma valido con testo sufficientemente lungo."""

        commas = parser._extract_commas(content)
        assert len(commas) == 2  # "Corto." should be filtered

    def test_empty_content(self):
        parser = CommaParser()
        commas = parser._extract_commas("")
        assert commas == []

    def test_multiple_blank_lines(self):
        parser = CommaParser()
        content = """Primo comma valido con testo lungo abbastanza.



Secondo comma dopo molte righe vuote."""

        commas = parser._extract_commas(content)
        assert len(commas) == 2


class TestCommaParserFullParse:
    """Test full article parsing."""

    def test_art_1453(self):
        """Test with real Art. 1453 text."""
        text = """Articolo 1453
Risoluzione per inadempimento

Nei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie le sue obbligazioni, l'altro può a sua scelta chiedere l'adempimento o la risoluzione del contratto, salvo, in ogni caso, il risarcimento del danno.

La risoluzione può essere domandata anche quando il giudizio è stato promosso per ottenere l'adempimento; ma non può più chiedersi l'adempimento quando è stata domandata la risoluzione."""

        result = parse_article(text)

        assert result.numero_articolo == "1453"
        assert result.rubrica == "Risoluzione per inadempimento"
        assert len(result.commas) == 2
        assert result.total_tokens > 0
        assert result.raw_text == text.strip()

    def test_art_1454_diffida(self):
        """Test with Art. 1454 (diffida ad adempiere)."""
        text = """Articolo 1454
Diffida ad adempiere

Alla parte inadempiente l'altra può intimare per iscritto di adempiere in un congruo termine, con dichiarazione che, decorso inutilmente detto termine, il contratto s'intenderà senz'altro risoluto.

Il termine non può essere inferiore a quindici giorni, salvo diversa pattuizione delle parti o salvo che, per la natura del contratto o secondo gli usi, risulti congruo un termine minore.

Decorso il termine senza che il contratto sia stato adempiuto, questo è risoluto di diritto."""

        result = parse_article(text)

        assert result.numero_articolo == "1454"
        assert result.rubrica == "Diffida ad adempiere"
        assert len(result.commas) == 3

    def test_empty_text_raises(self):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError):
            parse_article("")

        with pytest.raises(ValueError):
            parse_article("   ")

    def test_art_bis_format(self):
        """Test article with bis suffix."""
        text = """Articolo 614-bis
Misure di coercizione indiretta

Con il provvedimento di condanna il giudice, salvo che ciò sia manifestamente iniquo, fissa, su richiesta di parte, la somma di denaro dovuta dall'obbligato per ogni violazione o inosservanza successiva, ovvero per ogni ritardo nell'esecuzione del provvedimento."""

        result = parse_article(text)

        assert "614" in result.numero_articolo
        assert "bis" in result.numero_articolo.lower()

    def test_preserves_internal_newlines(self):
        """Test that commas preserve their internal structure."""
        text = """Articolo 1455
Importanza dell'inadempimento

Il contratto non si può risolvere se l'inadempimento di una delle parti ha scarsa importanza, avuto riguardo all'interesse dell'altra."""

        result = parse_article(text)
        # Should have a single comma since there's no double newline
        assert len(result.commas) == 1


class TestIsRubrica:
    """Test rubrica detection heuristics."""

    def test_typical_rubrica(self):
        parser = CommaParser()
        assert parser._is_rubrica("Risoluzione per inadempimento") is True
        assert parser._is_rubrica("Diffida ad adempiere") is True
        assert parser._is_rubrica("Clausola risolutiva espressa") is True

    def test_content_not_rubrica(self):
        parser = CommaParser()
        # Starts with article
        assert parser._is_rubrica("Il contratto si risolve quando...") is False
        assert parser._is_rubrica("La risoluzione può essere...") is False
        # Ends with period
        assert parser._is_rubrica("Questo è un titolo.") is False
        # Too long
        long_text = "A" * 200
        assert parser._is_rubrica(long_text) is False


class TestIsMetadata:
    """Test metadata detection."""

    def test_note_metadata(self):
        parser = CommaParser()
        assert parser._is_metadata("Note: vedi articolo 1456") is True

    def test_abrogato_tag(self):
        parser = CommaParser()
        assert parser._is_metadata("[ABROGATO]") is True
        assert parser._is_metadata("[VIGENTE]") is True

    def test_normal_content(self):
        parser = CommaParser()
        assert parser._is_metadata("Nei contratti con prestazioni corrispettive...") is False


class TestEdgeCases:
    """Test edge cases and unusual formats."""

    def test_article_with_only_title_line(self):
        """Article with just number line."""
        text = """Articolo 1456
Clausola risolutiva espressa

I contraenti possono convenire espressamente che il contratto si risolva nel caso che una determinata obbligazione non sia adempiuta secondo le modalità stabilite.

In questo caso, la risoluzione si verifica di diritto quando la parte interessata dichiara all'altra che intende valersi della clausola risolutiva."""

        result = parse_article(text)
        assert result.numero_articolo == "1456"
        assert "risolutiva" in result.rubrica.lower()
        assert len(result.commas) == 2

    def test_unicode_handling(self):
        """Test handling of accented characters."""
        text = """Articolo 1457
Termine essenziale per una delle parti

Se il termine fissato per la prestazione di una delle parti deve considerarsi essenziale nell'interesse dell'altra, questa, salvo patto o uso contrario, se vuole esigerne l'esecuzione nonostante la scadenza del termine, deve darne notizia all'altra parte entro tre giorni.

In mancanza, il contratto s'intende risoluto di diritto anche se non è stata espressamente pattuita la risoluzione."""

        result = parse_article(text)
        assert "à" in result.raw_text or "essenziale" in result.commas[0].testo

    def test_parser_reusability(self):
        """Test that parser can be reused for multiple articles."""
        parser = CommaParser()

        text1 = """Articolo 1453
Risoluzione per inadempimento

Nei contratti con prestazioni corrispettive..."""

        text2 = """Articolo 1454
Diffida ad adempiere

Alla parte inadempiente l'altra può intimare..."""

        result1 = parser.parse(text1)
        result2 = parser.parse(text2)

        assert result1.numero_articolo == "1453"
        assert result2.numero_articolo == "1454"


class TestLettera:
    """Test Lettera dataclass."""

    def test_auto_token_count(self):
        lettera = Lettera(lettera="a", testo="Testo della lettera a")
        assert lettera.token_count > 0

    def test_explicit_token_count(self):
        lettera = Lettera(lettera="b", testo="Test", token_count=50)
        assert lettera.token_count == 50

    def test_empty_text(self):
        lettera = Lettera(lettera="c", testo="")
        assert lettera.token_count == 0


class TestLetteraExtraction:
    """Test lettere extraction from commas."""

    def test_extract_lettere_from_art_117(self):
        """Test lettere extraction from Art. 117 Costituzione."""
        parser = CommaParser()
        text = """Art. 117

La potestà legislativa è esercitata dallo Stato e dalle Regioni.

Lo Stato ha legislazione esclusiva nelle seguenti materie:
a) politica estera e rapporti internazionali dello Stato;
b) immigrazione;
c) rapporti tra la Repubblica e le confessioni religiose;
d) difesa e Forze armate; sicurezza dello Stato;
e) moneta, tutela del risparmio e mercati finanziari."""

        result = parser.parse(text)

        # Dovremmo avere 2 commi: primo senza lettere, secondo con lettere
        assert len(result.commas) == 2

        # Primo comma senza lettere
        assert len(result.commas[0].lettere) == 0

        # Secondo comma con 5 lettere
        assert len(result.commas[1].lettere) == 5
        assert result.commas[1].lettere[0].lettera == "a"
        assert result.commas[1].lettere[1].lettera == "b"
        assert result.commas[1].lettere[4].lettera == "e"

    def test_extract_lettere_with_bis_suffix(self):
        """Test lettere con suffisso bis/ter."""
        parser = CommaParser()
        content = """Testo introduttivo:
a) prima lettera;
a-bis) lettera aggiunta;
b) seconda lettera."""

        lettere = parser._extract_lettere(content)

        assert len(lettere) == 3
        assert lettere[0].lettera == "a"
        assert lettere[1].lettera == "a-bis"
        assert lettere[2].lettera == "b"

    def test_no_lettere_single_match(self):
        """Test che una singola lettera non viene estratta (falso positivo)."""
        parser = CommaParser()
        # "a" nel testo non dovrebbe essere estratta come lettera
        content = "Il contratto a prestazioni corrispettive si risolve..."

        lettere = parser._extract_lettere(content)

        assert len(lettere) == 0

    def test_no_lettere_in_normal_text(self):
        """Test che testo normale senza lettere ritorna lista vuota."""
        parser = CommaParser()
        content = "Nei contratti con prestazioni corrispettive, quando uno dei contraenti non adempie le sue obbligazioni."

        lettere = parser._extract_lettere(content)

        assert len(lettere) == 0

    def test_lettere_with_period_delimiter(self):
        """Test lettere con delimitatore punto invece di parentesi."""
        parser = CommaParser()
        content = """Elenco:
a. prima voce;
b. seconda voce;
c. terza voce."""

        lettere = parser._extract_lettere(content)

        assert len(lettere) == 3
        assert lettere[0].lettera == "a"
        assert lettere[1].lettera == "b"
        assert lettere[2].lettera == "c"

    def test_comma_has_lettere_field(self):
        """Test che Comma ha il campo lettere."""
        comma = Comma(numero=1, testo="Test")
        assert hasattr(comma, 'lettere')
        assert isinstance(comma.lettere, list)
        assert len(comma.lettere) == 0  # Default empty

    def test_comma_with_lettere(self):
        """Test Comma con lettere esplicite."""
        lettere = [
            Lettera(lettera="a", testo="Prima"),
            Lettera(lettera="b", testo="Seconda"),
        ]
        comma = Comma(numero=1, testo="Test", lettere=lettere)

        assert len(comma.lettere) == 2
        assert comma.lettere[0].lettera == "a"
        assert comma.lettere[1].lettera == "b"


class TestFullArticleWithLettere:
    """Test full article parsing with lettere."""

    def test_art_117_costituzione(self):
        """Test completo Art. 117 Costituzione con commi e lettere."""
        parser = CommaParser()
        text = """Art. 117

La potestà legislativa è esercitata dallo Stato e dalle Regioni nel rispetto della Costituzione, nonché dei vincoli derivanti dall'ordinamento comunitario e dagli obblighi internazionali.

Lo Stato ha legislazione esclusiva nelle seguenti materie:
a) politica estera e rapporti internazionali dello Stato; rapporti dello Stato con l'Unione europea;
b) immigrazione;
c) rapporti tra la Repubblica e le confessioni religiose;
d) difesa e Forze armate; sicurezza dello Stato;
e) moneta, tutela del risparmio e mercati finanziari;

Sono materie di legislazione concorrente quelle relative a: rapporti internazionali."""

        result = parser.parse(text)

        # Articolo numero corretto
        assert result.numero_articolo == "117"

        # 3 commi
        assert len(result.commas) == 3

        # Comma 1: senza lettere
        assert len(result.commas[0].lettere) == 0
        assert "potestà legislativa" in result.commas[0].testo

        # Comma 2: con 5 lettere
        assert len(result.commas[1].lettere) == 5
        assert "legislazione esclusiva" in result.commas[1].testo

        # Comma 3: senza lettere
        assert len(result.commas[2].lettere) == 0
        assert "legislazione concorrente" in result.commas[2].testo

    def test_art_119_costituzione(self):
        """Test Art. 119 Costituzione (finanza regionale) - altro esempio con lettere."""
        parser = CommaParser()
        text = """Art. 119

I Comuni, le Province, le Città metropolitane e le Regioni hanno autonomia finanziaria di entrata e di spesa.

I Comuni, le Province, le Città metropolitane e le Regioni hanno risorse autonome.

La legge dello Stato istituisce un fondo perequativo, senza vincoli di destinazione, per i territori con minore capacità fiscale per abitante.

Le risorse derivanti dalle fonti di cui ai commi precedenti consentono ai Comuni, alle Province, alle Città metropolitane e alle Regioni di finanziare integralmente le funzioni pubbliche loro attribuite."""

        result = parser.parse(text)

        # 4 commi, nessuno con lettere
        assert len(result.commas) == 4
        for comma in result.commas:
            assert len(comma.lettere) == 0

    def test_codice_civile_art_2054(self):
        """Test Art. 2054 c.c. (circolazione veicoli) - articolo con lettere nel CC."""
        parser = CommaParser()
        text = """Art. 2054
Circolazione di veicoli

Il conducente di un veicolo senza guida di rotaie è obbligato a risarcire il danno prodotto a persone o a cose dalla circolazione del veicolo.

Il proprietario del veicolo, o in sua vece l'usufruttuario o l'acquirente con patto di riservato dominio, è responsabile in solido col conducente."""

        result = parser.parse(text)

        assert result.numero_articolo == "2054"
        assert "Circolazione" in result.rubrica
        # Nessuna lettera in questo articolo
        for comma in result.commas:
            assert len(comma.lettere) == 0
