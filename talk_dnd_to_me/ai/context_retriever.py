# -*- coding: utf-8 -*-
"""Context retrieval for RAG (Retrieval-Augmented Generation)."""

import json
from typing import List, Optional, Dict, Any

from ..database.chroma_client import ChromaClient
from ..content.embeddings import EmbeddingManager
from ..config.settings import ContentConfig
from ..core.world_state_manager import WorldStateManager


class ContextRetriever:
    """Retrieves relevant context from knowledge base and session history."""

    def __init__(
        self,
        chroma_client: ChromaClient,
        embedding_manager: EmbeddingManager,
        config: ContentConfig,
        world_state_manager: Optional[WorldStateManager] = None,
    ):
        """Initialize context retriever.

        Args:
            chroma_client: ChromaDB client instance
            embedding_manager: Embedding manager instance
            config: Content configuration
            world_state_manager: Optional world state manager for story context
        """
        self.chroma_client = chroma_client
        self.embedding_manager = embedding_manager
        self.config = config
        self.world_state_manager = world_state_manager

    def get_relevant_context(
        self,
        query: str,
        max_chunks: Optional[int] = None,
        current_session_id: Optional[str] = None,
    ) -> str:
        """Retrieve relevant context using three-tier prioritization system.

        Args:
            query: Query text to find relevant context for
            max_chunks: Maximum number of chunks to retrieve
            current_session_id: Current session ID for prioritizing current session data

        Returns:
            Formatted context string
        """
        if max_chunks is None:
            max_chunks = self.config.max_context_chunks

        try:
            # Analyze query intent for smart prioritization
            query_intent = self._enhanced_analyze_query_intent(query)

            # Adjust retrieval strategy based on session recall intent
            is_session_recall = query_intent.get("session_recall", False)

            if is_session_recall:
                # For session recall queries, prioritize session history heavily
                tier1_context = self._get_current_session_context(
                    query, current_session_id, max_results=2
                )
                remaining_slots = max_chunks - len(tier1_context)

                # Give most slots to session history
                tier2_context = self._get_session_history_context(
                    query, query_intent, max_results=min(6, remaining_slots)
                )
                remaining_slots = max_chunks - len(tier1_context) - len(tier2_context)

                # Minimal campaign content for session recall queries
                tier3_context = self._get_campaign_context(
                    query, max_results=min(2, remaining_slots)
                )
            else:
                # Normal three-tier retrieval
                tier1_context = self._get_current_session_context(
                    query, current_session_id, max_results=2
                )
                remaining_slots = max_chunks - len(tier1_context)

                tier2_context = self._get_session_history_context(
                    query, query_intent, max_results=min(4, remaining_slots)
                )
                remaining_slots = max_chunks - len(tier1_context) - len(tier2_context)

                tier3_context = self._get_campaign_context(
                    query, max_results=remaining_slots
                )

            # Combine all context with priority ordering
            all_context = tier1_context + tier2_context + tier3_context

            # Format context for output
            return self._format_context_output(all_context)

        except Exception as e:
            print(f"Warning: Error retrieving context: {e}")
            return ""

    def test_retrieval(self, test_query: str = "What is Death House?") -> bool:
        """Test context retrieval functionality.

        Args:
            test_query: Query to test with

        Returns:
            True if retrieval works, False otherwise
        """
        try:
            # Check if content collection has any documents
            content_collection = self.chroma_client.get_collection("campaign_reference")
            content_count = content_collection.count() if content_collection else 0

            # Check if history collection exists
            history_collection = self.chroma_client.get_collection("current_session")
            history_count = history_collection.count() if history_collection else 0

            if content_count == 0:
                print(
                    "⚠ Warning: No content loaded in database yet (this is normal on first run)"
                )
                return True  # Don't treat this as an error

            # Test actual retrieval
            context = self.get_relevant_context(test_query)
            if context:
                print(
                    f"✓ Context retrieval working ({content_count} content docs, {history_count} history docs)"
                )
                return True
            else:
                print(
                    f"⚠ Warning: Context retrieval returned empty results ({content_count} content docs available)"
                )
                return False

        except Exception as e:
            print(f"✗ Error testing context retrieval: {e}")
            return False

    def _get_current_session_context(
        self, query: str, current_session_id: Optional[str], max_results: int
    ) -> List[Dict[str, Any]]:
        """Get context from current session (Tier 1 - Highest Priority).

        Args:
            query: User query
            current_session_id: Current session ID
            max_results: Maximum results to return

        Returns:
            List of context items
        """
        if not current_session_id:
            return []

        try:
            query_embedding = self.embedding_manager.embed_query(query)

            # Query current session data from current_session collection
            results = self.chroma_client.query_collection(
                "current_session",
                query_embeddings=[query_embedding],
                where={"session_id": current_session_id},
                n_results=max_results,
                include=["documents", "metadatas", "distances"],
            )

            context_items = []
            if results["documents"] and results["documents"][0]:
                for doc, metadata, distance in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                ):
                    try:
                        entry = json.loads(doc)
                        if entry.get("entry_type") in ["player_input", "dm_response"]:
                            context_items.append(
                                {
                                    "text": entry.get("content", ""),
                                    "source": "current_session",
                                    "priority": "highest",
                                    "metadata": metadata,
                                    "distance": distance * 0.5,  # Boost current session
                                }
                            )
                    except json.JSONDecodeError:
                        continue

            return context_items

        except Exception as e:
            print(f"Warning: Error retrieving current session context: {e}")
            return []

    def _get_session_history_context(
        self, query: str, query_intent: Dict[str, int], max_results: int
    ) -> List[Dict[str, Any]]:
        """Get context from session history summaries (Tier 2 - High Priority).

        Args:
            query: User query
            query_intent: Query intent analysis
            max_results: Maximum results to return

        Returns:
            List of context items
        """
        try:
            query_embedding = self.embedding_manager.embed_query(query)

            # Query session history collection
            results = self.chroma_client.query_collection(
                "session_history",
                query_embeddings=[query_embedding],
                n_results=max_results,
                include=["documents", "metadatas", "distances"],
            )

            context_items = []
            if results["documents"] and results["documents"][0]:
                for doc, metadata, distance in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                ):
                    # Calculate priority boost based on query intent and session recency
                    priority_boost = self._calculate_session_priority_boost(
                        metadata, query_intent
                    )

                    context_items.append(
                        {
                            "text": doc,
                            "source": "session_history",
                            "priority": "high",
                            "metadata": metadata,
                            "distance": distance
                            * (0.7 - priority_boost),  # Apply boost
                        }
                    )

            # Sort by adjusted distance (lower = more relevant)
            context_items.sort(key=lambda x: x["distance"])

            return context_items

        except Exception as e:
            print(f"Warning: Error retrieving session history context: {e}")
            return []

    def _filter_by_progression(
        self, results: List[Dict], current_act_number: int
    ) -> List[Dict]:
        """Filter out future content based on current campaign progression.

        Args:
            results: List of context results from ChromaDB
            current_act_number: Current act number (1-4)

        Returns:
            Filtered list of results
        """
        filtered = []
        for result in results:
            metadata = result.get("metadata", {})

            # Always allow DM guide content - DMs need access to everything
            if metadata.get("is_dm_guide"):
                filtered.append(result)
                continue

            # Filter by act progression
            content_act_number = metadata.get("act_number")
            if content_act_number:
                try:
                    # Convert Roman numerals to numbers if needed
                    if isinstance(content_act_number, str):
                        act_map = {"I": 1, "II": 2, "III": 3, "IV": 4}
                        content_act_num = act_map.get(content_act_number, 1)
                    else:
                        content_act_num = int(content_act_number)

                    # Allow current and past acts
                    if content_act_num <= current_act_number:
                        filtered.append(result)
                    # Allow limited next act content for foreshadowing
                    elif content_act_num == current_act_number + 1:
                        story_relevance = metadata.get("story_relevance", "")
                        # Exclude explicit future spoilers
                        if (
                            "future_possibilities" not in story_relevance
                            and not metadata.get("contains_spoilers", False)
                        ):
                            filtered.append(result)
                except (ValueError, TypeError):
                    # If we can't parse act number, include it to be safe
                    filtered.append(result)
            else:
                # No act number - include general content
                filtered.append(result)

        return filtered

    def _score_content_priority(
        self, result: Dict, current_act: str, current_arc: str = ""
    ) -> float:
        """Calculate priority score for content based on campaign progression.

        Args:
            result: Context result with metadata and distance
            current_act: Current act string (e.g., "Act I")
            current_arc: Current arc string (e.g., "Arc A")

        Returns:
            Adjusted distance score (lower is better)
        """
        base_distance = result.get("distance", 1.0)
        metadata = result.get("metadata", {})

        # Boost current act content
        if metadata.get("act") == current_act:
            base_distance *= 0.6

        # Extra boost for current arc content
        source = metadata.get("source", "")
        if current_arc and current_arc in source:
            base_distance *= 0.5

        # Boost player-facing content during gameplay
        if metadata.get("is_player_content"):
            base_distance *= 0.8

        # Penalize future spoiler content
        if metadata.get("contains_spoilers") or "future_possibilities" in metadata.get(
            "story_relevance", ""
        ):
            base_distance *= 1.5

        return base_distance

    def _enhanced_analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """Enhanced query intent analysis for better content filtering.

        Args:
            query: User query string

        Returns:
            Dictionary with intent analysis results
        """
        query_lower = query.lower()

        return {
            "seeks_future_info": any(
                word in query_lower
                for word in [
                    "ending",
                    "final",
                    "eventually",
                    "later",
                    "future",
                    "outcome",
                ]
            ),
            "character_background": any(
                word in query_lower
                for word in ["background", "history", "past", "before", "origin"]
            ),
            "immediate_context": any(
                word in query_lower
                for word in ["now", "current", "here", "present", "currently"]
            ),
            "location_inquiry": any(
                word in query_lower
                for word in ["where", "location", "place", "area", "region"]
            ),
            "session_recall": any(
                word in query_lower
                for word in ["session", "last time", "previous", "remember", "happened"]
            ),
            "dm_planning": any(
                word in query_lower
                for word in ["prepare", "plan", "guide", "advice", "suggest"]
            ),
        }

    def _get_campaign_context(
        self, query: str, max_results: int
    ) -> List[Dict[str, Any]]:
        """Get context from campaign content (Tier 3 - Normal Priority).

        Args:
            query: User query
            max_results: Maximum results to return

        Returns:
            List of context items
        """
        try:
            # Get current campaign progression from world state
            world_context = self.world_state_manager.get_story_relevance_context(query)
            current_act_number = world_context.get("current_act_number", 1)
            current_act = world_context.get("current_act", "Act I")
            current_arc = world_context.get("current_arc", "")

            query_embedding = self.embedding_manager.embed_query(query)

            # Enhanced query intent analysis
            query_intent = self._enhanced_analyze_query_intent(query)

            # Apply enhanced content filtering
            where_filter = None
            if query_intent.get("session_recall"):
                # For session recall, avoid DM guides and future possibilities
                where_filter = {
                    "$and": [
                        {"is_dm_guide": {"$ne": True}},
                        {"story_relevance": {"$ne": "future_possibilities"}},
                    ]
                }
            elif query_intent.get("dm_planning"):
                # DM planning queries can access more content
                where_filter = None
            elif query_intent.get("seeks_future_info"):
                # Explicitly seeking future info - allow but mark as low priority
                pass
            else:
                # Standard queries - filter spoilers
                where_filter = {"contains_spoilers": {"$ne": True}}

            results = self.chroma_client.query_collection(
                "campaign_reference",
                query_embeddings=[query_embedding],
                where=where_filter,
                n_results=max_results * 2,  # Get more results for filtering
                include=["documents", "metadatas", "distances"],
            )

            # Convert to context items for filtering
            raw_context_items = []
            if results["documents"] and results["documents"][0]:
                for doc, metadata, distance in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                ):
                    raw_context_items.append(
                        {
                            "text": doc,
                            "source": "campaign_content",
                            "priority": "normal",
                            "metadata": metadata,
                            "distance": distance,
                        }
                    )

            # Apply campaign progression filtering
            filtered_items = self._filter_by_progression(
                raw_context_items, current_act_number
            )

            # Apply priority scoring and sort
            for item in filtered_items:
                item["distance"] = self._score_content_priority(
                    item, current_act, current_arc
                )

            # Sort by distance (lower is better) and limit results
            filtered_items.sort(key=lambda x: x["distance"])
            context_items = filtered_items[:max_results]

            return context_items

        except Exception as e:
            print(f"Warning: Error retrieving campaign context: {e}")
            return []

    def _calculate_session_priority_boost(
        self, metadata: Dict[str, Any], query_intent: Dict[str, Any]
    ) -> float:
        """Calculate priority boost for session history based on recency and relevance.

        Args:
            metadata: Session metadata
            query_intent: Query intent analysis results

        Returns:
            Priority boost value (0.0 to 0.3)
        """
        boost = 0.0

        # Recency boost (more recent sessions get higher priority)
        session_number = metadata.get("session_number", 0)
        if session_number > 0:
            # Assume max 10 sessions for now, adjust as needed
            recency_boost = min(session_number / 10.0, 1.0) * 0.2
            boost += recency_boost

        # Intent-based boost
        if query_intent.get("session_recall", False):
            boost += 0.1  # Boost for session recall queries

        # Character/location relevance boost
        characters_mentioned = metadata.get("characters_mentioned", "")
        locations_mentioned = metadata.get("locations_mentioned", "")

        if query_intent.get("character_background", False) and characters_mentioned:
            boost += 0.05

        if query_intent.get("location_inquiry", False) and locations_mentioned:
            boost += 0.05

        return min(boost, 0.3)  # Cap at 0.3

    def _format_context_output(self, context_items: List[Dict[str, Any]]) -> str:
        """Format context items for output to the LLM.

        Args:
            context_items: List of context items

        Returns:
            Formatted context string
        """
        if not context_items:
            return ""

        # Sort by priority and distance
        priority_order = {"highest": 0, "high": 1, "normal": 2}
        context_items.sort(
            key=lambda x: (priority_order.get(x["priority"], 3), x["distance"])
        )

        context_parts = []

        for item in context_items:
            source = item["source"]
            text = item["text"]
            metadata = item.get("metadata", {})

            if source == "current_session":
                context_parts.append(f"[Current Session] {text}")
            elif source == "session_history":
                session_num = metadata.get("session_number", "Unknown")
                section_type = metadata.get("section_type", "general")
                context_parts.append(
                    f"[Session {session_num} - {section_type.title()}] {text}"
                )
            elif source == "campaign_content":
                content_type = metadata.get("content_type", "Unknown")
                context_parts.append(f"[Campaign Content - {content_type}] {text}")

        return "\n\n".join(context_parts)
