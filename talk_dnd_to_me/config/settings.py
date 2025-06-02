# -*- coding: utf-8 -*-
"""Configuration settings for the D&D DM system."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    """ChromaDB configuration settings."""

    # Standardized collection names for content separation
    campaign_reference_collection: str = (
        "campaign_reference"  # DM guides, modules, NPCs
    )
    session_history_collection: str = "session_history"  # Completed session summaries
    current_session_collection: str = "current_session"  # Live session data
    character_collection: str = "character_data"  # Player characters, progression
    world_state_collection: str = "world_state"  # Current story position, flags
    cache_collection: str = "file_cache"  # File processing cache


@dataclass
class ContentConfig:
    """Content loading configuration."""

    content_directory: str = "Curse-of-Strahd-Reloaded"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_context_chunks: int = 5


@dataclass
class AIConfig:
    """AI/LLM configuration."""

    base_url: str = "http://localhost:11434/v1"
    api_key: str = "sk-xxxxxxxxxxxxxxxx"  # placeholder
    model_name: str = "llama.cpp"
    temperature: float = 0.7
    max_tokens: int = 500
    embedding_model_name: str = "all-MiniLM-L6-v2"
    enable_streaming: bool = True
    streaming_fallback_on_tools: bool = True


@dataclass
class GameConfig:
    """Game mechanics configuration."""

    max_dice_count: int = 20
    valid_dice_types: tuple = (4, 6, 8, 10, 12, 20, 100)
    conversation_history_limit: int = 10


@dataclass
class DMConfig:
    """Main DM engine configuration."""

    database: DatabaseConfig
    content: ContentConfig
    ai: AIConfig
    game: GameConfig

    @classmethod
    def default(cls) -> "DMConfig":
        """Create default configuration."""
        return cls(
            database=DatabaseConfig(),
            content=ContentConfig(),
            ai=AIConfig(),
            game=GameConfig(),
        )

    def update_content_directory(self, directory: str) -> "DMConfig":
        """Update content directory path."""
        self.content.content_directory = directory
        return self

    def update_ai_settings(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> "DMConfig":
        """Update AI configuration."""
        if base_url:
            self.ai.base_url = base_url
        if model_name:
            self.ai.model_name = model_name
        if temperature is not None:
            self.ai.temperature = temperature
        return self
