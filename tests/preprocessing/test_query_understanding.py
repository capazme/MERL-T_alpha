"""
Test Suite for Query Understanding Module
===========================================

Comprehensive tests for:
- Named Entity Recognition (NER)
- Intent Classification
- Legal Concept Extraction
- Norm Reference Extraction

50+ test cases covering:
- Italian legal references (Codice Civile, Penale, GDPR, etc.)
- Intent classification (5 types)
- Temporal references
- Monetary amounts
- Edge cases and error handling

Uses pytest + pytest-asyncio for async testing.
"""

import pytest
import json
from datetime import datetime
from typing import List

from merlt.preprocessing.query_understanding import (
    QueryUnderstandingService,
    LegalPatterns,
    QueryIntentType,
    LegalEntityType,
    LegalEntity,
    QueryUnderstandingResult,
    get_query_understanding_service,
    analyze_query,
    prepare_query_for_enrichment
)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def service():
    """Get QueryUnderstandingService instance"""
    return QueryUnderstandingService()


@pytest.fixture
def patterns():
    """Get LegalPatterns helper"""
    return LegalPatterns()


# ==========================================
# Tests: Norm Reference Extraction
# ==========================================

class TestNormReferenceExtraction:
    """Test extraction of legal norm references"""

    def test_codice_civile_single_article(self, patterns):
        """Extract single article from Codice Civile"""
        text = "L'art. 1321 c.c. definisce il contratto"
        norms = patterns.extract_norms(text)
        assert len(norms) > 0
        assert "1321" in norms[0][0]
        assert norms[0][1] == "codice_civile"
        assert norms[0][2] == "cc_art_1321"

    def test_codice_civile_with_comma(self, patterns):
        """Extract article with comma specification"""
        text = "Secondo l'art. 1321 co. 2 c.c., il contratto deve avere accordo"
        norms = patterns.extract_norms(text)
        assert len(norms) > 0

    def test_codice_penale_reference(self, patterns):
        """Extract Codice Penale reference"""
        text = "L'art. 575 c.p. punisce l'omicidio"
        norms = patterns.extract_norms(text)
        assert any("575" in n[0] for n in norms)

    def test_codice_procedura_civile(self, patterns):
        """Extract Codice Procedura Civile reference"""
        text = "Secondo l'art. 100 c.p.c., il ricorso deve contenere..."
        norms = patterns.extract_norms(text)
        assert any("100" in n[0] for n in norms)

    def test_costituzione_reference(self, patterns):
        """Extract Costituzione reference"""
        text = "L'art. 3 della Costituzione tutela l'eguaglianza"
        norms = patterns.extract_norms(text)
        assert len(norms) > 0

    def test_gdpr_reference(self, patterns):
        """Extract GDPR article reference"""
        text = "L'art. 82 GDPR riguarda la responsabilità del titolare"
        norms = patterns.extract_norms(text)
        assert any("82" in n[0] for n in norms)
        assert any("gdpr" in n[1].lower() for n in norms)

    def test_decree_reference(self, patterns):
        """Extract decreto legislativo reference"""
        text = "D.Lgs 196/2003 è il codice della privacy"
        norms = patterns.extract_norms(text)
        assert len(norms) > 0

    def test_multiple_norms_in_query(self, patterns):
        """Extract multiple norm references from single query"""
        text = "Art. 1321 c.c. e Art. 1352 c.c. disciplinano il contratto"
        norms = patterns.extract_norms(text)
        assert len(norms) >= 2

    def test_norm_normalization(self, patterns):
        """Test normalization of norm references"""
        text = "L'articolo 1321 codice civile"
        norms = patterns.extract_norms(text)
        if norms:
            assert norms[0][2].startswith("cc_art_")

    def test_case_insensitive_norm_extraction(self, patterns):
        """Norm extraction should be case-insensitive"""
        text_lower = "l'art. 1321 c.c."
        text_upper = "L'ART. 1321 C.C."
        norms_lower = patterns.extract_norms(text_lower)
        norms_upper = patterns.extract_norms(text_upper)
        assert len(norms_lower) > 0
        assert len(norms_upper) > 0


# ==========================================
# Tests: Legal Concept Extraction
# ==========================================

class TestLegalConceptExtraction:
    """Test extraction of legal concepts"""

    def test_gdpr_concepts(self, patterns):
        """Extract GDPR-related concepts"""
        text = "Il consenso al trattamento dei dati personali secondo GDPR"
        concepts = patterns.extract_legal_concepts(text)
        assert any("GDPR" in c or "consenso" in c.lower() for c in concepts)

    def test_contract_concepts(self, patterns):
        """Extract contract-related concepts"""
        text = "La clausola di un contratto deve avere consensus ad idem"
        concepts = patterns.extract_legal_concepts(text)
        assert any("contratto" in c.lower() for c in concepts)

    def test_responsibility_concepts(self, patterns):
        """Extract responsibility-related concepts"""
        text = "La responsabilità civile è conseguenza del danno"
        concepts = patterns.extract_legal_concepts(text)
        assert any("responsabilità" in c.lower() or "danno" in c.lower() for c in concepts)

    def test_multiple_concept_domains(self, patterns):
        """Extract concepts from multiple domains"""
        text = "Protezione dati personali (GDPR) e responsabilità civile nel contratto"
        concepts = patterns.extract_legal_concepts(text)
        assert len(concepts) > 1

    def test_concept_case_insensitive(self, patterns):
        """Concept extraction should be case-insensitive"""
        text1 = "Privacy e GDPR"
        text2 = "privacy e gdpr"
        concepts1 = patterns.extract_legal_concepts(text1)
        concepts2 = patterns.extract_legal_concepts(text2)
        assert len(concepts1) == len(concepts2)

    def test_no_concepts_when_not_present(self, patterns):
        """Return empty list when no concepts detected"""
        text = "Il gatto è un animale domestico"
        concepts = patterns.extract_legal_concepts(text)
        assert len(concepts) == 0 or all("gatto" not in c.lower() for c in concepts)


# ==========================================
# Tests: Entity Extraction
# ==========================================

class TestEntityExtraction:
    """Test named entity extraction"""

    def test_date_extraction_iso_format(self, patterns):
        """Extract ISO format dates"""
        text = "Dal 2024-01-15 la legge entra in vigore"
        dates = patterns.extract_dates(text)
        assert len(dates) > 0
        assert "2024-01-15" in dates

    def test_date_extraction_italian_format(self, patterns):
        """Extract Italian format dates"""
        text = "Dal 15/01/2024 la nuova normativa si applica"
        dates = patterns.extract_dates(text)
        assert len(dates) > 0

    def test_month_year_extraction(self, patterns):
        """Extract month-year references"""
        text = "A partire da gennaio 2024"
        dates = patterns.extract_dates(text)
        assert len(dates) > 0

    def test_amount_euro_extraction(self, patterns):
        """Extract euro amounts"""
        text = "Il risarcimento è di €500.000"
        amounts = patterns.extract_amounts(text)
        assert len(amounts) > 0

    def test_amount_numeric_extraction(self, patterns):
        """Extract numeric amounts"""
        text = "La multa è di 5000 euro"
        amounts = patterns.extract_amounts(text)
        assert len(amounts) > 0


# ==========================================
# Tests: Intent Classification
# ==========================================

class TestIntentClassification:
    """Test intent classification logic"""

    @pytest.mark.asyncio
    async def test_norm_search_intent_heuristic(self, service):
        """Identify norm search intent (heuristic)"""
        query = "Che cosa dice l'art. 1321 c.c.?"
        result = await service.analyze_query(query, use_llm=False)
        assert result.intent == QueryIntentType.NORM_SEARCH
        assert result.intent_confidence > 0.5

    @pytest.mark.asyncio
    async def test_interpretation_intent_heuristic(self, service):
        """Identify interpretation intent"""
        query = "Come si interpreta il principio di responsabilità?"
        result = await service.analyze_query(query, use_llm=False)
        assert result.intent in [QueryIntentType.INTERPRETATION, QueryIntentType.NORM_SEARCH]

    @pytest.mark.asyncio
    async def test_compliance_intent(self, service):
        """Identify compliance check intent"""
        query = "Siamo in conformità con il GDPR?"
        result = await service.analyze_query(query, use_llm=False)
        assert result.intent == QueryIntentType.COMPLIANCE_CHECK
        assert result.intent_confidence > 0.7

    @pytest.mark.asyncio
    async def test_drafting_intent(self, service):
        """Identify document drafting intent"""
        query = "Dammi un template di contratto di lavoro"
        result = await service.analyze_query(query, use_llm=False)
        assert result.intent == QueryIntentType.DOCUMENT_DRAFTING
        assert result.intent_confidence > 0.7

    @pytest.mark.asyncio
    async def test_risk_spotting_intent(self, service):
        """Identify risk spotting intent"""
        query = "Quali rischi legali comporta questo contratto?"
        result = await service.analyze_query(query, use_llm=False)
        assert result.intent == QueryIntentType.RISK_SPOTTING
        assert result.intent_confidence > 0.7

    def test_heuristic_intent_low_confidence(self, service):
        """Assign low confidence for ambiguous queries"""
        intent, confidence, reasoning = service._classify_intent_heuristic(
            "Gatto nero sotto scala",
            []
        )
        assert intent == QueryIntentType.UNKNOWN
        assert confidence < 0.6


# ==========================================
# Tests: Full Query Analysis
# ==========================================

class TestFullQueryAnalysis:
    """Test complete query understanding pipeline"""

    @pytest.mark.asyncio
    async def test_italian_civil_code_query(self, service):
        """Analyze realistic Italian legal query"""
        query = "L'art. 1321 c.c. definisce il contratto. Quali sono i requisiti per la validità?"
        result = await service.analyze_query(query, use_llm=False)

        assert result.query_id is not None
        assert result.original_query == query
        assert result.intent in QueryIntentType
        assert len(result.entities) > 0
        assert len(result.norm_references) > 0
        assert result.overall_confidence > 0.0
        assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_gdpr_compliance_query(self, service):
        """Analyze GDPR compliance question"""
        query = "Siamo in compliance con art. 82 GDPR nella raccolta del consenso?"
        result = await service.analyze_query(query, use_llm=False)

        assert result.intent == QueryIntentType.COMPLIANCE_CHECK
        assert len(result.norm_references) > 0
        assert any("gdpr" in ref.lower() for ref in result.norm_references)

    @pytest.mark.asyncio
    async def test_complex_multipart_query(self, service):
        """Analyze query with multiple parts"""
        query = "Art. 1321 c.c. e Art. 1352 c.c. sui contratti. Dal 15/01/2024 quale normativa si applica?"
        result = await service.analyze_query(query, use_llm=False)

        assert len(result.norm_references) >= 2
        assert len(result.dates) > 0

    @pytest.mark.asyncio
    async def test_query_with_amounts(self, service):
        """Analyze query mentioning monetary amounts"""
        query = "Il risarcimento è di €500.000. Che dice il c.c. al riguardo?"
        result = await service.analyze_query(query, use_llm=False)

        # Should extract entities even if concept detection differs
        assert len(result.entities) > 0

    @pytest.mark.asyncio
    async def test_empty_query(self, service):
        """Handle empty query gracefully"""
        result = await service.analyze_query("", use_llm=False)
        assert result.query_length == 0
        assert result.overall_confidence >= 0.0

    @pytest.mark.asyncio
    async def test_very_short_query(self, service):
        """Handle very short query"""
        result = await service.analyze_query("Art?", use_llm=False)
        assert result.processing_time_ms > 0
        assert isinstance(result, QueryUnderstandingResult)

    @pytest.mark.asyncio
    async def test_very_long_query(self, service):
        """Handle very long query"""
        long_query = "Art. 1321 c.c. " * 100
        result = await service.analyze_query(long_query, use_llm=False)
        assert result.query_length > 1000
        assert len(result.norm_references) >= 1


# ==========================================
# Tests: Entity Handling
# ==========================================

class TestEntityHandling:
    """Test entity extraction and representation"""

    @pytest.mark.asyncio
    async def test_entity_type_classification(self, service):
        """Entities have correct types"""
        query = "Art. 1321 c.c. dal 15/01/2024"
        result = await service.analyze_query(query, use_llm=False)

        entity_types = {e.entity_type for e in result.entities}
        assert LegalEntityType.NORM_REFERENCE in entity_types or \
               LegalEntityType.DATE in entity_types

    @pytest.mark.asyncio
    async def test_entity_confidence_scores(self, service):
        """Entities have confidence scores"""
        query = "Art. 1321 c.c."
        result = await service.analyze_query(query, use_llm=False)

        for entity in result.entities:
            assert 0.0 <= entity.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_entity_positions(self, service):
        """Entities have correct start/end positions"""
        query = "Art. 1321 c.c. definisce il contratto"
        result = await service.analyze_query(query, use_llm=False)

        for entity in result.entities:
            assert entity.start_pos >= 0
            assert entity.end_pos > entity.start_pos
            assert entity.end_pos <= len(query)

    @pytest.mark.asyncio
    async def test_entity_normalization(self, service):
        """Norm entities are normalized"""
        query = "Articolo 1321 codice civile"
        result = await service.analyze_query(query, use_llm=False)

        norm_entities = [e for e in result.entities
                        if e.entity_type == LegalEntityType.NORM_REFERENCE]
        for entity in norm_entities:
            assert entity.normalized is not None


# ==========================================
# Tests: Result Serialization
# ==========================================

class TestResultSerialization:
    """Test query result serialization"""

    @pytest.mark.asyncio
    async def test_result_to_dict(self, service):
        """Convert result to dictionary"""
        query = "Art. 1321 c.c. definisce il contratto"
        result = await service.analyze_query(query, use_llm=False)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "query_id" in result_dict
        assert "original_query" in result_dict
        assert "intent" in result_dict
        assert "entities" in result_dict

    @pytest.mark.asyncio
    async def test_result_json_serializable(self, service):
        """Result is JSON serializable"""
        query = "Art. 1321 c.c."
        result = await service.analyze_query(query, use_llm=False)
        result_dict = result.to_dict()

        # Should not raise
        json_str = json.dumps(result_dict)
        assert isinstance(json_str, str)
        assert len(json_str) > 0

    @pytest.mark.asyncio
    async def test_entity_to_dict(self, service):
        """Entity serializes correctly"""
        entity = LegalEntity(
            text="Art. 1321 c.c.",
            entity_type=LegalEntityType.NORM_REFERENCE,
            start_pos=0,
            end_pos=14,
            confidence=0.95,
            normalized="cc_art_1321"
        )
        entity_dict = entity.to_dict()

        assert entity_dict["text"] == "Art. 1321 c.c."
        assert entity_dict["entity_type"] == "norm_reference"
        assert entity_dict["confidence"] == 0.95


# ==========================================
# Tests: Performance
# ==========================================

class TestPerformance:
    """Test performance characteristics"""

    @pytest.mark.asyncio
    async def test_processing_time_reasonable(self, service):
        """Query processing completes in reasonable time"""
        query = "Art. 1321 c.c. definisce il contratto"
        result = await service.analyze_query(query, use_llm=False)

        # Phase 1 heuristic should be very fast (< 100ms)
        assert result.processing_time_ms < 100

    @pytest.mark.asyncio
    async def test_multiple_queries_processing(self, service):
        """Process multiple queries efficiently"""
        queries = [
            "Art. 1321 c.c.",
            "Art. 82 GDPR",
            "Che dice il codice civile?",
        ]
        import asyncio
        results = await asyncio.gather(*[
            service.analyze_query(q, use_llm=False) for q in queries
        ])

        assert len(results) == 3
        for result in results:
            assert result.processing_time_ms > 0


# ==========================================
# Tests: Confidence Scoring
# ==========================================

class TestConfidenceScoring:
    """Test confidence scoring mechanisms"""

    @pytest.mark.asyncio
    async def test_overall_confidence_calculation(self, service):
        """Overall confidence is calculated correctly"""
        query = "Art. 1321 c.c."
        result = await service.analyze_query(query, use_llm=False)

        assert 0.0 <= result.overall_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_high_confidence_for_clear_query(self, service):
        """Clear queries have high confidence"""
        query = "What does Art. 1321 c.c. say?"
        result = await service.analyze_query(query, use_llm=False)

        # Should have reasonable confidence
        assert result.overall_confidence >= 0.3

    @pytest.mark.asyncio
    async def test_review_flag_for_low_confidence(self, service):
        """Low confidence queries flagged for review"""
        query = "xyz abc def"
        result = await service.analyze_query(query, use_llm=False)

        if result.overall_confidence < 0.75:
            assert result.needs_review is True


# ==========================================
# Tests: Integration Functions
# ==========================================

class TestIntegrationFunctions:
    """Test integration with pipeline"""

    @pytest.mark.asyncio
    async def test_singleton_service(self):
        """Service singleton works correctly"""
        service1 = get_query_understanding_service()
        service2 = get_query_understanding_service()
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_convenience_analyze_function(self):
        """Convenience analyze_query function works"""
        result = await analyze_query("Art. 1321 c.c.")
        assert isinstance(result, QueryUnderstandingResult)
        assert result.original_query == "Art. 1321 c.c."

    @pytest.mark.asyncio
    async def test_prepare_for_enrichment(self):
        """Query preparation for enrichment stage"""
        prepared = await prepare_query_for_enrichment(
            "Art. 1321 c.c. definisce il contratto"
        )

        assert "query_id" in prepared
        assert "norm_references" in prepared
        assert "legal_concepts" in prepared
        assert "intent" in prepared
        assert isinstance(prepared["overall_confidence"], float)


# ==========================================
# Tests: Edge Cases
# ==========================================

class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_query_with_special_characters(self, service):
        """Handle queries with special characters"""
        query = "Art. 1321 c.c. (come modificato) – validità!"
        result = await service.analyze_query(query, use_llm=False)
        assert result is not None

    @pytest.mark.asyncio
    async def test_query_with_urls(self, service):
        """Handle queries mentioning URLs"""
        query = "Vedi https://www.normattiva.it/ per Art. 1321 c.c."
        result = await service.analyze_query(query, use_llm=False)
        assert len(result.norm_references) > 0

    @pytest.mark.asyncio
    async def test_query_all_numbers(self, service):
        """Handle queries with many numbers"""
        query = "1321 2024 500000 15/01/2024"
        result = await service.analyze_query(query, use_llm=False)
        # Should extract entities even if intent unclear
        assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_query_repeated_patterns(self, service):
        """Handle repeated legal references"""
        query = "Art. 1321 c.c. Art. 1321 c.c. Art. 1321 c.c."
        result = await service.analyze_query(query, use_llm=False)
        # Should still parse correctly
        assert len(result.norm_references) > 0

    @pytest.mark.asyncio
    async def test_unicode_handling(self, service):
        """Handle Unicode characters correctly"""
        query = "L'art. 3 Cost. tutela l'eguaglianza"
        result = await service.analyze_query(query, use_llm=False)
        assert len(result.entities) > 0

    @pytest.mark.asyncio
    async def test_mixed_language_query(self, service):
        """Handle mixed Italian/English"""
        query = "Article 1321 c.c. defines contratto"
        result = await service.analyze_query(query, use_llm=False)
        # Should at least process without error
        assert result is not None
