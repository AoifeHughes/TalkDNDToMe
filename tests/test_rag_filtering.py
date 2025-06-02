# -*- coding: utf-8 -*-
"""
Test RAG filtering and spoiler prevention.
"""

import pytest
from talk_dnd_to_me.ai.context_retriever import ContextRetriever


@pytest.mark.rag
class TestRAGFiltering:
    """Test RAG filtering and campaign progression respect."""

    def test_progression_filtering_blocks_future_content(
        self, context_retriever: ContextRetriever
    ):
        """Test that future acts are filtered out for Act I campaigns."""
        # Mock results representing different acts
        test_results = [
            {
                "text": "Death House content - Act I",
                "metadata": {
                    "act": "Act I",
                    "act_number": "I",
                    "is_dm_guide": False,
                    "story_relevance": "current_content",
                    "contains_spoilers": False,
                },
                "distance": 0.3,
            },
            {
                "text": "Dinner with the Devil - Act III spoiler content",
                "metadata": {
                    "act": "Act III",
                    "act_number": "III",
                    "is_dm_guide": False,
                    "story_relevance": "future_possibilities",
                    "contains_spoilers": True,
                },
                "distance": 0.2,
            },
            {
                "text": "DM Guide - Running Strahd",
                "metadata": {
                    "act": "Act III",
                    "act_number": "III",
                    "is_dm_guide": True,
                    "story_relevance": "dm_reference",
                    "contains_spoilers": False,
                },
                "distance": 0.4,
            },
        ]

        # Test filtering for Act I (current_act_number = 1)
        filtered = context_retriever._filter_by_progression(test_results, 1)

        # Should keep Act I content and DM guides, but filter spoilers
        assert len(filtered) == 2, f"Expected 2 results, got {len(filtered)}"

        # Check that Act I content is kept
        act_i_content = [r for r in filtered if r["metadata"]["act"] == "Act I"]
        assert len(act_i_content) == 1, "Act I content should be kept"

        # Check that DM guide is kept (even from future acts)
        dm_guides = [r for r in filtered if r["metadata"]["is_dm_guide"]]
        assert len(dm_guides) == 1, "DM guides should be kept"

        # Check that spoiler content is filtered
        spoilers = [r for r in filtered if r["metadata"]["contains_spoilers"]]
        assert len(spoilers) == 0, "Spoiler content should be filtered"

    def test_priority_scoring_boosts_current_act(
        self, context_retriever: ContextRetriever
    ):
        """Test that current act content gets priority boost."""
        test_result = {
            "text": "Current act content",
            "metadata": {
                "act": "Act I",
                "source": "Act I - Into the Mists/Arc A - Escape From Death House.md",
                "is_player_content": True,
                "contains_spoilers": False,
            },
            "distance": 0.5,
        }

        # Test priority scoring for current act
        new_distance = context_retriever._score_content_priority(
            test_result, "Act I", "Arc A"
        )

        # Should be improved (lower distance is better)
        assert (
            new_distance < test_result["distance"]
        ), f"Current act content should get priority boost: {new_distance} vs {test_result['distance']}"

    def test_priority_scoring_penalizes_spoilers(
        self, context_retriever: ContextRetriever
    ):
        """Test that spoiler content gets penalized."""
        test_result = {
            "text": "Future spoiler content",
            "metadata": {
                "act": "Act III",
                "contains_spoilers": True,
                "story_relevance": "future_possibilities",
            },
            "distance": 0.3,
        }

        # Test priority scoring
        new_distance = context_retriever._score_content_priority(
            test_result, "Act I", "Arc A"
        )

        # Should be penalized (higher distance is worse)
        assert (
            new_distance > test_result["distance"]
        ), f"Spoiler content should be penalized: {new_distance} vs {test_result['distance']}"

    def test_enhanced_query_intent_analysis(self, context_retriever: ContextRetriever):
        """Test enhanced query intent analysis."""
        test_cases = [
            {
                "query": "Tell me about Strahd and dinner",
                "expected_intents": [],  # Should not trigger specific intents
            },
            {
                "query": "What happened in our last session?",
                "expected_intents": ["session_recall"],
            },
            {
                "query": "I need to prepare for the next encounter",
                "expected_intents": ["dm_planning"],
            },
            {
                "query": "What is the final outcome of the campaign?",
                "expected_intents": ["seeks_future_info"],
            },
            {
                "query": "Tell me about the history of this place",
                "expected_intents": ["character_background"],
            },
        ]

        for case in test_cases:
            intent = context_retriever._enhanced_analyze_query_intent(case["query"])

            # Check that expected intents are detected
            for expected_intent in case["expected_intents"]:
                assert intent.get(
                    expected_intent
                ), f"Expected intent '{expected_intent}' not detected in query: '{case['query']}'"

    @pytest.mark.integration
    def test_no_spoilers_in_act_i_context(self, context_retriever: ContextRetriever):
        """Integration test: Ensure no spoilers appear in Act I context retrieval."""
        spoiler_queries = [
            "Tell me about Strahd",
            "What's in Castle Ravenloft?",
            "Who are the important NPCs in the campaign?",
        ]

        for query in spoiler_queries:
            context = context_retriever.get_relevant_context(query, max_chunks=5)

            # Check for specific late-game spoilers
            spoiler_phrases = [
                "dinner with the devil",
                "act iii",
                "act iv",
                "final battle",
                "amber temple",
                "ravenloft heist",
            ]

            found_spoilers = []
            for phrase in spoiler_phrases:
                if phrase in context.lower():
                    found_spoilers.append(phrase)

            assert (
                not found_spoilers
            ), f"Found spoilers {found_spoilers} in context for query '{query}'"


@pytest.mark.unit
class TestContentClassification:
    """Test content classification logic."""

    @pytest.mark.parametrize(
        "act_number,current_act,should_allow",
        [
            ("I", 1, True),  # Current act should be allowed
            ("II", 1, True),  # Next act allowed for foreshadowing (if no spoilers)
            ("III", 1, False),  # Far future should be blocked
            ("II", 2, True),  # Current act should be allowed
            ("I", 2, True),  # Past acts should be allowed
        ],
    )
    def test_act_filtering_logic(
        self,
        context_retriever: ContextRetriever,
        act_number: str,
        current_act: int,
        should_allow: bool,
    ):
        """Test act filtering logic with various scenarios."""
        test_result = {
            "metadata": {
                "act_number": act_number,
                "is_dm_guide": False,
                "contains_spoilers": False,
                "story_relevance": "current_content",
            }
        }

        filtered = context_retriever._filter_by_progression([test_result], current_act)

        if should_allow:
            assert (
                len(filtered) == 1
            ), f"Act {act_number} should be allowed for current act {current_act}"
        else:
            assert (
                len(filtered) == 0
            ), f"Act {act_number} should be blocked for current act {current_act}"

    def test_next_act_with_spoilers_blocked(self, context_retriever: ContextRetriever):
        """Test that next act content with spoilers is blocked."""
        test_result = {
            "metadata": {
                "act_number": "II",  # Next act
                "is_dm_guide": False,
                "contains_spoilers": True,  # Has spoilers
                "story_relevance": "current_content",
            }
        }

        filtered = context_retriever._filter_by_progression(
            [test_result], 1
        )  # Current act 1
        assert len(filtered) == 0, "Next act content with spoilers should be blocked"

    def test_next_act_future_possibilities_blocked(
        self, context_retriever: ContextRetriever
    ):
        """Test that next act content marked as future_possibilities is blocked."""
        test_result = {
            "metadata": {
                "act_number": "II",  # Next act
                "is_dm_guide": False,
                "contains_spoilers": False,
                "story_relevance": "future_possibilities",  # Future content
            }
        }

        filtered = context_retriever._filter_by_progression(
            [test_result], 1
        )  # Current act 1
        assert (
            len(filtered) == 0
        ), "Next act future_possibilities content should be blocked"
