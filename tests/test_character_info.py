# -*- coding: utf-8 -*-
"""
Test character information retrieval.
"""

import pytest
import re
from talk_dnd_to_me.core.dm_engine import DMEngine


@pytest.mark.llm
class TestCharacterInfo:
    """Test character information retrieval functionality."""

    def test_character_name_retrieval(self, dm_engine: DMEngine):
        """Test that asking about character returns Rose's name."""
        query = "Tell me about my character"
        response = dm_engine.generate_response(query)

        assert (
            "Rose" in response
        ), f"Character name 'Rose' not found in: {response[:200]}..."

    def test_character_details_retrieval(self, dm_engine: DMEngine):
        """Test that character details are included in responses."""
        queries = [
            "What are my character's stats?",
            "Tell me about my character's abilities",
            "Who am I playing as?",
        ]

        for query in queries:
            response = dm_engine.generate_response(query)

            # Check for character details - be more flexible with keywords
            character_keywords = [
                "elf",
                "bard",
                "charisma",
                "level",
                "stats",
                "character",
                "rose",
                "ability",
                "score",
            ]
            found_keywords = [
                kw for kw in character_keywords if kw.lower() in response.lower()
            ]

            assert (
                found_keywords
            ), f"No character details found in response to '{query}': {response[:200]}..."

    def test_character_stats_include_numbers(self, dm_engine: DMEngine):
        """Test that character stat queries include numeric values."""
        query = "What are my character's ability scores?"
        response = dm_engine.generate_response(query)

        # Look for numbers that could be ability scores (typically 8-20)
        numbers = re.findall(r"\b\d+\b", response)
        stat_numbers = [int(n) for n in numbers if 6 <= int(n) <= 20]

        assert stat_numbers, f"No ability score numbers found in: {response[:200]}..."

    @pytest.mark.parametrize(
        "query",
        [
            "What's my character's name?",
            "Tell me about Rose",
            "What class is my character?",
        ],
    )
    def test_various_character_queries(self, dm_engine: DMEngine, query: str):
        """Test various ways of asking about the character."""
        response = dm_engine.generate_response(query)

        # Should get a meaningful response (not empty or error) - relaxed length requirement
        assert len(response) > 10, f"Response too short for query '{query}': {response}"
        assert (
            "error" not in response.lower()
        ), f"Error in response to '{query}': {response}"
        assert (
            "trouble generating" not in response.lower()
        ), f"LLM error in response to '{query}': {response}"
