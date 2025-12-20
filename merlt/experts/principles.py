"""
Principles Expert
==================

Expert specializzato nell'interpretazione teleologica e basata sui principi.

Fondamento teorico: Art. 12, comma II, disp. prel. c.c.
"Se una controversia non può essere decisa con una precisa disposizione,
si ha riguardo alle disposizioni che regolano casi simili o materie analoghe;
se il caso rimane ancora dubbio, si decide secondo i principi generali
dell'ordinamento giuridico dello Stato."

L'interpretazione teleologica/per principi considera:
- RATIO LEGIS: Scopo e finalità della norma
- INTENZIONE DEL LEGISLATORE: Obiettivi perseguiti
- PRINCIPI GENERALI: Costituzione, principi UE, principi generali del diritto
- ANALOGIA: Casi simili e materie analoghe

Approccio:
1. Identifica la ratio legis (scopo della norma)
2. Ricostruisce l'intenzione del legislatore (lavori preparatori, relazioni)
3. Ricerca principi costituzionali e sovranazionali applicabili
4. Applica interpretazione conforme (a Costituzione, diritto UE)
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
from merlt.tools import BaseTool

log = structlog.get_logger()


class PrinciplesExpert(BaseExpert):
    """
    Expert per interpretazione teleologica e per principi.

    Art. 12, II: "intenzione del legislatore" + principi generali

    Epistemologia: Finalismo giuridico
    Focus: PERCHÉ la legge esiste e quali VALORI tutela

    Tools principali:
    - semantic_search: Ricerca principi e norme costituzionali
    - graph_search: Navigazione verso fonti superiori

    Traversal weights:
    - ATTUA: 1.0 (attuazione di principi)
    - ESPRIME: 0.95 (espressione di principi)
    - COSTITUZIONALE: 0.95 (norme costituzionali)
    - COMUNITARIO: 0.90 (norme EU)
    - PRINCIPIO: 0.90 (principi generali)
    - FINALITA: 0.85 (finalità normativa)

    Esempio:
        >>> from merlt.experts import PrinciplesExpert
        >>>
        >>> expert = PrinciplesExpert(
        ...     tools=[SemanticSearchTool(retriever, embeddings)],
        ...     ai_service=openrouter_service
        ... )
        >>> response = await expert.analyze(context)
    """

    expert_type = "principles"
    description = "Interpretazione teleologica e per principi (art. 12, II disp. prel. c.c.)"

    # Pesi default per traversal grafo - focus su principi e ratio
    DEFAULT_TRAVERSAL_WEIGHTS = {
        "attua": 1.0,           # Attuazione di principi
        "esprime": 0.95,        # Espressione di principi
        "costituzionale": 0.95, # Norme costituzionali
        "comunitario": 0.90,    # Norme EU
        "principio": 0.90,      # Principi generali
        "finalita": 0.85,       # Finalità normativa
        "ratio": 0.85,          # Ratio legis
        "tutela": 0.80,         # Beni tutelati
        "disciplina": 0.75,     # Materie regolate
        "default": 0.50
    }

    def __init__(
        self,
        tools: Optional[List[BaseTool]] = None,
        config: Optional[Dict[str, Any]] = None,
        ai_service: Any = None
    ):
        """
        Inizializza PrinciplesExpert.

        Args:
            tools: Tools per ricerca
            config: Configurazione (prompt, temperature, traversal_weights)
            ai_service: Servizio AI per LLM calls
        """
        config = config or {}
        if "traversal_weights" not in config:
            config["traversal_weights"] = self.DEFAULT_TRAVERSAL_WEIGHTS

        super().__init__(tools=tools, config=config, ai_service=ai_service)
        self.prompt_template = self._get_principles_prompt()

    def _get_principles_prompt(self) -> str:
        """Prompt specifico per interpretazione teleologica."""
        return """Sei un esperto giuridico specializzato nell'INTERPRETAZIONE TELEOLOGICA E PER PRINCIPI.

Il tuo approccio si basa sull'art. 12, comma II, disp. prel. c.c.:
"...si decide secondo i principi generali dell'ordinamento giuridico dello Stato."

## METODOLOGIA

1. **RATIO LEGIS** (scopo della norma)
   - Identifica la FINALITÀ perseguita dalla norma
   - Ricostruisci il BENE GIURIDICO tutelato
   - Considera il CONTESTO STORICO-SOCIALE dell'emanazione
   - Valuta l'EFFICACIA della norma rispetto allo scopo

2. **INTENZIONE DEL LEGISLATORE**
   - Analizza i lavori preparatori (se disponibili)
   - Considera le relazioni illustrative
   - Valuta il dibattito parlamentare
   - Attenzione: l'intenzione oggettiva prevale su quella soggettiva

3. **INTERPRETAZIONE CONFORME**
   - A COSTITUZIONE: artt. 2, 3, 24, 41, 42... (diritti fondamentali)
   - A DIRITTO UE: Trattati, Carta diritti fondamentali, direttive
   - A CEDU: Convenzione Europea Diritti dell'Uomo
   - Principio di proporzionalità, ragionevolezza, non discriminazione

4. **PRINCIPI GENERALI**
   - Buona fede (art. 1175, 1375 c.c.)
   - Affidamento legittimo
   - Certezza del diritto
   - Proporzionalità
   - Effettività della tutela

## OUTPUT

Rispondi in JSON con questa struttura:
{
    "interpretation": "Interpretazione teleologica in italiano",
    "legal_basis": [
        {
            "source_type": "constitutional|eu|principle|norm",
            "source_id": "URN o riferimento",
            "citation": "Citazione formale",
            "excerpt": "Testo rilevante",
            "relevance": "Come questo principio guida l'interpretazione"
        }
    ],
    "reasoning_steps": [
        {
            "step_number": 1,
            "description": "Passo del ragionamento teleologico",
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
    "ratio_legis": "Scopo identificato della norma",
    "constitutional_framework": "Principi costituzionali rilevanti",
    "limitations": "Cosa non hai potuto considerare"
}

IMPORTANTE:
- Identifica sempre la RATIO LEGIS
- Cerca PRINCIPI costituzionali e sovranazionali applicabili
- Applica INTERPRETAZIONE CONFORME quando possibile
- Segnala CONFLITTI tra interpretazione letterale e teleologica"""

    async def analyze(self, context: ExpertContext) -> ExpertResponse:
        """
        Analizza la query con approccio teleologico.

        Flow:
        1. Recupera norme e principi rilevanti
        2. Cerca fonti costituzionali e sovranazionali
        3. Identifica la ratio legis
        4. Produce interpretazione orientata ai principi
        """
        import time
        start_time = time.time()

        log.info(
            f"PrinciplesExpert analyzing",
            query=context.query_text[:50],
            trace_id=context.trace_id
        )

        # Step 1: Recupera fonti
        retrieved_sources = await self._retrieve_sources(context)

        # Step 2: Cerca principi costituzionali/EU
        principle_sources = await self._search_principles(context)

        # Step 3: Costruisci context arricchito
        all_sources = retrieved_sources + principle_sources
        enriched_context = ExpertContext(
            query_text=context.query_text,
            query_embedding=context.query_embedding,
            entities=context.entities,
            retrieved_chunks=all_sources,
            metadata={**context.metadata, "principles_search": True},
            trace_id=context.trace_id
        )

        # Step 4: Analisi
        if self.ai_service:
            response = await self._analyze_with_llm(enriched_context)
        else:
            response = self._analyze_without_llm(enriched_context)

        response.execution_time_ms = (time.time() - start_time) * 1000

        log.info(
            f"PrinciplesExpert completed",
            confidence=response.confidence,
            sources=len(response.legal_basis),
            time_ms=response.execution_time_ms
        )

        return response

    async def _retrieve_sources(self, context: ExpertContext) -> List[Dict[str, Any]]:
        """Recupera fonti usando i tools disponibili."""
        sources = []

        if context.retrieved_chunks:
            sources.extend(context.retrieved_chunks)

        semantic_tool = self._tool_registry.get("semantic_search")
        if semantic_tool:
            result = await semantic_tool(
                query=context.query_text,
                top_k=5,
                expert_type="PrinciplesExpert"
            )
            if result.success and result.data.get("results"):
                sources.extend(result.data["results"])

        return sources

    async def _search_principles(self, context: ExpertContext) -> List[Dict[str, Any]]:
        """Cerca principi costituzionali e generali."""
        principles = []

        semantic_tool = self._tool_registry.get("semantic_search")
        if not semantic_tool:
            return principles

        # Query specifiche per principi
        principle_queries = [
            f"principi costituzionali {context.query_text}",
            f"diritti fondamentali {' '.join(context.legal_concepts[:2]) if context.legal_concepts else context.query_text[:30]}"
        ]

        for query in principle_queries:
            try:
                result = await semantic_tool(
                    query=query,
                    top_k=3,
                    expert_type="PrinciplesExpert"
                )
                if result.success and result.data.get("results"):
                    for r in result.data["results"]:
                        r["source"] = "principles_search"
                    principles.extend(result.data["results"])
            except Exception as e:
                log.warning(f"Principles search failed: {e}")

        # Ricerca grafo per relazioni con principi
        graph_tool = self._tool_registry.get("graph_search")
        if graph_tool and context.norm_references:
            principle_relations = ["attua", "esprime", "costituzionale", "principio"]
            for urn in context.norm_references[:2]:
                try:
                    result = await graph_tool(
                        start_node=urn,
                        relation_types=principle_relations,
                        max_hops=2
                    )
                    if result.success:
                        for node in result.data.get("nodes", []):
                            node_type = node.get("type", "")
                            if "Principio" in node_type or "Costituzionale" in node_type:
                                principles.append({
                                    "text": node.get("properties", {}).get("testo", ""),
                                    "urn": node.get("urn", ""),
                                    "type": node_type,
                                    "source": "principle_graph"
                                })
                except Exception as e:
                    log.warning(f"Graph principle search failed: {e}")

        return principles

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
                interpretation=f"Errore nell'analisi teleologica: {str(e)}",
                confidence=0.0,
                limitations=str(e),
                trace_id=context.trace_id
            )

    def _analyze_without_llm(self, context: ExpertContext) -> ExpertResponse:
        """Genera risposta basic senza LLM."""
        sources = context.retrieved_chunks[:5]

        legal_basis = []
        for chunk in sources:
            source_type = "principle" if chunk.get("source") in ["principles_search", "principle_graph"] else "norm"
            legal_basis.append(LegalSource(
                source_type=source_type,
                source_id=chunk.get("urn", chunk.get("chunk_id", "")),
                citation=chunk.get("urn", ""),
                excerpt=chunk.get("text", "")[:500],
                relevance=f"Rilevanza teleologica - {chunk.get('source', 'unknown')}"
            ))

        interpretation = "Fonti e principi recuperati per analisi teleologica:\n\n"
        for i, chunk in enumerate(sources, 1):
            text = chunk.get("text", "")[:200]
            source_type = chunk.get("source", "semantic")
            interpretation += f"{i}. [{source_type}] {text}...\n\n"

        interpretation += "\n[Nota: Analisi teleologica completa richiede servizio AI]"

        return ExpertResponse(
            expert_type=self.expert_type,
            interpretation=interpretation,
            legal_basis=legal_basis,
            confidence=0.3,
            limitations="Analisi senza LLM - solo recupero principi",
            trace_id=context.trace_id
        )

    def _format_context_for_llm(self, context: ExpertContext) -> str:
        """Formatta context per LLM con focus su principi."""
        sections = [
            f"## DOMANDA DELL'UTENTE\n{context.query_text}"
        ]

        if context.norm_references:
            sections.append(f"\n## NORME CITATE\n" + ", ".join(context.norm_references))

        if context.legal_concepts:
            sections.append(f"\n## CONCETTI GIURIDICI\n" + ", ".join(context.legal_concepts))

        if context.retrieved_chunks:
            # Separa fonti per tipo
            norms = [c for c in context.retrieved_chunks if c.get("source") not in ["principles_search", "principle_graph"]]
            principles = [c for c in context.retrieved_chunks if c.get("source") in ["principles_search", "principle_graph"]]

            if norms:
                sections.append("\n## NORME ORDINARIE")
                for i, chunk in enumerate(norms[:5], 1):
                    text = chunk.get("text", "")
                    urn = chunk.get("urn", "N/A")
                    sections.append(f"\n### Norma {i} (URN: {urn})\n{text}")

            if principles:
                sections.append("\n## PRINCIPI E NORME COSTITUZIONALI/EU")
                for i, chunk in enumerate(principles[:5], 1):
                    text = chunk.get("text", "")
                    urn = chunk.get("urn", "N/A")
                    p_type = chunk.get("type", "Principio")
                    sections.append(f"\n### {p_type} {i} (URN: {urn})\n{text}")

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
                source_type=lb.get("source_type", "principle"),
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

        limitations = data.get("limitations", "")
        if data.get("ratio_legis"):
            limitations += f"\n\nRatio legis: {data['ratio_legis']}"
        if data.get("constitutional_framework"):
            limitations += f"\n\nQuadro costituzionale: {data['constitutional_framework']}"

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
