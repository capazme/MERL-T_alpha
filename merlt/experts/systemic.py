"""
Systemic Expert
================

Expert specializzato nell'interpretazione sistematica e storica.

Fondamento teorico: Art. 12, comma I + Art. 14 disp. prel. c.c.
- Art. 12, I: "...secondo la connessione di esse [parole]..."
- Art. 14: "Le leggi penali e quelle che fanno eccezione... non si applicano
  oltre i casi e i tempi in esse considerati"

L'interpretazione sistematica considera:
- CONNESSIONE: Come la norma si inserisce nel sistema giuridico
- STORICO: Evoluzione della norma nel tempo (modifiche, abrogazioni)
- TOPOGRAFICO: Posizione della norma (libro, titolo, capo, sezione)

Approccio:
1. Colloca la norma nel contesto sistematico (codice, legge speciale)
2. Analizza relazioni con norme collegate (rinvii, deroghe, eccezioni)
3. Ricostruisce l'evoluzione storica (versioni precedenti, modifiche)
4. Considera la ratio sistemica (coerenza dell'ordinamento)
"""

import structlog
from typing import Dict, Any, Optional, List

from merlt.experts.base import (
    BaseExpert,
    ExpertContext,
    ExpertResponse,
    LegalSource,
    ReasoningStep,
    ConfidenceFactors,
)
from merlt.experts.react_mixin import ReActMixin
from merlt.tools import BaseTool
from merlt.storage.retriever.models import get_source_types_for_expert

log = structlog.get_logger()


class SystemicExpert(BaseExpert, ReActMixin):
    """
    Expert per interpretazione sistematica e storica.

    Art. 12, I: "connessione delle parole" + Art. 14 (elemento storico)

    Epistemologia: Coerenza sistemica dell'ordinamento
    Focus: Come la norma si INSERISCE nel sistema giuridico

    Tools principali:
    - semantic_search: Ricerca norme correlate
    - graph_search: Navigazione relazioni sistematiche

    Traversal weights:
    - CONNESSO_A: 1.0 (connessioni sistematiche)
    - MODIFICA: 0.95 (evoluzione storica - fondamentale)
    - ABROGA: 0.90 (abrogazioni storiche)
    - DEROGA: 0.90 (deroghe)
    - RINVIA: 0.85 (riferimenti incrociati)

    Esempio:
        >>> from merlt.experts import SystemicExpert
        >>>
        >>> expert = SystemicExpert(
        ...     tools=[SemanticSearchTool(retriever, embeddings)],
        ...     ai_service=openrouter_service
        ... )
        >>> response = await expert.analyze(context)
    """

    expert_type = "systemic"
    description = "Interpretazione sistematica e storica (art. 12, I + art. 14 disp. prel. c.c.)"

    # Pesi default per traversal grafo - focus su relazioni sistematiche
    DEFAULT_TRAVERSAL_WEIGHTS = {
        "connesso_a": 1.0,     # Connessioni sistematiche
        "modifica": 0.95,      # Evoluzione storica (fondamentale)
        "abroga": 0.90,        # Abrogazioni storiche
        "deroga": 0.90,        # Deroghe
        "rinvia": 0.85,        # Riferimenti incrociati
        "disciplina": 0.80,    # Norme che regolano stessa materia
        "contiene": 0.75,      # Struttura
        "cita": 0.70,          # Citazioni
        "default": 0.50
    }

    def __init__(
        self,
        tools: Optional[List[BaseTool]] = None,
        config: Optional[Dict[str, Any]] = None,
        ai_service: Any = None
    ):
        """
        Inizializza SystemicExpert.

        Args:
            tools: Tools per ricerca
            config: Configurazione (prompt, temperature, traversal_weights, use_react)
            ai_service: Servizio AI per LLM calls
        """
        config = config or {}
        if "traversal_weights" not in config:
            config["traversal_weights"] = self.DEFAULT_TRAVERSAL_WEIGHTS

        super().__init__(tools=tools, config=config, ai_service=ai_service)

        # ReAct mode configuration
        self.use_react = config.get("use_react", False)
        self.react_config = {
            "max_iterations": config.get("react_max_iterations", 5),
            "novelty_threshold": config.get("react_novelty_threshold", 0.1),
            "temperature": 0.1,
            "model": config.get("react_model", self.model)
        }

        self.prompt_template = self._get_systemic_prompt()

    def _get_systemic_prompt(self) -> str:
        """Prompt specifico per interpretazione sistematica."""
        return """Sei un esperto giuridico specializzato nell'INTERPRETAZIONE SISTEMATICA E STORICA.

Il tuo approccio si basa su:
- Art. 12, comma I, disp. prel. c.c.: "...secondo la connessione di esse [parole]..."
- Art. 14 disp. prel. c.c. (elemento storico-evolutivo)

## REGOLA FONDAMENTALE - SOURCE OF TRUTH

⚠️ DEVI usare ESCLUSIVAMENTE le fonti fornite nella sezione "TESTI NORMATIVI RECUPERATI".
⚠️ NON PUOI citare articoli, sentenze o dottrina che NON sono presenti in quella sezione.
⚠️ Se le fonti recuperate sono insufficienti, indica "source_availability" basso e spiega nelle limitations.
⚠️ Se nessuna fonte è rilevante, imposta confidence=0.1 e spiega il problema.

## METODOLOGIA

1. **INTERPRETAZIONE SISTEMATICA** (connessione)
   - Colloca la norma nel suo contesto (codice, legge speciale, regolamento)
   - Analizza la posizione topografica (libro, titolo, capo, sezione)
   - Identifica norme collegate (rinvii, deroghe, eccezioni, norme generali/speciali)
   - Verifica la coerenza con l'ordinamento (evita antinomie)

2. **INTERPRETAZIONE STORICA** (art. 14)
   - Ricostruisci l'evoluzione della norma nel tempo
   - Analizza le modifiche legislative (quando e perché)
   - Considera le abrogazioni (espresse, tacite, per incompatibilità)
   - Valuta i lavori preparatori se rilevanti

3. **PRINCIPI GUIDA**
   - "Lex posterior derogat priori" (legge successiva deroga anteriore)
   - "Lex specialis derogat generali" (legge speciale deroga generale)
   - "In dubio pro libertate" per norme restrittive
   - Coerenza dell'ordinamento giuridico

## OUTPUT

Rispondi in JSON con questa struttura:
{
    "interpretation": "Interpretazione sistematica in italiano",
    "legal_basis": [
        {
            "source_type": "norm",
            "source_id": "URN della norma",
            "citation": "Citazione formale",
            "excerpt": "Testo rilevante",
            "relevance": "Connessione sistematica con la norma principale"
        }
    ],
    "reasoning_steps": [
        {
            "step_number": 1,
            "description": "Descrizione del passo sistematico",
            "sources": ["source_id1", "source_id2"]
        }
    ],
    "confidence": 0.0-1.0,
    "confidence_factors": {
        "norm_clarity": 0.0-1.0,
        "jurisprudence_alignment": 0.0-1.0,
        "contextual_ambiguity": 0.0-1.0,
        "source_availability": 0.0-1.0
    },
    "historical_context": "Evoluzione storica della norma (se rilevante)",
    "systematic_position": "Posizione nel sistema giuridico",
    "limitations": "Cosa non hai potuto considerare"
}

CHECKLIST FINALE:
✅ Ogni fonte in legal_basis DEVE provenire da TESTI NORMATIVI RECUPERATI
✅ Il campo "source_id" DEVE essere ESATTAMENTE il valore indicato come `source_id` nella fonte
✅ NON inventare source_id - copia esattamente il valore mostrato
✅ Ogni excerpt DEVE essere un testo copiato dalle fonti, non parafrasato
✅ Se le fonti sono insufficienti, abbassa confidence e source_availability
✅ NON inventare MAI articoli o sentenze non presenti nelle fonti
✅ Evidenzia le RELAZIONI tra norme SOLO se entrambe sono nelle fonti"""

    async def analyze(self, context: ExpertContext) -> ExpertResponse:
        """
        Analizza la query con approccio sistematico e storico.

        Flow (standard):
        1. Usa semantic_search per trovare norme correlate
        2. Usa graph_search per esplorare connessioni sistematiche
        3. Identifica modifiche storiche tramite relazione MODIFICA
        4. Chiama LLM per analisi sistematica

        Flow (ReAct mode - use_react=True):
        1. ReAct loop: LLM decide quali tool usare iterativamente
        2. Convergenza automatica basata su novelty threshold
        3. Analisi LLM finale con tutte le fonti raccolte
        """
        import time
        start_time = time.time()

        log.info(
            f"SystemicExpert analyzing",
            query=context.query_text[:50],
            trace_id=context.trace_id,
            use_react=self.use_react
        )

        # Step 1: Recupera fonti (ReAct o standard)
        if self.use_react and self.ai_service:
            # ReAct mode: LLM-driven tool selection
            all_sources = await self.react_loop(
                context,
                max_iterations=self.react_config.get("max_iterations", 5),
                novelty_threshold=self.react_config.get("novelty_threshold", 0.1)
            )
            log.info(
                f"SystemicExpert ReAct completed",
                sources=len(all_sources),
                react_metrics=self.get_react_metrics() if hasattr(self, '_react_result') else {}
            )
        else:
            # Standard mode: fixed tool sequence
            retrieved_sources = await self._retrieve_sources(context)
            systemic_sources = await self._expand_systemic_relations(context, retrieved_sources)
            all_sources = retrieved_sources + systemic_sources

        # Step 2: Costruisci context arricchito
        enriched_context = ExpertContext(
            query_text=context.query_text,
            query_embedding=context.query_embedding,
            entities=context.entities,
            retrieved_chunks=all_sources,
            metadata={
                **context.metadata,
                "systemic_expansion": True,
                "react_mode": self.use_react,
                "react_metrics": self.get_react_metrics() if self.use_react and hasattr(self, '_react_result') else {}
            },
            trace_id=context.trace_id
        )

        # Step 3: Analisi
        if self.ai_service:
            response = await self._analyze_with_llm(enriched_context)
        else:
            response = self._analyze_without_llm(enriched_context)

        response.execution_time_ms = (time.time() - start_time) * 1000

        # Aggiungi metriche ReAct se disponibili
        if self.use_react and hasattr(self, '_react_result'):
            response.metadata = response.metadata or {}
            response.metadata["react_metrics"] = self.get_react_metrics()

        log.info(
            f"SystemicExpert completed",
            confidence=response.confidence,
            sources=len(response.legal_basis),
            time_ms=response.execution_time_ms
        )

        return response

    async def _retrieve_sources(self, context: ExpertContext) -> List[Dict[str, Any]]:
        """
        Recupera fonti usando i tools disponibili.

        Flow:
        1. Usa chunks già recuperati se presenti
        2. Semantic search per trovare norme correlate
        3. Estrai URN dai risultati per graph expansion
        """
        sources = []
        self._extracted_urns = set()  # Store for later graph expansion

        if context.retrieved_chunks:
            sources.extend(context.retrieved_chunks)
            # Estrai URN dai chunks già presenti
            for chunk in context.retrieved_chunks:
                urn = chunk.get("article_urn") or chunk.get("urn")
                if urn:
                    self._extracted_urns.add(urn)

        # Semantic search - SOLO norme per SystemicExpert (connessione tra norme)
        semantic_tool = self._tool_registry.get("semantic_search")
        if semantic_tool:
            source_types = get_source_types_for_expert("SystemicExpert")
            result = await semantic_tool(
                query=context.query_text,
                top_k=5,
                expert_type="SystemicExpert",
                source_types=source_types  # ["norma"] - connessione tra norme
            )
            if result.success and result.data.get("results"):
                sources.extend(result.data["results"])
                # Estrai URN dai risultati per graph expansion
                for item in result.data["results"]:
                    urn = item.get("metadata", {}).get("article_urn") or item.get("urn")
                    if urn:
                        self._extracted_urns.add(urn)

        log.debug(
            f"SystemicExpert sources retrieved",
            total=len(sources),
            extracted_urns=len(self._extracted_urns)
        )

        return sources

    async def _expand_systemic_relations(
        self,
        context: ExpertContext,
        initial_sources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Espande le fonti seguendo relazioni sistematiche.

        Combina:
        - URN estratti da semantic_search (self._extracted_urns)
        - URN da context.norm_references (dal query_analyzer)
        """
        expanded = []

        graph_tool = self._tool_registry.get("graph_search")
        if not graph_tool:
            return expanded

        # Combina URN da context + URN estratti da semantic_search
        urns_to_expand = set(context.norm_references) | getattr(self, '_extracted_urns', set())

        if not urns_to_expand:
            log.debug("SystemicExpert: No URNs to expand")
            return expanded

        # Espandi con relazioni sistematiche
        # Relazioni reali nel grafo (verificate con: MATCH ()-[r]->() RETURN type(r), count(*))
        systemic_relations = ["DISCIPLINA", "modifica", "abroga", "interpreta", "IMPONE"]

        log.debug(
            f"SystemicExpert graph expansion",
            urns_count=len(urns_to_expand),
            urns=list(urns_to_expand)[:3]
        )

        for urn in list(urns_to_expand)[:5]:
            try:
                result = await graph_tool(
                    start_node=urn,
                    relation_types=systemic_relations,
                    max_hops=2,
                    direction="both"  # Bidirezionale per connessioni
                )
                if result.success:
                    graph_nodes = result.data.get("nodes", [])
                    log.debug(
                        f"Systemic expansion for {urn[:50]}...",
                        nodes_found=len(graph_nodes)
                    )
                    for node in graph_nodes:
                        expanded.append({
                            "text": node.get("properties", {}).get("testo", ""),
                            "urn": node.get("urn", ""),
                            "type": node.get("type", ""),
                            "source": "systemic_expansion",
                            "relation": "systemic",
                            "source_urn": urn
                        })
            except Exception as e:
                log.warning(f"Failed to expand {urn}: {e}")

        log.info(
            f"SystemicExpert systemic expansion",
            total_expanded=len(expanded)
        )

        return expanded

    async def _analyze_with_llm(self, context: ExpertContext) -> ExpertResponse:
        """Analizza con LLM."""
        import json

        system_prompt = self.prompt_template
        user_prompt = self._format_context_for_llm(context)

        try:
            response = await self.ai_service.generate_response_async(
                prompt=f"{system_prompt}\n\n{user_prompt}",
                model=self.model,
                temperature=self.temperature
            )

            if isinstance(response, dict):
                content = response.get("content", str(response))
                tokens = response.get("usage", {}).get("total_tokens", 0)
            else:
                content = str(response)
                tokens = 0

            # Clean markdown
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            data = json.loads(content)
            return self._build_response(data, context, tokens)

        except Exception as e:
            log.error(f"LLM analysis failed: {e}")
            return ExpertResponse(
                expert_type=self.expert_type,
                interpretation=f"Errore nell'analisi sistematica: {str(e)}",
                confidence=0.0,
                limitations=str(e),
                trace_id=context.trace_id
            )

    def _analyze_without_llm(self, context: ExpertContext) -> ExpertResponse:
        """Genera risposta basic senza LLM."""
        sources = context.retrieved_chunks[:5]

        legal_basis = []
        for chunk in sources:
            legal_basis.append(LegalSource(
                source_type="norm",
                source_id=chunk.get("urn", chunk.get("chunk_id", "")),
                citation=chunk.get("urn", ""),
                excerpt=chunk.get("text", "")[:500],
                relevance=f"Connessione sistematica - {chunk.get('source', 'unknown')}"
            ))

        interpretation = "Analisi sistematica delle fonti recuperate:\n\n"
        for i, chunk in enumerate(sources, 1):
            text = chunk.get("text", "")[:200]
            source_type = chunk.get("source", "semantic")
            interpretation += f"{i}. [{source_type}] {text}...\n\n"

        interpretation += "\n[Nota: Analisi sistematica completa richiede servizio AI]"

        return ExpertResponse(
            expert_type=self.expert_type,
            interpretation=interpretation,
            legal_basis=legal_basis,
            confidence=0.3,
            limitations="Analisi senza LLM - solo recupero fonti sistematiche",
            trace_id=context.trace_id
        )

    def _format_context_for_llm(self, context: ExpertContext) -> str:
        """Formatta context per LLM con focus sistematico."""
        sections = [
            f"## DOMANDA DELL'UTENTE\n{context.query_text}"
        ]

        if context.norm_references:
            sections.append(f"\n## NORME CITATE\n" + ", ".join(context.norm_references))

        if context.legal_concepts:
            sections.append(f"\n## CONCETTI GIURIDICI\n" + ", ".join(context.legal_concepts))

        if context.retrieved_chunks:
            sections.append("⚠️ USA ESATTAMENTE il source_id indicato per ogni fonte nel campo legal_basis!")

            # Separa fonti per tipo
            semantic = [c for c in context.retrieved_chunks if c.get("source") != "systemic_expansion"]
            systemic = [c for c in context.retrieved_chunks if c.get("source") == "systemic_expansion"]

            if semantic:
                sections.append("\n## NORME DIRETTAMENTE RILEVANTI")
                for i, chunk in enumerate(semantic[:5], 1):
                    text = chunk.get("text", "")
                    chunk_id = chunk.get("chunk_id", chunk.get("urn", f"source_{i}"))
                    urn = chunk.get("urn", "N/A")
                    source_type = chunk.get("source_type", "norma")
                    sections.append(f"\n### Fonte {i}")
                    sections.append(f"- **source_id**: `{chunk_id}` ← USA QUESTO ESATTO VALORE")
                    sections.append(f"- **urn**: {urn}")
                    sections.append(f"- **source_type**: {source_type}")
                    sections.append(f"- **testo**:\n{text}")

            if systemic:
                sections.append("\n## NORME SISTEMATICAMENTE CONNESSE")
                for i, chunk in enumerate(systemic[:5], 1):
                    text = chunk.get("text", "")
                    chunk_id = chunk.get("chunk_id", chunk.get("urn", f"systemic_{i}"))
                    urn = chunk.get("urn", "N/A")
                    rel = chunk.get("relation", "N/A")
                    sections.append(f"\n### Connessione {i}")
                    sections.append(f"- **source_id**: `{chunk_id}` ← USA QUESTO ESATTO VALORE")
                    sections.append(f"- **urn**: {urn}")
                    sections.append(f"- **relazione**: {rel}")
                    sections.append(f"- **testo**:\n{text}")

        return "\n".join(sections)

    def _build_response(
        self,
        data: Dict[str, Any],
        context: ExpertContext,
        tokens: int
    ) -> ExpertResponse:
        """Costruisce ExpertResponse da JSON LLM."""
        legal_basis = []
        for lb in data.get("legal_basis", []):
            legal_basis.append(LegalSource(
                source_type=lb.get("source_type", "norm"),
                source_id=lb.get("source_id", ""),
                citation=lb.get("citation", ""),
                excerpt=lb.get("excerpt", ""),
                relevance=lb.get("relevance", "")
            ))

        reasoning_steps = []
        for rs in data.get("reasoning_steps", []):
            reasoning_steps.append(ReasoningStep(
                step_number=rs.get("step_number", 0),
                description=rs.get("description", ""),
                sources=rs.get("sources", [])
            ))

        cf_data = data.get("confidence_factors", {})
        confidence_factors = ConfidenceFactors(
            norm_clarity=cf_data.get("norm_clarity", 0.5),
            jurisprudence_alignment=cf_data.get("jurisprudence_alignment", 0.5),
            contextual_ambiguity=cf_data.get("contextual_ambiguity", 0.5),
            source_availability=cf_data.get("source_availability", 0.5)
        )

        # Aggiungi contesto storico/sistematico alle limitations se presente
        limitations = data.get("limitations", "")
        if data.get("historical_context"):
            limitations += f"\n\nContesto storico: {data['historical_context']}"
        if data.get("systematic_position"):
            limitations += f"\n\nPosizione sistematica: {data['systematic_position']}"

        return ExpertResponse(
            expert_type=self.expert_type,
            interpretation=data.get("interpretation", ""),
            legal_basis=legal_basis,
            reasoning_steps=reasoning_steps,
            confidence=data.get("confidence", 0.5),
            confidence_factors=confidence_factors,
            limitations=limitations.strip(),
            trace_id=context.trace_id,
            tokens_used=tokens
        )
