"""
Specialized Legal NER Module (5-Stage Pipeline)
================================================

5-stage specialized pipeline for Italian legal text entity extraction.
Adapted from legal-ner project (github.com/user/legal-ner).

Architecture:
- Stage 1: EntityDetector (Italian_NER_XXL_v2) → Finds candidate spans
- Stage 2: LegalClassifier (Italian-legal-bert) → Classifies normative type
- Stage 3: NormativeParser (Distil-legal-bert + rules) → Structures components
- Stage 4: ReferenceResolver → Resolves incomplete references
- Stage 5: StructureBuilder → Final structured output

Supports dual-mode:
- Rule-Based: Uses NORMATTIVA mappings + semantic validation
- Fine-Tuned: Uses custom trained models for entity recognition
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, AutoModel
from sentence_transformers import SentenceTransformer
import re
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import os
import logging

# MERL-T imports
from .models import Node, Edge, EntityType, RelationType, Provenance, ValidationStatus, ExtractionResult

log = logging.getLogger(__name__)

# Costante per fonti non identificate
UNKNOWN_SOURCE = "fonte_non_identificata"

@dataclass
class TextSpan:
    """Span di testo con posizione e metadati."""
    text: str
    start_char: int
    end_char: int
    initial_confidence: float
    context_window: Optional[str] = None

@dataclass
class LegalClassification:
    """Risultato della classificazione legale."""
    span: TextSpan
    act_type: str
    confidence: float
    semantic_embedding: Optional[np.ndarray] = None

@dataclass
class ParsedNormative:
    """Componenti strutturati di una norma."""
    text: str
    act_type: str
    act_number: Optional[str] = None
    date: Optional[str] = None
    article: Optional[str] = None
    comma: Optional[str] = None
    letter: Optional[str] = None
    version: Optional[str] = None
    version_date: Optional[str] = None
    annex: Optional[str] = None
    is_complete_reference: bool = False
    confidence: float = 0.0
    start_char: int = 0
    end_char: int = 0

    def is_complete(self) -> bool:
        """Verifica se il riferimento è completo."""
        return self.act_type and self.act_number and (self.date or self.article)

@dataclass
class ResolvedNormative(ParsedNormative):
    """Norma con riferimenti risolti."""
    resolution_method: str = "direct"
    resolution_confidence: float = 1.0


class EntityDetector:
    """
    Stage 1: Usa Italian_NER_XXL_v2 per identificare span di testo
    che potrebbero essere riferimenti normativi.
    """

    def __init__(self, config: Dict[str, Any]):
        """Inizializza con configurazione esterna."""
        self.config = config
        log.info("Initializing EntityDetector with configuration")

        try:
            model_name = config.get("models", {}).get("entity_detector", {}).get("primary", "DeepMount00/Italian_NER_XXL_v2")
            self.model = AutoModelForTokenClassification.from_pretrained(model_name)
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            log.info(f"EntityDetector initialized successfully with {model_name}")
        except Exception as e:
            fallback = config.get("models", {}).get("entity_detector", {}).get("fallback", "Babelscape/wikineural-multilingual-ner")
            log.warning(f"Failed to load primary model, using fallback: {fallback}")
            self.model = AutoModelForTokenClassification.from_pretrained(fallback)
            self.tokenizer = AutoTokenizer.from_pretrained(fallback)

        # Carica mappatura NORMATTIVA dalla configurazione
        self.normattiva_mapping = self._build_flat_normattiva_mapping(
            config.get("normattiva_mapping", {})
        )
        log.info(f"NORMATTIVA mapping loaded with {len(self.normattiva_mapping)} abbreviations")

    def _build_flat_normattiva_mapping(self, normattiva_config: Dict[str, List[str]]) -> Dict[str, str]:
        """Costruisce mappatura piatta da configurazione."""
        flat_mapping = {}
        for act_type, abbreviations in normattiva_config.items():
            normalized_type = act_type.replace("_", ".")
            for abbrev in abbreviations:
                flat_mapping[abbrev] = normalized_type
        return flat_mapping

    def _get_all_regex_patterns(self) -> List[str]:
        """Restituisce tutti i pattern regex in una lista piatta."""
        all_patterns = []
        for pattern_group in self.config.get("regex_patterns", {}).values():
            all_patterns.extend(pattern_group)
        return all_patterns

    def detect_candidates(self, text: str) -> List[TextSpan]:
        """
        Trova candidati che potrebbero essere riferimenti normativi.
        Focus su PRECISIONE della posizione, non sulla classificazione.
        """
        log.debug(f"Starting entity detection for text of length {len(text)}")

        # Tokenization con offset mapping per posizione precisa
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            return_offsets_mapping=True,
            max_length=self.config.get("models", {}).get("entity_detector", {}).get("max_length", 256)
        )
        offset_mapping = inputs.pop("offset_mapping")[0]

        # Inferenza NER
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            predicted_token_class_ids = predictions.argmax(dim=-1)

        # Estrai entità con confidenze
        raw_entities = self._extract_entities_with_offsets(
            predicted_token_class_ids[0],
            predictions[0],
            offset_mapping,
            text
        )
        log.debug(f"Raw entities extracted: {len(raw_entities)}")

        # FALLBACK: Se il modello BERT non trova entità, usa rilevamento rule-based
        if not raw_entities:
            log.debug("No BERT entities found, using rule-based fallback detection")
            raw_entities = self._detect_candidates_rule_based(text)
            log.debug(f"Rule-based candidates found: {len(raw_entities)}")

        # Filtra solo candidati legali potenziali
        legal_candidates = []
        for entity in raw_entities:
            if self._is_potential_legal_reference(entity.text, text):
                expanded = self._expand_reference_boundaries(entity, text)
                legal_candidates.append(expanded)

        # Rimuovi duplicati e sovrapposizioni
        cleaned_candidates = self._remove_overlaps(legal_candidates)
        log.debug(f"Final candidates after cleaning: {len(cleaned_candidates)}")

        return cleaned_candidates

    def _detect_candidates_rule_based(self, text: str) -> List[TextSpan]:
        """
        Fallback rule-based per trovare candidati legali quando il modello BERT non trova nulla.
        """
        candidates = []

        patterns = [
            r'\bart\.?\s*\d+[a-z]*(?:-[a-z]+)?\b',
            r'\barticolo\s+\d+[a-z]*(?:-[a-z]+)?\b',
            r'\bc\.\s*c\.\b',
            r'\bc\.\s*p\.\b',
            r'\bc\.\s*p\.\s*c\.\b',
            r'\bc\.\s*p\.\s*p\.\b',
            r'\bd\.\s*l\.\s*g\.?\s*s\.?\b',
            r'\bd\.\s*l\.\b',
            r'\bd\.\s*p\.\s*r\.\b',
            r'\bd\.\s*m\.\b',
            r'\blegge\s+\d+(?:\s+del\s+\d{4})?\b',
            r'\blegge\s+costituzionale\b',
            r'\bt\.\s*u\.\b',
            r'\bdirettiva\s+(?:europea|ue|ce)\b',
            r'\bregolamento\s+(?:europeo|ue|ce)\b',
            r'\bcostituzione\b',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                candidates.append(TextSpan(
                    text=match.group(),
                    start_char=match.start(),
                    end_char=match.end(),
                    initial_confidence=0.7
                ))

        unique_candidates = []
        for candidate in candidates:
            is_duplicate = False
            for existing in unique_candidates:
                if (candidate.start_char >= existing.start_char and
                    candidate.end_char <= existing.end_char):
                    is_duplicate = True
                    break
                if (existing.start_char >= candidate.start_char and
                    existing.end_char <= candidate.end_char):
                    unique_candidates.remove(existing)
                    break

            if not is_duplicate:
                unique_candidates.append(candidate)

        return unique_candidates

    def _is_potential_legal_reference(self, text: str, full_text: str) -> bool:
        """Determina se un'entità potrebbe essere un riferimento normativo."""
        entity_lower = text.lower().strip()

        # Verifica diretta nella mappatura NORMATTIVA
        for abbrev in self.normattiva_mapping.keys():
            if abbrev.lower() in entity_lower:
                return True

        # Pattern specifici dalla configurazione
        all_patterns = self._get_all_regex_patterns()
        for pattern in all_patterns:
            if re.search(pattern, entity_lower, re.IGNORECASE):
                return True

        return False

    def _expand_reference_boundaries(self, entity: TextSpan, full_text: str) -> TextSpan:
        """Espande i confini dell'entità per catturare il riferimento normativo completo."""
        start_char = int(entity.start_char) if isinstance(entity.start_char, (torch.Tensor, np.integer)) else entity.start_char
        end_char = int(entity.end_char) if isinstance(entity.end_char, (torch.Tensor, np.integer)) else entity.end_char

        # Espandi a sinistra per catturare tipo di atto
        window_start = max(0, start_char - 50)
        left_context = full_text[window_start:start_char]

        left_patterns = [r'decreto\s+legislativo', r'decreto\s+legge', r'legge', r'd\.l\.g\.s\.']
        for pattern in left_patterns:
            match = re.search(pattern, left_context, re.IGNORECASE)
            if match:
                word_start = match.start()
                if word_start == 0 or left_context[word_start-1].isspace():
                    start_char = window_start + word_start
                    break

        # Espandi a destra per catturare data/anno
        window_end = min(len(full_text), end_char + 30)
        right_context = full_text[end_char:window_end]

        right_patterns = [r'\d{4}', r'del\s+\d{4}', r'come\s+modificato']
        for pattern in right_patterns:
            match = re.search(pattern, right_context, re.IGNORECASE)
            if match:
                end_char = end_char + match.end()
                break

        expanded_text = full_text[start_char:end_char].strip()
        expanded_text = re.sub(r'^[\W\s]+', '', expanded_text)
        expanded_text = re.sub(r'[\W\s.,:;)]+$', '', expanded_text)
        expanded_text = expanded_text.strip()

        if expanded_text != full_text[start_char:end_char].strip():
            clean_start = full_text.find(expanded_text, start_char)
            if clean_start != -1:
                start_char = clean_start
                end_char = clean_start + len(expanded_text)

        return TextSpan(
            text=expanded_text,
            start_char=start_char,
            end_char=end_char,
            initial_confidence=float(entity.initial_confidence) if isinstance(entity.initial_confidence, (np.floating, np.integer)) else entity.initial_confidence,
            context_window=full_text[
                max(0, start_char - 100):
                min(len(full_text), end_char + 100)
            ]
        )

    def _extract_entities_with_offsets(self, predicted_ids, predictions, offset_mapping, text):
        """Estrae entità con posizioni precise usando offset mapping."""
        entities = []
        current_entity = None

        for i, (token_id, token_probs) in enumerate(zip(predicted_ids, predictions)):
            if i >= len(offset_mapping):
                break

            start_offset, end_offset = offset_mapping[i]

            if isinstance(start_offset, torch.Tensor):
                start_offset = int(start_offset.item())
            else:
                start_offset = int(start_offset)

            if isinstance(end_offset, torch.Tensor):
                end_offset = int(end_offset.item())
            else:
                end_offset = int(end_offset)

            if start_offset == end_offset:
                continue

            label = self.model.config.id2label.get(token_id.item(), 'O')
            confidence = torch.max(token_probs).item()
            confidence = float(confidence)

            if label.startswith('B-'):
                if current_entity:
                    entities.append(current_entity)

                current_entity = TextSpan(
                    text=text[start_offset:end_offset],
                    start_char=start_offset,
                    end_char=end_offset,
                    initial_confidence=confidence
                )
            elif label.startswith('I-') and current_entity:
                current_entity.text = text[current_entity.start_char:end_offset]
                current_entity.end_char = end_offset
                current_entity.initial_confidence = float((current_entity.initial_confidence + confidence) / 2)
            else:
                if current_entity:
                    entities.append(current_entity)
                    current_entity = None

        if current_entity:
            entities.append(current_entity)

        return entities

    def _remove_overlaps(self, candidates: List[TextSpan]) -> List[TextSpan]:
        """Rimuove candidati sovrapposti, mantenendo quello con confidence maggiore."""
        if not candidates:
            return []

        sorted_candidates = sorted(candidates, key=lambda x: x.start_char)
        cleaned = [sorted_candidates[0]]

        for candidate in sorted_candidates[1:]:
            last = cleaned[-1]

            if candidate.start_char < last.end_char:
                if candidate.initial_confidence > last.initial_confidence:
                    cleaned[-1] = candidate
            else:
                cleaned.append(candidate)

        return cleaned


class LegalClassifier:
    """
    Stage 2: Classifica il tipo di riferimento normativo usando regole + semantica.
    Supporta sia modelli fine-tuned che classificazione rule-based.
    """

    def __init__(self, config: Dict[str, Any], fine_tuned_model_path: Optional[str] = None):
        """Inizializza con configurazione esterna e opzionale modello fine-tuned."""
        self.config = config
        self.fine_tuned_model_path = fine_tuned_model_path
        self.use_fine_tuned = fine_tuned_model_path is not None

        log.info(f"Initializing LegalClassifier (fine-tuned={self.use_fine_tuned})")

        # Carica modello per embeddings semantici
        try:
            model_name = config.get("models", {}).get("legal_classifier", {}).get("primary", "dlicari/distil-ita-legal-bert")
            self.model = AutoModel.from_pretrained(model_name)
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            log.info(f"Semantic model initialized successfully with {model_name}")
        except Exception as e:
            log.warning(f"Failed to load semantic model: {e}")
            self.model = None
            self.tokenizer = None

        # Carica modello fine-tuned se fornito
        self.fine_tuned_model = None
        self.fine_tuned_tokenizer = None
        self.label_config = None

        if self.use_fine_tuned:
            try:
                self.fine_tuned_model = AutoModelForTokenClassification.from_pretrained(
                    fine_tuned_model_path,
                    local_files_only=True
                )
                self.fine_tuned_tokenizer = AutoTokenizer.from_pretrained(
                    fine_tuned_model_path,
                    local_files_only=True
                )

                label_config_path = os.path.join(fine_tuned_model_path, "label_config.json")
                if os.path.exists(label_config_path):
                    with open(label_config_path, 'r') as f:
                        self.label_config = json.load(f)
                    log.info(f"Fine-tuned model loaded: {fine_tuned_model_path}")
                else:
                    self.label_config = {
                        "id2label": self.fine_tuned_model.config.id2label,
                        "label2id": self.fine_tuned_model.config.label2id
                    }
            except Exception as e:
                log.error(f"Failed to load fine-tuned model: {e}")
                self.use_fine_tuned = False
                self.fine_tuned_model = None
                self.fine_tuned_tokenizer = None

        # Costruisci il set di regole
        self._build_ruleset()
        log.info(f"LegalClassifier initialized with {len(self.rules)} rules")

    def _build_ruleset(self):
        """Costruisce un set di regole prioritizzate dalla configurazione."""
        self.rules = []
        rule_conf = self.config.get("confidence_thresholds", {}).get("rule_based_confidence", {})

        normattiva_mapping = self.config.get("normattiva_mapping", {})

        for act_type, abbreviations in normattiva_mapping.items():
            abbreviations_sorted = sorted(abbreviations, key=len, reverse=True)
            for abbrev in abbreviations_sorted:
                pattern = re.compile(r'\b' + re.escape(abbrev) + r'\b', re.IGNORECASE)
                confidence = rule_conf.get(act_type, 0.85)
                self.rules.append((pattern, act_type, confidence))

    def classify_legal_type(self, text_span: TextSpan, context: str) -> LegalClassification:
        """Classifica il tipo di entità normativa."""
        log.debug(f"Classifying: {text_span.text[:50]}")

        # Se fine-tuned model disponibile, usalo prioritariamente
        if self.use_fine_tuned:
            fine_tuned_result = self._classify_by_fine_tuned_model(text_span)
            if fine_tuned_result:
                return fine_tuned_result

        # Fallback a rule-based
        return self._classify_by_rules(text_span)

    def _classify_by_rules(self, text_span: TextSpan) -> LegalClassification:
        """Classificazione rule-based usando il ruleset."""
        text_lower = text_span.text.lower()

        for pattern, act_type, confidence in self.rules:
            if pattern.search(text_lower):
                return LegalClassification(
                    span=text_span,
                    act_type=act_type,
                    confidence=confidence,
                    semantic_embedding=None
                )

        return LegalClassification(
            span=text_span,
            act_type=UNKNOWN_SOURCE,
            confidence=0.5,
            semantic_embedding=None
        )

    def _classify_by_fine_tuned_model(self, text_span: TextSpan) -> Optional[LegalClassification]:
        """Classificazione con modello fine-tuned."""
        if not self.use_fine_tuned or self.fine_tuned_model is None:
            return None

        try:
            inputs = self.fine_tuned_tokenizer(
                text_span.text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
                return_offsets_mapping=True
            )
            offset_mapping = inputs.pop("offset_mapping")[0]

            with torch.no_grad():
                outputs = self.fine_tuned_model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                predicted_ids = predictions.argmax(dim=-1)[0]

            id2label = self.label_config.get("id2label", {})

            entities = []
            current_entity = None

            for i, token_id in enumerate(predicted_ids):
                if i >= len(offset_mapping):
                    break

                start_offset, end_offset = offset_mapping[i]
                if start_offset == end_offset:
                    continue

                label = id2label.get(str(token_id.item()), "O")
                confidence = predictions[0][i][token_id].item()

                if label.startswith("B-"):
                    if current_entity:
                        entities.append(current_entity)

                    act_type = label[2:]
                    current_entity = {
                        "act_type": act_type,
                        "confidences": [confidence],
                        "token_count": 1
                    }
                elif label.startswith("I-") and current_entity:
                    act_type = label[2:]
                    if act_type == current_entity["act_type"]:
                        current_entity["confidences"].append(confidence)
                        current_entity["token_count"] += 1
                else:
                    if current_entity:
                        entities.append(current_entity)
                        current_entity = None

            if current_entity:
                entities.append(current_entity)

            if not entities:
                return None

            best_entity = max(entities, key=lambda e: sum(e["confidences"]) / len(e["confidences"]))
            avg_confidence = sum(best_entity["confidences"]) / len(best_entity["confidences"])

            return LegalClassification(
                span=text_span,
                act_type=best_entity["act_type"],
                confidence=avg_confidence,
                semantic_embedding=None
            )

        except Exception as e:
            log.error(f"Error in fine-tuned classification: {e}")
            return None


class NormativeParser:
    """
    Stage 3: Estrae componenti strutturati da riferimenti normativi classificati.
    """
    def __init__(self, config: Dict[str, Any]):
        """Inizializza con configurazione esterna."""
        self.config = config
        log.info("Initializing NormativeParser")

    def parse(self, legal_classification: LegalClassification) -> ParsedNormative:
        """Estrae componenti strutturati da una classificazione legale."""
        text = legal_classification.span.text
        parsed_data = {
            "text": text,
            "act_type": legal_classification.act_type,
            "confidence": legal_classification.confidence,
            "start_char": legal_classification.span.start_char,
            "end_char": legal_classification.span.end_char
        }

        text_lower = text.lower()

        # Pattern per articoli
        article_match = re.search(r'art\.?\s*(\d+[a-z]*)', text_lower)
        if article_match:
            parsed_data["article"] = article_match.group(1)

        # Pattern per commi
        comma_match = re.search(r'comma\s+(\d+)', text_lower)
        if comma_match:
            parsed_data["comma"] = comma_match.group(1)

        # Pattern per lettere
        letter_match = re.search(r'lett\.?\s*([a-z])', text_lower)
        if letter_match:
            parsed_data["letter"] = letter_match.group(1)

        # Pattern per numeri di decreto
        number_match = re.search(r'(\d+)\s*/\s*(\d{4})', text_lower)
        if number_match:
            parsed_data["act_number"] = number_match.group(1)
            parsed_data["date"] = number_match.group(2)

        # Pattern per date
        date_match = re.search(r'del\s+(\d{1,2})\s+([a-z]+)\s+(\d{4})', text_lower)
        if date_match and not parsed_data.get("date"):
            parsed_data["date"] = f"{date_match.group(1)}/{date_match.group(2)}/{date_match.group(3)}"

        is_complete = parsed_data.get("act_number") and (parsed_data.get("date") or parsed_data.get("article"))
        parsed_data["is_complete_reference"] = is_complete

        return ParsedNormative(**parsed_data)


class ReferenceResolver:
    """
    Stage 4: Risolve riferimenti incompleti o ambigui usando il contesto.
    """
    def __init__(self, config: Dict[str, Any]):
        """Inizializza con configurazione esterna."""
        self.config = config
        log.info("Initializing ReferenceResolver")

    def resolve(self, parsed_normative: ParsedNormative, full_text: str) -> ResolvedNormative:
        """Risolve riferimenti incompleti basandosi sul contesto."""
        resolved_data = asdict(parsed_normative)
        resolved_data["resolution_method"] = "direct"
        resolved_data["resolution_confidence"] = 1.0
        return ResolvedNormative(**resolved_data)


class StructureBuilder:
    """
    Stage 5: Costruisce l'output finale strutturato.
    """
    def __init__(self, config: Dict[str, Any]):
        """Inizializza con configurazione esterna."""
        self.config = config
        log.info("Initializing StructureBuilder")

    def build(self, resolved_normative: ResolvedNormative) -> Dict[str, Any]:
        """Costruisce l'output strutturato finale."""
        structured_output = {
            "source_type": resolved_normative.act_type,
            "text": resolved_normative.text,
            "confidence": resolved_normative.confidence,
            "start_char": resolved_normative.start_char,
            "end_char": resolved_normative.end_char,
            "act_type": resolved_normative.act_type,
            "date": resolved_normative.date,
            "act_number": resolved_normative.act_number,
            "article": resolved_normative.article,
            "comma": resolved_normative.comma,
            "letter": resolved_normative.letter,
            "version": resolved_normative.version,
            "version_date": resolved_normative.version_date,
            "annex": resolved_normative.annex,
            "is_complete_reference": resolved_normative.is_complete_reference
        }

        # Filtra null values se configurato
        if self.config.get("output", {}).get("filter_null_values", True):
            return {k: v for k, v in structured_output.items() if v is not None}

        return structured_output


class LegalSourceExtractionPipeline:
    """
    Pipeline principale che coordina tutti gli stage specializzati.

    Supporta sia approccio rule-based che fine-tuned model.
    """

    def __init__(self, config: Dict[str, Any], fine_tuned_model_path: Optional[str] = None):
        """
        Inizializza pipeline con configurazione esterna.

        Args:
            config: Configurazione della pipeline (Dict)
            fine_tuned_model_path: Path al modello fine-tunato (opzionale)
        """
        log.info(f"Initializing LegalSourceExtractionPipeline (fine-tuned={fine_tuned_model_path is not None})")

        self.config = config
        self.fine_tuned_model_path = fine_tuned_model_path

        # Inizializza i componenti della pipeline
        self.entity_detector = EntityDetector(self.config)
        self.legal_classifier = LegalClassifier(self.config, fine_tuned_model_path=fine_tuned_model_path)
        self.normative_parser = NormativeParser(self.config)
        self.reference_resolver = ReferenceResolver(self.config)
        self.structure_builder = StructureBuilder(self.config)

        log.info("LegalSourceExtractionPipeline initialized successfully")

    def _is_spurious_entity(self, candidate: TextSpan) -> bool:
        """Filtra entità spurie usando configurazione."""
        text = candidate.text.strip()

        # Min length check
        if len(text) <= 2 and text.lower() not in ['c.c.', 'c.p.', 'd.l.']:
            return True

        # Single character check
        if len(text) == 1 and text.isalpha():
            return True

        # Spurious words
        spurious_words = {'il', 'la', 'del', 'di', 'da', 'e', 'o', 'un', 'una'}
        if text.lower() in spurious_words:
            return True

        return False

    async def extract_legal_sources(self, text: str) -> List[Dict[str, Any]]:
        """
        Estrae entità legali usando la pipeline specializzata.

        NUOVA LOGICA: Se modello fine-tuned disponibile, bypassa EntityDetector
        e lavora direttamente sul testo.
        """
        log.info(f"Starting legal source extraction (text_length={len(text)}, use_fine_tuned={self.legal_classifier.use_fine_tuned})")

        # Se abbiamo modello fine-tuned, lo usiamo direttamente
        if self.legal_classifier.use_fine_tuned:
            log.info("Using fine-tuned model directly (bypassing EntityDetector)")
            # TODO: Implementare extract_all_entities_from_text quando modelli disponibili
            classified_entities = []
        else:
            # STRATEGIA LEGACY: Usa pipeline a 2 stadi (EntityDetector → LegalClassifier)
            log.info("Using legacy 2-stage pipeline (EntityDetector + rule-based classifier)")

            # Stage 1: Detect candidates
            candidates = self.entity_detector.detect_candidates(text)
            log.info(f"Entity detection completed: {len(candidates)} candidates found")

            # Stage 2: Classify legal types
            classified_entities = []
            for candidate in candidates:
                if self._is_spurious_entity(candidate):
                    log.debug(f"Filtered spurious entity: {candidate.text}")
                    continue
                classification = self.legal_classifier.classify_legal_type(candidate, text)
                if classification and classification.act_type != UNKNOWN_SOURCE:
                    classified_entities.append(classification)
                    log.debug(f"Classified: {candidate.text} → {classification.act_type}")

        log.info(f"Entity classification completed: {len(classified_entities)} entities classified")

        # Stage 3: Parse normative components
        parsed_normatives = []
        for classification in classified_entities:
            parsed = self.normative_parser.parse(classification)
            parsed_normatives.append(parsed)

        # Stage 4: Resolve incomplete references
        resolved_normatives = []
        for parsed in parsed_normatives:
            resolved = self.reference_resolver.resolve(parsed, text)
            resolved_normatives.append(resolved)

        # Stage 5: Build final structured output
        final_results = []
        for resolved in resolved_normatives:
            structured_output = self.structure_builder.build(resolved)
            if structured_output:
                final_results.append(structured_output)
                log.debug(f"Built structured output: {resolved.text}")

        log.info(f"Extraction completed: {len(final_results)} final results")
        return final_results

    def to_extraction_result(self, text: str, extraction_results: List[Dict[str, Any]]) -> ExtractionResult:
        """
        Converte i risultati dell'estrazione in ExtractionResult (MERL-T format).

        Crea Node per ogni entità normalizzata e Edge per relazioni.
        """
        nodes = []
        edges = []
        stats = {"total_entities": len(extraction_results)}

        provenance = Provenance(
            source_type="ner_pipeline",
            extraction_method="automatic",
            extraction_timestamp=datetime.now(),
            extractor_version="1.0.0",
            raw_text=text
        )

        for idx, result in enumerate(extraction_results):
            # Crea un Node per ogni entità
            node = Node(
                id=f"ner_entity_{idx}",
                label=result.get("text", ""),
                entity_type=EntityType.NORMA,  # Mappare result["act_type"] a EntityType
                description=f"Fonte normativa: {result.get('act_type', 'unknown')}",
                article_number=result.get("article"),
                law_reference=result.get("act_number"),
                provenance=provenance,
                confidence=result.get("confidence", 0.0),
                validation_status=ValidationStatus.PENDING,
                tags={result.get("act_type", "unknown")}
            )
            nodes.append(node)

        return ExtractionResult(
            nodes=nodes,
            edges=edges,
            extraction_stats=stats
        )
