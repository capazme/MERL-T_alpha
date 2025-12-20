"""
Test per le metriche di Information Retrieval.

Questi test verificano la correttezza delle implementazioni di:
- Recall@K
- Precision@K
- Mean Reciprocal Rank (MRR)
- Hit Rate
- DCG/NDCG
"""

import pytest
from merlt.benchmark.metrics import (
    recall_at_k,
    precision_at_k,
    hit_at_k,
    reciprocal_rank,
    mrr,
    hit_rate,
    dcg_at_k,
    ndcg_at_k,
    compute_retrieval_metrics,
    compute_latency_metrics,
    RetrievalMetrics,
    LatencyMetrics,
)


class TestRecallAtK:
    """Test per Recall@K."""

    def test_perfect_recall(self):
        """Tutti i documenti rilevanti sono recuperati."""
        retrieved = ["a", "b", "c", "d"]
        relevant = ["a", "b"]
        assert recall_at_k(retrieved, relevant, k=4) == 1.0

    def test_partial_recall(self):
        """Solo alcuni documenti rilevanti sono recuperati."""
        retrieved = ["a", "b", "c", "d"]
        relevant = ["a", "x"]  # x non è recuperato
        assert recall_at_k(retrieved, relevant, k=4) == 0.5

    def test_zero_recall(self):
        """Nessun documento rilevante recuperato."""
        retrieved = ["a", "b", "c"]
        relevant = ["x", "y", "z"]
        assert recall_at_k(retrieved, relevant, k=3) == 0.0

    def test_k_limits_results(self):
        """K limita i risultati considerati."""
        retrieved = ["x", "y", "a", "b"]  # a,b sono dopo k=2
        relevant = ["a", "b"]
        assert recall_at_k(retrieved, relevant, k=2) == 0.0
        assert recall_at_k(retrieved, relevant, k=4) == 1.0

    def test_empty_relevant_returns_one(self):
        """Se non ci sono rilevanti, recall è 1.0 per convenzione."""
        retrieved = ["a", "b", "c"]
        relevant = []
        assert recall_at_k(retrieved, relevant, k=3) == 1.0

    def test_empty_retrieved(self):
        """Se non ci sono risultati, recall dipende dai rilevanti."""
        retrieved = []
        relevant = ["a", "b"]
        assert recall_at_k(retrieved, relevant, k=5) == 0.0

    def test_recall_with_duplicates_in_relevant(self):
        """Duplicati nei rilevanti sono gestiti correttamente."""
        retrieved = ["a", "b"]
        relevant = ["a", "a", "b"]  # 2 unici
        assert recall_at_k(retrieved, relevant, k=2) == 1.0


class TestPrecisionAtK:
    """Test per Precision@K."""

    def test_perfect_precision(self):
        """Tutti i risultati sono rilevanti."""
        retrieved = ["a", "b"]
        relevant = ["a", "b", "c"]
        assert precision_at_k(retrieved, relevant, k=2) == 1.0

    def test_half_precision(self):
        """Metà dei risultati sono rilevanti."""
        retrieved = ["a", "x", "b", "y"]
        relevant = ["a", "b"]
        assert precision_at_k(retrieved, relevant, k=4) == 0.5

    def test_zero_precision(self):
        """Nessun risultato rilevante."""
        retrieved = ["x", "y", "z"]
        relevant = ["a", "b"]
        assert precision_at_k(retrieved, relevant, k=3) == 0.0

    def test_k_zero_returns_zero(self):
        """K=0 restituisce 0."""
        retrieved = ["a", "b"]
        relevant = ["a"]
        assert precision_at_k(retrieved, relevant, k=0) == 0.0


class TestHitAtK:
    """Test per Hit@K."""

    def test_hit_present(self):
        """Almeno un rilevante è presente."""
        retrieved = ["x", "a", "y"]
        relevant = ["a"]
        assert hit_at_k(retrieved, relevant, k=3) is True

    def test_hit_absent(self):
        """Nessun rilevante è presente."""
        retrieved = ["x", "y", "z"]
        relevant = ["a", "b"]
        assert hit_at_k(retrieved, relevant, k=3) is False

    def test_hit_outside_k(self):
        """Rilevante è fuori da top-K."""
        retrieved = ["x", "y", "a"]
        relevant = ["a"]
        assert hit_at_k(retrieved, relevant, k=2) is False
        assert hit_at_k(retrieved, relevant, k=3) is True


class TestReciprocalRank:
    """Test per Reciprocal Rank."""

    def test_first_position(self):
        """Rilevante in prima posizione → RR = 1.0."""
        retrieved = ["a", "x", "y"]
        relevant = ["a"]
        assert reciprocal_rank(retrieved, relevant) == 1.0

    def test_second_position(self):
        """Rilevante in seconda posizione → RR = 0.5."""
        retrieved = ["x", "a", "y"]
        relevant = ["a"]
        assert reciprocal_rank(retrieved, relevant) == 0.5

    def test_third_position(self):
        """Rilevante in terza posizione → RR = 0.333..."""
        retrieved = ["x", "y", "a"]
        relevant = ["a"]
        assert abs(reciprocal_rank(retrieved, relevant) - 1/3) < 0.001

    def test_no_relevant_found(self):
        """Nessun rilevante trovato → RR = 0."""
        retrieved = ["x", "y", "z"]
        relevant = ["a", "b"]
        assert reciprocal_rank(retrieved, relevant) == 0.0

    def test_multiple_relevant(self):
        """Con più rilevanti, conta solo il primo."""
        retrieved = ["x", "a", "b"]  # a in pos 2, b in pos 3
        relevant = ["a", "b"]
        assert reciprocal_rank(retrieved, relevant) == 0.5  # Usa pos di 'a'


class TestMRR:
    """Test per Mean Reciprocal Rank."""

    def test_perfect_mrr(self):
        """Tutti i rilevanti in prima posizione → MRR = 1.0."""
        all_retrieved = [["a"], ["b"], ["c"]]
        all_relevant = [["a"], ["b"], ["c"]]
        assert mrr(all_retrieved, all_relevant) == 1.0

    def test_average_mrr(self):
        """MRR è la media dei RR."""
        all_retrieved = [
            ["a", "x"],  # RR = 1.0
            ["x", "b"],  # RR = 0.5
        ]
        all_relevant = [["a"], ["b"]]
        assert mrr(all_retrieved, all_relevant) == 0.75  # (1.0 + 0.5) / 2

    def test_zero_mrr(self):
        """Nessun rilevante trovato → MRR = 0."""
        all_retrieved = [["x"], ["y"]]
        all_relevant = [["a"], ["b"]]
        assert mrr(all_retrieved, all_relevant) == 0.0

    def test_empty_input(self):
        """Input vuoto → MRR = 0."""
        assert mrr([], []) == 0.0


class TestHitRate:
    """Test per Hit Rate."""

    def test_perfect_hit_rate(self):
        """Tutte le query hanno hit → 1.0."""
        all_retrieved = [["a"], ["b"], ["c"]]
        all_relevant = [["a"], ["b"], ["c"]]
        assert hit_rate(all_retrieved, all_relevant, k=1) == 1.0

    def test_partial_hit_rate(self):
        """Metà delle query hanno hit → 0.5."""
        all_retrieved = [["a"], ["x"]]
        all_relevant = [["a"], ["b"]]  # Seconda query non ha hit
        assert hit_rate(all_retrieved, all_relevant, k=1) == 0.5

    def test_zero_hit_rate(self):
        """Nessuna query ha hit → 0.0."""
        all_retrieved = [["x"], ["y"]]
        all_relevant = [["a"], ["b"]]
        assert hit_rate(all_retrieved, all_relevant, k=1) == 0.0


class TestDCG:
    """Test per DCG e NDCG."""

    def test_dcg_perfect_order(self):
        """DCG con ordine perfetto."""
        relevance_scores = [3, 2, 1, 0]  # Ordine decrescente
        dcg = dcg_at_k(relevance_scores, k=4)
        # DCG = (2^3-1)/log2(2) + (2^2-1)/log2(3) + (2^1-1)/log2(4) + 0
        # DCG = 7/1 + 3/1.585 + 1/2 + 0 = 7 + 1.893 + 0.5 = 9.393
        assert dcg > 9.3

    def test_dcg_k_limits(self):
        """K limita il calcolo DCG."""
        relevance_scores = [3, 2, 1, 0]
        dcg_2 = dcg_at_k(relevance_scores, k=2)
        dcg_4 = dcg_at_k(relevance_scores, k=4)
        assert dcg_2 < dcg_4

    def test_ndcg_perfect(self):
        """NDCG = 1.0 con ordine perfetto."""
        retrieved = [3, 2, 1]  # Ordine perfetto
        ideal = [3, 2, 1]
        assert ndcg_at_k(retrieved, ideal, k=3) == 1.0

    def test_ndcg_imperfect(self):
        """NDCG < 1.0 con ordine imperfetto."""
        retrieved = [1, 3, 2]  # Ordine sbagliato
        ideal = [3, 2, 1]
        assert ndcg_at_k(retrieved, ideal, k=3) < 1.0

    def test_ndcg_zero_ideal(self):
        """NDCG = 0 se IDCG = 0."""
        retrieved = [0, 0, 0]
        ideal = [0, 0, 0]
        assert ndcg_at_k(retrieved, ideal, k=3) == 0.0


class TestComputeRetrievalMetrics:
    """Test per compute_retrieval_metrics."""

    def test_basic_computation(self):
        """Verifica calcolo base delle metriche."""
        all_retrieved = [
            ["a", "b", "c"],  # Query 1
            ["x", "y", "a"],  # Query 2
        ]
        all_relevant = [
            ["a"],  # Query 1: hit at pos 1
            ["a"],  # Query 2: hit at pos 3
        ]

        metrics = compute_retrieval_metrics(all_retrieved, all_relevant)

        assert isinstance(metrics, RetrievalMetrics)
        assert metrics.num_queries == 2
        assert metrics.recall_at_1 == 0.5  # Solo query 1 ha hit@1
        assert metrics.mrr > 0.5  # (1.0 + 0.333) / 2 = 0.667

    def test_with_categories(self):
        """Verifica disaggregazione per categoria."""
        all_retrieved = [["a"], ["b"], ["x"]]
        all_relevant = [["a"], ["b"], ["c"]]
        categories = ["cat1", "cat1", "cat2"]

        metrics = compute_retrieval_metrics(
            all_retrieved, all_relevant, categories=categories
        )

        assert metrics.by_category is not None
        assert "cat1" in metrics.by_category
        assert "cat2" in metrics.by_category
        assert metrics.by_category["cat1"].recall_at_1 == 1.0
        assert metrics.by_category["cat2"].recall_at_1 == 0.0


class TestComputeLatencyMetrics:
    """Test per compute_latency_metrics."""

    def test_basic_computation(self):
        """Verifica calcolo statistiche di latenza."""
        latencies = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

        metrics = compute_latency_metrics(latencies, "test_op")

        assert isinstance(metrics, LatencyMetrics)
        assert metrics.operation == "test_op"
        assert metrics.num_samples == 10
        assert metrics.min_ms == 10
        assert metrics.max_ms == 100
        assert metrics.mean_ms == 55
        assert metrics.median_ms == 55  # (50 + 60) / 2

    def test_empty_latencies(self):
        """Input vuoto restituisce metriche zero."""
        metrics = compute_latency_metrics([], "empty_op")

        assert metrics.num_samples == 0
        assert metrics.min_ms == 0
        assert metrics.max_ms == 0

    def test_percentiles(self):
        """Verifica calcolo percentili."""
        latencies = list(range(1, 101))  # 1 to 100

        metrics = compute_latency_metrics(latencies, "percentile_op")

        # p90 dovrebbe essere circa il 90° valore (91 con int index)
        assert 89 <= metrics.p90_ms <= 92
        # p99 dovrebbe essere circa il 99° valore
        assert 98 <= metrics.p99_ms <= 100


class TestRetrievalMetricsDataclass:
    """Test per RetrievalMetrics dataclass."""

    def test_to_dict(self):
        """Verifica serializzazione a dizionario."""
        metrics = RetrievalMetrics(
            recall_at_1=0.75,
            recall_at_5=0.90,
            recall_at_10=1.0,
            mrr=0.85,
            hit_rate_at_5=0.95,
            num_queries=50,
        )

        d = metrics.to_dict()

        assert d["recall_at_1"] == 0.75
        assert d["recall_at_5"] == 0.90
        assert d["mrr"] == 0.85
        assert d["num_queries"] == 50

    def test_to_dict_with_categories(self):
        """Verifica serializzazione con categorie."""
        child_metrics = RetrievalMetrics(
            recall_at_1=0.5, recall_at_5=0.8, recall_at_10=1.0,
            mrr=0.7, hit_rate_at_5=0.9, num_queries=10
        )

        metrics = RetrievalMetrics(
            recall_at_1=0.75, recall_at_5=0.90, recall_at_10=1.0,
            mrr=0.85, hit_rate_at_5=0.95, num_queries=50,
            by_category={"cat1": child_metrics}
        )

        d = metrics.to_dict()

        assert "by_category" in d
        assert "cat1" in d["by_category"]


class TestLatencyMetricsDataclass:
    """Test per LatencyMetrics dataclass."""

    def test_to_dict(self):
        """Verifica serializzazione a dizionario."""
        metrics = LatencyMetrics(
            operation="search",
            num_samples=100,
            min_ms=5.123,
            max_ms=150.456,
            mean_ms=25.789,
            median_ms=20.111,
            p90_ms=50.222,
            p99_ms=100.333,
        )

        d = metrics.to_dict()

        assert d["operation"] == "search"
        assert d["num_samples"] == 100
        assert d["min_ms"] == 5.123
        assert d["median_ms"] == 20.111
