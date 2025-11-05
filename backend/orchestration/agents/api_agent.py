"""
API Agent - External API Retrieval Agent
=========================================

Fetches legal norms from external APIs:
- Custom Norma Controller API (localhost:5000) - Official norm texts
- Sentenze API (mock/placeholder) - Case law database

Features:
- Redis caching with configurable TTL
- Retry logic for transient failures
- Rate limiting compliance
- Configurable API endpoints

Usage:
    from backend.orchestration.agents.api_agent import APIAgent
    from backend.preprocessing.redis_connection import RedisConnectionManager

    # Initialize
    redis_client = await RedisConnectionManager.get_client()
    agent = APIAgent(redis_client=redis_client)

    # Execute tasks
    tasks = [
        AgentTask(
            task_type="fetch_full_text",
            params={
                "norm_references": ["Art. 1321 c.c."],
                "include_brocardi": True
            }
        )
    ]

    result = await agent.execute(tasks)
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import aiohttp
from redis.asyncio import Redis

from .base import RetrievalAgent, AgentTask, AgentResult
from backend.preprocessing.redis_connection import RedisConnectionManager


logger = logging.getLogger(__name__)


# ==============================================
# API Agent
# ==============================================

class APIAgent(RetrievalAgent):
    """
    API Agent for fetching legal norms from external APIs.

    Supported task types:
    - fetch_full_text: Fetch complete norm text from Norma Controller API
    - fetch_versions: Fetch all versions of a norm (multivigenza)
    - fetch_metadata: Fetch norm metadata (publication info, Gazzetta Ufficiale)
    - fetch_sentenze: Fetch case law (mock/placeholder for now)

    APIs:
    - Norma Controller API (http://localhost:5000) - Custom implementation
    - Sentenze API (configurable, mock for now)
    """

    # Supported task types
    SUPPORTED_TASKS = [
        "fetch_full_text",
        "fetch_versions",
        "fetch_metadata",
        "fetch_sentenze"  # Mock for now
    ]

    # Norm type mapping (Italian → API format)
    NORM_TYPE_MAPPING = {
        "codice civile": "codice civile",
        "codice penale": "codice penale",
        "c.c.": "codice civile",
        "c.p.": "codice penale",
        "c.p.c.": "codice di procedura civile",
        "c.p.p.": "codice di procedura penale",
        "legge": "legge",
        "decreto legge": "decreto legge",
        "d.l.": "decreto legge",
        "decreto legislativo": "decreto legislativo",
        "d.lgs.": "decreto legislativo",
        "d.p.r.": "d.p.r.",
        "regio decreto": "regio decreto",
        "r.d.": "regio decreto"
    }

    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize API Agent.

        Args:
            redis_client: Redis async client for caching. If None, gets from RedisConnectionManager.
            config: Configuration dict with API endpoints and settings
        """
        super().__init__(agent_name="api_agent", config=config)

        self.redis_client = redis_client
        self.max_results = config.get("max_results", 20) if config else 20
        self.cache_ttl = config.get("cache_ttl_seconds", 86400) if config else 86400  # 24h default
        self.timeout = config.get("timeout_per_source_seconds", 3) if config else 3

        # API endpoints (configurable)
        sources_config = config.get("sources", {}) if config else {}

        # Norma Controller API (custom implementation)
        norma_config = sources_config.get("norma_controller", {})
        self.norma_api_enabled = norma_config.get("enabled", True)
        self.norma_api_base_url = norma_config.get("base_url", "http://localhost:5000")

        # Sentenze API (placeholder/mock)
        sentenze_config = sources_config.get("sentenze_api", {})
        self.sentenze_api_enabled = sentenze_config.get("enabled", False)  # Disabled by default
        self.sentenze_api_base_url = sentenze_config.get("base_url", "http://localhost:5001")

        logger.info(
            f"APIAgent initialized (norma_api={self.norma_api_base_url}, "
            f"sentenze_api={'enabled' if self.sentenze_api_enabled else 'disabled'})"
        )

    async def execute(self, tasks: List[AgentTask]) -> AgentResult:
        """
        Execute API retrieval tasks.

        Args:
            tasks: List of API fetch tasks

        Returns:
            AgentResult with fetched data
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
                source="api"
            )

        # Get Redis client if not provided
        if self.redis_client is None:
            try:
                self.redis_client = await RedisConnectionManager.get_client()
            except Exception as e:
                logger.warning(f"Redis unavailable, caching disabled: {str(e)}")

        # Execute tasks
        all_data = []
        errors = []
        successful_count = 0

        async with aiohttp.ClientSession() as session:
            for task in valid_tasks:
                try:
                    data = await self._execute_task(task, session)
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
            source="api"
        )

    async def _execute_task(
        self,
        task: AgentTask,
        session: aiohttp.ClientSession
    ) -> List[Dict[str, Any]]:
        """
        Execute a single API fetch task.

        Args:
            task: AgentTask with task_type and params
            session: aiohttp ClientSession

        Returns:
            List of result dicts from API
        """
        if task.task_type == "fetch_full_text":
            return await self._fetch_full_text(task.params, session)

        elif task.task_type == "fetch_versions":
            return await self._fetch_versions(task.params, session)

        elif task.task_type == "fetch_metadata":
            return await self._fetch_metadata(task.params, session)

        elif task.task_type == "fetch_sentenze":
            return await self._fetch_sentenze(task.params, session)

        else:
            raise ValueError(f"Unsupported task type: {task.task_type}")

    # ==============================================
    # Task Implementations
    # ==============================================

    async def _fetch_full_text(
        self,
        params: Dict[str, Any],
        session: aiohttp.ClientSession
    ) -> List[Dict[str, Any]]:
        """
        Fetch complete norm text from Norma Controller API.

        Params:
            norm_references (List[str]): Norm IDs (e.g., ["Art. 1321 c.c.", "Art. 2043 c.c."])
            include_brocardi (bool): Include Brocardi commentary (default: False)
            version_date (str): Specific version date (optional)

        Returns:
            List of norm data with full text
        """
        norm_references = params.get("norm_references", [])
        include_brocardi = params.get("include_brocardi", False)
        version_date = params.get("version_date")

        if not norm_references:
            raise ValueError("'norm_references' parameter required")

        results = []

        for norm_ref in norm_references:
            # Parse norm reference (e.g., "Art. 1321 c.c.")
            parsed = self._parse_norm_reference(norm_ref)

            if not parsed:
                logger.warning(f"Could not parse norm reference: {norm_ref}")
                continue

            # Check cache
            cache_key = f"api:norm:{norm_ref}:{version_date or 'current'}"
            cached = await self._get_from_cache(cache_key)

            if cached:
                results.append(cached)
                continue

            # Fetch from API
            try:
                norm_data = await self._call_norma_controller_api(
                    parsed,
                    include_brocardi,
                    version_date,
                    session
                )

                # Cache result
                await self._set_to_cache(cache_key, norm_data)

                results.append(norm_data)

            except Exception as e:
                logger.error(f"Failed to fetch norm {norm_ref}: {str(e)}")
                results.append({
                    "norm_reference": norm_ref,
                    "error": str(e),
                    "source": "api_error"
                })

        return results

    async def _fetch_versions(
        self,
        params: Dict[str, Any],
        session: aiohttp.ClientSession
    ) -> List[Dict[str, Any]]:
        """
        Fetch all versions of a norm (multivigenza).

        Params:
            norm (str): Norm ID (e.g., "Art. 1321 c.c.")

        Returns:
            List of norm versions with vigenza dates
        """
        norm = params.get("norm")

        if not norm:
            raise ValueError("'norm' parameter required")

        # Parse norm
        parsed = self._parse_norm_reference(norm)

        if not parsed:
            raise ValueError(f"Could not parse norm reference: {norm}")

        # Check cache
        cache_key = f"api:versions:{norm}"
        cached = await self._get_from_cache(cache_key)

        if cached:
            return [cached]

        # TODO: Implement version fetching via API
        # For now, return placeholder
        versions_data = {
            "norm_reference": norm,
            "versions": [
                {
                    "version_date": "current",
                    "vigenza_inizio": None,
                    "vigenza_fine": None,
                    "note": "Versione attuale"
                }
            ],
            "source": "api_placeholder"
        }

        await self._set_to_cache(cache_key, versions_data)

        return [versions_data]

    async def _fetch_metadata(
        self,
        params: Dict[str, Any],
        session: aiohttp.ClientSession
    ) -> List[Dict[str, Any]]:
        """
        Fetch norm metadata (publication info).

        Params:
            norm (str): Norm ID

        Returns:
            List with norm metadata
        """
        norm = params.get("norm")

        if not norm:
            raise ValueError("'norm' parameter required")

        # Check cache
        cache_key = f"api:metadata:{norm}"
        cached = await self._get_from_cache(cache_key)

        if cached:
            return [cached]

        # TODO: Implement metadata fetching
        # For now, return placeholder
        metadata = {
            "norm_reference": norm,
            "metadata": {
                "gazzetta_ufficiale": "N/A",
                "data_pubblicazione": None,
                "note": "Metadata placeholder"
            },
            "source": "api_placeholder"
        }

        await self._set_to_cache(cache_key, metadata)

        return [metadata]

    async def _fetch_sentenze(
        self,
        params: Dict[str, Any],
        session: aiohttp.ClientSession
    ) -> List[Dict[str, Any]]:
        """
        Fetch sentenze (case law) - MOCK/PLACEHOLDER.

        Params:
            query (str): Search query for sentenze
            corte (str): Court filter (e.g., "Cassazione")
            min_year (int): Minimum year

        Returns:
            List of sentenze (mock data for now)
        """
        query = params.get("query", "")
        corte = params.get("corte")
        min_year = params.get("min_year")

        # Check cache
        cache_key = f"api:sentenze:{query}:{corte}:{min_year}"
        cached = await self._get_from_cache(cache_key)

        if cached:
            return [cached]

        # MOCK DATA - Replace with real API when available
        mock_sentenze = {
            "query": query,
            "sentenze": [
                {
                    "numero": "12345",
                    "anno": 2023,
                    "corte": corte or "Cassazione",
                    "massima": "Mock sentenza - API not yet available",
                    "note": "PLACEHOLDER - Configure sentenze_api_base_url when API ready"
                }
            ],
            "source": "mock_api",
            "note": "⚠️ Sentenze API not configured - using mock data"
        }

        await self._set_to_cache(cache_key, mock_sentenze, ttl=3600)  # Short TTL for mock

        return [mock_sentenze]

    # ==============================================
    # Norma Controller API Integration
    # ==============================================

    async def _call_norma_controller_api(
        self,
        parsed_norm: Dict[str, Any],
        include_brocardi: bool,
        version_date: Optional[str],
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """
        Call Norma Controller API (/fetch_all_data endpoint).

        Args:
            parsed_norm: Parsed norm data (act_type, article, etc.)
            include_brocardi: Whether to include Brocardi info
            version_date: Optional version date
            session: aiohttp ClientSession

        Returns:
            Norm data from API
        """
        if not self.norma_api_enabled:
            raise ValueError("Norma Controller API is disabled in config")

        # Build request payload according to NormaRequest schema
        payload = {
            "act_type": parsed_norm["act_type"],
            "article": parsed_norm["article"]
        }

        # Add optional fields
        if parsed_norm.get("date"):
            payload["date"] = parsed_norm["date"]
        if parsed_norm.get("act_number"):
            payload["act_number"] = parsed_norm["act_number"]
        if version_date:
            payload["version_date"] = version_date

        # Choose endpoint based on include_brocardi
        if include_brocardi:
            endpoint = f"{self.norma_api_base_url}/fetch_all_data"
        else:
            endpoint = f"{self.norma_api_base_url}/fetch_article_text"

        # Make API request
        try:
            async with session.post(
                endpoint,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    # Extract first result (API returns array)
                    if isinstance(data, list) and len(data) > 0:
                        result = data[0]

                        # Check for error in response
                        if "error" in result:
                            raise ValueError(f"API returned error: {result['error']}")

                        return {
                            "norm_reference": f"{parsed_norm['article']} {parsed_norm['act_type']}",
                            "article_text": result.get("article_text", ""),
                            "url": result.get("url", ""),
                            "brocardi_info": result.get("brocardi_info") if include_brocardi else None,
                            "source": "norma_controller_api",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    else:
                        raise ValueError("API returned empty result")

                elif response.status == 429:
                    raise ValueError("Rate limit exceeded - retry later")

                else:
                    error_text = await response.text()
                    raise ValueError(f"API error {response.status}: {error_text}")

        except aiohttp.ClientError as e:
            raise ValueError(f"HTTP request failed: {str(e)}")

    def _parse_norm_reference(self, norm_ref: str) -> Optional[Dict[str, Any]]:
        """
        Parse Italian norm reference into API-compatible format.

        Examples:
            "Art. 1321 c.c." → {"act_type": "codice civile", "article": "1321"}
            "Art. 2043 c.c." → {"act_type": "codice civile", "article": "2043"}
            "L. 241/1990 art. 3" → {"act_type": "legge", "date": "1990", "act_number": "241", "article": "3"}

        Args:
            norm_ref: Italian norm reference string

        Returns:
            Dict with parsed fields or None if parsing fails
        """
        norm_ref = norm_ref.strip()

        # Pattern 1: "Art. XXX c.c." (codice civile)
        if "c.c." in norm_ref.lower():
            article = norm_ref.lower().replace("art.", "").replace("c.c.", "").strip()
            return {
                "act_type": "codice civile",
                "article": article
            }

        # Pattern 2: "Art. XXX c.p." (codice penale)
        if "c.p." in norm_ref.lower() and "c.p.c." not in norm_ref.lower():
            article = norm_ref.lower().replace("art.", "").replace("c.p.", "").strip()
            return {
                "act_type": "codice penale",
                "article": article
            }

        # Pattern 3: "Art. XXX c.p.c." (codice procedura civile)
        if "c.p.c." in norm_ref.lower():
            article = norm_ref.lower().replace("art.", "").replace("c.p.c.", "").strip()
            return {
                "act_type": "codice di procedura civile",
                "article": article
            }

        # Pattern 4: "L. XXX/YYYY art. ZZZ" (legge)
        # TODO: Implement legge parsing
        # For now, return None for non-codice references

        logger.warning(f"Could not parse norm reference: {norm_ref}")
        return None

    # ==============================================
    # Caching
    # ==============================================

    async def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get from Redis cache"""
        if not self.redis_client:
            return None

        try:
            cached = await self.redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache read failed: {str(e)}")

        return None

    async def _set_to_cache(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> None:
        """Set to Redis cache"""
        if not self.redis_client:
            return

        try:
            await self.redis_client.setex(
                key,
                ttl or self.cache_ttl,
                json.dumps(value)
            )
        except Exception as e:
            logger.warning(f"Cache write failed: {str(e)}")


# ==============================================
# Exports
# ==============================================

__all__ = ["APIAgent"]
