"""
Test per il modulo Gold Standard.

Verifica:
- Creazione e gestione Query
- Serializzazione/deserializzazione GoldStandard
- Filtri per categoria e difficoltà
- Validazione dataset
"""

import pytest
import json
import tempfile
from pathlib import Path

from merlt.benchmark.gold_standard import (
    Query,
    QueryCategory,
    GoldStandard,
    create_libro_iv_gold_standard,
)


class TestQuery:
    """Test per la classe Query."""

    def test_create_query(self):
        """Verifica creazione base di una query."""
        q = Query(
            id="Q001",
            text="Cos'è il contratto?",
            category=QueryCategory.CONCETTUALE,
            expected_article="urn:cc:art1321",
            relevant_urns=["urn:cc:art1321", "urn:cc:art1322"],
        )

        assert q.id == "Q001"
        assert q.text == "Cos'è il contratto?"
        assert q.category == QueryCategory.CONCETTUALE
        assert len(q.relevant_urns) == 2

    def test_relevant_set(self):
        """Verifica conversione in set."""
        q = Query(
            id="Q001",
            text="test",
            category=QueryCategory.NORMATIVA,
            expected_article="urn:1",
            relevant_urns=["urn:1", "urn:2", "urn:1"],  # Duplicato
        )

        assert len(q.relevant_set) == 2  # Set elimina duplicati

    def test_to_dict(self):
        """Verifica serializzazione."""
        q = Query(
            id="Q001",
            text="Cos'è il contratto?",
            category=QueryCategory.CONCETTUALE,
            expected_article="urn:cc:art1321",
            relevant_urns=["urn:cc:art1321"],
            difficulty="easy",
            metadata={"source": "test"},
        )

        d = q.to_dict()

        assert d["id"] == "Q001"
        assert d["category"] == "concettuale"
        assert d["difficulty"] == "easy"
        assert d["metadata"]["source"] == "test"

    def test_from_dict(self):
        """Verifica deserializzazione."""
        data = {
            "id": "Q001",
            "text": "Test query",
            "category": "normativa",
            "expected_article": "urn:1",
            "relevant_urns": ["urn:1"],
            "difficulty": "hard",
        }

        q = Query.from_dict(data)

        assert q.id == "Q001"
        assert q.category == QueryCategory.NORMATIVA
        assert q.difficulty == "hard"

    def test_from_dict_defaults(self):
        """Verifica valori di default nella deserializzazione."""
        data = {
            "id": "Q001",
            "text": "Test",
        }

        q = Query.from_dict(data)

        assert q.category == QueryCategory.CONCETTUALE  # Default
        assert q.difficulty == "medium"  # Default
        assert q.source == "manual"  # Default


class TestQueryCategory:
    """Test per l'enum QueryCategory."""

    def test_all_categories_exist(self):
        """Verifica esistenza di tutte le categorie."""
        categories = [
            QueryCategory.CONCETTUALE,
            QueryCategory.NORMATIVA,
            QueryCategory.GIURISPRUDENZIALE,
            QueryCategory.PRATICA,
        ]

        assert len(categories) == 4

    def test_category_values(self):
        """Verifica valori string delle categorie."""
        assert QueryCategory.CONCETTUALE.value == "concettuale"
        assert QueryCategory.NORMATIVA.value == "normativa"
        assert QueryCategory.GIURISPRUDENZIALE.value == "giurisprudenziale"
        assert QueryCategory.PRATICA.value == "pratica"


class TestGoldStandard:
    """Test per la classe GoldStandard."""

    @pytest.fixture
    def sample_queries(self):
        """Fixture con query di esempio."""
        return [
            Query(
                id="Q001",
                text="Cos'è il contratto?",
                category=QueryCategory.CONCETTUALE,
                expected_article="urn:1",
                relevant_urns=["urn:1"],
                difficulty="easy",
            ),
            Query(
                id="Q002",
                text="Art. 1453 cc",
                category=QueryCategory.NORMATIVA,
                expected_article="urn:2",
                relevant_urns=["urn:2"],
                difficulty="easy",
            ),
            Query(
                id="Q003",
                text="Sentenza sulla risoluzione",
                category=QueryCategory.GIURISPRUDENZIALE,
                expected_article="urn:3",
                relevant_urns=["urn:3", "urn:4"],
                difficulty="hard",
            ),
        ]

    def test_create_gold_standard(self, sample_queries):
        """Verifica creazione GoldStandard."""
        gs = GoldStandard(queries=sample_queries)

        assert len(gs) == 3
        assert gs[0].id == "Q001"

    def test_iteration(self, sample_queries):
        """Verifica iterazione sulle query."""
        gs = GoldStandard(queries=sample_queries)

        ids = [q.id for q in gs]
        assert ids == ["Q001", "Q002", "Q003"]

    def test_categories_property(self, sample_queries):
        """Verifica property categories."""
        gs = GoldStandard(queries=sample_queries)

        cats = gs.categories
        assert cats == ["concettuale", "normativa", "giurisprudenziale"]

    def test_all_relevant_urns(self, sample_queries):
        """Verifica property all_relevant_urns."""
        gs = GoldStandard(queries=sample_queries)

        urns = gs.all_relevant_urns
        assert len(urns) == 3
        assert urns[2] == ["urn:3", "urn:4"]

    def test_filter_by_category(self, sample_queries):
        """Verifica filtro per categoria."""
        gs = GoldStandard(queries=sample_queries)

        conceptual = gs.filter_by_category(QueryCategory.CONCETTUALE)

        assert len(conceptual) == 1
        assert conceptual[0].id == "Q001"

    def test_filter_by_difficulty(self, sample_queries):
        """Verifica filtro per difficoltà."""
        gs = GoldStandard(queries=sample_queries)

        easy = gs.filter_by_difficulty("easy")
        hard = gs.filter_by_difficulty("hard")

        assert len(easy) == 2
        assert len(hard) == 1
        assert hard[0].id == "Q003"

    def test_get_statistics(self, sample_queries):
        """Verifica calcolo statistiche."""
        gs = GoldStandard(queries=sample_queries)

        stats = gs.get_statistics()

        assert stats["total_queries"] == 3
        assert stats["by_category"]["concettuale"] == 1
        assert stats["by_category"]["normativa"] == 1
        assert stats["by_difficulty"]["easy"] == 2
        assert stats["by_difficulty"]["hard"] == 1

    def test_validate_valid(self, sample_queries):
        """Verifica validazione di dataset valido."""
        gs = GoldStandard(queries=sample_queries)

        errors = gs.validate()

        assert len(errors) == 0

    def test_validate_duplicate_ids(self):
        """Verifica rilevamento ID duplicati."""
        queries = [
            Query(id="Q001", text="a", category=QueryCategory.CONCETTUALE,
                  expected_article="urn:1", relevant_urns=["urn:1"]),
            Query(id="Q001", text="b", category=QueryCategory.NORMATIVA,
                  expected_article="urn:2", relevant_urns=["urn:2"]),
        ]
        gs = GoldStandard(queries=queries)

        errors = gs.validate()

        assert any("Duplicate" in e for e in errors)

    def test_validate_empty_relevant(self):
        """Verifica rilevamento query senza rilevanti."""
        queries = [
            Query(id="Q001", text="test", category=QueryCategory.CONCETTUALE,
                  expected_article="urn:1", relevant_urns=[]),
        ]
        gs = GoldStandard(queries=queries)

        errors = gs.validate()

        assert any("no relevant URNs" in e for e in errors)

    def test_to_dict(self, sample_queries):
        """Verifica serializzazione a dizionario."""
        gs = GoldStandard(
            queries=sample_queries,
            metadata={"version": "1.0"}
        )

        d = gs.to_dict()

        assert "queries" in d
        assert "metadata" in d
        assert len(d["queries"]) == 3
        assert d["metadata"]["version"] == "1.0"

    def test_from_dict(self):
        """Verifica deserializzazione da dizionario."""
        data = {
            "metadata": {"version": "1.0"},
            "queries": [
                {
                    "id": "Q001",
                    "text": "Test",
                    "category": "concettuale",
                    "expected_article": "urn:1",
                    "relevant_urns": ["urn:1"],
                }
            ]
        }

        gs = GoldStandard.from_dict(data)

        assert len(gs) == 1
        assert gs.metadata["version"] == "1.0"

    def test_file_roundtrip(self, sample_queries):
        """Verifica salvataggio e caricamento da file."""
        gs = GoldStandard(queries=sample_queries, metadata={"test": True})

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            gs.to_file(path)
            loaded = GoldStandard.from_file(path)

            assert len(loaded) == len(gs)
            assert loaded[0].id == gs[0].id
            assert loaded.metadata["test"] is True
        finally:
            Path(path).unlink()

    def test_create_empty(self):
        """Verifica creazione dataset vuoto."""
        gs = GoldStandard.create_empty(
            name="Test",
            version="1.0",
            author="Test Author"
        )

        assert len(gs) == 0
        assert gs.metadata["name"] == "Test"
        assert gs.metadata["version"] == "1.0"

    def test_add_query(self):
        """Verifica aggiunta query."""
        gs = GoldStandard.create_empty()

        q = gs.add_query(
            text="Test query",
            category=QueryCategory.CONCETTUALE,
            expected_article="urn:test",
        )

        assert len(gs) == 1
        assert q.id == "Q001"
        assert q.text == "Test query"
        assert "urn:test" in q.relevant_urns

    def test_add_multiple_queries(self):
        """Verifica ID incrementali."""
        gs = GoldStandard.create_empty()

        gs.add_query("Q1", QueryCategory.CONCETTUALE, "urn:1")
        gs.add_query("Q2", QueryCategory.NORMATIVA, "urn:2")
        gs.add_query("Q3", QueryCategory.PRATICA, "urn:3")

        assert gs[0].id == "Q001"
        assert gs[1].id == "Q002"
        assert gs[2].id == "Q003"


class TestCreateLibroIVGoldStandard:
    """Test per la funzione factory."""

    def test_creates_50_queries(self):
        """Verifica creazione di 50 query."""
        gs = create_libro_iv_gold_standard()

        assert len(gs) == 50

    def test_all_categories_present(self):
        """Verifica distribuzione categorie."""
        gs = create_libro_iv_gold_standard()
        stats = gs.get_statistics()

        assert stats["by_category"]["concettuale"] == 15
        assert stats["by_category"]["normativa"] == 15
        assert stats["by_category"]["giurisprudenziale"] == 10
        assert stats["by_category"]["pratica"] == 10

    def test_all_queries_have_relevant(self):
        """Verifica che tutte le query abbiano URN rilevanti."""
        gs = create_libro_iv_gold_standard()

        for q in gs:
            assert len(q.relevant_urns) > 0, f"Query {q.id} has no relevant URNs"

    def test_unique_ids(self):
        """Verifica unicità degli ID."""
        gs = create_libro_iv_gold_standard()
        ids = [q.id for q in gs]

        assert len(ids) == len(set(ids))

    def test_urn_format(self):
        """Verifica formato URN."""
        gs = create_libro_iv_gold_standard()

        for q in gs:
            for urn in q.relevant_urns:
                assert "urn:nir:stato:regio.decreto" in urn, \
                    f"Invalid URN format: {urn}"

    def test_validation_passes(self):
        """Verifica che il dataset passi la validazione."""
        gs = create_libro_iv_gold_standard()
        errors = gs.validate()

        assert len(errors) == 0, f"Validation errors: {errors}"

    def test_difficulty_distribution(self):
        """Verifica distribuzione difficoltà."""
        gs = create_libro_iv_gold_standard()
        stats = gs.get_statistics()

        # Dovrebbe avere un mix di difficoltà
        assert stats["by_difficulty"]["easy"] > 0
        assert stats["by_difficulty"]["medium"] > 0
        assert stats["by_difficulty"]["hard"] > 0
