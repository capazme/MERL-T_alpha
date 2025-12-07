"""
MERL-T Test Configuration
=========================

Shared fixtures for all tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator

# Async test support
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Environment fixtures
@pytest.fixture
def test_config():
    """Get test environment configuration."""
    from merlt.config import get_environment_config, TEST_ENV
    return get_environment_config(TEST_ENV)


# Mock FalkorDB client for unit tests
@pytest.fixture
def mock_falkordb():
    """Mock FalkorDB client for unit tests."""
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    client.connect = AsyncMock()
    client.close = AsyncMock()
    client.query = AsyncMock(return_value=[])
    return client


# Sample data fixtures
@pytest.fixture
def sample_norma_visitata():
    """Create a sample NormaVisitata for testing."""
    from merlt.sources.utils.norma import NormaVisitata, Norma

    norma = Norma(tipo_atto="codice penale")
    return NormaVisitata(
        norma=norma,
        numero_articolo="52",
        rubrica="Difesa legittima",
        articolo_text="Non e' punibile chi ha commesso il fatto per esservi stato costretto dalla necessita' di difendere un diritto proprio od altrui...",
    )


@pytest.fixture
def sample_article_text():
    """Sample article text for testing."""
    return """
    Difesa legittima.

    Non e' punibile chi ha commesso il fatto per esservi stato costretto dalla necessita' di difendere un diritto proprio od altrui contro il pericolo attuale di un'offesa ingiusta, sempre che la difesa sia proporzionata all'offesa.

    Nei casi previsti dall'articolo 614, primo e secondo comma, sussiste sempre il rapporto di proporzione di cui al primo comma del presente articolo se taluno legittimamente presente in uno dei luoghi ivi indicati usa un'arma legittimamente detenuta o altro mezzo idoneo al fine di difendere:
    a) la propria o la altrui incolumita';
    b) i beni propri o altrui, quando non vi e' desistenza e vi e' pericolo d'aggressione.
    """
