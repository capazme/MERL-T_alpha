"""
Expert System Debugger - Streamlit Interface

Interfaccia per visualizzare tutti i passaggi del sistema multi-expert:
- Query input
- Routing decision
- Per ogni expert: retrieval, prompt, risposta LLM
- Aggregazione finale

Usage:
    streamlit run apps/expert_debugger.py
"""

import streamlit as st
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import sys
import re
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Import EXPERT_SOURCE_TYPES mapping
from merlt.storage.retriever.models import EXPERT_SOURCE_TYPES, get_source_types_for_expert

# Import ConfigManager per version tracking
from apps.config_manager import ConfigManager, ConfigSnapshot, render_config_sidebar, render_config_viewer

# Global config manager instance
_config_manager = ConfigManager()


# Global trace storage
class TraceCollector:
    """Collettore globale per i trace."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.retrieval_steps = []
        self.llm_calls = []
        self.routing = {}
        self.aggregation = {}
        self.expert_results = {}
        self.database_info = {}
        self.baseline = {}
        self.tool_calls = []  # Per dettaglio tool usage
        self.config_snapshot = None  # Snapshot configurazione

    def set_database_info(self, info: Dict):
        self.database_info = info

    def add_retrieval(self, expert: str, query: str, results: List[Dict], latency_ms: float):
        self.retrieval_steps.append({
            "expert": expert,
            "query": query,
            "results": results,
            "latency_ms": latency_ms,
            "timestamp": datetime.now().isoformat()
        })

    def add_llm_call(self, expert: str, prompt: str, response: str, tokens: int, latency_ms: float):
        self.llm_calls.append({
            "expert": expert,
            "prompt": prompt,
            "response": response,
            "tokens": tokens,
            "latency_ms": latency_ms,
            "timestamp": datetime.now().isoformat()
        })

    def set_routing(self, routing: Dict):
        self.routing = routing

    def set_aggregation(self, prompt: str, response: str):
        self.aggregation = {"prompt": prompt, "response": response}

    def add_expert_result(self, expert: str, result: Dict):
        self.expert_results[expert] = result

    def set_baseline(self, response: str, latency_ms: float, sources_cited: List[str]):
        """Setta la risposta baseline LLM."""
        self.baseline = {
            "response": response,
            "latency_ms": latency_ms,
            "sources_cited": sources_cited,
            "timestamp": datetime.now().isoformat()
        }

    def add_tool_call(self, expert: str, tool_name: str, params: Dict,
                      result_count: int, latency_ms: float):
        """Aggiunge dettaglio tool call."""
        self.tool_calls.append({
            "expert": expert,
            "tool": tool_name,
            "params": params,
            "result_count": result_count,
            "latency_ms": latency_ms,
            "timestamp": datetime.now().isoformat()
        })

    def set_config_snapshot(self, snapshot: ConfigSnapshot):
        """Salva snapshot configurazione."""
        self.config_snapshot = snapshot.to_dict() if snapshot else None


# Global collector instance
_collector = TraceCollector()


class TracingAIService:
    """AI Service wrapper che cattura tutti i prompt e le risposte."""

    def __init__(self, real_service, expert_name: str = "unknown"):
        self.real_service = real_service
        self.expert_name = expert_name

    def _estimate_tokens(self, text: str) -> int:
        """Stima tokens dal testo (circa 3 chars per token in italiano)."""
        return max(1, len(text) // 3)

    def _get_tokens(self, prompt: str, response: str) -> int:
        """Ottiene tokens reali o stimati."""
        # Try to get actual usage from service
        if hasattr(self.real_service, 'get_last_usage'):
            usage = self.real_service.get_last_usage()
            if usage.get("total_tokens", 0) > 0:
                return usage["total_tokens"]

        # Fallback: estimate from text length
        prompt_tokens = self._estimate_tokens(prompt)
        response_tokens = self._estimate_tokens(response)
        return prompt_tokens + response_tokens

    async def generate_response_async(self, prompt: str, **kwargs) -> Dict[str, Any]:
        start = time.time()
        response = await self.real_service.generate_response_async(prompt, **kwargs)
        latency = (time.time() - start) * 1000

        if isinstance(response, dict):
            content = response.get("content", str(response))
            tokens = response.get("usage", {}).get("total_tokens", 0)
        else:
            content = str(response)
            tokens = self._get_tokens(prompt, content)

        _collector.add_llm_call(self.expert_name, prompt, content, tokens, latency)
        return response

    async def generate_completion(self, prompt: str, **kwargs) -> str:
        start = time.time()
        response = await self.real_service.generate_completion(prompt, **kwargs)
        latency = (time.time() - start) * 1000

        # Get tokens from API or estimate
        tokens = self._get_tokens(prompt, response)

        _collector.add_llm_call(self.expert_name, prompt, response, tokens, latency)
        return response


class TracingSemanticSearchTool:
    """Wrapper per SemanticSearchTool che cattura i risultati."""

    def __init__(self, real_tool, expert_name: str = "unknown"):
        self.real_tool = real_tool
        self.expert_name = expert_name
        self.name = real_tool.name
        self.description = real_tool.description

    async def __call__(self, **kwargs):
        start = time.time()
        result = await self.real_tool(**kwargs)
        latency = (time.time() - start) * 1000

        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", 5)
        source_types = kwargs.get("source_types", [])  # Nuovo: cattura source_types
        expert_type = kwargs.get("expert_type", "")
        results = result.data.get("results", []) if result.success else []

        _collector.add_retrieval(self.expert_name, query, results, latency)

        # Aggiungi dettaglio tool call con source_types
        expected_source_types = get_source_types_for_expert(expert_type) if expert_type else []
        _collector.add_tool_call(
            expert=self.expert_name,
            tool_name="semantic_search",
            params={
                "query": query,
                "top_k": top_k,
                "source_types": source_types,  # Effettivamente usati
                "expert_type": expert_type,
                "expected_source_types": expected_source_types  # Da mapping
            },
            result_count=len(results),
            latency_ms=latency
        )
        return result

    def get_schema(self) -> Dict[str, Any]:
        return self.real_tool.get_schema()


class TracingGraphSearchTool:
    """Wrapper per GraphSearchTool che cattura i risultati."""

    def __init__(self, real_tool, expert_name: str = "unknown"):
        self.real_tool = real_tool
        self.expert_name = expert_name
        self.name = real_tool.name
        self.description = real_tool.description

    async def __call__(self, **kwargs):
        start = time.time()
        result = await self.real_tool(**kwargs)
        latency = (time.time() - start) * 1000

        # Parametri corretti per GraphSearchTool
        start_node = kwargs.get("start_node", "")
        relation_types = kwargs.get("relation_types", [])
        max_hops = kwargs.get("max_hops", 2)

        # Il tool restituisce "nodes", non "results"
        nodes = result.data.get("nodes", []) if result.success else []

        _collector.add_retrieval(
            f"{self.expert_name}_graph",
            f"traverse from: {start_node[:50]}..." if start_node else "(no start_node)",
            nodes,
            latency
        )

        # Aggiungi dettaglio tool call
        _collector.add_tool_call(
            expert=self.expert_name,
            tool_name="graph_search",
            params={
                "start_node": start_node,
                "relation_types": relation_types,
                "max_hops": max_hops
            },
            result_count=len(nodes),
            latency_ms=latency
        )
        return result

    def get_schema(self) -> Dict[str, Any]:
        return self.real_tool.get_schema()


class TracingArticleFetchTool:
    """Wrapper per ArticleFetchTool che cattura i risultati."""

    def __init__(self, real_tool, expert_name: str = "unknown"):
        self.real_tool = real_tool
        self.expert_name = expert_name
        self.name = real_tool.name
        self.description = real_tool.description

    async def __call__(self, **kwargs):
        start = time.time()
        result = await self.real_tool(**kwargs)
        latency = (time.time() - start) * 1000

        tipo_atto = kwargs.get("tipo_atto", "")
        numero_articolo = kwargs.get("numero_articolo", "")

        # Log retrieval step
        if result.success:
            text_preview = result.data.get("text", "")[:200]
            _collector.add_retrieval(
                f"{self.expert_name}_fetch",
                f"Fetch {tipo_atto} art. {numero_articolo}",
                [{"text": text_preview, "urn": result.data.get("urn", "")}],
                latency
            )

        # Add tool call
        _collector.add_tool_call(
            expert=self.expert_name,
            tool_name="article_fetch",
            params={
                "tipo_atto": tipo_atto,
                "numero_articolo": numero_articolo,
                "data_atto": kwargs.get("data_atto"),
                "numero_atto": kwargs.get("numero_atto")
            },
            result_count=1 if result.success else 0,
            latency_ms=latency
        )
        return result

    def get_schema(self) -> Dict[str, Any]:
        return self.real_tool.get_schema()


# Source type mapping (retrieval → expert)
SOURCE_TYPE_MAP = {
    "norma": "norm",
    "massima": "jurisprudence",
    "ratio": "doctrine",
    "spiegazione": "doctrine",
    "principio": "principle",
    "articolo": "norm",
    "sentenza": "jurisprudence"
}


def normalize_source_type(source_type: str) -> str:
    """Normalizza source_type da retrieval a formato expert."""
    if not source_type:
        return "unknown"
    return SOURCE_TYPE_MAP.get(source_type.lower(), source_type)


def validate_sources(expert_sources: List[Dict], retrieved_chunks: List[Dict]) -> Dict[str, Any]:
    """
    Valida che le fonti citate dagli expert esistano nel retrieval.

    Returns:
        Dict con validated, hallucinated, grounding_rate
    """
    # Estrai tutti gli ID dai chunk recuperati
    retrieved_ids = set()
    for step in retrieved_chunks:
        for r in step.get("results", []):
            chunk_id = r.get("chunk_id")
            if chunk_id:
                retrieved_ids.add(str(chunk_id))
            # Anche source_id se presente
            source_id = r.get("source_id")
            if source_id:
                retrieved_ids.add(str(source_id))

    validated = []
    hallucinated = []

    for source in expert_sources:
        source_id = source.get("source_id", "")
        # Controlla se il source_id è nel retrieval
        if str(source_id) in retrieved_ids:
            validated.append(source)
        else:
            hallucinated.append(source)

    total = len(expert_sources)
    grounding_rate = len(validated) / total if total > 0 else 0.0

    return {
        "validated": validated,
        "hallucinated": hallucinated,
        "validated_count": len(validated),
        "hallucinated_count": len(hallucinated),
        "grounding_rate": grounding_rate
    }


def extract_article_citations(text: str) -> List[str]:
    """Estrae citazioni di articoli dal testo (es. 'art. 1453 c.c.')."""
    patterns = [
        r'[Aa]rt\.?\s*\d+(?:\s*(?:bis|ter|quater|quinquies|sexies))?\s*c\.?c\.?',  # art. 1453 c.c.
        r'[Aa]rticolo\s*\d+(?:\s*(?:bis|ter|quater|quinquies|sexies))?\s*(?:del\s*)?(?:codice\s*civile|c\.?c\.?)?',
        r'[Aa]rt\.?\s*\d+(?:\s*(?:bis|ter|quater|quinquies|sexies))?\s*c\.?p\.?',  # art. 52 c.p.
        r'[Ll]egge\s*\d+/\d+',  # legge 123/2020
    ]

    citations = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        citations.extend(matches)

    return list(set(citations))


async def run_baseline_llm(query: str, ai_service) -> Dict[str, Any]:
    """
    Esegue la query con LLM generico SENZA retrieval.
    Serve come baseline per confrontare con il sistema multi-expert.
    """
    prompt = f"""Sei un esperto di diritto civile italiano.
Rispondi alla seguente domanda giuridica citando gli articoli di legge rilevanti.

DOMANDA: {query}

Fornisci una risposta concisa (max 300 parole) con:
1. La risposta alla domanda
2. Gli articoli di legge pertinenti
3. Eventuali principi giuridici applicabili"""

    start = time.time()
    response = await ai_service.generate_completion(prompt)
    latency = (time.time() - start) * 1000

    # Estrai citazioni dalla risposta
    sources_cited = extract_article_citations(response)

    return {
        "response": response,
        "latency_ms": latency,
        "sources_cited": sources_cited,
        "prompt": prompt
    }


async def run_query_with_full_tracing(
    query: str,
    use_react: bool = False,
    react_iterations: int = 5,
    # Retrieval parameters
    top_k: int = 5,
    alpha: float = 0.7,
    max_graph_hops: int = 3,
    over_retrieve_factor: int = 3,
    # Model parameters
    model: str = "google/gemini-2.5-flash",
    temperature: float = 0.3,
    # Database parameters
    graph_name: str = "merl_t_dev",
    # Expert selection
    selected_experts_override: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Esegue una query catturando TUTTI i passaggi."""
    from merlt import LegalKnowledgeGraph
    from merlt.rlcf.ai_service import OpenRouterService
    from merlt.experts import (
        LiteralExpert, SystemicExpert, PrinciplesExpert, PrecedentExpert,
        ExpertRouter, GatingNetwork
    )
    from merlt.experts.base import ExpertContext
    from merlt.tools import SemanticSearchTool, GraphSearchTool, ArticleFetchTool
    from merlt.storage.retriever import GraphAwareRetriever, RetrieverConfig

    # Reset collector
    _collector.reset()

    start_time = time.time()
    trace_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Store run parameters for visibility
    run_parameters = {
        "query": query,
        "trace_id": trace_id,
        "use_react": use_react,
        "react_iterations": react_iterations if use_react else None,
        "top_k": top_k,
        "alpha": alpha,
        "max_graph_hops": max_graph_hops,
        "over_retrieve_factor": over_retrieve_factor,
        "model": model,
        "temperature": temperature,
        "graph_name": graph_name,
        "selected_experts_override": selected_experts_override,
        "started_at": datetime.now().isoformat()
    }

    # Crea snapshot configurazione per version tracking
    config_snapshot = _config_manager.create_snapshot(trace_id)
    _collector.set_config_snapshot(config_snapshot)

    # Connect to KG
    from merlt.core.legal_knowledge_graph import MerltConfig
    config = MerltConfig(graph_name=graph_name)
    kg = LegalKnowledgeGraph(config=config)
    await kg.connect()

    # Capture database info
    qdrant_collection = kg.config.qdrant_collection
    try:
        qdrant_info = kg.qdrant.get_collection(qdrant_collection)
        qdrant_points = qdrant_info.points_count
    except Exception as e:
        qdrant_points = f"Error: {e}"

    # FalkorDB nodes count (async query)
    try:
        falkor_node_result = await kg.falkordb.query("MATCH (n) RETURN count(n) as nodes")
        falkor_nodes = falkor_node_result[0]["nodes"] if falkor_node_result else 0
    except Exception as e:
        falkor_nodes = f"Error: {e}"

    # FalkorDB relations count
    try:
        falkor_rel_result = await kg.falkordb.query("MATCH ()-[r]->() RETURN count(r) as relations")
        falkor_relations = falkor_rel_result[0]["relations"] if falkor_rel_result else 0
    except Exception as e:
        falkor_relations = f"Error: {e}"

    # Bridge table mappings count
    try:
        bridge_mappings = await kg.bridge_table.count()
    except Exception as e:
        bridge_mappings = f"Error: {e}"

    _collector.set_database_info({
        "falkordb_graph": kg.config.graph_name,
        "falkordb_nodes": falkor_nodes,
        "falkordb_relations": falkor_relations,
        "qdrant_collection": qdrant_collection,
        "qdrant_points": qdrant_points,
        "bridge_table": "bridge_table",
        "bridge_mappings": bridge_mappings
    })

    # Setup components
    real_ai_service = OpenRouterService()

    # Configure retriever with custom parameters
    retriever_config = RetrieverConfig(
        collection_name=qdrant_collection,
        alpha=alpha,
        max_graph_hops=max_graph_hops,
        over_retrieve_factor=over_retrieve_factor
    )
    retriever = GraphAwareRetriever(
        vector_db=kg.qdrant,
        graph_db=kg.falkordb,
        bridge_table=kg.bridge_table,
        config=retriever_config
    )

    real_semantic_tool = SemanticSearchTool(retriever, kg._embedding_service)
    real_graph_tool = GraphSearchTool(kg.falkordb)
    real_article_fetch_tool = ArticleFetchTool()  # Per recuperare articoli da Normattiva

    # Router
    router = ExpertRouter()

    # Context
    query_embedding = kg._embedding_service.encode_query(query)
    context = ExpertContext(
        query_text=query,
        query_embedding=query_embedding.tolist() if hasattr(query_embedding, 'tolist') else list(query_embedding),
        trace_id=trace_id
    )

    # Routing
    routing = await router.route(context)
    _collector.set_routing({
        "query_type": routing.query_type,
        "expert_weights": routing.expert_weights,
        "confidence": routing.confidence,
        "reasoning": routing.reasoning
    })

    # Seleziona expert (with override support)
    if selected_experts_override:
        selected_experts = selected_experts_override
    else:
        selected_experts = [exp for exp, weight in routing.expert_weights.items() if weight >= 0.15]

    # Esegui ogni expert
    expert_responses = []

    for exp_type in selected_experts:
        # Crea tool e AI service con tracing
        tracing_semantic = TracingSemanticSearchTool(real_semantic_tool, exp_type)
        tracing_graph = TracingGraphSearchTool(real_graph_tool, exp_type)
        tracing_article_fetch = TracingArticleFetchTool(real_article_fetch_tool, exp_type)
        tracing_ai = TracingAIService(real_ai_service, exp_type)
        tools = [tracing_semantic, tracing_graph, tracing_article_fetch]

        # Crea expert con config completa (ReAct + Model + Temperature)
        expert_config = {
            "use_react": use_react,
            "react_max_iterations": react_iterations,
            "react_novelty_threshold": 0.1,
            "model": model,
            "temperature": temperature,
            "top_k": top_k
        }

        if exp_type == "literal":
            expert = LiteralExpert(tools=tools, ai_service=tracing_ai, config=expert_config)
        elif exp_type == "systemic":
            expert = SystemicExpert(tools=tools, ai_service=tracing_ai, config=expert_config)
        elif exp_type == "principles":
            expert = PrinciplesExpert(tools=tools, ai_service=tracing_ai, config=expert_config)
        elif exp_type == "precedent":
            expert = PrecedentExpert(tools=tools, ai_service=tracing_ai, config=expert_config)
        else:
            continue

        try:
            response = await expert.analyze(context)
            expert_responses.append(response)

            _collector.add_expert_result(exp_type, {
                "interpretation": response.interpretation,
                "confidence": response.confidence,
                "sources": [s.to_dict() for s in response.legal_basis],
                "reasoning_steps": [rs.to_dict() for rs in response.reasoning_steps],
                "confidence_factors": response.confidence_factors.to_dict() if response.confidence_factors else {},
                "limitations": response.limitations,
                "tokens_used": response.tokens_used
            })
        except Exception as e:
            _collector.add_expert_result(exp_type, {"error": str(e)})

    # Aggregazione
    final_synthesis = ""
    final_confidence = 0.0

    if expert_responses:
        gating = GatingNetwork()
        gating.ai_service = TracingAIService(real_ai_service, "aggregation")

        aggregated = await gating.aggregate(expert_responses, routing.expert_weights, context.trace_id)
        final_synthesis = aggregated.synthesis
        final_confidence = aggregated.confidence

        # Capture aggregation prompt/response from llm_calls
        for call in reversed(_collector.llm_calls):
            if call.get("expert") == "aggregation":
                _collector.set_aggregation(call.get("prompt", ""), call.get("response", ""))
                break

    # Esegui baseline LLM (senza RAG) per confronto
    baseline_result = await run_baseline_llm(query, real_ai_service)
    _collector.set_baseline(
        response=baseline_result["response"],
        latency_ms=baseline_result["latency_ms"],
        sources_cited=baseline_result["sources_cited"]
    )

    total_latency = (time.time() - start_time) * 1000

    await kg.close()

    # Estrai fonti expert per confronto e validazione
    expert_sources = []
    expert_sources_full = []
    for exp_type, res in _collector.expert_results.items():
        if 'sources' in res:
            expert_sources.extend([s.get('citation', '') for s in res['sources']])
            expert_sources_full.extend(res['sources'])

    # Valida fonti contro retrieval
    source_validation = validate_sources(expert_sources_full, _collector.retrieval_steps)

    # Compute token/cost statistics
    total_tokens = sum(call.get("tokens", 0) for call in _collector.llm_calls)
    expert_tokens = {exp: 0 for exp in selected_experts}
    for call in _collector.llm_calls:
        exp = call.get("expert", "unknown")
        if exp in expert_tokens:
            expert_tokens[exp] += call.get("tokens", 0)

    # Model-specific cost per 1K tokens (input + output average)
    MODEL_COSTS = {
        "google/gemini-2.5-flash": 0.00015,  # ~$0.075/1M input + $0.30/1M output avg
        "google/gemini-2.5-pro": 0.00625,    # ~$1.25/1M input + $10/1M output avg
        "anthropic/claude-3.5-sonnet": 0.009, # $3/1M input + $15/1M output avg
        "openai/gpt-4o-mini": 0.0003,        # $0.15/1M input + $0.60/1M output avg
        "openai/gpt-4o": 0.0075,             # $2.5/1M input + $10/1M output avg
    }
    cost_per_1k = MODEL_COSTS.get(model, 0.0005)  # Default fallback
    estimated_cost = (total_tokens / 1000) * cost_per_1k

    # Calculate per-expert costs
    expert_costs = {exp: (tokens / 1000) * cost_per_1k for exp, tokens in expert_tokens.items()}

    token_stats = {
        "total_tokens": total_tokens,
        "tokens_by_expert": expert_tokens,
        "costs_by_expert": expert_costs,
        "aggregation_tokens": sum(c.get("tokens", 0) for c in _collector.llm_calls if c.get("expert") == "aggregation"),
        "baseline_tokens": sum(c.get("tokens", 0) for c in _collector.llm_calls if "baseline" in c.get("expert", "")),
        "estimated_cost_usd": round(estimated_cost, 6),
        "cost_per_1k_tokens": cost_per_1k,
        "model_used": model,
        "llm_calls_count": len(_collector.llm_calls)
    }

    # Update run_parameters with completion info
    run_parameters["completed_at"] = datetime.now().isoformat()
    run_parameters["selected_experts_final"] = selected_experts
    run_parameters["total_latency_ms"] = total_latency

    # Costruisci risultato finale
    return {
        "query": query,
        "trace_id": trace_id,
        "timestamp": datetime.now().isoformat(),
        "total_latency_ms": total_latency,
        "run_parameters": run_parameters,
        "token_stats": token_stats,
        "database_info": _collector.database_info,
        "routing": _collector.routing,
        "retrieval_steps": _collector.retrieval_steps,
        "llm_calls": _collector.llm_calls,
        "tool_calls": _collector.tool_calls,
        "expert_results": _collector.expert_results,
        "aggregation": _collector.aggregation,
        "final_synthesis": final_synthesis,
        "final_confidence": final_confidence,
        "baseline": _collector.baseline,
        "comparison": {
            "expert_sources_count": len(expert_sources),
            "baseline_sources_count": len(baseline_result["sources_cited"]),
            "expert_sources": list(set(expert_sources)),
            "baseline_sources": baseline_result["sources_cited"],
            "expert_grounded": True,  # Da retrieval
            "baseline_grounded": False  # Inventate da LLM
        },
        "source_validation": source_validation,
        "config_snapshot": _collector.config_snapshot
    }


def render_retrieval_step(step: Dict, idx: int):
    """Render un passaggio di retrieval."""
    is_graph = "_graph" in step.get('expert', '')
    icon = "🔗" if is_graph else "🔍"

    with st.expander(f"{icon} [{step['expert']}] {step['query'][:60]}...", expanded=False):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Query:** `{step['query']}`")
        with col2:
            st.metric("Latency", f"{step['latency_ms']:.0f}ms")
            st.metric("Results", len(step['results']))

        if step['results']:
            st.markdown("---")
            for i, result in enumerate(step['results'][:5]):
                if is_graph:
                    # Graph search results hanno struttura diversa
                    props = result.get("properties", {})
                    if isinstance(props, dict) and "properties" in props:
                        props = props["properties"]

                    node_type = result.get("type", props.get("labels", ["Unknown"])[0] if isinstance(props.get("labels"), list) else "Unknown")
                    if node_type == "Unknown":
                        node_type = props.get("labels", ["Node"])[0] if isinstance(props.get("labels"), list) else "Node"

                    text = props.get("testo_vigente", props.get("testo", props.get("nome", props.get("descrizione", ""))))[:400]
                    urn = props.get("URN", props.get("node_id", ""))
                    estremi = props.get("estremi", props.get("nome", ""))

                    st.markdown(f"**[{i+1}] {node_type}**: `{estremi or urn[:50]}`")
                    if text:
                        st.code(text, language=None)
                else:
                    # Semantic search results
                    text = result.get("text", "")[:400]
                    score = result.get("final_score", result.get("similarity_score", 0))
                    source_type = result.get("source_type", "unknown")

                    st.markdown(f"**[{i+1}] Score: {score:.3f} | Type: `{source_type}`**")
                    st.code(text, language=None)


def render_llm_call(call: Dict, idx: int):
    """Render una chiamata LLM."""
    expert = call.get('expert', 'unknown')
    tokens = call.get('tokens', 0)
    latency = call.get('latency_ms', 0)

    with st.expander(f"🤖 [{expert}] LLM Call ({tokens} tokens, {latency:.0f}ms)", expanded=False):
        tab1, tab2 = st.tabs(["Prompt", "Response"])

        with tab1:
            prompt = call.get('prompt', '')
            # Mostra parti significative del prompt
            st.code(prompt[:4000] + ("\n\n... [truncated]" if len(prompt) > 4000 else ""), language="markdown")

        with tab2:
            response = call.get('response', '')
            # Prova a formattare JSON
            try:
                parsed = json.loads(response)
                st.json(parsed)
            except:
                st.code(response[:6000] + ("\n\n... [truncated]" if len(response) > 6000 else ""), language="json")


def main():
    st.set_page_config(
        page_title="MERL-T Expert Debugger",
        page_icon="⚖️",
        layout="wide"
    )

    st.title("⚖️ MERL-T Expert System Debugger")
    st.markdown("Visualizza tutti i passaggi: retrieval dal database, prompt LLM, risposte degli expert.")

    # Sidebar
    with st.sidebar:
        st.header("📊 Info Database")
        st.markdown("""
        **Storage:**
        - FalkorDB: `localhost:6380`
        - Qdrant: `localhost:6333`
        - PostgreSQL: `localhost:5433`

        **Contenuto:**
        - Libro IV Codice Civile
        - Artt. 1173-2059 (Obbligazioni)
        """)

        st.divider()

        st.header("🎯 Expert Source Types")
        st.markdown("*Ogni expert cerca tipi di fonte specifici (Art. 12 Preleggi)*")
        expert_types_info = {
            "LiteralExpert": ("norma", "Significato proprio delle parole"),
            "SystemicExpert": ("norma", "Connessione tra norme"),
            "PrinciplesExpert": ("ratio, spiegazione", "Principi generali"),
            "PrecedentExpert": ("massima", "Diritto vivente"),
        }
        for exp, (types, desc) in expert_types_info.items():
            st.markdown(f"**{exp}**")
            st.caption(f"`{types}` - {desc}")

        st.divider()

        st.header("📝 Query di Esempio")
        examples = [
            "Quali sono le fonti delle obbligazioni secondo l'art. 1173 c.c.?",
            "Cosa prevede l'art. 1218 c.c. sulla responsabilità del debitore?",
            "Come funziona la risoluzione per inadempimento (art. 1453 c.c.)?",
            "Qual è la responsabilità del vettore nel contratto di trasporto?",
            "Orientamento della Cassazione sulla fideiussione omnibus",
        ]

        for i, ex in enumerate(examples):
            if st.button(ex[:45] + "...", key=f"ex_{i}", use_container_width=True):
                st.session_state.query_input = ex

        # Configuration Section
        st.divider()
        st.header("⚙️ Run Parameters")

        # Database Selection
        with st.expander("🗄️ Database", expanded=False):
            graph_name = st.selectbox(
                "Graph Database",
                options=["merl_t_dev", "merl_t_prod"],
                index=0,
                help="Select development or production database"
            )
            st.session_state.graph_name = graph_name

        # Retrieval Settings
        with st.expander("🔍 Retrieval Settings", expanded=False):
            top_k = st.slider(
                "Top K Results",
                min_value=3,
                max_value=20,
                value=st.session_state.get("top_k", 5),
                step=1,
                help="Number of results to retrieve per query"
            )
            st.session_state.top_k = top_k

            alpha = st.slider(
                "Alpha (semantic vs graph)",
                min_value=0.3,
                max_value=0.9,
                value=st.session_state.get("alpha", _config_manager.get_retrieval_alpha()),
                step=0.05,
                help="0.7 = 70% semantic, 30% graph"
            )
            st.session_state.alpha = alpha

            max_graph_hops = st.slider(
                "Max Graph Hops",
                min_value=1,
                max_value=5,
                value=st.session_state.get("max_graph_hops", 3),
                step=1,
                help="Maximum hops for graph traversal"
            )
            st.session_state.max_graph_hops = max_graph_hops

            over_retrieve_factor = st.slider(
                "Over-retrieve Factor",
                min_value=1,
                max_value=5,
                value=st.session_state.get("over_retrieve_factor", 3),
                step=1,
                help="Retrieve N x top_k for re-ranking"
            )
            st.session_state.over_retrieve_factor = over_retrieve_factor

        # Model Settings
        with st.expander("🤖 Model Settings", expanded=False):
            model = st.selectbox(
                "LLM Model",
                options=[
                    "google/gemini-2.5-flash",
                    "google/gemini-2.5-pro",
                    "anthropic/claude-3.5-sonnet",
                    "openai/gpt-4o-mini",
                    "openai/gpt-4o"
                ],
                index=0,
                help="Select the LLM model for expert reasoning"
            )
            st.session_state.model = model

            temperature = st.slider(
                "LLM Temperature",
                min_value=0.0,
                max_value=1.0,
                value=st.session_state.get("temperature", 0.3),
                step=0.1,
                help="Lower = more deterministic"
            )
            st.session_state.temperature = temperature

        # Expert Settings
        with st.expander("🧠 Expert Settings", expanded=False):
            # Expert Selection Override
            st.markdown("**Expert Selection**")
            all_experts = ["literal", "systemic", "principles", "precedent"]
            selected_experts = st.multiselect(
                "Force Specific Experts",
                options=all_experts,
                default=st.session_state.get("selected_experts_override", []),
                help="Leave empty for automatic routing"
            )
            st.session_state.selected_experts_override = selected_experts if selected_experts else None

            # ReAct Mode Toggle
            st.markdown("---")
            st.markdown("**🔄 ReAct Mode**")
            use_react = st.toggle(
                "Enable ReAct Pattern",
                value=st.session_state.get("use_react", False),
                help="LLM decides dynamically which tools to use (experimental)"
            )
            st.session_state.use_react = use_react

            if use_react:
                react_iterations = st.slider(
                    "Max ReAct Iterations",
                    min_value=2,
                    max_value=10,
                    value=st.session_state.get("react_iterations", 5),
                    step=1,
                    help="Max tool calls per expert"
                )
                st.session_state.react_iterations = react_iterations
                st.info("⚡ ReAct mode: LLM autonomously selects tools at each step")

        # Gating Weights
        with st.expander("Expert Gating", expanded=False):
            gating = _config_manager.get_gating_weights()
            st.caption("Pesi per ogni Expert (devono sommare a 1.0)")

            literal_w = st.slider("Literal", 0.0, 0.6, gating.get("LiteralExpert", 0.25), 0.05, key="g_lit")
            systemic_w = st.slider("Systemic", 0.0, 0.6, gating.get("SystemicExpert", 0.25), 0.05, key="g_sys")
            principles_w = st.slider("Principles", 0.0, 0.6, gating.get("PrinciplesExpert", 0.25), 0.05, key="g_pri")
            precedent_w = st.slider("Precedent", 0.0, 0.6, gating.get("PrecedentExpert", 0.25), 0.05, key="g_pre")

            total = literal_w + systemic_w + principles_w + precedent_w
            if abs(total - 1.0) > 0.05:
                st.warning(f"Somma: {total:.2f} (dovrebbe essere 1.0)")

        # Config Hash (version tracking)
        config_hash = _config_manager.compute_hash()
        st.caption(f"Config hash: `{config_hash[:8]}...`")

    # Main content
    query = st.text_area(
        "🔎 Inserisci la tua query giuridica",
        value=st.session_state.get("query_input", ""),
        height=80,
        placeholder="Es: Cosa prevede l'art. 1218 c.c. sulla responsabilità del debitore?"
    )

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        run_button = st.button("🚀 Esegui", type="primary", use_container_width=True)
    with col2:
        if st.button("🗑️ Reset", use_container_width=True):
            if "result" in st.session_state:
                del st.session_state.result

    if run_button and query:
        # Collect all parameters from session state
        use_react = st.session_state.get("use_react", False)
        react_iterations = st.session_state.get("react_iterations", 5)
        top_k = st.session_state.get("top_k", 5)
        alpha = st.session_state.get("alpha", 0.7)
        max_graph_hops = st.session_state.get("max_graph_hops", 3)
        over_retrieve_factor = st.session_state.get("over_retrieve_factor", 3)
        model = st.session_state.get("model", "google/gemini-2.5-flash")
        temperature = st.session_state.get("temperature", 0.3)
        graph_name = st.session_state.get("graph_name", "merl_t_dev")
        selected_experts_override = st.session_state.get("selected_experts_override", None)

        mode_str = "ReAct" if use_react else "Standard"
        with st.spinner(f"⏳ Elaborazione in corso ({mode_str} mode)... (può richiedere 15-30 secondi)"):
            try:
                result = asyncio.run(run_query_with_full_tracing(
                    query,
                    use_react=use_react,
                    react_iterations=react_iterations,
                    top_k=top_k,
                    alpha=alpha,
                    max_graph_hops=max_graph_hops,
                    over_retrieve_factor=over_retrieve_factor,
                    model=model,
                    temperature=temperature,
                    graph_name=graph_name,
                    selected_experts_override=selected_experts_override
                ))
                st.session_state.result = result
                st.success(f"✅ Query completata! ({mode_str} mode)")
            except Exception as e:
                st.error(f"❌ Errore: {e}")
                import traceback
                with st.expander("Stack trace"):
                    st.code(traceback.format_exc())

    # Mostra risultati
    if "result" in st.session_state:
        result = st.session_state.result

        st.divider()

        # Primary Metrics Row
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric("🎯 Confidence", f"{result['final_confidence']:.2f}")
        with col2:
            st.metric("🧠 Experts", len(result['expert_results']))
        with col3:
            st.metric("⏱️ Latency", f"{result['total_latency_ms']:.0f}ms")
        with col4:
            st.metric("📂 Query Type", result['routing'].get('query_type', 'N/A'))
        with col5:
            token_stats = result.get('token_stats', {})
            st.metric("🔤 Tokens", f"{token_stats.get('total_tokens', 0):,}")
        with col6:
            st.metric("💰 Est. Cost", f"${token_stats.get('estimated_cost_usd', 0):.4f}")

        # Run Parameters Summary
        run_params = result.get('run_parameters', {})
        if run_params:
            with st.expander("📋 Run Parameters", expanded=False):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f"**Trace ID:** `{run_params.get('trace_id', 'N/A')}`")
                    st.markdown(f"**Model:** `{run_params.get('model', 'N/A')}`")
                    st.markdown(f"**Temperature:** `{run_params.get('temperature', 'N/A')}`")
                with col2:
                    st.markdown(f"**Top K:** `{run_params.get('top_k', 'N/A')}`")
                    st.markdown(f"**Alpha:** `{run_params.get('alpha', 'N/A')}`")
                    st.markdown(f"**Max Hops:** `{run_params.get('max_graph_hops', 'N/A')}`")
                with col3:
                    st.markdown(f"**Database:** `{run_params.get('graph_name', 'N/A')}`")
                    st.markdown(f"**ReAct Mode:** `{run_params.get('use_react', False)}`")
                    if run_params.get('use_react'):
                        st.markdown(f"**ReAct Iterations:** `{run_params.get('react_iterations', 'N/A')}`")
                with col4:
                    experts_used = run_params.get('selected_experts_final', [])
                    st.markdown(f"**Experts Used:** `{', '.join(experts_used) if experts_used else 'N/A'}`")
                    st.markdown(f"**Started:** `{run_params.get('started_at', 'N/A')[:19]}`")
                    st.markdown(f"**Duration:** `{run_params.get('total_latency_ms', 0):.0f}ms`")

        st.divider()

        # Database info banner
        db_info = result.get('database_info', {})
        if db_info:
            falkor_info = f"FalkorDB `{db_info.get('falkordb_graph')}` ({db_info.get('falkordb_nodes')} nodi, {db_info.get('falkordb_relations')} relazioni)"
            qdrant_info = f"Qdrant `{db_info.get('qdrant_collection')}` ({db_info.get('qdrant_points')} vettori)"
            bridge_info = f"Bridge Table ({db_info.get('bridge_mappings')} mappings)"
            st.info(f"🗄️ **Database**: {falkor_info} | {qdrant_info} | {bridge_info}")

        # Tabs principali
        tab_routing, tab_retrieval, tab_tools, tab_llm, tab_experts, tab_synthesis, tab_baseline, tab_rlcf, tab_config, tab_trace = st.tabs([
            "🎯 Routing",
            "🔍 Retrieval",
            "🔧 Tool Calls",
            "🤖 LLM Calls",
            "🧠 Expert Results",
            "📄 Sintesi Finale",
            "📊 Baseline",
            "📈 RLCF Stats",
            "⚙️ Config",
            "📜 Full Trace"
        ])

        with tab_routing:
            st.subheader("Routing Decision")
            routing = result['routing']

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Query Type:** `{routing.get('query_type', 'N/A')}`")
                st.markdown(f"**Confidence:** `{routing.get('confidence', 0):.2f}`")
                st.markdown(f"**Reasoning:** {routing.get('reasoning', 'N/A')}")

            with col2:
                st.markdown("**Expert Weights:**")
                weights = routing.get('expert_weights', {})
                for exp, weight in sorted(weights.items(), key=lambda x: -x[1]):
                    color = "green" if weight >= 0.3 else "orange" if weight >= 0.15 else "gray"
                    st.markdown(f":{color}[{exp}]: {weight:.2f} {'✓ selected' if weight >= 0.15 else ''}")

        with tab_retrieval:
            st.subheader(f"Retrieval Steps ({len(result['retrieval_steps'])})")
            if result['retrieval_steps']:
                for i, step in enumerate(result['retrieval_steps']):
                    render_retrieval_step(step, i)
            else:
                st.info("Nessun retrieval eseguito")

        with tab_tools:
            st.subheader(f"Tool Calls ({len(result.get('tool_calls', []))})")
            tool_calls = result.get('tool_calls', [])

            if tool_calls:
                # Raggruppa per expert
                by_expert = defaultdict(list)
                for tc in tool_calls:
                    by_expert[tc['expert']].append(tc)

                for expert, calls in by_expert.items():
                    # Mostra source_types attesi per questo expert
                    expected_st = get_source_types_for_expert(expert.replace("_graph", ""))
                    expert_label = f"🔧 {expert.upper()} - {len(calls)} tool calls"
                    if expected_st:
                        expert_label += f" | source_types: `{expected_st}`"

                    with st.expander(expert_label, expanded=True):
                        for tc in calls:
                            col1, col2, col3 = st.columns([2, 1, 1])
                            with col1:
                                st.markdown(f"**{tc['tool']}**")

                                # Evidenzia source_types se presenti
                                params = tc['params']
                                source_types = params.get('source_types', [])
                                expected = params.get('expected_source_types', [])

                                if source_types:
                                    match = "✅" if source_types == expected else "⚠️"
                                    st.markdown(f"{match} **source_types**: `{source_types}`")
                                else:
                                    st.markdown("⚠️ **source_types**: *non specificato*")

                                # Mostra altri params
                                display_params = {k: v for k, v in params.items()
                                                  if k not in ['source_types', 'expected_source_types']}
                                st.code(json.dumps(display_params, indent=2), language="json")
                            with col2:
                                st.metric("Results", tc['result_count'])
                            with col3:
                                st.metric("Latency", f"{tc['latency_ms']:.0f}ms")
            else:
                st.info("Nessun tool call registrato")

        with tab_llm:
            st.subheader(f"LLM Calls ({len(result['llm_calls'])})")
            if result['llm_calls']:
                # Raggruppa per expert
                by_expert = defaultdict(list)
                for call in result['llm_calls']:
                    by_expert[call['expert']].append(call)

                for expert, calls in by_expert.items():
                    st.markdown(f"### {expert.upper()}")
                    for i, call in enumerate(calls):
                        render_llm_call(call, i)
            else:
                st.info("Nessuna chiamata LLM")

        with tab_experts:
            st.subheader("Expert Results")
            for expert, res in result['expert_results'].items():
                status = "✅" if res.get('confidence', 0) > 0.5 else "⚠️" if 'error' not in res else "❌"
                tokens = res.get('tokens_used', 0)
                with st.expander(f"{status} {expert.upper()} (conf: {res.get('confidence', 0):.2f}, {tokens} tokens)", expanded=True):
                    if 'error' in res:
                        st.error(res['error'])
                    else:
                        st.markdown("**Interpretazione:**")
                        st.markdown(res.get('interpretation', '*Nessuna*'))

                        # Reasoning Steps
                        if res.get('reasoning_steps'):
                            st.markdown("**Ragionamento:**")
                            for step in res['reasoning_steps']:
                                step_num = step.get('step_number', '?')
                                description = step.get('description', '')
                                sources = step.get('sources', [])
                                st.markdown(f"{step_num}. {description}")
                                if sources:
                                    st.caption(f"   Fonti: {', '.join(sources)}")

                        # Sources
                        if res.get('sources'):
                            st.markdown("**Fonti giuridiche:**")
                            for src in res['sources']:
                                citation = src.get('citation', 'N/A')
                                source_type = src.get('source_type', 'N/A')
                                source_id = src.get('source_id', 'N/A')
                                st.markdown(f"- `{citation}` | Type: `{source_type}` | ID: `{source_id[:30]}...`")

                        # Confidence Factors
                        if res.get('confidence_factors'):
                            cf = res['confidence_factors']
                            st.markdown("**Confidence Factors:**")
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Norm Clarity", f"{cf.get('norm_clarity', 0):.2f}")
                            with col2:
                                st.metric("Jurisp. Align", f"{cf.get('jurisprudence_alignment', 0):.2f}")
                            with col3:
                                st.metric("Ctx Ambiguity", f"{cf.get('contextual_ambiguity', 0):.2f}")
                            with col4:
                                st.metric("Source Avail", f"{cf.get('source_availability', 0):.2f}")

                        if res.get('limitations'):
                            st.markdown(f"**Limitazioni:** {res['limitations']}")

        with tab_synthesis:
            st.subheader("Sintesi Finale")
            st.markdown(f"**Confidence:** {result['final_confidence']:.2f}")
            st.divider()
            st.markdown(result['final_synthesis'] or "*Nessuna sintesi generata*")

            if result.get('aggregation', {}).get('prompt'):
                with st.expander("📝 Aggregation Prompt"):
                    st.code(result['aggregation']['prompt'][:3000], language="markdown")

        with tab_baseline:
            st.subheader("📊 Confronto Scientifico: Expert System vs Baseline LLM")
            st.markdown("""
            *Confronto rigoroso basato su metriche EXP-020:*
            - **Source Grounding (SG)**: % fonti verificabili nel database
            - **Hallucination Rate (HR)**: % fonti inventate
            - **Faithfulness (F)**: fedeltà alle fonti citate
            """)

            baseline = result.get('baseline', {})
            comparison = result.get('comparison', {})
            validation = result.get('source_validation', {})
            expert_results = result.get('expert_results', {})

            # Compute scientific metrics
            expert_sources_count = comparison.get('expert_sources_count', 0)
            baseline_sources_count = comparison.get('baseline_sources_count', 0)

            # Expert metrics
            expert_grounding_rate = validation.get('grounding_rate', 0)
            expert_hallucination_rate = 1 - expert_grounding_rate
            expert_validated = validation.get('validated_count', 0)
            expert_hallucinated = validation.get('hallucinated_count', 0)

            # Baseline metrics (assume all sources are hallucinated since no retrieval)
            baseline_grounding_rate = 0.0  # No retrieval = no grounding
            baseline_hallucination_rate = 1.0  # All sources are potentially invented

            # Confidence comparison
            expert_confidences = [r.get('confidence', 0) for r in expert_results.values()]
            avg_expert_confidence = sum(expert_confidences) / len(expert_confidences) if expert_confidences else 0

            st.divider()

            # Scientific Metrics Dashboard
            st.markdown("### 📈 Metriche Scientifiche")

            # Create comparison table
            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)

            with metrics_col1:
                st.markdown("#### Source Grounding (SG)")
                st.markdown("*% fonti verificate nel database*")

                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Expert",
                        f"{expert_grounding_rate:.1%}",
                        delta=f"+{expert_grounding_rate - baseline_grounding_rate:.1%}",
                        delta_color="normal"
                    )
                with col2:
                    st.metric(
                        "Baseline",
                        f"{baseline_grounding_rate:.1%}",
                        help="0% perché non usa retrieval"
                    )

                # Progress bars
                st.progress(expert_grounding_rate, text=f"Expert: {expert_grounding_rate:.1%}")
                st.progress(baseline_grounding_rate, text=f"Baseline: {baseline_grounding_rate:.1%}")

            with metrics_col2:
                st.markdown("#### Hallucination Rate (HR)")
                st.markdown("*% fonti potenzialmente inventate*")

                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Expert",
                        f"{expert_hallucination_rate:.1%}",
                        delta=f"{expert_hallucination_rate - baseline_hallucination_rate:.1%}",
                        delta_color="inverse"  # Lower is better
                    )
                with col2:
                    st.metric(
                        "Baseline",
                        f"{baseline_hallucination_rate:.1%}",
                        help="100% perché non verifica fonti"
                    )

                # Progress bars (inverted - less is better)
                st.progress(expert_hallucination_rate, text=f"Expert: {expert_hallucination_rate:.1%}")
                st.progress(baseline_hallucination_rate, text=f"Baseline: {baseline_hallucination_rate:.1%}")

            with metrics_col3:
                st.markdown("#### Confidence Score")
                st.markdown("*Affidabilità auto-valutata*")

                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Expert",
                        f"{avg_expert_confidence:.2f}",
                        help="Media confidence dei 4 expert"
                    )
                with col2:
                    # Baseline doesn't have confidence, estimate from response
                    baseline_confidence = 0.5  # Default uncertain
                    st.metric(
                        "Baseline",
                        f"{baseline_confidence:.2f}",
                        help="Stimato (no self-assessment)"
                    )

                st.progress(avg_expert_confidence, text=f"Expert: {avg_expert_confidence:.2f}")
                st.progress(baseline_confidence, text=f"Baseline: {baseline_confidence:.2f}")

            st.divider()

            # Detailed Source Analysis
            st.markdown("### 🔍 Analisi Dettagliata Fonti")

            source_col1, source_col2 = st.columns(2)

            with source_col1:
                st.markdown("#### ✅ Expert System")
                st.success(f"**{expert_validated}** fonti verificate su **{expert_sources_count}** totali")

                if expert_validated > 0:
                    st.markdown("**Fonti Verificate nel Database:**")
                    validated_sources = validation.get('validated', [])
                    for src in validated_sources[:8]:
                        citation = src.get('citation', src.get('source_id', 'N/A'))
                        st.markdown(f"✓ `{citation}`")
                    if len(validated_sources) > 8:
                        st.markdown(f"*... e altre {len(validated_sources) - 8}*")

                if expert_hallucinated > 0:
                    st.warning(f"**{expert_hallucinated}** fonti non trovate nel database")
                    hallucinated = validation.get('hallucinated', [])
                    for src in hallucinated[:5]:
                        citation = src.get('citation', src.get('source_id', 'N/A'))
                        st.markdown(f"⚠️ `{citation}`")

            with source_col2:
                st.markdown("#### ⚠️ Baseline LLM")
                st.warning(f"**{baseline_sources_count}** fonti citate - **NESSUNA VERIFICATA**")

                baseline_sources = comparison.get('baseline_sources', [])
                if baseline_sources:
                    st.markdown("**Articoli Citati (non verificabili):**")
                    for src in baseline_sources[:8]:
                        st.markdown(f"❓ `{src}`")
                    if len(baseline_sources) > 8:
                        st.markdown(f"*... e altre {len(baseline_sources) - 8}*")
                else:
                    st.info("Nessuna fonte citata esplicitamente")

            st.divider()

            # Performance Comparison
            st.markdown("### ⚡ Performance Comparison")

            perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)

            expert_latency = result['total_latency_ms'] - baseline.get('latency_ms', 0)
            baseline_latency = baseline.get('latency_ms', 0)
            latency_overhead = ((expert_latency / baseline_latency) - 1) * 100 if baseline_latency > 0 else 0

            with perf_col1:
                st.metric(
                    "Expert Latency",
                    f"{expert_latency:.0f}ms",
                    delta=f"+{latency_overhead:.0f}% vs baseline",
                    delta_color="off"
                )

            with perf_col2:
                st.metric(
                    "Baseline Latency",
                    f"{baseline_latency:.0f}ms",
                    help="Più veloce ma senza retrieval"
                )

            with perf_col3:
                expert_tokens = result.get('token_stats', {}).get('total_tokens', 0)
                st.metric(
                    "Expert Tokens",
                    f"{expert_tokens:,}",
                    help="Include retrieval + 4 expert + aggregation"
                )

            with perf_col4:
                baseline_tokens = result.get('token_stats', {}).get('baseline_tokens', 0)
                st.metric(
                    "Baseline Tokens",
                    f"{baseline_tokens:,}",
                    help="Solo chiamata LLM diretta"
                )

            st.divider()

            # Side-by-side Response Comparison
            st.markdown("### 📝 Confronto Risposte")

            resp_col1, resp_col2 = st.columns(2)

            with resp_col1:
                st.markdown("#### ✅ Risposta Expert System (RAG)")
                with st.container(border=True):
                    st.success("Fonti verificate nel knowledge graph")
                    synthesis = result.get('final_synthesis', '')
                    if synthesis:
                        st.markdown(synthesis[:2000] + ("..." if len(synthesis) > 2000 else ""))
                    else:
                        st.info("*Nessuna sintesi generata*")

            with resp_col2:
                st.markdown("#### ⚠️ Risposta Baseline LLM")
                with st.container(border=True):
                    st.warning("Fonti potenzialmente inventate")
                    baseline_response = baseline.get('response', '')
                    if baseline_response:
                        st.markdown(baseline_response[:2000] + ("..." if len(baseline_response) > 2000 else ""))
                    else:
                        st.info("*Nessuna risposta baseline*")

            st.divider()

            # Summary Table
            st.markdown("### 📋 Tabella Riepilogativa")

            summary_data = {
                "Metrica": [
                    "Source Grounding",
                    "Hallucination Rate",
                    "Fonti Citate",
                    "Fonti Verificate",
                    "Confidence",
                    "Latency (ms)",
                    "Tokens Usati"
                ],
                "Expert System": [
                    f"{expert_grounding_rate:.1%}",
                    f"{expert_hallucination_rate:.1%}",
                    str(expert_sources_count),
                    str(expert_validated),
                    f"{avg_expert_confidence:.2f}",
                    f"{expert_latency:.0f}",
                    f"{expert_tokens:,}"
                ],
                "Baseline LLM": [
                    f"{baseline_grounding_rate:.1%}",
                    f"{baseline_hallucination_rate:.1%}",
                    str(baseline_sources_count),
                    "0",
                    f"{baseline_confidence:.2f}",
                    f"{baseline_latency:.0f}",
                    f"{baseline_tokens:,}"
                ],
                "Δ (Expert - Baseline)": [
                    f"+{(expert_grounding_rate - baseline_grounding_rate):.1%}",
                    f"{(expert_hallucination_rate - baseline_hallucination_rate):.1%}",
                    f"+{expert_sources_count - baseline_sources_count}",
                    f"+{expert_validated}",
                    f"+{(avg_expert_confidence - baseline_confidence):.2f}",
                    f"+{expert_latency - baseline_latency:.0f}",
                    f"+{expert_tokens - baseline_tokens:,}"
                ]
            }

            import pandas as pd
            df_summary = pd.DataFrame(summary_data)
            st.dataframe(df_summary, use_container_width=True, hide_index=True)

            # Export comparison
            st.divider()
            comparison_export = {
                "query": result.get('query'),
                "trace_id": result.get('trace_id'),
                "timestamp": result.get('timestamp'),
                "metrics": {
                    "expert": {
                        "source_grounding": expert_grounding_rate,
                        "hallucination_rate": expert_hallucination_rate,
                        "sources_cited": expert_sources_count,
                        "sources_verified": expert_validated,
                        "confidence": avg_expert_confidence,
                        "latency_ms": expert_latency,
                        "tokens": expert_tokens
                    },
                    "baseline": {
                        "source_grounding": baseline_grounding_rate,
                        "hallucination_rate": baseline_hallucination_rate,
                        "sources_cited": baseline_sources_count,
                        "sources_verified": 0,
                        "confidence": baseline_confidence,
                        "latency_ms": baseline_latency,
                        "tokens": baseline_tokens
                    },
                    "delta": {
                        "source_grounding": expert_grounding_rate - baseline_grounding_rate,
                        "hallucination_rate": expert_hallucination_rate - baseline_hallucination_rate,
                        "confidence": avg_expert_confidence - baseline_confidence
                    }
                },
                "expert_synthesis": result.get('final_synthesis'),
                "baseline_response": baseline.get('response'),
                "sources": {
                    "expert_verified": validation.get('validated', []),
                    "expert_hallucinated": validation.get('hallucinated', []),
                    "baseline_cited": comparison.get('baseline_sources', [])
                }
            }

            st.download_button(
                "📥 Esporta Confronto Scientifico (JSON)",
                data=json.dumps(comparison_export, indent=2, ensure_ascii=False, default=str),
                file_name=f"comparison_{result.get('trace_id', 'unknown')}.json",
                mime="application/json",
                use_container_width=True
            )

        with tab_rlcf:
            st.subheader("📈 Statistiche RLCF (Reinforcement Learning from Community Feedback)")

            # Calcola statistiche
            retrievals = result.get('retrieval_steps', [])
            llm_calls = result.get('llm_calls', [])
            expert_results = result.get('expert_results', {})
            baseline = result.get('baseline', {})

            # Retrieval Quality
            st.markdown("### 🔍 Retrieval Quality")
            if retrievals:
                all_scores = []
                all_final_scores = []
                source_types = defaultdict(int)
                unique_chunks = set()

                for step in retrievals:
                    for r in step.get('results', []):
                        if r.get('similarity_score'):
                            all_scores.append(r['similarity_score'])
                        if r.get('final_score'):
                            all_final_scores.append(r['final_score'])
                        if r.get('source_type'):
                            source_types[r['source_type']] += 1
                        if r.get('chunk_id'):
                            unique_chunks.add(r['chunk_id'])

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    avg_sim = sum(all_scores) / len(all_scores) if all_scores else 0
                    st.metric("Avg Similarity", f"{avg_sim:.3f}")
                with col2:
                    avg_final = sum(all_final_scores) / len(all_final_scores) if all_final_scores else 0
                    st.metric("Avg Final Score", f"{avg_final:.3f}")
                with col3:
                    st.metric("Unique Chunks", len(unique_chunks))
                with col4:
                    total_results = sum(len(s.get('results', [])) for s in retrievals)
                    st.metric("Total Results", total_results)

                # Source Type Distribution
                if source_types:
                    st.markdown("**Source Type Distribution:**")
                    st.bar_chart(dict(source_types))
            else:
                st.info("Nessun retrieval per calcolare statistiche")

            st.divider()

            # Expert Quality
            st.markdown("### 🧠 Expert Quality")
            if expert_results:
                confidences = [r.get('confidence', 0) for r in expert_results.values() if 'confidence' in r]

                col1, col2, col3 = st.columns(3)
                with col1:
                    avg_conf = sum(confidences) / len(confidences) if confidences else 0
                    st.metric("Avg Confidence", f"{avg_conf:.2f}")
                with col2:
                    st.metric("Experts Used", len(expert_results))
                with col3:
                    errors = sum(1 for r in expert_results.values() if 'error' in r)
                    st.metric("Expert Errors", errors, delta_color="inverse")

                # Confidence per expert
                st.markdown("**Confidence per Expert:**")
                conf_data = {exp: res.get('confidence', 0) for exp, res in expert_results.items() if 'confidence' in res}
                if conf_data:
                    st.bar_chart(conf_data)

            st.divider()

            # Latency Breakdown
            st.markdown("### ⏱️ Latency Breakdown")
            retrieval_latency = sum(s.get('latency_ms', 0) for s in retrievals)
            llm_latency = sum(c.get('latency_ms', 0) for c in llm_calls)
            baseline_latency = baseline.get('latency_ms', 0)
            other_latency = max(0, result['total_latency_ms'] - retrieval_latency - llm_latency - baseline_latency)

            latency_data = {
                "Retrieval": retrieval_latency,
                "LLM Calls": llm_latency,
                "Baseline": baseline_latency,
                "Other": other_latency
            }
            st.bar_chart(latency_data)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total", f"{result['total_latency_ms']:.0f}ms")
            with col2:
                st.metric("Retrieval %", f"{(retrieval_latency / result['total_latency_ms'] * 100):.1f}%")
            with col3:
                st.metric("LLM %", f"{(llm_latency / result['total_latency_ms'] * 100):.1f}%")

            st.divider()

            # Source Grounding
            st.markdown("### ✅ Source Grounding")
            validation = result.get('source_validation', {})
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Validated Sources", validation.get('validated_count', 0),
                         help="Fonti che esistono nel retrieval")
            with col2:
                st.metric("Hallucinated Sources", validation.get('hallucinated_count', 0),
                         help="Fonti inventate dall'LLM", delta_color="inverse")
            with col3:
                grounding_rate = validation.get('grounding_rate', 0)
                st.metric("Grounding Rate", f"{grounding_rate:.1%}",
                         help="% di fonti verificate nel database")
            with col4:
                comparison = result.get('comparison', {})
                st.metric("Baseline Grounded", "❌ No",
                         help="Baseline sources are generated without retrieval")

            # Dettaglio fonti hallucinate
            if validation.get('hallucinated'):
                with st.expander(f"⚠️ Fonti Hallucinate ({validation.get('hallucinated_count', 0)})", expanded=False):
                    for src in validation['hallucinated']:
                        st.markdown(f"- `{src.get('citation', 'N/A')}` (ID: `{src.get('source_id', 'N/A')[:30]}...`)")

            st.divider()

            # RLCF Feedback Section - Enhanced
            st.markdown("### 📝 RLCF Feedback Loop")
            st.markdown("*Valuta la qualità delle risposte per migliorare il sistema tramite Reinforcement Learning*")

            # Initialize RLCF session state
            if "feedback_submitted" not in st.session_state:
                st.session_state.feedback_submitted = {}
            if "feedback_history" not in st.session_state:
                st.session_state.feedback_history = []
            if "rlcf_stats" not in st.session_state:
                st.session_state.rlcf_stats = {
                    "total_feedbacks": 0,
                    "avg_rating_by_expert": {},
                    "weight_updates": [],
                    "authority_score": 0.5  # Default authority
                }

            # RLCF Status Panel
            rlcf_col1, rlcf_col2, rlcf_col3, rlcf_col4 = st.columns(4)
            with rlcf_col1:
                st.metric(
                    "🔄 Feedbacks (sessione)",
                    len(st.session_state.feedback_history),
                    help="Numero di feedback inviati in questa sessione"
                )
            with rlcf_col2:
                avg_all = sum(f.get("user_rating", 0) for f in st.session_state.feedback_history) / max(len(st.session_state.feedback_history), 1)
                st.metric(
                    "⭐ Rating Medio",
                    f"{avg_all:.2f}",
                    help="Rating medio di tutti i feedback"
                )
            with rlcf_col3:
                st.metric(
                    "🏆 Authority Score",
                    f"{st.session_state.rlcf_stats.get('authority_score', 0.5):.2f}",
                    help="Il tuo punteggio di authority (più alto = più influenza sui pesi)"
                )
            with rlcf_col4:
                weight_updates = len(st.session_state.rlcf_stats.get('weight_updates', []))
                st.metric(
                    "⚖️ Weight Updates",
                    weight_updates,
                    help="Numero di aggiornamenti pesi basati sui tuoi feedback"
                )

            st.divider()

            # Batch Feedback Form
            st.markdown("#### 📊 Valuta tutti gli Expert")

            expert_results = result.get('expert_results', {})
            if expert_results:
                # Create a form for batch feedback
                with st.form(key="batch_feedback_form"):
                    feedback_data = {}

                    for expert_name, expert_res in expert_results.items():
                        feedback_key = f"{result.get('trace_id', 'unknown')}_{expert_name}"
                        already_submitted = feedback_key in st.session_state.feedback_submitted

                        col1, col2, col3, col4 = st.columns([1.5, 2, 1, 1])

                        with col1:
                            expert_icon = {"literal": "📖", "systemic": "🔗", "principles": "⚖️", "precedent": "🏛️"}.get(expert_name, "🧠")
                            if already_submitted:
                                st.markdown(f"{expert_icon} **{expert_name.upper()}** ✅")
                            else:
                                st.markdown(f"{expert_icon} **{expert_name.upper()}**")

                        with col2:
                            if already_submitted:
                                st.markdown(f"Rating: `{st.session_state.feedback_submitted[feedback_key]:.1f}`")
                            else:
                                rating = st.slider(
                                    f"Rating",
                                    min_value=0.0,
                                    max_value=1.0,
                                    value=float(expert_res.get('confidence', 0.5)),  # Default to expert confidence
                                    step=0.1,
                                    key=f"batch_rating_{expert_name}",
                                    label_visibility="collapsed"
                                )
                                feedback_data[expert_name] = rating

                        with col3:
                            st.markdown(f"Conf: `{expert_res.get('confidence', 0):.2f}`")

                        with col4:
                            st.markdown(f"Fonti: `{len(expert_res.get('sources', []))}`")

                    st.divider()

                    # Feedback options
                    col1, col2 = st.columns(2)
                    with col1:
                        feedback_type = st.selectbox(
                            "Tipo di Feedback",
                            ["accuracy", "utility", "transparency", "completeness"],
                            help="accuracy = correttezza, utility = utilità, transparency = chiarezza fonti, completeness = completezza"
                        )
                    with col2:
                        feedback_comment = st.text_input(
                            "Commento (opzionale)",
                            placeholder="es. Manca riferimento a art. 1218 c.c."
                        )

                    # Submit batch feedback
                    submitted = st.form_submit_button("📤 Invia Tutti i Feedback", use_container_width=True)

                    if submitted and feedback_data:
                        for expert_name, rating in feedback_data.items():
                            feedback_key = f"{result.get('trace_id', 'unknown')}_{expert_name}"
                            expert_res = expert_results.get(expert_name, {})

                            # Create feedback record
                            feedback_record = {
                                "trace_id": result.get('trace_id', 'unknown'),
                                "expert_type": expert_name,
                                "user_rating": rating,
                                "feedback_type": feedback_type,
                                "comment": feedback_comment,
                                "response_confidence": expert_res.get('confidence', 0),
                                "sources_used": len(expert_res.get('sources', [])),
                                "model_used": result.get('token_stats', {}).get('model_used', 'unknown'),
                                "timestamp": datetime.now().isoformat(),
                                "persisted_to_db": False
                            }

                            # Simulate weight update suggestion
                            weight_delta = (rating - 0.5) * 0.1  # Small adjustment based on rating
                            feedback_record["suggested_weight_delta"] = weight_delta

                            # Store in session
                            st.session_state.feedback_submitted[feedback_key] = rating
                            st.session_state.feedback_history.append(feedback_record)

                            # Update authority (simulated - increases with more feedbacks)
                            current_authority = st.session_state.rlcf_stats.get('authority_score', 0.5)
                            new_authority = min(1.0, current_authority + 0.02)  # Slowly increase
                            st.session_state.rlcf_stats['authority_score'] = new_authority

                            # Track weight updates
                            st.session_state.rlcf_stats['weight_updates'].append({
                                "expert": expert_name,
                                "delta": weight_delta,
                                "timestamp": datetime.now().isoformat()
                            })

                        st.success(f"✅ {len(feedback_data)} feedback registrati! Authority: {st.session_state.rlcf_stats['authority_score']:.2f}")
                        st.rerun()

                # Feedback History & Analytics
                st.divider()
                st.markdown("#### 📈 Feedback Analytics")

                if st.session_state.feedback_history:
                    # Calculate stats
                    fb_by_expert = defaultdict(list)
                    for fb in st.session_state.feedback_history:
                        fb_by_expert[fb['expert_type']].append(fb['user_rating'])

                    # Show charts
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**Rating medio per Expert:**")
                        avg_by_expert = {exp: sum(ratings)/len(ratings) for exp, ratings in fb_by_expert.items()}
                        if avg_by_expert:
                            st.bar_chart(avg_by_expert)

                    with col2:
                        st.markdown("**Weight Updates suggeriti:**")
                        weight_updates = st.session_state.rlcf_stats.get('weight_updates', [])
                        if weight_updates:
                            deltas_by_expert = defaultdict(float)
                            for wu in weight_updates:
                                deltas_by_expert[wu['expert']] += wu['delta']
                            st.bar_chart(dict(deltas_by_expert))
                        else:
                            st.info("Nessun weight update ancora")

                    # Detailed history
                    with st.expander("📋 Cronologia Feedback Completa", expanded=False):
                        for i, fb in enumerate(reversed(st.session_state.feedback_history[-10:]), 1):
                            st.markdown(f"""
                            **{i}. {fb['expert_type'].upper()}** - Rating: `{fb['user_rating']:.1f}` ({fb['feedback_type']})
                            - Trace: `{fb['trace_id']}`
                            - Confidence originale: `{fb['response_confidence']:.2f}`
                            - Weight delta suggerito: `{fb.get('suggested_weight_delta', 0):+.3f}`
                            """)

                    # Export feedback
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            "📥 Esporta Feedback (JSON)",
                            data=json.dumps(st.session_state.feedback_history, indent=2, ensure_ascii=False),
                            file_name=f"rlcf_feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                    with col2:
                        if st.button("🗑️ Reset Feedback History", use_container_width=True):
                            st.session_state.feedback_history = []
                            st.session_state.feedback_submitted = {}
                            st.session_state.rlcf_stats = {
                                "total_feedbacks": 0,
                                "avg_rating_by_expert": {},
                                "weight_updates": [],
                                "authority_score": 0.5
                            }
                            st.rerun()
                else:
                    st.info("📭 Nessun feedback ancora. Valuta gli expert sopra per iniziare il loop RLCF!")

            else:
                st.info("Nessun risultato expert disponibile per il feedback")

        with tab_config:
            st.subheader("⚙️ Configuration Snapshot")
            st.markdown("*Configurazione usata per questa run - per version tracking*")

            config_snapshot = result.get('config_snapshot', {})

            if config_snapshot:
                # Config summary
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Config Hash", config_snapshot.get('config_hash', 'N/A')[:8] + "...")
                with col2:
                    st.metric("Trace ID", config_snapshot.get('trace_id', 'N/A'))
                with col3:
                    timestamp = config_snapshot.get('timestamp', '')[:19]
                    st.metric("Timestamp", timestamp)

                st.divider()

                # Show configurations by file
                configs = config_snapshot.get('configs', {})
                overrides = config_snapshot.get('overrides', {})

                tabs_cfg = st.tabs(["Retriever", "Experts", "Weights", "Overrides", "Raw JSON"])

                with tabs_cfg[0]:
                    st.markdown("### `retriever_weights.yaml`")
                    retriever_cfg = configs.get('retriever', {})
                    if retriever_cfg:
                        # Show key params
                        retrieval = retriever_cfg.get('retrieval', {})
                        st.markdown(f"**Alpha**: `{retrieval.get('alpha', 'N/A')}`")
                        st.markdown(f"**Over-retrieve factor**: `{retrieval.get('over_retrieve_factor', 'N/A')}`")
                        st.markdown(f"**Max graph hops**: `{retrieval.get('max_graph_hops', 'N/A')}`")

                        with st.expander("Full Config"):
                            st.json(retriever_cfg)
                    else:
                        st.info("No retriever config")

                with tabs_cfg[1]:
                    st.markdown("### `experts.yaml`")
                    experts_cfg = configs.get('experts', {})
                    if experts_cfg:
                        # Show expert settings
                        defaults = experts_cfg.get('defaults', {})
                        st.markdown(f"**Default Model**: `{defaults.get('model', 'N/A')}`")
                        st.markdown(f"**Default Temperature**: `{defaults.get('temperature', 'N/A')}`")

                        experts = experts_cfg.get('experts', {})
                        for exp_name, exp_cfg in experts.items():
                            with st.expander(f"{exp_name.upper()}"):
                                st.markdown(f"- Model: `{exp_cfg.get('model', 'default')}`")
                                st.markdown(f"- Temperature: `{exp_cfg.get('temperature', 'default')}`")
                                st.markdown("- Traversal weights:")
                                weights = exp_cfg.get('traversal_weights', {})
                                for w_name, w_val in list(weights.items())[:5]:
                                    st.caption(f"  `{w_name}`: {w_val}")
                    else:
                        st.info("No experts config")

                with tabs_cfg[2]:
                    st.markdown("### `weights.yaml`")
                    weights_cfg = configs.get('weights', {})
                    if weights_cfg:
                        st.markdown(f"**Version**: `{weights_cfg.get('version', 'N/A')}`")
                        st.markdown(f"**Last Updated**: `{weights_cfg.get('last_updated', 'N/A')}`")

                        with st.expander("Retrieval Weights"):
                            st.json(weights_cfg.get('retrieval', {}))

                        with st.expander("Expert Traversal Weights"):
                            st.json(weights_cfg.get('expert_traversal', {}))

                        with st.expander("Gating Weights"):
                            st.json(weights_cfg.get('gating', {}))
                    else:
                        st.info("No weights config")

                with tabs_cfg[3]:
                    st.markdown("### Runtime Overrides")
                    if overrides:
                        st.warning("Questa run ha usato override runtime!")
                        st.json(overrides)
                    else:
                        st.success("Nessun override - configurazione da file")

                with tabs_cfg[4]:
                    st.markdown("### Full Snapshot JSON")
                    st.json(config_snapshot)
            else:
                st.info("Nessun config snapshot disponibile per questa run")

        with tab_trace:
            st.subheader("📜 Full Trace Visualization")
            st.markdown("*Visualizzazione completa di tutti i dati della run*")

            # Trace Overview
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Trace ID", result.get('trace_id', 'N/A'))
            with col2:
                st.metric("Total Steps", len(result.get('retrieval_steps', [])) + len(result.get('llm_calls', [])))
            with col3:
                st.metric("Tool Calls", len(result.get('tool_calls', [])))
            with col4:
                st.metric("LLM Calls", len(result.get('llm_calls', [])))

            st.divider()

            # Token Statistics Breakdown
            st.markdown("### 🔤 Token Statistics")
            token_stats = result.get('token_stats', {})
            if token_stats:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Token Distribution by Expert:**")
                    tokens_by_expert = token_stats.get('tokens_by_expert', {})
                    if tokens_by_expert:
                        st.bar_chart(tokens_by_expert)
                with col2:
                    st.markdown("**Token Breakdown:**")
                    st.markdown(f"- **Total Tokens:** {token_stats.get('total_tokens', 0):,}")
                    for exp, toks in tokens_by_expert.items():
                        st.markdown(f"- **{exp}:** {toks:,}")
                    st.markdown(f"- **Aggregation:** {token_stats.get('aggregation_tokens', 0):,}")
                    st.markdown(f"- **Estimated Cost:** ${token_stats.get('estimated_cost_usd', 0):.6f}")
                    st.markdown(f"- **Model:** `{token_stats.get('model_used', 'N/A')}`")

            st.divider()

            # Timeline View
            st.markdown("### ⏱️ Execution Timeline")
            timeline_data = []

            # Add retrieval steps to timeline
            for i, step in enumerate(result.get('retrieval_steps', [])):
                timeline_data.append({
                    "Step": i + 1,
                    "Type": "Retrieval",
                    "Expert": step.get('expert', 'N/A'),
                    "Details": step.get('query', '')[:50] + "...",
                    "Results": len(step.get('results', [])),
                    "Latency (ms)": step.get('latency_ms', 0)
                })

            # Add LLM calls to timeline
            for i, call in enumerate(result.get('llm_calls', [])):
                timeline_data.append({
                    "Step": len(result.get('retrieval_steps', [])) + i + 1,
                    "Type": "LLM Call",
                    "Expert": call.get('expert', 'N/A'),
                    "Details": f"Tokens: {call.get('tokens', 0)}",
                    "Results": call.get('tokens', 0),
                    "Latency (ms)": call.get('latency_ms', 0)
                })

            if timeline_data:
                import pandas as pd
                df = pd.DataFrame(timeline_data)
                st.dataframe(df, use_container_width=True)

            st.divider()

            # Raw Data Sections
            st.markdown("### 📊 Raw Data")

            raw_tabs = st.tabs(["Run Parameters", "Routing", "Retrieval", "LLM Calls", "Tool Calls", "Expert Results", "Full JSON"])

            with raw_tabs[0]:
                st.markdown("**Run Parameters:**")
                st.json(result.get('run_parameters', {}))

            with raw_tabs[1]:
                st.markdown("**Routing Decision:**")
                st.json(result.get('routing', {}))

            with raw_tabs[2]:
                st.markdown(f"**Retrieval Steps ({len(result.get('retrieval_steps', []))}):**")
                for i, step in enumerate(result.get('retrieval_steps', [])):
                    with st.expander(f"Step {i+1}: {step.get('expert', 'N/A')}", expanded=False):
                        st.json(step)

            with raw_tabs[3]:
                st.markdown(f"**LLM Calls ({len(result.get('llm_calls', []))}):**")
                for i, call in enumerate(result.get('llm_calls', [])):
                    with st.expander(f"Call {i+1}: {call.get('expert', 'N/A')} ({call.get('tokens', 0)} tokens)", expanded=False):
                        st.json(call)

            with raw_tabs[4]:
                st.markdown(f"**Tool Calls ({len(result.get('tool_calls', []))}):**")
                for i, tc in enumerate(result.get('tool_calls', [])):
                    with st.expander(f"Tool {i+1}: {tc.get('tool', 'N/A')} by {tc.get('expert', 'N/A')}", expanded=False):
                        st.json(tc)

            with raw_tabs[5]:
                st.markdown("**Expert Results:**")
                st.json(result.get('expert_results', {}))

            with raw_tabs[6]:
                st.markdown("**Complete Result JSON:**")
                st.json(result)

        st.divider()

        # Enhanced Export Section
        st.markdown("### 📥 Export Options")
        col1, col2, col3, col4 = st.columns(4)

        trace_id = result.get('trace_id', datetime.now().strftime('%Y%m%d_%H%M%S'))

        with col1:
            st.download_button(
                "📄 Full Trace (JSON)",
                data=json.dumps(result, indent=2, ensure_ascii=False, default=str),
                file_name=f"trace_{trace_id}.json",
                mime="application/json",
                use_container_width=True
            )

        with col2:
            # Export only expert results
            expert_export = {
                "trace_id": result.get('trace_id'),
                "query": result.get('query'),
                "expert_results": result.get('expert_results'),
                "final_synthesis": result.get('final_synthesis'),
                "final_confidence": result.get('final_confidence')
            }
            st.download_button(
                "🧠 Expert Results",
                data=json.dumps(expert_export, indent=2, ensure_ascii=False, default=str),
                file_name=f"experts_{trace_id}.json",
                mime="application/json",
                use_container_width=True
            )

        with col3:
            # Export run parameters and stats
            stats_export = {
                "trace_id": result.get('trace_id'),
                "run_parameters": result.get('run_parameters'),
                "token_stats": result.get('token_stats'),
                "routing": result.get('routing'),
                "source_validation": result.get('source_validation'),
                "total_latency_ms": result.get('total_latency_ms')
            }
            st.download_button(
                "📊 Statistics",
                data=json.dumps(stats_export, indent=2, ensure_ascii=False, default=str),
                file_name=f"stats_{trace_id}.json",
                mime="application/json",
                use_container_width=True
            )

        with col4:
            # Export LLM calls for prompt analysis
            llm_export = {
                "trace_id": result.get('trace_id'),
                "model": result.get('token_stats', {}).get('model_used'),
                "llm_calls": result.get('llm_calls'),
                "aggregation": result.get('aggregation')
            }
            st.download_button(
                "🤖 LLM Calls",
                data=json.dumps(llm_export, indent=2, ensure_ascii=False, default=str),
                file_name=f"llm_calls_{trace_id}.json",
                mime="application/json",
                use_container_width=True
            )


if __name__ == "__main__":
    main()
