"""
Pytest configuration and shared fixtures.
"""

import pytest
import os
import sys
import requests
from typing import Generator

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from talk_dnd_to_me.config.settings import DMConfig
from talk_dnd_to_me.core.dm_engine import DMEngine
from talk_dnd_to_me.database.chroma_client import ChromaClient
from talk_dnd_to_me.database.cache_manager import CacheManager
from talk_dnd_to_me.content.embeddings import EmbeddingManager
from talk_dnd_to_me.ai.context_retriever import ContextRetriever


@pytest.fixture(scope="session")
def dm_config() -> DMConfig:
    """Provide DM configuration for tests."""
    return DMConfig.default()


@pytest.fixture(scope="session")
def chroma_client(dm_config: DMConfig) -> Generator[ChromaClient, None, None]:
    """Provide initialized ChromaDB client."""
    client = ChromaClient(dm_config.database)
    if not client.initialize():
        pytest.fail("Failed to initialize ChromaDB client")
    yield client


@pytest.fixture(scope="session")
def embedding_manager(dm_config: DMConfig) -> EmbeddingManager:
    """Provide embedding manager."""
    return EmbeddingManager(dm_config.content)


@pytest.fixture(scope="session")
def cache_manager(chroma_client: ChromaClient) -> CacheManager:
    """Provide cache manager."""
    return CacheManager(chroma_client)


@pytest.fixture(scope="session") 
def context_retriever(chroma_client: ChromaClient, embedding_manager: EmbeddingManager, dm_config: DMConfig) -> ContextRetriever:
    """Provide context retriever."""
    from talk_dnd_to_me.core.world_state_manager import WorldStateManager
    world_state_manager = WorldStateManager(chroma_client, embedding_manager)
    return ContextRetriever(
        chroma_client=chroma_client,
        embedding_manager=embedding_manager,
        world_state_manager=world_state_manager,
        config=dm_config.content
    )


@pytest.fixture(scope="function")
def dm_engine(dm_config: DMConfig) -> Generator[DMEngine, None, None]:
    """Provide initialized DM engine for each test."""
    engine = DMEngine(dm_config)
    if not engine.initialize():
        pytest.fail("Failed to initialize DM engine")
    yield engine


@pytest.fixture(scope="session")
def sample_character_data() -> dict:
    """Provide sample character data for testing."""
    return {
        "name": "Rose",
        "race": "Elf",
        "class": "Bard",
        "level": 3,
        "stats": {
            "strength": 10,
            "dexterity": 16,
            "constitution": 14,
            "intelligence": 12,
            "wisdom": 13,
            "charisma": 18
        },
        "hp": {"current": 22, "max": 22},
        "equipment": ["Rapier", "Light Crossbow", "Studded Leather Armor"]
    }


def pytest_configure(config):
    """Pytest configuration hook."""
    # Add custom markers
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "llm: Tests requiring LLM")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "caching: Caching related tests")
    config.addinivalue_line("markers", "rag: RAG and context tests")


def check_llm_available():
    """Check if local LLM is available."""
    try:
        response = requests.get("http://localhost:11434/v1/models", timeout=2)
        return response.status_code == 200
    except:
        return False


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    llm_available = check_llm_available()
    
    for item in items:
        # Mark tests that require LLM
        if "llm" in item.nodeid or "dm_engine" in str(item.fixturenames):
            item.add_marker(pytest.mark.llm)
            # Skip LLM tests if no LLM is available
            if not llm_available:
                item.add_marker(pytest.mark.skip(reason="Local LLM not available at localhost:11434"))
        
        # Mark integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
            
        # Mark caching tests
        if "caching" in item.nodeid or "cache" in item.nodeid:
            item.add_marker(pytest.mark.caching)
            
        # Mark RAG tests
        if "rag" in item.nodeid or "context" in item.nodeid:
            item.add_marker(pytest.mark.rag)