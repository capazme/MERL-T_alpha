"""
Enrichment Extractors
=====================

Estrattori LLM-based per entità giuridiche.

Estrattori disponibili:
- ConceptExtractor: Estrae concetti giuridici (buona fede, dolo, etc.)
- PrincipleExtractor: Estrae principi giuridici (affidamento, etc.)
- DefinitionExtractor: Estrae definizioni legali esplicite
- GenericExtractor: Estrattore generico per tutti i tipi di entità

Factory:
- create_extractor: Crea l'estrattore appropriato per un tipo di entità

Esempio:
    from merlt.pipeline.enrichment.extractors import create_extractor
    from merlt.pipeline.enrichment.models import EntityType

    # Usa la factory per creare l'estrattore appropriato
    extractor = create_extractor(llm_service, EntityType.SOGGETTO)
    entities = await extractor.extract(content)
"""

from merlt.pipeline.enrichment.extractors.base import BaseEntityExtractor
from merlt.pipeline.enrichment.extractors.concept import ConceptExtractor
from merlt.pipeline.enrichment.extractors.principle import PrincipleExtractor
from merlt.pipeline.enrichment.extractors.definition import DefinitionExtractor
from merlt.pipeline.enrichment.extractors.generic import (
    GenericExtractor,
    create_extractor,
)

__all__ = [
    "BaseEntityExtractor",
    "ConceptExtractor",
    "PrincipleExtractor",
    "DefinitionExtractor",
    "GenericExtractor",
    "create_extractor",
]
