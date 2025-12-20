"""
Precedent Expert
=================

Expert specializzato nell'interpretazione giurisprudenziale.

Fondamento teorico: Prassi applicativa
Nel sistema italiano, pur non essendo i precedenti formalmente vincolanti
(a differenza del common law), la giurisprudenza ha un ruolo cruciale:
- Corte Costituzionale: interpretazione conforme, sentenze additive/ablative
- Corte di Cassazione: funzione nomofilattica (art. 65 Ord. Giud.)
- Corti EU: CGUE, CEDU - vincolanti per il giudice nazionale

L'interpretazione giurisprudenziale considera:
- GIURISPRUDENZA COSTANTE: Orientamenti consolidati
- NOMOFILACHIA: Decisioni della Cassazione a SU
- OVERRULING: Cambiamenti di orientamento
- DIRITTO VIVENTE: Come la norma è effettivamente applicata

Approccio:
1. Cerca precedenti giurisprudenziali rilevanti
2. Identifica orientamenti consolidati vs. contrasti
3. Valuta pronunce delle Corti superiori
4. Considera il "diritto vivente" (prassi applicativa)
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


class PrecedentExpert(BaseExpert):
    """
    Expert per interpretazione giurisprudenziale.

    Focus sulla prassi applicativa e sul "diritto vivente".

    Epistemologia: Realismo giuridico
    Focus: Come la norma VIENE APPLICATA in concreto

    Tools principali:
    - semantic_search: Ricerca massime e sentenze
    - graph_search: Navigazione tra sentenze e norme interpretate

    Traversal weights:
    - INTERPRETA: 1.0 (sentenze che interpretano norme)
    - APPLICA: 0.95 (applicazione giurisprudenziale)
    - CITA: 0.90 (citazioni in sentenze)
    - CONFERMA: 0.85 (conferme giurisprudenziali)
    - COMMENTA: 0.85 (commenti dottrinali)
    - SUPERA: 0.80 (overruling)

    Esempio:
        >>> from merlt.experts import PrecedentExpert
        >>>
        >>> expert = PrecedentExpert(
        ...     tools=[SemanticSearchTool(retriever, embeddings)],
        ...     ai_service=openrouter_service
        ... )
        >>> response = await expert.analyze(context)
    """

    expert_type = "precedent"
    description = "Interpretazione giurisprudenziale (prassi applicativa)"

    # Pesi default per traversal grafo - focus su giurisprudenza
    DEFAULT_TRAVERSAL_WEIGHTS = {
        "interpreta": 1.0,     # Sentenze che interpretano norme
        "applica": 0.95,       # Applicazione giurisprudenziale
        "cita": 0.90,          # Citazioni in sentenze
        "conferma": 0.85,      # Conferme giurisprudenziali
        "commenta": 0.85,      # Commenti dottrinali
        "supera": 0.80,        # Overruling
        "contrasta": 0.75,     # Contrasti giurisprudenziali
        "disciplina": 0.70,    # Norme di riferimento
        "default": 0.50
    }

    # Gerarchia delle fonti giurisprudenziali
    COURT_HIERARCHY = {
        "corte_costituzionale": 1.0,  # Massima autorità
        "cassazione_su": 0.95,         # Sezioni Unite
        "cassazione": 0.85,            # Cassazione ordinaria
        "cgue": 0.90,                  # Corte di Giustizia UE
        "cedu": 0.88,                  # Corte Europea Diritti Uomo
        "consiglio_stato": 0.80,       # Giustizia amministrativa
        "corte_appello": 0.70,         # Secondo grado
        "tribunale": 0.60,             # Primo grado
        "default": 0.50
    }

    def __init__(
        self,
        tools: Optional[List[BaseTool]] = None,
        config: Optional[Dict[str, Any]] = None,
        ai_service: Any = None
    ):
        """
        Inizializza PrecedentExpert.

        Args:
            tools: Tools per ricerca
            config: Configurazione (prompt, temperature, traversal_weights)
            ai_service: Servizio AI per LLM calls
        """
        config = config or {}
        if "traversal_weights" not in config:
            config["traversal_weights"] = self.DEFAULT_TRAVERSAL_WEIGHTS

        super().__init__(tools=tools, config=config, ai_service=ai_service)
        self.prompt_template = self._get_precedent_prompt()

    def _get_precedent_prompt(self) -> str:
        """Prompt specifico per interpretazione giurisprudenziale."""
        return """Sei un esperto giuridico specializzato nell'INTERPRETAZIONE GIURISPRUDENZIALE.

Il tuo approccio si basa sulla prassi applicativa e sul "diritto vivente":
come le corti interpretano e applicano effettivamente le norme.

## METODOLOGIA

1. **GERARCHIA DELLE FONTI GIURISPRUDENZIALI**
   - Corte Costituzionale: Massima autorità, sentenze interpretative/additive
   - Cassazione a Sezioni Unite: Funzione nomofilattica (art. 65 Ord. Giud.)
   - CGUE: Interpretazione vincolante del diritto UE
   - CEDU: Standard minimi diritti fondamentali
   - Cassazione ordinaria: Orientamenti consolidati
   - Giurisprudenza di merito: Prassi applicativa diffusa

2. **ANALISI DEI PRECEDENTI**
   - Identifica la MASSIMA (principio di diritto estratto)
   - Distingui RATIO DECIDENDI (vincolante) da OBITER DICTUM
   - Valuta la COSTANZA dell'orientamento
   - Segnala CONTRASTI giurisprudenziali

3. **EVOLUZIONE GIURISPRUDENZIALE**
   - Orientamento CONSOLIDATO vs. ISOLATO
   - Eventuali OVERRULING (cambiamenti di orientamento)
   - Tendenze RECENTI della giurisprudenza
   - Interventi delle Sezioni Unite per dirimere contrasti

4. **TIPOLOGIE DI PRONUNCE (Corte Cost.)**
   - Sentenze interpretative di rigetto
   - Sentenze additive ("nella parte in cui non prevede...")
   - Sentenze ablative/sostitutive
   - Sentenze di inammissibilità con monito

## OUTPUT

Rispondi in JSON con questa struttura:
{
    "interpretation": "Interpretazione giurisprudenziale in italiano",
    "legal_basis": [
        {
            "source_type": "jurisprudence",
            "source_id": "Riferimento sentenza (es. Cass. SU 12345/2020)",
            "citation": "Citazione formale",
            "excerpt": "Massima o passaggio chiave",
            "relevance": "Perché questo precedente è rilevante"
        }
    ],
    "reasoning_steps": [
        {
            "step_number": 1,
            "description": "Passo dell'analisi giurisprudenziale",
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
    "jurisprudential_trend": "Orientamento consolidato / in evoluzione / contrastato",
    "key_precedents": ["Lista dei precedenti più rilevanti"],
    "limitations": "Cosa non hai potuto considerare"
}

IMPORTANTE:
- Cita SEMPRE le sentenze con riferimento completo
- Distingui giurisprudenza COSTANTE da orientamenti ISOLATI
- Segnala CONTRASTI tra diverse corti o sezioni
- Indica l'AUTORITÀ della fonte (SU > sez. semplice)
- Considera il TEMPO: sentenze recenti vs. risalenti"""

    async def analyze(self, context: ExpertContext) -> ExpertResponse:
        """
        Analizza la query cercando precedenti giurisprudenziali.

        Flow:
        1. Cerca massime e sentenze rilevanti
        2. Identifica orientamenti consolidati
        3. Valuta gerarchia delle fonti
        4. Produce interpretazione basata sulla prassi
        """
        import time
        start_time = time.time()

        log.info(
            f"PrecedentExpert analyzing",
            query=context.query_text[:50],
            trace_id=context.trace_id
        )

        # Step 1: Recupera fonti
        retrieved_sources = await self._retrieve_sources(context)

        # Step 2: Cerca specificamente giurisprudenza
        jurisprudence_sources = await self._search_jurisprudence(context)

        # Step 3: Ordina per autorità
        all_sources = self._rank_by_authority(retrieved_sources + jurisprudence_sources)

        # Step 4: Costruisci context arricchito
        enriched_context = ExpertContext(
            query_text=context.query_text,
            query_embedding=context.query_embedding,
            entities=context.entities,
            retrieved_chunks=all_sources,
            metadata={**context.metadata, "jurisprudence_search": True},
            trace_id=context.trace_id
        )

        # Step 5: Analisi
        if self.ai_service:
            response = await self._analyze_with_llm(enriched_context)
        else:
            response = self._analyze_without_llm(enriched_context)

        response.execution_time_ms = (time.time() - start_time) * 1000

        log.info(
            f"PrecedentExpert completed",
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
                expert_type="PrecedentExpert"
            )
            if result.success and result.data.get("results"):
                sources.extend(result.data["results"])

        return sources

    async def _search_jurisprudence(self, context: ExpertContext) -> List[Dict[str, Any]]:
        """Cerca specificamente fonti giurisprudenziali."""
        jurisprudence = []

        semantic_tool = self._tool_registry.get("semantic_search")
        if not semantic_tool:
            return jurisprudence

        # Query specifiche per giurisprudenza
        base_query = context.query_text[:100]
        jur_queries = [
            f"giurisprudenza cassazione {base_query}",
            f"massima {' '.join(context.legal_concepts[:2]) if context.legal_concepts else base_query}"
        ]

        for query in jur_queries:
            try:
                result = await semantic_tool(
                    query=query,
                    top_k=3,
                    expert_type="PrecedentExpert"
                )
                if result.success and result.data.get("results"):
                    for r in result.data["results"]:
                        r["source"] = "jurisprudence_search"
                    jurisprudence.extend(result.data["results"])
            except Exception as e:
                log.warning(f"Jurisprudence search failed: {e}")

        # Ricerca grafo per relazioni giurisprudenziali
        graph_tool = self._tool_registry.get("graph_search")
        if graph_tool and context.norm_references:
            jur_relations = ["interpreta", "applica", "cita", "conferma"]
            for urn in context.norm_references[:2]:
                try:
                    result = await graph_tool(
                        start_node=urn,
                        relation_types=jur_relations,
                        max_hops=2,
                        direction="incoming"  # Sentenze che citano la norma
                    )
                    if result.success:
                        for node in result.data.get("nodes", []):
                            node_type = node.get("type", "")
                            if "Massima" in node_type or "Sentenza" in node_type:
                                jurisprudence.append({
                                    "text": node.get("properties", {}).get("testo", ""),
                                    "urn": node.get("urn", ""),
                                    "type": node_type,
                                    "source": "jurisprudence_graph",
                                    "court": node.get("properties", {}).get("corte", "unknown")
                                })
                except Exception as e:
                    log.warning(f"Graph jurisprudence search failed: {e}")

        return jurisprudence

    def _rank_by_authority(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ordina le fonti per autorità della corte."""
        def get_authority_score(source: Dict[str, Any]) -> float:
            court = source.get("court", "").lower()
            text = source.get("text", "").lower()

            # Identifica la corte dal testo o metadati
            if "corte costituzionale" in court or "corte costituzionale" in text:
                return self.COURT_HIERARCHY["corte_costituzionale"]
            elif "sezioni unite" in court or "s.u." in text or "ss.uu." in text:
                return self.COURT_HIERARCHY["cassazione_su"]
            elif "cassazione" in court or "cass." in text:
                return self.COURT_HIERARCHY["cassazione"]
            elif "cgue" in court or "corte di giustizia" in text:
                return self.COURT_HIERARCHY["cgue"]
            elif "cedu" in court or "corte europea" in text:
                return self.COURT_HIERARCHY["cedu"]
            elif "consiglio di stato" in court or "cons. stato" in text:
                return self.COURT_HIERARCHY["consiglio_stato"]

            # Fallback: usa score esistente se presente
            return source.get("final_score", self.COURT_HIERARCHY["default"])

        # Aggiungi authority score
        for source in sources:
            source["authority_score"] = get_authority_score(source)

        # Ordina per authority (decrescente)
        return sorted(sources, key=lambda x: x.get("authority_score", 0), reverse=True)

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
                interpretation=f"Errore nell'analisi giurisprudenziale: {str(e)}",
                confidence=0.0,
                limitations=str(e),
                trace_id=context.trace_id
            )

    def _analyze_without_llm(self, context: ExpertContext) -> ExpertResponse:
        """Genera risposta basic senza LLM."""
        sources = context.retrieved_chunks[:5]

        legal_basis = []
        for chunk in sources:
            source_type = "jurisprudence" if chunk.get("source") in ["jurisprudence_search", "jurisprudence_graph"] else "norm"
            legal_basis.append(LegalSource(
                source_type=source_type,
                source_id=chunk.get("urn", chunk.get("chunk_id", "")),
                citation=chunk.get("urn", ""),
                excerpt=chunk.get("text", "")[:500],
                relevance=f"Autorità: {chunk.get('authority_score', 'N/A')}"
            ))

        interpretation = "Fonti giurisprudenziali recuperate (ordinate per autorità):\n\n"
        for i, chunk in enumerate(sources, 1):
            text = chunk.get("text", "")[:200]
            authority = chunk.get("authority_score", "N/A")
            source_type = chunk.get("source", "semantic")
            interpretation += f"{i}. [{source_type}] (autorità: {authority}) {text}...\n\n"

        interpretation += "\n[Nota: Analisi giurisprudenziale completa richiede servizio AI]"

        return ExpertResponse(
            expert_type=self.expert_type,
            interpretation=interpretation,
            legal_basis=legal_basis,
            confidence=0.3,
            limitations="Analisi senza LLM - solo recupero giurisprudenza",
            trace_id=context.trace_id
        )

    def _format_context_for_llm(self, context: ExpertContext) -> str:
        """Formatta context per LLM con focus su giurisprudenza."""
        sections = [
            f"## DOMANDA DELL'UTENTE\n{context.query_text}"
        ]

        if context.norm_references:
            sections.append(f"\n## NORME DI RIFERIMENTO\n" + ", ".join(context.norm_references))

        if context.legal_concepts:
            sections.append(f"\n## CONCETTI GIURIDICI\n" + ", ".join(context.legal_concepts))

        if context.retrieved_chunks:
            # Separa per tipo e ordina per autorità
            norms = [c for c in context.retrieved_chunks if c.get("source") not in ["jurisprudence_search", "jurisprudence_graph"]]
            jur = [c for c in context.retrieved_chunks if c.get("source") in ["jurisprudence_search", "jurisprudence_graph"]]

            if jur:
                sections.append("\n## FONTI GIURISPRUDENZIALI (ordinate per autorità)")
                for i, chunk in enumerate(jur[:7], 1):
                    text = chunk.get("text", "")
                    urn = chunk.get("urn", "N/A")
                    authority = chunk.get("authority_score", "N/A")
                    court = chunk.get("court", "N/D")
                    sections.append(f"\n### Precedente {i} (autorità: {authority}, corte: {court})\nRiferimento: {urn}\n{text}")

            if norms:
                sections.append("\n## NORME INTERPRETATE")
                for i, chunk in enumerate(norms[:3], 1):
                    text = chunk.get("text", "")
                    urn = chunk.get("urn", "N/A")
                    sections.append(f"\n### Norma {i} (URN: {urn})\n{text}")

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
                source_type=lb.get("source_type", "jurisprudence"),
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
        if data.get("jurisprudential_trend"):
            limitations += f"\n\nTendenza giurisprudenziale: {data['jurisprudential_trend']}"
        if data.get("key_precedents"):
            limitations += f"\n\nPrecedenti chiave: {', '.join(data['key_precedents'])}"

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
