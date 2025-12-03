"""
KG Agent - Knowledge Graph Retrieval Agent
==========================================

Executes graph queries on Neo4j to retrieve:
- Related legal concepts
- Hierarchical norm structure
- Jurisprudence (sentenze)
- Temporal norm evolution (multivigenza)

Reuses existing Neo4j connection from kg_enrichment_service.

Usage:
    from backend.orchestration.agents.kg_agent import KGAgent
    from backend.preprocessing.neo4j_connection import Neo4jConnectionManager

    # Initialize
    driver = await Neo4jConnectionManager.get_driver()
    agent = KGAgent(neo4j_driver=driver)

    # Execute tasks
    tasks = [
        AgentTask(
            task_type="expand_related_concepts",
            params={"concept": "contratto", "max_depth": 2}
        )
    ]

    result = await agent.execute(tasks)
"""

import logging
from typing import List, Dict, Any, Optional

from neo4j import AsyncDriver

from .base import RetrievalAgent, AgentTask, AgentResult
from backend.preprocessing.neo4j_connection import Neo4jConnectionManager


logger = logging.getLogger(__name__)


# ==============================================
# KG Agent
# ==============================================

class KGAgent(RetrievalAgent):
    """
    Knowledge Graph Agent for Neo4j queries.

    Supported task types:
    - expand_related_concepts: Find concepts related to a legal concept
    - hierarchical_traversal: Navigate norm hierarchy (codice → libro → titolo → articolo)
    - jurisprudence_lookup: Find sentenze that cite specific norms
    - temporal_evolution: Find all versions of a norm over time (multivigenza)
    """

    # Supported task types
    SUPPORTED_TASKS = [
        "expand_related_concepts",
        "hierarchical_traversal",
        "jurisprudence_lookup",
        "temporal_evolution"
    ]

    def __init__(
        self,
        neo4j_driver: Optional[AsyncDriver] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize KG Agent.

        Args:
            neo4j_driver: Neo4j async driver. If None, gets from Neo4jConnectionManager.
            config: Configuration dict (e.g., max_results, timeout)
        """
        super().__init__(agent_name="kg_agent", config=config)

        self.neo4j_driver = neo4j_driver
        self.max_results = config.get("max_results", 50) if config else 50
        self.timeout_ms = config.get("cypher_timeout_ms", 3000) if config else 3000

        logger.info(f"KGAgent initialized (max_results={self.max_results})")

    async def execute(self, tasks: List[AgentTask]) -> AgentResult:
        """
        Execute KG retrieval tasks.

        Args:
            tasks: List of graph query tasks

        Returns:
            AgentResult with graph data
        """
        import time
        start_time = time.time()

        # Validate tasks
        valid_tasks = self._validate_tasks(tasks, self.SUPPORTED_TASKS)

        if not valid_tasks:
            return AgentResult(
                agent_name=self.agent_name,
                success=True,
                data=[],
                tasks_executed=len(tasks),
                tasks_successful=0,
                source="neo4j"
            )

        # Get Neo4j driver
        if self.neo4j_driver is None:
            try:
                self.neo4j_driver = await Neo4jConnectionManager.get_driver()
            except Exception as e:
                return self._create_error_result(
                    f"Failed to get Neo4j driver: {str(e)}",
                    len(tasks)
                )

        # Execute tasks
        all_data = []
        errors = []
        successful_count = 0

        for task in valid_tasks:
            try:
                data = await self._execute_task(task)
                all_data.extend(data)
                successful_count += 1

            except Exception as e:
                error_msg = f"Task {task.task_type} failed: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        # Calculate execution time
        execution_time_ms = (time.time() - start_time) * 1000

        return AgentResult(
            agent_name=self.agent_name,
            success=len(errors) == 0,
            data=all_data,
            errors=errors,
            execution_time_ms=execution_time_ms,
            tasks_executed=len(valid_tasks),
            tasks_successful=successful_count,
            source="neo4j"
        )

    async def _execute_task(self, task: AgentTask) -> List[Dict[str, Any]]:
        """
        Execute a single graph query task.

        Args:
            task: AgentTask with task_type and params

        Returns:
            List of result dicts from Neo4j
        """
        if task.task_type == "expand_related_concepts":
            return await self._expand_related_concepts(task.params)

        elif task.task_type == "hierarchical_traversal":
            return await self._hierarchical_traversal(task.params)

        elif task.task_type == "jurisprudence_lookup":
            return await self._jurisprudence_lookup(task.params)

        elif task.task_type == "temporal_evolution":
            return await self._temporal_evolution(task.params)

        else:
            raise ValueError(f"Unsupported task type: {task.task_type}")

    # ==============================================
    # Task Implementations
    # ==============================================

    async def _expand_related_concepts(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find concepts related to a legal concept.

        Params:
            concept (str): Legal concept name (e.g., "contratto")
            max_depth (int): Max relationship hops (default: 2)
            relationship_types (List[str]): Filter by relationship types (optional)

        Returns:
            List of related concepts with relationships
        """
        concept = params.get("concept")
        max_depth = params.get("max_depth", 2)

        if not concept:
            raise ValueError("'concept' parameter required")

        cypher = f"""
        MATCH path = (c:ConceptoGiuridico {{nome: $concept}})-[r*1..{max_depth}]-(related)
        WHERE related:ConceptoGiuridico OR related:Norma
        RETURN
            related.nome AS nome,
            labels(related) AS tipo,
            type(relationships(path)[0]) AS relazione,
            length(path) AS distanza
        LIMIT $max_results
        """

        async with self.neo4j_driver.session() as session:
            result = await session.run(
                cypher,
                concept=concept,
                max_results=self.max_results
            )

            records = [
                {
                    "nome": record["nome"],
                    "tipo": record["tipo"][0] if record["tipo"] else "unknown",
                    "relazione": record["relazione"],
                    "distanza": record["distanza"]
                }
                async for record in result
            ]

        return records

    async def _hierarchical_traversal(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Navigate norm hierarchy.

        Params:
            norm_id (str): Starting norm ID (e.g., "Art. 1321 c.c.")
            direction (str): "up" (to codice) or "down" (to articoli) (default: "both")

        Returns:
            List of norms in hierarchy
        """
        norm_id = params.get("norm_id")
        direction = params.get("direction", "both")

        if not norm_id:
            raise ValueError("'norm_id' parameter required")

        if direction == "up":
            # Navigate up: Articolo → Titolo → Libro → Codice
            cypher = """
            MATCH path = (n:Norma {estremi: $norm_id})-[:PARTE_DI*]->(parent)
            RETURN
                parent.estremi AS estremi,
                parent.tipo AS tipo,
                parent.testo AS testo,
                length(path) AS livello
            ORDER BY livello ASC
            LIMIT $max_results
            """

        elif direction == "down":
            # Navigate down: Codice → Libro → Titolo → Articolo
            cypher = """
            MATCH path = (n:Norma {estremi: $norm_id})<-[:PARTE_DI*]-(child)
            RETURN
                child.estremi AS estremi,
                child.tipo AS tipo,
                child.testo AS testo,
                length(path) AS livello
            ORDER BY livello ASC
            LIMIT $max_results
            """

        else:  # both
            cypher = """
            MATCH path = (n:Norma {estremi: $norm_id})-[:PARTE_DI*]-(related)
            RETURN
                related.estremi AS estremi,
                related.tipo AS tipo,
                related.testo AS testo,
                length(path) AS livello
            ORDER BY livello ASC
            LIMIT $max_results
            """

        async with self.neo4j_driver.session() as session:
            result = await session.run(
                cypher,
                norm_id=norm_id,
                max_results=self.max_results
            )

            records = [
                {
                    "estremi": record["estremi"],
                    "tipo": record["tipo"],
                    "testo": record["testo"][:200] if record["testo"] else "",  # Truncate
                    "livello": record["livello"]
                }
                async for record in result
            ]

        return records

    async def _jurisprudence_lookup(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find sentenze that cite specific norms.

        Params:
            norm (str): Norm ID (e.g., "Art. 1321 c.c.")
            corte (str): Court filter (optional, e.g., "Cassazione")
            min_year (int): Minimum year filter (optional)

        Returns:
            List of sentenze with citation info
        """
        norm = params.get("norm")
        corte = params.get("corte")
        min_year = params.get("min_year")

        if not norm:
            raise ValueError("'norm' parameter required")

        # Build query with optional filters
        filters = []
        if corte:
            filters.append("s.corte = $corte")
        if min_year:
            filters.append("s.anno >= $min_year")

        where_clause = " AND ".join(filters) if filters else "1=1"

        cypher = f"""
        MATCH (n:Norma {{estremi: $norm}})<-[:CITA]-(s:Sentenza)
        WHERE {where_clause}
        RETURN
            s.numero AS numero,
            s.anno AS anno,
            s.corte AS corte,
            s.massima AS massima,
            s.fonte AS fonte
        ORDER BY s.anno DESC, s.numero DESC
        LIMIT $max_results
        """

        query_params = {
            "norm": norm,
            "max_results": self.max_results
        }
        if corte:
            query_params["corte"] = corte
        if min_year:
            query_params["min_year"] = min_year

        async with self.neo4j_driver.session() as session:
            result = await session.run(cypher, **query_params)

            records = [
                {
                    "numero": record["numero"],
                    "anno": record["anno"],
                    "corte": record["corte"],
                    "massima": record["massima"][:300] if record["massima"] else "",
                    "fonte": record["fonte"]
                }
                async for record in result
            ]

        return records

    async def _temporal_evolution(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find all versions of a norm over time (multivigenza).

        Params:
            norm (str): Norm ID (e.g., "Art. 1321 c.c.")

        Returns:
            List of norm versions with vigenza dates
        """
        norm = params.get("norm")

        if not norm:
            raise ValueError("'norm' parameter required")

        cypher = """
        MATCH (n:Norma)
        WHERE n.estremi_base = $norm_base OR n.estremi = $norm
        RETURN
            n.estremi AS estremi,
            n.testo AS testo,
            n.vigenza_inizio AS vigenza_inizio,
            n.vigenza_fine AS vigenza_fine,
            n.fonte AS fonte,
            n.modificata_da AS modificata_da
        ORDER BY n.vigenza_inizio DESC
        LIMIT $max_results
        """

        # Extract base norm (e.g., "Art. 1321 c.c." from "Art. 1321 c.c. (versione 2020)")
        norm_base = norm.split("(")[0].strip()

        async with self.neo4j_driver.session() as session:
            result = await session.run(
                cypher,
                norm=norm,
                norm_base=norm_base,
                max_results=self.max_results
            )

            records = [
                {
                    "estremi": record["estremi"],
                    "testo": record["testo"][:200] if record["testo"] else "",
                    "vigenza_inizio": record["vigenza_inizio"],
                    "vigenza_fine": record["vigenza_fine"],
                    "fonte": record["fonte"],
                    "modificata_da": record["modificata_da"]
                }
                async for record in result
            ]

        return records


# ==============================================
# Exports
# ==============================================

__all__ = ["KGAgent"]
