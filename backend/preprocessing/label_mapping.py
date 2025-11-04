"""
Dynamic Legal Label Mapping System
===================================

Hot-reloadable label mapping for entity classification.
Supports both traditional Italian legal act types and semantic ontology labels.

Adapted from legal-ner project (github.com/user/legal-ner).
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import yaml
import logging
from pathlib import Path

log = logging.getLogger(__name__)


class LabelCategory(Enum):
    """Label categories for semantic organization."""
    ACT_TYPE = "act_type"              # Traditional: decreto_legislativo, legge, etc.
    LEGAL_SOURCE = "legal_source"      # Semantic: fonte_normativa, fonte_giurisdizionale
    LEGAL_CONCEPT = "legal_concept"    # Semantic: istituto, principio, diritto
    INSTITUTION = "institution"         # Semantic: organo_costituzionale
    PERSON = "person"                  # Semantic: persona_fisica, persona_giuridica
    CRIME = "crime"                    # Semantic: reato
    OTHER = "other"


@dataclass
class LabelMetadata:
    """Metadata per ogni label nel sistema."""
    label: str
    category: LabelCategory
    display_name: str
    description: Optional[str] = None
    synonyms: List[str] = None
    confidence_bias: float = 0.0  # Boost/penalty per confidence scoring
    priority: int = 0  # Higher = prioritized in classification

    def __post_init__(self):
        if self.synonyms is None:
            self.synonyms = []


class LabelMappingManager:
    """
    Manages dynamic label mappings with hot-reload support.

    Supports two label systems:
    1. Traditional Act Types: decreto_legislativo, legge, codice_civile, etc.
    2. Semantic Ontology: fonte_normativa, istituto, persona_fisica, etc.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize label mapping system.

        Args:
            config_path: Path to label mapping YAML config (optional)
        """
        self.config_path = config_path
        self.act_type_to_label: Dict[str, str] = {}
        self.label_to_act_type: Dict[str, str] = {}
        self.label_metadata: Dict[str, LabelMetadata] = {}
        self.custom_labels: Dict[str, str] = {}

        log.info("Initializing LabelMappingManager")

        # Load default mappings
        self._load_default_mappings()

        # Load config if provided
        if config_path and Path(config_path).exists():
            self._load_from_yaml(config_path)
            log.info(f"Loaded custom label mappings from {config_path}")

    def _load_default_mappings(self):
        """Load default Italian legal label mappings."""
        # Traditional ACT TYPE → Display LABEL mappings
        default_act_types = {
            # Decreti
            "decreto_legislativo": "D.LGS.",
            "decreto_legge": "D.L.",
            "decreto_presidente_repubblica": "D.P.R.",
            "decreto_ministeriale": "D.M.",
            "decreto_presidente_consiglio": "D.P.C.M.",
            "decreto_dirigenziale": "D.D.",

            # Leggi
            "legge": "L.",
            "legge_fallimentare": "L.F.",
            "legge_costituzionale": "L.COST.",
            "legge_regionale": "L.R.",

            # Codici
            "codice_civile": "C.C.",
            "codice_penale": "C.P.",
            "codice_procedura_civile": "C.P.C.",
            "codice_procedura_penale": "C.P.P.",
            "codice_amministrativo": "COD. AMM.",
            "codice_ambiente": "COD. AMB.",
            "codice_crisi_impresa": "C.C.I.I.",

            # Testi Unici
            "testo_unico_bancario": "T.U.B.",
            "testo_unico_finanza": "T.U.F.",
            "testo_unico_enti_locali": "T.U.E.L.",

            # Costituzione e normativa superiore
            "costituzione": "COST.",
            "direttiva_ue": "DIR. UE",
            "regolamento_ue": "REG. UE",

            # Delibere
            "delibera_giunta_regionale": "D.G.R.",
            "delibera_consiglio_regionale": "D.C.R.",
            "delibera_giunta_comunale": "D.G.C.",
            "delibera_consiglio_comunale": "D.C.C.",

            # Fallback
            "unknown": "UNKNOWN",
            "fonte_non_identificata": "UNKNOWN"
        }

        for act_type, label in default_act_types.items():
            self.act_type_to_label[act_type] = label
            self.label_to_act_type[label] = act_type

        # Semantic ontology labels (alternative system for fine-tuned models)
        semantic_labels = {
            "fonte_normativa": LabelMetadata(
                label="fonte_normativa",
                category=LabelCategory.LEGAL_SOURCE,
                display_name="Legal Norm Source",
                description="Reference to legislative act (law, decree, etc.)",
                priority=10
            ),
            "fonte_giurisdizionale": LabelMetadata(
                label="fonte_giurisdizionale",
                category=LabelCategory.LEGAL_SOURCE,
                display_name="Case Law Source",
                description="Reference to court decisions or case law",
                priority=9
            ),
            "fonte_amministrativa": LabelMetadata(
                label="fonte_amministrativa",
                category=LabelCategory.LEGAL_SOURCE,
                display_name="Administrative Source",
                description="Reference to administrative acts",
                priority=8
            ),
            "persona_fisica": LabelMetadata(
                label="persona_fisica",
                category=LabelCategory.PERSON,
                display_name="Natural Person",
                description="Reference to an individual person",
                priority=7
            ),
            "persona_giuridica": LabelMetadata(
                label="persona_giuridica",
                category=LabelCategory.PERSON,
                display_name="Legal Entity",
                description="Reference to a legal entity or organization",
                priority=7
            ),
            "organo_costituzionale": LabelMetadata(
                label="organo_costituzionale",
                category=LabelCategory.INSTITUTION,
                display_name="Constitutional Body",
                description="Reference to a constitutional institution",
                priority=10
            ),
            "istituto": LabelMetadata(
                label="istituto",
                category=LabelCategory.LEGAL_CONCEPT,
                display_name="Legal Institute",
                description="Legal concept or institute (e.g., property, contract)",
                priority=6
            ),
            "reato": LabelMetadata(
                label="reato",
                category=LabelCategory.CRIME,
                display_name="Crime",
                description="Reference to a specific crime or offense",
                priority=8
            ),
            "bene_giuridico_protetto": LabelMetadata(
                label="bene_giuridico_protetto",
                category=LabelCategory.LEGAL_CONCEPT,
                display_name="Protected Legal Interest",
                description="A legally protected good or interest",
                priority=5
            ),
            "principio": LabelMetadata(
                label="principio",
                category=LabelCategory.LEGAL_CONCEPT,
                display_name="Legal Principle",
                description="General legal principle or doctrine",
                priority=6
            ),
            "regola": LabelMetadata(
                label="regola",
                category=LabelCategory.LEGAL_CONCEPT,
                display_name="Legal Rule",
                description="Specific legal rule or norm",
                priority=6
            ),
            "diritto": LabelMetadata(
                label="diritto",
                category=LabelCategory.LEGAL_CONCEPT,
                display_name="Right",
                description="A right conferred by law",
                priority=6
            ),
        }

        for label_name, metadata in semantic_labels.items():
            self.label_metadata[label_name] = metadata

        log.info(f"Loaded {len(self.act_type_to_label)} act type mappings and {len(semantic_labels)} semantic labels")

    def _load_from_yaml(self, config_path: str):
        """Load custom label mappings from YAML file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if not config:
                log.warning(f"Empty YAML config at {config_path}")
                return

            # Load act type mappings
            if "act_type_to_label" in config:
                for act_type, label in config["act_type_to_label"].items():
                    self.act_type_to_label[act_type] = label
                    self.label_to_act_type[label] = act_type
                log.info(f"Loaded {len(config['act_type_to_label'])} custom act type mappings")

            # Load semantic labels metadata
            if "semantic_labels" in config:
                for label_name, metadata_dict in config["semantic_labels"].items():
                    category = LabelCategory(metadata_dict.get("category", "other"))
                    metadata = LabelMetadata(
                        label=label_name,
                        category=category,
                        display_name=metadata_dict.get("display_name", label_name),
                        description=metadata_dict.get("description"),
                        synonyms=metadata_dict.get("synonyms", []),
                        confidence_bias=metadata_dict.get("confidence_bias", 0.0),
                        priority=metadata_dict.get("priority", 0)
                    )
                    self.label_metadata[label_name] = metadata
                log.info(f"Loaded {len(config['semantic_labels'])} custom semantic labels")

        except Exception as e:
            log.error(f"Failed to load label mappings from {config_path}: {e}")

    def act_type_to_label(self, act_type: str) -> str:
        """
        Convert internal act_type to display label.

        Args:
            act_type: Internal act type identifier (e.g., "decreto_legislativo")

        Returns:
            Display label (e.g., "D.LGS."), or normalized act_type if not found
        """
        if act_type in self.act_type_to_label:
            return self.act_type_to_label[act_type]

        # Fallback to uppercase normalization
        return act_type.upper().replace("_", " ")

    def label_to_act_type(self, label: str) -> Optional[str]:
        """
        Convert display label back to internal act_type.

        Args:
            label: Display label (e.g., "D.LGS.")

        Returns:
            Internal act type, or None if not found
        """
        return self.label_to_act_type.get(label)

    def get_label_metadata(self, label: str) -> Optional[LabelMetadata]:
        """Get metadata for a semantic label."""
        return self.label_metadata.get(label)

    def get_labels_by_category(self, category: LabelCategory) -> List[str]:
        """Get all labels in a specific category."""
        return [
            label for label, metadata in self.label_metadata.items()
            if metadata.category == category
        ]

    def register_custom_label(self, act_type: str, display_label: str, category: LabelCategory = LabelCategory.OTHER):
        """
        Register a new custom label without file changes.

        Args:
            act_type: Internal act type identifier
            display_label: Display label
            category: Label category for organization
        """
        self.act_type_to_label[act_type] = display_label
        self.label_to_act_type[display_label] = act_type
        self.custom_labels[act_type] = display_label

        # Create metadata
        metadata = LabelMetadata(
            label=act_type,
            category=category,
            display_name=display_label,
            description=f"Custom label: {display_label}"
        )
        self.label_metadata[act_type] = metadata

        log.info(f"Registered custom label: {act_type} → {display_label}")

    def update_label_mapping(self, act_type: str, display_label: str, category: str = 'other'):
        """
        Update or create a label mapping.

        Args:
            act_type: Internal act type identifier
            display_label: Display label
            category: Category name
        """
        try:
            category_enum = LabelCategory(category)
        except ValueError:
            category_enum = LabelCategory.OTHER

        self.register_custom_label(act_type, display_label, category_enum)

    def get_all_act_types(self) -> List[str]:
        """Get list of all registered act types."""
        return list(self.act_type_to_label.keys())

    def get_all_labels(self) -> List[str]:
        """Get list of all display labels."""
        return list(self.label_to_act_type.keys())

    def get_semantic_ontology(self) -> Dict[str, Dict]:
        """
        Get complete semantic ontology.

        Returns:
            Dict mapping labels to metadata dicts
        """
        return {
            label: {
                "category": metadata.category.value,
                "display_name": metadata.display_name,
                "description": metadata.description,
                "synonyms": metadata.synonyms,
                "priority": metadata.priority,
                "confidence_bias": metadata.confidence_bias
            }
            for label, metadata in self.label_metadata.items()
        }

    def export_to_yaml(self, output_path: str):
        """
        Export current mappings to YAML file.

        Args:
            output_path: Path where to save the YAML file
        """
        config = {
            "act_type_to_label": self.act_type_to_label,
            "semantic_labels": self.get_semantic_ontology()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        log.info(f"Exported label mappings to {output_path}")

    def validate_label(self, label: str) -> bool:
        """Check if a label is valid in either system."""
        return (label in self.label_to_act_type or
                label in self.label_metadata or
                label in self.act_type_to_label)

    def __repr__(self) -> str:
        return (
            f"LabelMappingManager("
            f"act_types={len(self.act_type_to_label)}, "
            f"semantic_labels={len(self.label_metadata)}, "
            f"custom_labels={len(self.custom_labels)})"
        )


# Singleton instance for application-wide use
_label_manager: Optional[LabelMappingManager] = None


def get_label_manager(config_path: Optional[str] = None) -> LabelMappingManager:
    """
    Get or create the global label mapping manager.

    Args:
        config_path: Optional path to label mapping YAML config

    Returns:
        Singleton LabelMappingManager instance
    """
    global _label_manager

    if _label_manager is None:
        _label_manager = LabelMappingManager(config_path)

    return _label_manager


def reload_label_manager(config_path: str):
    """
    Reload label mappings from config file (hot-reload).

    Args:
        config_path: Path to label mapping YAML config
    """
    global _label_manager
    _label_manager = LabelMappingManager(config_path)
    log.info(f"Label manager reloaded from {config_path}")
